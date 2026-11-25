import base64
import json
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.ai_extractor import OpenAIExtractor
from app.docx_export import create_worklog_docx
from app.parser import filter_sessions_by_date, parse_session_file
from app.persian import (
    gregorian_to_persian,
    persian_month_title,
    persian_to_gregorian,
    title_filename,
)

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = ROOT / "exports"
EXPORT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Worklog")


@app.get("/api/persian-today")
def persian_today():
    from datetime import date

    today = date.today().isoformat()
    return {"gregorian": today, "persian": gregorian_to_persian(today)}


@app.post("/api/persian-to-gregorian")
def convert_persian_date(data: dict[str, str]):
    try:
        return {"gregorian": persian_to_gregorian(data["value"])}
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="تاریخ شمسی معتبر نیست") from exc


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


@app.post("/api/select-files")
def select_files():
    initial_directory = Path(os.environ.get(
        "CODEX_SESSIONS_DIR",
        str(Path.home() / ".codex" / "sessions" / "2026"),
    ))
    if not initial_directory.is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"پوشه جلسات Codex پیدا نشد: {initial_directory}",
        )

    folder = str(initial_directory).replace("'", "''")
    script = f'''Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.InitialDirectory = '{folder}'
$dialog.RestoreDirectory = $true
$dialog.Filter = 'فایل‌های Codex (*.jsonl.zst)|*.jsonl.zst'
$dialog.Multiselect = $true
$dialog.Title = 'انتخاب فایل‌های جلسه Codex'
$dialog.CheckFileExists = $true
$dialog.CheckPathExists = $true
if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {{ return }}
$dialog.FileNames | ForEach-Object {{
    $file = Get-Item $_
    [PSCustomObject]@{{
        name = $file.Name
        size = $file.Length
        data = [Convert]::ToBase64String([IO.File]::ReadAllBytes($file.FullName))
    }}
}} | ConvertTo-Json -Depth 3 -Compress'''

    encoded_script = base64.b64encode(script.encode("utf-16-le")).decode("ascii")

    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-STA", "-WindowStyle", "Normal", "-EncodedCommand", encoded_script],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail="باز کردن پنجره انتخاب فایل با خطا مواجه شد")

        output = result.stdout.strip()
        if not output:
            return {"files": []}

        parsed = json.loads(output)
        if isinstance(parsed, dict):
            parsed = [parsed]
        return {"files": parsed}
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="انتخاب فایل زمان‌سنجی شد") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="نتیجه انتخاب فایل قابل پردازش نبود") from exc


app.mount("/", StaticFiles(directory=ROOT / "static", html=True), name="static")
