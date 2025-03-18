from langchain.prompts import PromptTemplate
from fastapi import HTTPException, UploadFile
from io import StringIO
from app import *
import pandas as pd
from langchain_core.output_parsers import JsonOutputParser

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