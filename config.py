import os
import re

# ── LLM Provider ──
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

# ── Agent behaviour ──
MAX_MEMORY_ENTRIES = 15
MAX_LOOP_STEPS = 20
REQUEST_TIMEOUT = 120
LLM_RETRIES = 3
LLM_RETRY_BACKOFF_SEC = 2

# ── Logging ──
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs", "session.log")

# ── Whitelisted tools ──
ALLOWED_TOOLS = {"nmap", "whois", "enum"}

# ── Injection safety ──
DANGEROUS_CHARS = {";", "|", "&", "$", "`", "(", ")", "\n", "\r"}

_IPV4_RE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$"
)

_DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z]{2,63}$"
)


def validate_target(target: str) -> str:
    target = target.strip()

    if not target:
        raise ValueError("Target cannot be empty.")

    # Strip common protocol prefixes
    for prefix in ("https://", "http://", "ftp://"):
        if target.startswith(prefix):
            target = target[len(prefix):]
            break

    # Strip path, query, fragment
    if "/" in target:
        target = target.split("/")[0]
    if "?" in target:
        target = target.split("?")[0]

    if not (_IPV4_RE.match(target) or _DOMAIN_RE.match(target)):
        raise ValueError(
            f"Target '{target}' is not a valid IPv4 address or domain name."
        )

    return target


def is_safe_arg(arg: str) -> bool:
    if any(c in arg for c in DANGEROUS_CHARS):
        return False
    return True
