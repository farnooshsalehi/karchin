import json
import os
from typing import Iterable

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


SYSTEM_PROMPT = """You extract completed technical work from Codex conversation sessions.

Return a JSON object with this exact shape:
{"tasks": ["Persian technical bullet text", ...]}

Rules:
- Use Persian, concise, direct, professional technical language.
- Preserve English technical terms exactly where appropriate.
- Include only activities supported by clear evidence in the conversations.
- Include completed implementation, investigation, testing, debugging, and successfully performed work.
- Distinguish independent tasks; never merge unrelated components or activities.
- Merge repeated or duplicate discussions about the same performed activity.
- Never report plans, suggestions, future work, abandoned attempts, or intended features as completed.
- Never invent results, files, commands, test outcomes, or achievements.
- Output bullet text only; no headings, summaries, tables, percentages, or explanations.
- If no evidence exists, return {"tasks": []}.
"""


class OpenAIExtractor:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def extract(self, sessions: Iterable[dict]) -> list[str]:
        if not self.api_key:
            raise RuntimeError("کلید OpenAI تنظیم نشده است؛ OPENAI_API_KEY را در فایل .env وارد کنید")

        prepared = []
        for session in sessions:
            messages = session.get("messages", [])
            if messages:
                prepared.append({
                    "session_id": session.get("session_id"),
                    "timestamp": session.get("timestamp"),
                    "project": session.get("project"),
                    "conversation": messages,
                })

        if not prepared:
            return []

        client = OpenAI(api_key=self.api_key)
        response = client.responses.create(
            model=self.model,
            instructions=SYSTEM_PROMPT,
            input=json.dumps({"sessions": prepared}, ensure_ascii=False),
            text={"format": {"type": "json_object"}},
        )

        output = response.output_text
        try:
            data = json.loads(output)
        except json.JSONDecodeError as exc:
            raise RuntimeError("پاسخ مدل قابل پردازش نبود؛ لطفاً دوباره تلاش کنید") from exc

        tasks = data.get("tasks")
        if not isinstance(tasks, list):
            raise RuntimeError("ساختار خروجی مدل معتبر نیست")

        clean = []
        seen = set()
        for task in tasks:
            if not isinstance(task, str):
                continue
            task = task.strip()
            if task and task not in seen:
                seen.add(task)
                clean.append(task)
        return clean
