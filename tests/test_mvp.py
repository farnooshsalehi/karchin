import json

import jdatetime
import zstandard as zstd

from app.docx_export import create_worklog_docx
from app.parser import parse_session_file
from app.persian import persian_month_title


def test_parse_zstd_jsonl():
    lines = [
        {"session_id": "test-session", "timestamp": "2026-10-20T10:00:00Z", "cwd": "/project", "payload": {"role": "user", "content": "پیاده‌سازی UART را انجام بده"}},
        {"payload": {"role": "assistant", "content": "UART init و driver را پیاده‌سازی کردم"}},
        "malformed line",
    ]
    raw = "\n".join(json.dumps(item, ensure_ascii=False) if isinstance(item, dict) else item for item in lines).encode()
    compressed = zstd.ZstdCompressor().compress(raw)

    session = parse_session_file("test.jsonl.zst", compressed)

    assert session["session_id"] == "test-session"
    assert session["project"] == "/project"
    assert session["malformed_count"] == 1
    assert len(session["messages"]) == 2


def test_persian_titles():
    assert persian_month_title("2026-10-01", "2026-10-15") == "گزارش فنی نیمه اول ماه مهر"
    assert persian_month_title("2026-10-16", "2026-10-31") == "گزارش فنی نیمه دوم ماه مهر"


def test_docx_creation(tmp_path):
    output = tmp_path / "report.docx"
    create_worklog_docx(str(output), "گزارش فنی نیمه اول ماه مهر", ["پیاده‌سازی UART Driver"])
    assert output.exists()
    assert output.stat().st_size > 0
