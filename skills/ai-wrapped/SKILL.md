---
name: ai-wrapped
description: >-
  100% offline ChatGPT, Claude & Gemini Wrapped story generator and Portable Brain
  migrator. Converts official chat exports (ZIP, conversations.json, Google
  Takeout MyActivity, JSONL) completely locally with zero cloud uploads into an
  interactive Spotify-Wrapped-style HTML story & Bento dashboard plus a portable
  BRAIN_PORTABLE.md memory brief for switching across AI platforms.
license: MIT
compatibility: Requires Python 3.10+ (stdlib only, zero external packages). Works completely offline.
metadata:
  author: codesphere-u
  version: "1.0.1"
  repository: https://github.com/codesphere-u/ai-wrapped
---

# AI Wrapped — Offline AI History Wrapped & Portable Brain Migrator

Turn messy **ChatGPT**, **Claude**, and **Gemini** exports into a **Spotify-Wrapped-style interactive visual story** and a **portable personal memory brief (`BRAIN_PORTABLE.md`)**—100% offline with zero data leaving the user's device.

## When to Use

- The user asks for their **AI Wrapped**, **ChatGPT Wrapped**, **Claude Wrapped**, or usage stats across AI tools
- The user wants to switch from **ChatGPT -> Claude -> Gemini -> Cursor** and migrate their context, preferences, and forgotten project ideas without starting from zero
- The user drops a ChatGPT export `.zip`, Claude `conversations.json`, Google Takeout Gemini export, or wants to preview an instant demo (`--demo`)

## Step-by-Step Workflow

### 1. Choose the Right Input Mode

- **Explicit export file or folder**: Pass the `.zip`, `conversations.json`, or folder directly.
- **Auto-detect from Downloads**: Pass `--auto` to inspect newest export `.zip` / `conversations.json` files in `~/Downloads`.
- **No export ready yet**: Run `--demo` so the user immediately sees the interactive HTML experience, and point them to [references/privacy-and-formats.md](references/privacy-and-formats.md) for 30-second export instructions.
- **Include local coding agents (only when asked)**: Add `--include-agents` to also summarize local `~/.claude/projects` and `~/.codex/sessions` logs.

### 2. Run the Offline Generator

Run via installed skill script (`~/.agents/skills/ai-wrapped/scripts/ai_wrapped.py` or `.agents/skills/ai-wrapped/scripts/ai_wrapped.py`) or `ai-wrapped` CLI:

Run against a specific export ZIP or JSON file:

```bash
python3 ~/.agents/skills/ai-wrapped/scripts/ai_wrapped.py path/to/export.zip --output-dir ai-wrapped-out
```

Auto-detect newest export in Downloads:

```bash
python3 ~/.agents/skills/ai-wrapped/scripts/ai_wrapped.py --auto --output-dir ai-wrapped-out
```

Generate an instant preview with the built-in multi-platform sample:

```bash
python3 ~/.agents/skills/ai-wrapped/scripts/ai_wrapped.py --demo --output-dir ai-wrapped-out
```

Filter to a single year, convert clock hours to local timezone, and print JSON metrics to stdout:

```bash
python3 ~/.agents/skills/ai-wrapped/scripts/ai_wrapped.py path/to/export.zip --year 2026 --tz local --json
```

> Load [references/privacy-and-formats.md](references/privacy-and-formats.md) for non-developer export instructions and exact PII/key redaction guarantees.

### 3. Deliver & Personalize the Output

1. Read `ai-wrapped-out/wrapped-summary.json` and `ai-wrapped-out/BRAIN_PORTABLE.md`.
2. Highlight the top fun metrics cleanly for the user (Archetype, novel-length word comparison, peak clock hour, 2–5 AM rabbit-holes, politeness score, received AI cliché count, and top buried unfinished projects).
3. Help the user open `ai-wrapped-out/ai-wrapped.html` in their browser (or paste `BRAIN_PORTABLE.md` into Claude Projects, ChatGPT Custom Instructions, Gemini Gems, or `MEMORY.md`).
4. Never fabricate stats, upload raw exports externally, or expose raw API keys or personal emails when summarizing results.
