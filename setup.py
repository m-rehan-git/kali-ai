#!/usr/bin/env python3
"""setup.py — One-time first-run configuration wizard for kali-ai-agent.

Prompts for provider + credentials, validates the key, writes a .env file.
Run once after cloning::

    python setup.py

Re-run at any time to change providers or keys::

    python setup.py --reset

.env.example documents every variable.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ENV_PATH = Path(__file__).parent / ".env"

_PROVIDERS = {
    "1": ("openai",    "OpenAI — GPT-4o-mini or any OpenAI-compatible API"),
    "2": ("openrouter","OpenRouter — 100+ models via one API key (free tier available)"),
    "3": ("ollama",    "Ollama — local LLM server (no API key needed)"),
    "4": ("mock",      "Mock — deterministic offline mode, no network calls"),
}
_OPENAI_DEFAULT_MODEL = "gpt-4o-mini"
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_OPENROUTER_DEFAULT_MODEL = "meta-llama/llama-3.1-8b-instruct:free"
_OLLAMA_DEFAULT_URL = "http://localhost:11434"
_OLLAMA_DEFAULT_MODEL = "llama3.2:3b"


def _prompt_provider() -> str:
    print("\n=== kali-ai-agent setup wizard ===\n")
    print("Choose your LLM provider:\n")
    for key, (name, desc) in _PROVIDERS.items():
        print(f"  [{key}] {name:12s}  — {desc}")
    print()
    while True:
        choice = input("Enter 1, 2, 3, or 4: ").strip()
        if choice in _PROVIDERS:
            return _PROVIDERS[choice][0]
        print("  Invalid choice — enter 1, 2, or 3.")


def _validate_openrouter_key(key: str, model: str) -> bool:
    """Return True if the key can reach OpenRouter with the chosen model.

    Sends a 1-token test completion so we catch auth errors + model-not-found
    before writing the key to .env.
    """
    import requests  # type: ignore[import]

    try:
        resp = requests.post(
            f"{_OPENROUTER_BASE_URL.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/m-rehan-git/kali-ai",
                "X-Title": "kali-ai-agent",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "OK"}],
                "max_tokens": 1,
            },
            timeout=15,
        )
        resp.raise_for_status()
        print(f"[OK] Key accepted. Model '{model}' is reachable.")
        return True
    except Exception as exc:
        status = getattr(exc, "response", None)
        detail = ""
        if status is not None and hasattr(status, "text"):
            try:
                detail = f" — {status.json().get('error', {}).get('message', status.text[:120])}"
            except Exception:
                detail = f" — {status.text[:120]}"
        print(f"[WARN] Key validation failed: {exc}{detail}")
        return False


def _validate_openai_key(key: str, model: str) -> bool:
    """Return True if the key can list/retrieve the given model."""
    try:
        from openai import OpenAI  # type: ignore[import]
        client = OpenAI(api_key=key)
        client.models.retrieve(model)
        return True
    except Exception as exc:
        print(f"[WARN] Key validation failed: {exc}")
        return False


def _validate_ollama(url: str, model: str) -> bool:
    """Ping the Ollama API and check whether the model is already pulled."""
    import requests  # type: ignore[import]

    try:
        resp = requests.get(f"{url.rstrip('/')}/api/tags", timeout=5)
        resp.raise_for_status()
        tags = resp.json()
        names = {m["name"] for m in tags.get("models", [])}
        if model not in names:
            print(
                f"[WARN] Model '{model}' not found on the Ollama server.\n"
                f"       Run: ollama pull {model}"
            )
            return False
        print(f"[OK] Ollama server reachable, model '{model}' is installed.")
        return True
    except Exception as exc:
        print(f"[WARN] Could not reach Ollama at {url}: {exc}")
        return False


def _collect_env(provider: str) -> dict[str, str]:
    env: dict[str, str] = {"LLM_PROVIDER": provider}

    if provider == "openai":
        print("\n── OpenAI ──────────────────────────────────────────")
        key = input("Enter your OpenAI API key (sk-...): ").strip()
        if not key:
            print("[FATAL] API key cannot be empty.")
            sys.exit(1)
        model = (
            input(f"Model [{_OPENAI_DEFAULT_MODEL}]: ").strip()
            or _OPENAI_DEFAULT_MODEL
        )
        env["OPENAI_API_KEY"] = key
        env["OPENAI_MODEL"] = model

        print("\n  Validating key …")
        ok = _validate_openai_key(key, model)
        if not ok:
            retry = input("  Key looks invalid. Write anyway? [y/N]: ").strip().lower()
            if retry != "y":
                print("  Aborted.")
                sys.exit(1)

    elif provider == "openrouter":
        print("\n── OpenRouter ───────────────────────────────────────")
        key = input("Enter your OpenRouter API key (sk-or-...): ").strip()
        if not key:
            print("[FATAL] API key cannot be empty.")
            sys.exit(1)
        model = (
            input(f"Model [{_OPENROUTER_DEFAULT_MODEL}]: ").strip()
            or _OPENROUTER_DEFAULT_MODEL
        )
        env["OPENROUTER_API_KEY"] = key
        env["OPENROUTER_MODEL"] = model

        print("\n  Validating key …")
        ok = _validate_openrouter_key(key, model)
        if not ok:
            retry = input("  Key looks invalid. Write anyway? [y/N]: ").strip().lower()
            if retry != "y":
                print("  Aborted.")
                sys.exit(1)

    elif provider == "ollama":
        print("\n── Ollama ──────────────────────────────────────────")
        url = (
            input(f"Ollama base URL [{_OLLAMA_DEFAULT_URL}]: ").strip()
            or _OLLAMA_DEFAULT_URL
        )
        model = (
            input(f"Model [{_OLLAMA_DEFAULT_MODEL}]: ").strip()
            or _OLLAMA_DEFAULT_MODEL
        )
        env["OLLAMA_BASE_URL"] = url
        env["OLLAMA_MODEL"] = model

        print("\n  Checking Ollama server …")
        _validate_ollama(url, model)

    else:
        print("\n  Mock provider selected — no API key required.")

    return env


def _write_env(env: dict[str, str]) -> None:
    lines = "\n".join(f'{k}="{v}"' for k, v in env.items()) + "\n"
    ENV_PATH.write_text(lines, encoding="utf-8")
    print(f"\n[OK] Config written to {ENV_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="setup",
        description="One-time setup wizard for kali-ai-agent.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        default=False,
        help="Re-run the wizard and overwrite the existing .env file.",
    )
    args = parser.parse_args()

    if ENV_PATH.exists() and not args.reset:
        print(f"[INFO] {ENV_PATH} already exists.")
        resp = input("  Overwrite? [y/N]: ").strip().lower()
        if resp != "y":
            print("  Aborted.")
            return

    provider = _prompt_provider()
    env = _collect_env(provider)
    _write_env(env)

    print("\n  Next steps:")
    if provider in ("openai", "openrouter"):
        print(f"    export LLM_PROVIDER={provider}   # or leave .env in place")
        print("    python main.py")
    elif provider == "ollama":
        print("    export LLM_PROVIDER=ollama   # or leave .env in place")
        print("    python main.py")
    else:
        print("    python main.py")
    print()


if __name__ == "__main__":
    main()
