from fastapi import APIRouter, Form, UploadFile, HTTPException, File
from fastapi.responses import HTMLResponse
from app import *
from typing import Optional
from prompts.posting import preprocess_job_posting
from prompts.combined import analyze_combined_for_job
from prompts.resume import analyze_resume_for_job
from prompts.portfolio import analyze_portfolio_for_job
from utility.parse import extract_resume_info
from utility.format import format_string_response
from dotenv import load_dotenv

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY must be set in your environment variables.")

if not os.getenv("USER_AGENT"):
    os.environ["USER_AGENT"] = "GenAICareerConsultant/1.0"

router = APIRouter()

# --- Main Endpoint ---
@router.post("/analyze/") 
async def analyze(
    url: str = Form(...),
    resume_file: Optional[UploadFile] = File(None),
    portfolio_file: Optional[UploadFile] = File(None),
    use_both: str = Form(...),  # Will receive "true" or "false"
    model_choice: str = Form(...)
):
    # Validate model choice (existing code)
    allowed_models = {"llama-3.3-70b-versatile", "llama-3.2-3b-preview", "llama-3.1-8b-instant", "gemma2-9b-it", "mixtral-8x7b-32768"}
    if model_choice not in allowed_models:
        raise HTTPException(status_code=400, detail=f"Invalid model selected. Choose one of: {', '.join(allowed_models)}")
    
    # Validate at least one file is provided when use_both=False
    if not use_both:
        has_resume = resume_file and resume_file.filename
        has_portfolio = portfolio_file and portfolio_file.filename
        if not (has_resume or has_portfolio):
            raise HTTPException(status_code=400, detail="Please provide either a Resume or Portfolio file.")
    
    try:
        llm = ChatGroq(temperature=0.2, groq_api_key=groq_api_key, model_name=model_choice)
        job_desc = preprocess_job_posting(url, llm)
        
        if use_both:
            # Validate both files are present and valid
            if not (resume_file and resume_file.filename and portfolio_file and portfolio_file.filename):
                raise HTTPException(status_code=400, detail="Both resume and portfolio files are required when 'analyze both' is selected.")
            
            resume_info = extract_resume_info(resume_file)
            portfolio_file.file.seek(0)  # Reset file pointer
            combined_result = analyze_combined_for_job(resume_info["content"], portfolio_file, job_desc, llm)
            formatted_result = format_string_response(combined_result, job_desc)
            return HTMLResponse(content=f"<div>{formatted_result}</div>")
        
        else:
            if resume_file and resume_file.filename:
                resume_info = extract_resume_info(resume_file)
                result = analyze_resume_for_job(resume_info["content"], job_desc, llm)
                formatted_result = format_string_response(result, job_desc)
                return HTMLResponse(content=f"<div>{formatted_result}</div>")
            
            elif portfolio_file and portfolio_file.filename:
                result = analyze_portfolio_for_job(portfolio_file, job_desc, llm)
                formatted_result = format_string_response(result, job_desc)
                return HTMLResponse(content=f"<div>{formatted_result}</div>")
            
            else:
                # This should be unreachable due to earlier check
                raise HTTPException(status_code=400, detail="No valid file provided.")
    
    except HTTPException as he:
        raise he  # Re-raise handled exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))