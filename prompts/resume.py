# resume.py
from langchain.prompts import PromptTemplate
from fastapi import HTTPException
# from app import ChatGroq # Assuming app.py defines ChatGroq
from langchain_groq import ChatGroq # Make sure ChatGroq is imported
from langchain_core.output_parsers import JsonOutputParser
import os # Import os if needed for ChatGroq init

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
        1. Analyze the resume content against the job posting details.
        2. Compare the skills, experience, and qualifications mentioned in the resume with the required skills and job description.
        3. Calculate the percentage of required skills explicitly mentioned or strongly implied in the resume. Provide the calculation or reasoning if possible.
        4. Based *only* on the analysis of the resume against the job requirements:
           - If the match (skills and relevant experience) is 80% or higher: Set Suitability to "Yes". Generate *at least* 5 relevant technical interview questions with concise answers based on the job requirements and the candidate's resume. Generate *at least* 2 behavioral questions related to experiences described in the resume. List the matched skills and the calculated percentage.
           - If the match is less than 80%: Set Suitability to "No". Provide detailed reasons for unsuitability focusing on specific skill gaps or missing experience highlighted in the job description but absent in the resume. Offer 3-4 specific, actionable suggestions for improvement tailored to bridge the gap (e.g., skills to acquire, experiences to gain, resume adjustments). List the matched skills and the calculated percentage.
        5. Structure the entire output as a single, valid JSON object with keys like "Suitability", "Skill Match Percentage", "Matched Skills", "Interview Questions" (list of objects with "Question" and "Answer"), "Behavioral Questions" (list of strings), "Reasons for Unsuitability" (list of strings), "Suggestions" (list of strings). Only include keys relevant to the suitability outcome.
        6. Ensure the JSON is valid and contains no preamble or commentary outside the JSON structure.

        ### VALID JSON OUTPUT EXAMPLE (Suitability: Yes):
        {{
          "Suitability": "Yes",
          "Skill Match Percentage": 90,
          "Matched Skills": ["Java", "Spring Boot", "SQL", "Microservices", "AWS"],
          "Interview Questions": [
            {{"Question": "Explain the difference between @Component, @Service, and @Repository in Spring.", "Answer": "@Component is a generic stereotype. @Service is for business logic, @Repository is for data access layers. All are specialized @Components."}},
            {{"Question": "How would you implement security in a Spring Boot application?", "Answer": "Using Spring Security, configure authentication (e.g., JWT, OAuth2) and authorization (e.g., method security, URL patterns)."}},
            {{"Question": "Describe your experience with microservices.", "Answer": "Based on the resume, the candidate designed and deployed microservices using Spring Boot, likely involving service discovery (Eureka/Consul) and communication (REST/messaging queues)."}},
            {{"Question": "What AWS services have you used according to your resume?", "Answer": "The resume mentions EC2, S3, and RDS, suggesting experience with core compute, storage, and database services."}},
            {{"Question": "Write a SQL query to join two tables: Orders and Customers.", "Answer": "SELECT * FROM Orders o JOIN Customers c ON o.CustomerID = c.CustomerID;"}}
          ],
          "Behavioral Questions": [
            "Your resume mentions leading a project migration; can you elaborate on the challenges and your role?",
            "Tell me about the 'XYZ Project' listed on your resume. What was your specific contribution?"
          ]
        }}

        ### VALID JSON OUTPUT EXAMPLE (Suitability: No):
        {{
          "Suitability": "No",
          "Skill Match Percentage": 50,
          "Matched Skills": ["Java", "SQL"],
          "Reasons for Unsuitability": [
            "Lacks required experience with Spring Boot framework.",
            "No mention of microservices architecture experience.",
            "Missing experience with cloud platforms like AWS, which is listed as required."
          ],
          "Suggestions": [
            "Focus on learning Spring Boot through tutorials and building small projects.",
            "Explore microservices concepts and patterns; consider a project demonstrating basic microservice communication.",
            "Gain hands-on experience with core AWS services (EC2, S3, RDS) via the AWS Free Tier.",
            "Update the resume to clearly highlight any relevant project work, even academic, using Java and SQL."
          ]
        }}

        ### GENERATE JSON:
    """)

    formatted_prompt = prompt_resume_analysis.format(
        job_role=job_role,
        job_skills=job_skills,
        job_desc_text=job_desc_text,
        resume_text=resume_text
    )
    # print("--- Resume Prompt ---")
    # print(formatted_prompt) # For debugging
    response = llm.invoke(formatted_prompt)
    response_content = response.content
    # print("--- Resume LLM Raw Response ---")
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
        print(f"Failed to parse resume analysis JSON. Raw content:\n{response_content}") # Log raw content on error
        raise HTTPException(status_code=500, detail=f"Failed to parse resume analysis JSON from LLM. Error: {str(e)}. Raw response: {response_content[:500]}...") # Include part of raw response in error

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
