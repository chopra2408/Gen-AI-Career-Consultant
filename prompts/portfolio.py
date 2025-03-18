from langchain.prompts import PromptTemplate
from fastapi import HTTPException, UploadFile
from io import StringIO
from app import *
import pandas as pd
from langchain_core.output_parsers import JsonOutputParser

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