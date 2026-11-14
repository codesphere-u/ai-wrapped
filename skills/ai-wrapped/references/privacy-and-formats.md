# Export Formats & Offline Privacy Guarantees

**AI Wrapped runs 100% locally in Python (`stdlib` only).** It never makes network calls, never uploads your conversations to any server, never writes extracted ZIP files to disk, and automatically redacts detected API keys, Bearer tokens, email addresses, credit card patterns, and SSNs from any quoted snippets or titles inside outputs.

---

## How to Export Your Data (30 Seconds, No Coding Needed)

### ChatGPT (OpenAI)
1. Sign in at ChatGPT and open **Settings**.
2. Click **Data controls** -> **Export data** -> **Confirm export**.
3. Open the email from OpenAI and download the `.zip` file (usually saved to `Downloads`).
4. Run:
   ```bash
   ai-wrapped ~/Downloads/chatgpt-export.zip
   ```
   *(Supports both classic single `conversations.json` exports and newer sharded `conversations-000.json`, `conversations-001.json`, ... ZIP archives.)*

### Claude (Anthropic)
1. Open Claude and go to **Settings** -> **Privacy** -> **Export Data**.
2. Download the `.zip` archive sent to your email.
3. Run:
   ```bash
   ai-wrapped ~/Downloads/claude-export.zip
   ```

### Google Gemini (Google Takeout)
1. Visit **takeout.google.com**, click **Deselect all**.
2. Check **My Activity** -> click **All activity data included** -> select only **Gemini Apps**.
3. Download the `.zip` (JSON or HTML format both supported).
4. Run:
   ```bash
   ai-wrapped ~/Downloads/takeout-gemini.zip
   ```

### Combine All of Them Together
Drop all your exported `.zip` or `.json` files into a folder (for example `~/Documents/my-ai-exports`) and point `ai-wrapped` at that folder:

```bash
ai-wrapped ~/Documents/my-ai-exports
```

It merges ChatGPT + Claude + Gemini seamlessly into one unified **Wrapped Story** and **`BRAIN_PORTABLE.md`**.

---

## Built-In Safety Guardrails

- **In-memory ZIP streaming**: Archives are read inside `zipfile.ZipFile` with path-traversal rejection (`..`) and strict per-entry size limits (`200 MB`), avoiding messy temp folders.
- **Broad-root protection**: Refuses scanning `~` (`$HOME`) or `/` unless `--allow-home` is explicitly passed.
- **Screenshot-safe redaction**: Patterns matching OpenAI/Anthropic/GitHub/Google/AWS/Slack keys (`sk-...`, `ghp_...`, `AIza...`, `AKIA...`, `xox...`), emails, and card/SSN sequences are masked before rendering HTML/Markdown/JSON.
- **XSS-safe HTML**: Every user-derived string inside `ai-wrapped.html` is HTML-escaped cleanly (`html.escape(..., quote=True)`).
