# portfolio.py
from langchain.prompts import PromptTemplate
from fastapi import HTTPException, UploadFile
from io import StringIO
# Assuming app.py defines ChatGroq, adjust if necessary
# from app import ChatGroq
from langchain_groq import ChatGroq # Make sure ChatGroq is imported
import pandas as pd
from langchain_core.output_parsers import JsonOutputParser
import os # Import os if needed for ChatGroq init

def analyze_portfolio_for_job(portfolio_file: UploadFile, job_description, llm: ChatGroq):
    try:
        portfolio_bytes = portfolio_file.file.read()
        # Attempt common encodings if utf-8 fails
        try:
            portfolio_str = portfolio_bytes.decode('utf-8')
        except UnicodeDecodeError:
            try:
                portfolio_str = portfolio_bytes.decode('latin-1')
            except UnicodeDecodeError:
                portfolio_str = portfolio_bytes.decode('cp1252') # Another common one
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading or decoding portfolio file: {e}")

    try:
        portfolio_df = pd.read_csv(StringIO(portfolio_str))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV file provided for portfolio. Error: {e}")

    if 'Technology' not in portfolio_df.columns:
        raise HTTPException(status_code=400, detail="Portfolio CSV file must contain a 'Technology' column.")

    candidate_skills = ", ".join(portfolio_df['Technology'].dropna().unique().tolist()) # Use unique skills

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
        2. Calculate the percentage of required skills matched by the candidate's portfolio. Provide the calculation or reasoning if possible.
        3. Based *only* on the skill match percentage:
           - If the match is 80% or higher: Set Suitability to "Yes". Generate *at least* 5 relevant technical interview questions with concise answers based on the job requirements and candidate skills. Generate *at least* 2 behavioral questions specifically about potential portfolio projects related to the job skills. List the matched skills and the calculated percentage.
           - If the match is less than 80%: Set Suitability to "No". Provide detailed reasons for unsuitability focusing on the skill gap. Offer 3-4 specific, actionable suggestions for improvement tailored to bridge the gap towards the job requirements. List the matched skills and the calculated percentage.
        4. Structure the entire output as a single, valid JSON object with keys like "Suitability", "Skill Match Percentage", "Matched Skills", "Interview Questions" (list of objects with "Question" and "Answer"), "Behavioral Questions" (list of strings), "Reasons for Unsuitability" (list of strings), "Suggestions" (list of strings). Only include keys relevant to the suitability outcome (e.g., don't include "Reasons for Unsuitability" if Suitability is "Yes").
        5. Ensure the JSON is valid and contains no preamble or commentary outside the JSON structure.

        ### VALID JSON OUTPUT EXAMPLE (Suitability: Yes):
        {{
          "Suitability": "Yes",
          "Skill Match Percentage": 85,
          "Matched Skills": ["Python", "SQL", "Pandas", "API Development"],
          "Interview Questions": [
            {{"Question": "Explain how you would use Pandas to clean a dataset with missing values.", "Answer": "Identify missing values using isnull().sum(), then decide on a strategy like imputation (mean, median, mode) using fillna() or dropping rows/columns using dropna()."}},
            {{"Question": "Describe the difference between REST and SOAP APIs.", "Answer": "REST is an architectural style using standard HTTP methods (GET, POST, PUT, DELETE), typically stateless and often uses JSON. SOAP is a protocol with stricter standards, uses XML for messages, and can maintain state."}},
            {{"Question": "How do you handle errors in Python?", "Answer": "Using try-except blocks to catch specific exceptions and handle them gracefully, possibly logging the error or providing user feedback."}},
            {{"Question": "Write a SQL query to find the second highest salary.", "Answer": "SELECT MAX(Salary) FROM Employees WHERE Salary < (SELECT MAX(Salary) FROM Employees);"}},
            {{"Question": "What is the purpose of an index in a database?", "Answer": "Indexes speed up data retrieval operations (SELECT queries) by creating a data structure that allows faster lookups, at the cost of slower writes (INSERT, UPDATE, DELETE) and storage space."}}
          ],
          "Behavioral Questions": [
            "Can you walk me through the project where you implemented the API? What challenges did you face?",
            "Tell me about a time you used Python and Pandas for data analysis in one of your portfolio projects. What was the outcome?"
          ]
        }}

        ### VALID JSON OUTPUT EXAMPLE (Suitability: No):
        {{
          "Suitability": "No",
          "Skill Match Percentage": 60,
          "Matched Skills": ["Python", "SQL"],
          "Reasons for Unsuitability": [
            "Lacks experience with Pandas for data manipulation, which is crucial for the role.",
            "No demonstrated experience with API Development (REST/SOAP) as required.",
            "Missing cloud platform experience (e.g., AWS, Azure) mentioned in the job description."
          ],
          "Suggestions": [
            "Complete online courses or tutorials focused on Pandas dataframes and data manipulation.",
            "Build a small project involving creating or consuming a REST API (e.g., using Flask or FastAPI).",
            "Gain familiarity with a cloud platform like AWS S3 or EC2 through their free tier offerings.",
            "Update portfolio to explicitly showcase projects using Python and SQL, detailing the specific tasks performed."
          ]
        }}

        ### GENERATE JSON:
    """)

    formatted_prompt = prompt_portfolio_analysis.format(
        job_role=job_role,
        job_skills=job_skills,
        job_desc_text=job_desc_text,
        candidate_skills=candidate_skills
    )
    # print("--- Portfolio Prompt ---")
    # print(formatted_prompt) # For debugging
    response = llm.invoke(formatted_prompt)
    response_content = response.content
    # print("--- Portfolio LLM Raw Response ---")
    # print(response_content) # For debugging

    # Clean potential markdown ```json ... ```
    if response_content.strip().startswith("```json"):
        response_content = response_content.strip()[7:-3].strip()
    elif response_content.strip().startswith("```"):
         response_content = response_content.strip()[3:-3].strip()


    json_parser = JsonOutputParser()
    try:
        parsed_response = json_parser.parse(response_content)
    except Exception as e:
        print(f"Failed to parse portfolio analysis JSON. Raw content:\n{response_content}") # Log raw content on error
        raise HTTPException(status_code=500, detail=f"Failed to parse portfolio analysis JSON from LLM. Error: {str(e)}. Raw response: {response_content[:500]}...") # Include part of raw response in error

    # Add default empty lists if keys are missing but expected based on suitability
    suitability = parsed_response.get("Suitability", "N/A").lower()
    if suitability == "yes":
        parsed_response.setdefault("Interview Questions", [])
        parsed_response.setdefault("Behavioral Questions", [])
    else:
        parsed_response.setdefault("Reasons for Unsuitability", [])
        parsed_response.setdefault("Suggestions", [])
    parsed_response.setdefault("Matched Skills", [])


    return parsed_response
