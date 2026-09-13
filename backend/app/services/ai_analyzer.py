import json

from google import genai

from app.core.config import settings


client = genai.Client(
    api_key=settings.GEMINI_API_KEY
)


def analyze_with_ai(
    file_name: str,
    content: str,
) -> dict:

    prompt = f"""
You are a senior QA engineer and software security reviewer.

Analyze the following source code carefully.

File name:
{file_name}

Source code:
```text
{content}
Return ONLY valid JSON.

Use exactly this structure:

{{
    "overall_score": 0,
    "summary": "",
    "bugs": [],
    "security_issues": [],
    "code_quality_issues": [],
    "test_cases": [],
    "recommendations": []
}}

Rules:

1. overall_score must be an integer from 0 to 100.
2. Identify likely logic bugs.
3. Identify security vulnerabilities.
4. Identify code quality problems.
5. Generate useful test cases.
6. Give practical recommendations.
7. Do not invent problems without evidence.
8. Keep findings specific to the provided code.
"""

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
    )

    text = response.text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

    try:
        return json.loads(text)

    except json.JSONDecodeError:
        return {
            "overall_score": 0,
            "summary": "AI returned an invalid JSON response.",
            "bugs": [],
            "security_issues": [],
            "code_quality_issues": [],
            "test_cases": [],
            "recommendations": [],
            "raw_response": response.text,
        }