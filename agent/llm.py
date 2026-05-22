"""agent/llm.py

LLM provider abstraction — OpenAI, Ollama, or mock.
All providers are forced to return strictly-formatted JSON.
SYSTEM_PROMPT is imported from agent.prompts so the wording lives in one place.
"""

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
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    OPENROUTER_BASE_URL,
)
from agent.prompts import REASONING_PROMPT

SYSTEM_PROMPT = REASONING_PROMPT


def _parse_json(raw: str) -> dict:
    """Coerce *raw* into a dict.  Best-effort — never raises."""
    for candidate in _extract_candidates(raw):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return {"tool": "none", "args": {}, "reason": "JSON parsing failed."}


def _extract_candidates(raw: str) -> list[str]:
    """Return a priority-ordered list of plausible JSON sub-strings from *raw*."""
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("\n", 1)
        raw = parts[1].lstrip() if len(parts) > 1 else ""
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")].rstrip()

    candidates: list[str] = []
    if raw.startswith("{"):
        candidates.append(raw)
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("{"):
            candidates.append(line)
    if not candidates:
        candidates.append(raw)
    return candidates


def _call_openai(messages: list[dict]) -> dict:
    from openai import OpenAI  # type: ignore[import]

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
    resp = requests.post(
        url,
        json={
            "model": OLLAMA_MODEL,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            "stream": False,
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return _parse_json(resp.json()["message"]["content"])


def _call_openrouter(messages: list[dict]) -> dict:
    """Call OpenRouter's OpenAI-compatible API.

    OpenRouter accepts the standard openai Python SDK pointed at their
    base URL, plus two extra headers (HTTP-Referer and X-Title) that
    they use for tracking and rate-limit tiering.
    """
    from openai import OpenAI  # type: ignore[import]

    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
    )
    resp = client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        timeout=REQUEST_TIMEOUT,
        extra_headers={
            "HTTP-Referer": "https://github.com/m-rehan-git/kali-ai",
            "X-Title": "kali-ai-agent",
        },
    )
    return _parse_json(resp.choices[0].message.content)


_DEFAULT_WORDLIST = "/usr/share/wordlists/dirb/common.txt"

_TARGET_RE = re.compile(r"^TARGET=(.+)$", re.IGNORECASE)


def _extract_target(messages: list[dict]) -> str:
    """Return the target from the first user seed message, or ''."""
    for m in messages:
        if m.get("role") == "user":
            content = m.get("content", "").strip()
            m2 = _TARGET_RE.match(content)
            if m2:
                return m2.group(1).strip()
            return content
    return ""


def _get_last_tool(messages: list[dict]) -> str:
    """Return the tool name from the last assistant message, or '_init'."""
    for m in reversed(messages):
        if m.get("role") == "assistant":
            try:
                prev = json.loads(m.get("content", "{}"))
                return prev.get("tool", "_init")
            except Exception:
                return "_init"
    return "_init"


def _mock_call(messages: list[dict]) -> dict:
    target = _extract_target(messages)
    last_tool = _get_last_tool(messages)

    # The LLM decision messages are role "assistant" with JSON content.
    # Memory tool-result entries are role "tool" — skip those by checking
    # content starts with '{'.
    if last_tool == "_init":
        # Very first call — start the chain
        return {"tool": "enum",
                "args": {"target": target},
                "reason": "Starting reconnaissance with lightweight enum."}

    if last_tool == "none":
        return {"tool": "none", "args": {},
                "reason": "All steps completed."}

    _sequence: dict[str, str] = {
        "enum":    "nmap",
        "nmap":    "gobuster",
        "gobuster":"whois",
        "whois":   "none",
    }
    next_tool = _sequence.get(last_tool, "none")

    args: dict = {"target": target}
    if next_tool == "gobuster":
        args["mode"] = "dir"
        args["wordlist"] = _DEFAULT_WORDLIST

    return {"tool": next_tool, "args": args,
            "reason": f"Next step after {last_tool}."}


def get_next_step(messages: list[dict]) -> dict:
    if LLM_PROVIDER == "openai":
        return _call_openai(messages)
    if LLM_PROVIDER == "openrouter":
        return _call_openrouter(messages)
    if LLM_PROVIDER == "ollama":
        return _call_ollama(messages)
    return _mock_call(messages)
