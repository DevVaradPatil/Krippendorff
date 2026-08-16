"""Probe which providers/models actually have usable free quota."""

import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(r"E:\Projects\Vibes\grading_agent\.env")

GEMINI = "https://generativelanguage.googleapis.com/v1beta/openai/"


def probe(label, base_url, key_env, model):
    key = os.environ.get(key_env)
    if not key:
        print(f"{label:34s} no key in {key_env}")
        return
    try:
        client = OpenAI(api_key=key, base_url=base_url, timeout=60.0, max_retries=0)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with the single word OK."}],
            max_tokens=20,
        )
        print(f"{label:34s} OK -> {response.choices[0].message.content!r}")
    except Exception as exc:
        text = str(exc)
        quota = re.search(r"quotaValue['\"]?: ['\"]?(\d+)", text)
        retry = re.search(r"retry in ([\d.]+)s", text)
        status = getattr(exc, "status_code", "")
        detail = f"quota/day={quota.group(1)}" if quota else text[:110].replace("\n", " ")
        extra = f" retry_in={retry.group(1)}s" if retry else ""
        print(f"{label:34s} {type(exc).__name__} {status} {detail}{extra}")


probe("gemini-2.5-flash-lite", GEMINI, "GEMINI_API_KEY", "gemini-2.5-flash-lite")
probe("gemini-2.0-flash", GEMINI, "GEMINI_API_KEY", "gemini-2.0-flash")
probe("gemini-2.5-flash (used up)", GEMINI, "GEMINI_API_KEY", "gemini-2.5-flash")
probe(
    "groq llama-3.3-70b",
    "https://api.groq.com/openai/v1",
    "GROQ_API_KEY",
    "llama-3.3-70b-versatile",
)
probe(
    "openrouter llama-3.3-70b:free",
    "https://openrouter.ai/api/v1",
    "OPENROUTER_API_KEY",
    "meta-llama/llama-3.3-70b-instruct:free",
)
