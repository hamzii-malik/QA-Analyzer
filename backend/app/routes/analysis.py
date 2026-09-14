import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
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


async def _get_record(analysis_id: int, db: AsyncSession) -> Analysis:
    result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return analysis


@router.get("/{analysis_id}/status", summary="Get analysis status")
async def get_analysis_status(analysis_id: int, db: AsyncSession = Depends(get_db)):
    analysis = await _get_record(analysis_id, db)
    return {"analysis_id": analysis.id, "status": analysis.status, "created_at": analysis.created_at}


@router.get("/{analysis_id}/results", summary="Get complete analysis results")
async def get_analysis_results(analysis_id: int, db: AsyncSession = Depends(get_db)):
    analysis = await _get_record(analysis_id, db)
    return {"analysis_id": analysis.id, "status": analysis.status, "result": json.loads(analysis.result) if analysis.result else {}}


@router.get("/{analysis_id}/security", summary="Get security results")
async def get_security_results(analysis_id: int, db: AsyncSession = Depends(get_db)):
    analysis = await _get_record(analysis_id, db)
    result = json.loads(analysis.result) if analysis.result else {}
    return {"analysis_id": analysis.id, "security": result.get("security", {})}


@router.get("/{analysis_id}/tests", summary="Get testing results")
async def get_test_results(analysis_id: int, db: AsyncSession = Depends(get_db)):
    analysis = await _get_record(analysis_id, db)
    result = json.loads(analysis.result) if analysis.result else {}
    return {"analysis_id": analysis.id, "testing": result.get("testing", {})}


@router.get("/{analysis_id}/findings", summary="Get normalized findings")
async def get_findings(analysis_id: int, db: AsyncSession = Depends(get_db)):
    analysis = await _get_record(analysis_id, db)
    result = json.loads(analysis.result) if analysis.result else {}
    security = result.get("security", {}).get("scanners", {})
    findings = [finding for scanner in security.values() for finding in scanner.get("findings", [])]
    findings.extend(result.get("testing", {}).get("logical", {}).get("findings", []))
    findings.extend(result.get("testing", {}).get("boundary", {}).get("findings", []))
    return {"analysis_id": analysis.id, "findings": findings, "count": len(findings)}


@router.get("/{analysis_id}/report", summary="Get report metadata")
async def get_report(analysis_id: int, db: AsyncSession = Depends(get_db)):
    analysis = await _get_record(analysis_id, db)
    result = json.loads(analysis.result) if analysis.result else {}
    return {"analysis_id": analysis.id, "report_url": result.get("report_url"), "report_path": result.get("report_path")}


@router.get("/{analysis_id}/report/download", summary="Download generated report")
async def download_report(analysis_id: int, db: AsyncSession = Depends(get_db)):
    analysis = await _get_record(analysis_id, db)
    result = json.loads(analysis.result) if analysis.result else {}
    report_path = result.get("report_path")
    if not report_path or not Path(report_path).exists():
        raise HTTPException(status_code=404, detail="Report is not available.")
    return FileResponse(report_path, filename=Path(report_path).name)


@router.post("/{analysis_id}/cancel", summary="Cancel analysis")
async def cancel_analysis(analysis_id: int, db: AsyncSession = Depends(get_db)):
    analysis = await _get_record(analysis_id, db)
    if analysis.status in {"completed", "failed", "cancelled"}:
        return {"analysis_id": analysis.id, "status": analysis.status}
    analysis.status = "cancelled"
    await db.commit()
    return {"analysis_id": analysis.id, "status": "cancelled"}