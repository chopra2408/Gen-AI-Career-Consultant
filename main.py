import os
import json
from io import StringIO
from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse
import pandas as pd
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import PyPDF2
import docx
from langchain_community.document_loaders import WebBaseLoader
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY must be set in your environment variables.")

# (Optional) Set a default USER_AGENT if not set
if not os.getenv("USER_AGENT"):
    os.environ["USER_AGENT"] = "GenAICareerConsultant/1.0"

# Initialize FastAPI app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the language model using ChatGroq.
llm = ChatGroq(
    temperature=0.2,
    groq_api_key=groq_api_key,
    model_name="gemma2-9b-it"
)

# --- Utility Functions for Document Parsing ---

def parse_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted
    return text

def parse_docx(file):
    doc = docx.Document(file)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def extract_resume_info(file: UploadFile):
    if file.content_type == "application/pdf":
        text = parse_pdf(file.file)
    elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        text = parse_docx(file.file)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a PDF or DOCX file.")
    return {"content": text}

# --- Job Posting Extraction ---
def preprocess_job_posting(url: str):
    try:
        loader = WebBaseLoader(url)
        page_data = loader.load().pop().page_content
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load or scrape the URL: {str(e)}")

    prompt_extract = PromptTemplate.from_template(''' 
        ### SCRAPED TEXT FROM WEBSITE:
        {page_data}
        ### INSTRUCTION:
        The scraped text is from the career page of a website.
        Extract and return the following information in JSON format:
          - role
          - skills (the skills required for the job)
          - description (a brief job description)
        Only return a valid JSON response with no additional commentary.
        ### VALID JSON (NO PREAMBLE):
    ''')
    formatted_prompt = prompt_extract.format(page_data=page_data)
    response = llm.invoke(formatted_prompt)
    response_content = response.content

    json_parser = JsonOutputParser()
    try:
        json_res = json_parser.parse(response_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse job posting JSON: {str(e)}")
    
    return json_res

# --- Analysis for Resume ---
def analyze_resume_for_job(resume_text: str, job_description):
    job_role = job_description.get("role", "Unknown Role")
    job_skills = job_description.get("skills", "No skills provided")
    job_desc_text = job_description.get("description", "No description provided")
    
    prompt_resume_analysis = PromptTemplate.from_template(""" 
        ### JOB POSTING DETAILS:
        Role: {job_role}
        Skills Required: {job_skills}
        Job Description: {job_desc_text}

        ### RESUME CONTENT:
        {resume_text}

        ### INSTRUCTION:
        Compare the skills mentioned in the resume with the required skills.
        If the candidate's skills match at least 80% of the required skills, then:
           - Suitability is "Yes"
           - Provide a detailed list of interview questions.
        Otherwise:
           - Suitability is "No"
           - Provide detailed reasons why the candidate is not suitable. Ensure to include specific gaps in skills or experiences.
           - Offer tailored suggestions for improvement based on the job posting. Ensure these suggestions are actionable.
        Only return valid JSON with no additional commentary.
        ### VALID JSON (NO PREAMBLE):
    """)
    
    formatted_prompt = prompt_resume_analysis.format(
        job_role=job_role,
        job_skills=job_skills,
        job_desc_text=job_desc_text,
        resume_text=resume_text
    )
    response = llm.invoke(formatted_prompt)
    response_content = response.content

    json_parser = JsonOutputParser()
    try:
        parsed_response = json_parser.parse(response_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse resume analysis JSON: {str(e)}")
    return parsed_response

# --- Analysis for Portfolio ---
def analyze_portfolio_for_job(portfolio_file: UploadFile, job_description):
    try:
        portfolio_bytes = portfolio_file.file.read()
        portfolio_str = portfolio_bytes.decode('utf-8')
        portfolio_df = pd.read_csv(StringIO(portfolio_str))
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid CSV file provided for portfolio.")
    
    if 'Technology' not in portfolio_df.columns:
        raise HTTPException(status_code=400, detail="CSV file must contain a 'Technology' column.")
    
    candidate_skills = ", ".join(portfolio_df['Technology'].dropna().tolist())
    
    job_role = job_description.get("role", "Unknown Role")
    job_skills = job_description.get("skills", "No skills provided")
    job_desc_text = job_description.get("description", "No description provided")
    
    prompt_portfolio_analysis = PromptTemplate.from_template(""" 
        ### JOB POSTING DETAILS:
        Role: {job_role}
        Skills Required: {job_skills}
        Job Description: {job_desc_text}

        ### CANDIDATE PORTFOLIO SKILLS:
        {candidate_skills}

        ### INSTRUCTION:
        Compare the candidate's portfolio skills with the required job skills.
        If the candidate's skills match at least 80% of the required skills, then:
           - Suitability is "Yes"
           - Provide a detailed list of interview questions.
        Otherwise:
           - Suitability is "No"
           - Provide detailed reasons why the candidate is not suitable, ensuring to identify specific skill gaps or experiences lacking compared to job requirements.
           - Offer tailored suggestions for improvement based on the job posting and ensure these suggestions are actionable.
        Only return valid JSON with no additional commentary.
        ### VALID JSON (NO PREAMBLE):
    """)
    
    formatted_prompt = prompt_portfolio_analysis.format(
        job_role=job_role,
        job_skills=job_skills,
        job_desc_text=job_desc_text,
        candidate_skills=candidate_skills
    )
    response = llm.invoke(formatted_prompt)
    response_content = response.content

    json_parser = JsonOutputParser()
    try:
        parsed_response = json_parser.parse(response_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse portfolio analysis JSON: {str(e)}")
    return parsed_response

# --- Helper function to ensure a value is a list ---
def ensure_list(val):
    if isinstance(val, list):
        return val
    elif isinstance(val, str):
        return [val.replace("\n", " ").strip()]
    return []

# --- Format the Analysis Output as an HTML Fragment ---
def format_string_response(result, job_info):
    suitability = result.get("Suitability", "N/A")
    interview_questions = ensure_list(result.get("Interview Questions", []))
    unsuitability_reasons = ensure_list(result.get("Reasons for Unsuitability", []))
    suggestions = ensure_list(result.get("Suggestions", []))
    
    # Fallback for empty unsuitability reasons
    if suitability.lower() == "no" and not unsuitability_reasons:
        unsuitability_reasons.append("No specific reasons provided. Please ensure that your resume aligns better with the job requirements.")

    job_role = job_info.get("role", "N/A")
    job_desc = job_info.get("description", "N/A")
    job_skills = job_info.get("skills", "N/A")
    
    job_details_html = f"""
        <h3>Job Details</h3>
        <p><strong>Role:</strong> {job_role}</p>
        <p><strong>Job Description:</strong> {job_desc}</p>
        <p><strong>Skills Required:</strong> {job_skills}</p>
    """
    
    if suitability.lower() == "yes":
        extra_section = f"""
            <h3>Interview Questions</h3>
            <ul>{"".join(f"<li>{q}</li>" for q in interview_questions)}</ul>
        """
    else:
        extra_section = f"""
            <h3>Reasons for Unsuitability</h3>
            <ul>{"".join(f"<li>{r}</li>" for r in unsuitability_reasons)}</ul>
            <h3>Suggestions for Improvement</h3>
            <ul>{"".join(f"<li>{s}</li>" for s in suggestions)}</ul>
        """
    
    formatted_html = f"""
        <div class="analysis-result" style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 8px; background-color: #ffffff; color: #000000;">
            <h2>Suitability: {suitability}</h2>
            {job_details_html}
            {extra_section}
        </div>
    """
    return formatted_html

# --- Main Endpoint ---
@app.post("/analyze/")
async def analyze(
    url: str = Form(...),
    portfolio_file: UploadFile = None,
    resume_file: UploadFile = None,
    use_both: bool = Form(False)
):
    if not url or (not portfolio_file and not resume_file):
        raise HTTPException(status_code=400, detail="Please provide a URL and either a Resume or Portfolio file.")
    
    try:
        job_desc = preprocess_job_posting(url)
        
        if use_both:
            if portfolio_file and resume_file:
                resume_info = extract_resume_info(resume_file)
                portfolio_file.file.seek(0)
                portfolio_result = analyze_portfolio_for_job(portfolio_file, job_desc)
                resume_result = analyze_resume_for_job(resume_info["content"], job_desc)
                
                formatted_resume = format_string_response(resume_result, job_desc)
                formatted_portfolio = format_string_response(portfolio_result, job_desc)
                
                final_fragment = f"""
                    <div>
                        <h2>Resume Analysis</h2>
                        {formatted_resume}
                        <h2>Portfolio Analysis</h2>
                        {formatted_portfolio}
                    </div>
                """
                return HTMLResponse(content=final_fragment, media_type="text/html")
            else:
                raise HTTPException(status_code=400, detail="Both resume and portfolio files are required when 'analyze both' is selected.")
        else:
            if resume_file:
                resume_info = extract_resume_info(resume_file)
                result = analyze_resume_for_job(resume_info["content"], job_desc)
                formatted_result = format_string_response(result, job_desc)
                final_fragment = f"""<div>{formatted_result}</div>"""
                return HTMLResponse(content=final_fragment, media_type="text/html")
            elif portfolio_file:
                portfolio_result = analyze_portfolio_for_job(portfolio_file, job_desc)
                formatted_result = format_string_response(portfolio_result, job_desc)
                final_fragment = f"""<div>{formatted_result}</div>"""
                return HTMLResponse(content=final_fragment, media_type="text/html")
            else:
                raise HTTPException(status_code=400, detail="Please provide either a resume or a portfolio file.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
