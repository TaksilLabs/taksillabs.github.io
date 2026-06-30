import json
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parents[2]

SEASON_ID = "summer_2026"
SEASON_TYPE = "regular_season"

REGULAR_SEASON_DIR = (
    BASE_DIR
    / "data"
    / "live_season"
    / SEASON_ID
    / SEASON_TYPE
)

SCHEDULE_FILE = REGULAR_SEASON_DIR / "schedule.json"
MATCHES_FILE = REGULAR_SEASON_DIR / "matches.json"
BROADCASTS_FILE = REGULAR_SEASON_DIR / "broadcasts.json"

HOST = "localhost"
PORT = 8783


HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SPL Broadcast Editor</title>

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
      --purple: #b266ff;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      background:
        radial-gradient(circle at top right, rgba(178, 102, 255, 0.12), transparent 34%),
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
      min-height: 100px;
      resize: vertical;
      line-height: 1.45;
      font-family: Arial, sans-serif;
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

    .caster-button {
      background: rgba(0, 209, 209, 0.12);
      border-color: var(--accent);
    }

    .danger-button {
      background: rgba(255, 92, 92, 0.12);
      border-color: var(--danger);
    }

    .main {
      display: grid;
      grid-template-columns: 430px 1fr;
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

    .match-list {
      max-height: calc(100vh - 200px);
      overflow-y: auto;
    }

    .match-row {
      padding: 13px 14px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      cursor: pointer;
    }

    .match-row:hover {
      background: rgba(0, 209, 209, 0.08);
    }

    .match-row.active {
      background: rgba(0, 209, 209, 0.18);
      border-left: 4px solid var(--accent);
    }

    .match-row.casted {
      border-right: 4px solid var(--purple);
    }

    .match-row strong {
      display: block;
      margin-bottom: 5px;
    }

    .match-row small {
      display: block;
      color: var(--muted);
      line-height: 1.35;
    }

    .pill-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 8px;
    }

    .pill {
      display: inline-block;
      padding: 3px 7px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--muted);
      background: rgba(7, 16, 24, 0.72);
      font-size: 0.72rem;
      font-weight: 800;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }

    .pill-casted {
      color: var(--purple);
      border-color: rgba(178, 102, 255, 0.55);
      background: rgba(178, 102, 255, 0.1);
    }

    .pill-final {
      color: var(--good);
      border-color: rgba(92, 255, 157, 0.45);
      background: rgba(92, 255, 157, 0.1);
    }

    .editor {
      padding: 18px;
    }

    .editor label,
    .caster-row label {
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

    .editor-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    .match-title {
      margin: 0 0 10px;
      color: var(--text);
      font-size: 1.6rem;
    }

    .match-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 18px;
      color: var(--muted);
    }

    .checkbox-line {
      display: flex;
      gap: 10px;
      align-items: center;
      margin: 12px 0 18px;
      color: var(--text);
      font-weight: 800;
    }

    .checkbox-line input {
      width: auto;
      transform: scale(1.25);
    }

    .casters {
      display: grid;
      gap: 10px;
      margin-bottom: 14px;
    }

    .caster-row {
      display: grid;
      grid-template-columns: 1fr 180px 90px;
      gap: 10px;
      align-items: end;
      padding: 12px;
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 12px;
      background: rgba(17, 28, 38, 0.75);
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

    @media (max-width: 1050px) {
      .main {
        grid-template-columns: 1fr;
      }

      .match-list {
        max-height: 330px;
      }

      .editor-grid,
      .caster-row {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>

<body>
  <header>
    <h1>Broadcast Editor</h1>

    <div class="toolbar">
      <input id="searchInput" type="text" placeholder="Search teams, divisions, weeks...">

      <select id="castedFilter" onchange="renderMatchList()">
        <option value="all">All Matches</option>
        <option value="casted">Casted Only</option>
        <option value="uncasted">Uncasted Only</option>
      </select>

      <select id="statusFilter" onchange="renderMatchList()">
        <option value="all">All Statuses</option>
        <option value="scheduled">Scheduled</option>
        <option value="final">Final</option>
      </select>

      <button class="save-button" onclick="saveBroadcasts()">Save Broadcasts</button>

      <span id="status" class="status">Loading...</span>
    </div>
  </header>

  <div class="main">
    <aside class="sidebar">
      <div id="matchList" class="match-list"></div>
    </aside>

    <section id="editor" class="editor">
      <div class="empty">Select a match to edit broadcast info.</div>
    </section>
  </div>

<script>
let appData = null;
let matches = [];
let broadcasts = {};
let selectedMatchId = null;
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

function getMatchId(match) {
  return cleanText(
    match.match_id
    || match.id
    || match.schedule_id
    || match.source_id
  );
}

function getMatchArray(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.matches)) return data.matches;
  if (Array.isArray(data?.schedule)) return data.schedule;
  return [];
}

function normalizeKey(value) {
  return cleanText(value)
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function titleCase(value) {
  return cleanText(value)
    .replace(/_/g, " ")
    .replace(/\b\w/g, letter => letter.toUpperCase());
}

function isFinal(match) {
  const status = cleanText(match.status || match.match_status).toLowerCase();

  return status === "final"
    || status === "completed"
    || status === "complete"
    || (
      match.home_score !== undefined
      && match.away_score !== undefined
      && match.home_score !== null
      && match.away_score !== null
    );
}

function getMatchSortValue(match) {
  const rawDate = match.date || match.datetime || match.scheduled_at || match.played_at || "";

  if (rawDate) {
    const value = Date.parse(rawDate);

    if (!Number.isNaN(value)) {
      return value;
    }
  }

  const week = Number(match.week || 0);
  const matchNumber = Number(match.match_number || match.match || 0);

  return (week * 1000) + matchNumber;
}

function formatMatchDate(match) {
  const raw = match.date || match.datetime || match.scheduled_at || match.played_at || "";

  if (!raw) return "Date TBD";

  const date = new Date(raw);

  if (Number.isNaN(date.getTime())) {
    return "Date TBD";
  }

  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

function getMatchLabel(match) {
  const away = cleanText(match.away_team || match.away_team_display_name || match.away_team_id || "Away");
  const home = cleanText(match.home_team || match.home_team_display_name || match.home_team_id || "Home");

  return `${away} @ ${home}`;
}

function getBroadcast(matchId) {
  return broadcasts?.[matchId] || null;
}

function ensureBroadcast(match) {
  const matchId = getMatchId(match);

  if (!broadcasts[matchId]) {
    broadcasts[matchId] = {
      match_id: matchId,
      is_casted: false,
      channel_name: "",
      channel_url: "",
      casters: [],
      notes: "",
      updated_at_utc: ""
    };
  }

  return broadcasts[matchId];
}

function mergeMatches(scheduleData, matchData) {
  const schedule = getMatchArray(scheduleData);
  const results = getMatchArray(matchData);

  const byId = new Map();

  schedule.forEach(match => {
    const id = getMatchId(match);
    if (id) byId.set(id, match);
  });

  results.forEach(match => {
    const id = getMatchId(match);
    if (!id) return;

    byId.set(id, {
      ...(byId.get(id) || {}),
      ...match
    });
  });

  return [...byId.values()]
    .filter(match => getMatchId(match))
    .sort((a, b) => getMatchSortValue(a) - getMatchSortValue(b));
}

async function loadData() {
  const response = await fetch("/api/data");

  if (!response.ok) {
    setStatus("Failed to load broadcast data.");
    return;
  }

  appData = await response.json();

  matches = mergeMatches(appData.schedule, appData.matches);
  broadcasts = appData.broadcasts || {};

  setStatus(`Loaded ${matches.length} matches`);
  renderMatchList();

  if (matches.length && !selectedMatchId) {
    selectedMatchId = getMatchId(matches[0]);
    renderEditor();
    renderMatchList();
  }
}

function matchMatchesSearch(match, query) {
  if (!query) return true;

  const haystack = [
    getMatchId(match),
    match.source_id,
    match.match_code,
    match.division,
    match.week,
    match.home_team,
    match.home_team_id,
    match.away_team,
    match.away_team_id,
    getMatchLabel(match)
  ].join(" ").toLowerCase();

  return haystack.includes(query.toLowerCase());
}

function renderMatchList() {
  const query = cleanText(document.getElementById("searchInput").value);
  const castedFilter = cleanText(document.getElementById("castedFilter").value);
  const statusFilter = cleanText(document.getElementById("statusFilter").value);
  const container = document.getElementById("matchList");

  const filtered = matches.filter(match => {
    const matchId = getMatchId(match);
    const broadcast = getBroadcast(matchId);
    const casted = Boolean(broadcast?.is_casted || broadcast?.channel_name);
    const final = isFinal(match);

    if (castedFilter === "casted" && !casted) return false;
    if (castedFilter === "uncasted" && casted) return false;

    if (statusFilter === "scheduled" && final) return false;
    if (statusFilter === "final" && !final) return false;

    return matchMatchesSearch(match, query);
  });

  if (!filtered.length) {
    container.innerHTML = `<div class="empty">No matching matches.</div>`;
    return;
  }

  container.innerHTML = filtered.map(match => {
    const matchId = getMatchId(match);
    const broadcast = getBroadcast(matchId);
    const casted = Boolean(broadcast?.is_casted || broadcast?.channel_name);
    const final = isFinal(match);

    return `
      <div
        class="match-row ${matchId === selectedMatchId ? "active" : ""} ${casted ? "casted" : ""}"
        onclick="selectMatch('${escapeAttr(matchId)}')"
      >
        <strong>${escapeHtml(getMatchLabel(match))}</strong>
        <small>
          ${escapeHtml(titleCase(match.division || "No Division"))}
          · Week ${escapeHtml(match.week || "?")}
          · ${escapeHtml(formatMatchDate(match))}
        </small>

        <div class="pill-row">
          ${casted ? `<span class="pill pill-casted">Casted</span>` : `<span class="pill">Uncasted</span>`}
          ${final ? `<span class="pill pill-final">Final</span>` : `<span class="pill">Scheduled</span>`}
          ${broadcast?.channel_name ? `<span class="pill">${escapeHtml(broadcast.channel_name)}</span>` : ""}
        </div>
      </div>
    `;
  }).join("");
}

function getSelectedMatch() {
  return matches.find(match => getMatchId(match) === selectedMatchId) || null;
}

function selectMatch(matchId) {
  selectedMatchId = matchId;
  renderMatchList();
  renderEditor();
}

function updateBroadcastField(field, value) {
  const match = getSelectedMatch();
  if (!match) return;

  const broadcast = ensureBroadcast(match);
  broadcast[field] = value;
  broadcast.updated_at_utc = new Date().toISOString();

  markDirty();
  renderMatchList();
}

function updateBroadcastChecked(field, checked) {
  updateBroadcastField(field, checked);
}

function addCaster() {
  const match = getSelectedMatch();
  if (!match) return;

  const broadcast = ensureBroadcast(match);

  if (!Array.isArray(broadcast.casters)) {
    broadcast.casters = [];
  }

  broadcast.casters.push({
    name: "",
    role: "caster"
  });

  broadcast.is_casted = true;
  broadcast.updated_at_utc = new Date().toISOString();

  markDirty();
  renderEditor();
  renderMatchList();
}

function updateCaster(index, field, value) {
  const match = getSelectedMatch();
  if (!match) return;

  const broadcast = ensureBroadcast(match);

  if (!Array.isArray(broadcast.casters)) {
    broadcast.casters = [];
  }

  if (!broadcast.casters[index]) return;

  broadcast.casters[index][field] = value;
  broadcast.updated_at_utc = new Date().toISOString();

  markDirty();
  renderMatchList();
}

function removeCaster(index) {
  const match = getSelectedMatch();
  if (!match) return;

  const broadcast = ensureBroadcast(match);

  if (!Array.isArray(broadcast.casters)) {
    broadcast.casters = [];
  }

  broadcast.casters.splice(index, 1);
  broadcast.updated_at_utc = new Date().toISOString();

  markDirty();
  renderEditor();
  renderMatchList();
}

function clearBroadcast() {
  const match = getSelectedMatch();
  if (!match) return;

  const matchId = getMatchId(match);

  const confirmed = confirm(`Clear broadcast info for ${getMatchLabel(match)}?`);
  if (!confirmed) return;

  broadcasts[matchId] = {
    match_id: matchId,
    is_casted: false,
    channel_name: "",
    channel_url: "",
    casters: [],
    notes: "",
    updated_at_utc: new Date().toISOString()
  };

  markDirty();
  renderEditor();
  renderMatchList();
}

function renderEditor() {
  const match = getSelectedMatch();
  const editor = document.getElementById("editor");

  if (!match) {
    editor.innerHTML = `<div class="empty">Select a match to edit broadcast info.</div>`;
    return;
  }

  const matchId = getMatchId(match);
  const broadcast = ensureBroadcast(match);
  const casters = Array.isArray(broadcast.casters) ? broadcast.casters : [];

  editor.innerHTML = `
    <h2 class="match-title">${escapeHtml(getMatchLabel(match))}</h2>

    <div class="match-meta">
      <span class="pill">${escapeHtml(matchId)}</span>
      <span class="pill">${escapeHtml(titleCase(match.division || "No Division"))}</span>
      <span class="pill">Week ${escapeHtml(match.week || "?")}</span>
      <span class="pill">${escapeHtml(formatMatchDate(match))}</span>
      ${isFinal(match) ? `<span class="pill pill-final">Final</span>` : `<span class="pill">Scheduled</span>`}
    </div>

    <label class="checkbox-line">
      <input
        type="checkbox"
        ${broadcast.is_casted ? "checked" : ""}
        onchange="updateBroadcastChecked('is_casted', this.checked)"
      >
      Mark this match as casted
    </label>

    <div class="editor-grid">
      <label>
        Channel Name
        <input
          value="${escapeAttr(broadcast.channel_name || "")}"
          placeholder="SPL, DarthTaksil, Team Channel..."
          oninput="updateBroadcastField('channel_name', this.value)"
        >
      </label>

      <label>
        Channel URL
        <input
          value="${escapeAttr(broadcast.channel_url || "")}"
          placeholder="https://twitch.tv/..."
          oninput="updateBroadcastField('channel_url', this.value)"
        >
      </label>
    </div>

    <div class="toolbar" style="margin-bottom: 12px;">
      <button class="caster-button" onclick="addCaster()">Add Caster</button>
      <button class="danger-button" onclick="clearBroadcast()">Clear Broadcast Info</button>
    </div>

    <div class="casters">
      ${
        casters.length
          ? casters.map((caster, index) => renderCasterRow(caster, index)).join("")
          : `<div class="empty">No casters listed yet.</div>`
      }
    </div>

    <label>
      Broadcast Notes
      <textarea
        placeholder="Internal notes, coverage plans, co-stream details..."
        oninput="updateBroadcastField('notes', this.value)"
      >${escapeHtml(broadcast.notes || "")}</textarea>
    </label>
  `;
}

function renderCasterRow(caster, index) {
  return `
    <div class="caster-row">
      <label>
        Caster Name
        <input
          value="${escapeAttr(caster.name || "")}"
          oninput="updateCaster(${index}, 'name', this.value)"
        >
      </label>

      <label>
        Role
        <select onchange="updateCaster(${index}, 'role', this.value)">
          ${selectOption("caster", caster.role, "Caster")}
          ${selectOption("play_by_play", caster.role, "Play-by-play")}
          ${selectOption("color", caster.role, "Color")}
          ${selectOption("analyst", caster.role, "Analyst")}
          ${selectOption("producer", caster.role, "Producer")}
        </select>
      </label>

      <button class="danger-button" onclick="removeCaster(${index})">
        Remove
      </button>
    </div>
  `;
}

function selectOption(value, selected, label) {
  return `
    <option
      value="${value}"
      ${cleanText(selected).toLowerCase() === value ? "selected" : ""}
    >
      ${label}
    </option>
  `;
}

async function saveBroadcasts() {
  const response = await fetch("/api/broadcasts", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(broadcasts, null, 2)
  });

  if (!response.ok) {
    const text = await response.text();
    alert(`Save failed: ${text}`);
    return;
  }

  dirty = false;
  setStatus("Saved broadcasts.json");
}

window.addEventListener("beforeunload", event => {
  if (!dirty) return;

  event.preventDefault();
  event.returnValue = "";
});

document.getElementById("searchInput").addEventListener("input", renderMatchList);

loadData();
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


def normalize_broadcasts(data):
    if isinstance(data, dict):
        return data

    return {}


def get_match_array(data):
    if isinstance(data, list):
        return data

    if isinstance(data, dict) and isinstance(data.get("matches"), list):
        return data["matches"]

    if isinstance(data, dict) and isinstance(data.get("schedule"), list):
        return data["schedule"]

    return []


def get_match_id(match):
    return str(
        match.get("match_id")
        or match.get("id")
        or match.get("schedule_id")
        or match.get("source_id")
        or ""
    ).strip()


def normalize_posted_broadcasts(data):
    if not isinstance(data, dict):
        return {}

    normalized = {}

    for match_id, broadcast in data.items():
        if not isinstance(broadcast, dict):
            continue

        clean_match_id = str(match_id or broadcast.get("match_id") or "").strip()

        if not clean_match_id:
            continue

        casters = broadcast.get("casters")

        if not isinstance(casters, list):
            casters = []

        normalized[clean_match_id] = {
            "match_id": clean_match_id,
            "is_casted": bool(broadcast.get("is_casted")),
            "channel_name": str(broadcast.get("channel_name") or "").strip(),
            "channel_url": str(broadcast.get("channel_url") or "").strip(),
            "casters": [
                {
                    "name": str(caster.get("name") or "").strip(),
                    "role": str(caster.get("role") or "caster").strip() or "caster",
                }
                for caster in casters
                if isinstance(caster, dict)
                and (
                    str(caster.get("name") or "").strip()
                    or str(caster.get("role") or "").strip()
                )
            ],
            "notes": str(broadcast.get("notes") or "").strip(),
            "updated_at_utc": str(broadcast.get("updated_at_utc") or "").strip()
            or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        }

    return normalized


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

        if parsed.path == "/api/data":
            data = {
                "schedule": load_json(SCHEDULE_FILE, {"matches": []}),
                "matches": load_json(MATCHES_FILE, {"matches": []}),
                "broadcasts": normalize_broadcasts(load_json(BROADCASTS_FILE, {})),
            }

            self._send(
                200,
                json.dumps(data, indent=2, ensure_ascii=False),
                "application/json; charset=utf-8"
            )
            return

        self._send(404, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path != "/api/broadcasts":
            self._send(404, "Not found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")

        try:
            data = json.loads(raw_body)
        except Exception as error:
            self._send(400, f"Invalid JSON: {error}")
            return

        normalized = normalize_posted_broadcasts(data)

        write_json(BROADCASTS_FILE, normalized)

        self._send(200, "Saved")

    def log_message(self, format, *args):
        return


def main():
    if not SCHEDULE_FILE.exists():
        print(f"Schedule file not found: {SCHEDULE_FILE}")
        print("Run this first:")
        print("  python tools/live/import_regular_schedule.py")
        return

    BROADCASTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not BROADCASTS_FILE.exists():
        write_json(BROADCASTS_FILE, {})

    server = HTTPServer((HOST, PORT), Handler)

    url = f"http://{HOST}:{PORT}"

    print(f"Broadcast Editor running at {url}")
    print(f"Editing: {BROADCASTS_FILE}")
    print("Press Ctrl+C to stop.")

    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        print("Stopped.")


if __name__ == "__main__":
    main()