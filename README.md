# AI Wrapped — 100% Offline ChatGPT, Claude & Gemini Wrapped + Portable Brain

[![CI](https://github.com/codesphere-u/ai-wrapped/actions/workflows/ci.yml/badge.svg)](https://github.com/codesphere-u/ai-wrapped/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

**Turn years of messy ChatGPT, Claude, and Gemini exports into a Spotify-Wrapped interactive visual story AND a portable personal memory file (`BRAIN_PORTABLE.md`)—without uploading a single private chat to the cloud.**

Zero API keys. Zero external libraries. Works in 2 seconds for **both non-developers and developers** directly on your laptop.

---

## Why People Love It

| Feature | What It Does | Why It Matters |
| :--- | :--- | :--- |
| **Interactive Wrapped Story + Bento View (`ai-wrapped.html`)** | Animated 7-card story deck + switchable overview with SVG charts, share button, and PDF export | Open in any browser offline—screenshot your **AI Archetype Card** for X, LinkedIn, or friends |
| **Novel-Scale Volume & Streaking** | Counts total conversations, prompts, words written (*"1.4x The Great Gatsby"*), streaks & peak day | See how much you actually wrote to AI this year |
| **2 AM Rabbit-Hole Clock** | 24-hour circadian chart + late-night session percentage | Reveals when your weirdest brainstorms happen |
| **Politeness vs. AI Cliché Mirror** | Scores your `"please"`/`"thank you"` ratio vs. `"!!!"` AND counts how many `"Great question!"` / `"delve"` clichés AI fed you | Instant viral screenshot bait with receipts |
| **Buried Ideas Resurfacer** | Surfaces forgotten multi-turn plans, trips, side projects & goals buried in old threads | Recover winning ideas you dropped months ago |
| **Portable AI Brain (`BRAIN_PORTABLE.md`)** | Extracts formatting preferences, recurring obsessions, and open projects cleanly | Switch between ChatGPT, Claude, Gemini, or Cursor in 10 seconds |
| **Screenshot-Safe Privacy Shield** | Streams ZIPs in-memory + auto-masks `sk-`/`ghp_` API keys, emails, and SSNs/cards | Zero cloud uploads and safe to share screenshots |

---

## Try the Instant Demo Right Now (No Export Needed!)

Run the built-in multi-platform sample in 1 second via `uvx`, `curl`, or after installing:

Zero-install via `uvx`:

```bash
uvx --from git+https://github.com/codesphere-u/ai-wrapped@v1 ai-wrapped --demo
```

Zero-install one-liner (Python 3.10+ stdlib only):

```bash
curl -fsSL https://raw.githubusercontent.com/codesphere-u/ai-wrapped/v1/skills/ai-wrapped/scripts/ai_wrapped.py | python3 - --demo
```

Then open `ai-wrapped-out/ai-wrapped.html` in your browser!

---

## Install & Run on Your Own Chats

### 1. Install as an AI Agent Skill ([skills.sh](https://skills.sh) / Antigravity / Claude Code / Cursor / Codex)

```bash
npx skills add codesphere-u/ai-wrapped
```

Auto-detect your newest ChatGPT / Claude / Gemini export ZIP in `~/Downloads`:

```bash
python3 ~/.agents/skills/ai-wrapped/scripts/ai_wrapped.py --auto
```

Or pass an exact export file or folder:

```bash
python3 ~/.agents/skills/ai-wrapped/scripts/ai_wrapped.py ~/Downloads/chatgpt-export.zip
```

*(If installed into a workspace rather than globally, replace `~/.agents/` with `.agents/`.)*

### 2. Install as a Claude Code Plugin

```text
/plugin install ai-wrapped --marketplace codesphere-u/ai-wrapped
```

### 3. Install Global CLI (`uv tool` or `pip`)

```bash
uv tool install git+https://github.com/codesphere-u/ai-wrapped@v1
```

```bash
pip install git+https://github.com/codesphere-u/ai-wrapped@v1
```

Once installed, run from anywhere:

```bash
ai-wrapped ~/Downloads/chatgpt-export.zip --year 2026 --tz local
```

Merge multiple exports (ChatGPT + Claude + Gemini Takeout) in one folder:

```bash
ai-wrapped ~/Documents/my-ai-exports --output-dir my-wrapped
```

---

## How to Export Your Data (30 Seconds)

- **ChatGPT**: **Settings -> Data controls -> Export data** (download ZIP; supports both `conversations.json` and sharded `conversations-000.json` exports)
- **Claude**: **Settings -> Privacy -> Export Data**
- **Google Gemini**: **takeout.google.com** -> select **My Activity -> Gemini Apps** (`.zip`, `MyActivity.json`, or `My Activity.html`)

Full format & privacy breakdown: [`skills/ai-wrapped/references/privacy-and-formats.md`](skills/ai-wrapped/references/privacy-and-formats.md)

---

## Development

```bash
uv venv --clear .venv && uv pip install --python .venv/bin/python -e ".[dev]" pip-audit
.venv/bin/ruff check .
.venv/bin/mypy
.venv/bin/pytest -v
.venv/bin/pip-audit --skip-editable
```

---

## License

MIT — see [LICENSE](LICENSE).
