# Getting Started with AI Wrapped

`ai-wrapped` turns raw ChatGPT, Claude, and Google Gemini chat exports into two portable artifacts on your own disk—with zero external libraries (`Python 3.10+` stdlib only) and zero network traffic:
1. **`ai-wrapped.html`** — interactive 7-card Spotify-Wrapped-style Story + Bento Dashboard.
2. **`BRAIN_PORTABLE.md`** — concise memory pack capturing formatting rules, recurring projects, and AI cliché guardrails.

---

## Try the Instant Demo

Run without downloading any export file:

```bash
uvx --from git+https://github.com/codesphere-u/ai-wrapped ai-wrapped --demo
```

Or run the installed CLI directly:

```bash
ai-wrapped --demo --output-dir ai-wrapped-out
```

Open `ai-wrapped-out/ai-wrapped.html` directly over `file://` in any browser.

---

## Install Options

### 1. Agent Skill (Antigravity / Claude Code / Cursor / Codex)
```bash
npx skills add codesphere-u/ai-wrapped
```

### 2. Global CLI (`uv tool` or `pip`)
```bash
uv tool install git+https://github.com/codesphere-u/ai-wrapped
```

```bash
pip install git+https://github.com/codesphere-u/ai-wrapped
```

---

## CLI Reference

| Flag | Default | Purpose |
| :--- | :--- | :--- |
| `target` | — | Path to `.zip`, `conversations.json`, `.jsonl`, or folder containing exports |
| `--demo` | `false` | Build a preview from the bundled 20-conversation multi-platform sample |
| `--auto` | `false` | Auto-discover the newest export archive or UUID folder in `~/Downloads` |
| `--include-agents` | `false` | Merge local `~/.claude/projects` and `~/.codex/sessions` JSONL transcripts |
| `--year YEAR` | All years | Filter metrics to a specific calendar year (e.g. `2026`) |
| `--tz {utc,local}` | `utc` | Render 24-hour clock charts and peak hours in UTC or local machine timezone |
| `--output-dir DIR` | `./ai-wrapped-out` | Destination folder for `ai-wrapped.html`, `BRAIN_PORTABLE.md`, and JSON |
| `--json` | `false` | Emit structured analytics JSON directly to stdout |
| `--allow-home` | `false` | Override the broad-root safeguard when intentionally targeting `$HOME` or `/` |
