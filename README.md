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
MAX_UPLOAD_SIZE_MB=100
MAX_EXTRACTED_SIZE_MB=500
MAX_EXTRACTED_FILES=10000
ANALYSIS_TIMEOUT=1800
FUZZ_CASES=25
FUZZ_MAX_STRING_LENGTH=500
ZAP_ENABLED=False
ZAP_PATH=
ZAP_HOST=127.0.0.1
ZAP_PORT=8090
FRONTEND_URL=http://127.0.0.1:5173
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
- Project upload: `POST /api/upload/project/start`
- Detailed health: `GET /api/health`
- Analysis status/results/security/tests/findings/report: `GET /api/analysis/{id}/...`

## Notes

- Uploaded code is analyzed as text only; it is never executed.
- Runtime readiness is detected using allowlisted command suggestions; uploaded application commands are not executed automatically.
- OWASP ZAP is disabled by default and accepts only localhost/loopback targets.
- The frontend must call the backend at `http://127.0.0.1:8000`.
