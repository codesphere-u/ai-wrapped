from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "skills" / "ai-wrapped" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ai_wrapped  # noqa: E402


def test_demo_mode_generates_all_outputs(tmp_path: Path) -> None:
    out_dir = tmp_path / "demo-out"
    rc = ai_wrapped.main(["--demo", "--output-dir", str(out_dir)])
    assert rc == 0

    html_file = out_dir / "ai-wrapped.html"
    brain_file = out_dir / "BRAIN_PORTABLE.md"
    json_file = out_dir / "wrapped-summary.json"
    assert html_file.is_file()
    assert brain_file.is_file()
    assert json_file.is_file()

    html_text = html_file.read_text(encoding="utf-8")
    assert "AI WRAPPED" in html_text
    assert "Story Slides" in html_text
    assert "Bento Overview" in html_text

    summary = json.loads(json_file.read_text(encoding="utf-8"))
    assert summary["overview"]["conversations"] == 20
    assert summary["overview"]["longest_streak_days"] >= 9
    assert len(summary["platforms"]) == 3
    assert summary["tone"]["sycophancy_total"] > 0

    brain_text = brain_file.read_text(encoding="utf-8")
    assert "Portable AI Brain" in brain_text
    assert "Unfinished Loops" in brain_text


def test_multi_platform_zips_and_redaction(tmp_path: Path) -> None:
    # 1. ChatGPT sharded ZIP with regenerated branch, secret key, and XSS attempt
    chatgpt_payload = [
        {
            "id": "cg-1",
            "title": "Launch Plan <script>alert(1)</script> & sk-proj-supersecretkey123456",
            "default_model_slug": "gpt-4o",
            "create_time": 1767315600.0,
            "current_node": "n3",
            "mapping": {
                "root": {"id": "root", "message": None, "parent": None},
                "n1": {
                    "id": "n1",
                    "parent": "root",
                    "message": {
                        "author": {"role": "user"},
                        "create_time": 1767315600.0,
                        "content": {"parts": ["Please help build a weekend recipe app with bullet points for jane@example.com."]},
                    },
                },
                "n2_old": {
                    "id": "n2_old",
                    "parent": "n1",
                    "message": {
                        "author": {"role": "assistant"},
                        "create_time": 1767315610.0,
                        "content": {"parts": ["Ignored abandoned regeneration branch."]},
                    },
                },
                "n2": {
                    "id": "n2",
                    "parent": "n1",
                    "message": {
                        "author": {"role": "assistant"},
                        "create_time": 1767315620.0,
                        "content": {"parts": ["Certainly! Let's break this down step by step."]},
                    },
                },
                "n3": {
                    "id": "n3",
                    "parent": "n2",
                    "message": {
                        "author": {"role": "user"},
                        "create_time": 1767315700.0,
                        "content": {"parts": ["Thanks! Also add my plan to learn Italian."]},
                    },
                },
            },
        }
    ]
    cg_zip = tmp_path / "chatgpt-export.zip"
    with zipfile.ZipFile(cg_zip, "w") as zf:
        zf.writestr("conversations-000.json", json.dumps(chatgpt_payload))
        zf.writestr("../../evil.json", json.dumps(chatgpt_payload))

    # 2. Claude export ZIP
    claude_payload = [
        {
            "uuid": "cl-1",
            "name": "Lease Check",
            "created_at": "2026-01-03T10:00:00Z",
            "chat_messages": [
                {"sender": "human", "created_at": "2026-01-03T10:00:00Z", "content": [{"type": "text", "text": "Please review clause 4 in plain English."}]},
                {"sender": "assistant", "created_at": "2026-01-03T10:01:00Z", "content": [{"type": "text", "text": "Great question! Here is what clause 4 means."}]},
            ],
        }
    ]
    cl_zip = tmp_path / "claude-export.zip"
    with zipfile.ZipFile(cl_zip, "w") as zf:
        zf.writestr("conversations.json", json.dumps(claude_payload))

    # 3. Google Gemini Takeout MyActivity JSON + HTML
    gem_json = [
        {
            "header": "Gemini Apps",
            "title": "Prompted Explain compound interest with a concrete example",
            "time": "2026-01-04T02:15:00Z",
            "safeHtmlItem": [{"html": "<p>I'd be happy to explain compound interest clearly.</p>"}],
        }
    ]
    (tmp_path / "MyActivity.json").write_text(json.dumps(gem_json), encoding="utf-8")

    convs, _ = ai_wrapped.load_conversations_from_target(tmp_path)
    summary = ai_wrapped.analyze_conversations(convs, ["tmp"])

    assert summary["overview"]["conversations"] == 3
    assert summary["overview"]["longest_streak_days"] == 3
    assert summary["rhythm"]["two_am_rabbit_holes"] == 1
    assert {p["name"] for p in summary["platforms"]} == {"ChatGPT", "Claude", "Gemini"}

    # Ensure abandoned branch was NOT included & secrets/XSS are sanitized
    rendered_html = ai_wrapped.render_html(summary)
    assert "sk-proj-supersecretkey123456" not in rendered_html
    assert "[redacted-api-key]" in rendered_html
    assert "jane@example.com" not in rendered_html
    assert "<script>alert(1)</script>" not in rendered_html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered_html


def test_gemini_html_jsonl_markdown_and_year_filter(tmp_path: Path) -> None:
    (tmp_path / "My Activity.html").write_text(
        '<div class="outer-cell"><div class="content-cell">Gemini Apps<br>'
        'Prompted Best banana bread recipe<br>Jan 5, 2025, 3:00:00 PM UTC</div>'
        '<div class="content-cell">Use ripe bananas and brown butter.</div></div>',
        encoding="utf-8",
    )
    (tmp_path / "session.jsonl").write_text(
        json.dumps({"type": "user", "timestamp": "2026-05-01T12:00:00Z", "message": {"role": "user", "content": "Help plan my trip"}}) + "\n"
        + json.dumps({"type": "assistant", "timestamp": "2026-05-01T12:01:00Z", "message": {"role": "assistant", "model": "claude-sonnet-4", "content": [{"type": "text", "text": "Happy to plan it!"}]}}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "notes-chat.md").write_text(
        "You: Give me a short checklist for packing.\n\nAssistant: Passports, chargers, rain shell.\n",
        encoding="utf-8",
    )

    convs, _ = ai_wrapped.load_conversations_from_target(tmp_path)
    assert len(convs) == 3

    only_2025 = ai_wrapped.analyze_conversations(convs, ["tmp"], year=2025)
    assert only_2025["overview"]["conversations"] == 1
    assert only_2025["platforms"][0]["name"] == "Gemini"


def test_broad_root_guard_and_zsh_safe_docs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert ai_wrapped.main([str(tmp_path)]) == 2
    assert "refusing to scan broad directory" in capsys.readouterr().err
    assert ai_wrapped.main(["/"]) == 2

    for doc_path in (REPO_ROOT / "README.md", REPO_ROOT / "skills" / "ai-wrapped" / "SKILL.md"):
        content = doc_path.read_text(encoding="utf-8")
        for match in re.finditer(r"```bash\n(.*?)```", content, flags=re.DOTALL):
            for raw_line in match.group(1).splitlines():
                stripped = raw_line.strip()
                assert not stripped.startswith("#"), f"zsh-unsafe comment in {doc_path.name}: {stripped}"
