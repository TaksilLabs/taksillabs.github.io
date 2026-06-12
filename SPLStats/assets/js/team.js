const LEADER_CATEGORIES = [
  ["Goals", "goals"],
  ["Assists", "assists"],
  ["Points", "points"],
  ["Shots", "shots"],
  ["Takeaways", "takeaways"],

  ["Saves", "saves"],
  ["Blocks", "blocks"],
  ["Faceoff %", "faceoff_percent"],
  ["Games Played", "games_played"],
  ["Seasons Played", "seasons_played"]
];

function getLeaderValue(player, stat) {
  if (stat === "faceoff_percent") {
    const gp = Number(player.stats?.games_played || 0);
    const won = Number(player.stats?.faceoffs_won || 0);
    const lost = Number(player.stats?.faceoffs_lost || 0);
    const total = won + lost;

    if (gp < 10 || total === 0) return null;

    return (won / total) * 100;
  }

  if (stat === "seasons_played") {
    return Number(player.seasons_played || 0);
  }

  return Number(player.stats?.[stat] || 0);
}

function formatLeaderValue(value, stat) {
  if (value === null || value === undefined) return "—";

  if (stat === "faceoff_percent") {
    return `${value.toFixed(1)}%`;
  }

  return Math.round(value);
}

function topPlayers(players, stat, limit = 5) {
  return [...players]
    .map(player => ({
      ...player,
      leaderValue: getLeaderValue(player, stat)
    }))
    .filter(player => player.leaderValue !== null && player.leaderValue > 0)
    .sort((a, b) => b.leaderValue - a.leaderValue)
    .slice(0, limit);
}

function renderTeamLeaders(players) {
  const container = document.querySelector("#teamLeaders");
  if (!container) return;

  container.innerHTML = LEADER_CATEGORIES.map(([label, stat]) => {
    const leaders = topPlayers(players, stat);

    return `
      <div class="leader-card">
        <h3>${label}</h3>
        ${leaders.map((p, i) => `
            <div class="leader-row">
                <span>
                ${i + 1}.
                <a href="player.html?id=${encodeURIComponent(p.player_name.toLowerCase())}">
                    ${p.player_name}
                </a>
                </span>
                <strong>${formatLeaderValue(p.leaderValue, stat)}</strong>
            </div>
        `).join("")}
      </div>
    `;
  }).join("");
}

// ------------------------------------------------------------------------

function getTeamFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("team");
}

async function loadTeam() {
  const teamName = getTeamFromUrl();

  const response = await fetch("data/teams.json");
  const teams = await response.json();

  const team = teams.find(t =>
    t.team_name.toLowerCase() === teamName.toLowerCase()
  );

  if (!team) {
    document.querySelector("#teamName").textContent = "Team Not Found";
    return;
  }

  renderTeam(team);
}

function renderHeaderStats(career) {
  const container =
    document.querySelector("#teamHeaderStats");

  const stats = [
    ["GP", career.games_played],
    ["Goals", career.goals],
    ["Assists", career.assists],
    ["Points", career.points],
    ["Saves", career.saves],
    ["Blocks", career.blocks]
  ];

  container.innerHTML = stats.map(([label, value]) => `
    <div class="stat-box">
      <span>${label}</span>
      <strong>${value ?? 0}</strong>
    </div>
  `).join("");
}

function renderTeam(team) {
  document.title = `${team.team_name} | SPLStats`;

  document.querySelector("#teamName").textContent =
    team.team_name;

  renderTeamLeaders(team.players || []);

  renderCareer(team.career);
  renderSeasons(team.seasons);
  renderDivisions(team.divisions);
  renderRoster(team.players);
}

function renderCareer(career) {
  const stats = [
    ["GP", career.games_played],
    ["Goals", career.goals],
    ["Assists", career.assists],
    ["Points", career.points],
    ["Shots", career.shots],
    ["Saves", career.saves],
    ["Blocks", career.blocks]
  ];

  document.querySelector("#careerStats").innerHTML =
    stats.map(([label, value]) => `
      <div class="stat-box">
        <span>${label}</span>
        <strong>${value ?? 0}</strong>
      </div>
    `).join("");
}

function renderTagList(selector, items, className = "") {
  const container = document.querySelector(selector);

  container.innerHTML = items.length
    ? items.map(item => `
        <span class="info-tag ${className}">
          ${item}
        </span>
      `).join("")
    : "None listed.";
}

function sortSeasons(seasons) {
  const SEASON_ORDER = {
    winter: 1,
    spring: 2,
    summer: 3,
    fall: 4
  };

  return [...seasons].sort((a, b) => {
    const matchA = String(a).match(/^([A-Za-z]+)\s+(\d{4})$/);
    const matchB = String(b).match(/^([A-Za-z]+)\s+(\d{4})$/);

    if (!matchA || !matchB) {
      return String(b).localeCompare(String(a));
    }

    const valueA =
      Number(matchA[2]) * 10 +
      (SEASON_ORDER[matchA[1].toLowerCase()] || 0);

    const valueB =
      Number(matchB[2]) * 10 +
      (SEASON_ORDER[matchB[1].toLowerCase()] || 0);

    return valueB - valueA;
  });
}

function renderSeasons(seasons) {
  renderTagList(
    "#seasonList",
    sortSeasons(seasons),
    "season-tag"
  );
}

function divisionSortValue(name) {
  const text = String(name).toLowerCase();

  if (text.includes("erveon")) return 1;
  if (text.includes("pro")) return 2;

  if (text.includes("blade")) return 3;
  if (text.includes("challenger")) return 4;

  if (text.includes("intermediate")) return 5;
  if (text.includes("prospect")) return 6;
  if (text.includes("open")) return 7;

  if (text.includes("central a")) return 8;
  if (text.includes("central b")) return 9;
  if (text.includes("central c")) return 10;
  if (text.includes("central d")) return 11;

  if (text.includes("masters")) return 12;
  if (text.includes("contenders")) return 13;

  if (text.includes("preseason")) return 98;
  if (text.includes("playoff")) return 99;
  if (text.includes("cup")) return 100;

  return 999;
}

function renderDivisions(divisions) {
  const sorted = [...divisions].sort(
    (a, b) => divisionSortValue(a) - divisionSortValue(b)
  );

  renderTagList(
    "#divisionList",
    sorted,
    "division-tag"
  );
}

function renderRoster(players) {
  const tbody =
    document.querySelector("#rosterTable tbody");

  tbody.innerHTML = players.map(player => `
    <tr>
      <td>
        <a href="player.html?id=${encodeURIComponent(player.player_name.toLowerCase())}">
          ${player.player_name}
        </a>
      </td>
      <td>${player.stats.games_played ?? 0}</td>
      <td>${player.stats.goals ?? 0}</td>
      <td>${player.stats.assists ?? 0}</td>
      <td>${player.stats.points ?? 0}</td>
    </tr>
  `).join("");
}

loadTeam();