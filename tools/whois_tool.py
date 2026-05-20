import subprocess
import shlex
from config import is_safe_arg, REQUEST_TIMEOUT


def run_whois(target: str) -> str:
    if not is_safe_arg(target):
        raise ValueError(f"[whois] Unsafe characters in target: {target!r}")

    try:
        result = subprocess.run(
            ["whois", target],
            capture_output=True,
            text=True,
            timeout=REQUEST_TIMEOUT,
        )
        output = result.stdout + (result.stderr if result.stderr else "")
        return output.strip()
    except subprocess.TimeoutExpired:
        return "[ERROR] whois timed out."
    except FileNotFoundError:
        return "[ERROR] whois is not installed on this system."
