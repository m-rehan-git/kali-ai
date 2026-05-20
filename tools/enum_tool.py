def run_enum(target: str) -> str:
    """Lightweight analysis helper — does NOT execute unsafe shell commands."""
    if not target:
        raise ValueError("[enum] Target cannot be empty.")

    findings = []
    target_lower = target.lower()

    if "." in target_lower:
        findings.append(f"[ENUM] Domain/IP: {target}")
        findings.append("[ENUM] Suggested next steps: nmap -sV " + target + "  |  whois " + target)
    else:
        findings.append(f"[ENUM] Single-label host: {target}")
        findings.append("[ENUM] Treating as hostname — nmap scan recommended.")

    return "\n".join(findings)
