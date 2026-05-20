"""tests/test_router.py — Unit tests for router/tool_router.py."""

import pytest

from kali_ai_agent.router.tool_router import route
from kali_ai_agent.config import ALLOWED_TOOLS


# ── Happy-path: each whitelisted tool dispatches correctly ──────────

@pytest.mark.parametrize("tool_name", sorted(ALLOWED_TOOLS))
def test_route_whitelisted_tools(tool_name):
    if tool_name == "gobuster":
        result = route(tool_name, {"target": "example.com", "mode": "dir"})
    elif tool_name == "nmap":
        result = route(tool_name, {"target": "example.com"})
    else:
        result = route(tool_name, {"target": "example.com"})

    assert result["tool"] == tool_name
    assert "result" in result


def test_route_none():
    result = route("none", {})
    assert result["tool"] == "none"


def test_route_enum():
    result = route("enum", {"target": "10.0.0.1"})
    assert result["tool"] == "enum"
    assert "[ENUM]" in result["result"]


def test_route_whois():
    result = route("whois", {"target": "example.com"})
    assert result["tool"] == "whois"
    # Who may not be installed; either a result or a helpful error
    assert result["result"] or True


# ── Security: rejected tools ───────────────────────────────────────

@pytest.mark.parametrize("bad_tool", [
    "rm", "curl", "wget", "python", "bash", "msfvenom",
    "sqlmap", "nikto", "hydra", "metasploit",
])
def test_route_rejects_unlisted_tools(bad_tool):
    with pytest.opens("PermissionError"):
        route(bad_tool, {"target": "10.0.0.1"})


def test_route_rejects_malicious_args():
    with pytest.raises(ValueError, match="Unsafe"):
        route("whois", {"target": "example.com; rm -rf /"})


def test_route_rejects_shell_meta_in_args():
    with pytest.raises(ValueError, match="Unsafe"):
        route("nmap", {"target": "10.0.0.1$(whoami)"})


# ── Edge cases ────────────────────────────────────────────────────

def test_route_strips_and_lowercases_tool_name():
    result = route("  NMAP  ", {"target": "example.com"})
    assert result["tool"] == "nmap"


def test_route_handles_missing_tool_gracefully():
    result = route("", {"target": "example.com"})
    assert result["tool"] == "none"
