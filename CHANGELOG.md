# Changelog

All notable changes to **AI Wrapped** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-11-14

### Added
- **Editorial Website & Browser Wrapped Studio (`website/`)**: Warm Ivory, Saffron Gold (`#eab308`) & Mediterranean Cobalt (`#2563eb`) multi-page website (`index.html`, `studio.html`, `proof.html`, `rules.html`, `docs.html`) featuring a custom mascot & wordmark, live client-side Privacy Redactor & AI Cliché Counter, Archetype & Novel Length Calculator, and `BRAIN_PORTABLE.md` Generator.
- **GEO / Search Discovery & Documentation**: Added `llms.txt`, `llms-full.txt`, `robots.txt`, `sitemap.xml`, `manifest.webmanifest`, Schema.org `@graph` JSON-LD, `website/marketing/` playbooks, `docs/GETTING_STARTED.md`, `docs/EXPORT_AND_PRIVACY.md`, `.github/workflows/pages.yml`, and automated regression checks (`tests/test_website_and_docs.py`).

## [1.0.1] - 2026-11-14

### Fixed & Hardened
- **Keyword Secret Stripping**: Redacts API tokens (`sk-`, `hf_`, `gsk_`, `pplx-`, JWTs, Bearer headers, emails) *before* frequency tokenization so secret substrings can never surface inside `top_keywords` or `BRAIN_PORTABLE.md`.
- **Real-World Export Resilience**: Broadens `--auto` discovery in `~/Downloads` to inspect OpenAI/Claude UUID-named `.zip` exports and extracted export folders via ZIP central-directory detection while tolerating broken symlinks; supports broader ChatGPT sharded filenames (`conversations-*.json`), `Bard` Takeout history, non-UTC Takeout timestamp suffixes (`PST`, `EST`, `GMT+03:00`), and skips ChatGPT internal tool-call JSON payloads (`recipient != all`).
- **Deduplication & Bounded Reads**: Deduplicates overlapping ZIP + unzipped JSON archives inside the same directory, enforces true byte limits on decompressed ZIP streams against spoofed `ZipInfo.file_size` headers, and halts nested folder traversal cleanly at `MAX_CONVERSATIONS`.
- **Browser Offline (`file://`) & Timezone UX**: Adds `--tz utc|local` for displaying hourly activity in local clock time, `execCommand('copy')` clipboard fallback when opening `ai-wrapped.html` directly over `file://`, a slide progress indicator (`1 / 7`), responsive word wrapping on mobile, and `<`/`>`/`&` script-tag escaping.

## [1.0.0] - 2026-11-14

### Added
- **Universal Offline Archive Parsers**: Parses ChatGPT exports (single `conversations.json` and sharded `conversations-*.json` inside ZIPs via active `current_node` branch resolution), Claude exports (`chat_messages`), Google Gemini Takeout (`MyActivity.json` / `My Activity.html`), opt-in local coding agent JSONL sessions (`--include-agents`), and Markdown transcripts—100% locally using Python 3.10+ stdlib only.
- **Interactive Story + Bento Dashboard (`ai-wrapped.html`)**: Generates a zero-CDN, single-file Spotify-Wrapped-style HTML story & toggleable Bento dashboard featuring novel-length word comparisons, 24-hour circadian bar chart, monthly evolution graph, longest daily streak, politeness score vs. received AI cliché meter, buried unfinished project detection, AI Archetype badge, and one-click shareable summary copying.
- **Portable Memory Pack (`BRAIN_PORTABLE.md`)**: Distills recurring obsessions, explicit response-formatting preferences, unfinished multi-turn projects, and standing instructions for instant migration across ChatGPT, Claude, Gemini, Cursor, and coding agents.
- **Privacy & Security Hardening**: In-memory ZIP parsing with size limits & traversal guards, automatic redaction of API keys/tokens/emails/SSNs/cards from surfaced previews, strict HTML escaping, and `$HOME`/`/` broad-root safety checks.
