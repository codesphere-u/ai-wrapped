# Export Formats & Offline Privacy Architecture

Every parser and sanitizer inside `ai_wrapped.py` runs in local Python 3.10+ memory using only standard library modules (`zipfile`, `json`, `html.parser`, `re`, `hashlib`).

---

## Supported Exports

### OpenAI ChatGPT
- Download from **Settings -> Data controls -> Export data**.
- Handles both monolithic `conversations.json` and sharded `conversations-0001-of-0002.json` inside `.zip` archives.
- Resolves the active `current_node` branch cleanly so abandoned regens are never double-counted, and skips internal tool JSON (`recipient != all`).

### Anthropic Claude
- Download from **Settings -> Privacy -> Export Data**.
- Reads `chat_messages` arrays cleanly alongside `name`, `created_at`, and text blocks.

### Google Gemini (Google Takeout)
- Export **My Activity -> Gemini Apps** from `takeout.google.com`.
- Supports JSON (`MyActivity.json`), HTML (`My Activity.html`), `Bard` legacy headers, and regional timezone suffixes (`PST`, `EST`, `GMT+03:00`).

---

## Privacy & Redaction Patterns (`SECRET_REDACT_PATTERNS`)

Secrets and PII are redacted **prior to** keyword tokenization and HTML rendering so tokens never surface in `top_keywords`, story cards, or `BRAIN_PORTABLE.md`:
- OpenAI / Anthropic project keys (`sk-...`, `sk-proj-...`, `sk-ant-...`)
- GitHub, HuggingFace, Groq, and npm tokens (`ghp_`, `github_pat_`, `hf_`, `gsk_`, `npm_`)
- Perplexity (`pplx-...`), Google (`AIza...`), Slack (`xox...`), AWS (`AKIA...`)
- JWTs (`eyJ...`) and `Authorization: Bearer ...` headers
- Email addresses, US SSNs (`ddd-dd-dddd`), and 13-19 digit card sequences

## Resource Caps & Path Guards
- **ZIP Member Cap**: `200 MB` per compressed entry (streamed with verified byte counts against spoofed headers).
- **Zip-Slip Protection**: Rejects entries containing `..` traversal components.
- **Broad-Root Guard**: Exits with status `2` if pointed directly at `$HOME` or `/` unless `--allow-home` is specified.
- **XSS Hardening**: All user titles and quotes inside `ai-wrapped.html` pass through `html.escape(..., quote=True)` and script-tag escaping.
