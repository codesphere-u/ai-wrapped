from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "skills" / "ai-wrapped" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ai_wrapped  # noqa: E402

WEBSITE = ROOT / "website"


def test_required_website_and_docs_files_exist() -> None:
    expected = [
        WEBSITE / "index.html",
        WEBSITE / "studio.html",
        WEBSITE / "proof.html",
        WEBSITE / "rules.html",
        WEBSITE / "docs.html",
        WEBSITE / "styles.css",
        WEBSITE / "app.js",
        WEBSITE / "favicon.svg",
        WEBSITE / "og-image.svg",
        WEBSITE / "robots.txt",
        WEBSITE / "sitemap.xml",
        WEBSITE / "manifest.webmanifest",
        WEBSITE / "llms.txt",
        WEBSITE / "llms-full.txt",
        WEBSITE / "marketing" / "LAUNCH_PLAYBOOK.md",
        WEBSITE / "marketing" / "PROGRAMMATIC_SEO.md",
        ROOT / "llms.txt",
        ROOT / "llms-full.txt",
        ROOT / "docs" / "GETTING_STARTED.md",
        ROOT / "docs" / "EXPORT_AND_PRIVACY.md",
        ROOT / ".github" / "workflows" / "pages.yml",
    ]
    missing = [str(p.relative_to(ROOT)) for p in expected if not p.is_file()]
    assert not missing, f"Missing required files: {missing}"


def test_website_has_no_pink_palette_and_valid_jsonld() -> None:
    pink_tokens = ("#f472b6", "#ec4899", "#e75480", "#fb7185", "#fda4af", "236, 72, 153")
    for path in list(WEBSITE.glob("*.css")) + list(WEBSITE.glob("*.html")) + list(WEBSITE.glob("*.svg")):
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        for tok in pink_tokens:
            assert tok not in lower, f"Disallowed pink token {tok} in {path.name}"

    for html_file in WEBSITE.glob("*.html"):
        text = html_file.read_text(encoding="utf-8")
        desc_match = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', text)
        assert desc_match, f"Missing meta description in {html_file.name}"
        desc_len = len(desc_match.group(1))
        assert 50 <= desc_len <= 160, f"Description length {desc_len} out of 50-160 range in {html_file.name}"

        scripts = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>',
            text,
            flags=re.DOTALL,
        )
        assert scripts, f"Missing JSON-LD in {html_file.name}"
        for raw in scripts:
            parsed = json.loads(raw)
            assert "@context" in parsed
        for href in re.findall(r'href="([^"#?]+\.(?:html|css|svg|txt|webmanifest))"', text):
            if not href.startswith(("http://", "https://")):
                assert (WEBSITE / href).is_file(), f"Broken local href {href} in {html_file.name}"


def test_version_alignment_across_website_and_package() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    plugin = (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    index_html = (WEBSITE / "index.html").read_text(encoding="utf-8")
    assert ai_wrapped.VERSION == "1.1.0"
    assert 'version = "1.1.0"' in pyproject
    assert "## [1.1.0]" in changelog
    assert '"version": "1.1.0"' in plugin
    assert "v1.1.0" in index_html
