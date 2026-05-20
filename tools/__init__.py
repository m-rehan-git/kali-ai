# tools package — re-export tool map for router convenience

from tools.nmap_tool import run_nmap         # noqa: F401
from tools.whois_tool import run_whois        # noqa: F401
from tools.enum_tool import run_enum          # noqa: F401
from tools.gobuster_tool import run_gobuster  # noqa: F401

__all__ = ["run_nmap", "run_whois", "run_enum", "run_gobuster"]

TOOL_MAP = {
    "nmap": run_nmap,
    "whois": run_whois,
    "enum": run_enum,
    "gobuster": run_gobuster,
}
