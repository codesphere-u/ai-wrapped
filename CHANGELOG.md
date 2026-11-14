# Changelog

All notable changes to **AI Wrapped** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-11-14

### Added
- **Universal Offline Archive Parsers**: Parses ChatGPT exports (single `conversations.json` and sharded `conversations-*.json` inside ZIPs via active `current_node` branch resolution), Claude exports (`chat_messages`), Google Gemini Takeout (`MyActivity.json` / `My Activity.html`), opt-in local coding agent JSONL sessions (`--include-agents`), and Markdown transcripts—100% locally using Python 3.10+ stdlib only.
- **Interactive Story + Bento Dashboard (`ai-wrapped.html`)**: Generates a zero-CDN, single-file Spotify-Wrapped-style HTML story & toggleable Bento dashboard featuring novel-length word comparisons, 24-hour circadian bar chart, monthly evolution graph, longest daily streak, politeness score vs. received AI cliché meter, buried unfinished project detection, AI Archetype badge, and one-click shareable summary copying.
- **Portable Memory Pack (`BRAIN_PORTABLE.md`)**: Distills recurring obsessions, explicit response-formatting preferences, unfinished multi-turn projects, and standing instructions for instant migration across ChatGPT, Claude, Gemini, Cursor, and coding agents.
- **Privacy & Security Hardening**: In-memory ZIP parsing with size limits & traversal guards, automatic redaction of API keys/tokens/emails/SSNs/cards from surfaced previews, strict HTML escaping, and `$HOME`/`/` broad-root safety checks.
