import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.analysis import Analysis
from app.schemas.analysis import AnalysisCreate, AnalysisResponse
from app.services.qa_analyzer import analyze_content


router = APIRouter(
    prefix="/api/analysis",
    tags=["QA Analysis"],
)


@router.post(
    "/",
    response_model=AnalysisResponse,
)
async def create_analysis(
    data: AnalysisCreate,
    db: AsyncSession = Depends(get_db),
):
    result = analyze_content(data.content)

    analysis = Analysis(
        project_name=data.project_name,
        file_name=data.file_name,
        analysis_type="qa",
        status=result["status"],
        result=json.dumps(result),
    )

    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    return analysis


@router.get("/")
async def get_all_analyses(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Analysis).order_by(Analysis.created_at.desc())
    )

    analyses = result.scalars().all()

    return {
        "success": True,
        "count": len(analyses),
        "analyses": [
            {
                "id": analysis.id,
                "project_name": analysis.project_name,
                "file_name": analysis.file_name,
                "analysis_type": analysis.analysis_type,
                "status": analysis.status,
                "result": json.loads(analysis.result)
                if analysis.result
                else None,
                "created_at": analysis.created_at,
            }
            for analysis in analyses
        ],
    }


@router.get("/{analysis_id}")
async def get_analysis(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id)
    )

    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found.",
        )

    return {
        "success": True,
        "analysis": {
            "id": analysis.id,
            "project_name": analysis.project_name,
            "file_name": analysis.file_name,
            "analysis_type": analysis.analysis_type,
            "status": analysis.status,
            "result": json.loads(analysis.result)
            if analysis.result
            else None,
            "created_at": analysis.created_at,
        },
    }