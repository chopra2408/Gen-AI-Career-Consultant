# analyze.py
from fastapi import APIRouter, Form, UploadFile, HTTPException, File
from fastapi.responses import HTMLResponse
# from app import ChatGroq # Assuming app.py defines ChatGroq
from langchain_groq import ChatGroq # Make sure ChatGroq is imported
from typing import Optional
from prompts.posting import preprocess_job_posting
from prompts.combined import analyze_combined_for_job
from prompts.resume import analyze_resume_for_job
from prompts.portfolio import analyze_portfolio_for_job
from utility.parse import extract_resume_info
from utility.format import format_string_response
from dotenv import load_dotenv
import os # Import os

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY must be set in your environment variables.")

# Set a default User-Agent if not present, required by some web loaders
if not os.getenv("USER_AGENT"):
    os.environ["USER_AGENT"] = "GenAICareerConsultant/1.0 (compatible; http://example.com/bot)"


router = APIRouter()

# --- Main Endpoint ---
@router.post("/analyze/")
async def analyze(
    url: str = Form(...),
    resume_file: Optional[UploadFile] = File(None),
    portfolio_file: Optional[UploadFile] = File(None),
    use_both: str = Form(...),  # Expecting "true" or "false" as string
    model_choice: str = Form(...)
):
    # Validate model choice
    allowed_models = {"llama-3.3-70b-versatile", "llama-3.2-3b-preview", "llama-3.1-8b-instant", "gemma2-9b-it", "qwen-2.5-32b"} # Update with current Groq models if needed
    if model_choice not in allowed_models:
        raise HTTPException(status_code=400, detail=f"Invalid model selected. Choose one of: {', '.join(allowed_models)}")

    # Convert use_both to lowercase boolean for easier checking
    analyze_both = use_both.lower() == "true"

    # --- Input Validation ---
    has_resume = resume_file and resume_file.filename
    has_portfolio = portfolio_file and portfolio_file.filename

    if analyze_both:
        if not (has_resume and has_portfolio):
            raise HTTPException(status_code=400, detail="Both resume and portfolio files are required when 'Analyze Both' is selected.")
    else: # Not analyzing both, so at least one must be present
        if not (has_resume or has_portfolio):
            raise HTTPException(status_code=400, detail="When not analyzing both, please provide either a Resume or Portfolio file.")
        # Optional: Check if *both* are provided when analyze_both is false, which might be confusing
        # if has_resume and has_portfolio:
        #     raise HTTPException(status_code=400, detail="Please select 'Analyze Both' if you want to submit both files, otherwise submit only one.")


    try:
        llm = ChatGroq(temperature=0.1, groq_api_key=groq_api_key, model_name=model_choice) # Slightly lower temp for consistency
        job_desc = preprocess_job_posting(url, llm)

        result = None
        formatted_result = ""

        if analyze_both:
            # --- Analyze Both ---
            print("Analyzing both Resume and Portfolio...")
            # Ensure files are readable again if needed (FastAPI might consume them)
            await resume_file.seek(0)
            await portfolio_file.seek(0)
            resume_info = extract_resume_info(resume_file) # Parses PDF/DOCX
            # Pass the portfolio_file directly to the analysis function
            result = analyze_combined_for_job(resume_info["content"], portfolio_file, job_desc, llm)

        else:
            # --- Analyze Single File ---
            if has_resume:
                print("Analyzing Resume only...")
                await resume_file.seek(0)
                resume_info = extract_resume_info(resume_file)
                result = analyze_resume_for_job(resume_info["content"], job_desc, llm)
            elif has_portfolio:
                print("Analyzing Portfolio only...")
                await portfolio_file.seek(0)
                result = analyze_portfolio_for_job(portfolio_file, job_desc, llm)
            else:
                # This case should be caught by validation, but as a safeguard:
                 raise HTTPException(status_code=400, detail="No valid file provided for single analysis.")

        # --- Format and Return ---
        if result:
            formatted_result = format_string_response(result, job_desc)
            return HTMLResponse(content=f"<div>{formatted_result}</div>")
        else:
             # Should not happen if logic is correct, but handle it
             raise HTTPException(status_code=500, detail="Analysis could not be completed.")

    except HTTPException as he:
        # Re-raise specific HTTP exceptions (like parsing errors, validation errors)
        raise he
    except Exception as e:
        # Catch broader errors (LLM issues, unexpected problems)
        print(f"An unexpected error occurred: {e}") # Log the error server-side
        import traceback
        traceback.print_exc() # Print detailed traceback for debugging
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")
    finally:
        # Ensure files are closed if they were opened
        if resume_file:
            await resume_file.close()
        if portfolio_file:
            await portfolio_file.close()
