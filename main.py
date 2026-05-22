"""main.py — Entry point for kali-ai-agent.

Usage examples
--------------
Interactive mode:
    python main.py

CLI flags:
    python main.py --target 10.0.0.10 --provider ollama
    python main.py --target scanme.nmap.org --dry-run
    python main.py --target 192.168.1.50 --steps 5
"""

import argparse
import os
import sys

from pathlib import Path

from config import LOG_FILE, SESSION_JSON_DIR
from config import validate_target, LLM_PROVIDER
from agent.llm import get_next_step
from core.loop import run

_REPO_ROOT = Path(__file__).parent


WELCOME = r"""
╔══════════════════════════════════════════════════╗
║          kali-ai-agent  v2.5                    ║
║  Authorized Lab Reconnaissance Only             ║
║  Ensure you have WRITTEN PERMISSION before use. ║
╚══════════════════════════════════════════════════╝
"""


def _check_setup() -> None:
    """Print a helpful hint if neither .env nor env vars are configured."""
    env_configured = bool(
        os.getenv("LLM_PROVIDER")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("OPENROUTER_API_KEY")
        or os.getenv("OLLAMA_BASE_URL")
    )
    if not _REPO_ROOT.joinpath(".env").exists() and not env_configured:
        print("[WARN] No .env found and no env vars set.")
        print("[HINT] Run:  python setup.py")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="kali-ai-agent",
        description="LLM-driven authorized-lab reconnaissance agent.",
    )
    p.add_argument(
        "--target", "-t",
        default=None,
        help="IP address or domain to scan (interactive prompt if omitted).",
    )
    p.add_argument(
        "--provider", "-p",
        choices=["openai", "openrouter", "ollama", "mock"],
        default=None,
        help="LLM provider (overrides LLM_PROVIDER env var).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Force mock mode and skip all subprocess tool calls.",
    )
    p.add_argument(
        "--steps", "-s",
        type=int,
        default=None,
        metavar="N",
        help="Override MAX_LOOP_STEPS for this run.",
    )
    return p.parse_args()


def main() -> None:
    print(WELCOME)

    _check_setup()

    args = _parse_args()

    # ── Collect target ───────────────────────────────────────────────
    if args.target:
        raw_target = args.target.strip()
    else:
        raw_target = input("Enter target IP or domain (lab only): ").strip()

    try:
        target, warnings = validate_target(raw_target)
    except ValueError as exc:
        print(f"[FATAL] {exc}")
        sys.exit(1)

    for w in warnings:
        print(f"[WARN] {w}")

    # ── Apply CLI overrides ──────────────────────────────────────────
    import config as _cfg

    if args.provider:
        _cfg.LLM_PROVIDER = args.provider
        print(f"[INFO] LLM provider set to: {args.provider}")
    else:
        print(f"[INFO] LLM provider: {_cfg.LLM_PROVIDER}")

    if args.steps is not None:
        _cfg.MAX_LOOP_STEPS = max(1, args.steps)
        print(f"[INFO] Max steps set to: {_cfg.MAX_LOOP_STEPS}")

    if args.dry_run:
        _cfg.LLM_PROVIDER = "mock"
        print("[INFO] DRY-RUN mode — mock LLM + no subprocess calls.")

    print(f"\n[INFO] Target: {target}")
    print("[INFO] Starting agent loop …\n")

    summary = run(target, dry_run=args.dry_run)
    print(f"\n[SUMMARY] {summary}")


if __name__ == "__main__":
    main()
