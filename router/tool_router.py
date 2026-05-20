import json
from config import ALLOWED_TOOLS, is_safe_arg

import tools.nmap_tool as nmap_tool
import tools.whois_tool as whois_tool
import tools.enum_tool as enum_tool


_TOOL_MAP = {
    "nmap": nmap_tool.run_nmap,
    "whois": whois_tool.run_whois,
    "enum": enum_tool.run_enum,
}


def route(tool_name: str, args: dict) -> dict:
    tool_name = (tool_name or "").strip().lower()

    if tool_name == "none":
        return {"tool": "none", "result": "No tool requested — stopping loop."}

    if tool_name not in ALLOWED_TOOLS:
        raise PermissionError(
            f"Tool '{tool_name}' is not whitelisted. "
            f"Allowed: {sorted(ALLOWED_TOOLS)}"
        )

    for key, val in args.items():
        if not is_safe_arg(str(val)):
            raise ValueError(f"Unsafe argument in key='{key}': {val!r}")

    func = _TOOL_MAP[tool_name]
    try:
        result = func(**args)
    except Exception as exc:
        result = f"[ERROR] {tool_name} execution failed: {exc}"

    return {"tool": tool_name, "result": result}
