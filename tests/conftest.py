"""tests/conftest.py — Shared pytest fixtures and path configuration.

Import path
-----------
Running ``pytest tests/`` from the repo root (which has ``pythonpath = ["."]``
set in pyproject.toml) is the standard entry point; the fixtures below work
without invariants.
"""

import sys
from pathlib import Path

# Guarantee the project root is importable so flat modules like
# `config`, `agent.llm`, `router.tool_router` etc. resolve correctly.
# (pyproject.toml also sets [tool.pytest.ini_options] pythonpath = ["."],
# but this guard protects tests run standalone.)
_repo_root = str(Path(__file__).resolve().parents[1])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

import json

import config as _cfg   # noqa: E402  — imported after sys.path fix above

import pytest
from config import LOG_FILE, SESSION_JSON_DIR  # noqa  (kept for backwards compat)


@pytest.fixture(autouse=True)
def isolated_logs(tmp_path, monkeypatch):
    """Redirect log files to a temp directory for every test.

    Uses ``monkeypatch.setattr`` — not ``setenv`` — because ``LOG_FILE``
    and ``SESSION_JSON_DIR`` are module-level constants resolved once at
    import time; patching the env var after import has zero effect.
    """
    fake_log = str(tmp_path / "session.log")
    fake_dir = str(tmp_path / "sessions")
    monkeypatch.setattr(_cfg, "LOG_FILE", fake_log)
    monkeypatch.setattr(_cfg, "SESSION_JSON_DIR", fake_dir)


@pytest.fixture()
def lab_target():
    """A deterministic lab-range IP used by smoke-tests."""
    return "10.0.0.42"


@pytest.fixture()
def public_domain():
    """A public domain that is safe to touch in tests."""
    return "example.com"
