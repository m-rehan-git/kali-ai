"""tests/test_router.py — Unit tests for router/tool_router.py."""

import pytest

from router.tool_router import route
from config import ALLOWED_TOOLS


_GOBUSTER_WORDLIST = "/usr/share/wordlists/dirb/common.txt"


def _call_route(tool_name: str, **kwargs) -> dict:
    if tool_name == "gobuster":
        kwargs.setdefault("wordlist", _GOBUSTER_WORDLIST)
    result = route(tool_name, kwargs)
    assert isinstance(result["result"], str), (
        f"Expected str, got {type(result['result']).__name__}:"
        f" {result['result'][:120]!r}"
    )
    assert len(result["result"]) > 0, "Tool returned an empty string."
    return result


# ── Happy-path: each whitelisted tool gets its own sub-test ──────────

@pytest.mark.parametrize("tool_name,extra", [
    ("enum",    {"target": "10.0.0.1"}),
    ("nmap",    {"target": "example.com"}),
    ("gobuster",{"target": "example.com", "mode": "dir",
                 "wordlist": _GOBUSTER_WORDLIST}),
    ("whois",   {"target": "example.com"}),
], ids=lambda t: t[0] if isinstance(t, str) else t[0][:3])
def test_route_whitelisted_tools(tool_name, extra):
    result = _call_route(tool_name, **extra)
    assert result["tool"] == tool_name


def test_route_none():
    result = route("none", {})
    assert result["tool"] == "none"
    assert isinstance(result["result"], str)


def test_route_enum_contains_output():
    result = _call_route("enum", target="10.0.0.1")
    assert "[ENUM]" in result["result"]


# whois may not be installed on all CI runners; skip when offline
def test_route_whois_output():
    result = _call_route("whois", target="example.com")
    # Must be a real string with meaningful length
    assert len(result["result"]) > 10


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
