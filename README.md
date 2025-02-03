# Resume & Portfolio Analysis API

## Overview
This project is a FastAPI-based application that evaluates resumes and portfolios against job postings. It extracts job details from a given URL, processes resume and portfolio files, and provides a structured analysis using AI-powered matching. The project also includes a frontend built with HTML, CSS, and JavaScript for user interaction.

## Features
- **Job Posting Extraction**: Scrapes job details (role, skills, and description) from a given URL.
- **Resume Analysis**: Parses PDF/DOCX resumes and evaluates them against job requirements.
- **Portfolio Analysis**: Reads CSV files containing technologies and compares them with job skills.
- **AI-Powered Suitability Check**: Uses LLM (Groq-powered Gemma2-9B-IT) to determine match percentage.
- **Actionable Insights**: Generates interview questions or suggests improvements based on skill gaps.
- **CORS Enabled**: Supports cross-origin requests for frontend integration.
- **Frontend UI**: Provides a user-friendly interface built with HTML, CSS, and JavaScript.

## Tech Stack
- **FastAPI** (Backend Framework)
- **LangChain** (LLM Integration)
- **Groq** (AI Model Provider)
- **PyPDF2 & python-docx** (Resume Parsing)
- **Pandas** (Portfolio Processing)
- **WebBaseLoader** (Job Posting Scraping)
- **HTML, CSS, JavaScript** (Frontend Development)
- **HTMLResponse** (Frontend Rendering)

## Installation
### Prerequisites
Ensure you have Python 3.8+ installed.

### Clone the Repository
```sh
git clone https://github.com/your-username/resume-portfolio-analyzer.git
cd resume-portfolio-analyzer
```

### Install Dependencies
```sh
pip install -r requirements.txt
```

### Set Up Environment Variables
Create a `.env` file and add the following:
```env
GROQ_API_KEY=your_groq_api_key
USER_AGENT=GenAICareerConsultant/1.0
```

## Running the API
```sh
uvicorn main:app --reload
```

## API Endpoints
### 1. **Analyze Resume/Portfolio**
```http
POST /analyze/
```
**Parameters:**
- `url` (string, required) – Job posting URL.
- `resume_file` (file, optional) – PDF/DOCX resume.
- `portfolio_file` (file, optional) – CSV portfolio file.
- `use_both` (boolean, optional) – Analyze both resume and portfolio.

**Response:**
Returns an HTML fragment with the suitability analysis.

## Usage Example
### Request:
```sh
curl -X 'POST' \
  'http://127.0.0.1:8000/analyze/' \
  -F 'url=https://example.com/job-posting' \
  -F 'resume_file=@path/to/resume.pdf' \
  -F 'use_both=false'
```

### Response (HTML Rendered):
- Suitability Check
- Interview Questions (if suitable)
- Improvement Suggestions (if not suitable)

## Contribution
Feel free to fork and submit PRs.


