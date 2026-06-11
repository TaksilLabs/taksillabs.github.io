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
  renderTeams(player.teams_played_for || []);
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

function renderTeams(teams) {
  document.querySelector("#teamsPlayed").textContent =
    teams.length ? teams.join(", ") : "No teams listed.";
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