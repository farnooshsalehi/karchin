import io
import json
from datetime import datetime, timezone
from typing import Any

import zstandard as zstd


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (ValueError, OverflowError, OSError):
            return None
    if isinstance(value, str):
        text = value.strip()
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
    return None


def decompress_zst(data: bytes) -> bytes:
    try:
        decompressor = zstd.ZstdDecompressor()
        try:
            return decompressor.decompress(data)
        except zstd.ZstdError:
            with decompressor.stream_reader(io.BytesIO(data)) as reader:
                return reader.read()
    except Exception as exc:
        raise ValueError("فایل Zstandard معتبر نیست یا خراب است") from exc


def parse_session_file(filename: str, data: bytes) -> dict:
    raw = decompress_zst(data)
    records = []
    malformed = 0
    for line_number, raw_line in enumerate(raw.decode("utf-8", errors="replace").splitlines(), 1):
        if not raw_line.strip():
            continue
        try:
            records.append(json.loads(raw_line))
        except json.JSONDecodeError:
            malformed += 1

    session_id = None
    timestamp = None
    project = None
    messages = []

    for record in records:
        if not isinstance(record, dict):
            continue
        session_id = session_id or record.get("session_id") or record.get("sessionId")
        if timestamp is None:
            for key in ("timestamp", "ts", "created_at", "time"):
                timestamp = _parse_timestamp(record.get(key))
                if timestamp:
                    break

        for key in ("cwd", "working_directory", "project_path", "project"):
            value = record.get(key)
            if isinstance(value, str) and value:
                project = project or value

        payload = record.get("payload")
        if isinstance(payload, dict):
            project = project or payload.get("cwd") or payload.get("working_directory")
            for key in ("timestamp", "ts", "created_at", "time"):
                if timestamp is None:
                    timestamp = _parse_timestamp(payload.get(key))

            message = payload.get("message")
            if isinstance(message, dict):
                role = message.get("role")
                content = message.get("content")
            else:
                role = payload.get("role")
                content = payload.get("content")

            if role in ("user", "assistant"):
                text_parts = []
                if isinstance(content, str):
                    text_parts.append(content)
                elif isinstance(content, list):
                    for item in content:
                        if isinstance(item, str):
                            text_parts.append(item)
                        elif isinstance(item, dict):
                            if isinstance(item.get("text"), str):
                                text_parts.append(item["text"])
                            elif isinstance(item.get("output"), str):
                                text_parts.append(item["output"])
                text = "\n".join(part.strip() for part in text_parts if part and part.strip())
                if text:
                    messages.append({"role": role, "text": text[:12000]})

            # Preserve relevant tool execution and command evidence only.
            if payload.get("type") in ("tool_call", "tool_result", "command_execution") or "tool" in payload:
                tool = payload.get("tool") or payload.get("name") or payload.get("type")
                output = payload.get("output") or payload.get("result") or payload.get("command")
                if isinstance(output, str) and output.strip():
                    messages.append({"role": "tool", "text": f"Tool: {tool}\n{output[:12000]}"})

    return {
        "filename": filename,
        "session_id": session_id,
        "timestamp": timestamp.isoformat() if timestamp else None,
        "project": project,
        "messages": messages,
        "record_count": len(records),
        "malformed_count": malformed,
    }


def filter_sessions_by_date(sessions: list[dict], start_date: str, end_date: str) -> list[dict]:
    start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
    filtered = []
    for session in sessions:
        if not session.get("timestamp"):
            continue
        timestamp = datetime.fromisoformat(session["timestamp"])
        if start <= timestamp <= end:
            filtered.append(session)
    return filtered
