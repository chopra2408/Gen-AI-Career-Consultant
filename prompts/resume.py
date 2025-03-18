from langchain.prompts import PromptTemplate
from fastapi import HTTPException 
from app import *
from langchain_core.output_parsers import JsonOutputParser

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