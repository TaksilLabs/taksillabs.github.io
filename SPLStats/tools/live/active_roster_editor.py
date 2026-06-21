import json
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parents[2]

SEASON_ID = "summer_2026"
ROSTERS_FILE = (
    BASE_DIR
    / "data"
    / "live_season"
    / SEASON_ID
    / "active_rosters.json"
)

HOST = "localhost"
PORT = 8781


HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Active Roster Editor</title>

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
      background: rgba(12, 20, 28, 0.92);
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
    button {
      border-radius: 8px;
      border: 1px solid var(--line);
      background: #071018;
      color: var(--text);
      padding: 9px 11px;
      font-size: 0.95rem;
    }

    input {
      min-width: 220px;
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

    .add-button {
      background: rgba(0, 209, 209, 0.12);
      border-color: var(--accent);
    }

    .danger-button {
      background: rgba(255, 92, 92, 0.12);
      border-color: var(--danger);
    }

    .main {
      display: grid;
      grid-template-columns: 320px 1fr;
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

    .team-list {
      max-height: calc(100vh - 190px);
      overflow-y: auto;
    }

    .team-row {
      padding: 12px 14px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      cursor: pointer;
    }

    .team-row:hover {
      background: rgba(0, 209, 209, 0.08);
    }

    .team-row.active {
      background: rgba(0, 209, 209, 0.18);
      border-left: 4px solid var(--accent);
    }

    .team-row strong {
      display: block;
    }

    .team-row small {
      color: var(--muted);
    }

    .editor {
      padding: 18px;
    }

    .editor-head {
      display: grid;
      grid-template-columns: 1fr 180px 160px;
      gap: 10px;
      margin-bottom: 18px;
    }

    .editor-head label,
    .player-row label {
      display: flex;
      flex-direction: column;
      gap: 6px;
      color: var(--muted);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 700;
    }

    .editor-head input {
      width: 100%;
      min-width: 0;
    }

    .players {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .player-row {
      display: grid;
      grid-template-columns: 150px 1fr 220px 95px;
      gap: 10px;
      align-items: end;

      padding: 12px;
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 12px;
      background: rgba(17, 28, 38, 0.75);
    }

    .player-row input,
    .player-row select {
      width: 100%;
      min-width: 0;
    }

    .status {
      color: var(--muted);
      padding-left: 8px;
    }

    .empty {
      padding: 30px;
      text-align: center;
      color: var(--muted);
    }

    .count-pill {
      display: inline-block;
      margin-left: 8px;
      padding: 2px 7px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--muted);
      font-size: 0.8rem;
    }

    @media (max-width: 950px) {
      .main {
        grid-template-columns: 1fr;
      }

      .editor-head,
      .player-row {
        grid-template-columns: 1fr;
      }

      .team-list {
        max-height: 260px;
      }
    }
  </style>
</head>

<body>
  <header>
    <h1>Active Roster Editor</h1>

    <div class="toolbar">
      <input id="searchInput" type="text" placeholder="Search teams or players...">

      <button class="save-button" onclick="saveRosters()">Save Rosters</button>
      <button class="add-button" onclick="addTeam()">Add Team</button>

      <span id="status" class="status">Loading...</span>
    </div>
  </header>

  <div class="main">
    <aside class="sidebar">
      <div id="teamList" class="team-list"></div>
    </aside>

    <section id="editor" class="editor">
      <div class="empty">Select a team to edit.</div>
    </section>
  </div>

<script>
let rosterData = null;
let teams = [];
let selectedTeamId = null;
let dirty = false;

function cleanText(value) {
  return String(value || "").trim();
}

function makeId(value, fallback = "unknown") {
  let text = cleanText(value).toLowerCase();

  text = text.replace(/\s*\([A-Z0-9]{2,8}\)\s*$/i, "");
  text = text.replace(/[^a-z0-9_\-\s]/g, "");
  text = text.replace(/[\s\-]+/g, "_");
  text = text.replace(/_+/g, "_");
  text = text.replace(/^_+|_+$/g, "");

  return text || fallback;
}

function setStatus(message) {
  document.getElementById("status").textContent = message;
}

function markDirty() {
  dirty = true;
  setStatus("Unsaved changes");
}

async function loadRosters() {
  const response = await fetch("/api/rosters");

  if (!response.ok) {
    setStatus("Failed to load rosters.");
    return;
  }

  rosterData = await response.json();
  teams = rosterData.teams || [];

  teams.sort((a, b) =>
    cleanText(a.team_display_name).localeCompare(cleanText(b.team_display_name))
  );

  setStatus(`Loaded ${teams.length} teams`);
  renderTeamList();
}

function teamMatchesSearch(team, query) {
  if (!query) return true;

  const haystack = [
    team.team_id,
    team.team_display_name,
    team.team,
    team.team_abbreviation,
    team.region,
    ...(team.players || []).map(p => `${p.steam_name} ${p.slap_id} ${p.role}`)
  ].join(" ").toLowerCase();

  return haystack.includes(query.toLowerCase());
}

function renderTeamList() {
  const query = cleanText(document.getElementById("searchInput").value);
  const container = document.getElementById("teamList");

  const filtered = teams.filter(team => teamMatchesSearch(team, query));

  container.innerHTML = filtered.map(team => {
    const playerCount = (team.players || []).length;
    const slapCount = (team.slap_ids || []).length;

    return `
      <div
        class="team-row ${team.team_id === selectedTeamId ? "active" : ""}"
        onclick="selectTeam('${team.team_id}')"
      >
        <strong>${team.team_display_name || team.team || team.team_id}</strong>
        <small>
          ${team.region || "unknown"}
          <span class="count-pill">${playerCount} players</span>
          <span class="count-pill">${slapCount} IDs</span>
        </small>
      </div>
    `;
  }).join("");
}

function selectTeam(teamId) {
  selectedTeamId = teamId;
  renderTeamList();
  renderEditor();
}

function getSelectedTeam() {
  return teams.find(team => team.team_id === selectedTeamId) || null;
}

function rebuildSlapIds(team) {
  const seen = new Set();

  team.slap_ids = [];

  (team.players || []).forEach(player => {
    const slapId = cleanText(player.slap_id);

    if (slapId && !seen.has(slapId)) {
      seen.add(slapId);
      team.slap_ids.push(slapId);
    }
  });
}

function updateTeamField(field, value) {
  const team = getSelectedTeam();
  if (!team) return;

  team[field] = value;

  if (field === "team_display_name") {
    team.team = value;
  }

  markDirty();
  renderTeamList();
}

function updatePlayer(index, field, value) {
  const team = getSelectedTeam();
  if (!team) return;

  team.players[index][field] = value;

  rebuildSlapIds(team);

  markDirty();
  renderTeamList();
}

function addPlayer() {
  const team = getSelectedTeam();
  if (!team) return;

  if (!Array.isArray(team.players)) {
    team.players = [];
  }

  team.players.push({
    role: "player",
    steam_name: "",
    slap_id: ""
  });

  rebuildSlapIds(team);
  markDirty();
  renderEditor();
  renderTeamList();
}

function removePlayer(index) {
  const team = getSelectedTeam();
  if (!team) return;

  const player = team.players[index];

  const confirmed = confirm(
    `Remove ${player.steam_name || player.slap_id || "this player"}?`
  );

  if (!confirmed) return;

  team.players.splice(index, 1);

  rebuildSlapIds(team);
  markDirty();
  renderEditor();
  renderTeamList();
}

function addTeam() {
  const name = prompt("Team name?");
  if (!name) return;

  const teamId = makeId(name, "new_team");

  if (teams.some(team => team.team_id === teamId)) {
    alert("A team with that team_id already exists.");
    return;
  }

  const team = {
    team_id: teamId,
    team_display_name: name,
    team: name,
    team_abbreviation: "",
    region: "",
    players: [],
    slap_ids: []
  };

  teams.push(team);
  teams.sort((a, b) =>
    cleanText(a.team_display_name).localeCompare(cleanText(b.team_display_name))
  );

  selectedTeamId = teamId;
  markDirty();
  renderTeamList();
  renderEditor();
}

function renderEditor() {
  const team = getSelectedTeam();
  const editor = document.getElementById("editor");

  if (!team) {
    editor.innerHTML = `<div class="empty">Select a team to edit.</div>`;
    return;
  }

  const players = team.players || [];

  editor.innerHTML = `
    <div class="editor-head">
      <label>
        Team Name
        <input
          value="${escapeAttr(team.team_display_name || team.team || "")}"
          oninput="updateTeamField('team_display_name', this.value)"
        >
      </label>

      <label>
        Abbreviation
        <input
          value="${escapeAttr(team.team_abbreviation || "")}"
          oninput="updateTeamField('team_abbreviation', this.value)"
        >
      </label>

      <label>
        Region
        <select onchange="updateTeamField('region', this.value)">
          ${regionOption("", team.region, "Unknown")}
          ${regionOption("east", team.region, "East")}
          ${regionOption("central", team.region, "Central")}
          ${regionOption("west", team.region, "West")}
        </select>
      </label>
    </div>

    <div class="toolbar" style="margin-bottom: 14px;">
      <button class="add-button" onclick="addPlayer()">Add Player</button>
      <span class="status">
        ${(team.slap_ids || []).length} Slap IDs available for log matching
      </span>
    </div>

    <div class="players">
      ${players.map((player, index) => renderPlayerRow(player, index)).join("")}
    </div>
  `;
}

function regionOption(value, selected, label) {
  return `
    <option
      value="${value}"
      ${cleanText(selected).toLowerCase() === value ? "selected" : ""}
    >
      ${label}
    </option>
  `;
}

function renderPlayerRow(player, index) {
  return `
    <div class="player-row">
      <label>
        Role
        <select onchange="updatePlayer(${index}, 'role', this.value)">
          ${roleOption("gm", player.role, "GM")}
          ${roleOption("captain", player.role, "Captain")}
          ${roleOption("player", player.role, "Player")}
        </select>
      </label>

      <label>
        Steam Name
        <input
          value="${escapeAttr(player.steam_name || "")}"
          oninput="updatePlayer(${index}, 'steam_name', this.value)"
        >
      </label>

      <label>
        Slap ID
        <input
          value="${escapeAttr(player.slap_id || "")}"
          oninput="updatePlayer(${index}, 'slap_id', this.value)"
        >
      </label>

      <button class="danger-button" onclick="removePlayer(${index})">
        Remove
      </button>
    </div>
  `;
}

function roleOption(value, selected, label) {
  return `
    <option
      value="${value}"
      ${cleanText(selected).toLowerCase() === value ? "selected" : ""}
    >
      ${label}
    </option>
  `;
}

function escapeAttr(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function saveRosters() {
  teams.forEach(rebuildSlapIds);

  rosterData.teams = teams;

  const response = await fetch("/api/rosters", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(rosterData, null, 2)
  });

  if (!response.ok) {
    const text = await response.text();
    alert(`Save failed: ${text}`);
    return;
  }

  dirty = false;
  setStatus("Saved active_rosters.json");
}

window.addEventListener("beforeunload", event => {
  if (!dirty) return;

  event.preventDefault();
  event.returnValue = "";
});

document.getElementById("searchInput").addEventListener("input", renderTeamList);

loadRosters();
</script>
</body>
</html>
"""


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

        if parsed.path == "/api/rosters":
            if not ROSTERS_FILE.exists():
                self._send(
                    404,
                    f"Roster file not found: {ROSTERS_FILE}"
                )
                return

            with ROSTERS_FILE.open("r", encoding="utf-8") as file:
                data = file.read()

            self._send(200, data, "application/json; charset=utf-8")
            return

        self._send(404, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path != "/api/rosters":
            self._send(404, "Not found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")

        try:
            data = json.loads(raw_body)
        except Exception as error:
            self._send(400, f"Invalid JSON: {error}")
            return

        if not isinstance(data, dict) or not isinstance(data.get("teams"), list):
            self._send(400, "Expected JSON object with a teams list.")
            return

        ROSTERS_FILE.parent.mkdir(parents=True, exist_ok=True)

        with ROSTERS_FILE.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
            file.write("\n")

        self._send(200, "Saved")

    def log_message(self, format, *args):
        return


def main():
    if not ROSTERS_FILE.exists():
        print(f"Roster file not found: {ROSTERS_FILE}")
        print("Run this first:")
        print(r"  py tools\live\build_active_rosters.py")
        return

    server = HTTPServer((HOST, PORT), Handler)

    url = f"http://{HOST}:{PORT}"

    print(f"Active Roster Editor running at {url}")
    print(f"Editing: {ROSTERS_FILE}")
    print("Press Ctrl+C to stop.")

    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        print("Stopped.")


if __name__ == "__main__":
    main()