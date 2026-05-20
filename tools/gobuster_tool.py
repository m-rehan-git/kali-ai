"""gobuster_tool.py — subprocess wrapper around gobuster.

Safe execution rules
--------------------
*   Uses subprocess with a *list* of arguments (no shell=True).
*   Every token is validated with is_safe_arg() before joining the command.
*   Wordlist path is passed as a single list element.

Supported modes: dir, dns, vhost, s3
"""

import subprocess
import shlex
from config import is_safe_arg, REQUEST_TIMEOUT


def run_gobuster(
    target: str,
    mode: str = "dir",
    wordlist: str = "",
    extra_args: str = "",
) -> str:
    if not is_safe_arg(target):
        raise ValueError(f"[gobuster] Unsafe characters in target: {target!r}")
    if mode not in ("dir", "dns", "vhost", "s3"):
        raise ValueError(
            f"[gobuster] Unknown mode {mode!r}. Allowed: dir, dns, vhost, s3"
        )
    if mode in ("dir", "vhost"):
        if not wordlist:
            return ("[gobuster] A wordlist is required for dir/vhost mode. "
                    "Provide it via the 'wordlist' argument.")
        if not is_safe_arg(wordlist):
            raise ValueError(f"[gobuster] Unsafe wordlist path: {wordlist!r}")

    cmd = ["gobuster", mode, "-u", target]
    if wordlist:
        cmd += ["-w", wordlist]

    if extra_args:
        for tok in shlex.split(extra_args):
            if not is_safe_arg(tok):
                raise ValueError(f"[gobuster] Unsafe token: {tok!r}")
            cmd.append(tok)

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=REQUEST_TIMEOUT,
        )
        out = completed.stdout + (completed.stderr or "")
        return out.strip() or "[gobuster] No results found."
    except subprocess.TimeoutExpired:
        return "[gobuster] Timed out."
    except FileNotFoundError:
        return ("[gobuster] gobuster binary not found on this system. "
                "Install with: go install github.com/OJ/gobuster/v3@latest")
