#Gen-AI-Career-Consultant

## Overview
This FastAPI application analyzes resumes, job postings, and portfolios to assess candidate suitability for job roles using Groq's AI models.

## Features
- **Resume & Portfolio Parsing**: Extracts text from PDF, DOCX, and CSV files.
- **Job Posting Scraper**: Fetches job details from URLs.
- **Candidate Analysis**: Compares resumes and portfolios against job requirements, calculates skill match percentage, and provides interview questions or improvement suggestions.
- **AI-Powered Processing**: Uses Groq's LLM to extract structured insights.
- **CORS & FastAPI Integration**: Allows frontend interaction with unrestricted API access.

## Installation

### Prerequisites
- Python 3.8+
- pip
- FastAPI

### Setup
```bash
# Clone the repository
git clone Gen-AI-Career-Consultant
cd Gen-AI-Career-Consultant

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Running the API
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### API Endpoints
| Endpoint               | Method | Description |
|------------------------|--------|-------------|
| `/upload_resume`       | POST   | Upload and parse resume |
| `/upload_portfolio`    | POST   | Upload and parse portfolio |
| `/fetch_job_details`   | GET    | Scrape job details from a URL |
| `/analyze_candidate`   | POST   | Compare resume with job requirements |

## Configuration
- Update the `config.py` file with necessary API keys and settings.

 
## Contributing
Contributions are welcome! Please submit a pull request or open an issue.
 

