const REGION_PATTERNS = {
  east: [
    "erveon",
    "blade",
    "genesis",
    "pro division",
    "minor league",
    "challenger",
    "intermediate",
    "open division",
    "prospect",
    "east"
  ],
  central: [
    "central",
    "gazz",
    "gaz",
    "b bowl"
  ],
  west: [
    "west",
    "masters",
    "pacific",
    "bome",
    "contenders"
  ]
};

function divisionBelongsToRegion(division, region) {
  if (!region || region === "all") return true;

  const patterns = REGION_PATTERNS[region];
  if (!patterns) return true;

  const text = String(division || "").toLowerCase();

  return patterns.some(pattern => text.includes(pattern));
}

function getPlayerIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("id");
}

function normalizeName(name) {
  return String(name || "").toLowerCase();
}

async function loadPlayer() {
  const playerId = getPlayerIdFromUrl();

  const response = await fetch("data/all_time_players.json");
  const players = await response.json();

  const player = players.find(p =>
    normalizeName(p.player_name) === normalizeName(playerId)
  );

  if (!player) {
    document.querySelector("#playerName").textContent = "Player Not Found";
    return;
  }

  renderPlayer(player);
}

function renderPlayer(player) {
  document.title = `${player.player_name} | SPLStats`;
  document.querySelector("#playerName").textContent = player.player_name;

  renderCareerStats(player.career || {});
  renderTeams(player.by_season || []);
  renderSeasons(player.by_season || []);
}

function renderCareerStats(career) {
  const container = document.querySelector("#careerStats");

  const stats = [
    ["GP", career.games_played],
    ["Goals", career.goals],
    ["Assists", career.assists],
    ["Points", career.points],
    ["Shots", career.shots],
    ["Saves", career.saves],
    ["Blocks", career.blocks],
    ["Passes", career.passes],
    ["Takeaways", career.takeaways],
    ["Turnovers", career.turnovers]
  ];

  container.innerHTML = stats.map(([label, value]) => `
    <div class="stat-box">
      <span>${label}</span>
      <strong>${value ?? 0}</strong>
    </div>
  `).join("");
}

function renderTeams(rows) {
  const container = document.querySelector("#teamsPlayed");

  const teamTotals = {};

  rows.forEach(row => {
    const team = row.team || "Unknown";
    const gp = Number(row.stats?.games_played || 0);

    if (!teamTotals[team]) {
      teamTotals[team] = {
        games: 0,
        regions: {}
      };
    }

    teamTotals[team].games += gp;

    if (divisionBelongsToRegion(row.division, "east")) {
      teamTotals[team].regions.east = true;
    }

    if (divisionBelongsToRegion(row.division, "central")) {
      teamTotals[team].regions.central = true;
    }

    if (divisionBelongsToRegion(row.division, "west")) {
      teamTotals[team].regions.west = true;
    }
  });

  const teams = Object.entries(teamTotals)
    .map(([team, info]) => ({
      team,
      games: info.games,
      regions: info.regions
    }))
    .sort((a, b) => b.games - a.games);

  container.innerHTML = teams.length
    ? teams.map(t => {
        const region =
          t.regions.east ? "east" :
          t.regions.central ? "central" :
          t.regions.west ? "west" :
          "unknown";

        return `
          <div class="team-box ${region}">
            <span class="team-gp">${t.games} GP</span>
            <div class="team-name ${region}">
              ${t.team}
            </div>
          </div>
        `;
      }).join("")
    : "No teams listed.";
}

function renderSeasons(rows) {
  const tbody = document.querySelector("#seasonTable tbody");

  const SEASON_ORDER = {
    winter: 1,
    spring: 2,
    summer: 3,
    fall: 4
  };

  rows.sort((a, b) => {
        const [seasonA, yearA] = String(a.season_id || "").toLowerCase().split("_");
        const [seasonB, yearB] = String(b.season_id || "").toLowerCase().split("_");

        const valueA = (Number(yearA) * 10) + (SEASON_ORDER[seasonA] || 0);
        const valueB = (Number(yearB) * 10) + (SEASON_ORDER[seasonB] || 0);

        return valueB - valueA;
    });

  tbody.innerHTML = rows.map(row => {
    const s = row.stats || {};

    return `
      <tr>
        <td>${row.season}</td>
        <td>${row.division}</td>
        <td>${row.team}</td>
        <td>${s.games_played ?? 0}</td>
        <td>${s.goals ?? 0}</td>
        <td>${s.assists ?? 0}</td>
        <td>${s.points ?? 0}</td>
        <td>${s.shots ?? 0}</td>
        <td>${s.saves ?? 0}</td>
        <td>${s.blocks ?? 0}</td>
      </tr>
    `;
  }).join("");
}

loadPlayer();