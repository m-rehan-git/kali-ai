import json
import logging
import time

from config import MAX_LOOP_STEPS, REQUEST_TIMEOUT, LOG_FILE, LLM_RETRIES, LLM_RETRY_BACKOFF_SEC
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


def _safe_parse(raw: str, fallback: dict) -> dict:
    """Return the JSON object parsed from *raw* or *fallback on failure."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw[:-3]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        for line in raw.split("\n"):
            line = line.strip()
            if line.startswith("{"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        return fallback


def _llm_with_retry(messages: list[dict]) -> dict:
    """Call the LLM up to LLM_RETRIES times with exponential back-off."""
    last_exc: Exception | None = None
    for attempt in range(1, LLM_RETRIES + 1):
        try:
            return get_next_step(messages)
        except Exception as exc:
            last_exc = exc
            if attempt < LLM_RETRIES:
                wait = LLM_RETRY_BACKOFF_SEC * (2 ** (attempt - 1))
                log.warning("LLM attempt %d/%d failed (%s). Retrying in %.1fs ...",
                            attempt, LLM_RETRIES, exc, wait)
                time.sleep(wait)
    log.error("LLM failed after %d attempt(s). Last error: %s", LLM_RETRIES, last_exc)
    return {"tool": "none", "args": {},
            "reason": f"LLM unavailable after {LLM_RETRIES} attempts."}


def run(target: str):
    step = 0
    memory = Memory()
    log.info("=== New session started | Target: %s ===", target)
    memory.add("user", f"TARGET={target}")

    for step in range(1, MAX_LOOP_STEPS + 1):
        msgs = memory.as_messages()

        try:
            llm_output = _llm_with_retry(msgs)
        except Exception as exc:
            log.error("[Step %d] LLM call failed fatally: %s", step, exc)
            break

        if not isinstance(llm_output, dict):
            llm_output = {"tool": "none", "args": {}, "reason": "Invalid LLM output."}
        if not isinstance(llm_output.get("args"), dict):
            llm_output["args"] = {}

        tool = (llm_output.get("tool") or "").strip().lower()
        args = llm_output.get("args") or {}
        reason = (llm_output.get("reason") or "No reason given.").strip()

        log.info(
            "[Step %d] Tool: '%s' | Args: %s | Reason: %s",
            step, tool, json.dumps(args), reason,
        )
        print(f"\n[Step {step}] LLM → tool={tool!r} | reason={reason}")

        if tool == "none":
            print("[DONE] LLM signalled completion.")
            log.info("[Step %d] LLM signalled completion (tool=none).", step)
            break

        try:
            route_result = route(tool, args)
            exec_output = route_result["result"]
        except (PermissionError, ValueError) as exc:
            exec_output = f"[ROUTER REJECTED] {exc}"
            log.warning("[Step %d] Router rejection: %s", step, exc)
        except Exception as exc:
            exec_output = f"[ERROR] Tool execution exception: {exc}"
            log.error("[Step %d] Tool execution error: %s", step, exc)

        log.info("[Step %d] Tool output: %s", step, exec_output[:500])
        print(f"[Step {step}] Output:\n{exec_output[:600]}\n---")
        memory.add_tool_result(tool, args, exec_output)

    log.info("=== Session ended after %d step(s) ===", step)
