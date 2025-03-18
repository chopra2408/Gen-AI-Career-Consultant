from app import *
from langchain_core.output_parsers import JsonOutputParser
from fastapi import HTTPException
from langchain.prompts import PromptTemplate
from langchain_community.document_loaders import WebBaseLoader

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