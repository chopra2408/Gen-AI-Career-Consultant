# combined.py
from langchain.prompts import PromptTemplate
from fastapi import HTTPException, UploadFile
from io import StringIO
# from app import ChatGroq # Assuming app.py defines ChatGroq
from langchain_groq import ChatGroq # Make sure ChatGroq is imported
import pandas as pd
from langchain_core.output_parsers import JsonOutputParser
import os # Import os if needed for ChatGroq init

def analyze_combined_for_job(resume_text: str, portfolio_file: UploadFile, job_description, llm: ChatGroq):
    # Process the CSV portfolio file
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

    candidate_portfolio_skills = ", ".join(portfolio_df['Technology'].dropna().unique().tolist()) # Use unique skills

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

        ### PORTFOLIO SKILLS (CSV):
        {candidate_portfolio_skills}

        ### INSTRUCTION:
        1. Analyze the candidate’s resume content AND portfolio skills together against the job posting.
        2. Synthesize information from BOTH sources (resume and portfolio) to assess skills, experience, and project work.
        3. Compare the combined candidate profile with the required job skills and description.
        4. Calculate the overall percentage of required skills matched, considering evidence from both resume and portfolio. Provide the calculation or reasoning if possible.
        5. Based on the combined analysis:
           - If the overall match is 80% or higher: Set Suitability to "Yes". Generate *at least* 5 relevant technical interview questions with concise answers, drawing from job requirements and skills/experiences evident in BOTH resume and portfolio. Generate *at least* 2 behavioral questions related to projects or experiences mentioned in EITHER the resume or portfolio. List the matched skills (from both sources) and the calculated percentage.
           - If the overall match is less than 80%: Set Suitability to "No". Provide detailed reasons for unsuitability, identifying specific skill/experience gaps considering both resume and portfolio. Offer 3-4 specific, actionable suggestions for improvement tailored to bridge the gap towards the job requirements, potentially suggesting how to better showcase existing skills. List the matched skills (from both sources) and the calculated percentage.
        6. Structure the entire output as a single, valid JSON object with keys like "Suitability", "Skill Match Percentage", "Matched Skills", "Interview Questions" (list of objects with "Question" and "Answer"), "Behavioral Questions" (list of strings), "Reasons for Unsuitability" (list of strings), "Suggestions" (list of strings). Only include keys relevant to the suitability outcome.
        7. Ensure the JSON is valid and contains no preamble or commentary outside the JSON structure.

        ### VALID JSON OUTPUT EXAMPLE (Suitability: Yes):
        {{
          "Suitability": "Yes",
          "Skill Match Percentage": 88,
          "Matched Skills": ["Python", "Pandas", "SQL", "API Development", "Git", "Data Visualization"],
          "Interview Questions": [
             {{"Question": "Your resume mentions Python and your portfolio lists Pandas. How have you used them together for data analysis?", "Answer": "Likely used Pandas within Python scripts to load, clean (e.g., handle missing values, transform data types), analyze (e.g., group by, aggregate), and potentially visualize data."}},
             {{"Question": "The job requires API development, and it's listed in your portfolio. Can you describe an API you built or consumed?", "Answer": "Candidate should describe a specific project, mentioning the framework (e.g., Flask, FastAPI, Node/Express) or method (e.g., REST principles, specific endpoints) used."}},
             {{"Question": "Explain how you would version control your code using Git, as mentioned on your resume.", "Answer": "Using commands like git clone, git add, git commit, git push, git pull, git branch, git merge. Emphasize commit frequency and meaningful messages."}},
             {{"Question": "Write a SQL query to find users who have placed more than 5 orders.", "Answer": "SELECT CustomerID, COUNT(OrderID) FROM Orders GROUP BY CustomerID HAVING COUNT(OrderID) > 5;"}},
             {{"Question": "What data visualization libraries (mentioned in portfolio) have you used and for what purpose?", "Answer": "Candidate should name libraries (e.g., Matplotlib, Seaborn, Plotly) and describe creating charts (e.g., bar, line, scatter) to communicate insights."}}
          ],
          "Behavioral Questions": [
            "Tell me about the 'Data Cleaning Project' listed in your portfolio. What was the most challenging aspect?",
            "Your resume mentions collaborating on a team project. How did you handle disagreements within the team?"
          ]
        }}

        ### VALID JSON OUTPUT EXAMPLE (Suitability: No):
        {{
          "Suitability": "No",
          "Skill Match Percentage": 65,
          "Matched Skills": ["Python", "SQL", "Git"],
          "Reasons for Unsuitability": [
            "While Python and SQL are present, lacks demonstrated experience with Pandas (portfolio) or data analysis tasks (resume) required for the role.",
            "Missing required API development skills (not found in resume or portfolio).",
            "No evidence of data visualization experience, which is preferred."
          ],
          "Suggestions": [
            "Undertake projects specifically using Pandas for data manipulation and analysis; add these to the portfolio.",
            "Learn basics of REST API development (e.g., using Python Flask/FastAPI) and build a simple API project.",
            "Explore data visualization libraries like Matplotlib or Seaborn and add a visualization component to a project.",
            "Update resume to quantify achievements in Python/SQL projects if possible."
          ]
        }}

        ### GENERATE JSON:
    """)

    formatted_prompt = prompt_combined.format(
        job_role=job_role,
        job_skills=job_skills,
        job_desc_text=job_desc_text,
        resume_text=resume_text,
        candidate_portfolio_skills=candidate_portfolio_skills
    )
    # print("--- Combined Prompt ---")
    # print(formatted_prompt) # For debugging
    response = llm.invoke(formatted_prompt)
    response_content = response.content
    # print("--- Combined LLM Raw Response ---")
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
        print(f"Failed to parse combined analysis JSON. Raw content:\n{response_content}") # Log raw content on error
        raise HTTPException(status_code=500, detail=f"Failed to parse combined analysis JSON from LLM. Error: {str(e)}. Raw response: {response_content[:500]}...") # Include part of raw response in error

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
