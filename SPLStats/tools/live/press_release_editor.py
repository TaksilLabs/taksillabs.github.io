import json
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parents[2]

SEASON_ID = "summer_2026"

DRAFTS_FILE = (
    BASE_DIR
    / "data"
    / "live_season"
    / SEASON_ID
    / "news"
    / "press_release_drafts.json"
)

HOST = "localhost"
PORT = 8782


HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SPL Press Release Editor</title>

  <style>
    :root {
      --bg: #05080c;
      --card: #0c141c;
      --surface: #111c26;
      --line: #244255;
      --text: #f4f4f4;
      --muted: #9fb3c8;
      --accent: #00d1d1;
      --warn: #ffd166;
      --danger: #ff5c5c;
      --good: #5cff9d;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      background:
        radial-gradient(circle at top right, rgba(0, 209, 209, 0.12), transparent 34%),
        var(--bg);
      color: var(--text);
      font-family: Arial, sans-serif;
    }

    header {
      padding: 22px;
      border-bottom: 1px solid var(--line);
      background: rgba(12, 20, 28, 0.94);
      position: sticky;
      top: 0;
      z-index: 10;
    }

    h1 {
      margin: 0 0 14px;
      color: var(--accent);
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }

    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }

    input,
    select,
    textarea,
    button {
      border-radius: 8px;
      border: 1px solid var(--line);
      background: #071018;
      color: var(--text);
      padding: 9px 11px;
      font-size: 0.95rem;
    }

    input,
    textarea {
      width: 100%;
    }

    textarea {
      min-height: 170px;
      resize: vertical;
      line-height: 1.45;
      font-family: Consolas, Monaco, monospace;
    }

    button {
      cursor: pointer;
      font-weight: 700;
    }

    button:hover {
      border-color: var(--accent);
    }

    .save-button {
      background: rgba(92, 255, 157, 0.14);
      border-color: var(--good);
    }

    .main {
      display: grid;
      grid-template-columns: 360px 1fr;
      gap: 18px;
      padding: 18px;
    }

    .sidebar,
    .editor {
      background: rgba(12, 20, 28, 0.88);
      border: 1px solid var(--line);
      border-radius: 14px;
      min-height: 70vh;
    }

    .sidebar {
      overflow: hidden;
    }

    .draft-list {
      max-height: calc(100vh - 200px);
      overflow-y: auto;
    }

    .draft-row {
      padding: 13px 14px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      cursor: pointer;
    }

    .draft-row:hover {
      background: rgba(0, 209, 209, 0.08);
    }

    .draft-row.active {
      background: rgba(0, 209, 209, 0.18);
      border-left: 4px solid var(--accent);
    }

    .draft-row strong {
      display: block;
      margin-bottom: 5px;
    }

    .draft-row small {
      display: block;
      color: var(--muted);
      line-height: 1.35;
    }

    .status-pill {
      display: inline-block;
      margin-top: 7px;
      padding: 3px 7px;
      border-radius: 999px;
      border: 1px solid var(--line);
      font-size: 0.72rem;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .status-draft {
      color: var(--warn);
      border-color: rgba(255, 209, 102, 0.45);
      background: rgba(255, 209, 102, 0.1);
    }

    .status-ready {
      color: var(--good);
      border-color: rgba(92, 255, 157, 0.45);
      background: rgba(92, 255, 157, 0.1);
    }

    .status-published {
      color: var(--accent);
      border-color: rgba(0, 209, 209, 0.45);
      background: rgba(0, 209, 209, 0.1);
    }

    .editor {
      padding: 18px;
    }

    .editor-grid {
      display: grid;
      grid-template-columns: 1fr 180px;
      gap: 12px;
      margin-bottom: 12px;
    }

    .editor label {
      display: flex;
      flex-direction: column;
      gap: 6px;
      color: var(--muted);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 700;
      margin-bottom: 12px;
    }

    .editor input,
    .editor select,
    .editor textarea {
      margin-top: 2px;
    }

    .article-preview {
      margin-top: 16px;
      padding: 16px;
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 12px;
      background: rgba(17, 28, 38, 0.55);
    }

    .article-preview h2 {
      margin: 0 0 8px;
      color: var(--text);
    }

    .article-preview h3 {
      margin: 0 0 14px;
      color: var(--muted);
      font-size: 1rem;
      font-weight: 500;
    }

    .article-preview p {
      line-height: 1.55;
      margin: 0 0 12px;
    }

    .meta-line {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 14px;
      color: var(--muted);
      font-size: 0.82rem;
    }

    .meta-pill {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 8px;
      background: rgba(7, 16, 24, 0.75);
    }

    .empty {
      padding: 30px;
      text-align: center;
      color: var(--muted);
    }

    .status {
      color: var(--muted);
      padding-left: 8px;
    }

    .press-release-quote {
      position: relative;
      overflow: hidden;
      margin: 22px 0;
      padding: 22px 24px;
      border-radius: 18px;
      border: 1px solid var(--quote-color);
      background: rgba(7, 16, 24, 0.92);
      box-shadow: inset 6px 0 0 var(--quote-color);
    }

    .press-release-quote::before {
      content: "“";
      position: absolute;
      right: 14px;
      top: -28px;
      color: rgba(255, 255, 255, 0.08);
      font-size: 8rem;
      font-weight: 900;
      line-height: 1;
      pointer-events: none;
    }

    .press-release-quote blockquote {
      position: relative;
      z-index: 1;
      margin: 0;
      color: var(--text);
      font-size: 1.45rem;
      line-height: 1.35;
      font-weight: 900;
    }

    .press-release-quote figcaption {
      position: relative;
      z-index: 1;
      margin-top: 12px;
      color: var(--muted);
      font-size: 0.82rem;
      font-weight: 800;
      letter-spacing: 0.11em;
      text-transform: uppercase;
    }

    .press-release-quote figcaption::before {
      content: "— ";
      color: var(--quote-color);
    }

    @media (max-width: 980px) {
      .main {
        grid-template-columns: 1fr;
      }

      .draft-list {
        max-height: 300px;
      }

      .editor-grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>

<body>
  <header>
    <h1>Press Release Editor</h1>

    <div class="toolbar">
      <input id="searchInput" type="text" placeholder="Search drafts, teams, players...">

      <select id="statusFilter" onchange="renderDraftList()">
        <option value="all">All Statuses</option>
        <option value="draft">Draft</option>
        <option value="ready">Ready</option>
        <option value="published">Published</option>
      </select>

      <button class="save-button" onclick="saveDrafts()">Save Drafts</button>

      <span id="status" class="status">Loading...</span>
    </div>
  </header>

  <div class="main">
    <aside class="sidebar">
      <div id="draftList" class="draft-list"></div>
    </aside>

    <section id="editor" class="editor">
      <div class="empty">Select a press release draft to edit.</div>
    </section>
  </div>

<script>
let draftData = null;
let drafts = [];
let selectedDraftId = null;
let dirty = false;

function cleanText(value) {
  return String(value || "").trim();
}

function setStatus(message) {
  document.getElementById("status").textContent = message;
}

function markDirty() {
  dirty = true;
  setStatus("Unsaved changes");
}

function escapeAttr(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function makeSlug(value) {
  return cleanText(value)
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function formatDate(value) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

async function loadDrafts() {
  const response = await fetch("/api/drafts");

  if (!response.ok) {
    setStatus("Failed to load press release drafts.");
    return;
  }

  draftData = await response.json();
  drafts = draftData.drafts || [];

  drafts.sort((a, b) => {
    return Date.parse(b.created_at_utc || "") - Date.parse(a.created_at_utc || "");
  });

  setStatus(`Loaded ${drafts.length} drafts`);
  renderDraftList();

  if (drafts.length && !selectedDraftId) {
    selectDraft(drafts[0].draft_id);
  }
}

function draftMatchesSearch(draft, query) {
  if (!query) return true;

  const players = Array.isArray(draft.players)
    ? draft.players.map(player => `${player.player_display_name} ${player.player_id} ${player.slap_id}`).join(" ")
    : "";

  const haystack = [
    draft.headline,
    draft.subheadline,
    draft.slug,
    draft.status,
    draft.team_display_name,
    draft.team_abbreviation,
    draft.division,
    draft.region,
    draft.player_display_name,
    draft.player_id,
    players,
    draft.body_markdown,
    draft.writer_notes
  ].join(" ").toLowerCase();

  return haystack.includes(query.toLowerCase());
}

function renderDraftList() {
  const query = cleanText(document.getElementById("searchInput").value);
  const statusFilter = cleanText(document.getElementById("statusFilter").value).toLowerCase();
  const container = document.getElementById("draftList");

  const filtered = drafts.filter(draft => {
    const status = cleanText(draft.status || "draft").toLowerCase();

    if (statusFilter !== "all" && status !== statusFilter) {
      return false;
    }

    return draftMatchesSearch(draft, query);
  });

  if (!filtered.length) {
    container.innerHTML = `<div class="empty">No matching drafts.</div>`;
    return;
  }

  container.innerHTML = filtered.map(draft => {
    const status = cleanText(draft.status || "draft").toLowerCase();
    const team = cleanText(draft.team_abbreviation || draft.team_display_name || "TBD");
    const date = formatDate(draft.created_at_utc);

    return `
      <div
        class="draft-row ${draft.draft_id === selectedDraftId ? "active" : ""}"
        onclick="selectDraft('${escapeAttr(draft.draft_id)}')"
      >
        <strong>${escapeHtml(draft.headline || "Untitled Draft")}</strong>
        <small>${escapeHtml(team)} · ${escapeHtml(date)}</small>
        <small>${escapeHtml(draft.subheadline || "")}</small>
        <span class="status-pill status-${escapeAttr(status)}">${escapeHtml(status)}</span>
      </div>
    `;
  }).join("");
}

function getSelectedDraft() {
  return drafts.find(draft => draft.draft_id === selectedDraftId) || null;
}

function selectDraft(draftId) {
  selectedDraftId = draftId;
  renderDraftList();
  renderEditor();
}

function updateDraftField(field, value) {
  const draft = getSelectedDraft();
  if (!draft) return;

  draft[field] = value;

  if (field === "headline") {
    const currentSlug = cleanText(draft.slug);
    const oldGeneratedSlug = makeSlug(draft._last_headline || "");

    if (!currentSlug || currentSlug === oldGeneratedSlug) {
      draft.slug = makeSlug(value);
    }

    draft._last_headline = value;
  }

  draft.updated_at_utc = new Date().toISOString();

  markDirty();
  renderDraftList();

  if (field === "headline" || field === "subheadline" || field === "body_markdown") {
    renderPreview();
  }
}

function renderPlayerSummary(draft) {
  const players = Array.isArray(draft.players)
    ? draft.players
    : [];

  if (players.length) {
    return players.map(player => {
      const symbol = cleanText(player.type).toLowerCase() === "add"
        ? "+"
        : cleanText(player.type).toLowerCase() === "remove"
          ? "−"
          : "•";

      const jersey = cleanText(player.jersey_number)
        ? `#${player.jersey_number} `
        : "";

      return `${symbol} ${jersey}${player.player_display_name || player.player_id || "Unknown Player"}`;
    }).join(" · ");
  }

  const jersey = cleanText(draft.jersey_number)
    ? `#${draft.jersey_number} `
    : "";

  if (draft.player_display_name) {
    return `${jersey}${draft.player_display_name}`;
  }

  return "";
}

function isQuoteBlock(lines) {
  if (lines.length < 3) return false;

  const quoteLine = cleanText(lines[0]);
  const colorLine = cleanText(lines[1]);
  const speakerLine = cleanText(lines[2]);

  return quoteLine.startsWith('"')
    && quoteLine.endsWith('"')
    && colorLine.toLowerCase().startsWith("#color:")
    && speakerLine.startsWith("-");
}

function getSafeQuoteColor(value) {
  const raw = cleanText(value)
    .replace(/^#color:/i, "")
    .replace("#", "");

  if (/^[0-9a-f]{6}$/i.test(raw)) {
    return `#${raw}`;
  }

  return "#00d1d1";
}

function renderQuoteBlock(lines) {
  const quote = cleanText(lines[0]).replace(/^"|"$/g, "");
  const color = getSafeQuoteColor(lines[1]);
  const speaker = cleanText(lines[2]).replace(/^-+/, "").trim();

  return `
    <figure class="press-release-quote" style="--quote-color: ${color};">
      <blockquote>
        “${escapeHtml(quote)}”
      </blockquote>
      <figcaption>
        ${escapeHtml(speaker)}
      </figcaption>
    </figure>
  `;
}

function renderTextParagraph(lines) {
  return `<p>${lines.map(line => escapeHtml(line)).join("<br>")}</p>`;
}

function markdownToHtml(markdown) {
  const blocks = cleanText(markdown)
    .split(/\n\s*\n/g)
    .map(block => block.trim())
    .filter(Boolean);

  if (!blocks.length) {
    return `<p>No body text yet.</p>`;
  }

  return blocks.map(block => {
    const lines = block
      .split("\n")
      .map(line => line.trim())
      .filter(Boolean);

    if (isQuoteBlock(lines)) {
      return renderQuoteBlock(lines);
    }

    return renderTextParagraph(lines);
  }).join("");
}

function renderPreview() {
  const draft = getSelectedDraft();
  const preview = document.getElementById("articlePreview");

  if (!draft || !preview) return;

  preview.innerHTML = `
    <h2>${escapeHtml(draft.headline || "Untitled Draft")}</h2>
    <h3>${escapeHtml(draft.subheadline || "")}</h3>

    <div class="meta-line">
      <span class="meta-pill">${escapeHtml(draft.team_display_name || "Unknown Team")}</span>
      <span class="meta-pill">${escapeHtml(draft.division || "No Division")}</span>
      <span class="meta-pill">${escapeHtml(draft.status || "draft")}</span>
    </div>

    ${markdownToHtml(draft.body_markdown || "")}
  `;
}

function renderEditor() {
  const draft = getSelectedDraft();
  const editor = document.getElementById("editor");

  if (!draft) {
    editor.innerHTML = `<div class="empty">Select a press release draft to edit.</div>`;
    return;
  }

  draft._last_headline = draft._last_headline || draft.headline || "";

  const playerSummary = renderPlayerSummary(draft);

  editor.innerHTML = `
    <div class="meta-line">
      <span class="meta-pill">${escapeHtml(draft.team_display_name || "Unknown Team")}</span>
      <span class="meta-pill">${escapeHtml(draft.team_abbreviation || "TBD")}</span>
      <span class="meta-pill">${escapeHtml(draft.division || "No Division")}</span>
      ${playerSummary ? `<span class="meta-pill">${escapeHtml(playerSummary)}</span>` : ""}
    </div>

    <div class="editor-grid">
      <label>
        Headline
        <input
          value="${escapeAttr(draft.headline || "")}"
          oninput="updateDraftField('headline', this.value)"
        >
      </label>

      <label>
        Status
        <select onchange="updateDraftField('status', this.value)">
          ${selectOption("draft", draft.status, "Draft")}
          ${selectOption("ready", draft.status, "Ready")}
          ${selectOption("published", draft.status, "Published")}
        </select>
      </label>
    </div>

    <label>
      Subheadline
      <input
        value="${escapeAttr(draft.subheadline || "")}"
        oninput="updateDraftField('subheadline', this.value)"
      >
    </label>

    <label>
      Slug
      <input
        value="${escapeAttr(draft.slug || "")}"
        oninput="updateDraftField('slug', this.value)"
      >
    </label>

    <label>
      Body Markdown
      <textarea oninput="updateDraftField('body_markdown', this.value)">${escapeHtml(draft.body_markdown || "")}</textarea>
    </label>

    <label>
      Writer Notes
      <textarea oninput="updateDraftField('writer_notes', this.value)">${escapeHtml(draft.writer_notes || "")}</textarea>
    </label>

    <section class="article-preview" id="articlePreview"></section>
  `;

  renderPreview();
}

function selectOption(value, selected, label) {
  return `
    <option
      value="${value}"
      ${cleanText(selected || "draft").toLowerCase() === value ? "selected" : ""}
    >
      ${label}
    </option>
  `;
}

async function saveDrafts() {
  draftData.drafts = drafts.map(draft => {
    const copy = { ...draft };
    delete copy._last_headline;
    return copy;
  });

  const response = await fetch("/api/drafts", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(draftData, null, 2)
  });

  if (!response.ok) {
    const text = await response.text();
    alert(`Save failed: ${text}`);
    return;
  }

  dirty = false;
  setStatus("Saved press_release_drafts.json");
}

window.addEventListener("beforeunload", event => {
  if (!dirty) return;

  event.preventDefault();
  event.returnValue = "";
});

document.getElementById("searchInput").addEventListener("input", renderDraftList);

loadDrafts();
</script>
</body>
</html>
"""


def load_json(path, fallback):
    if not path.exists():
        return fallback

    try:
        with path.open("r", encoding="utf-8") as file:
            raw = file.read().strip()

        if not raw:
            return fallback

        return json.loads(raw)

    except json.JSONDecodeError:
        print(f"WARNING: Invalid JSON in {path}. Using fallback.")
        return fallback


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def normalize_draft_data(data):
    if not isinstance(data, dict):
        data = {}

    if not isinstance(data.get("drafts"), list):
        data["drafts"] = []

    data["season_id"] = data.get("season_id") or SEASON_ID
    data["updated_at_utc"] = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    return data


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, content_type="text/plain; charset=utf-8"):
        encoded = body.encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self._send(200, HTML, "text/html; charset=utf-8")
            return

        if parsed.path == "/api/drafts":
            data = normalize_draft_data(load_json(DRAFTS_FILE, {
                "season_id": SEASON_ID,
                "drafts": []
            }))

            self._send(
                200,
                json.dumps(data, indent=2, ensure_ascii=False),
                "application/json; charset=utf-8"
            )
            return

        self._send(404, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path != "/api/drafts":
            self._send(404, "Not found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")

        try:
            data = json.loads(raw_body)
        except Exception as error:
            self._send(400, f"Invalid JSON: {error}")
            return

        data = normalize_draft_data(data)

        write_json(DRAFTS_FILE, data)

        self._send(200, "Saved")

    def log_message(self, format, *args):
        return


def main():
    DRAFTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not DRAFTS_FILE.exists():
        write_json(DRAFTS_FILE, {
            "season_id": SEASON_ID,
            "drafts": []
        })

    server = HTTPServer((HOST, PORT), Handler)

    url = f"http://{HOST}:{PORT}"

    print(f"Press Release Editor running at {url}")
    print(f"Editing: {DRAFTS_FILE}")
    print("Press Ctrl+C to stop.")

    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        print("Stopped.")


if __name__ == "__main__":
    main()