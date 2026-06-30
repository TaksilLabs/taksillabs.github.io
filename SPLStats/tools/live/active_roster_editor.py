import json
import webbrowser
from datetime import datetime, timezone
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

TRANSACTIONS_FILE = (
    BASE_DIR
    / "data"
    / "live_season"
    / SEASON_ID
    / "roster_transactions.json"
)

PRESS_RELEASE_DRAFTS_FILE = (
    BASE_DIR
    / "data"
    / "live_season"
    / SEASON_ID
    / "news"
    / "press_release_drafts.json"
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
      grid-template-columns: 1fr 150px 150px 190px 190px;
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
      grid-template-columns: 130px 1fr 110px 220px 95px;
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

function normalizeRegionValue(value) {
  const text = cleanText(value).toLowerCase();

  if (text.includes("east") || text.includes("main slapshot league")) {
    return "east";
  }

  if (text.includes("central")) {
    return "central";
  }

  if (text.includes("west")) {
    return "west";
  }

  return text;
}

function ensureTeamSeasonFields(team) {
  team.season_id = team.season_id || rosterData?.season_id || "summer_2026";
  team.region = normalizeRegionValue(team.region);
  team.division = team.division || "";
  team.conference = team.conference ?? "";
}

async function loadRosters() {
  const response = await fetch("/api/rosters");

  if (!response.ok) {
    setStatus("Failed to load rosters.");
    return;
  }

  rosterData = await response.json();
  teams = rosterData.teams || [];

  teams.forEach(ensureTeamSeasonFields);

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
    team.division,
    team.conference,
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
          ${formatTeamMetaLine(team)}
          <span class="count-pill">${playerCount} players</span>
          <span class="count-pill">${slapCount} IDs</span>
        </small>
      </div>
    `;
  }).join("");
}

function titleCaseValue(value) {
  return cleanText(value)
    .replace(/_/g, " ")
    .replace(/\b\w/g, letter => letter.toUpperCase());
}

function formatTeamMetaLine(team) {
  const pieces = [
    team.region ? titleCaseValue(team.region) : "Unknown Region",
    team.division ? titleCaseValue(team.division) : "No Division",
    team.conference ? titleCaseValue(team.conference) : ""
  ].filter(Boolean);

  return pieces.join(" · ");
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
    jersey_number: "",
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
    season_id: rosterData?.season_id || "summer_2026",
    region: "",
    division: "",
    conference: "",
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
          ${selectOption("", team.region, "Unknown")}
          ${selectOption("east", team.region, "East")}
          ${selectOption("central", team.region, "Central")}
          ${selectOption("west", team.region, "West")}
        </select>
      </label>

      <label>
        Division
        <select onchange="updateTeamField('division', this.value)">
          ${selectOption("", team.division, "None")}
          ${selectOption("pro", team.division, "Pro")}
          ${selectOption("challenger", team.division, "Challenger")}
          ${selectOption("intermediate", team.division, "Intermediate")}
          ${selectOption("prospect", team.division, "Prospect")}
          ${selectOption("open", team.division, "Open")}
          ${selectOption("central_a", team.division, "Central A")}
          ${selectOption("central_b", team.division, "Central B")}
          ${selectOption("central_c", team.division, "Central C")}
          ${selectOption("central_d", team.division, "Central D")}
          ${selectOption("masters", team.division, "Masters")}
          ${selectOption("contenders", team.division, "Contenders")}
        </select>
      </label>

      <label>
        Conference
        <select onchange="updateTeamField('conference', this.value)">
          ${selectOption("", team.conference, "None")}
          ${selectOption("1", team.conference, "1")}
          ${selectOption("2", team.conference, "2")}
          ${selectOption("3", team.conference, "3")}
          ${selectOption("4", team.conference, "4")}
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
        Number
        <input
          value="${escapeAttr(player.jersey_number || "")}"
          oninput="updatePlayer(${index}, 'jersey_number', this.value)"
          placeholder="00"
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
  teams.forEach(team => {
    ensureTeamSeasonFields(team);
    rebuildSlapIds(team);
  });

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

def clean(value):
    return str(value or "").strip()


def load_json(path, fallback):
    if not path.exists():
        return fallback

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def utc_now_iso():
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def get_roster_teams(roster_data):
    if isinstance(roster_data, dict) and isinstance(roster_data.get("teams"), list):
        return roster_data["teams"]

    if isinstance(roster_data, list):
        return roster_data

    return []


def get_team_id(team):
    return clean(team.get("team_id"))


def get_team_display_name(team):
    return clean(
        team.get("team_display_name")
        or team.get("team")
        or team.get("team_name")
        or get_team_id(team)
    )


def get_team_abbreviation(team):
    return clean(
        team.get("team_abbreviation")
        or team.get("abbreviation")
        or get_team_display_name(team)[:3].upper()
    )


def get_player_slap_id(player):
    return clean(
        player.get("slap_id")
        or player.get("game_user_id")
    )


def get_player_id(player):
    value = clean(
        player.get("player_id")
        or player.get("url_id")
        or player.get("id")
    )

    if value:
        return value

    return make_id(
        get_player_display_name(player)
        or get_player_slap_id(player)
        or "unknown_player"
    )


def get_player_display_name(player):
    return clean(
        player.get("player_display_name")
        or player.get("steam_name")
        or player.get("display_name")
        or player.get("player_name")
        or player.get("name")
        or player.get("username")
        or get_player_slap_id(player)
        or "Unknown Player"
    )


def get_player_jersey_number(player):
    return clean(
        player.get("jersey_number")
        or player.get("number")
    )


def make_id(value, fallback="unknown"):
    text = clean(value).lower()

    text = text.replace("&", "and")
    text = text.replace("$", "s")
    text = text.replace("@", "a")
    text = text.replace("!", "i")
    text = text.replace("’", "")
    text = text.replace("'", "")

    import re
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")

    return text or fallback


def make_player_audit_key(team, player):
    team_id = get_team_id(team)
    slap_id = get_player_slap_id(player)
    player_id = get_player_id(player)

    if team_id and slap_id:
        return f"{team_id}::{slap_id}"

    return f"{team_id}::{player_id}"


def build_player_lookup(roster_data):
    lookup = {}

    for team in get_roster_teams(roster_data):
        for player in team.get("players", []) or []:
            key = make_player_audit_key(team, player)

            if not key:
                continue

            lookup[key] = {
                "team": team,
                "player": player,
            }

    return lookup


def load_transactions():
    return load_json(TRANSACTIONS_FILE, {
        "season_id": SEASON_ID,
        "transactions": []
    })


def make_transaction_id(created_at_utc, team_id, action, player_id, slap_id):
    timestamp = (
        clean(created_at_utc)
        .replace("-", "")
        .replace(":", "")
        .replace(".", "")
        .replace("+", "")
    )

    safe_player = clean(player_id or slap_id or "unknown_player")

    return "_".join([
        timestamp,
        clean(team_id) or "unknown_team",
        clean(action) or "unknown_action",
        safe_player,
    ])


def make_roster_transaction(action, team, player, previous_player=None):
    created_at_utc = utc_now_iso()

    team_id = get_team_id(team)
    player_id = get_player_id(player)
    slap_id = get_player_slap_id(player)

    return {
        "transaction_id": make_transaction_id(
            created_at_utc,
            team_id,
            action,
            player_id,
            slap_id,
        ),
        "created_at_utc": created_at_utc,

        "type": action,

        "team_id": team_id,
        "team_abbreviation": get_team_abbreviation(team),
        "team_display_name": get_team_display_name(team),
        "division": clean(team.get("division")),
        "region": clean(team.get("region")),
        "conference": clean(team.get("conference")),

        "player_id": player_id,
        "player_display_name": get_player_display_name(player),
        "slap_id": slap_id,
        "jersey_number": get_player_jersey_number(player),

        "previous_jersey_number": get_player_jersey_number(previous_player or {}),
        "source": "active_roster_editor",
    }


def append_roster_transactions(transactions_to_add):
    if not transactions_to_add:
        return []

    data = load_transactions()
    transactions = data.setdefault("transactions", [])

    existing_ids = {
        clean(row.get("transaction_id"))
        for row in transactions
    }

    added = []

    for transaction in transactions_to_add:
        transaction_id = clean(transaction.get("transaction_id"))

        if transaction_id in existing_ids:
            continue

        transactions.append(transaction)
        existing_ids.add(transaction_id)
        added.append(transaction)

    data["transactions"] = sorted(
        transactions,
        key=lambda row: clean(row.get("created_at_utc")),
        reverse=True,
    )

    write_json(TRANSACTIONS_FILE, data)

    return added


def build_roster_transactions_from_diff(old_roster_data, new_roster_data):
    old_lookup = build_player_lookup(old_roster_data)
    new_lookup = build_player_lookup(new_roster_data)

    old_keys = set(old_lookup.keys())
    new_keys = set(new_lookup.keys())

    transactions = []

    for key in sorted(new_keys - old_keys):
        row = new_lookup[key]

        transactions.append(
            make_roster_transaction(
                "add",
                row["team"],
                row["player"],
            )
        )

    for key in sorted(old_keys - new_keys):
        row = old_lookup[key]

        transactions.append(
            make_roster_transaction(
                "remove",
                row["team"],
                row["player"],
            )
        )

    return transactions




## Start of helper functions for press release template


def get_transaction_day_key(transaction):
    created_at = clean(transaction.get("created_at_utc"))

    if "T" in created_at:
        return created_at.split("T", 1)[0]

    return created_at[:10] or utc_now_iso().split("T", 1)[0]


def group_transactions_for_press_releases(transactions):
    groups = {}

    for transaction in transactions:
        day_key = get_transaction_day_key(transaction)
        team_id = clean(transaction.get("team_id")) or "unknown_team"

        group_key = f"{day_key}_{team_id}_roster_moves"

        if group_key not in groups:
            groups[group_key] = {
                "draft_id": group_key,
                "day_key": day_key,
                "created_at_utc": clean(transaction.get("created_at_utc")) or utc_now_iso(),

                "team_id": clean(transaction.get("team_id")),
                "team_abbreviation": clean(transaction.get("team_abbreviation")),
                "team_display_name": clean(transaction.get("team_display_name")),
                "division": clean(transaction.get("division")),
                "region": clean(transaction.get("region")),
                "conference": clean(transaction.get("conference")),

                "transactions": [],
            }

        groups[group_key]["transactions"].append(transaction)

        if clean(transaction.get("created_at_utc")) > clean(groups[group_key].get("created_at_utc")):
            groups[group_key]["created_at_utc"] = clean(transaction.get("created_at_utc"))

    return list(groups.values())

def make_slug(value):
    return make_id(value).replace("_", "-")


def load_press_release_drafts():
    return load_json(PRESS_RELEASE_DRAFTS_FILE, {
        "season_id": SEASON_ID,
        "drafts": []
    })


def get_short_team_name(transaction):
    team_name = clean(transaction.get("team_display_name"))

    replacements = [
        "Long Island ",
        "Atlantic City ",
        "Battle Creek ",
        "Camden ",
        "Yucatan ",
    ]

    for replacement in replacements:
        if team_name.startswith(replacement):
            return team_name.replace(replacement, "", 1)

    return team_name or clean(transaction.get("team_abbreviation")) or "the team"


def get_jersey_prefix(transaction):
    jersey_number = clean(transaction.get("jersey_number"))

    if not jersey_number:
        return ""

    return f"#{jersey_number} "


def make_grouped_press_release_headline(group):
    team_name = clean(group.get("team_display_name")) or "Unknown Team"
    transactions = group.get("transactions", [])

    adds = [
        transaction for transaction in transactions
        if clean(transaction.get("type")).lower() == "add"
    ]

    removes = [
        transaction for transaction in transactions
        if clean(transaction.get("type")).lower() == "remove"
    ]

    if len(transactions) == 1:
        transaction = transactions[0]
        player_name = clean(transaction.get("player_display_name")) or "Unknown Player"
        transaction_type = clean(transaction.get("type")).lower()

        if transaction_type == "add":
            return f"{team_name} Add {player_name}"

        if transaction_type == "remove":
            return f"{team_name} Remove {player_name}"

    if adds and removes:
        return f"{team_name} Make Roster Moves"

    if adds:
        return f"{team_name} Add {len(adds)} Player{'s' if len(adds) != 1 else ''}"

    if removes:
        return f"{team_name} Remove {len(removes)} Player{'s' if len(removes) != 1 else ''}"

    return f"{team_name} Update Roster"


def format_transaction_player_name(transaction):
    player_name = clean(transaction.get("player_display_name")) or "Unknown Player"
    jersey_number = clean(transaction.get("jersey_number"))

    if jersey_number:
        return f"#{jersey_number} {player_name}"

    return player_name


def join_names(names):
    names = [name for name in names if clean(name)]

    if not names:
        return ""

    if len(names) == 1:
        return names[0]

    if len(names) == 2:
        return f"{names[0]} and {names[1]}"

    return f"{', '.join(names[:-1])}, and {names[-1]}"


def make_grouped_press_release_subheadline(group):
    short_team_name = get_short_team_name(group)
    transactions = group.get("transactions", [])

    added_players = [
        format_transaction_player_name(transaction)
        for transaction in transactions
        if clean(transaction.get("type")).lower() == "add"
    ]

    removed_players = [
        format_transaction_player_name(transaction)
        for transaction in transactions
        if clean(transaction.get("type")).lower() == "remove"
    ]

    added_text = join_names(added_players)
    removed_text = join_names(removed_players)

    if added_text and removed_text:
        return f"The {short_team_name} have added {added_text} and removed {removed_text} from their active roster."

    if added_text:
        return f"The {short_team_name} have added {added_text} to their active roster."

    if removed_text:
        return f"The {short_team_name} have removed {removed_text} from their active roster."

    return f"The {short_team_name} have updated their active roster."


def make_grouped_press_release_body(group):
    team_name = clean(group.get("team_display_name")) or "Unknown Team"
    short_team_name = get_short_team_name(group)
    transactions = group.get("transactions", [])

    added_players = [
        format_transaction_player_name(transaction)
        for transaction in transactions
        if clean(transaction.get("type")).lower() == "add"
    ]

    removed_players = [
        format_transaction_player_name(transaction)
        for transaction in transactions
        if clean(transaction.get("type")).lower() == "remove"
    ]

    paragraphs = []

    if added_players and removed_players:
        paragraphs.append(
            f"The {team_name} have added {join_names(added_players)} and removed "
            f"{join_names(removed_players)} from their active roster."
        )
    elif added_players:
        paragraphs.append(
            f"The {team_name} have added {join_names(added_players)} to their active roster "
            f"adding another card to their deck."
        )
    elif removed_players:
        paragraphs.append(
            f"The {team_name} have removed {join_names(removed_players)} from their active roster."
        )
    else:
        paragraphs.append(
            f"The {team_name} have updated their active roster during the Summer 2026 regular season."
        )

    if added_players:
        paragraphs.append(
            f"The move gives the {short_team_name} another option as they continue to shape their roster "
            f"for the current campaign."
        )

    if removed_players:
        paragraphs.append(
            f"The departing player{'s' if len(removed_players) != 1 else ''} will no longer be listed "
            f"on the club's active roster."
        )

    paragraphs.append("Further details may be added by SPL staff.")

    return "\n\n".join(paragraphs)


def make_grouped_press_release_draft(group):
    draft_id = clean(group.get("draft_id"))
    created_at_utc = clean(group.get("created_at_utc")) or utc_now_iso()

    headline = make_grouped_press_release_headline(group)

    transactions = group.get("transactions", [])

    transaction_ids = [
        clean(transaction.get("transaction_id"))
        for transaction in transactions
        if clean(transaction.get("transaction_id"))
    ]

    players = []

    for transaction in transactions:
        players.append({
            "type": clean(transaction.get("type")),
            "player_id": clean(transaction.get("player_id")),
            "player_display_name": clean(transaction.get("player_display_name")),
            "slap_id": clean(transaction.get("slap_id")),
            "jersey_number": clean(transaction.get("jersey_number")),
        })

    tags = [
        "transactions",
        "roster",
        clean(group.get("team_id")),
        clean(group.get("division")),
    ]

    tags = [tag for tag in tags if tag]

    return {
        "draft_id": draft_id,
        "transaction_ids": transaction_ids,

        # Keep this for backwards compatibility with single-transaction drafts.
        "transaction_id": transaction_ids[0] if len(transaction_ids) == 1 else "",

        "status": "draft",
        "created_at_utc": created_at_utc,
        "updated_at_utc": created_at_utc,

        "headline": headline,
        "subheadline": make_grouped_press_release_subheadline(group),
        "slug": make_slug(headline),

        "team_id": clean(group.get("team_id")),
        "team_abbreviation": clean(group.get("team_abbreviation")),
        "team_display_name": clean(group.get("team_display_name")),
        "division": clean(group.get("division")),
        "region": clean(group.get("region")),
        "conference": clean(group.get("conference")),

        "players": players,

        "article_type": "transaction",
        "tags": tags,

        "body_markdown": make_grouped_press_release_body(group),

        "writer_notes": "",
        "created_by": "active_roster_editor",
        "last_edited_by": "",
    }


def append_press_release_drafts_for_transactions(transactions):
    if not transactions:
        return []

    data = load_press_release_drafts()
    drafts = data.setdefault("drafts", [])

    existing_draft_ids = {
        clean(draft.get("draft_id"))
        for draft in drafts
    }

    groups = group_transactions_for_press_releases(transactions)

    added = []

    for group in groups:
        draft = make_grouped_press_release_draft(group)
        draft_id = clean(draft.get("draft_id"))

        if not draft_id:
            continue

        if draft_id in existing_draft_ids:
            continue

        drafts.append(draft)
        existing_draft_ids.add(draft_id)
        added.append(draft)

    data["drafts"] = sorted(
        drafts,
        key=lambda row: clean(row.get("created_at_utc")),
        reverse=True,
    )

    write_json(PRESS_RELEASE_DRAFTS_FILE, data)

    return added

## End of helper functions for press release template

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

        old_data = load_json(ROSTERS_FILE, {"teams": []})

        transactions_to_add = build_roster_transactions_from_diff(
            old_data,
            data,
        )

        ROSTERS_FILE.parent.mkdir(parents=True, exist_ok=True)

        with ROSTERS_FILE.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
            file.write("\n")

        try:
            added_transactions = append_roster_transactions(transactions_to_add)
        except Exception as error:
            print(f"WARNING: Roster saved, but transaction audit failed: {error}")
            added_transactions = []

        try:
            added_drafts = append_press_release_drafts_for_transactions(added_transactions)
        except Exception as error:
            print(f"WARNING: Roster saved, but press release draft generation failed: {error}")
            added_drafts = []

        self._send(
            200,
            (
                f"Saved. "
                f"Logged {len(added_transactions)} roster transaction(s). "
                f"Created {len(added_drafts)} press release draft(s)."
            )
        )

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