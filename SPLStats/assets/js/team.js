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

function formatSeason(value) {
  if (!value) return "Unknown";

  const text = String(value);

  const match = text.match(/^([a-z]+)_(\d{4})$/i);

  if (!match) {
    return text;
  }

  const season =
    match[1].charAt(0).toUpperCase()
    + match[1].slice(1).toLowerCase();

  return `${season} ${match[2]}`;
}

function findTeamFranchise(teamName, franchises) {
  const cleanTeamName =
    teamName
      .replace(/\s*\([^)]*\)$/, "")
      .trim()
      .toLowerCase();

  for (const franchise of franchises) {
    const membership = (franchise.memberships || []).find(m => {
      const memberTeam =
        m.team
          .replace(/\s*\([^)]*\)$/, "")
          .trim()
          .toLowerCase();

      return memberTeam === cleanTeamName;
    });

    if (membership) {
      return {
        franchise,
        membership
      };
    }
  }

  return null;
}

function renderTeamFranchise(teamName, franchises) {
  const result = findTeamFranchise(teamName, franchises);

  const section = document.querySelector("#teamFranchiseSection");
  const card = document.querySelector("#teamFranchiseCard");

  if (!section || !card) {
    return;
  }

  if (!result) {
    section.style.display = "none";
    return;
  }

  const { franchise, membership } = result;
  const theme = franchise.theme || {};

  section.style.display = "";

  const logoHTML =
  franchise.logo
    ? `
      <img
        class="team-franchise-logo-bg"
        src="${franchise.logo}"
        alt=""
        aria-hidden="true"
      >
    `
    : "";

  card.innerHTML = `
    <a
      class="team-franchise-card"
      href="franchise.html?id=${encodeURIComponent(franchise.franchise_id)}"
      style="
        --franchise-primary: ${theme.primary || "#ffffff"};
        --franchise-secondary: ${theme.secondary || "#cccccc"};
        --franchise-accent: ${theme.accent || "#ffffff"};
        --franchise-background: ${theme.background || "#050505"};
        --franchise-card: ${theme.card || "#111111"};
        --franchise-surface: ${theme.surface || "#1a1a1a"};
      "
    >
      ${logoHTML}

      <div class="team-franchise-card-content">
        <div class="team-franchise-name">
          ${franchise.franchise_name}
        </div>

        <div class="team-franchise-meta">
          ${formatSeason(membership.start_season)}
          →
          ${
            membership.end_season
              ? formatSeason(membership.end_season)
              : "Present"
          }
        </div>

        ${
          membership.order
            ? `<div class="team-franchise-order">Franchise Team #${membership.order}</div>`
            : ""
        }
      </div>
    </a>
  `;
}

function cleanTeamName(teamName) {
  return String(teamName)
    .replace(/\s*\([^)]*\)$/, "")
    .trim()
    .toLowerCase();
}

function findTeamRecord(teamName, teamRecords) {
  const cleanName = cleanTeamName(teamName);

  return teamRecords.find(record =>
    cleanTeamName(record.team) === cleanName
  ) || null;
}

async function loadTeam() {
  const teamName = getTeamFromUrl();

  const [
    teamsResponse,
    franchisesResponse,
    teamRecordsResponse,
    championshipsResponse
  ] = await Promise.all([
    fetch("data/teams.json"),
    fetch("data/franchises.json"),
    fetch("data/team_records.json"),
    fetch("data/championships.json")
  ]);

  const teams = await teamsResponse.json();
  const franchises = await franchisesResponse.json();
  const teamRecords = await teamRecordsResponse.json();
  const championships = await championshipsResponse.json();

  const team = teams.find(t =>
    t.team_name.toLowerCase() === teamName.toLowerCase()
  );

  if (!team) {
    document.querySelector("#teamName").textContent = "Team Not Found";
    return;
  }

  const teamRecord = findTeamRecord(
    team.team_name,
    teamRecords
  );

  renderTeam(team, teamRecord, championships);
  renderTeamFranchise(team.team_name, franchises);
}

function normalizeTeamNameForCompare(name) {
  return String(name || "")
    .replace(/\s*\([^)]*\)$/, "")
    .trim()
    .toLowerCase();
}

function getTeamChampionships(team, championships = []) {
  const teamName = normalizeTeamNameForCompare(team.team_name);

  return championships.filter(champ =>
    normalizeTeamNameForCompare(champ.winner_team) === teamName
  );
}

function getChampionshipClass(championship) {
  const cup = String(championship || "").toLowerCase();

  if (cup.includes("erveon")) return "champ-east";
  if (cup.includes("gazz")) return "champ-central";
  if (cup.includes("pacific")) return "champ-west";

  return "";
}

function getTeamChampionshipCounts(teamChamps) {
  const counts = {
    total: teamChamps.length,
    east: 0,
    central: 0,
    west: 0
  };

  teamChamps.forEach(champ => {
    const region = String(champ.region || "").toLowerCase();

    if (region === "east") counts.east += 1;
    if (region === "central") counts.central += 1;
    if (region === "west") counts.west += 1;
  });

  return counts;
}

function renderTeamChampionships(team, championships = []) {
  const card = document.querySelector("#teamChampionshipsCard");
  const container = document.querySelector("#teamChampionships");
  const countsContainer = document.querySelector("#teamChampionshipCounts");

  if (!card || !container) return;

  const teamChamps = getTeamChampionships(team, championships);

  if (!teamChamps.length) {
    card.style.display = "none";
    container.innerHTML = "";
    container.classList.remove("championship-carousel-centered");

    if (countsContainer) {
      countsContainer.innerHTML = "";
    }

    return;
  }

  card.style.display = "";

  container.classList.toggle(
    "championship-carousel-centered",
    teamChamps.length <= 4
  );

  const counts = getTeamChampionshipCounts(teamChamps);

  container.innerHTML = teamChamps.map(champ => {
    const champClass = getChampionshipClass(champ.championship);

    return `
      <div class="championship-card ${champClass}">
        <div class="championship-ring">🏆</div>

        <div class="championship-season">
          ${champ.season}
        </div>

        <div class="championship-card-main">
          <div class="championship-title">
            ${champ.championship}
          </div>

          <div class="championship-team">
            ${champ.winner_team}
          </div>

          <div class="championship-series">
            def. ${champ.runner_up_team}
            ${champ.series_result ? `(${champ.series_result})` : ""}
          </div>
        </div>

        <div class="championship-qualifier">
          ${champ.championship_roster?.length || 0} Qualified Players
        </div>
      </div>
    `;
  }).join("");

  if (countsContainer) {
    countsContainer.innerHTML = `
      <div class="championship-count championship-count-total">
        <span>Total</span>
        <strong>${counts.total}</strong>
      </div>

      <div class="championship-count champ-east">
        <span>East</span>
        <strong>${counts.east}</strong>
      </div>

      <div class="championship-count champ-central">
        <span>Central</span>
        <strong>${counts.central}</strong>
      </div>

      <div class="championship-count champ-west">
        <span>West</span>
        <strong>${counts.west}</strong>
      </div>
    `;
  }
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

function renderTeam(team, teamRecord, championships = []) {
  document.title = `${team.team_name} | SPLStats`;

  document.querySelector("#teamName").textContent =
    team.team_name;

  renderTeamLeaders(team.players || []);
  renderTeamChampionships(team, championships);
  renderCareer(team.career, teamRecord);
  renderSeasons(team.seasons);
  renderDivisions(team.divisions);
  renderRoster(team.players);
}

function renderCareer(career, teamRecord) {
  const teamStats = [
    ["Games Played", teamRecord?.games_played],
    ["Wins", teamRecord?.wins],
    ["Losses", teamRecord?.losses],
    ["Goals For", teamRecord?.goals_for],
    ["Goals Against", teamRecord?.goals_against]
  ];

  const playerStats = [
    ["Man Games", career.games_played],
    ["Goals", career.goals],
    ["Assists", career.assists],
    ["Points", career.points],
    ["Shots", career.shots],
    ["Saves", career.saves],
    ["Blocks", career.blocks]
  ];

  const renderCard = ([label, value]) => `
    <div class="stat-box">
      <span>${label}</span>
      <strong>${value ?? 0}</strong>
    </div>
  `;

  document.querySelector("#teamStats").innerHTML = `
    <div class="team-stat-row team-record-row">
      ${teamStats.map(renderCard).join("")}
    </div>

    <div class="team-stat-row player-total-row">
      ${playerStats.map(renderCard).join("")}
    </div>
  `;
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
      <td>${player.stats.shots ?? 0}</td>
      <td>${player.stats.saves ?? 0}</td>
      <td>${player.stats.blocks ?? 0}</td>
      <td>${player.stats.passes ?? 0}</td>
    </tr>
  `).join("");
}

loadTeam();