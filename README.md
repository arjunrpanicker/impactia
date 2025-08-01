# 🚀 Code Change Impact Analysis Backend

## Overview
This backend system analyzes code changes from Pull Requests and generates test cases using Azure OpenAI. The response is structured as JSON for easy integration.

## Features
- Analyzes code changes from Pull Requests
- Uses Azure OpenAI for impact analysis and test generation
- Smart Impact Summary for token efficiency (~85% reduction)
- Generates API and UI test cases
- Structured JSON output

## Setup

### Prerequisites
- Python 3.9+
- Azure OpenAI API access

### Installation
1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your Azure OpenAI configuration

## Usage
1. Start the server:
   ```bash
   uvicorn app.main:app --reload
   ```
2. The API will be available at `http://localhost:8000`
3. API documentation is available at `http://localhost:8000/docs`

## API Endpoints

### POST /analyze
Analyze code changes from a Pull Request.

### POST /generate-tests
Generate API and UI test cases from code changes.

**Request:**
```json
{
  "pull_request_id": "string",
  "modified_files": ["string"],
  "smart_impact_summary": "string",
  "test_generation_options": {
    "include_api_tests": true,
    "include_ui_tests": true,
    "max_test_cases": 20
  }
}
```

**Response:**
```json
{
  "test_generation_id": "string",
  "summary": {
    "total_tests": "number",
    "api_tests": "number",
    "ui_tests": "number"
  },
  "tests": [
    {
      "id": "string",
      "type": "API|UI",
      "title": "string",
      "description": "string",
      "priority": "string",
      "test_steps": [
        {
          "step": "number",
          "action": "string",
          "expected_result": "string"
        }
      ]
    }
  ],
  "traceability": {
    "file_to_tests": {
      "filename": ["test_ids"]
    }
  }
}
```

### GET /health
Health check endpoint.

## Smart Impact Summary
- Automatically generated from code analysis
- Reduces token usage by ~85% in test generation
- Structured format with change type, risk level, and test focus areas
- Used internally for efficient AI processing

## Project Structure
```
app/
├── main.py                     # FastAPI application
├── models/
│   ├── analysis.py            # Analysis data models
│   └── test_generation.py     # Test generation models
├── services/
│   ├── azure_openai_service.py    # Azure OpenAI integration
│   ├── smart_summary_service.py   # Smart summary generation
│   └── test_generation_service.py # Test case generation
└── utils/
    └── error_handling.py      # Error handling utilities
```

## License
This project is licensed under the MIT License. 