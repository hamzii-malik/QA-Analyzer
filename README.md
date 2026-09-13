# P4 QA Analyzer

AI-powered QA analysis tool for uploaded source files.

## Features

- Source file upload and validation
- Rule-based QA checks
- AI-powered analysis using Gemini
- Security, bug, and quality review
- History tracking in PostgreSQL
- Result viewing from saved analysis records
- React + Vite frontend
- FastAPI backend

## Requirements

- Python 3.11+
- Node.js 18+
- PostgreSQL running locally

## Environment

Create `.env` in the project root with values like:

```env
APP_NAME=QA Analyzer
DEBUG=True
DATABASE_URL=postgresql+asyncpg://postgres:1234@localhost:5432/p4_qa_db
API_HOST=127.0.0.1
API_PORT=8000
TARGET_PROJECTS_ROOT=C:\\Users\\your-user\\Downloads
REPORTS_DIR=../reports
SCREENSHOTS_DIR=../screenshots
LOG_LEVEL=INFO
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
```

## Backend

```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

## API

- Health: `GET /health`
- Analysis list: `GET /api/analysis/`
- Analysis detail: `GET /api/analysis/{id}`
- Upload analyze: `POST /api/upload/analyze`

## Notes

- Uploaded code is analyzed as text only; it is never executed.
- The frontend must call the backend at `http://127.0.0.1:8000`.
