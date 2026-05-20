"""All shared prompt templates for kali-ai-agent.

Each string uses f-string-style ``{placeholder}`` tokens so the caller can
inject dynamic context via ``.format(...)`` without touching the wording.

TOOL_CATALOG_PROMPT
-------------------
A human-readable summary of every available tool.  Pass it as a user
message at the start of a fresh session when you want the LLM to have
full context on what's available before it makes its first decision.

    from agent.prompts import TOOL_CATALOG_PROMPT
    catalog = TOOL_CATALOG_PROMPT.format(
        target="10.0.0.10",
        step_count=0,
    )
    memory.add("user", catalog)
"""

REASONING_PROMPT = (
    "You are a cybersecurity reconnaissance assistant running in an "
    "authorized lab environment only. "
    "You MUST respond with valid JSON ONLY. "
    "No markdown. No extra text. No explanations outside the JSON object.\n\n"
    'Required JSON format:\n'
    '{{"tool": "nmap | whois | enum | gobuster | none", '
    '"args": {{}}, "reason": "short explanation"}}\n\n'
    "Rules:\n"
    "- Use ONLY the tools listed; start with enum, then nmap, then gobuster, then whois.\n"
    "- If enough information has been collected, set tool=none to stop.\n"
    "- Never suggest tools outside this whitelist.\n"
    "- Keep reason under 120 characters.\n"
    "Target is always stored in memory context; do not include it in the JSON.\n"
    "Argument schemas:\n"
    '  nmap:    {{"target": "<ip-or-domain>"}}\n'
    '  whois:   {{"target": "<domain>"}}\n'
    '  enum:    {{"target": "<ip-or-domain>"}}\n'
    '  gobuster:{{"target": "<ip-or-domain>", "mode": "dir", "wordlist": "<path>"}}'
)

TOOL_CATALOG_PROMPT = """\
Available reconnaissance tools on this system:
  - enum     — lightweight host analysis (no subprocess)
  - nmap     — service-version scan: nmap -sV <target>
  - gobuster — web directory / DNS enumeration: gobuster <mode> -u <target> -w <wordlist>
  - whois    — domain registration lookup: whois <domain>

Target: {target}
Steps taken so far: {step_count}
"""
