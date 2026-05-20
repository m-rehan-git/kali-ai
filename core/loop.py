"""core/loop.py

Main reasoning loop: LLM → Router → Tool → Memory → repeat.
Supports dry-run mode and structured JSON session logging.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from config import (
    MAX_LOOP_STEPS, REQUEST_TIMEOUT, LOG_FILE,
    LLM_RETRIES, LLM_RETRY_BACKOFF_SEC,
    SESSION_JSON_DIR,
)
from agent.llm import get_next_step
from agent.memory import Memory
from router.tool_router import route

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a"),
        logging.StreamHandler(),
    ],
)

log = logging.getLogger("kali-ai-agent")


# ── Structured JSON session logging ──────────────────────────────────

def _write_json_session(session_id: str, events: list[dict]) -> None:
    """Write the session record as pretty-printed JSON (overwrite, not append)."""
    out_dir = Path(SESSION_JSON_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"session_{session_id}.json"
    record = {
        "session_id": session_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "events": events,
    }
    with open(out_path, "w") as f:
        json.dump(record, f, indent=2)


# ── Retry helper ─────────────────────────────────────────────────────

def _llm_with_retry(messages: list[dict]) -> dict:
    last_exc: Exception | None = None
    for attempt in range(1, LLM_RETRIES + 1):
        try:
            return get_next_step(messages)
        except Exception as exc:
            last_exc = exc
            if attempt < LLM_RETRIES:
                wait = LLM_RETRY_BACKOFF_SEC * (2 ** (attempt - 1))
                log.warning(
                    "LLM attempt %d/%d failed (%s). Retrying in %.1fs …",
                    attempt, LLM_RETRIES, exc, wait,
                )
                time.sleep(wait)
    log.error("LLM failed after %d attempt(s). Last error: %s",
              LLM_RETRIES, last_exc)
    return {"tool": "none", "args": {},
            "reason": f"LLM unavailable after {LLM_RETRIES} attempts."}


# ── Main loop ────────────────────────────────────────────────────────

def run(target: str, dry_run: bool = False) -> dict:
    """Execute the agent loop for *target*.

    Parameters
    ----------
    target : str
        Validated IP address or domain name.
    dry_run : bool
        When True the LLM is forced to mock mode and no subprocess
        calls are made; each tool returns a dry-run placeholder string.

    Returns
    -------
    dict
        Session summary: target, session_id, step_count, tools_run, dry_run flag.
    """
    session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    step = 0
    memory = Memory()
    json_events: list[dict] = []
    tools_run: list[str] = []

    log.info("=== New session | target=%s | dry_run=%s ===", target, dry_run)
    memory.add("user", f"TARGET={target}")

    json_events.append({
        "ts": session_id, "step": 0,
        "role": "user", "content": f"TARGET={target}",
    })

    for step in range(1, MAX_LOOP_STEPS + 1):
        msgs = memory.as_messages()
        ts = datetime.now(timezone.utc).isoformat()

        try:
            llm_output = _llm_with_retry(msgs)
        except Exception as exc:
            log.error("[Step %d] LLM call failed fatally: %s", step, exc)
            json_events.append({
                "ts": ts, "step": step,
                "role": "system", "content": f"LLM fatal error: {exc}",
                "status": "fatal",
            })
            break

        if not isinstance(llm_output, dict):
            llm_output = {"tool": "none", "args": {}, "reason": "Invalid LLM output."}
        if not isinstance(llm_output.get("args"), dict):
            llm_output["args"] = {}

        tool = (llm_output.get("tool") or "").strip().lower()
        args = llm_output.get("args") or {}
        reason = (llm_output.get("reason") or "No reason given.").strip()

        log.info("[Step %d] tool=%s args=%s reason=%s",
                 step, tool, json.dumps(args), reason)
        print(f"\n[Step {step}] LLM → tool={tool!r} | {reason}")

        json_events.append({
            "ts": ts, "step": step,
            "role": "assistant", "content": llm_output,
        })

        if tool == "none":
            print("[DONE] LLM signalled completion.")
            json_events.append({
                "ts": ts, "step": step,
                "role": "system", "content": "stopped by LLM", "status": "done",
            })
            break

        # ── Dry-run: skip subprocess, return placeholder ──
        if dry_run:
            exec_output = (f"[DRY-RUN] Tool '{tool}' would be called "
                           f"with args={json.dumps(args)}. "
                           "Subprocess execution skipped.")
        else:
            try:
                route_result = route(tool, args)
                exec_output = route_result["result"]
            except (PermissionError, ValueError) as exc:
                exec_output = f"[ROUTER REJECTED] {exc}"
                log.warning("[Step %d] Router rejected: %s", step, exc)
            except Exception as exc:
                exec_output = f"[ERROR] {exc}"
                log.error("[Step %d] Tool error: %s", step, exc)

        log.info("[Step %d] Output: %s", step, exec_output[:500])
        print(f"[Step {step}] Output:\n{exec_output[:600]}\n---")

        if tool not in tools_run:
            tools_run.append(tool)
        memory.add_tool_result(tool, args, exec_output)
        json_events.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "step": step,
            "role": "tool", "name": tool,
            "content": exec_output[:1000],
            "dry_run": dry_run,
        })

    log.info("Session ended after %d step(s).", step)
    _write_json_session(session_id, json_events)

    return {
        "target": target,
        "session_id": session_id,
        "steps": step,
        "tools_run": tools_run,
        "dry_run": dry_run,
    }
