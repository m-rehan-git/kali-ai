# kali-ai-agent

A production-ready, locally-runnable LLM-driven cybersecurity reconnaissance agent designed exclusively for **authorized lab use on Kali Linux**.

---

## ⚠️ Legal & Ethical Warning

> **Use this tool ONLY against systems you own or have WRITTEN PERMISSION to test.**
> Unauthorised scanning — even of a single port — is illegal in most
> jurisdictions and may result in criminal prosecution.
> The author accepts **no responsibility** for misuse.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Safety Rules](#safety-rules)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Running the Agent](#running-the-agent)
7. [Example Execution Flow](#example-execution-flow)
8. [Project Structure](#project-structure)

---

## Project Overview

`kali-ai-agent` is a **controlled penetration-testing orchestration agent**.
It does **not** autonomously attack systems. Instead, it:

1. Accepts a user-supplied target IP or domain string.
2. Passes the target to an LLM agent block.
3. The LLM decides — based on accumulated tool output — which **one** whitelisted
   recon tool to execute next.
4. The chosen tool is executed through a **strict router** layer.
5. Output is summarised and fed back to the LLM as context.
6. The loop continues until the LLM returns `tool: "none"`.

### Supported LLM Providers

| Provider | Env Var | Notes |
|---|---|---|
| **Mock** | `LLM_PROVIDER=mock` *(default)* | Deterministic dummy loop — works offline. |
| **Ollama** | `LLM_PROVIDER=ollama` | Uses a local Ollama server (`http://localhost:11434`). |
| **OpenAI** | `LLM_PROVIDER=openai` | Requires `OPENAI_API_KEY` env var. |

---

## Architecture

```
User Input (Target IP / Domain)
        │
        ▼
┌──────────────────────────┐
│     LLM Agent            │  ← Decides next action
│  (agent/llm.py)          │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│   Strict Tool Router     │  ← Whitelist gate (router/tool_router.py)
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Kali Tool Wrappers      │  ← subprocess | No shell=True
│  (tools/*_tool.py)       │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│   Parsed Output          │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│   Memory Buffer          │  ← last 15 interactions (agent/memory.py)
└──────────┬───────────────┘
           │
           └────────►  Loop back to LLM Agent
```

---

## Safety Rules

| Rule | Enforcement Location |
|---|---|
| **Lab-only input** | `config.py` — `validate_target()` |
| **Whitelisted tools only** | `router/tool_router.py` |
| **No shell injection** | Every tool wrapper uses `subprocess` with a list; `shlex.split`; argument character check |
| **LLM never runs commands** | LLM only returns JSON decision; `first/second` never runs raw strings |
| **All execution via router** | `core/loop.py` calls `route()` exclusively |
| **Full audit log** | `logs/session.log` — timestamp + tool + args + output |
| **Graceful shutdown** | `tool=none` from LLM, Ctrl+C handler in `main.py` |

---

## Installation

### Prerequisites

- **Kali Linux** (rolling or 2024.x)
- Python 3.10+
- Git

### Steps

```bash
# 1. Clone
git clone https://github.com/<your-username>/kali-ai-agent.git
cd kali-ai-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Run with Ollama instead of mock LLM
# Install Ollama: https://ollama.com
ollama pull llama3.2:3b
export LLM_PROVIDER=ollama
```

**Required Kali tools:**

```bash
sudo apt update && sudo apt install -y nmap whois python3-pip
pip3 install -r requirements.txt
```

---

## Configuration

All configuration lives in `config.py`. No sensitive keys are hardcoded.

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `mock` | `openai`, `ollama`, or `mock` |
| `OPENAI_API_KEY` | `""` | Required when using OpenAI |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `OLLAMA_MODEL` | `llama3.2:3b` | Ollama model tag |
| `MAX_MEMORY_ENTRIES` | `15` | Context window size |
| `MAX_LOOP_STEPS` | `20` | Hard cap on loop iterations |
| `ALLOWED_TOOLS` | `{nmap, whois, enum}` | Router whitelist |

---

## Running the Agent

### Mock mode (no LLM server required)

```bash
export LLM_PROVIDER=mock
python3 main.py
```

### OpenAI mode

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY="sk-..."
python3 main.py
```

### Ollama mode

```bash
export LLM_PROVIDER=ollama
python3 main.py
```

---

## Example Execution Flow

```
╔══════════════════════════════════════════════════╗
║          kali-ai-agent  v1.0                    ║
║  Authorized Lab Reconnaissance Only             ║
╚══════════════════════════════════════════════════╝

Enter target IP or domain (lab only): scanme.nmap.org

[INFO] Target set to: scanme.nmap.org
[INFO] Starting agent loop ...

[Step 1] LLM → tool='enum' | reason=Start with lightweight enum analysis.
[Step 1] Output:
[ENUM] Domain/IP: scanme.nmap.org
[ENUM] Suggested next steps: nmap -sV scanme.nmap.org  |  whois scanme.nmap.org
---
[Step 2] LLM → tool='nmap' | reason=Run nmap service version scan on the target.
[Step 2] Output:
Nmap scan report for scanme.nmap.org (45.33.32.156)
Host is up (0.014s latency).
Not shown: 995 closed tcp ports
PORT      STATE  SERVICE        VERSION
22/tcp    open   ssh            OpenSSH 6.6.1p1 Ubuntu 2ubuntu2.13
25/tcp    closed smtp
80/tcp    open   http           Apache httpd 2.4.7
---
[Step 3] LLM → tool='whois' | reason=Gather WHOIS registration data.
[Step 3] Output:
Domain Name: NMAP.ORG
Registry Domain ID: D218300003-LROR
Registrar WHOIS Server: whois.gandi.net
...
---
[DONE] LLM signalled completion.

=== Session ended after 3 step(s) ===
```

---

## Project Structure

```
kali-ai-agent/
│
├── main.py               # Entry point
├── config.py             # Env vars, whitelist, validation
├── requirements.txt      # Python dependencies
├── logger.py             # Shared logging helper
│
├── agent/
│   ├── llm.py            # LLM provider abstraction
│   ├── memory.py         # Context window (last 15 steps)
│   └── prompts.py        # Prompt templates
│
├── tools/
│   ├── nmap_tool.py      # subprocess wrapper — nmap -sV <target>
│   ├── whois_tool.py     # subprocess wrapper — whois <domain>
│   └── enum_tool.py      # Lightweight analysis placeholder
│
├── router/
│   └── tool_router.py    # Whitelist enforcement + dispatch
│
├── core/
│   └── loop.py           # Main reasoning loop
│
└── logs/
    └── session.log       # Append-only audit trail
```

---

## Security Notes

- **No raw shell execution.** Every command is built as a Python list and
  passed to `subprocess.run(..., shell=False)`.
- **Whitelist is enforced in code**, not configuration. New tools cannot
  be added by setting an environment variable.
- **All tool arguments are checked against a dangerous-character set** before
  execution.
- The LLM **never** receives write or exec permissions; it only returns
  structured JSON decisions that the router validates.
- The memory buffer is bounded (15 steps) to prevent context-window attacks.
