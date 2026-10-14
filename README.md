# 🚀 GitHub App & AI Agent Skill Finder

An AI-powered discovery and evaluation engine that translates natural language requirements into optimized GitHub queries, concurrently fetches `README.md` and `SKILL.md` documentation, and ranks **Open-Source Applications** as well as **AI Agent Skills (`SKILL.md` / MCP Servers / Agent Tools)** with structured match scoring (`0–100`).

Supports both **Terminal CLI Mode** (`python app.py`) and **Interactive Web UI Mode** (`streamlit run app.py`), with built-in **English (`🇺🇸`)** and **Vietnamese (`🇻🇳`)** language switching.

---

## ✨ Key Features

### 1. 🤖 Built-in Free AI Models (Zero-Key & Free API Providers)
- ⚡ **Free No-API-Key Mode (Smart Hybrid AI - Default):**
  - **`hybrid-auto`**: Combines free cloud LLM inference with an automatic fallback to the built-in `SmartZeroKeyEngine` — guaranteed 100% uptime with zero API keys required.
  - **`local-smart-nlp`**: Ultra-fast (< 2s) local NLP & Markdown/`SKILL.md` structural analyzer with zero external LLM rate limits.
- 🟢 **Zhipu AI / GLM (100% Free API):** Supports `glm-4-flash`, `glm-z1-flash` (reasoning), `glm-4-flash-250414`, and `glm-4.5-flash`.
- 🌐 **OpenRouter (`:free` models):** Supports `z-ai/glm-4.5-air:free`, `thudm/glm-4-9b:free`, `deepseek/deepseek-r1:free`, `deepseek/deepseek-chat-v3-0324:free`, `qwen/qwen-2.5-72b-instruct:free`, `meta-llama/llama-3.3-70b-instruct:free`.
- 🚀 **Groq Cloud (Free Tier):** `llama-3.3-70b-versatile`, `qwen-qwq-32b`, `gemma2-9b-it`.
- 💻 **Ollama Local:** Run local models completely offline (`glm4:latest`, `qwen2.5:latest`, `llama3.2:latest`).
- ✨ **Google Gemini (AI Studio Free Tier):** `gemini-3.8-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-pro-preview`.

### 2. 🎯 Dual Discovery Modes
1. **📱 Open-Source Apps Finder (`app` mode):**
   - Extracts functional and technical criteria from natural language prompts.
   - Distinguishes complete end-user applications (`📦 Complete App`, `🌐 Web App / Self-hosted`, `🛠️ CLI Tool`) from curated lists or libraries.
   - Extracts key features, caveats, and quick installation commands directly from `README.md`.
2. **🤖 AI Agent Skills & MCP Finder (`skill` mode):**
   - Finds skills and tools compatible with **Antigravity, Claude Code, Cursor, Cline, OpenAI Codex, OpenHands, and MCP Clients**.
   - Automatically scans repository file trees via the GitHub Git Trees API and raw endpoints to discover standalone and nested `SKILL.md`, `AGENTS.md`, `CLAUDE.md`, and `.cursorrules` files.
   - Classifies results into `🧩 Standard SKILL.md`, `🗂️ Skill Pack`, `🔌 MCP Server / Tool`, or `📜 Agent Rules / Workflow`, and provides quick integration commands.

---

## 📂 Project Structure

```text
github-app-skill-finder/
├── app.py             # Dual-mode entrypoint: Terminal CLI & Streamlit Web UI
├── ai_engine.py       # Multi-provider AI engine & SmartZeroKeyEngine analyzer
├── github_client.py   # GitHub Search API client & parallel README/SKILL.md fetcher
├── models.py          # Pydantic schemas (SearchPlan, RepoCandidate, RepoEvaluation)
├── requirements.txt   # Python dependencies
└── .env.example       # Optional environment variable template
```

---

## 🛠️ Installation

```bash
git clone https://github.com/duongvantai16022007-cloud/github-app-skill-finder.git
cd github-app-skill-finder
pip install -r requirements.txt
```

*(Optional)* Copy `.env.example` to `.env` if you want to pre-configure API keys for GLM, OpenRouter, Groq, Gemini, or a GitHub Personal Access Token:

```bash
cp .env.example .env
```

---

## 💻 Usage

### Option A: Run Directly in Terminal (CLI Mode)

1. **Interactive Terminal Menu:**
   ```bash
   python app.py
   ```
2. **One-Line Command (Find Open-Source Apps):**
   ```bash
   python app.py "Find a cross-platform expense tracker app built with Flutter"
   ```
3. **One-Line Command (Find AI Agent Skills / `SKILL.md` / MCP):**
   ```bash
   python app.py --mode skill "Playwright browser automation and UI testing skill"
   ```
4. **CLI Flags:**
   ```bash
   python app.py --mode skill --provider glm_bigmodel --model glm-4-flash --stars 20 --limit 8 --output results.json "Security audit skill for Claude Code"
   ```

### Option B: Run Interactive Web UI (Streamlit Mode)

```bash
streamlit run app.py
```
