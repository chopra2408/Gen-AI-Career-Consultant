# prompts/posting.py
from app import * # Remove this if ChatGroq is imported directly below
from langchain_core.output_parsers import JsonOutputParser
from fastapi import HTTPException
from langchain.prompts import PromptTemplate
from langchain_community.document_loaders import WebBaseLoader
from langchain_groq import ChatGroq # Make sure ChatGroq is imported here

def preprocess_job_posting(url: str, llm: ChatGroq):
    try:
        # Consider adding headers for robustness if needed by the site
        # headers = {"User-Agent": os.getenv("USER_AGENT", "GenAICareerConsultant/1.0")}
        # loader = WebBaseLoader(url, header_template=headers)
        loader = WebBaseLoader(url)
        docs = loader.load()
        if not docs:
             raise HTTPException(status_code=404, detail=f"Could not retrieve content from the URL: {url}")
        page_data = docs[0].page_content # Use docs[0] instead of pop() for clarity
    except Exception as e:
        # Catch more specific exceptions if possible (e.g., network errors)
        raise HTTPException(status_code=400, detail=f"Failed to load or scrape the URL: {str(e)}")

    if not page_data:
         raise HTTPException(status_code=400, detail="No content found on the page after loading.")

    prompt_extract = PromptTemplate.from_template('''
        ### SCRAPED TEXT FROM WEBSITE:
        {page_data}
        ### INSTRUCTION:
        Analyze the scraped text from the job posting page.
        Extract and return ONLY the following information as a single, valid JSON object:
          - "role": The specific job title or role being advertised.
          - "skills": A list of key skills, technologies, or qualifications required for the job. If listed as a string, try to parse into a list. If not found, use an empty list [].
          - "description": A concise summary of the job description, responsibilities, or role overview.
        Ensure the output is ONLY the JSON object, with no introductory text, explanations, or markdown formatting like ```json ... ```.
        If you cannot reliably extract a field, use a suitable default like "Not specified" for strings or an empty list for skills.

        ### VALID JSON OUTPUT EXAMPLE:
        {{
          "role": "Software Engineer",
          "skills": ["Python", "React", "AWS", "SQL"],
          "description": "Develop and maintain web applications using Python and React..."
        }}

        ### GENERATE JSON:
    ''') # Added more specific instructions for the LLM

    formatted_prompt = prompt_extract.format(page_data=page_data)
    try:
        response = llm.invoke(formatted_prompt)
        response_content = response.content.strip()

        # Clean potential markdown ```json ... ``` or ``` ... ```
        if response_content.startswith("```json"):
            response_content = response_content[7:-3].strip()
        elif response_content.startswith("```"):
             response_content = response_content[3:-3].strip()

    except Exception as e:
         # Handle potential LLM API errors
         raise HTTPException(status_code=503, detail=f"Error invoking LLM for job posting analysis: {str(e)}")


    json_parser = JsonOutputParser()
    try:
        parsed_output = json_parser.parse(response_content)
    except Exception as e:
        print(f"Failed to parse job posting JSON. Raw content:\n{response_content}") # Log raw content
        raise HTTPException(status_code=500, detail=f"Failed to parse job posting JSON from LLM response. Error: {str(e)}. Raw response snippet: {response_content[:200]}...")

    # --- FIX: Ensure the result is a dictionary ---
    job_details_dict = None
    if isinstance(parsed_output, list):
        if len(parsed_output) == 1 and isinstance(parsed_output[0], dict):
            # If it's a list containing a single dictionary, extract the dictionary
            job_details_dict = parsed_output[0]
            print("Warning: LLM returned a list containing one job details object. Extracted the object.")
        else:
            # If it's a list but not the expected format, raise an error
            raise HTTPException(status_code=500, detail=f"Unexpected format from job posting analysis: Received a list, expected a single dictionary. Content: {str(parsed_output)}")
    elif isinstance(parsed_output, dict):
        # If it's already a dictionary, use it directly
        job_details_dict = parsed_output
    else:
        # If it's neither a list nor a dictionary, raise an error
        raise HTTPException(status_code=500, detail=f"Unexpected data type from job posting analysis: Expected dict, got {type(parsed_output)}. Content: {str(parsed_output)}")

    # --- END FIX ---

    # Optional: Validate essential keys exist, though .get() in consuming functions handles missing keys
    # required_keys = ["role", "skills", "description"]
    # if not all(key in job_details_dict for key in required_keys):
    #     print(f"Warning: Job details dictionary missing some keys. Found: {job_details_dict.keys()}")
        # Decide if this should be an error or just proceed with defaults

    return job_details_dict # Return the guaranteed dictionary
