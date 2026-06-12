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

function renderPlayer(player) {
  document.title = `${player.player_name} | SPLStats`;
  document.querySelector("#playerName").textContent = player.player_name;

  renderCareerStats(player);
  renderTeams(player.by_season || []);
  renderSeasons(player.by_season || []);
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

function formatTime(seconds) {
  seconds = Math.round(Number(seconds || 0));

  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;

  return [
    h,
    String(m).padStart(2, "0"),
    String(s).padStart(2, "0")
  ].join(":");
}

function renderCareerStats(player) {
  const career = player.career || {};
  const container = document.querySelector("#careerStats");

  const statRows = [
    [
      ["Seasons", player.seasons_played?.length || 0],
      ["Games", career.games_played],
      ["Periods", career.periods_played]
    ],

    [
      ["Goals", career.goals],
      ["Assists", career.assists],
      ["Points", career.points],
      ["Shots", career.shots]
    ],

    [
      ["Saves", career.saves],
      ["Blocks", career.blocks]
    ],

    [
      ["Takeaways", career.takeaways],
      ["Turnovers", career.turnovers]
    ],

    [
      ["Faceoff %",
        career.faceoff_win_percent
          ? `${career.faceoff_win_percent.toFixed(1)}%`
          : "0.0%"
      ],
      ["Faceoffs Won", career.faceoffs_won],
      ["Faceoffs Lost", career.faceoffs_lost]
    ],

    [
      ["Posts Hit", career.post_hits],
      ["Poss Time", formatTime(career.possession_time_sec)]
    ]
  ];

  container.className = "career-stat-layout";

  container.innerHTML = statRows.map(row => `
    <div class="career-row">
      ${row.map(([label, value]) => `
        <div class="career-stat">
          <div class="career-stat-label">${label}</div>
          <div class="career-stat-value">${value ?? 0}</div>
        </div>
      `).join("")}
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
        seasons: new Set(),
        regions: {}
      };
    }

    teamTotals[team].games += gp;
    teamTotals[team].seasons.add(row.season);

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
      seasons: info.seasons.size,
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
            <div class="team-card-stats">
              <div>
                <span class="team-stat-label">Seasons</span>
                <strong>${t.seasons}</strong>
              </div>
              <div>
                <span class="team-stat-label">Games</span>
                <strong>${t.games}</strong>
              </div>
            </div>

            <a class="team-name ${region}" href="team.html?team=${encodeURIComponent(t.team)}">
              ${t.team}
            </a>
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
        <td>
          <a href="team.html?team=${encodeURIComponent(row.team)}">
            ${row.team}
          </a>
        </td>
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