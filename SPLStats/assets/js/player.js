async function fetchJsonOrFallback(url, fallback) {
  try {
    const response = await fetch(url);

    if (!response.ok) {
      console.warn(`Could not load ${url}: ${response.status}`);
      return fallback;
    }

    return await response.json();
  } catch (error) {
    console.warn(`Could not load ${url}:`, error);
    return fallback;
  }
}

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

let DIVISION_DISPLAY_NAMES = {};

function mergePlayerSeasonRows(rows) {
  const merged = new Map();

  for (const row of rows || []) {
    const normalizedDivision =
      normalizeDivisionName(row.division);

    const key = [
      row.season_id || row.season || "",
      normalizedDivision,
      row.team || row.team_name || ""
    ].join("|");

    if (!merged.has(key)) {
      merged.set(key, {
        ...row,
        division: normalizedDivision,
        stats: { ...(row.stats || {}) },

        // Optional: preserves the original LR division labels
        source_divisions: row.division
          ? [row.division]
          : []
      });

      continue;
    }

    const existing = merged.get(key);

    // Keep track of what got combined.
    if (
      row.division &&
      !existing.source_divisions.includes(row.division)
    ) {
      existing.source_divisions.push(row.division);
    }

    // Add raw stat totals together.
    for (const [stat, value] of Object.entries(row.stats || {})) {
      const numberValue = Number(value || 0);

      // Skip derived percentage/rate stats.
      // We'll recalculate these after merging.
      if (
        stat.endsWith("_percent") ||
        stat === "gaa" ||
        stat === "save_percent" ||
        stat === "shot_percent" ||
        stat === "faceoff_win_percent"
      ) {
        continue;
      }

      existing.stats[stat] =
        Number(existing.stats[stat] || 0) + numberValue;
    }
  }

  // Recalculate derived stats after merging.
  for (const row of merged.values()) {
    const stats = row.stats;

    const goals = Number(stats.goals || 0);
    const assists = Number(stats.assists || 0);
    const shots = Number(stats.shots || 0);
    const saves = Number(stats.saves || 0);
    const shotsAgainst = Number(stats.shots_against || 0);
    const goalsAgainst = Number(stats.goals_against || 0);
    const gamesPlayed = Number(stats.games_played || 0);
    const faceoffsWon = Number(stats.faceoffs_won || 0);
    const faceoffsLost = Number(stats.faceoffs_lost || 0);

    stats.points = goals + assists;

    stats.shot_percent =
      shots ? (goals / shots) * 100 : 0;

    stats.save_percent =
      shotsAgainst ? (saves / shotsAgainst) * 100 : 0;

    stats.gaa =
      gamesPlayed ? goalsAgainst / gamesPlayed : 0;

    stats.faceoffs_total =
      faceoffsWon + faceoffsLost;

    stats.faceoff_win_percent =
      stats.faceoffs_total
        ? (faceoffsWon / stats.faceoffs_total) * 100
        : 0;
  }

  return [...merged.values()];
}

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

function normalizeDivisionName(division) {
  return DIVISION_DISPLAY_NAMES[division] || division || "Unknown";
}

function getCareerStat(player, statName) {
  return Number(player?.career?.[statName] || 0);
}

function calculateTopPercentile(player, allPlayers, statName = "points") {
  const playerValue = getCareerStat(player, statName);

  const eligiblePlayers = allPlayers.filter(p =>
    getCareerStat(p, "games_played") > 0
    && getCareerStat(p, statName) > 0
  );

  if (!eligiblePlayers.length || playerValue <= 0) {
    return null;
  }

  const playersAbove = eligiblePlayers.filter(p =>
    getCareerStat(p, statName) > playerValue
  ).length;

  const rank = playersAbove + 1;
  const percentile = Math.ceil((rank / eligiblePlayers.length) * 100);

  return {
    rank,
    totalPlayers: eligiblePlayers.length,
    percentile: Math.max(1, percentile),
    value: playerValue
  };
}

function renderCareerPercentile(player, allPlayers) {
  const badge = document.querySelector("#careerPercentileBadge");
  if (!badge) return;

  const result = calculateTopPercentile(player, allPlayers, "points");

  if (!result) {
    badge.innerHTML = "";
    badge.style.display = "none";
    return;
  }

  badge.style.display = "";

  badge.innerHTML = `
    <div class="career-percentile-main">
      Top ${result.percentile}%
    </div>
    <div class="career-percentile-sub">
      Career Points
    </div>
    <div class="career-percentile-rank">
      Rank #${result.rank} of ${result.totalPlayers}
    </div>
  `;
}

function renderPlayer(player, championships = [], allPlayers = []) {
  document.title = `${player.player_name} | SPLStats`;
  document.querySelector("#playerName").textContent = player.player_name;

  renderPlayerChampionships(player, championships);

  renderCareerStats(player, allPlayers);
  renderTeams(player.by_season || []);
  renderSeasons(player.by_season || []);
}

function normalizePlayerNameForCompare(name) {
  return String(name || "")
    .trim()
    .toLowerCase();
}

function getPlayerChampionships(player, championships = []) {
  const playerName = normalizePlayerNameForCompare(player.player_name);

  return championships.filter(champ =>
    (champ.championship_roster || []).some(rosterPlayer =>
      normalizePlayerNameForCompare(rosterPlayer.player_name) === playerName
    )
  );
}

function getChampionshipClass(championship) {
  const cup = String(championship || "").toLowerCase();

  if (cup.includes("erveon")) return "champ-east";
  if (cup.includes("gazz")) return "champ-central";
  if (cup.includes("pacific")) return "champ-west";

  return "";
}

function getQualifiedByText(rosterEntry) {
  const qualifiedBy = rosterEntry.qualified_by || [];

  const labels = {
    regular_season_50_percent: "Regular Season",
    playoffs_50_percent: "Playoffs",
    finals_appearance: "Finals Appearance"
  };

  return qualifiedBy
    .map(key => labels[key] || key)
    .join(", ");
}

function renderPlayerChampionships(player, championships) {
  const card = document.querySelector("#championshipsCard");
  const container = document.querySelector("#playerChampionships");
  const countsContainer = document.querySelector("#playerChampionshipCounts");

  if (!card || !container) return;

  const playerChamps = getPlayerChampionships(player, championships);

  if (!playerChamps.length) {
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
    playerChamps.length <= 3
  );

  const counts = getChampionshipCounts(playerChamps);

  container.innerHTML = playerChamps.map(champ => {
    const rosterEntry = (champ.championship_roster || []).find(rosterPlayer =>
      normalizePlayerNameForCompare(rosterPlayer.player_name)
        === normalizePlayerNameForCompare(player.player_name)
    );

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
          ${getQualifiedByText(rosterEntry || {})}
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

function getChampionshipCounts(playerChamps) {
  const counts = {
    total: playerChamps.length,
    east: 0,
    central: 0,
    west: 0
  };

  playerChamps.forEach(champ => {
    const region = String(champ.region || "").toLowerCase();

    if (region === "east") counts.east += 1;
    if (region === "central") counts.central += 1;
    if (region === "west") counts.west += 1;
  });

  return counts;
}

async function loadPlayer() {
  const playerId = getPlayerIdFromUrl();

  const [
    players,
    divisionNames,
    championships
  ] = await Promise.all([
    fetchJsonOrFallback("data/all_time_players.json", []),
    fetchJsonOrFallback("data/division_display_names.json", {}),
    fetchJsonOrFallback("data/championships.json", [])
  ]);

  DIVISION_DISPLAY_NAMES = divisionNames;

  const player = players.find(p =>
    normalizeName(p.player_name) === normalizeName(playerId)
  );

  if (!player) {
    document.querySelector("#playerName").textContent = "Player Not Found";
    return;
  }

  renderPlayer(player, championships, players);
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

function renderCareerStats(player, allPlayers = []) {
  const career = player.career || {};
  const container = document.querySelector("#careerStats");

  const statRows = [
    [
      ["Seasons", player.seasons_played?.length || 0, "seasons_played"],
      ["Games", career.games_played, "games_played"],
      ["Periods", career.periods_played, "periods_played"]
    ],

    [
      ["Goals", career.goals, "goals"],
      ["Assists", career.assists, "assists"],
      ["Points", career.points, "points"],
      ["Shots", career.shots, "shots"]
    ],

    [
      [
        "Save %",
        career.save_percent
          ? (career.save_percent / 100).toFixed(3).replace(/^0/, "")
          : ".000", "save_percent"
      ],
      ["GAA", career.gaa ? career.gaa.toFixed(2) : "0.00", "gaa"],
      ["Saves", career.saves, "saves"],
      ["Blocks", career.blocks, "blocks"]
    ],

    [
      ["Shots Against", career.shots_against, "shots_against"],
      ["Goals Against", career.goals_against, "goals_against"],
    ],

    [
      ["Takeaways", career.takeaways, "takeaways"],
      ["Turnovers", career.turnovers, "turnovers"]
    ],

    [
      ["Faceoff %",
        career.faceoff_win_percent
          ? `${career.faceoff_win_percent.toFixed(1)}%`
          : "0.0%", "faceoff_win_percent"
      ],
      ["Faceoffs Won", career.faceoffs_won, "faceoffs_won"],
      ["Faceoffs Lost", career.faceoffs_lost, "faceoffs_lost"]
    ],

    [
      ["Posts Hit", career.post_hits, "post_hits"],
      ["Passes", career.passes, "passes"],
      ["Poss Time", formatTime(career.possession_time_sec), "possession_time_sec"]
    ]
  ];

  container.className = "career-stat-layout";

  container.innerHTML = statRows.map(row => `
    <div class="career-row">
      ${row.map(([label, value, statKey]) =>
        renderCareerStat(label, value, statKey, player, allPlayers)
      ).join("")}
    </div>
  `).join("");
}

function renderCareerStat(label, value, statKey, player, allPlayers) {
  return `
    <div class="career-stat">
      ${renderPercentileBadge(player, allPlayers, statKey)}
      <div class="career-stat-label">${label}</div>
      <div class="career-stat-value">${value ?? 0}</div>
    </div>
  `;
}

function getCareerValue(player, statKey) {
  if (statKey === "seasons_played") {
    return Array.isArray(player?.seasons_played)
      ? player.seasons_played.length
      : Number(player?.seasons_played || 0);
  }

  return Number(player?.career?.[statKey] || 0);
}

function formatPercentile(percentile) {
  if (!Number.isFinite(percentile)) {
    return "0%";
  }

  if (percentile < 1) {
    return `${percentile.toFixed(2)}%`;
  }

  if (percentile < 10) {
    return `${percentile.toFixed(1)}%`;
  }

  return `${Math.round(percentile)}%`;
}

function calculateTopPercentileForStat(player, allPlayers, statKey) {
  const playerValue = getCareerValue(player, statKey);

  const eligiblePlayers = allPlayers.filter(p =>
    getCareerValue(p, "games_played") > 0
    && getCareerValue(p, statKey) > 0
  );

  if (!eligiblePlayers.length || playerValue <= 0) {
    return null;
  }

  const playersAbove = eligiblePlayers.filter(p =>
    getCareerValue(p, statKey) > playerValue
  ).length;

  const rank = playersAbove + 1;
  const percentile = (rank / eligiblePlayers.length) * 100;

  return {
    rank,
    totalPlayers: eligiblePlayers.length,
    percentile,
    percentileText: formatPercentile(percentile)
  };
}

function renderPercentileBadge(player, allPlayers, statKey) {
  const result = calculateTopPercentileForStat(player, allPlayers, statKey);

  if (!result) {
    return "";
  }

  const percentileClass = getPercentileClass(result.percentile);

  return `
    <div
      class="career-stat-percentile ${percentileClass}"
      title="Rank #${result.rank} of ${result.totalPlayers}"
    >
      Top ${result.percentileText}
    </div>
  `;
}

function getPercentileClass(percentile) {
  if (percentile <= 1) return "percentile-elite";
  if (percentile <= 5) return "percentile-great";
  if (percentile <= 10) return "percentile-good";
  if (percentile <= 25) return "percentile-solid";
  if (percentile <= 50) return "percentile-average";

  return "percentile-normal";
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

  rows = mergePlayerSeasonRows(rows);

  const SEASON_ORDER = {
    winter: 1,
    spring: 2,
    summer: 3,
    fall: 4
  };

  function divisionDisplaySortValue(division) {
  const text = String(division || "").toLowerCase();

  if (text.includes("playoffs")) {
    return 1;
  }

  if (text.includes("preseason")) {
    return 3;
  }

  if (text.includes("vs disbanded teams")) {
    return 4;
  }

  return 2;
}

  rows.sort((a, b) => {
    const [seasonA, yearA] =
      String(a.season_id || "")
        .toLowerCase()
        .split("_");

    const [seasonB, yearB] =
      String(b.season_id || "")
        .toLowerCase()
        .split("_");

    const valueA =
      (Number(yearA) * 10)
      + (SEASON_ORDER[seasonA] || 0);

    const valueB =
      (Number(yearB) * 10)
      + (SEASON_ORDER[seasonB] || 0);

    // 1. Season order, newest first
    if (valueB !== valueA) {
      return valueB - valueA;
    }

    // 2. Team name grouping
    const teamCompare =
      String(a.team || "").localeCompare(
        String(b.team || "")
      );

    if (teamCompare !== 0) {
      return teamCompare;
    }

    // 3. Division type inside team group
    const divA =
      divisionDisplaySortValue(a.division);

    const divB =
      divisionDisplaySortValue(b.division);

    if (divA !== divB) {
      return divA - divB;
    }

    // 4. Fallback alphabetical division sort
    return String(a.division || "").localeCompare(
      String(b.division || "")
    );
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