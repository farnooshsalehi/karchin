import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.ai_extractor import OpenAIExtractor
from app.docx_export import create_worklog_docx
from app.parser import filter_sessions_by_date, parse_session_file
from app.persian import persian_month_title, title_filename

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = ROOT / "exports"
EXPORT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Worklog")


class ExportRequest(BaseModel):
    title: str
    tasks: list[str]


@app.post("/api/analyze")
async def analyze(
    files: list[UploadFile] = File(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
):
    if not files:
        raise HTTPException(status_code=400, detail="حداقل یک فایل انتخاب کنید")
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="تاریخ شروع نباید بعد از تاریخ پایان باشد")

    sessions = []
    errors = []
    malformed_count = 0
    for upload in files:
        if not upload.filename.lower().endswith(".jsonl.zst"):
            errors.append(f"{upload.filename}: فرمت فایل پشتیبانی نمی‌شود")
            continue
        data = await upload.read()
        try:
            session = parse_session_file(upload.filename, data)
            sessions.append(session)
            malformed_count += session["malformed_count"]
        except Exception as exc:
            errors.append(f"{upload.filename}: {exc}")

    filtered = filter_sessions_by_date(sessions, start_date, end_date)
    try:
        tasks = OpenAIExtractor().extract(filtered)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    title = persian_month_title(start_date, end_date)
    return {
        "title": title,
        "filename": title_filename(title),
        "tasks": tasks,
        "start_date": start_date,
        "end_date": end_date,
        "uploaded_sessions": len(sessions),
        "analyzed_sessions": len(filtered),
        "conversation_count": sum(len(session["messages"]) for session in filtered),
        "malformed_records": malformed_count,
        "errors": errors,
    }


@app.post("/api/export")
def export(request: ExportRequest):
    title = request.title.strip()
    tasks = [task.strip() for task in request.tasks if task.strip()]
    if not title:
        raise HTTPException(status_code=400, detail="عنوان گزارش نمی‌تواند خالی باشد")

    output = EXPORT_DIR / title_filename(title)
    try:
        create_worklog_docx(str(output), title, tasks)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"خطا در ایجاد فایل Word: {exc}")

    return FileResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=output.name,
    )


app.mount("/", StaticFiles(directory=ROOT / "static", html=True), name="static")
