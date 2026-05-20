"""tests/test_config.py — Unit tests for config.py security helpers."""

import pytest

from kali_ai_agent.config import (
    is_safe_arg,
    _IPV4_RE,
    _DOMAIN_RE,
    _is_special_ip,
    validate_target,
)


# ── is_safe_arg ─────────────────────────────────────────────────────

@pytest.mark.parametrize("val,expected", [
    ("normal_arg",     True),
    ("10.0.0.1",        True),
    ("scanme.nmap.org", True),
    ("target-host",     True),
    ("",               True),   # empty is safe (caller checks emptiness)
    # Not used in tools list
])
def test_is_safe_arg_clean(val, expected):
    assert is_safe_arg(val) == expected


@pytest.mark.parametrize("val", [
    "cmd1; cmd2",
    "cat | grep",
    "rm -rf / &",
    "ls `whoami`",
    "nc$(whoami)",
    "echo\nwhoami",
    "ping\r\nhost",
])
def test_is_safe_arg_rejects_injection(val):
    assert is_safe_arg(val) is False


# ── IPv4 regex ─────────────────────────────────────────────────────

@pytest.mark.parametrize("ip", [
    "127.0.0.1",
    "10.0.0.1",
    "192.168.1.1",
    "0.0.0.0",
    "8.8.8.8",
    "255.255.255.255",
])
def test_ipv4_re_valid(ip):
    assert _IPV4_RE.match(ip), f"{ip!r} should be a valid IPv4"


@pytest.mark.parametrize("ip", [
    "256.0.0.1",
    "1.2.3",
    "1.2.3.4.5",
    "abc.def.ghi.jkl",
    "",
])
def test_ipv4_re_invalid(ip):
    assert not _IPV4_RE.match(ip), f"{ip!r} should NOT be a valid IPv4"


# ── Domain regex ───────────────────────────────────────────────────

@pytest.mark.parametrize("domain", [
    "scanme.nmap.org",
    "example.com",
    "sub.domain.co.uk",
])
def test_domain_re_valid(domain):
    assert _DOMAIN_RE.match(domain), f"{domain!r} should be a valid domain"


# ── _is_special_ip ─────────────────────────────────────────────────

@pytest.mark.parametrize("ip,expected", [
    ("127.0.0.1",    True),
    ("10.0.0.1",     True),
    ("172.16.0.1",   True),
    ("192.168.1.1",  True),
    ("169.254.1.1",  True),
    ("0.0.0.0",      True),
    ("8.8.8.8",      False),
    ("1.1.1.1",      False),
    ("208.67.222.222", False),
])
def test_is_special_ip(ip, expected):
    assert _is_special_ip(ip) == expected


# ── validate_target integration ─────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("10.0.0.1",              "10.0.0.1"),
    ("scanme.nmap.org",        "scanme.nmap.org"),
    ("http://10.0.0.1/path",  "10.0.0.1"),
    ("https://evil.com/../../", "evil.com"),
])
def test_validate_target_accepts(raw, expected):
    target, _ = validate_target(raw)
    assert target == expected


def test_validate_target_rejects_empty():
    with pytest.raises(ValueError, match="empty"):
        validate_target("")


def test_validate_target_rejects_bad_format():
    with pytest.raises(ValueError, match="valid"):
        validate_target("not-a-host-!!")


def test_validate_target_rejects_public_ip_without_warn():
    target, warnings = validate_target("8.8.8.8")
    assert target == "8.8.8.8"
    assert any("PUBLIC IP" in w for w in warnings)


def test_validate_target_rejects_private_outside_allowlist():
    """42.42.42.42 looks fine syntactically — special IPs should still fail."""
    # 0.0.0.1 is a blocklisted special range but NOT in lab allowlist
    with pytest.raises(ValueError, match="private"):
        validate_target("0.0.0.1")


def test_validate_target_allows_lab_subnets():
    for ip in ("10.0.0.1", "172.16.0.1", "192.168.1.1", "127.0.0.1"):
        target, warnings = validate_target(ip)
        assert target == ip
        assert any("Lab-range" in w for w in warnings)
