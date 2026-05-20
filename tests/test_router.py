"""tests/test_router.py — Unit tests for router/tool_router.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from router.tool_router import route
from config import ALLOWED_TOOLS


# ── Happy-path ─────────────────────────────────────────────────────

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


# ── Security: rejected tools ───────────────────────────────────────

@pytest.mark.parametrize("bad_tool", [
    "rm", "curl", "wget", "python", "bash",
    "msfvenom", "sqlmap", "nikto", "hydra", "metasploit",
])
def test_route_rejects_unlisted_tools(bad_tool):
    with pytest.raises(PermissionError):
        route(bad_tool, {"target": "10.0.0.1"})


def test_route_rejects_malicious_args():
    with pytest.raises(ValueError, match="Unsafe"):
        route("whois", {"target": "example.com; rm -rf /"})


def test_route_rejects_shell_meta_in_args():
    with pytest.raises(ValueError, match="Unsafe"):
        route("nmap", {"target": "10.0.0.1$(whoami)"})


# ── Edge cases ────────────────────────────────────────────────────

def test_route_normalises_tool_name():
    result = route("  NMAP  ", {"target": "example.com"})
    assert result["tool"] == "nmap"


def test_route_empty_tool_returns_none():
    result = route("", {"target": "example.com"})
    assert result["tool"] == "none"
