import json
import re
import subprocess
import sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent.parent
ALIASES_FILE = BASE_DIR / "data" / "player_aliases.json"
UPDATE_ALL_SCRIPT = BASE_DIR / "tools" / "update_all.py"
HOST = "localhost"
PORT = 8765


def load_aliases():
    if not ALIASES_FILE.exists():
        return []

    with ALIASES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)

def run_data_builders():
    if not UPDATE_ALL_SCRIPT.exists():
        return {
            "ok": False,
            "output": f"Could not find update_all.py at:\n{UPDATE_ALL_SCRIPT}"
        }

    try:
        result = subprocess.run(
            [sys.executable, str(UPDATE_ALL_SCRIPT)],
            cwd=UPDATE_ALL_SCRIPT.parent,
            capture_output=True,
            text=True
        )

        output = ""

        if result.stdout:
            output += result.stdout

        if result.stderr:
            output += "\n\n--- STDERR ---\n"
            output += result.stderr

        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "output": output.strip() or "No output."
        }

    except Exception as error:
        return {
            "ok": False,
            "output": str(error)
        }

def save_aliases(data):
    ALIASES_FILE.parent.mkdir(parents=True, exist_ok=True)

    data.sort(
        key=lambda entry: entry.get("player_display_name", "").lower()
    )

    with ALIASES_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def make_player_id(name):
    text = str(name or "").strip().lower()
    text = re.sub(r"[^a-z0-9_\-\s]", "", text)
    text = re.sub(r"[\s\-]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_") or "unknown_player"


HTML = r"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>SPLStats Alias Admin</title>
  <style>
    :root {
        --bg: #05080c;
        --card: #101821;
        --card2: #0b1118;
        --teal: #00d1d1;
        --gold: #ffd166;
        --red: #ff4d4d;
        --text: #e8f0f2;
        --muted: #8ea3aa;
    }

    body {
        margin: 0;
        font-family: Arial, sans-serif;
        background: radial-gradient(circle at top, #142536, var(--bg) 45%);
        color: var(--text);
    }

    header {
        padding: 24px 32px;
        border-bottom: 1px solid rgba(255,255,255,.12);
        background: rgba(0,0,0,.35);
        position: sticky;
        top: 0;
        z-index: 5;
        backdrop-filter: blur(8px);
    }

    h1 {
        margin: 0;
        color: var(--teal);
        letter-spacing: .04em;
    }

    .status {
        margin-top: 8px;
        color: var(--muted);
        font-size: .9rem;
    }

    main {
        display: grid;
        grid-template-columns: 360px 1fr;
        gap: 20px;
        padding: 24px;
        max-width: 1400px;
        margin: 0 auto;
    }

    .panel {
        background: linear-gradient(135deg, var(--card), var(--card2));
        border: 1px solid rgba(255,255,255,.12);
        border-radius: 14px;
        padding: 18px;
        box-shadow: 0 10px 28px rgba(0,0,0,.35);
    }

    input, textarea {
        width: 100%;
        box-sizing: border-box;
        background: #071018;
        color: var(--text);
        border: 1px solid rgba(255,255,255,.18);
        border-radius: 10px;
        padding: 10px 12px;
        font-size: 1rem;
    }

    label {
        display: block;
        color: var(--muted);
        font-size: .78rem;
        text-transform: uppercase;
        letter-spacing: .08em;
        margin: 14px 0 6px;
        font-weight: bold;
    }

    button {
        cursor: pointer;
        border: 0;
        border-radius: 10px;
        padding: 10px 14px;
        font-weight: 800;
        color: #041014;
        background: var(--teal);
        margin-top: 10px;
    }

    button.secondary {
        background: #2a3944;
        color: var(--text);
    }

    button.danger {
        background: var(--red);
        color: white;
    }

    button.gold {
        background: var(--gold);
        color: #201600;
    }

    .button-row {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
    }

    .player-list {
        margin-top: 14px;
        max-height: 68vh;
        overflow: auto;
    }

    .player-item {
        padding: 10px 12px;
        border-radius: 10px;
        margin-bottom: 8px;
        background: rgba(255,255,255,.045);
        border: 1px solid rgba(255,255,255,.08);
        cursor: pointer;
    }

    .player-item:hover,
    .player-item.active {
        border-color: var(--teal);
        background: rgba(0,209,209,.12);
    }

    .player-id {
        color: var(--muted);
        font-size: .78rem;
        margin-top: 4px;
    }

    .alias-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 7px 10px;
        margin: 5px 5px 0 0;
        border: 1px solid rgba(255,255,255,.16);
        background: rgba(255,255,255,.06);
        border-radius: 999px;
    }

    .alias-pill button {
        margin: 0;
        padding: 2px 6px;
        border-radius: 999px;
        background: rgba(255,77,77,.85);
        color: white;
        font-size: .75rem;
    }

    .hint {
        color: var(--muted);
        font-size: .88rem;
        line-height: 1.4;
    }

    .builder-output {
        margin-top: 8px;
        max-height: 320px;
        overflow: auto;

        background: #020609;
        color: #d8f6f6;

        border: 1px solid rgba(255,255,255,.14);
        border-radius: 12px;

        padding: 14px;
        white-space: pre-wrap;

        font-family: Consolas, Monaco, monospace;
        font-size: 0.82rem;
        line-height: 1.35;
    }

    .big-number {
        color: var(--gold);
        font-weight: 900;
    }

    @media (max-width: 900px) {
        main {
            grid-template-columns: 1fr;
        }
    }
  </style>
</head>
<body>
<header>
  <h1>SPLStats Alias Admin</h1>
  <div class="status" id="status">Loading...</div>
</header>

<main>
  <section class="panel">
    <label>Search</label>
    <input id="searchInput" placeholder="Search display name, alias, or player_id">

    <div class="button-row">
      <button class="gold" onclick="newPlayer()">Add New Player</button>
      <button class="secondary" onclick="reloadData()">Reload</button>
    </div>

    <div class="player-list" id="playerList"></div>
  </section>

  <section class="panel">
    <h2 id="editorTitle">Select a player</h2>

    <div class="hint">
      Edits save directly to <span class="big-number">data/player_aliases.json</span>.
      Keep <strong>player_id</strong> stable. Change display name freely.
    </div>

    <label>Player ID</label>
    <input id="playerIdInput" placeholder="noob_weapons">

    <label>Display Name</label>
    <input id="displayNameInput" placeholder="Noob_Weapons">

    <label>Add Alias</label>
    <input id="newAliasInput" placeholder="Old name or alternate spelling">
    <button onclick="addAlias()">Add Alias</button>

    <label>Aliases</label>
    <div id="aliasesList"></div>

    <label>Slap IDs</label>
    <div class="hint">Leave blank for now. This is ready for game-log identity later.</div>
    <input id="newSlapIdInput" placeholder="7656119...">
    <button onclick="addSlapId()">Add Slap ID</button>
    <div id="slapIdsList"></div>

    <div class="button-row" style="margin-top: 22px;">
      <button onclick="saveCurrent()">Save Player</button>
      <button class="gold" onclick="rebuildData()">Rebuild Data</button>
      <button class="secondary" onclick="copyJson()">Copy JSON</button>
      <button class="danger" onclick="deleteCurrent()">Delete Player</button>
    </div>

    <label>Builder Output</label>
    <pre id="builderOutput" class="builder-output">No rebuild run yet.</pre>
  </section>
</main>

<script>
let aliases = [];
let selectedIndex = -1;

function normalize(value) {
  return String(value || "").trim().toLowerCase();
}

function makePlayerId(name) {
  return String(name || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_\-\s]/g, "")
    .replace(/[\s\-]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "") || "unknown_player";
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json();
}

async function reloadData() {
  aliases = await api("/api/aliases");
  selectedIndex = -1;
  renderList();
  renderEditor();
  setStatus(`Loaded ${aliases.length} players.`);
}

function setStatus(message) {
  document.getElementById("status").textContent = message;
}

function filteredAliases() {
  const query = normalize(document.getElementById("searchInput").value);

  if (!query) return aliases;

  return aliases.filter(entry => {
    const haystack = [
      entry.player_id,
      entry.player_display_name,
      ...(entry.aliases || []),
      ...(entry.slap_ids || [])
    ].map(normalize).join(" | ");

    return haystack.includes(query);
  });
}

function renderList() {
  const list = document.getElementById("playerList");
  const filtered = filteredAliases();

  list.innerHTML = filtered.map(entry => {
    const realIndex = aliases.indexOf(entry);
    const active = realIndex === selectedIndex ? "active" : "";

    return `
      <div class="player-item ${active}" onclick="selectPlayer(${realIndex})">
        <strong>${entry.player_display_name || "Unnamed"}</strong>
        <div class="player-id">${entry.player_id}</div>
      </div>
    `;
  }).join("");
}

function selectPlayer(index) {
  selectedIndex = index;
  renderList();
  renderEditor();
}

function currentEntry() {
  return aliases[selectedIndex] || null;
}

function renderEditor() {
  const entry = currentEntry();

  document.getElementById("editorTitle").textContent =
    entry ? entry.player_display_name : "Select a player";

  document.getElementById("playerIdInput").value = entry?.player_id || "";
  document.getElementById("displayNameInput").value = entry?.player_display_name || "";
  document.getElementById("newAliasInput").value = "";
  document.getElementById("newSlapIdInput").value = "";

  document.getElementById("aliasesList").innerHTML = entry
    ? (entry.aliases || []).map((alias, i) => `
        <span class="alias-pill">
          ${alias}
          <button onclick="removeAlias(${i})">x</button>
        </span>
      `).join("")
    : "";

  document.getElementById("slapIdsList").innerHTML = entry
    ? (entry.slap_ids || []).map((id, i) => `
        <span class="alias-pill">
          ${id}
          <button onclick="removeSlapId(${i})">x</button>
        </span>
      `).join("")
    : "";
}

function newPlayer() {
  const displayName = prompt("Display name for new player?");
  if (!displayName) return;

  const playerId = makePlayerId(displayName);

  aliases.push({
    player_id: playerId,
    player_display_name: displayName,
    aliases: [displayName],
    slap_ids: []
  });

  selectedIndex = aliases.length - 1;
  renderList();
  renderEditor();
  setStatus("New player created. Press Save Player to write file.");
}

function addAlias() {
  const entry = currentEntry();
  if (!entry) return;

  const input = document.getElementById("newAliasInput");
  const alias = input.value.trim();
  if (!alias) return;

  entry.aliases = entry.aliases || [];

  if (!entry.aliases.some(a => normalize(a) === normalize(alias))) {
    entry.aliases.push(alias);
  }

  input.value = "";
  renderEditor();
}

function removeAlias(index) {
  const entry = currentEntry();
  if (!entry) return;

  entry.aliases.splice(index, 1);
  renderEditor();
}

function addSlapId() {
  const entry = currentEntry();
  if (!entry) return;

  const input = document.getElementById("newSlapIdInput");
  const id = input.value.trim();
  if (!id) return;

  entry.slap_ids = entry.slap_ids || [];

  if (!entry.slap_ids.some(existing => normalize(existing) === normalize(id))) {
    entry.slap_ids.push(id);
  }

  input.value = "";
  renderEditor();
}

function removeSlapId(index) {
  const entry = currentEntry();
  if (!entry) return;

  entry.slap_ids.splice(index, 1);
  renderEditor();
}

function applyEditorToCurrent() {
  const entry = currentEntry();
  if (!entry) return null;

  const playerId = document.getElementById("playerIdInput").value.trim();
  const displayName = document.getElementById("displayNameInput").value.trim();

  if (!playerId || !displayName) {
    alert("Player ID and Display Name are required.");
    return null;
  }

  entry.player_id = playerId;
  entry.player_display_name = displayName;
  entry.aliases = entry.aliases || [];
  entry.slap_ids = entry.slap_ids || [];

  if (!entry.aliases.some(alias => normalize(alias) === normalize(displayName))) {
    entry.aliases.unshift(displayName);
  }

  return entry;
}

function validateAliases() {
  const ids = new Map();
  const aliasMap = new Map();
  const errors = [];

  aliases.forEach(entry => {
    const idKey = normalize(entry.player_id);

    if (ids.has(idKey)) {
      errors.push(`Duplicate player_id: ${entry.player_id}`);
    }

    ids.set(idKey, entry);

    for (const alias of entry.aliases || []) {
      const aliasKey = normalize(alias);

      if (aliasMap.has(aliasKey) && aliasMap.get(aliasKey) !== entry) {
        errors.push(`Alias "${alias}" is used by multiple players.`);
      }

      aliasMap.set(aliasKey, entry);
    }
  });

  return errors;
}

async function rebuildData() {
  const confirmed = confirm(
    "Are you sure you want to rebuild SPLStats data?\n\n" +
    "This will save aliases, rerun the data builders, and overwrite generated JSON files."
  );

  if (!confirmed) {
    return;
  }

  applyEditorToCurrent();

  const errors = validateAliases();

  if (errors.length) {
    alert("Fix these before rebuilding:\n\n" + errors.join("\n"));
    return;
  }

  const output = document.getElementById("builderOutput");

  output.textContent = "Saving aliases...\n";
  setStatus("Saving aliases...");

  try {
    await api("/api/aliases", {
      method: "POST",
      body: JSON.stringify(aliases)
    });

    output.textContent += "Running data builders...\nPlease wait.";
    setStatus("Running data builders...");

    const result = await api("/api/rebuild", {
      method: "POST",
      body: JSON.stringify({})
    });

    output.textContent = result.output || "Rebuild finished.";
    setStatus("Data rebuild completed.");

  } catch (error) {
    output.textContent = String(error);
    setStatus("Data rebuild failed.");
  }
}

async function saveCurrent() {
  applyEditorToCurrent();

  const errors = validateAliases();

  if (errors.length) {
    alert("Fix these before saving:\\n\\n" + errors.join("\\n"));
    return;
  }

  const result = await api("/api/aliases", {
    method: "POST",
    body: JSON.stringify(aliases)
  });

  aliases = result.aliases;
  renderList();
  renderEditor();
  setStatus(`Saved ${aliases.length} players.`);
}

function deleteCurrent() {
  const entry = currentEntry();
  if (!entry) return;

  if (!confirm(`Delete ${entry.player_display_name}?`)) return;

  aliases.splice(selectedIndex, 1);
  selectedIndex = -1;
  renderList();
  renderEditor();
  setStatus("Deleted locally. Press Save Player to write file.");
}

async function copyJson() {
  applyEditorToCurrent();
  await navigator.clipboard.writeText(JSON.stringify(aliases, null, 2));
  setStatus("Copied JSON to clipboard.");
}

document.getElementById("searchInput").addEventListener("input", renderList);

reloadData();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, text, status=200, content_type="text/plain"):
        body = text.encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/" or path == "/alias-admin":
            return self.send_text(HTML, content_type="text/html")

        if path == "/api/aliases":
            return self.send_json(load_aliases())

        return self.send_text("Not found", status=404)

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/rebuild":
            result = run_data_builders()

            status = 200 if result.get("ok") else 500

            return self.send_json(
                result,
                status=status
            )

        if path != "/api/aliases":
            return self.send_text("Not found", status=404)

        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8")

        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError:
            return self.send_text("Invalid JSON", status=400)

        if not isinstance(data, list):
            return self.send_text("Expected a list of aliases", status=400)

        save_aliases(data)

        return self.send_json({
            "ok": True,
            "aliases": load_aliases()
        })


def main():
    print()
    print("SPLStats Alias Admin")
    print("=" * 40)
    print(f"Editing: {ALIASES_FILE.resolve()}")
    print(f"Open: http://{HOST}:{PORT}")
    print()
    print("Press Ctrl+C to stop.")
    print()

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()