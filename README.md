# kali-ai-agent

A production-ready, locally-runnable LLM-driven cybersecurity reconnaissance
agent designed exclusively for **authorized lab use on Kali Linux**.

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
4. [Installation & One-Time Setup](#installation--one-time-setup)
5. [Configuration](#configuration)
6. [Running the Agent](#running-the-agent)
7. [CLI Reference](#cli-reference)
8. [Example Execution Flow](#example-execution-flow)
9. [Project Structure](#project-structure)

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

| Provider | Description |
|---|---|
| **Mock** | Deterministic offline mode — no API key needed, always works |
| **OpenRouter** | 100+ models via one API key — free tier available |
| **Ollama** | Local LLM server — no API key, runs fully offline |
| **OpenAI** | Remote cloud LLM — requires API key |

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
| **Lab-only input** | `config.py` — `validate_target()` + private-IP blocklist |
| **Whitelisted tools only** | `router/tool_router.py` — hardcoded `ALLOWED_TOOLS` set |
| **No shell injection** | Subprocess list args + `shlex.split` + `DANGEROUS_CHARS` filter |
| **LLM never runs commands** | LLM returns JSON only; router executes everything |
| **Full audit trail** | `logs/session.log` + `logs/sessions/*.json` |
| **Graceful shutdown** | `tool=none` from LLM, Ctrl+C handler in `main.py` |

---

## Installation & One-Time Setup

### Prerequisites

- **Kali Linux** (rolling or 2024.x)
- Python 3.10+
- Git

### 1 — Clone

```bash
git clone https://github.com/<your-username>/kali-ai.git
cd kali-ai
```

### 2 — Install Dependencies
normal pip command won't work, you have to create a a virtual environment and always activate before running
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Required Kali tools:

```bash
sudo apt update && sudo apt install -y nmap whois gobuster
```

### 3 — Run the Setup Wizard

```bash
python setup.py
```

The wizard will:

1. Present a numbered provider menu (OpenAI / Ollama / Mock).
2. Prompt for credentials and model name.
3. **Validate the key** against the live API before saving.
4. Write a `.env` file to the project root.

```
=== kali-ai-agent setup wizard ===

Choose your LLM provider:

  [1] openai      — OpenAI — GPT-4o-mini or any OpenAI-compatible API
  [2] openrouter  — OpenRouter — 100+ models via one API key (free tier available)
  [3] ollama      — Ollama — local LLM server (no API key needed)
  [4] mock        — Mock — deterministic offline mode, no network calls

Enter 1, 2, 3, or 4:
```

### 4 — Re-run Setup to Change Providers

```bash
python setup.py --reset
```

This overwrites `.env` without touching any existing scan logs.

---

## Configuration

All runtime configuration lives in `config.py`. Secrets are loaded from
`.env` automatically via `python-dotenv`.

### `.env` Reference (written by `setup.py`)

```ini
# ── LLM provider ────────────────────────────────────────────────
LLM_PROVIDER=mock          # mock | openai | openrouter | ollama

# ── OpenAI ─────────────────────────────────────────────────────
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# ── OpenRouter ─────────────────────────────────────────────────
# Get a key at https://openrouter.ai/keys
# Free models: https://openrouter.ai/models?q=free
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# ── Ollama ─────────────────────────────────────────────────────
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

### Runtime Override Table

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `mock` | `openai`, `openrouter`, `ollama`, or `mock` |
| `OPENAI_API_KEY` | *(empty)* | OpenAI API key — **never committed** |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `OPENROUTER_API_KEY` | *(empty)* | OpenRouter API key — **never committed** |
| `OPENROUTER_MODEL` | `meta-llama/llama-3.1-8b-instruct:free` | OpenRouter model tag |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2:3b` | Ollama model tag |
| `MAX_MEMORY_ENTRIES` | `15` | Context window size |
| `MAX_LOOP_STEPS` | `20` | Hard cap on loop iterations |
| `ALLOWED_TOOLS` | `{nmap,whois,enum,gobuster}` | Router whitelist |

---

## Running the Agent

```bash
# ── Interactive mode (prompts for target) ──────────────────────
python main.py

# ── Non-interactive mode with a fixed target ───────────────────
python main.py --target 10.0.0.10

# ── Dry-run — no subprocess calls, mock LLM only ───────────────
python main.py --target 10.0.0.1 --dry-run

# ── Use a non-default provider at runtime ──────────────────────
python main.py --target scanme.nmap.org --provider openrouter
python main.py --target 10.0.0.10 --provider ollama

# ── Limit the loop to N steps ──────────────────────────────────
python main.py --target 10.0.0.1 --steps 5
```

---

## CLI Reference

```
usage: kali-ai-agent [-h] [--target TARGET] [--provider {openai,openrouter,ollama,mock}]
                     [--dry-run] [--steps STEPS]

LLM-driven authorized-lab reconnaissance agent.

flags:
  -t, --target TARGET          IP address or domain to scan
  -p, --provider {openai,openrouter,ollama,mock}
                                LLM provider
  --dry-run                Force mock mode; skip subprocess calls
  -s, --steps STEPS        Override MAX_LOOP_STEPS for this run
  -h, --help               Show this help message
```

---

## Example Execution Flow

```
╔══════════════════════════════════════════════════╗
║          kali-ai-agent  v2.0                    ║
║  Authorized Lab Reconnaissance Only             ║
╚══════════════════════════════════════════════════╝

[INFO] LLM provider: mock
[INFO] Target: 10.0.0.42
[INFO] Starting agent loop …

[Step 1] LLM → tool='enum' | reason='Starting reconnaissance with lightweight enum.'
[Step 1] Output:
[ENUM] Domain/IP: 10.0.0.42
[ENUM] Suggested next steps: nmap -sV 10.0.0.42  |  whois 10.0.0.42
---
[Step 2] LLM → tool='nmap' | reason='Run nmap service-version scan on the target.'
[Step 2] Output:
Nmap scan report for 10.0.0.42
Host is up (0.001s latency).
PORT   STATE SERVICE
22/tcp open  ssh
80/tcp open  http
---
[Step 3] LLM → tool='gobuster' | reason='Enumerate web directories after nmap.'
[Step 3] Output:
===============================================================
[DRY-RUN] Tool 'gobuster' would be called with args={"target": "10.0.0.42", ...}.
Subprocess execution skipped.
---
[DONE] LLM signalled completion.

[SUMMARY] {'target': '10.0.0.42', 'session_id': '20260520T...', ...}
```

---
