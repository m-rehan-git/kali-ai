import subprocess
import shlex
from config import is_safe_arg, REQUEST_TIMEOUT


def run_nmap(target: str, extra_args: str = "") -> str:
    if not is_safe_arg(target):
        raise ValueError(f"[nmap] Unsafe characters in target: {target!r}")

    cmd = ["nmap", "-sV", target]
    if extra_args:
        for tok in shlex.split(extra_args):
            if not is_safe_arg(tok):
                raise ValueError(f"[nmap] Unsafe argument token: {tok!r}")
            cmd.append(tok)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=REQUEST_TIMEOUT,
        )
        output = result.stdout + (result.stderr if result.stderr else "")
        return output.strip()
    except subprocess.TimeoutExpired:
        return "[ERROR] nmap timed out."
    except FileNotFoundError:
        return "[ERROR] nmap is not installed on this system."
