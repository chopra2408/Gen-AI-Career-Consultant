import os
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
def preprocess_job_posting(url: str, llm: ChatGroq):
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

# --- Combined Resume and Portfolio Analysis ---
def analyze_combined_for_job(resume_text: str, portfolio_file: UploadFile, job_description, llm: ChatGroq):
    # Process the CSV portfolio file
    try:
        portfolio_bytes = portfolio_file.file.read()
        portfolio_str = portfolio_bytes.decode('utf-8')
        portfolio_df = pd.read_csv(StringIO(portfolio_str))
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid CSV file provided for portfolio.")

    if 'Technology' not in portfolio_df.columns:
        raise HTTPException(status_code=400, detail="CSV file must contain a 'Technology' column.")

    candidate_portfolio_skills = ", ".join(portfolio_df['Technology'].dropna().tolist())

    job_role = job_description.get("role", "Unknown Role")
    job_skills = job_description.get("skills", "No skills provided")
    job_desc_text = job_description.get("description", "No description provided")
    
    # Create a combined prompt that includes both resume content and portfolio skills
    prompt_combined = PromptTemplate.from_template("""
        ### JOB POSTING DETAILS:
        Role: {job_role}
        Skills Required: {job_skills}
        Job Description: {job_desc_text}

        ### RESUME CONTENT:
        {resume_text}

        ### PORTFOLIO SKILLS:
        {candidate_portfolio_skills}

        ### INSTRUCTION:
        1. Analyze the candidate’s resume and portfolio skills together.
        2. Compare the candidate's skills with the required job skills and calculate the percentage of required skills matched.
        3. If the candidate's skills match at least 80% of the required skills:
           - Mark Suitability as "Yes".
           - Return 5-10 technical interview questions with their answers that are relevant for the role.
           - Include 2-3 behavioral questions regarding the candidate’s projects.
           - List the matched skills and the percentage of required skills matched.
        4. If the candidate's skills match less than 80%:
           - Mark Suitability as "No".
           - Provide detailed reasons for unsuitability and identify specific skill gaps.
           - Offer 3-4 tailored suggestions for improvement.
           - List the matched skills and the percentage of required skills matched to be always shown.
        Only return valid JSON with no additional commentary.
        ### VALID JSON (NO PREAMBLE):
    """)
    
    formatted_prompt = prompt_combined.format(
        job_role=job_role,
        job_skills=job_skills,
        job_desc_text=job_desc_text,
        resume_text=resume_text,
        candidate_portfolio_skills=candidate_portfolio_skills
    )
    response = llm.invoke(formatted_prompt)
    response_content = response.content

    json_parser = JsonOutputParser()
    try:
        parsed_response = json_parser.parse(response_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse combined analysis JSON: {str(e)}")
    return parsed_response

# --- Existing Analysis Functions for Single Input (if needed) ---
def analyze_resume_for_job(resume_text: str, job_description, llm: ChatGroq):
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
        1. Compare the skills mentioned in the resume with the required skills.
        2. Calculate the percentage of required skills matched by the candidate's resume.
        3. If the candidate's skills match at least 80% of the required skills:
           - Suitability is "Yes"
           - Provide a detailed list of interview questions and their answers.
           - List the matched skills and the percentage of required skills matched.
        4. If the candidate's skills match less than 80%:
           - Suitability is "No"
           - Provide detailed reasons why the candidate is not suitable, ensuring to identify specific skill gaps or experiences lacking compared to job requirements.
           - Offer 3 to 4 tailored suggestions for improvement based on the job posting and ensure these suggestions are actionable.
           - List the matched skills and the percentage of required skills matched to be always shown.
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

def analyze_portfolio_for_job(portfolio_file: UploadFile, job_description, llm: ChatGroq):
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
        1. Compare the candidate's portfolio skills with the required job skills.
        2. Calculate the percentage of required skills matched by the candidate's portfolio.
        3. If the candidate's skills match at least 80% of the required skills:
           - Suitability is "Yes"
           - Provide 5-10 technical interview questions with answers that would be relevant for this role.
           - Include 2-3 behavioral questions about their portfolio projects.
           - List the matched skills and the percentage of required skills matched.
        4. If the candidate's skills match less than 80%:
           - Suitability is "No"
           - Provide detailed reasons for unsuitability.
           - Offer 3-4 tailored suggestions for improvement.
           - List the matched skills and percentage to be shown always.
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

def ensure_list(val):
    if isinstance(val, list):
        return val
    elif isinstance(val, str):
        # Split string into list items if separated by newlines
        return [item.strip() for item in val.split('\n') if item.strip()]
    return []

# --- Format the Analysis Output as an HTML Fragment ---
def format_string_response(result, job_info):
    suitability = result.get("Suitability", "N/A")
    interview_questions = result.get("Interview Questions", [])
    unsuitability_reasons = ensure_list(result.get("Reasons for Unsuitability", []))
    suggestions = ensure_list(result.get("Suggestions", []))
    matched_skills = ensure_list(result.get("Matched Skills", []))
    skill_match_percentage = result.get("Skill Match Percentage", "N/A")
    
    # For "Yes" suitability, ensure that more than 5 interview questions (i.e. at least 6) are provided.
    if suitability.lower() == "yes":
        if len(interview_questions) < 5:
            default_questions = [
                {
                    "Question": "Can you walk us through your most challenging project?",
                    "Answer": "This project involved [brief description] where I overcame [specific challenge] by [solution]."
                },
                {
                    "Question": "How do you stay updated with the latest developments in your field?",
                    "Answer": "I regularly engage with industry news, attend webinars, and follow key influencers."
                },
                {
                    "Question": "What strategies do you use to overcome technical challenges?",
                    "Answer": "I analyze the problem, research solutions, and consult with colleagues when necessary."
                },
                {
                    "Question": "Can you describe a time when you had to learn a new skill quickly?",
                    "Answer": "I took an online course and applied the knowledge immediately on a real-world project."
                },
                {
                    "Question": "How do you manage deadlines when multiple projects overlap?",
                    "Answer": "I prioritize tasks, set clear milestones, and maintain regular communication with my team."
                },
            ]
            # Calculate how many more questions are needed to reach at least 6.
            questions_needed = 5 - len(interview_questions)
            interview_questions.extend(default_questions[:questions_needed])
    
    job_role = job_info.get("role", "N/A")
    job_desc = job_info.get("description", "N/A")
    job_skills = job_info.get("skills", "N/A")
    
    job_details_html = f"""
        <h3>Job Details</h3>
        <p><strong>Role:</strong> {job_role}</p>
        <p><strong>Job Description:</strong> {job_desc}</p>
        <p><strong>Skills Required:</strong> {job_skills}</p>
    """
    
    matched_skills_html = f"""
        <h3>Matched Skills</h3>
        <p><strong>Percentage of Required Skills Matched:</strong> {skill_match_percentage}%</p>
        <ul>{"".join(f"<li>{s}</li>" for s in matched_skills)}</ul>
    """
    
    if suitability.lower() == "yes":
        extra_section = f"""
            <h3>Interview Questions</h3>
            <ul>{
                "".join(
                    f"<li><strong>Q:</strong> {item.get('Question', 'N/A')}<br><strong>A:</strong> {item.get('Answer', 'N/A')}</li>" 
                    for item in interview_questions
                )
            }</ul>
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
            {matched_skills_html}
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
    use_both: bool = Form(False),
    model_choice: str = Form("gemma2")  # Default model is now gemma2
):
    # Allowed models for selection
    allowed_models = {"llama-3.3-70b-versatile", "llama-3.2-3b-preview", "llama-3.1-8b-instant", "gemma2-9b-it", "mixtral-8x7b-32768"}
    if model_choice not in allowed_models:
        raise HTTPException(status_code=400, detail=f"Invalid model selected. Choose one of: {', '.join(allowed_models)}")
    
    if not url or (not portfolio_file and not resume_file):
        raise HTTPException(status_code=400, detail="Please provide a URL and either a Resume or Portfolio file.")
    
    try:
        # Create a new ChatGroq instance based on the user's model choice.
        llm = ChatGroq(
            temperature=0.2,
            groq_api_key=groq_api_key,
            model_name=model_choice
        )
        
        job_desc = preprocess_job_posting(url, llm)
        
        if use_both:
            if portfolio_file and resume_file:
                resume_info = extract_resume_info(resume_file)
                # Reset portfolio file pointer
                portfolio_file.file.seek(0)
                combined_result = analyze_combined_for_job(resume_info["content"], portfolio_file, job_desc, llm)
                formatted_result = format_string_response(combined_result, job_desc)
                final_fragment = f"""<div>{formatted_result}</div>"""
                return HTMLResponse(content=final_fragment, media_type="text/html")
            else:
                raise HTTPException(status_code=400, detail="Both resume and portfolio files are required when 'analyze both' is selected.")
        else:
            if resume_file:
                resume_info = extract_resume_info(resume_file)
                result = analyze_resume_for_job(resume_info["content"], job_desc, llm)
                formatted_result = format_string_response(result, job_desc)
                final_fragment = f"""<div>{formatted_result}</div>"""
                return HTMLResponse(content=final_fragment, media_type="text/html")
            elif portfolio_file:
                result = analyze_portfolio_for_job(portfolio_file, job_desc, llm)
                formatted_result = format_string_response(result, job_desc)
                final_fragment = f"""<div>{formatted_result}</div>"""
                return HTMLResponse(content=final_fragment, media_type="text/html")
            else:
                raise HTTPException(status_code=400, detail="Please provide either a resume or a portfolio file.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
