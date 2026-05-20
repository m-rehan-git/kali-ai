import json
import os
import re
from config import (
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    REQUEST_TIMEOUT,
)
from agent.prompts import REASONING_PROMPT

import time

SYSTEM_PROMPT = REASONING_PROMPT

_TARGET_RE = re.compile(r"^TARGET=(.+)$", re.IGNORECASE)


def _extract_target(messages: list[dict]) -> str:
    """Return the target string from the first 'user' message or ''."""
    for m in messages:
        if m.get("role") == "user":
            content = m.get("content", "")
            m2 = _TARGET_RE.match(content.strip())
            if m2:
                return m2.group(1).strip()
            # Fall back: return the full content stripped
            return content.strip()
    return ""


def _call_openai(messages: list[dict]) -> dict:
    try:
        from openai import OpenAI  # type: ignore[import]
    except ImportError:
        raise RuntimeError("openai package not installed. Run: pip install openai")

    client = OpenAI(api_key=OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        timeout=REQUEST_TIMEOUT,
    )
    return _parse_json(resp.choices[0].message.content)


def _call_ollama(messages: list[dict]) -> dict:
    import requests  # type: ignore[import]

    url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "stream": False,
    }
    resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return _parse_json(data["message"]["content"])


def _mock_call(messages: list[dict]) -> dict:
    target = _extract_target(messages)

    last_tool = "none"
    for m in reversed(messages):
        if m.get("role") == "assistant":
            try:
                prev = json.loads(m.get("content", "{}"))
                last_tool = prev.get("tool", "none")
            except Exception:
                pass
            break

    # Check if we already completed
    if last_tool == "none":
        return {"tool": "none", "args": {},
                "reason": "All steps completed."}

    tool_sequence = {"enum": "nmap", "nmap": "whois", "whois": "none"}
    next_tool = tool_sequence.get(last_tool, "none")

    return {"tool": next_tool,
            "args": {"target": target},
            "reason": f"Next step after {last_tool}."}


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw[:-3]
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        for line in raw.split("\n"):
            try:
                parsed = json.loads(line.strip())
                break
            except json.JSONDecodeError:
                continue
        else:
            parsed = {"tool": "none", "args": {}, "reason": "JSON parsing failed."}
    return parsed


def get_next_step(messages: list[dict]) -> dict:
    if LLM_PROVIDER == "openai":
        return _call_openai(messages)
    if LLM_PROVIDER == "ollama":
        return _call_ollama(messages)
    return _mock_call(messages)
