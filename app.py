from dotenv import load_dotenv
from fastapi import FastAPI
import os
from langchain_groq import ChatGroq
from routes import analyze
from fastapi.middleware.cors import CORSMiddleware


# Initialize FastAPI app
app = FastAPI(
    title="Gen AI Career Consultant",
    description="An AI Career Consultant App.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, tags=["analyze"])

@app.get("/")
async def root():
    return {"message": "Welcome to AI Career Consultant!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

