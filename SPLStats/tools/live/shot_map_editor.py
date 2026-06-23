import json
import mimetypes
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


BASE_DIR = Path(__file__).resolve().parents[2]

HOST = "localhost"
PORT = 8782

SEASON_ID = "summer_2026"
PHASE = "preseason"

DATA_DIR = BASE_DIR / "data" / "live_season" / SEASON_ID / PHASE
SHOT_MAP_DIR = DATA_DIR / "shot_maps"

SCHEDULE_FILE = DATA_DIR / "schedule.json"
ROSTER_SNAPSHOTS_FILE = DATA_DIR / "roster_snapshots.json"
TEAM_METADATA_FILE = BASE_DIR / "data" / "team_metadata.json"


APP_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SPL Shot Map Editor</title>

  <style>
    :root {
      --bg: #05080c;
      --panel: #0c141c;
      --panel-2: #111c26;
      --text: #f4f4f4;
      --muted: #9fb3c8;
      --teal: #7bdff2;
      --gold: #ffd166;
      --green: #5cff9d;
      --red: #ff6b6b;
      --orange: #ff9f1c;
      --line: rgba(123, 223, 242, 0.22);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      background:
        radial-gradient(circle at top right, rgba(0, 209, 209, 0.13), transparent 34%),
        linear-gradient(135deg, #05080c, #08111a);
      color: var(--text);
      font-family: Arial, sans-serif;
    }

    header {
      padding: 22px;
      border-bottom: 3px solid #00d1d1;
      background: rgba(5, 8, 12, 0.88);
      box-shadow: 0 10px 28px rgba(0, 0, 0, 0.4);
    }

    h1 {
      margin: 0;
      color: var(--teal);
      font-size: 2rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      text-shadow: -2px 2px 0 #000;
    }

    header p {
      margin: 8px 0 0;
      color: var(--muted);
      font-weight: 800;
    }

    main {
      width: min(1500px, calc(100% - 28px));
      margin: 18px auto 40px;
      display: grid;
      grid-template-columns: 320px minmax(0, 1fr) 360px;
      gap: 16px;
    }

    .panel {
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(12, 20, 28, 0.94);
      box-shadow: 0 10px 26px rgba(0, 0, 0, 0.28);
    }

    .panel h2 {
      margin: 0 0 12px;
      color: var(--teal);
      font-size: 1.1rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    label {
      display: block;
      margin: 12px 0 6px;
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 1000;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    select,
    input {
      width: 100%;
      padding: 10px;
      border: 1px solid #244255;
      border-radius: 10px;
      background: #071018;
      color: var(--text);
      font-weight: 800;
    }

    button {
      border: 1px solid rgba(123, 223, 242, 0.34);
      border-radius: 10px;
      background: rgba(123, 223, 242, 0.09);
      color: var(--text);
      padding: 10px 12px;
      font-weight: 1000;
      cursor: pointer;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    button:hover {
      border-color: rgba(123, 223, 242, 0.75);
      background: rgba(123, 223, 242, 0.16);
    }

    button.active {
      border-color: var(--gold);
      color: var(--gold);
      background: rgba(255, 209, 102, 0.15);
    }

    .button-row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    .button-row button {
      flex: 1 1 auto;
    }

    .match-summary {
      margin-top: 12px;
      padding: 12px;
      border-radius: 12px;
      background: rgba(0, 0, 0, 0.22);
      color: var(--muted);
      font-weight: 800;
      line-height: 1.45;
    }

    .team-name {
      color: #ffffff;
      font-weight: 1000;
    }

    .rink-panel {
      min-width: 0;
    }

    .rink-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
      flex-wrap: wrap;
    }

    .rink-toolbar strong {
      color: var(--gold);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .attack-label-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;

        margin: 0 8px 8px;
    }

        .attack-label {
        color: rgba(255, 255, 255, 0.78);

        font-size: 0.78rem;
        font-weight: 1000;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }

    .attack-label.left {
        text-align: left;
    }

        .attack-label.right {
        text-align: right;
    }

    .rink {
        position: relative;
        width: 100%;
        overflow: hidden;

        border: 2px solid rgba(123, 223, 242, 0.38);
        border-radius: 22px;

        background: #000;

        box-shadow:
            inset 0 0 28px rgba(255, 255, 255, 0.035),
            0 14px 34px rgba(0, 0, 0, 0.42);

        cursor: crosshair;
    }

    .pellet {
        position: absolute;

        width: 18px;
        height: 18px;

        z-index: 5;

        border-radius: 999px;
        transform: translate(-50%, -50%);

        border: 2px solid #000;

        box-shadow:
            0 0 0 2px rgba(255, 255, 255, 0.72),
            0 0 12px rgba(255, 255, 255, 0.35),
            0 2px 8px rgba(0, 0, 0, 0.85);

        cursor: pointer;
    }

    .rink-image {
        display: block;
        width: 100%;
        height: auto;

        user-select: none;
        pointer-events: none;
    }

    .pellet-layer {
        position: absolute;
        inset: 0;
        z-index: 2;

        pointer-events: none;
    }

    .pellet {
        position: absolute;

        width: 18px;
        height: 18px;

        border-radius: 999px;
        transform: translate(-50%, -50%);

        border: 2px solid #000;

        box-shadow:
            0 0 0 2px rgba(255, 255, 255, 0.72),
            0 0 12px rgba(255, 255, 255, 0.35),
            0 2px 8px rgba(0, 0, 0, 0.85);

        cursor: pointer;
        pointer-events: auto;
        z-index: 5;
    }

    .pellet.goal {
      background: var(--green);
    }

    .pellet.shot_on_goal {
      background: var(--teal);
    }

    .pellet.shot_blocked {
      background: var(--orange);
    }

    .pellet.selected {
      outline: 3px solid var(--gold);
      z-index: 20;
    }

    .shot-form {
      display: none;
    }

    .shot-form.open {
      display: block;
    }

    .player-pellets {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 8px;
    }

    .player-pellets button {
      flex: 1 1 auto;
      padding: 8px 9px;
      font-size: 0.78rem;
      text-transform: none;
      letter-spacing: 0;
    }

    .result-goal.active {
      border-color: var(--green);
      color: var(--green);
    }

    .result-sog.active {
      border-color: var(--teal);
      color: var(--teal);
    }

    .result-blocked.active {
      border-color: var(--orange);
      color: var(--orange);
    }

    .save-button {
      width: 100%;
      margin-top: 14px;
      border-color: var(--green);
      color: var(--green);
      background: rgba(92, 255, 157, 0.10);
    }

    .delete-button {
      width: 100%;
      margin-top: 8px;
      border-color: var(--red);
      color: var(--red);
      background: rgba(255, 107, 107, 0.10);
    }

    .shot-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      max-height: 60vh;
      overflow: auto;
      padding-right: 4px;
    }

    .shot-item {
      padding: 10px;
      border: 1px solid rgba(123, 223, 242, 0.18);
      border-radius: 12px;
      background: rgba(0, 0, 0, 0.20);
      cursor: pointer;
    }

    .shot-item:hover {
      border-color: rgba(123, 223, 242, 0.55);
    }

    .shot-item strong {
      color: #ffffff;
      display: block;
      margin-bottom: 3px;
    }

    .shot-item span {
      color: var(--muted);
      font-size: 0.82rem;
      font-weight: 800;
    }

    .shot-type {
      display: inline-flex;
      margin-top: 6px;
      padding: 3px 7px;
      border-radius: 999px;
      font-size: 0.68rem;
      font-weight: 1000;
      text-transform: uppercase;
    }

    .shot-type.goal {
      color: var(--green);
      border: 1px solid var(--green);
    }

    .shot-type.shot_on_goal {
      color: var(--teal);
      border: 1px solid var(--teal);
    }

    .shot-type.shot_blocked {
      color: var(--orange);
      border: 1px solid var(--orange);
    }

    .status {
      margin-top: 12px;
      color: var(--muted);
      font-weight: 800;
      line-height: 1.35;
    }

    @media (max-width: 1100px) {
      main {
        grid-template-columns: 1fr;
      }

      .shot-list {
        max-height: none;
      }
    }
  </style>
</head>

<body>
  <header>
    <h1>SPL Shot Map Editor</h1>
    <p>Click the rink, choose team/player/result, save the shot map JSON.</p>
  </header>

  <main>
    <section class="panel">
      <h2>Match</h2>

      <label for="matchSelect">Final Match</label>
      <select id="matchSelect"></select>

      <div id="matchSummary" class="match-summary">
        Select a match.
      </div>

      <label>Attack Direction</label>
      <div class="button-row">
        <button id="homeLtrButton" type="button" class="active">
          Home L→R
        </button>
        <button id="homeRtlButton" type="button">
          Home R→L
        </button>
      </div>

      <div class="status" id="saveStatus"></div>
    </section>

    <section class="panel rink-panel">
      <div class="rink-toolbar">
        <strong id="rinkTitle">Shot Map</strong>

        <div class="button-row">
          <button id="saveMapButton" type="button">Save Map</button>
          <button id="clearSelectionButton" type="button">Clear Selection</button>
        </div>
      </div>

      <div class="attack-label-row">
        <div class="attack-label left" id="leftAttackLabel"></div>
        <div class="attack-label right" id="rightAttackLabel"></div>
      </div>

      <div id="rink" class="rink">
        <img
            class="rink-image"
            src="/assets/images/rink/slapshot-rink.png"
            alt=""
            aria-hidden="true"
        >

        <div id="pelletLayer" class="pellet-layer"></div>
      </div>
    </section>

    <section class="panel">
      <h2>Shot Event</h2>

      <div id="shotForm" class="shot-form">
        <label>Team</label>
        <div class="button-row">
          <button id="homeTeamButton" type="button"></button>
          <button id="awayTeamButton" type="button"></button>
        </div>

        <label>Player</label>
        <div id="playerPellets" class="player-pellets"></div>

        <label>Result</label>
        <div class="button-row">
          <button class="result-goal" data-result="goal" type="button">Goal</button>
          <button class="result-sog" data-result="shot_on_goal" type="button">Shot on Goal</button>
          <button class="result-blocked" data-result="shot_blocked" type="button">Shot Blocked</button>
        </div>

        <label>Period</label>
        <div class="button-row">
          <button data-period="1" type="button">1st</button>
          <button data-period="2" type="button">2nd</button>
          <button data-period="3" type="button">3rd</button>
          <button data-period="OT" type="button">OT</button>
        </div>

        <label for="timeRemaining">Time Remaining</label>
        <input id="timeRemaining" placeholder="4:12">

        <button id="saveShotButton" type="button" class="save-button">
          Save Shot
        </button>

        <button id="deleteShotButton" type="button" class="delete-button">
          Delete Shot
        </button>
      </div>

      <div id="noShotSelected" class="status">
        Click the rink to add a shot, or click an existing pellet to edit it.
      </div>

      <h2 style="margin-top: 20px;">Shot List</h2>
      <div id="shotList" class="shot-list"></div>
    </section>
  </main>

  <script>
    const state = {
      matches: [],
      snapshots: {},
      metadata: {},
      currentMatch: null,
      currentMap: null,
      selectedShotId: null,
      draftShot: null
    };

    const RESULT_LABELS = {
      goal: "Goal",
      shot_on_goal: "Shot on Goal",
      shot_blocked: "Shot Blocked"
    };

    function cleanText(value) {
      return String(value || "").trim();
    }

    function makeShotId() {
      return `shot_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
    }

    function getTeamMeta(teamId) {
      return state.metadata[teamId] || {};
    }

    function getTeamTheme(teamId) {
      return getTeamMeta(teamId).theme || {};
    }

    function getSnapshotForCurrentMatch() {
      if (!state.currentMatch) return null;
      return state.snapshots[state.currentMatch.match_id] || null;
    }

    function getRosterForSide(side) {
      const snapshot = getSnapshotForCurrentMatch();

      if (!snapshot) {
        return { players: [] };
      }

      return side === "home"
        ? snapshot.home_roster
        : snapshot.away_roster;
    }

    function getTeamInfo(side) {
      const match = state.currentMatch;

      if (!match) return null;

      if (side === "home") {
        return {
          side: "home",
          team_id: match.home_team_id,
          team: match.home_team,
          attack_direction: state.currentMap.rink_orientation.home
        };
      }

      return {
        side: "away",
        team_id: match.away_team_id,
        team: match.away_team,
        attack_direction: state.currentMap.rink_orientation.away
      };
    }

    function getShotById(shotId) {
      return (state.currentMap?.shots || []).find(shot => shot.id === shotId) || null;
    }

    async function apiGet(path) {
      const response = await fetch(path);

      if (!response.ok) {
        throw new Error(`GET ${path} failed: ${response.status}`);
      }

      return response.json();
    }

    async function apiPost(path, payload) {
      const response = await fetch(path, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(`POST ${path} failed: ${response.status} ${text}`);
      }

      return response.json();
    }

    async function loadInitialData() {
      const data = await apiGet("/api/bootstrap");

      state.matches = data.matches;
      state.snapshots = data.roster_snapshots;
      state.metadata = {};

      data.team_metadata.forEach(team => {
        if (team.team_id) {
          state.metadata[team.team_id] = team;
        }
      });

      renderMatchSelect();

      if (state.matches.length) {
        await selectMatch(state.matches[0].match_id);
      }
    }

    function renderMatchSelect() {
      const select = document.querySelector("#matchSelect");

      select.innerHTML = state.matches.map(match => `
        <option value="${match.match_id}">
          ${match.schedule_id} — ${match.home_team} vs ${match.away_team}
        </option>
      `).join("");
    }

    async function selectMatch(matchId) {
      state.currentMatch = state.matches.find(match => match.match_id === matchId) || null;
      state.selectedShotId = null;
      state.draftShot = null;

      if (!state.currentMatch) return;

      document.querySelector("#matchSelect").value = matchId;

      const loadedMap = await apiGet(`/api/shot-map?match_id=${encodeURIComponent(matchId)}`);

      state.currentMap = loadedMap;

      renderAll();
    }

    function createEmptyShotMap(match) {
      return {
        match_id: match.match_id,
        schedule_id: match.schedule_id,
        season_id: match.season_id,
        season_name: match.season_name,
        phase: match.phase,
        region: match.region,
        home_team_id: match.home_team_id,
        home_team: match.home_team,
        away_team_id: match.away_team_id,
        away_team: match.away_team,
        rink_orientation: {
          home: "left_to_right",
          away: "right_to_left"
        },
        shots: []
      };
    }

    function renderAll() {
      renderMatchSummary();
      renderOrientationButtons();
      renderRink();
      renderShotForm();
      renderShotList();
    }

    function renderMatchSummary() {
      const match = state.currentMatch;

      document.querySelector("#matchSummary").innerHTML = `
        <div>
          <span class="team-name">${match.home_team}</span>
          vs
          <span class="team-name">${match.away_team}</span>
        </div>
        <div>
          ${match.home_score ?? "-"} - ${match.away_score ?? "-"}
          · ${match.region_display || match.region}
          · ${match.status}
        </div>
      `;

      document.querySelector("#homeTeamButton").textContent = match.home_team;
      document.querySelector("#awayTeamButton").textContent = match.away_team;
      document.querySelector("#rinkTitle").textContent =
        `${match.schedule_id} Shot Map`;
    }

    function renderOrientationButtons() {
      const homeDirection = state.currentMap.rink_orientation.home;

      document.querySelector("#homeLtrButton").classList.toggle(
        "active",
        homeDirection === "left_to_right"
      );

      document.querySelector("#homeRtlButton").classList.toggle(
        "active",
        homeDirection === "right_to_left"
      );

      if (homeDirection === "left_to_right") {
        document.querySelector("#leftAttackLabel").textContent = `${state.currentMatch.home_team} attacks →`;
        document.querySelector("#rightAttackLabel").textContent = `← ${state.currentMatch.away_team} attacks`;
      } else {
        document.querySelector("#leftAttackLabel").textContent = `${state.currentMatch.away_team} attacks →`;
        document.querySelector("#rightAttackLabel").textContent = `← ${state.currentMatch.home_team} attacks`;
      }
    }

    function renderRink() {
        const layer = document.querySelector("#pelletLayer");

        layer.innerHTML = "";

        (state.currentMap.shots || []).forEach(shot => {
            const pellet = document.createElement("button");
            pellet.type = "button";
            pellet.className = `pellet ${shot.result}`;
            pellet.style.left = `${shot.x}%`;
            pellet.style.top = `${shot.y}%`;
            pellet.title = `${shot.player} — ${RESULT_LABELS[shot.result] || shot.result}`;
            pellet.dataset.shotId = shot.id;

            if (shot.id === state.selectedShotId) {
                pellet.classList.add("selected");
            }

            pellet.addEventListener("click", event => {
                event.stopPropagation();
                selectShot(shot.id);
            });

            layer.appendChild(pellet);
        });
    }

    function renderShotForm() {
      const form = document.querySelector("#shotForm");
      const empty = document.querySelector("#noShotSelected");

      const shot = state.draftShot || getShotById(state.selectedShotId);

      if (!shot) {
        form.classList.remove("open");
        empty.style.display = "";
        return;
      }

      form.classList.add("open");
      empty.style.display = "none";

      document.querySelector("#homeTeamButton").classList.toggle("active", shot.team_side === "home");
      document.querySelector("#awayTeamButton").classList.toggle("active", shot.team_side === "away");

      renderPlayerButtons(shot.team_side, shot.player_id);

      document.querySelectorAll("[data-result]").forEach(button => {
        button.classList.toggle("active", button.dataset.result === shot.result);
      });

      document.querySelectorAll("[data-period]").forEach(button => {
        button.classList.toggle("active", button.dataset.period === shot.period);
      });

      document.querySelector("#timeRemaining").value = shot.time_remaining || "";
      document.querySelector("#deleteShotButton").style.display =
        state.selectedShotId ? "" : "none";
    }

    function renderPlayerButtons(teamSide, selectedPlayerId) {
      const container = document.querySelector("#playerPellets");
      const roster = getRosterForSide(teamSide);

      container.innerHTML = (roster.players || []).map(player => {
        const playerId = cleanText(player.slap_id || player.steam_name);
        const playerName = cleanText(player.steam_name || player.slap_id || "Unknown");

        return `
          <button
            type="button"
            data-player-id="${playerId}"
            data-player-name="${playerName}"
            class="${playerId === selectedPlayerId ? "active" : ""}"
          >
            ${playerName}
          </button>
        `;
      }).join("");

      container.querySelectorAll("[data-player-id]").forEach(button => {
        button.addEventListener("click", () => {
          updateCurrentShot({
            player_id: button.dataset.playerId,
            player: button.dataset.playerName
          });
        });
      });
    }

    function renderShotList() {
      const list = document.querySelector("#shotList");
      const shots = state.currentMap?.shots || [];

      if (!shots.length) {
        list.innerHTML = `
          <div class="status">
            No shots entered yet.
          </div>
        `;
        return;
      }

      list.innerHTML = shots.map(shot => `
        <div class="shot-item" data-shot-id="${shot.id}">
          <strong>${shot.player || "Unknown Player"}</strong>
          <span>${shot.team} · ${shot.period || "No period"} ${shot.time_remaining || ""}</span>
          <br>
          <span class="shot-type ${shot.result}">
            ${RESULT_LABELS[shot.result] || shot.result}
          </span>
        </div>
      `).join("");

      list.querySelectorAll("[data-shot-id]").forEach(item => {
        item.addEventListener("click", () => {
          selectShot(item.dataset.shotId);
        });
      });
    }

    function beginShotAt(x, y) {
      state.selectedShotId = null;

      state.draftShot = {
        id: makeShotId(),
        x,
        y,
        team_id: "",
        team_side: "",
        team: "",
        attack_direction: "",
        player_id: "",
        player: "",
        result: "shot_on_goal",
        period: "",
        time_remaining: ""
      };

      renderRink();
      renderShotForm();
    }

    function selectShot(shotId) {
      state.selectedShotId = shotId;
      state.draftShot = null;
      renderAll();
    }

    function updateCurrentShot(patch) {
      const shot = state.draftShot || getShotById(state.selectedShotId);

      if (!shot) return;

      Object.assign(shot, patch);

      renderShotForm();
      renderShotList();
      renderRink();
    }

    function setTeamSide(side) {
      const team = getTeamInfo(side);

      updateCurrentShot({
        team_side: side,
        team_id: team.team_id,
        team: team.team,
        attack_direction: team.attack_direction,
        player_id: "",
        player: ""
      });
    }

    function saveCurrentShot() {
      const shot = state.draftShot || getShotById(state.selectedShotId);

      if (!shot) return;

      shot.time_remaining = cleanText(document.querySelector("#timeRemaining").value);

      if (!shot.team_side || !shot.player_id || !shot.result) {
        alert("Please select team, player, and result before saving.");
        return;
      }

      if (state.draftShot) {
        state.currentMap.shots.push(state.draftShot);
        state.selectedShotId = state.draftShot.id;
        state.draftShot = null;
      }

      renderAll();
    }

    function deleteCurrentShot() {
      if (!state.selectedShotId) return;

      state.currentMap.shots = state.currentMap.shots.filter(
        shot => shot.id !== state.selectedShotId
      );

      state.selectedShotId = null;
      state.draftShot = null;
      renderAll();
    }

    async function saveMap() {
      document.querySelector("#saveStatus").textContent = "Saving...";

      await apiPost("/api/save-shot-map", state.currentMap);

      document.querySelector("#saveStatus").textContent =
        `Saved ${state.currentMap.shots.length} shots.`;
    }

    function setHomeDirection(direction) {
      state.currentMap.rink_orientation.home = direction;
      state.currentMap.rink_orientation.away =
        direction === "left_to_right"
          ? "right_to_left"
          : "left_to_right";

      (state.currentMap.shots || []).forEach(shot => {
        if (shot.team_side === "home") {
          shot.attack_direction = state.currentMap.rink_orientation.home;
        }

        if (shot.team_side === "away") {
          shot.attack_direction = state.currentMap.rink_orientation.away;
        }
      });

      renderAll();
    }

    document.querySelector("#matchSelect").addEventListener("change", event => {
      selectMatch(event.target.value);
    });

    document.querySelector("#rink").addEventListener("click", event => {
      if (!state.currentMatch) return;

      const rect = event.currentTarget.getBoundingClientRect();

      const x = ((event.clientX - rect.left) / rect.width) * 100;
      const y = ((event.clientY - rect.top) / rect.height) * 100;

      beginShotAt(
        Math.round(x * 10) / 10,
        Math.round(y * 10) / 10
      );
    });

    document.querySelector("#homeTeamButton").addEventListener("click", () => {
      setTeamSide("home");
    });

    document.querySelector("#awayTeamButton").addEventListener("click", () => {
      setTeamSide("away");
    });

    document.querySelectorAll("[data-result]").forEach(button => {
      button.addEventListener("click", () => {
        updateCurrentShot({
          result: button.dataset.result
        });
      });
    });

    document.querySelectorAll("[data-period]").forEach(button => {
      button.addEventListener("click", () => {
        updateCurrentShot({
          period: button.dataset.period
        });
      });
    });

    document.querySelector("#timeRemaining").addEventListener("input", event => {
      updateCurrentShot({
        time_remaining: event.target.value
      });
    });

    document.querySelector("#saveShotButton").addEventListener("click", saveCurrentShot);
    document.querySelector("#deleteShotButton").addEventListener("click", deleteCurrentShot);
    document.querySelector("#saveMapButton").addEventListener("click", saveMap);

    document.querySelector("#clearSelectionButton").addEventListener("click", () => {
      state.selectedShotId = null;
      state.draftShot = null;
      renderAll();
    });

    document.querySelector("#homeLtrButton").addEventListener("click", () => {
      setHomeDirection("left_to_right");
    });

    document.querySelector("#homeRtlButton").addEventListener("click", () => {
      setHomeDirection("right_to_left");
    });

    loadInitialData().catch(error => {
      console.error(error);
      document.querySelector("#saveStatus").textContent = error.message;
    });
  </script>
</body>
</html>
"""


def read_json(path, fallback):
    if not path.exists():
        return fallback

    try:
        with path.open("r", encoding="utf-8") as file:
            content = file.read().strip()

            if not content:
                return fallback

            return json.loads(content)

    except json.JSONDecodeError:
        return fallback


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def get_final_matches():
    matches = read_json(SCHEDULE_FILE, [])

    return [
        match for match in matches
        if match.get("status") == "final"
    ]


def make_empty_shot_map(match):
    return {
        "match_id": match["match_id"],
        "schedule_id": match["schedule_id"],
        "season_id": match["season_id"],
        "season_name": match["season_name"],
        "phase": match["phase"],
        "region": match["region"],
        "home_team_id": match["home_team_id"],
        "home_team": match["home_team"],
        "away_team_id": match["away_team_id"],
        "away_team": match["away_team"],
        "rink_orientation": {
            "home": "left_to_right",
            "away": "right_to_left"
        },
        "shots": []
    }


class ShotMapEditorHandler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        encoded = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_text(self, text, status=200, content_type="text/plain; charset=utf-8"):
        encoded = text.encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self.send_text(APP_HTML, content_type="text/html; charset=utf-8")
            return

        if parsed.path == "/api/bootstrap":
            self.send_json({
                "matches": get_final_matches(),
                "roster_snapshots": read_json(ROSTER_SNAPSHOTS_FILE, {}),
                "team_metadata": read_json(TEAM_METADATA_FILE, []),
            })
            return

        if parsed.path == "/api/shot-map":
            query = parse_qs(parsed.query)
            match_id = clean_query_value(query.get("match_id"))

            if not match_id:
                self.send_json({"error": "Missing match_id"}, status=400)
                return

            shot_map_file = SHOT_MAP_DIR / f"{match_id}.json"
            existing = read_json(shot_map_file, None)

            if existing:
                self.send_json(existing)
                return

            match = next(
                (item for item in get_final_matches() if item.get("match_id") == match_id),
                None
            )

            if not match:
                self.send_json({"error": "Match not found"}, status=404)
                return

            self.send_json(make_empty_shot_map(match))
            return

        # Optional static file support, mostly for future rink images.
        static_path = (BASE_DIR / parsed.path.lstrip("/")).resolve()

        if BASE_DIR in static_path.parents and static_path.exists() and static_path.is_file():
            content_type = mimetypes.guess_type(static_path.name)[0] or "application/octet-stream"

            with static_path.open("rb") as file:
                data = file.read()

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        self.send_json({"error": "Not found"}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path != "/api/save-shot-map":
            self.send_json({"error": "Not found"}, status=404)
            return

        content_length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(content_length).decode("utf-8")

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, status=400)
            return

        match_id = clean_text(payload.get("match_id"))

        if not match_id:
            self.send_json({"error": "Missing match_id"}, status=400)
            return

        write_json(SHOT_MAP_DIR / f"{match_id}.json", payload)

        self.send_json({
            "ok": True,
            "match_id": match_id,
            "shot_count": len(payload.get("shots", [])),
        })

    def log_message(self, format, *args):
        return


def clean_text(value):
    return str(value or "").strip()


def clean_query_value(values):
    if not values:
        return ""

    return clean_text(values[0])


def main():
    SHOT_MAP_DIR.mkdir(parents=True, exist_ok=True)

    server = ThreadingHTTPServer((HOST, PORT), ShotMapEditorHandler)
    url = f"http://{HOST}:{PORT}"

    print(f"SPL Shot Map Editor running at {url}")
    print("Press Ctrl+C to stop.")

    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        print("Stopping server...")


if __name__ == "__main__":
    main()