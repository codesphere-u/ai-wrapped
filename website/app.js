(function () {
  "use strict";

  function esc(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function showToast(msg) {
    var toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add("visible");
    window.clearTimeout(showToast._timer);
    showToast._timer = window.setTimeout(function () {
      toast.classList.remove("visible");
    }, 2100);
  }

  function copyText(text, label) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(
        function () { showToast((label || "Copied") + " to clipboard"); },
        function () { fallbackCopy(text, label); }
      );
    } else {
      fallbackCopy(text, label);
    }
  }

  function fallbackCopy(text, label) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    var ok = false;
    try {
      ok = document.execCommand("copy");
    } catch (err) {
      showToast("Copy unavailable: " + (err && err.message ? err.message : "clipboard blocked"));
    }
    document.body.removeChild(ta);
    if (ok) {
      showToast((label || "Copied") + " to clipboard");
    } else {
      showToast("Select and copy the snippet manually");
    }
  }

  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest("[data-copy-target]");
    if (!btn) return;
    var el = document.getElementById(btn.getAttribute("data-copy-target"));
    if (el) copyText(el.textContent.trim(), "Command copied");
  });

  function initHomePage() {
    var copyBtn = document.getElementById("cta-copy-btn");
    var capEl = document.getElementById("cta-caption-text");
    var popBtn = document.getElementById("cta-popover-toggle");
    var popEl = document.getElementById("cta-popover");
    var popCode = document.getElementById("cta-pop-code");
    var popCopy = document.getElementById("cta-pop-copy");

    if (copyBtn && capEl) {
      copyBtn.addEventListener("click", function () {
        copyText(capEl.textContent.trim(), "Demo command copied");
      });
    }

    if (popBtn && popEl) {
      popBtn.addEventListener("click", function (ev) {
        ev.stopPropagation();
        var open = !popEl.classList.contains("open");
        popEl.classList.toggle("open", open);
        popBtn.setAttribute("aria-expanded", String(open));
      });
      document.addEventListener("click", function (ev) {
        if (!popEl.contains(ev.target) && ev.target !== popBtn) {
          popEl.classList.remove("open");
          popBtn.setAttribute("aria-expanded", "false");
        }
      });
    }

    document.querySelectorAll(".pop-tab").forEach(function (tab) {
      tab.addEventListener("click", function () {
        document.querySelectorAll(".pop-tab").forEach(function (t) { t.classList.remove("active"); });
        tab.classList.add("active");
        var cmd = tab.getAttribute("data-cmd") || "";
        if (popCode) popCode.textContent = cmd;
        if (capEl) capEl.textContent = cmd;
      });
    });

    if (popCopy && popCode) {
      popCopy.addEventListener("click", function () {
        copyText(popCode.textContent.trim(), "Preset command copied");
      });
    }

    var previewBody = document.getElementById("home-preview-body");
    if (!previewBody) return;

    var homeTabs = {
      story: {
        stats: [
          ["Archetype", "Midnight Polymath"],
          ["Peak Clock", "11 PM UTC"],
          ["Politeness", "80 / 100"],
          ["AI Clichés", "37 survived"]
        ],
        note: "Observed from running ai-wrapped --demo across 20 multi-platform sample chats.",
        lines: [
          ["Platform Mix", "ChatGPT (8), Claude (7), Gemini (5) · Longest streak: 9 days", ""],
          ["Unfinished Project Resurfaced", "6-Day Kyoto & Naoshima Autumn Itinerary · Build Local Recipe MVP", ""],
          ["Top Formatting Cues", "Scannable bullets (4x), comparison tables (3x), plain English (2x)", ""]
        ]
      },
      brain: {
        stats: [
          ["Output File", "BRAIN_PORTABLE.md"],
          ["Target Models", "Claude / GPT / Gem"],
          ["Open Loops", "5 detected"],
          ["Cloud Uploads", "0 bytes"]
        ],
        note: "Paste into Claude Projects, ChatGPT Memory, Gemini Gems, or AGENTS.md.",
        lines: [
          ["How I Like Responses Formatted", "Likes scannable bullet points and step checklists; prefers plain-English tradeoffs.", ""],
          ["Standing Guardrails", "Skip filler praise (you received 'Certainly / Absolutely!' 37 times).", "warn-border"],
          ["Transfer Time", "Move years of context across assistants in under 10 seconds.", ""]
        ]
      },
      privacy: {
        stats: [
          ["Redactors", "11 patterns"],
          ["ZIP Limit", "200 MB / entry"],
          ["Network Calls", "0 (Stdlib Only)"],
          ["XSS Escaping", "Strict Quote"]
        ],
        note: "Secrets and PII are masked BEFORE keyword extraction and HTML rendering.",
        lines: [
          ["Token Masking", "sk-proj-... -> [redacted-api-key] · ghp_... -> [redacted-token]", ""],
          ["Identity Scrubbing", "user@domain.com -> [redacted-email] · JWTs & Bearer tokens stripped", ""],
          ["Broad-Root Guard", "Refuses scanning ~ or / unless --allow-home is passed explicitly.", ""]
        ]
      }
    };

    function renderHomePreview(key) {
      var data = homeTabs[key] || homeTabs.story;
      var html = '<div class="score-row">';
      data.stats.forEach(function (item) {
        html += '<div class="score-cell"><span>' + esc(item[0]) + "</span><strong>" + esc(item[1]) + "</strong></div>";
      });
      html += '</div><div class="diag-note">' + esc(data.note) + '</div><div class="rw-list">';
      data.lines.forEach(function (ln) {
        html += '<div class="rw-item ' + esc(ln[2]) + '"><span>' + esc(ln[0]) + "</span><p>" + esc(ln[1]) + "</p></div>";
      });
      html += "</div>";
      previewBody.innerHTML = html;
    }

    document.querySelectorAll("[data-home-tab]").forEach(function (tab) {
      tab.addEventListener("click", function () {
        document.querySelectorAll("[data-home-tab]").forEach(function (t) { t.classList.remove("active"); });
        tab.classList.add("active");
        renderHomePreview(tab.getAttribute("data-home-tab"));
      });
    });

    renderHomePreview("story");
  }

  function initStudioPage() {
    var shieldInput = document.getElementById("shield-input");
    if (!shieldInput) return;

    document.querySelectorAll("[data-studio-tab]").forEach(function (tab) {
      tab.addEventListener("click", function () {
        var target = tab.getAttribute("data-studio-tab");
        document.querySelectorAll("[data-studio-tab]").forEach(function (t) { t.classList.remove("active"); });
        document.querySelectorAll(".studio-panel").forEach(function (p) { p.classList.remove("active"); });
        tab.classList.add("active");
        var panel = document.getElementById("panel-" + target);
        if (panel) panel.classList.add("active");
      });
    });

    var presets = {
      secrets:
        "User: Please debug why sk-proj-demo9876543210abcd fails for jane.doe@example.com with ghp_secret1234567890abcd.\n" +
        "Assistant: Great question! I'd be happy to check Authorization: Bearer eyJhbGciOi.LetS123456.sig123456!\n" +
        "User: Thanks, keep it concise in bullet points please.",
      cliches:
        "User: Could you explain Kyoto rain backups in plain English please?\n" +
        "Assistant: Certainly! What a thoughtful question. Let's break this down into a comprehensive guide exploring multifaceted museums. It is important to note I'd be happy to help!",
      clean:
        "User: Please summarize our pantry inventory schema in a short comparison table. Thank you!\n" +
        "Assistant: Here is the minimal 3-table SQLite schema and local backup checklist."
    };

    var redactors = [
      [/\bsk-(?:proj-|ant-|live-|test-)?[A-Za-z0-9_-]{10,}\b/g, "[redacted-api-key]"],
      [/\b(?:ghp|gho|ghu|ghs|github_pat|hf|gsk|npm)_[A-Za-z0-9_]{12,}\b/g, "[redacted-token]"],
      [/\bAIza[0-9A-Za-z_-]{16,}\b/g, "[redacted-google-key]"],
      [/\bBearer\s+[A-Za-z0-9._~+/-]{12,}=*/gi, "Bearer [redacted]"],
      [/\beyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\b/g, "[redacted-jwt]"],
      [/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g, "[redacted-email]"],
      [/\b\d{3}-\d{2}-\d{4}\b/g, "[redacted-ssn]"]
    ];
    var cliches = [
      /\b(?:great|excellent|wonderful|fantastic|thoughtful)\s+question\b/gi,
      /\b(?:certainly|absolutely|of course|sure thing)[!.,]/gi,
      /\bi['’]?(?:d| would)\s+(?:be\s+)?(?:happy|glad|delighted)\s+to\b/gi,
      /\blet['’]?s\s+(?:break\s+this\s+down|dive\s+in|explore)\b/gi,
      /\bdelv(?:e|es|ing)\b/gi,
      /\b(?:multifaceted|testament|ever-evolving)\b/gi,
      /\bit\s+is\s+(?:important|worth)\s+(?:to\s+note|noting)\b/gi,
      /\bcomprehensive\s+(?:guide|overview|breakdown)\b/gi
    ];

    function runShieldAudit() {
      var raw = shieldInput.value;
      var masked = raw;
      var secretHits = 0;
      redactors.forEach(function (pair) {
        masked = masked.replace(pair[0], function () {
          secretHits += 1;
          return pair[1];
        });
      });

      var clicheHits = 0;
      cliches.forEach(function (rx) {
        var m = raw.match(rx);
        if (m) clicheHits += m.length;
      });

      var politeHits = (raw.match(/\b(?:please|thank you|thanks|kindly|could you|appreciate)\b/gi) || []).length;
      var urgentHits = (raw.match(/(?:!{2,}|\b(?:asap|urgent|broken|wrong again)\b)/gi) || []).length;

      document.getElementById("sh-masked-count").textContent = String(secretHits);
      document.getElementById("sh-cliche-count").textContent = String(clicheHits);
      document.getElementById("sh-polite-count").textContent = String(politeHits);
      document.getElementById("sh-urgent-count").textContent = String(urgentHits);
      document.getElementById("sh-redacted-out").textContent = masked || "(Paste snippet above)";
    }

    document.querySelectorAll("[data-shield-preset]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll("[data-shield-preset]").forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        shieldInput.value = presets[btn.getAttribute("data-shield-preset")] || presets.secrets;
        runShieldAudit();
      });
    });
    shieldInput.addEventListener("input", runShieldAudit);
    shieldInput.value = presets.secrets;
    runShieldAudit();

    /* Tab 2: Archetype & Novel Length */
    function updateArchetype() {
      var night = parseInt(document.getElementById("ar-night").value, 10) || 0;
      var polite = parseInt(document.getElementById("ar-politeness").value, 10) || 0;
      var platforms = parseInt(document.getElementById("ar-platforms").value, 10) || 1;
      var words = parseInt(document.getElementById("ar-words").value, 10) || 1000;

      document.getElementById("ar-night-val").textContent = night + "%";
      document.getElementById("ar-polite-val").textContent = String(polite);

      var name = "The Everyday Explorer";
      var tagline = "Uses AI as a true second brain—balancing work, learning, trips, and real life cleanly.";
      if (night >= 28) {
        name = "The Midnight Polymath";
        tagline = "Best ideas arrive after 10 PM—shipping side projects, deep questions, and 2 AM rabbit holes.";
      } else if (polite >= 78) {
        name = "The Polite Perfectionist";
        tagline = "Says 'please' and 'thank you' to silicon every single session—future AI overlords will promote you.";
      } else if (platforms >= 3) {
        name = "The Multi-Model Strategist";
        tagline = "Switches cleanly across ChatGPT, Claude, and Gemini to match every problem to the sharpest model.";
      }

      var novels = [
        ["The Old Man and the Sea", 27000],
        ["The Great Gatsby", 47000],
        ["1984", 89000],
        ["Dune", 188000],
        ["War and Peace", 587000]
      ];
      var chosenNovel = novels[0];
      novels.forEach(function (nv) {
        if (words >= nv[1] * 0.75) chosenNovel = nv;
      });
      var ratio = (words / chosenNovel[1]).toFixed(1) + "x " + chosenNovel[0];
      var tone = polite >= 75 ? "AI Overlords Spare You" : (polite >= 35 ? "Crisp Strategist" : "No-Mercy Deadline Mode");

      document.getElementById("ar-title").textContent = name;
      document.getElementById("ar-tagline").textContent = tagline;
      document.getElementById("ar-novel").textContent = ratio;
      document.getElementById("ar-tone").textContent = tone;
    }

    ["ar-night", "ar-politeness", "ar-platforms", "ar-words"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener("input", updateArchetype);
    });
    updateArchetype();

    /* Tab 3: BRAIN_PORTABLE.md Builder */
    function updateBrain() {
      var target = document.getElementById("br-target").value;
      var style = document.getElementById("br-style").value;
      var styleRule = {
        concise: "- Likes scannable bullet points and Markdown comparison tables.\n- Prefers concise answers without filler preambles.",
        steps: "- Appreciates numbered step-by-step walkthroughs.\n- Learns fastest with concrete examples before abstract theory.",
        critical: "- Flag tradeoffs, hidden assumptions, and missing edge cases upfront.\n- Skip flattery; give direct technical critique."
      }[style];

      var md = "# Portable AI Brain & Personal Context Pack\n\n" +
        "> Target Workspace: **" + target + "** (Generated 100% offline by AI Wrapped v1.1.0)\n\n" +
        "## 1. Interaction & Style Rules\n" + styleRule + "\n\n" +
        "## 2. Primary Focus Areas\n" +
        "- Coding & Tech (Python AST tooling, SQL schemas, CLI automation)\n" +
        "- Writing & Strategy (Clear documentation, crisp changelogs)\n\n" +
        "## 3. Standing Guardrails\n" +
        "- Skip canned filler ('Great question!', 'Certainly!', 'I would be happy to').\n" +
        "- Keep sensitive API keys, emails, and tokens out of echoed summaries.";
      document.getElementById("br-output").textContent = md;
    }

    ["br-target", "br-style"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener("change", updateBrain);
    });
    var copyBrain = document.getElementById("copy-brain-btn");
    if (copyBrain) {
      copyBrain.addEventListener("click", function () {
        copyText(document.getElementById("br-output").textContent, "BRAIN_PORTABLE.md copied");
      });
    }
    updateBrain();
  }

  function initRulesPage() {
    var search = document.getElementById("rules-search");
    var category = document.getElementById("rules-category");
    var tbody = document.getElementById("rules-tbody");
    var countEl = document.getElementById("rules-count");
    var resetBtn = document.getElementById("rules-reset");
    if (!tbody || !search || !category) return;

    var rows = Array.prototype.slice.call(tbody.querySelectorAll("tr"));
    function applyFilter() {
      var q = search.value.trim().toLowerCase();
      var cat = category.value;
      var visible = 0;
      rows.forEach(function (row) {
        var matchCat = cat === "all" || row.getAttribute("data-cat") === cat;
        var matchText = !q || row.textContent.toLowerCase().indexOf(q) !== -1;
        var show = matchCat && matchText;
        row.style.display = show ? "" : "none";
        if (show) visible += 1;
      });
      if (countEl) countEl.textContent = "Showing " + visible + " of " + rows.length + " rules";
    }

    search.addEventListener("input", applyFilter);
    category.addEventListener("change", applyFilter);
    if (resetBtn) {
      resetBtn.addEventListener("click", function () {
        search.value = "";
        category.value = "all";
        applyFilter();
      });
    }
  }

  function initDocsPage() {
    var panels = Array.prototype.slice.call(document.querySelectorAll("[data-doc-panel]"));
    if (!panels.length) return;

    var order = panels.map(function (p) { return p.getAttribute("data-doc-panel"); });
    var titles = {
      install: "Install & Demo",
      exports: "Export Your Data",
      "cli-flags": "CLI Flags",
      "portable-brain": "Portable Brain",
      privacy: "Privacy Shield"
    };

    var prevBtn = document.getElementById("doc-prev-btn");
    var prevLabel = document.getElementById("doc-prev-label");
    var nextBtn = document.getElementById("doc-next-btn");
    var nextLabel = document.getElementById("doc-next-label");
    var currentIdx = 0;

    function activateSection(id, scrollTop) {
      var idx = order.indexOf(id);
      if (idx === -1) idx = 0;
      currentIdx = idx;
      var activeId = order[idx];

      panels.forEach(function (p) {
        p.hidden = p.getAttribute("data-doc-panel") !== activeId;
      });
      document.querySelectorAll("[data-doc-target]").forEach(function (btn) {
        btn.classList.toggle("active", btn.getAttribute("data-doc-target") === activeId);
      });
      document.querySelectorAll("[data-subrail-for]").forEach(function (sr) {
        sr.classList.toggle("open", sr.getAttribute("data-subrail-for") === activeId);
      });

      if (prevBtn && prevLabel) {
        if (idx > 0) {
          prevBtn.hidden = false;
          prevLabel.textContent = titles[order[idx - 1]] || order[idx - 1];
        } else {
          prevBtn.hidden = true;
        }
      }
      if (nextBtn && nextLabel) {
        if (idx < order.length - 1) {
          nextBtn.hidden = false;
          nextLabel.textContent = titles[order[idx + 1]] || order[idx + 1];
        } else {
          nextBtn.hidden = true;
        }
      }
      if (scrollTop) window.scrollTo({ top: 0, behavior: "smooth" });
    }

    document.querySelectorAll("[data-doc-target]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        activateSection(btn.getAttribute("data-doc-target"), true);
      });
    });

    if (prevBtn) prevBtn.addEventListener("click", function () { if (currentIdx > 0) activateSection(order[currentIdx - 1], true); });
    if (nextBtn) nextBtn.addEventListener("click", function () { if (currentIdx < order.length - 1) activateSection(order[currentIdx + 1], true); });

    var installCmds = {
      uvx: "uvx --from git+https://github.com/codesphere-u/ai-wrapped ai-wrapped --demo",
      skill: "npx skills add codesphere-u/ai-wrapped",
      pip: "pip install git+https://github.com/codesphere-u/ai-wrapped"
    };
    var docsInstallPre = document.getElementById("docs-install-pre");
    document.querySelectorAll("[data-install-tab]").forEach(function (tab) {
      tab.addEventListener("click", function () {
        document.querySelectorAll("[data-install-tab]").forEach(function (t) { t.classList.remove("active"); });
        tab.classList.add("active");
        if (docsInstallPre) docsInstallPre.textContent = installCmds[tab.getAttribute("data-install-tab")] || installCmds.uvx;
      });
    });

    document.querySelectorAll(".doc-sub-link").forEach(function (lnk) {
      lnk.addEventListener("click", function () {
        document.querySelectorAll(".doc-sub-link").forEach(function (a) { a.classList.remove("active"); });
        lnk.classList.add("active");
      });
    });

    activateSection("install", false);
  }

  initHomePage();
  initStudioPage();
  initRulesPage();
  initDocsPage();
})();
