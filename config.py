import os
import re

from dotenv import load_dotenv  # type: ignore[import]

load_dotenv()  # loads .env in the project root before os.getenv() calls below

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
SESSION_JSON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs", "sessions")

# ── Whitelisted tools ──
ALLOWED_TOOLS = {"nmap", "whois", "enum", "gobuster"}

# ── Injection safety ──
DANGEROUS_CHARS = {";", "|", "&", "$", "`", "(", ")", "\n", "\r",
                   ">", "<", "'"}

# ── Private / non-routable IP RFC blocks ──
_PRIVATE_CIDRS = [
    ("127.0.0.0", 8),      # loopback
    ("10.0.0.0", 8),       # RFC1918 Class A
    ("172.16.0.0", 12),    # RFC1918 Class B
    ("192.168.0.0", 16),   # RFC1918 Class C
    ("169.254.0.0", 16),   # link-local
    ("0.0.0.0", 8),        # "this" network
]

# ── Regex patterns ──

_IPV4_RE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$"
)

_DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z]{2,63}$"
)

_LAB_ALLOWLIST_RE = re.compile(
    r"^(?:10\.|172\.1[6-9]\.|172\.2[0-9]\.|172\.3[0-1]\.|"
    r"192\.168\.|127\.)"
)


def _ipv4_to_int(ip: str) -> int:
    parts = ip.split(".")
    return (int(parts[0]) << 24) | (int(parts[1]) << 16) | (int(parts[2]) << 8) | int(parts[3])


def _is_special_ip(target: str) -> bool:
    """Return True if target is a private / loopback / link-local IP."""
    if not _IPV4_RE.match(target):
        return False
    ip_int = _ipv4_to_int(target)
    for net, bits in _PRIVATE_CIDRS:
        mask = (0xFFFFFFFF << (32 - bits)) & 0xFFFFFFFF
        if (ip_int & mask) == (_ipv4_to_int(net) & mask):
            return True
    return False


def validate_target(target: str) -> tuple[str, list[str]]:
    """
    Validate and normalise *target*.

    Returns
    -------
    (normalised_target, warnings)

    Raises
    ------
    ValueError
        If the target is empty, not an IP/domain, or a private IP that is
        not in the lab-allowlisted range (10.x / 172.16-31.x / 192.168.x / 127.x).
    """
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

    warnings: list[str] = []

    # Warn if it's a public IP (not private at all)
    if _IPV4_RE.match(target) and not _is_special_ip(target):
        warnings.append(
            f"WARNING: '{target}' is a PUBLIC IP address. "
            "Ensure you have WRITTEN AUTHORISATION before scanning."
        )

    # Reject private IPs outside the lab allowlist
    if _IPV4_RE.match(target) and _is_special_ip(target):
        if not _LAB_ALLOWLIST_RE.match(target):
            raise ValueError(
                f"Target '{target}' is a private/loopback IP outside the "
                "lab allowlist (10.x / 172.16-31.x / 192.168.x / 127.x). "
                "Use a lab-range IP or a reachable domain name."
            )
        warnings.append(f"Lab-range IP detected: {target}. Proceeding.")

    return target, warnings


def is_safe_arg(arg: str) -> bool:
    if any(c in arg for c in DANGEROUS_CHARS):
        return False
    return True
