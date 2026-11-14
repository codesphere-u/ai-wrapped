#!/usr/bin/env python3
"""AI Wrapped — 100% Offline ChatGPT, Claude & Gemini Wrapped + Portable Brain Migrator.

Zero-dependency Python 3.10+ analyzer that processes exported AI chat archives
locally (zero cloud uploads), redacts sensitive tokens from surfaced previews,
renders an interactive single-file Spotify-Wrapped-style HTML story & Bento
dashboard, and distills a portable `BRAIN_PORTABLE.md` memory brief for switching
cleanly across ChatGPT, Claude, Gemini, Cursor, and coding agents.
"""

from __future__ import annotations

import argparse
import dataclasses
import html
import io
import json
import math
import os
import re
import sys
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Literal

VERSION = "1.0.0"

MAX_ZIP_MEMBER_BYTES = 200 * 1024 * 1024
MAX_TEXT_FILE_BYTES = 120 * 1024 * 1024
MAX_JSONL_BYTES = 50 * 1024 * 1024
MAX_CONVERSATIONS = 100_000

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "Library",
    "AppData",
    "Applications",
}

POLITE_RE = re.compile(
    r"\b(?:please|thank you|thanks|thx|sorry|appreciate|kindly|could you|would you mind|cheers)\b",
    re.IGNORECASE,
)
URGENT_RE = re.compile(
    r"(?:!{2,}|\b(?:asap|urgent|immediately|why isn['’]?t|broken|still failing|wrong again|fix this)\b)",
    re.IGNORECASE,
)

AI_SYCOPHANCY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Great question!", re.compile(r"\b(?:great|excellent|wonderful|fantastic|thoughtful)\s+question\b", re.I)),
    ("Certainly / Absolutely!", re.compile(r"(?:^|\n)\s*(?:certainly|absolutely|of course|sure thing)[!.,]", re.I)),
    ("I'd be happy to", re.compile(r"\bi['’]?(?:d| would)\s+(?:be\s+)?(?:happy|glad|delighted)\s+to\b", re.I)),
    ("Let's break this down", re.compile(r"\blet['’]?s\s+(?:break\s+this\s+down|dive\s+in|explore)\b", re.I)),
    ("Delve / Delving", re.compile(r"\bdelv(?:e|es|ing)\b", re.I)),
    ("Tapestry / Multifaceted", re.compile(r"\b(?:tapestry|multifaceted|testament|ever-evolving)\b", re.I)),
    ("It's important to note", re.compile(r"\bit\s+is\s+(?:important|worth)\s+(?:to\s+note|noting)\b", re.I)),
    ("Comprehensive guide/overview", re.compile(r"\bcomprehensive\s+(?:guide|overview|breakdown)\b", re.I)),
]

STYLE_PREFERENCE_SIGNALS: list[tuple[str, re.Pattern[str], str]] = [
    ("concise", re.compile(r"\b(?:be concise|keep it short|tl;?dr|briefly|concisely|no fluff|short answer)\b", re.I), "Prefers concise, low-fluff answers over long essays."),
    ("bullets", re.compile(r"\b(?:bullet points?|bullets|numbered list|checklist)\b", re.I), "Likes scannable bullet points and step checklists."),
    ("steps", re.compile(r"\b(?:step[- ]by[- ]step|walk me through|from scratch)\b", re.I), "Appreciates clear step-by-step walkthroughs."),
    ("tables", re.compile(r"\b(?:in a table|comparison table|markdown table|matrix)\b", re.I), "Uses comparison tables for decisions and tradeoffs."),
    ("plain", re.compile(r"\b(?:plain english|eli5|simple terms|like i['’]?m 5|non-technical|no jargon)\b", re.I), "Prefers plain-English explanations without heavy jargon."),
    ("examples", re.compile(r"\b(?:give me examples?|real example|concrete example|show example)\b", re.I), "Learns fastest with concrete, real-world examples."),
    ("critical", re.compile(r"\b(?:roast|critique|brutally honest|poke holes|devil['’]?s advocate|what am i missing)\b", re.I), "Values direct, unfiltered critique over flattery."),
]

DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Coding & Tech": (
        "python", "typescript", "javascript", "react", "next", "nextjs", "sql", "api", "bug", "error",
        "docker", "git", "deploy", "server", "database", "function", "script", "code", "app", "cli",
        "html", "css", "tailwind", "linux", "vercel", "supabase", "postgres", "regex", "json", "terminal",
    ),
    "Writing & Content": (
        "write", "rewrite", "email", "draft", "essay", "blog", "post", "caption", "tweet", "linkedin",
        "headline", "newsletter", "copy", "proofread", "tone", "edit", "subject", "speech", "bio", "script",
    ),
    "Career & Business": (
        "resume", "cv", "interview", "salary", "offer", "negotiate", "startup", "product", "pricing",
        "pitch", "investor", "client", "invoice", "marketing", "strategy", "roadmap", "meeting", "manager", "job",
    ),
    "Learning & Research": (
        "explain", "understand", "summarize", "summary", "paper", "study", "exam", "history", "physics",
        "math", "book", "concept", "quiz", "flashcard", "translate", "language", "meaning", "difference", "why",
    ),
    "Home, Food & Travel": (
        "recipe", "cook", "dinner", "meal", "ingredient", "bake", "trip", "itinerary", "flight", "hotel",
        "vacation", "pack", "city", "restaurant", "coffee", "garden", "apartment", "lease", "move", "cleaning",
    ),
    "Finance & Legal": (
        "budget", "tax", "deduction", "contract", "clause", "nda", "mortgage", "rent", "loan", "credit",
        "invest", "etf", "retirement", "insurance", "claim", "expense", "subscription", "bank", "savings",
    ),
    "Health & Fitness": (
        "workout", "gym", "run", "running", "protein", "calories", "sleep", "marathon", "stretch", "back",
        "posture", "habit", "meditation", "recovery", "training", "nutrition", "walk", "steps",
    ),
    "Creative & Projects": (
        "idea", "ideas", "brainstorm", "name", "naming", "story", "design", "logo", "color", "gift",
        "birthday", "wedding", "playlist", "podcast", "video", "game", "art", "character", "worldbuild",
    ),
}

UNFINISHED_ACTION_RE = re.compile(
    r"\b(?:plan|build|launch|start|create|make|learn|design|write|publish|organize|trip|moving|project|side[- ]?project|business|book|course|garden|budget)\b",
    re.IGNORECASE,
)

STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "you", "your", "have", "from", "are", "was", "were",
    "can", "could", "would", "should", "what", "when", "where", "which", "who", "whom", "how", "why",
    "about", "into", "more", "some", "any", "all", "not", "but", "out", "use", "using", "used", "make",
    "want", "need", "like", "just", "know", "help", "please", "thanks", "thank", "give", "get", "got",
    "here", "there", "then", "than", "also", "very", "really", "well", "much", "many", "such", "only",
    "each", "other", "over", "after", "before", "being", "been", "does", "did", "doing", "done", "has",
    "had", "its", "their", "them", "they", "she", "her", "him", "his", "our", "ours", "one", "two",
    "three", "new", "good", "best", "first", "way", "look", "see", "let", "lets", "tell", "say", "said",
    "may", "might", "will", "now", "today", "work", "time", "thing", "things", "something", "anything",
    "everything", "someone", "people", "still", "even", "most", "back", "take", "took", "find", "found",
    "keep", "sure", "surely", "okay", "ok", "yes", "yeah", "hey", "hello", "hi", "write", "create",
    "explain", "list", "show", "file", "code", "text", "data", "page", "line", "step", "part",
    "item", "items", "example", "examples", "question", "answer", "response", "prompt", "message",
    "conversation", "new chat", "untitled", "chat", "cannot", "cant", "dont", "wont", "isnt",
    "youre", "ive", "im", "ill", "id", "thats", "theres", "heres", "whatre", "doesnt", "didnt",
    "these", "those", "turn", "turns", "hour", "hours", "minute", "minutes", "week", "month", "year",
    "days", "every", "quick", "quickly", "check", "actually", "going", "think",
    "under", "without", "between", "through", "within", "above", "below", "during", "while", "since",
    "wait", "points", "point", "bullet", "bullets", "concise", "table", "tables", "organize", "sorted",
    "short", "shorter", "clean", "plain", "draft", "drafts", "notes", "summary", "plan", "swap",
}

SECRET_REDACT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bsk-(?:proj-|ant-|live-|test-)?[A-Za-z0-9_-]{12,}\b"), "[redacted-api-key]"),
    (re.compile(r"\b(?:ghp|gho|ghu|ghs|github_pat)_[A-Za-z0-9_]{16,}\b"), "[redacted-token]"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"), "[redacted-google-key]"),
    (re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b"), "[redacted-slack-token]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[redacted-aws-key]"),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._-]{16,}\b"), "Bearer [redacted]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[redacted-email]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[redacted-ssn]"),
    (re.compile(r"\b(?:\d[ -]*?){13,19}\b"), "[redacted-number]"),
]

NOVEL_BENCHMARKS: list[tuple[str, int]] = [
    ("The Old Man and the Sea", 27_000),
    ("The Great Gatsby", 47_000),
    ("1984", 89_000),
    ("Dune", 188_000),
    ("War and Peace", 587_000),
]


@dataclasses.dataclass
class Turn:
    role: Literal["user", "assistant"]
    text: str
    timestamp: datetime | None = None
    model: str | None = None


@dataclasses.dataclass
class Conversation:
    conv_id: str
    platform: str
    title: str
    created_at: datetime | None
    updated_at: datetime | None
    model: str | None
    turns: list[Turn]


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4"}:
            self._parts.append("\n")

    def get_text(self) -> str:
        joined = "".join(self._parts)
        return re.sub(r"\n{3,}", "\n\n", joined).strip()


def strip_html_tags(raw_html: str) -> str:
    parser = _HTMLTextExtractor()
    try:
        parser.feed(raw_html)
        parser.close()
    except Exception:
        return re.sub(r"<[^>]+>", " ", raw_html).strip()
    return parser.get_text()


def sanitize_preview(text: str, max_len: int = 120) -> str:
    cleaned = " ".join(text.split())
    for pat, repl in SECRET_REDACT_PATTERNS:
        cleaned = pat.sub(repl, cleaned)
    if len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 1].rstrip() + "…"
    return cleaned


def parse_timestamp(val: Any) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        if val <= 0:
            return None
        # Handle millisecond epochs cleanly
        epoch = val / 1000.0 if val > 1e12 else float(val)
        try:
            return datetime.fromtimestamp(epoch, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return None
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        # Google Takeout plain English timestamps fallback
        for fmt in (
            None,
            "%b %d, %Y, %I:%M:%S %p %Z",
            "%b %d, %Y, %I:%M:%S %p",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.fromisoformat(s) if fmt is None else datetime.strptime(s.replace("\u202f", " "), fmt)
                return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def _extract_chatgpt_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    chunks: list[str] = []
    if isinstance(parts, list):
        for p in parts:
            if isinstance(p, str) and p.strip():
                chunks.append(p.strip())
            elif isinstance(p, dict):
                txt = p.get("text")
                if isinstance(txt, str) and txt.strip():
                    chunks.append(txt.strip())
    elif isinstance(content.get("text"), str):
        chunks.append(str(content["text"]).strip())
    return "\n".join(chunks).strip()


def _parse_chatgpt_list(data: list[Any], source_label: str = "ChatGPT") -> list[Conversation]:
    convs: list[Conversation] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict) or not isinstance(item.get("mapping"), dict):
            continue
        mapping: dict[str, Any] = item["mapping"]
        current_node = item.get("current_node")

        ordered_nodes: list[dict[str, Any]] = []
        if isinstance(current_node, str) and current_node in mapping:
            seen: set[str] = set()
            cursor: str | None = current_node
            chain: list[dict[str, Any]] = []
            while cursor and cursor not in seen and cursor in mapping:
                seen.add(cursor)
                node = mapping[cursor]
                if isinstance(node, dict):
                    chain.append(node)
                    parent = node.get("parent")
                    cursor = parent if isinstance(parent, str) else None
                else:
                    break
            ordered_nodes = list(reversed(chain))
        else:
            candidates = [n for n in mapping.values() if isinstance(n, dict)]
            ordered_nodes = sorted(
                candidates,
                key=lambda n: float((n.get("message") or {}).get("create_time") or 0.0)
                if isinstance(n.get("message"), dict)
                else 0.0,
            )

        turns: list[Turn] = []
        detected_model: str | None = (
            str(item["default_model_slug"]) if isinstance(item.get("default_model_slug"), str) else None
        )
        for node in ordered_nodes:
            msg = node.get("message")
            if not isinstance(msg, dict):
                continue
            author = msg.get("author")
            role_raw = author.get("role") if isinstance(author, dict) else None
            if role_raw not in {"user", "assistant"}:
                continue
            text = _extract_chatgpt_text(msg.get("content"))
            if not text:
                continue
            meta = msg.get("metadata")
            msg_model: str | None = None
            if isinstance(meta, dict) and isinstance(meta.get("model_slug"), str):
                msg_model = meta["model_slug"]
                if detected_model is None:
                    detected_model = msg_model
            ts = parse_timestamp(msg.get("create_time"))
            role: Literal["user", "assistant"] = "user" if role_raw == "user" else "assistant"
            turns.append(Turn(role=role, text=text, timestamp=ts, model=msg_model))

        if not turns:
            continue
        title = str(item.get("title") or "Untitled Chat").strip() or "Untitled Chat"
        conv_id = str(item.get("id") or item.get("conversation_id") or f"cgpt-{idx}")
        created = parse_timestamp(item.get("create_time")) or next((t.timestamp for t in turns if t.timestamp), None)
        updated = parse_timestamp(item.get("update_time")) or next(
            (t.timestamp for t in reversed(turns) if t.timestamp), created
        )
        convs.append(
            Conversation(
                conv_id=conv_id,
                platform=source_label,
                title=title,
                created_at=created,
                updated_at=updated,
                model=detected_model,
                turns=turns,
            )
        )
    return convs


def _extract_claude_text(msg: dict[str, Any]) -> str:
    content = msg.get("content")
    if isinstance(content, list):
        chunks: list[str] = []
        for blk in content:
            if isinstance(blk, dict) and blk.get("type") == "text" and isinstance(blk.get("text"), str):
                if blk["text"].strip():
                    chunks.append(blk["text"].strip())
            elif isinstance(blk, str) and blk.strip():
                chunks.append(blk.strip())
        if chunks:
            return "\n".join(chunks)
    if isinstance(msg.get("text"), str):
        return str(msg["text"]).strip()
    if isinstance(content, str):
        return content.strip()
    return ""


def _parse_claude_list(data: list[Any]) -> list[Conversation]:
    convs: list[Conversation] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict) or not isinstance(item.get("chat_messages"), list):
            continue
        turns: list[Turn] = []
        detected_model = str(item["model"]) if isinstance(item.get("model"), str) else None
        for msg in item["chat_messages"]:
            if not isinstance(msg, dict):
                continue
            sender = str(msg.get("sender") or msg.get("role") or "").lower()
            if sender not in {"human", "user", "assistant"}:
                continue
            text = _extract_claude_text(msg)
            if not text:
                continue
            role: Literal["user", "assistant"] = "user" if sender in {"human", "user"} else "assistant"
            ts = parse_timestamp(msg.get("created_at") or msg.get("updated_at"))
            msg_model = str(msg["model"]) if isinstance(msg.get("model"), str) else None
            if detected_model is None and msg_model:
                detected_model = msg_model
            turns.append(Turn(role=role, text=text, timestamp=ts, model=msg_model))

        if not turns:
            continue
        title = str(item.get("name") or item.get("title") or "Untitled Chat").strip() or "Untitled Chat"
        conv_id = str(item.get("uuid") or item.get("id") or f"claude-{idx}")
        created = parse_timestamp(item.get("created_at")) or next((t.timestamp for t in turns if t.timestamp), None)
        updated = parse_timestamp(item.get("updated_at")) or next(
            (t.timestamp for t in reversed(turns) if t.timestamp), created
        )
        convs.append(
            Conversation(
                conv_id=conv_id,
                platform="Claude",
                title=title,
                created_at=created,
                updated_at=updated,
                model=detected_model,
                turns=turns,
            )
        )
    return convs


def _parse_gemini_activity_json(data: list[Any]) -> list[Conversation]:
    convs: list[Conversation] = []
    for idx, entry in enumerate(data):
        if not isinstance(entry, dict):
            continue
        header = str(entry.get("header") or "")
        title_raw = str(entry.get("title") or "")
        if "gemini" not in header.lower() and not title_raw.lower().startswith("prompted "):
            # Check explicit Gemini contents schema
            if isinstance(entry.get("contents"), list):
                turns: list[Turn] = []
                for c in entry["contents"]:
                    if not isinstance(c, dict):
                        continue
                    r_raw = str(c.get("role") or "").lower()
                    role: Literal["user", "assistant"] = "user" if r_raw == "user" else "assistant"
                    parts = c.get("parts")
                    if isinstance(parts, list):
                        txt = "\n".join(
                            str(p.get("text") or "")
                            for p in parts
                            if isinstance(p, dict) and p.get("text")
                        ).strip()
                        if txt:
                            turns.append(Turn(role=role, text=txt, timestamp=parse_timestamp(entry.get("time"))))
                if turns:
                    convs.append(
                        Conversation(
                            conv_id=f"gemini-c-{idx}",
                            platform="Gemini",
                            title=sanitize_preview(turns[0].text, 64),
                            created_at=turns[0].timestamp,
                            updated_at=turns[-1].timestamp,
                            model=str(entry.get("model")) if isinstance(entry.get("model"), str) else None,
                            turns=turns,
                        )
                    )
            continue

        prompt_text = re.sub(r"^Prompted\s+", "", title_raw, flags=re.I).strip()
        ts = parse_timestamp(entry.get("time"))
        turns = []
        if prompt_text:
            turns.append(Turn(role="user", text=prompt_text, timestamp=ts))
        safe_items = entry.get("safeHtmlItem")
        if isinstance(safe_items, list):
            ai_chunks = [
                strip_html_tags(str(s.get("html") or ""))
                for s in safe_items
                if isinstance(s, dict) and s.get("html")
            ]
            ai_text = "\n".join(c for c in ai_chunks if c).strip()
            if ai_text:
                turns.append(Turn(role="assistant", text=ai_text, timestamp=ts))
        if not turns:
            continue
        convs.append(
            Conversation(
                conv_id=f"gemini-{idx}",
                platform="Gemini",
                title=sanitize_preview(prompt_text or title_raw, 64),
                created_at=ts,
                updated_at=ts,
                model=None,
                turns=turns,
            )
        )
    return convs


def _parse_gemini_takeout_html(raw_html: str) -> list[Conversation]:
    convs: list[Conversation] = []
    blocks = re.split(r'<div[^>]+class="[^"]*outer-cell[^"]*"[^>]*>', raw_html)
    for idx, blk in enumerate(blocks[1:], 1):
        txt = strip_html_tags(blk)
        lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
        prompt_line = next((ln for ln in lines if ln.lower().startswith("prompted ")), "")
        if not prompt_line:
            continue
        prompt_text = re.sub(r"^Prompted\s+", "", prompt_line, flags=re.I).strip()
        ts: datetime | None = None
        for ln in lines:
            parsed = parse_timestamp(ln)
            if parsed is not None:
                ts = parsed
                break
        body_lines = [
            ln
            for ln in lines
            if ln != prompt_line and "gemini apps" not in ln.lower() and parse_timestamp(ln) is None
        ]
        turns = [Turn(role="user", text=prompt_text, timestamp=ts)]
        if body_lines:
            turns.append(Turn(role="assistant", text="\n".join(body_lines), timestamp=ts))
        convs.append(
            Conversation(
                conv_id=f"gemini-html-{idx}",
                platform="Gemini",
                title=sanitize_preview(prompt_text, 64),
                created_at=ts,
                updated_at=ts,
                model=None,
                turns=turns,
            )
        )
    return convs


def parse_json_payload(payload: Any, platform_hint: str | None = None) -> list[Conversation]:
    items = payload.get("conversations") if isinstance(payload, dict) and isinstance(payload.get("conversations"), list) else payload
    if not isinstance(items, list):
        return []
    sample = next((x for x in items if isinstance(x, dict)), None)
    if sample is None:
        return []
    if "mapping" in sample:
        return _parse_chatgpt_list(items, platform_hint or "ChatGPT")
    if "chat_messages" in sample:
        return _parse_claude_list(items)
    if "header" in sample or "safeHtmlItem" in sample or "contents" in sample or (
        isinstance(sample.get("title"), str) and sample["title"].lower().startswith("prompted ")
    ):
        return _parse_gemini_activity_json(items)
    # Generic list of normalized conversations {"title": ..., "messages": [{"role": ..., "content": ...}]}
    convs: list[Conversation] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        msgs = item.get("messages") or item.get("turns")
        if not isinstance(msgs, list):
            continue
        turns: list[Turn] = []
        for m in msgs:
            if not isinstance(m, dict):
                continue
            r_raw = str(m.get("role") or m.get("sender") or "").lower()
            if r_raw not in {"user", "human", "assistant", "model"}:
                continue
            content = m.get("content") or m.get("text")
            if isinstance(content, list):
                content = "\n".join(
                    str(c.get("text") or "") if isinstance(c, dict) else str(c) for c in content
                )
            txt = str(content or "").strip()
            if txt:
                role: Literal["user", "assistant"] = "user" if r_raw in {"user", "human"} else "assistant"
                turns.append(Turn(role=role, text=txt, timestamp=parse_timestamp(m.get("timestamp") or m.get("created_at"))))
        if turns:
            created = parse_timestamp(item.get("created_at") or item.get("create_time")) or turns[0].timestamp
            convs.append(
                Conversation(
                    conv_id=str(item.get("id") or f"generic-{idx}"),
                    platform=str(item.get("platform") or platform_hint or "AI Chat"),
                    title=str(item.get("title") or "Untitled Chat"),
                    created_at=created,
                    updated_at=turns[-1].timestamp or created,
                    model=str(item.get("model")) if isinstance(item.get("model"), str) else None,
                    turns=turns,
                )
            )
    return convs


def _extract_jsonl_text(msg_obj: Any) -> str:
    if isinstance(msg_obj, str):
        return msg_obj.strip()
    if isinstance(msg_obj, list):
        parts: list[str] = []
        for item in msg_obj:
            if isinstance(item, dict) and item.get("type") in {"text", "input_text", "output_text"} and isinstance(item.get("text"), str):
                parts.append(item["text"].strip())
            elif isinstance(item, str):
                parts.append(item.strip())
        return "\n".join(p for p in parts if p).strip()
    if isinstance(msg_obj, dict):
        if isinstance(msg_obj.get("content"), (str, list)):
            return _extract_jsonl_text(msg_obj["content"])
        if isinstance(msg_obj.get("text"), str):
            return str(msg_obj["text"]).strip()
    return ""


def parse_jsonl_session(raw_text: str, rel_name: str, platform: str = "Claude Code") -> list[Conversation]:
    turns: list[Turn] = []
    detected_model: str | None = None
    inferred_platform = platform
    if "codex" in rel_name.lower():
        inferred_platform = "Codex CLI"

    for line in raw_text.splitlines():
        line_s = line.strip()
        if not line_s.startswith("{"):
            continue
        try:
            ev = json.loads(line_s)
        except json.JSONDecodeError:
            continue
        if not isinstance(ev, dict):
            continue
        ts = parse_timestamp(ev.get("timestamp") or ev.get("created_at") or ev.get("ts"))

        # Claude Code JSONL schema: {"type": "user"|"assistant", "message": {"role": ..., "content": ...}}
        ev_type = str(ev.get("type") or ev.get("role") or "").lower()
        msg_payload = ev.get("message") or ev.get("payload") or ev
        role_raw = ""
        if ev_type in {"user", "human"}:
            role_raw = "user"
        elif ev_type == "assistant":
            role_raw = "assistant"
        elif isinstance(msg_payload, dict) and str(msg_payload.get("role") or "").lower() in {"user", "assistant"}:
            role_raw = str(msg_payload["role"]).lower()

        if role_raw not in {"user", "assistant"}:
            continue
        if isinstance(ev.get("isMeta"), bool) and ev["isMeta"]:
            continue

        txt = _extract_jsonl_text(msg_payload)
        if not txt or txt.startswith("<command-"):
            continue
        if isinstance(msg_payload, dict) and isinstance(msg_payload.get("model"), str):
            detected_model = msg_payload["model"]
        role: Literal["user", "assistant"] = "user" if role_raw == "user" else "assistant"
        turns.append(Turn(role=role, text=txt, timestamp=ts, model=detected_model))

    if not turns:
        return []
    first_user = next((t.text for t in turns if t.role == "user"), rel_name)
    created = next((t.timestamp for t in turns if t.timestamp), None)
    updated = next((t.timestamp for t in reversed(turns) if t.timestamp), created)
    return [
        Conversation(
            conv_id=f"jsonl-{Path(rel_name).stem}",
            platform=inferred_platform,
            title=sanitize_preview(first_user, 64),
            created_at=created,
            updated_at=updated,
            model=detected_model,
            turns=turns,
        )
    ]


def parse_markdown_transcript(raw_text: str, rel_name: str, mtime: datetime | None) -> list[Conversation]:
    role_re = re.compile(
        r"^(?:#{1,3}\s*|\*\*\s*)?(You|User|Human|Prompt|Assistant|Claude|ChatGPT|Gemini)\s*(?:\*\*|:)\s*(.*)$",
        re.IGNORECASE,
    )
    turns: list[Turn] = []
    cur_role: Literal["user", "assistant"] | None = None
    buf: list[str] = []

    def _flush() -> None:
        nonlocal cur_role, buf
        if cur_role is not None:
            txt = "\n".join(buf).strip()
            if txt:
                turns.append(Turn(role=cur_role, text=txt, timestamp=mtime))
        buf = []

    for line in raw_text.splitlines():
        m = role_re.match(line.strip())
        if m:
            _flush()
            speaker = m.group(1).lower()
            cur_role = "user" if speaker in {"you", "user", "human", "prompt"} else "assistant"
            if m.group(2).strip():
                buf.append(m.group(2).strip())
        elif cur_role is not None:
            buf.append(line)
    _flush()

    if len(turns) < 2:
        return []
    return [
        Conversation(
            conv_id=f"md-{Path(rel_name).stem}",
            platform="Markdown Notes",
            title=Path(rel_name).stem.replace("-", " ").replace("_", " ").title(),
            created_at=mtime,
            updated_at=mtime,
            model=None,
            turns=turns,
        )
    ]


def _load_zip_archive(zip_path: Path) -> tuple[list[Conversation], list[str]]:
    convs: list[Conversation] = []
    sources: list[str] = []
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for info in sorted(zf.infolist(), key=lambda i: i.filename):
                if info.is_dir():
                    continue
                if ".." in Path(info.filename).parts:
                    continue
                if info.file_size > MAX_ZIP_MEMBER_BYTES:
                    continue
                lower = info.filename.lower()
                base = Path(lower).name
                if base.endswith(".json") and (
                    base == "conversations.json"
                    or re.fullmatch(r"conversations-\d+\.json", base)
                    or "activity" in base
                    or "gemini" in lower
                ):
                    with zf.open(info, "r") as fh:
                        raw = io.TextIOWrapper(fh, encoding="utf-8", errors="ignore").read()
                    try:
                        parsed_json = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    found = parse_json_payload(parsed_json)
                    if found:
                        convs.extend(found)
                        sources.append(f"{zip_path.name}:{info.filename}")
                elif lower.endswith(".html") and ("activity" in base or "gemini" in lower):
                    with zf.open(info, "r") as fh:
                        raw_html = io.TextIOWrapper(fh, encoding="utf-8", errors="ignore").read()
                    found = _parse_gemini_takeout_html(raw_html)
                    if found:
                        convs.extend(found)
                        sources.append(f"{zip_path.name}:{info.filename}")
    except (OSError, zipfile.BadZipFile):
        return [], []
    return convs, sources


def load_conversations_from_target(
    target: Path,
    *,
    include_agents: bool = False,
) -> tuple[list[Conversation], list[str]]:
    convs: list[Conversation] = []
    sources: list[str] = []

    def _consume_file(fpath: Path, *, allow_md: bool = False) -> None:
        if len(convs) >= MAX_CONVERSATIONS or fpath.is_symlink() or not fpath.is_file():
            return
        lower = fpath.name.lower()
        try:
            size = fpath.stat().st_size
        except OSError:
            return

        if lower.endswith(".zip"):
            z_convs, z_srcs = _load_zip_archive(fpath)
            convs.extend(z_convs)
            sources.extend(z_srcs)
            return

        if lower.endswith(".json"):
            if size > MAX_TEXT_FILE_BYTES:
                return
            try:
                data = json.loads(fpath.read_text(encoding="utf-8", errors="ignore"))
            except (OSError, json.JSONDecodeError):
                return
            found = parse_json_payload(data)
            if found:
                convs.extend(found)
                sources.append(fpath.name)
            return

        if lower.endswith(".html") and ("activity" in lower or "gemini" in str(fpath).lower()):
            if size > MAX_TEXT_FILE_BYTES:
                return
            try:
                found = _parse_gemini_takeout_html(fpath.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                return
            if found:
                convs.extend(found)
                sources.append(fpath.name)
            return

        if lower.endswith(".jsonl") and size <= MAX_JSONL_BYTES:
            try:
                found = parse_jsonl_session(
                    fpath.read_text(encoding="utf-8", errors="ignore"),
                    str(fpath),
                )
            except OSError:
                return
            if found:
                convs.extend(found)
                sources.append(fpath.name)
            return

        if allow_md and lower.endswith((".md", ".txt")) and size <= 5 * 1024 * 1024:
            try:
                mtime = datetime.fromtimestamp(fpath.stat().st_mtime, tz=timezone.utc)
                found = parse_markdown_transcript(
                    fpath.read_text(encoding="utf-8", errors="ignore"),
                    str(fpath),
                    mtime,
                )
            except OSError:
                return
            if found:
                convs.extend(found)
                sources.append(fpath.name)

    if target.is_file():
        _consume_file(target, allow_md=True)
    elif target.is_dir():
        allow_hidden_root = target.name.startswith(".") or include_agents
        for dirpath, dirnames, filenames in os.walk(target):
            dirnames[:] = sorted(
                d
                for d in dirnames
                if d not in EXCLUDED_DIRS and (allow_hidden_root or not d.startswith("."))
            )
            for fname in sorted(filenames):
                fpath = Path(dirpath) / fname
                lower = fname.lower()
                if lower.endswith((".zip", ".jsonl")) or (
                    lower.endswith(".json")
                    and (
                        lower == "conversations.json"
                        or bool(re.fullmatch(r"conversations-\d+\.json", lower))
                        or "activity" in lower
                        or "wrapped" in lower
                        or "export" in lower
                    )
                ) or (lower.endswith((".html", ".md", ".txt")) and "readme" not in lower and "portable" not in lower):
                    _consume_file(fpath, allow_md=lower.endswith((".md", ".txt")))
                    if len(convs) >= MAX_CONVERSATIONS:
                        break

    if include_agents:
        home = Path.home()
        for agent_dir in (home / ".claude" / "projects", home / ".codex" / "sessions"):
            if agent_dir.is_dir() and agent_dir.resolve() != target.resolve():
                for root_s, _, files in os.walk(agent_dir):
                    for fn in sorted(files):
                        if fn.endswith(".jsonl"):
                            _consume_file(Path(root_s) / fn)

    return convs[:MAX_CONVERSATIONS], sources


def build_demo_conversations() -> tuple[list[Conversation], list[str]]:
    """Build a realistic multi-platform sample export for instant zero-config preview."""
    base = datetime(2026, 2, 1, 9, 15, tzinfo=timezone.utc)
    samples: list[tuple[str, str, str, int, int, list[tuple[str, str]]]] = [
        (
            "ChatGPT",
            "gpt-4o",
            "15-Minute Weeknight Crispy Tofu & Chili Crisp Bowl",
            3,
            19,
            [
                ("user", "Can you please give me a concise step-by-step recipe for crispy pan-seared tofu under 15 minutes? Keep it simple."),
                ("assistant", "Certainly! Let's break this down into 4 crisp steps so dinner hits the table fast."),
                ("user", "Thanks! Can I swap cornstarch for potato starch and add cucumber salad?"),
                ("assistant", "Great question! Potato starch actually crisps up even lighter. Here is the quick table."),
            ],
        ),
        (
            "ChatGPT",
            "gpt-4o",
            "6-Day Kyoto & Naoshima Autumn Itinerary Without Tourist Crowds",
            14,
            23,
            [
                ("user", "Help me plan a realistic 6-day Kyoto + Naoshima trip in November without waking up at 5 AM every day."),
                ("assistant", "I'd be happy to craft a relaxed itinerary! Let's break this down day by day."),
                ("user", "Could you put the train hops and luggage-forwarding costs in a comparison table?"),
                ("assistant", "Certainly! Here is a comprehensive overview in table format."),
                ("user", "Wait, what about rainy-day museum backups near Higashiyama?"),
                ("assistant", "Great question! Here are 4 quiet ceramic studios and covered arcades."),
            ],
        ),
        (
            "Claude",
            "claude-3.7-sonnet",
            "Apartment Lease Renewal Pushback & Deposit Cap Email",
            28,
            14,
            [
                ("user", "My landlord raised rent 11% with 20 days notice. Please draft a polite firm email asking to cap at 4% with bullet points."),
                ("assistant", "I'd be happy to help craft a calm, clear counter-proposal."),
                ("user", "Make it two paragraphs shorter and plain English. Keep it respectful."),
                ("assistant", "Certainly! Here is the tightened 110-word version ready to send."),
            ],
        ),
        (
            "Claude",
            "claude-3.7-sonnet",
            "Build Local-First Recipe & Pantry App MVP",
            45,
            2,
            [
                ("user", "I want to build an offline weekend project app that suggests meals from pantry photos. Critique my idea brutally—what am I missing?"),
                ("assistant", "Great question! Let's delve into the three biggest pitfalls with photo-first pantry apps."),
                ("user", "Good call on manual barcode fatigue. How do we ship v1 in one Sunday using SQLite + Next.js?"),
                ("assistant", "Let's break this down into a lean schema and fast receipt-scan fallback."),
                ("user", "Write the minimal schema and zero-signup local storage flow. No fluff please."),
                ("assistant", "Here is the exact 3-table schema and offline flow."),
            ],
        ),
        (
            "Gemini",
            "gemini-2.5-pro",
            "Explain ETF Tax-Loss Harvesting in Plain English",
            62,
            20,
            [
                ("user", "Explain ETF tax-loss harvesting like I'm 5 with a concrete example. No jargon please."),
                ("assistant", "Think of tax-loss harvesting like trading two very similar coats at the end of winter."),
                ("user", "Thank you! What triggers the 30-day wash-sale rule if dividends reinvest automatically?"),
                ("assistant", "Great question! It is important to note that automatic DRIP buys count as purchases."),
            ],
        ),
        (
            "Claude",
            "claude-3.7-sonnet",
            "Salary Counter-Offer Script After Verbal Offer",
            85,
            1,
            [
                ("user", "They offered $135k base + zero sign-on, but market band goes up to $155k. Draft a confident negotiation script."),
                ("assistant", "Certainly! Let's anchor on total impact and ask calmly for $152k plus a sign-on bridge."),
                ("user", "Could you give me 3 objection responses if they say budgets are frozen?"),
                ("assistant", "Of course! Here are three concise pivots covering title, review cycle, and signing bonus."),
                ("user", "Wait, also add a deadline line without sounding pushy. Thanks!"),
                ("assistant", "It is important to note how calmly setting a Friday decision date keeps momentum."),
            ],
        ),
        (
            "ChatGPT",
            "o3",
            "Fix Half-Marathon Knee Pain & Taper Schedule",
            110,
            22,
            [
                ("user", "Week 9 of half-marathon prep and outer knee feels tight after 10km. Should I swap Wednesday's tempo run for cycling?"),
                ("assistant", "Great question! Swapping load for low-impact cadence while keeping aerobic volume is smart."),
                ("user", "Give me a 2-week recovery + strength checklist in bullet points."),
                ("assistant", "Certainly! Let's delve into hip-glute stabilization drills."),
            ],
        ),
        (
            "Gemini",
            "gemini-2.5-flash",
            "Convert Messy Q3 Customer Survey Into Executive Summary",
            135,
            11,
            [
                ("user", "Summarize these 40 interview notes into top 5 churn reasons with exact percentages in a table. Concise only."),
                ("assistant", "Here is a comprehensive overview showing onboarding friction accounts for 38%."),
                ("user", "Thanks! Now turn row 1 and row 2 into a 4-sentence Slack update for founders."),
                ("assistant", "Sure thing! Here is the tight 4-sentence founder update."),
            ],
        ),
        (
            "ChatGPT",
            "gpt-4o",
            "Launch Micro-Newsletter on Backyard Vegetable Gardening",
            170,
            3,
            [
                ("user", "Help me design and launch a bi-weekly backyard gardening newsletter for apartment balconies. Give me 10 issue titles."),
                ("assistant", "What a tapestry of urban growing ideas! I'd be happy to brainstorm 10 compelling hooks."),
                ("user", "Pick the top 3 for beginners in March and outline issue #1 step-by-step."),
                ("assistant", "Certainly! Issue #1 focuses on herbs that thrive in 4 hours of sunlight."),
                ("user", "Can we also plan a lead magnet PDF checklist?"),
                ("assistant", "Let's break this down into a one-page watering and soil sheet."),
            ],
        ),
        (
            "Claude",
            "claude-3.7-sonnet",
            "Debug Async Python Webhook Timeout & Memory Leak",
            205,
            23,
            [
                ("user", "Why is this httpx webhook worker hanging at 2AM?! Look at line 42—fix this ASAP, production queue is backed up!!!"),
                ("assistant", "Look at line 42: httpx.post omits a timeout and creates a fresh client inside the loop."),
                ("user", "Got it, thank you! Add an exponential backoff cap and bounded semaphore, concise code please."),
                ("assistant", "Here is the bounded AsyncClient singleton with max 5 retries."),
            ],
        ),
        (
            "ChatGPT",
            "gpt-4o",
            "Plan Indie Film Short Budget & Shot List",
            245,
            16,
            [
                ("user", "Help me organize a $1,200 weekend short film shoot: gear rental, catering, and shot list in a markdown table."),
                ("assistant", "I'd be happy to organize a lean 2-day shoot schedule and budget table."),
                ("user", "Please add rain backup indoor locations and a concise call-sheet template."),
                ("assistant", "Certainly! Here is your plug-and-play call sheet."),
            ],
        ),
    ]

    convs: list[Conversation] = []
    # Expand across calendar dates to showcase genuine streaks & realistic volume
    for idx, (platform, model, title, day_offset, hour, pairs) in enumerate(samples):
        turns: list[Turn] = []
        t0 = base + timedelta(days=day_offset, hours=(hour - 9))
        for t_idx, (role_s, txt) in enumerate(pairs):
            role: Literal["user", "assistant"] = "user" if role_s == "user" else "assistant"
            turns.append(Turn(role=role, text=txt, timestamp=t0 + timedelta(minutes=t_idx * 4), model=model))
        convs.append(
            Conversation(
                conv_id=f"demo-{idx + 1}",
                platform=platform,
                title=title,
                created_at=t0,
                updated_at=turns[-1].timestamp,
                model=model,
                turns=turns,
            )
        )

    streak_prompts = [
        ("Weekly Grocery & Meal Prep Budget", "Please organize this week's dinner recipes and grocery list under a $90 budget.", "Sure thing! Here is your budget meal plan."),
        ("Morning Mobility & Marathon Recovery", "Could you build a 15-minute hip stretch and running recovery routine after my 10km?", "Certainly! Let's break down three recovery stretches."),
        ("Client Kickoff Summary Email", "Turn my rough meeting notes into a polite crisp follow-up email with bullet points.", "I'd be happy to draft that client recap cleanly."),
        ("Spanish Coffee-Shop Survival Phrases", "Teach me 10 practical Spanish travel phrases for ordering coffee and trains in Madrid.", "Great question! Here are 10 natural everyday phrases."),
        ("Quarterly Freelance Tax Deduction Check", "Explain which home-office laptop and software expenses count on quarterly estimated taxes.", "It is important to note IRS documentation basics."),
        ("Newsletter Subject Line A/B Test", "Rewrite these 3 newsletter headlines in a punchier human tone—no fluff please.", "Certainly! Here are three concise subject variants."),
        ("Fix React Modal Scroll Lock Bug", "Why does iOS Safari scroll behind my modal? Keep the fix concise in TypeScript.", "Here is a clean 8-line overscroll fix."),
        ("Apartment Closet Capsule Wardrobe", "Help me organize a minimalist 14-piece autumn travel wardrobe for rainy weather.", "I'd be happy to map out a packable capsule list."),
        ("Sunday Evening Reset & Priority Plan", "Thanks! Prioritize my career pitch, workout plan, and apartment clean-up into Sunday morning blocks.", "Certainly! Here is a realistic Sunday sprint plan."),
    ]
    for offset_idx, (st_title, st_user, st_ai) in enumerate(streak_prompts):
        streak_day = 250 + offset_idx
        dt = base + timedelta(days=streak_day, hours=(2 + offset_idx) % 24)
        plat = ("ChatGPT", "Claude", "Gemini")[offset_idx % 3]
        mod = {"ChatGPT": "gpt-4o", "Claude": "claude-3.7-sonnet", "Gemini": "gemini-2.5-pro"}[plat]
        convs.append(
            Conversation(
                conv_id=f"demo-streak-{streak_day}",
                platform=plat,
                title=st_title,
                created_at=dt,
                updated_at=dt + timedelta(minutes=2),
                model=mod,
                turns=[
                    Turn(role="user", text=st_user, timestamp=dt),
                    Turn(role="assistant", text=st_ai, timestamp=dt + timedelta(minutes=1)),
                ],
            )
        )

    return convs, ["built-in-demo-sample"]


def _longest_streak(active_days: set[str]) -> int:
    if not active_days:
        return 0
    dates = sorted(datetime.strptime(d, "%Y-%m-%d").date() for d in active_days)
    best = 1
    run = 1
    for prev, cur in zip(dates, dates[1:], strict=False):
        if (cur - prev).days == 1:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def _pick_novel_comparison(user_words: int) -> str:
    if user_words < 1_000:
        return f"{user_words:,} words (~{max(1, round(user_words / 250))} single-spaced pages)"
    # Pick closest memorable book benchmark
    best_name, best_words = min(
        NOVEL_BENCHMARKS,
        key=lambda item: abs(user_words - item[1]),
    )
    ratio = user_words / best_words
    return f"{ratio:.1f}x the length of {best_name}"


def _pick_archetype(
    *,
    night_pct: float,
    morning_pct: float,
    politeness_score: int,
    avg_turns: float,
    domain_counts: Counter[str],
    platform_count: int,
) -> tuple[str, str]:
    top_domain = domain_counts.most_common(1)[0][0] if domain_counts else ""
    if night_pct >= 28.0:
        return (
            "The Midnight Polymath",
            "Best ideas arrive after 10 PM—shipping side projects, deep questions, and 2 AM rabbit holes.",
        )
    if avg_turns >= 10.0 and top_domain == "Coding & Tech":
        return (
            "The Deep-Dive Systems Builder",
            "Treats AI like a co-architect—multi-turn debugging, schema iterations, and ruthless clarity.",
        )
    if politeness_score >= 78:
        return (
            "The Polite Perfectionist",
            "Says 'please' and 'thank you' to silicon every single session—future AI overlords will promote you.",
        )
    if platform_count >= 3:
        return (
            "The Multi-Model Strategist",
            "Switches cleanly across ChatGPT, Claude, and Gemini to match every problem to the sharpest model.",
        )
    if morning_pct >= 40.0:
        return (
            "The Dawn Sprinter",
            "Clears tough writing, planning, and decisions with coffee before the rest of the team wakes up.",
        )
    if avg_turns <= 4.5:
        return (
            "The Rapid-Fire Operator",
            "Fast, targeted prompts in and answers out—uses AI as an instant precision lever.",
        )
    if top_domain in {"Writing & Content", "Creative & Projects"}:
        return (
            "The Editorial Wordsmith",
            "Iterates headlines, stories, and emails until every sentence sounds unmistakable and human.",
        )
    return (
        "The Everyday Explorer",
        "Uses AI as a true second brain—balancing work, learning, trips, finances, and real life cleanly.",
    )


def analyze_conversations(
    conversations: list[Conversation],
    sources: list[str],
    *,
    year: int | None = None,
) -> dict[str, Any]:
    """Compute deterministic analytics, archetype, unfinished loops, and style signals."""
    filtered: list[Conversation] = []
    for conv in conversations:
        if year is not None:
            year_turns = [t for t in conv.turns if t.timestamp and t.timestamp.year == year]
            if not year_turns and not (conv.created_at and conv.created_at.year == year):
                continue
            filtered.append(
                dataclasses.replace(
                    conv,
                    turns=year_turns if year_turns else conv.turns,
                )
            )
        else:
            filtered.append(conv)

    if not filtered:
        return {
            "tool": "ai-wrapped",
            "version": VERSION,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
            "year_filter": year,
            "sources": sources,
            "empty": True,
            "overview": {
                "conversations": 0,
                "user_turns": 0,
                "assistant_turns": 0,
                "user_words": 0,
                "assistant_words": 0,
                "estimated_tokens": 0,
                "novel_comparison": "0 words",
                "active_days": 0,
                "longest_streak_days": 0,
                "peak_day": None,
                "peak_day_turns": 0,
                "busiest_month": None,
                "date_start": None,
                "date_end": None,
                "avg_turns_per_chat": 0.0,
                "longest_chat_turns": 0,
                "longest_chat_title": "",
            },
            "rhythm": {
                "hours": [0] * 24,
                "weekdays": [0] * 7,
                "peak_hour": 12,
                "night_owl_pct": 0.0,
                "morning_pct": 0.0,
                "two_am_rabbit_holes": 0,
            },
            "tone": {
                "politeness_score": 50,
                "polite_hits": 0,
                "urgent_hits": 0,
                "politeness_verdict": "Balanced & Direct",
                "sycophancy_total": 0,
                "top_ai_cliches": [],
            },
            "platforms": [],
            "models": [],
            "domains": [],
            "top_keywords": [],
            "monthly_counts": [],
            "unfinished_projects": [],
            "style_preferences": [],
            "archetype": {"name": "The Clean Slate", "tagline": "No matching chats found in this archive."},
        }

    hours = [0] * 24
    weekdays = [0] * 7
    day_turns: Counter[str] = Counter()
    month_turns: Counter[str] = Counter()
    platform_counts: Counter[str] = Counter()
    model_counts: Counter[str] = Counter()
    domain_counts: Counter[str] = Counter()
    keyword_counts: Counter[str] = Counter()
    cliche_counts: Counter[str] = Counter()
    style_hits: Counter[str] = Counter()
    style_desc: dict[str, str] = {}

    user_turns = 0
    assistant_turns = 0
    user_words = 0
    assistant_words = 0
    polite_hits = 0
    urgent_hits = 0
    two_am_count = 0
    morning_count = 0
    night_count = 0
    timed_user_turns = 0
    all_dates: list[datetime] = []

    longest_chat_turns = 0
    longest_chat_title = ""

    for conv in filtered:
        platform_counts[conv.platform] += 1
        if conv.model:
            model_counts[conv.model] += 1
        if len(conv.turns) > longest_chat_turns:
            longest_chat_turns = len(conv.turns)
            longest_chat_title = sanitize_preview(conv.title, 80)

        conv_user_blob: list[str] = [conv.title]
        for turn in conv.turns:
            words = re.findall(r"[A-Za-z0-9']+", turn.text)
            if turn.role == "user":
                user_turns += 1
                user_words += len(words)
                conv_user_blob.append(turn.text)
                if POLITE_RE.search(turn.text):
                    polite_hits += 1
                if URGENT_RE.search(turn.text):
                    urgent_hits += 1
                for key, pat, desc in STYLE_PREFERENCE_SIGNALS:
                    if pat.search(turn.text):
                        style_hits[key] += 1
                        style_desc[key] = desc
                for tok in words:
                    low = tok.lower().strip("'")
                    if len(low) >= 4 and low not in STOPWORDS and not low.isdigit():
                        keyword_counts[low] += 1
                if turn.timestamp is not None:
                    timed_user_turns += 1
                    all_dates.append(turn.timestamp)
                    hr = turn.timestamp.hour
                    hours[hr] += 1
                    weekdays[turn.timestamp.weekday()] += 1
                    day_turns[turn.timestamp.strftime("%Y-%m-%d")] += 1
                    month_turns[turn.timestamp.strftime("%Y-%m")] += 1
                    if 2 <= hr <= 4:
                        two_am_count += 1
                    if hr >= 22 or hr <= 4:
                        night_count += 1
                    if 6 <= hr <= 11:
                        morning_count += 1
            else:
                assistant_turns += 1
                assistant_words += len(words)
                if turn.model and not conv.model:
                    model_counts[turn.model] += 1
                for label, pat in AI_SYCOPHANCY_PATTERNS:
                    matches = pat.findall(turn.text)
                    if matches:
                        cliche_counts[label] += len(matches)

        blob_lower = " ".join(conv_user_blob).lower()
        blob_tokens = set(re.findall(r"[a-z0-9-]+", blob_lower))
        matched_any_domain = False
        for dom_name, dom_terms in DOMAIN_KEYWORDS.items():
            score = sum(1 for term in dom_terms if term in blob_tokens)
            if score >= 2 or (score == 1 and any(term in conv.title.lower() for term in dom_terms)):
                domain_counts[dom_name] += 1
                matched_any_domain = True
        if not matched_any_domain:
            domain_counts["Everyday & General"] += 1

    # Unfinished / Deep Projects detection (multi-turn actionable threads)
    max_dt = max(all_dates) if all_dates else None
    unfinished: list[dict[str, Any]] = []
    for conv in sorted(filtered, key=lambda c: len(c.turns), reverse=True):
        if len(conv.turns) < 4:
            continue
        combined = f"{conv.title} " + " ".join(t.text for t in conv.turns if t.role == "user")[:500]
        if UNFINISHED_ACTION_RE.search(combined):
            last_user = next((t.text for t in reversed(conv.turns) if t.role == "user"), "")
            stale_days = (max_dt - conv.updated_at).days if (max_dt and conv.updated_at) else None
            unfinished.append(
                {
                    "title": sanitize_preview(conv.title, 76),
                    "platform": conv.platform,
                    "turns": len(conv.turns),
                    "last_prompt": sanitize_preview(last_user, 110),
                    "last_active": conv.updated_at.strftime("%Y-%m-%d") if conv.updated_at else None,
                    "stale_days": stale_days,
                }
            )
        if len(unfinished) >= 6:
            break

    active_days_set = set(day_turns.keys())
    streak = _longest_streak(active_days_set)
    peak_day, peak_day_turns = day_turns.most_common(1)[0] if day_turns else (None, 0)
    busiest_month = month_turns.most_common(1)[0][0] if month_turns else None

    total_convs = len(filtered)
    avg_turns = round((user_turns + assistant_turns) / total_convs, 1) if total_convs else 0.0
    night_pct = round(100.0 * night_count / timed_user_turns, 1) if timed_user_turns else 0.0
    morning_pct = round(100.0 * morning_count / timed_user_turns, 1) if timed_user_turns else 0.0
    peak_hour = max(range(24), key=lambda h: hours[h]) if timed_user_turns else 12

    polite_ratio = polite_hits / max(1, user_turns)
    urgent_ratio = urgent_hits / max(1, user_turns)
    politeness_score = max(5, min(99, round(52 + (polite_ratio * 65) - (urgent_ratio * 55))))
    if politeness_score >= 78:
        politeness_verdict = "AI Overlords Will Spare You"
    elif politeness_score >= 55:
        politeness_verdict = "Warm & Respectful Collaborator"
    elif politeness_score >= 35:
        politeness_verdict = "Crisp & Direct Strategist"
    else:
        politeness_verdict = "Pure No-Mercy Deadline Mode"

    arch_name, arch_tagline = _pick_archetype(
        night_pct=night_pct,
        morning_pct=morning_pct,
        politeness_score=politeness_score,
        avg_turns=avg_turns,
        domain_counts=domain_counts,
        platform_count=len(platform_counts),
    )

    est_tokens = round((user_words + assistant_words) * 1.33)
    sorted_months = sorted(month_turns.items())[-12:]

    return {
        "tool": "ai-wrapped",
        "version": VERSION,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        "year_filter": year,
        "sources": sources[:25],
        "empty": False,
        "overview": {
            "conversations": total_convs,
            "user_turns": user_turns,
            "assistant_turns": assistant_turns,
            "user_words": user_words,
            "assistant_words": assistant_words,
            "estimated_tokens": est_tokens,
            "novel_comparison": _pick_novel_comparison(user_words),
            "active_days": len(active_days_set),
            "longest_streak_days": streak,
            "peak_day": peak_day,
            "peak_day_turns": peak_day_turns,
            "busiest_month": busiest_month,
            "date_start": min(all_dates).strftime("%Y-%m-%d") if all_dates else None,
            "date_end": max(all_dates).strftime("%Y-%m-%d") if all_dates else None,
            "avg_turns_per_chat": avg_turns,
            "longest_chat_turns": longest_chat_turns,
            "longest_chat_title": longest_chat_title,
        },
        "rhythm": {
            "hours": hours,
            "weekdays": weekdays,
            "peak_hour": peak_hour,
            "night_owl_pct": night_pct,
            "morning_pct": morning_pct,
            "two_am_rabbit_holes": two_am_count,
        },
        "tone": {
            "politeness_score": politeness_score,
            "polite_hits": polite_hits,
            "urgent_hits": urgent_hits,
            "politeness_verdict": politeness_verdict,
            "sycophancy_total": sum(cliche_counts.values()),
            "top_ai_cliches": [{"phrase": p, "count": c} for p, c in cliche_counts.most_common(6)],
        },
        "platforms": [
            {"name": p, "conversations": c, "pct": round(100.0 * c / total_convs, 1)}
            for p, c in platform_counts.most_common()
        ],
        "models": [{"name": m, "count": c} for m, c in model_counts.most_common(6)],
        "domains": [{"name": d, "count": c} for d, c in domain_counts.most_common(8)],
        "top_keywords": [{"word": w, "count": c} for w, c in keyword_counts.most_common(14)],
        "monthly_counts": [{"month": m, "turns": c} for m, c in sorted_months],
        "unfinished_projects": unfinished,
        "style_preferences": [
            {"id": k, "hits": c, "rule": style_desc[k]}
            for k, c in style_hits.most_common(6)
        ],
        "archetype": {"name": arch_name, "tagline": arch_tagline},
    }


def render_portable_brain(summary: dict[str, Any]) -> str:
    ov = summary["overview"]
    arch = summary["archetype"]
    domains = summary["domains"]
    keywords = summary["top_keywords"]
    prefs = summary["style_preferences"]
    projects = summary["unfinished_projects"]
    platforms = ", ".join(f"{p['name']} ({p['pct']}%)" for p in summary["platforms"]) or "None"

    lines = [
        "# Portable AI Brain & Personal Context Pack",
        "",
        f"> Generated offline by **AI Wrapped v{summary['version']}** across {ov['conversations']:,} chats "
        f"({ov['user_words']:,} user words). Sensitive keys/emails were automatically redacted.",
        "",
        "Paste this file into **Claude Projects / Custom Instructions**, **ChatGPT Memory**, **Gemini Gems**, or your project's **`CLAUDE.md` / `AGENTS.md`** so any new AI knows how to collaborate with you immediately.",
        "",
        "## 1. Identity & Interaction Profile",
        f"- **Archetype**: {arch['name']} — {arch['tagline']}",
        f"- **Platforms Analyzed**: {platforms}",
        f"- **Typical Thread Depth**: {ov['avg_turns_per_chat']} messages/chat (deepest thread: {ov['longest_chat_turns']} turns)",
        f"- **Active Peak Window**: Hour `{summary['rhythm']['peak_hour']:02d}:00 UTC` "
        f"(night-owl share: {summary['rhythm']['night_owl_pct']}%)",
        "",
        "## 2. How I Like Responses Formatted",
    ]
    if prefs:
        for pr in prefs:
            lines.append(f"- {pr['rule']} *(observed {pr['hits']}x in past prompts)*")
    else:
        lines.append("- Prefer clear, direct answers backed by concrete examples and next steps.")

    if domains:
        lines.extend(["", "## 3. Primary Focus Areas & Obsessions"])
        for dom in domains[:6]:
            lines.append(f"- **{dom['name']}** ({dom['count']} threads)")

    if keywords:
        kw_str = ", ".join(f"`{k['word']}`" for k in keywords[:12])
        lines.extend(["", "## 4. Recurring Topics & Vocabulary", f"- Focus keywords: {kw_str}"])

    if projects:
        lines.extend(["", "## 5. Unfinished Loops & Active Projects to Remember"])
        for proj in projects:
            stale = f" *(last active {proj['last_active']})*" if proj.get("last_active") else ""
            lines.append(
                f"- **{proj['title']}** [{proj['platform']}, {proj['turns']} turns]{stale}: "
                f"last asked — \"{proj['last_prompt']}\""
            )

    lines.extend(
        [
            "",
            "## 6. Standing Guardrails for Any Assistant",
            f"- Skip filler praise (you received **\"{summary['tone']['top_ai_cliches'][0]['phrase']}\"** and similar clichés "
            f"{summary['tone']['sycophancy_total']} times in past chats)."
            if summary["tone"]["sycophancy_total"]
            else "- Skip filler praise and start directly with the substance.",
            "- Ask clarifying questions only when ambiguity changes the outcome; otherwise execute cleanly.",
            "- Flag hidden tradeoffs, assumptions, and missing edge cases upfront.",
            "",
        ]
    )
    return "\n".join(lines)


def _format_hour_12(hr: int) -> str:
    if hr == 0:
        return "12 AM"
    if hr < 12:
        return f"{hr} AM"
    if hr == 12:
        return "12 PM"
    return f"{hr - 12} PM"


def _build_hours_svg(hours: list[int]) -> str:
    peak = max(hours) if any(hours) else 1
    bars: list[str] = []
    width = 620
    height = 148
    bar_w = 19
    gap = 6
    for hr, val in enumerate(hours):
        x = 12 + hr * (bar_w + gap)
        bh = max(4, round((val / peak) * 100)) if val > 0 else 4
        y = 116 - bh
        is_night = hr >= 22 or hr <= 4
        fill = "#a855f7" if is_night else "#22d3ee"
        opacity = "0.22" if val == 0 else "0.92"
        bars.append(
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bh}" rx="4" fill="{fill}" opacity="{opacity}">'
            f"<title>{_format_hour_12(hr)}: {val} prompts</title></rect>"
        )
        if hr in {0, 6, 12, 18, 23}:
            bars.append(
                f'<text x="{x + bar_w / 2}" y="138" text-anchor="middle" fill="#94a3b8" font-size="10">{hr:02d}h</text>'
            )
    return f'<svg viewBox="0 0 {width} {height}" class="chart-svg" role="img" aria-label="24-hour activity clock">{"".join(bars)}</svg>'


def _build_monthly_svg(monthly: list[dict[str, Any]]) -> str:
    if not monthly:
        return '<div class="muted">No timestamped monthly activity found.</div>'
    peak = max(m["turns"] for m in monthly) or 1
    width = 620
    height = 132
    n = len(monthly)
    slot = max(28, math.floor((width - 24) / n))
    bar_w = min(38, slot - 8)
    parts: list[str] = []
    for idx, item in enumerate(monthly):
        x = 12 + idx * slot + (slot - bar_w) / 2
        bh = max(6, round((item["turns"] / peak) * 86))
        y = 102 - bh
        lbl = item["month"][2:]
        parts.append(
            f'<rect x="{x:.1f}" y="{y}" width="{bar_w}" height="{bh}" rx="5" fill="url(#barGrad)">'
            f"<title>{html.escape(item['month'])}: {item['turns']} prompts</title></rect>"
        )
        parts.append(
            f'<text x="{x + bar_w / 2:.1f}" y="122" text-anchor="middle" fill="#94a3b8" font-size="10">{html.escape(lbl)}</text>'
        )
    defs = '<defs><linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#38bdf8"/><stop offset="100%" stop-color="#6366f1"/></linearGradient></defs>'
    return f'<svg viewBox="0 0 {width} {height}" class="chart-svg" role="img" aria-label="Monthly prompt cadence">{defs}{"".join(parts)}</svg>'


def render_html(summary: dict[str, Any]) -> str:
    """Render a self-contained interactive Story + Bento Dashboard HTML file."""
    ov = summary["overview"]
    rhythm = summary["rhythm"]
    tone = summary["tone"]
    arch = summary["archetype"]
    e = html.escape

    span_label = (
        f"{ov['date_start']} → {ov['date_end']}"
        if ov["date_start"] and ov["date_end"]
        else "All Exported Chats"
    )
    share_text = (
        f"My AI Wrapped:\n"
        f"• Archetype: {arch['name']}\n"
        f"• {ov['conversations']:,} conversations | {ov['user_words']:,} words written ({ov['novel_comparison']})\n"
        f"• Peak hour: {_format_hour_12(rhythm['peak_hour'])} ({rhythm['two_am_rabbit_holes']} at 2–5 AM)\n"
        f"• Politeness score: {tone['politeness_score']}/100 ({tone['politeness_verdict']})\n"
        f"• AI clichés survived: {tone['sycophancy_total']}\n"
        f"Generated 100% offline with codesphere-u/ai-wrapped"
    )
    safe_json_share = json.dumps(share_text).replace("<", "\\u003c")

    hours_svg = _build_hours_svg(rhythm["hours"])
    monthly_svg = _build_monthly_svg(summary["monthly_counts"])

    dom_max = max((d["count"] for d in summary["domains"]), default=1)
    domain_rows = "".join(
        f'<div class="bar-row"><div class="bar-head"><span>{e(d["name"])}</span><span class="mono">{d["count"]} chats</span></div>'
        f'<div class="track"><div class="fill c-teal" style="width:{max(6, round(100 * d["count"] / dom_max))}%"></div></div></div>'
        for d in summary["domains"][:6]
    )

    plat_rows = "".join(
        f'<div class="bar-row"><div class="bar-head"><span>{e(p["name"])}</span><span class="mono">{p["conversations"]} ({p["pct"]}%)</span></div>'
        f'<div class="track"><div class="fill c-violet" style="width:{max(6, round(p["pct"]))}%"></div></div></div>'
        for p in summary["platforms"]
    )
    model_chips = "".join(
        f'<span class="chip">{e(m["name"])} <em>×{m["count"]}</em></span>'
        for m in summary["models"]
    )
    kw_chips = "".join(
        f'<span class="chip">{e(k["word"])} <em>{k["count"]}</em></span>'
        for k in summary["top_keywords"][:12]
    )
    cliche_rows = "".join(
        f'<div class="stat-line"><span>“{e(c["phrase"])}”</span><strong class="mono">{c["count"]}×</strong></div>'
        for c in tone["top_ai_cliches"]
    ) or '<div class="muted">Zero clichés detected.</div>'

    project_cards = "".join(
        f'<div class="loop-card"><div class="loop-meta"><span>{e(p["platform"])}</span>'
        f'<span>{p["turns"]} turns</span></div>'
        f'<div class="loop-title">{e(p["title"])}</div>'
        f'<div class="loop-last">Last prompt: {e(p["last_prompt"])}</div></div>'
        for p in summary["unfinished_projects"]
    ) or '<div class="muted">No multi-turn unfinished projects found in this slice.</div>'

    circ = 2 * math.pi * 44
    dash = round((tone["politeness_score"] / 100.0) * circ, 1)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Wrapped — {e(arch['name'])}</title>
<style>
  :root {{
    --bg: #070b14;
    --card: #101727;
    --border: rgba(148, 163, 184, 0.16);
    --text: #f8fafc;
    --muted: #94a3b8;
    --cyan: #22d3ee;
    --violet: #a855f7;
    --amber: #f59e0b;
    --emerald: #10b981;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
    background: radial-gradient(circle at 15% 10%, rgba(56,189,248,0.14), transparent 36%),
                radial-gradient(circle at 85% 20%, rgba(168,85,247,0.16), transparent 38%),
                var(--bg);
    color: var(--text);
    line-height: 1.5;
    min-height: 100vh;
  }}
  .topbar {{
    position: sticky; top: 0; z-index: 20;
    backdrop-filter: blur(14px);
    background: rgba(7, 11, 20, 0.85);
    border-bottom: 1px solid var(--border);
    padding: 12px 20px;
    display: flex; flex-wrap: wrap; gap: 10px; align-items: center; justify-content: space-between;
  }}
  .brand {{ font-weight: 800; letter-spacing: -0.02em; display: flex; align-items: center; gap: 10px; }}
  .badge {{ background: linear-gradient(135deg, var(--cyan), var(--violet)); color: #050811; padding: 3px 9px; border-radius: 999px; font-size: 11px; font-weight: 800; }}
  .controls {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
  button {{
    appearance: none; border: 1px solid var(--border); background: #151e32; color: var(--text);
    padding: 7px 13px; border-radius: 10px; font-size: 13px; font-weight: 600; cursor: pointer;
    transition: transform 0.12s ease, border-color 0.15s ease, background 0.15s ease;
  }}
  button:hover {{ border-color: var(--cyan); background: #1a2640; }}
  button.primary {{ background: linear-gradient(135deg, var(--cyan), #818cf8); color: #060913; border: none; }}
  button.active-mode {{ border-color: var(--cyan); box-shadow: 0 0 0 1px var(--cyan); }}
  main {{ max-width: 1120px; margin: 0 auto; padding: 26px 20px 64px; }}
  .story-nav {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }}
  .dots {{ display: flex; gap: 6px; }}
  .dot {{ width: 9px; height: 9px; border-radius: 999px; background: rgba(148,163,184,0.28); cursor: pointer; border: none; padding: 0; }}
  .dot.on {{ width: 26px; background: linear-gradient(90deg, var(--cyan), var(--violet)); }}
  .deck.story-mode .card {{ display: none; min-height: 430px; }}
  .deck.story-mode .card.active {{ display: flex; flex-direction: column; justify-content: space-between; animation: pop 0.25s ease-out; }}
  .deck.bento-mode {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(330px, 1fr)); gap: 18px; }}
  .deck.bento-mode .span-2 {{ grid-column: 1 / -1; }}
  .deck.bento-mode ~ .story-nav {{ display: none; }}
  @keyframes pop {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: translateY(0); }} }}
  .card {{
    background: linear-gradient(160deg, rgba(16, 23, 39, 0.96), rgba(11, 16, 29, 0.98));
    border: 1px solid var(--border);
    border-radius: 22px;
    padding: 28px;
    box-shadow: 0 18px 45px rgba(0, 0, 0, 0.35);
  }}
  .hero {{
    background: radial-gradient(circle at 80% 15%, rgba(168,85,247,0.28), transparent 46%),
                radial-gradient(circle at 12% 88%, rgba(34,211,238,0.22), transparent 44%),
                linear-gradient(155deg, #10192e, #0a101f);
  }}
  .eyebrow {{ font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; color: var(--cyan); margin-bottom: 8px; }}
  h1, h2 {{ margin: 0 0 10px; letter-spacing: -0.025em; }}
  h1 {{ font-size: clamp(28px, 4.2vw, 44px); line-height: 1.1; }}
  h2 {{ font-size: clamp(22px, 2.8vw, 28px); }}
  .muted {{ color: var(--muted); font-size: 14px; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 14px; margin-top: 22px; }}
  .kpi {{ background: rgba(15, 23, 42, 0.78); border: 1px solid var(--border); border-radius: 14px; padding: 15px; }}
  .kpi-val {{ font-size: 28px; font-weight: 800; letter-spacing: -0.02em; }}
  .kpi-lbl {{ font-size: 12px; color: var(--muted); margin-top: 2px; }}
  .bar-row {{ margin-bottom: 12px; }}
  .bar-head {{ display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 5px; }}
  .track {{ height: 9px; border-radius: 999px; background: rgba(148,163,184,0.14); overflow: hidden; }}
  .fill {{ height: 100%; border-radius: 999px; }}
  .c-teal {{ background: linear-gradient(90deg, var(--cyan), #38bdf8); }}
  .c-violet {{ background: linear-gradient(90deg, var(--violet), #ec4899); }}
  .chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }}
  .chip {{ background: rgba(34,211,238,0.10); border: 1px solid rgba(34,211,238,0.28); color: #e0f2fe; padding: 5px 11px; border-radius: 999px; font-size: 12px; font-weight: 600; }}
  .chip em {{ color: var(--cyan); font-style: normal; margin-left: 4px; }}
  .chart-svg {{ width: 100%; height: auto; display: block; margin-top: 10px; }}
  .split {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; align-items: center; margin-top: 10px; }}
  .gauge-wrap {{ display: flex; align-items: center; gap: 18px; }}
  .stat-line {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px dashed var(--border); font-size: 14px; }}
  .loops-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin-top: 14px; }}
  .loop-card {{ background: rgba(15, 23, 42, 0.72); border: 1px solid var(--border); border-radius: 14px; padding: 14px; }}
  .loop-meta {{ display: flex; justify-content: space-between; font-size: 11px; color: var(--cyan); font-weight: 700; text-transform: uppercase; margin-bottom: 6px; }}
  .loop-title {{ font-weight: 700; font-size: 14px; margin-bottom: 6px; }}
  .loop-last {{ font-size: 12px; color: var(--muted); }}
  .mono {{ font-variant-numeric: tabular-nums; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
  .footer-note {{ text-align: center; color: var(--muted); font-size: 12px; margin-top: 26px; }}
  @media print {{
    .topbar, .story-nav {{ display: none !important; }}
    .deck.story-mode {{ display: block !important; }}
    .deck.story-mode .card {{ display: block !important; margin-bottom: 16px; break-inside: avoid; }}
    body {{ background: #070b14 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  }}
</style>
</head>
<body>
<header class="topbar">
  <div class="brand">
    <span class="badge">AI WRAPPED v{e(summary['version'])}</span>
    <span>100% Offline • {e(span_label)}</span>
  </div>
  <div class="controls">
    <button id="btn-story" class="active-mode" onclick="setMode('story')">Story Slides</button>
    <button id="btn-bento" onclick="setMode('bento')">Bento Overview</button>
    <button id="btn-copy" class="primary" onclick="copyShare()">Copy Share Post</button>
    <button onclick="window.print()">Save PDF</button>
  </div>
</header>

<main>
  <div id="story-nav" class="story-nav">
    <button onclick="step(-1)">← Previous</button>
    <div id="dots" class="dots"></div>
    <button onclick="step(1)">Next →</button>
  </div>

  <div id="deck" class="deck story-mode">
    <section class="card hero span-2 active" data-slide="0">
      <div>
        <div class="eyebrow">01 / YOUR AI ARCHETYPE</div>
        <h1>{e(arch['name'])}</h1>
        <p class="muted" style="font-size:17px; max-width:660px;">{e(arch['tagline'])}</p>
      </div>
      <div class="kpi-grid">
        <div class="kpi"><div class="kpi-val">{ov['conversations']:,}</div><div class="kpi-lbl">Total Conversations</div></div>
        <div class="kpi"><div class="kpi-val">{ov['user_turns']:,}</div><div class="kpi-lbl">Prompts You Sent</div></div>
        <div class="kpi"><div class="kpi-val">{ov['user_words']:,}</div><div class="kpi-lbl">Words You Wrote</div></div>
        <div class="kpi"><div class="kpi-val">{ov['longest_streak_days']}d</div><div class="kpi-lbl">Longest Active Streak</div></div>
      </div>
    </section>

    <section class="card" data-slide="1">
      <div>
        <div class="eyebrow">02 / SHEER VOLUME</div>
        <h2>You wrote {e(ov['novel_comparison'])}</h2>
        <p class="muted">Across {ov['active_days']} active days, your prompts and AI replies totaled ~{ov['estimated_tokens']:,} tokens.</p>
        {monthly_svg}
      </div>
      <div class="kpi-grid">
        <div class="kpi"><div class="kpi-val">{ov['assistant_words']:,}</div><div class="kpi-lbl">AI Words Generated</div></div>
        <div class="kpi"><div class="kpi-val">{ov['avg_turns_per_chat']}</div><div class="kpi-lbl">Avg Messages / Chat</div></div>
        <div class="kpi"><div class="kpi-val">{e(str(ov['peak_day'] or '—'))}</div><div class="kpi-lbl">Busiest Day ({ov['peak_day_turns']} prompts)</div></div>
      </div>
    </section>

    <section class="card" data-slide="2">
      <div>
        <div class="eyebrow">03 / CLOCK RHYTHM</div>
        <h2>Peak flow hits at {_format_hour_12(rhythm['peak_hour'])} UTC</h2>
        <p class="muted">Purple bars mark 10 PM–4 AM night-owl sessions ({rhythm['night_owl_pct']}% of all prompts, including {rhythm['two_am_rabbit_holes']} between 2 AM and 5 AM).</p>
        {hours_svg}
      </div>
      <div class="stat-line"><span>Longest single marathon thread</span><strong>{ov['longest_chat_turns']} turns — {e(ov['longest_chat_title'])}</strong></div>
    </section>

    <section class="card" data-slide="3">
      <div>
        <div class="eyebrow">04 / WHAT YOU OBSESSED OVER</div>
        <h2>Top Domains & Signature Keywords</h2>
        {domain_rows}
      </div>
      <div>
        <div class="muted" style="margin-top:10px;">Most repeated words in your prompts</div>
        <div class="chips">{kw_chips}</div>
      </div>
    </section>

    <section class="card" data-slide="4">
      <div>
        <div class="eyebrow">05 / YOUR AI STACK</div>
        <h2>Platform & Model Distribution</h2>
        {plat_rows}
      </div>
      <div>
        <div class="muted" style="margin-top:10px;">Models observed</div>
        <div class="chips">{model_chips or '<span class="muted">Model slugs not tagged in export</span>'}</div>
      </div>
    </section>

    <section class="card" data-slide="5">
      <div>
        <div class="eyebrow">06 / INTERACTION MIRROR</div>
        <h2>{e(tone['politeness_verdict'])}</h2>
        <div class="split">
          <div class="gauge-wrap">
            <svg width="110" height="110" viewBox="0 0 110 110" role="img" aria-label="Politeness Score {tone['politeness_score']} out of 100">
              <circle cx="55" cy="55" r="44" stroke="rgba(148,163,184,0.2)" stroke-width="11" fill="none"/>
              <circle cx="55" cy="55" r="44" stroke="#22d3ee" stroke-width="11" fill="none"
                      stroke-dasharray="{dash} {round(circ, 1)}" stroke-linecap="round" transform="rotate(-90 55 55)"/>
              <text x="55" y="61" text-anchor="middle" fill="#f8fafc" font-size="22" font-weight="800">{tone['politeness_score']}</text>
            </svg>
            <div>
              <div style="font-weight:700;">Politeness Meter</div>
              <div class="muted">{tone['polite_hits']} polite prompts vs {tone['urgent_hits']} urgent bursts</div>
            </div>
          </div>
          <div>
            <div style="font-weight:700; margin-bottom:6px;">AI Clichés You Survived ({tone['sycophancy_total']} total)</div>
            {cliche_rows}
          </div>
        </div>
      </div>
    </section>

    <section class="card span-2" data-slide="6">
      <div>
        <div class="eyebrow">07 / BURIED GOLD</div>
        <h2>Unfinished Ideas & Multi-Turn Threads Worth Revisiting</h2>
        <p class="muted">Actionable deep-dives extracted locally and included in <code>BRAIN_PORTABLE.md</code> for seamless migration.</p>
        <div class="loops-grid">{project_cards}</div>
      </div>
    </section>
  </div>

  <div class="footer-note">
    Processed 100% locally with <strong>codesphere-u/ai-wrapped</strong> • Zero data left your machine • Keys & emails automatically redacted
  </div>
</main>

<script>
  const SHARE_TEXT = {safe_json_share};
  const slides = Array.from(document.querySelectorAll('#deck .card'));
  const dotsEl = document.getElementById('dots');
  let cur = 0;

  slides.forEach((_, i) => {{
    const b = document.createElement('button');
    b.className = 'dot' + (i === 0 ? ' on' : '');
    b.setAttribute('aria-label', 'Slide ' + (i + 1));
    b.onclick = () => go(i);
    dotsEl.appendChild(b);
  }});

  function go(idx) {{
    cur = (idx + slides.length) % slides.length;
    slides.forEach((s, i) => s.classList.toggle('active', i === cur));
    Array.from(dotsEl.children).forEach((d, i) => d.classList.toggle('on', i === cur));
  }}

  function step(delta) {{ go(cur + delta); }}

  function setMode(mode) {{
    const deck = document.getElementById('deck');
    const nav = document.getElementById('story-nav');
    deck.classList.toggle('story-mode', mode === 'story');
    deck.classList.toggle('bento-mode', mode === 'bento');
    nav.style.display = mode === 'bento' ? 'none' : 'flex';
    document.getElementById('btn-story').classList.toggle('active-mode', mode === 'story');
    document.getElementById('btn-bento').classList.toggle('active-mode', mode === 'bento');
  }}

  async function copyShare() {{
    const btn = document.getElementById('btn-copy');
    try {{
      await navigator.clipboard.writeText(SHARE_TEXT);
      btn.textContent = 'Copied!';
      setTimeout(() => btn.textContent = 'Copy Share Post', 1800);
    }} catch {{
      window.prompt('Copy your AI Wrapped post:', SHARE_TEXT);
    }}
  }}

  document.addEventListener('keydown', (e) => {{
    if (document.getElementById('deck').classList.contains('story-mode')) {{
      if (e.key === 'ArrowRight') step(1);
      if (e.key === 'ArrowLeft') step(-1);
    }}
  }});
</script>
</body>
</html>
"""


def format_terminal_report(summary: dict[str, Any], html_path: Path, brain_path: Path, json_path: Path) -> str:
    ov = summary["overview"]
    arch = summary["archetype"]
    tone = summary["tone"]
    rhythm = summary["rhythm"]
    platforms = ", ".join(f"{p['name']} ({p['conversations']})" for p in summary["platforms"]) or "None"
    top_doms = ", ".join(d["name"] for d in summary["domains"][:3]) or "General"
    lines = [
        f"AI Wrapped v{summary['version']} — Offline History & Portable Brain Report",
        f"Archetype: {arch['name']} — {arch['tagline']}",
        f"Stats:     {ov['conversations']:,} chats | {ov['user_turns']:,} prompts | {ov['user_words']:,} words ({ov['novel_comparison']})",
        f"Rhythm:    Peak {_format_hour_12(rhythm['peak_hour'])} UTC | Streak: {ov['longest_streak_days']}d | 2-5 AM rabbit holes: {rhythm['two_am_rabbit_holes']}",
        f"Platforms: {platforms}",
        f"Themes:    {top_doms}",
        f"Tone:      Politeness {tone['politeness_score']}/100 ({tone['politeness_verdict']}) | AI cliches survived: {tone['sycophancy_total']}",
        "Outputs:",
        f"  Wrapped HTML:   {html_path}",
        f"  Portable Brain: {brain_path}",
        f"  JSON Summary:   {json_path}",
    ]
    return "\n".join(lines)


def _is_unsafe_broad_root(target: Path) -> bool:
    resolved = target.resolve()
    return resolved == resolved.parent or resolved == Path.home().resolve()


def _auto_discover_exports() -> Path | None:
    downloads = Path.home() / "Downloads"
    if not downloads.is_dir():
        return None
    patterns = ("*chatgpt*export*.zip", "*claude*export*.zip", "*takeout*.zip", "*conversations*.json")
    matches: list[Path] = []
    for pat in patterns:
        matches.extend(downloads.glob(pat))
    if not matches:
        return None
    return max(matches, key=lambda p: p.stat().st_mtime)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ai-wrapped",
        description="100% offline ChatGPT, Claude & Gemini Wrapped story + Portable Brain generator.",
    )
    p.add_argument(
        "target",
        nargs="?",
        default=None,
        help="Path to ChatGPT/Claude/Gemini export .zip, conversations.json, .jsonl, or folder",
    )
    p.add_argument("--demo", action="store_true", help="Generate an instant preview using the built-in multi-AI sample")
    p.add_argument("--auto", action="store_true", help="Auto-detect the newest AI export ZIP/JSON in ~/Downloads")
    p.add_argument("--include-agents", action="store_true", help="Also include local ~/.claude/projects and ~/.codex/sessions")
    p.add_argument("--year", type=int, default=None, help="Filter metrics to a specific calendar year (e.g. 2026)")
    p.add_argument("--output-dir", type=Path, default=Path("ai-wrapped-out"), help="Output directory (default: ./ai-wrapped-out)")
    p.add_argument("--json", action="store_true", help="Print full JSON summary to stdout")
    p.add_argument("--allow-home", action="store_true", help="Allow scanning the home directory or filesystem root")
    p.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    convs: list[Conversation] = []
    sources: list[str] = []

    if args.demo:
        convs, sources = build_demo_conversations()
    elif args.target is not None:
        target = Path(args.target)
        if not target.exists():
            print(f"ai-wrapped: path does not exist: {target}", file=sys.stderr)
            return 2
        if target.is_dir() and not args.allow_home and _is_unsafe_broad_root(target):
            print(
                f"ai-wrapped: refusing to scan broad directory `{target.resolve()}` "
                "(pass your export .zip/file, a project/export folder, `--auto`, `--demo`, or `--allow-home`).",
                file=sys.stderr,
            )
            return 2
        convs, sources = load_conversations_from_target(target, include_agents=args.include_agents)
    elif args.auto:
        discovered = _auto_discover_exports()
        if discovered is not None:
            convs, sources = load_conversations_from_target(discovered, include_agents=args.include_agents)
        elif args.include_agents:
            convs, sources = load_conversations_from_target(Path.home() / ".claude", include_agents=True)
        else:
            print(
                "ai-wrapped: no ChatGPT/Claude/Gemini export found in ~/Downloads "
                "(pass a file path or run `ai-wrapped --demo` for an instant preview).",
                file=sys.stderr,
            )
            return 2
    elif args.include_agents:
        home = Path.home()
        for agent_dir in (home / ".claude" / "projects", home / ".codex" / "sessions"):
            if agent_dir.is_dir():
                c_part, s_part = load_conversations_from_target(agent_dir, include_agents=False)
                convs.extend(c_part)
                sources.extend(s_part)
    else:
        print(
            "ai-wrapped: pass an export path (e.g. `ai-wrapped ~/Downloads/export.zip`), "
            "`--auto`, or `--demo` to preview immediately.",
            file=sys.stderr,
        )
        return 2

    if not convs:
        print(
            "ai-wrapped: no supported AI conversations found in the provided input. "
            "Supported: ChatGPT ZIP/conversations.json, Claude ZIP/conversations.json, Gemini Takeout JSON/HTML, JSONL.",
            file=sys.stderr,
        )
        return 1

    summary = analyze_conversations(convs, sources, year=args.year)
    if summary.get("empty"):
        print(f"ai-wrapped: no conversations matched `--year {args.year}`.", file=sys.stderr)
        return 1

    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / "ai-wrapped.html"
    brain_path = out_dir / "BRAIN_PORTABLE.md"
    json_path = out_dir / "wrapped-summary.json"

    html_path.write_text(render_html(summary), encoding="utf-8")
    brain_path.write_text(render_portable_brain(summary), encoding="utf-8")
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(format_terminal_report(summary, html_path, brain_path, json_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
