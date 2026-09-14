import asyncio
import json
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.db.database import AsyncSessionLocal
from app.models.analysis import Analysis
from app.services.ai_analyzer import analyze_with_ai
from app.services.archive_service import extract_archive, safe_list_project_files
from app.services.project_analyzer import generate_project_summary
from app.services.qa_analyzer import SUPPORTED_EXTENSIONS, analyze_file
from app.services.qa_pipeline import run_project_qa_pipeline
from app.services.report_builder import (
    build_category_report_sections,
    build_file_reviews,
    generate_docx_report,
    generate_html_report,
    generate_json_report,
)
from app.core.config import settings


router = APIRouter(
    prefix="/api/upload",
    tags=["File Upload"],
)


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROJECT_JOBS: dict[str, dict] = {}


def _save_upload(upload: UploadFile, destination: Path) -> None:
    maximum = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    total = 0
    with destination.open("wb") as buffer:
        while chunk := upload.file.read(1024 * 1024):
            total += len(chunk)
            if total > maximum:
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="Uploaded file exceeds the configured size limit.")
            buffer.write(chunk)


def _update_project_job(job_id: str, **updates) -> None:
    PROJECT_JOBS.setdefault(job_id, {}).update(updates)


def _run_project_job(job_id: str, archive_path: Path, extract_dir: Path, name: str) -> None:
    try:
        _update_project_job(
            job_id,
            phase="extracting",
            progress_percent=0,
            extraction_percent=0,
            current_file="Starting archive extraction",
            analysis_step="Reading archive structure",
        )

        def on_extraction_progress(percent: int, current_file: str) -> None:
            _update_project_job(
                job_id,
                extraction_percent=percent,
                progress_percent=round(percent * 0.6),
                analysis_step="Extracting archive contents",
                current_file=current_file,
            )

        project_root = extract_archive(str(archive_path), str(extract_dir), on_extraction_progress)
        _update_project_job(
            job_id,
            phase="scanning",
            extraction_percent=100,
            progress_percent=60,
            current_file="Building project file list",
            analysis_step="Discovering project files",
        )
        scanned_files = 0

        def on_file_scan(percent: int, current_file: str) -> None:
            nonlocal scanned_files
            scanned_files += 1
            _update_project_job(
                job_id,
                files_scanned=scanned_files,
                progress_percent=60 + round(percent * 0.2),
                analysis_step="Building file inventory",
                current_file=current_file,
            )

        files = safe_list_project_files(project_root, on_file_scan)
        _update_project_job(
            job_id,
            phase="testing",
            progress_percent=80,
            files_scanned=len(files),
            analysis_step="Reviewing project structure",
            current_file="Preparing QA category checks",
        )
        result = run_project_qa_pipeline({"root": project_root, "files": files})
        _update_project_job(
            job_id,
            phase="testing",
            progress_percent=82,
            analysis_step="Running static checks file by file",
            current_file="Starting file-level QA review",
        )
        result["file_reviews"] = build_file_reviews(
            project_root,
            files,
            lambda percent, current_file: _update_project_job(
                job_id,
                progress_percent=82 + round(percent * 0.13),
                analysis_step="Running static checks file by file",
                current_file=current_file,
            ),
        )
        for category_name, category_data in result["categories"].items():
            category_data["report_sections"] = build_category_report_sections(
                category_name,
                result["file_reviews"],
            )

        report_dir = Path("reports") / "project_reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        _update_project_job(
            job_id,
            phase="reporting",
            progress_percent=96,
            analysis_step="Generating final DOCX report",
            current_file="Compiling findings and guidance",
        )
        report_path = report_dir / f"{uuid4().hex}_qa_report.docx"
        report_file = generate_docx_report(str(report_path), name, result)
        report_url = f"/reports/project_reports/{Path(report_file).name}"
        json_file = generate_json_report(str(report_path.with_suffix(".json")), result)
        html_file = generate_html_report(str(report_path.with_suffix(".html")), name, result)
        result_to_save = {
            "success": True,
            **result,
            "project_name": name,
            "report_path": report_file,
            "report_url": report_url,
            "json_report_url": f"/reports/project_reports/{Path(json_file).name}",
            "html_report_url": f"/reports/project_reports/{Path(html_file).name}",
            "files_scanned": len(files),
        }
        
        async def _save():
            async with AsyncSessionLocal() as db:
                analysis = Analysis(
                    project_name=name,
                    file_name=name,
                    analysis_type="project_qa",
                    status="completed",
                    result=json.dumps(result_to_save),
                )
                db.add(analysis)
                await db.commit()
                
        try:
            asyncio.run(_save())
        except Exception as e:
            print("Failed to save project analysis to db:", e)
            raise

        _update_project_job(
            job_id,
            status="completed",
            phase="completed",
            progress_percent=100,
            extraction_percent=100,
            analysis_step="Analysis complete",
            current_file="QA report ready",
            result=result_to_save,
        )

    except Exception as exc:
        _update_project_job(
            job_id,
            status="failed",
            phase="failed",
            current_file="Analysis failed",
            error=str(exc),
        )
    finally:
        if archive_path.exists():
            archive_path.unlink()
        if extract_dir.exists():
            shutil.rmtree(extract_dir, ignore_errors=True)


@router.post("/analyze")
async def upload_and_analyze(
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided.",
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Unsupported file type.",
                "supported_extensions": sorted(
                    SUPPORTED_EXTENSIONS
                ),
            },
        )

    safe_name = f"{uuid4().hex}_{Path(file.filename).name}"
    file_path = UPLOAD_DIR / safe_name

    try:
        _save_upload(file, file_path)

        rule_result = analyze_file(str(file_path))

        content = file_path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        ai_result = analyze_with_ai(
            file.filename,
            content,
        )

        result = {
            "rule_based_analysis": rule_result,
            "ai_analysis": ai_result,
        }

        async with AsyncSessionLocal() as db:
            analysis = Analysis(
                project_name="Uploaded Project",
                file_name=file.filename,
                analysis_type="ai_qa",
                status="completed",
                result=json.dumps(result),
            )

            db.add(analysis)
            await db.commit()
            await db.refresh(analysis)

        return {
            "success": True,
            "analysis_id": analysis.id,
            "file_name": file.filename,
            "analysis": result,
        }

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Unable to read this file as text.",
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"AI analysis failed: {str(exc)}",
        )

    finally:
        if file_path.exists():
            file_path.unlink()


@router.post("/project")
async def upload_project_zip(
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No project archive provided.")

    name = Path(file.filename).name
    lower_name = name.lower()
    if not (lower_name.endswith(".zip") or lower_name.endswith(".rar")):
        raise HTTPException(status_code=400, detail="Only ZIP or RAR project archives are allowed.")

    archive_dir = UPLOAD_DIR / "projects"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_name = f"{uuid4().hex}_{name}"
    archive_path = archive_dir / archive_name

    try:
        _save_upload(file, archive_path)

        extract_dir = archive_dir / f"{uuid4().hex}_extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)

        project_root = extract_archive(str(archive_path), str(extract_dir))
        files = safe_list_project_files(project_root)

        result = run_project_qa_pipeline({
            "root": project_root,
            "files": files,
        })
        result["file_reviews"] = build_file_reviews(project_root, files)
        for category_name, category_data in result["categories"].items():
            category_data["report_sections"] = build_category_report_sections(
                category_name,
                result["file_reviews"],
            )

        report_dir = Path("reports") / "project_reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{uuid4().hex}_qa_report.docx"
        report_file = generate_docx_report(str(report_path), name, result)
        report_url = f"/reports/project_reports/{Path(report_file).name}"
        json_file = generate_json_report(str(report_path.with_suffix(".json")), result)
        html_file = generate_html_report(str(report_path.with_suffix(".html")), name, result)

        result_to_save = {
            "success": True,
            **result,
            "project_name": name,
            "report_path": report_file,
            "report_url": report_url,
            "json_report_url": f"/reports/project_reports/{Path(json_file).name}",
            "html_report_url": f"/reports/project_reports/{Path(html_file).name}",
            "files_scanned": len(files),
        }
        
        async with AsyncSessionLocal() as db:
            analysis = Analysis(
                project_name=name,
                file_name=name,
                analysis_type="project_qa",
                status="completed",
                result=json.dumps(result_to_save),
            )
            db.add(analysis)
            await db.commit()

        return result_to_save

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Project archive analysis failed: {str(exc)}")
    finally:
        if archive_path.exists():
            archive_path.unlink()

        for cleanup in list(UPLOAD_DIR.glob("projects/*_extracted")):
            if cleanup.exists():
                shutil.rmtree(cleanup, ignore_errors=True)


@router.post("/project/start")
@router.post("", include_in_schema=False)
async def start_project_analysis(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No project archive provided.")

    name = Path(file.filename).name
    if not name.lower().endswith((".zip", ".rar")):
        raise HTTPException(status_code=400, detail="Only ZIP or RAR project archives are allowed.")

    archive_dir = UPLOAD_DIR / "projects"
    archive_dir.mkdir(parents=True, exist_ok=True)
    job_id = uuid4().hex
    archive_path = archive_dir / f"{job_id}_{name}"
    extract_dir = archive_dir / f"{job_id}_extracted"

    _save_upload(file, archive_path)
    extract_dir.mkdir(parents=True, exist_ok=True)
    PROJECT_JOBS[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "phase": "queued",
        "extraction_percent": 0,
        "progress_percent": 0,
        "files_scanned": 0,
        "current_file": "Waiting to start",
        "analysis_step": "Waiting for analysis worker",
    }
    background_tasks.add_task(_run_project_job, job_id, archive_path, extract_dir, name)
    return PROJECT_JOBS[job_id]


@router.get("/project/status/{job_id}")
async def get_project_analysis_status(job_id: str):
    job = PROJECT_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Project analysis job not found.")
    return job