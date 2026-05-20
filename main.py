from config import validate_target
from core.loop import run


WELCOME = r"""
╔══════════════════════════════════════════════════╗
║          kali-ai-agent  v1.0                    ║
║  Authorized Lab Reconnaissance Only             ║
║  Ensure you have WRITTEN PERMISSION before use. ║
╚══════════════════════════════════════════════════╝
"""


def main():
    print(WELCOME)
    target = input("Enter target IP or domain (lab only): ").strip()
    try:
        target = validate_target(target)
    except ValueError as exc:
        print(f"[FATAL] {exc}")
        return

    print(f"\n[INFO] Target set to: {target}")
    print("[INFO] Starting agent loop ...\n")

    try:
        run(target)
    except KeyboardInterrupt:
        print("\n[INFO] Session interrupted by user.")
    except Exception as exc:
        print(f"\n[FATAL] Unexpected error: {exc}")


if __name__ == "__main__":
    main()
