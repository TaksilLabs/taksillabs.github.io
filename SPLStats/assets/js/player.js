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

function normalizeDivisionName(division) {

  // Last Updated 2026-06-16    //    SPL 22 - Summer 2026
  const DIVISION_DISPLAY_NAMES = {
    "B Bowl - Playoffs": "B Bowl Playoffs",
    "B Bowl Playoffs": "B Bowl Playoffs",
    "Blade Cup - Playoffs": "Blade Cup Playoffs",
    "Blade Cup Playoffs": "Blade Cup Playoffs",
    "Bome Cup - Playoffs": "Bome Cup Playoffs",
    "CHALLENGER - Promotional Series": "Challenger Promotional Series",
    "CHALLENGER PLAYOFFS": "Blade Cup Playoffs",
    "CHALLENGER PROMOTIONAL SERIES": "Challenger Promotional Series",
    "Central A": "Central A",
    "Central A - Playoffs": "Gazz Cup Playoffs",
    "Central B": "Central B",
    "Central B - East": "Central B",
    "Central B - East vs North": "Central B",
    "Central B - East vs South": "Central B",
    "Central B - East vs West": "Central B",
    "Central B - Playoffs": "B Bowl Playoffs",
    "Central B - South": "Central B",
    "Central B - South vs North": "Central B",
    "Central B - South vs West": "Central B",
    "Central B - West": "Central B",
    "Central B - West vs North": "Central B",
    "Central C": "Central C",
    "Central C - Playoffs": "Central C Playoffs",
    "Central C Playoffs": "Central C Playoffs",
    "Central D": "Central D",
    "Central D - Playoffs": "Central D Playoffs",
    "Challenger Cross-Conf": "Challenger Division",
    "Challenger Cross-Play": "Challenger Division",
    "Challenger Division": "Challenger Division",
    "Challenger Division - M1NNSNOWTA": "Challenger Division",
    "Challenger Division - Playoffs": "Balde Cup Playoffs",
    "Challenger Play-In": "Challenger Play-In Tournament",
    "Challenger Play-in": "Challenger Play-In Tournament",
    "Challenger Promotional Series": "Challenger Promotional Series",
    "Cluster Cup - Playoffs": "Cluster Cup Playoffs",
    "Contenders Circuit": "Contenders Circuit",
    "Contenders Playoffs": "Bome Cup Playoffs",
    "Erveon Cup - Playoffs": "Erveon Cup Playoffs",
    "Erveon Cup Playoffs": "Erveon Cup Playoffs",
    "Erveon Trophy - Playoffs": "Erveon Cup Playoffs",
    "Gazz Cup - Playoffs": "Gazz Cup Playoffs",
    "Gazz Cup Playoffs": "Gazz Cup Playoffs",
    "Genesis Cup - Playoffs": "Genesis Cup Playoffs",
    "Genesis Cup Playoffs": "Genesis Cup Playoffs",
    "IM Cross-Play": "Intermediate Division",
    "IM Play-in": "Intermediate Play-In Tournament",
    "IM Play-in Series": "Intermediate Play-In Tournament",
    "IM Promotional Series": "Intermediate Promotional Series",
    "INTERMEDIATE - Promotional Series": "Intermediate Promotional Series",
    "INTERMEDIATE PROMOTIONAL SERIES": "Intermediate Promotional Series",
    "Intermediate Cross-Play": "Intermediate Division",
    "Intermediate Cup - Playoffs": "Intermediate Cup Playoffs",
    "Intermediate Division": "Intermediate Division",
    "Intermediate Division - Baguette - Intermediate Division - Omelette": "Intermediate Division",
    "Intermediate Division - Omelette": "Intermediate Division",
    "Intermediate Division - Omelette - Intermediate Division": "Intermediate Division",
    "Intermediate Division - Playoffs": "Intermediate Cup Playoffs",
    "Intermediate Play-In": "Intermediate Play-In Tournament",
    "Intermediate Playoffs": "Intermediate Cup Playoffs",
    "Intermediate Promotional Series": "Intermediate Promotional Series",
    "Intermediate Promotional Tournament": "Intermediate Promotional Series",
    "Masters Playoffs": "Pacific Cup Playoffs",
    "Minor League": "Minor League",
    "OPEN Promotional Series": "Intermediate Promotional Series",
    "Open Benders - Playoffs": "Genesis Cup Playoffs",
    "Open Cross Conf": "Open Division",
    "Open Division": "Open Division",
    "Open Division - Dusters": "Open Division",
    "Open Division - Playoffs": "Genesis Cup Playoffs",
    "Open Division Playoffs": "Genesis Cup Playoffs",
    "Open Dusters - Playoffs": "Genesis Cup Playoffs",
    "Other Matches": "Vs Disbanded Teams",
    "PRO - Promotional Series": "Pro Promotional Series",
    "PRO DIVISION - PLAYOFFS": "Erveon Cup Playoffs",
    "PRO DIVISION - Playoffs": "Erveon Cup Playoffs",
    "PRO DIVISION PLAYOFFS": "Erveon Cup Playoffs",
    "PRO PROMOTIONAL SERIES": "Pro Promotional Series",
    "PRO Playoffs": "Erveon Cup Playoffs",
    "Pacific Cup - Playoffs": "Pacific Cup Playoffs",
    "Pacific Cup Playoffs": "Pacific Cup Playoffs",
    "Placement Season Playoffs": "Erveon Cup Playoffs",
    "Play-ins": "Preseason",
    "Preseason": "Preseason",
    "Preseason Playin": "Preseason",
    "Pro Division": "Pro Division",
    "Pro Division Playoffs": "Erveon Cup Playoffs",
    "Pro Play-in": "Pro Play-In Tournament",
    "Pro Promotional Series": "Pro Promotional Series",
    "Pro Promotional Tournament": "Pro Promotional Series",
    "Prospect Cross-Play": "Prospect Division",
    "Prospect Division": "Prospect Division",
    "Prospect Division - Beauties": "Prospect Division",
    "Prospect Division - Playoffs": "Prospect Cup Playoffs",
    "Prospect Play-in": "Prospect Play-In",
    "S1 Pro Playoffs": "Erveon Cup Playoffs",
    "SPL Season 1 Pro Playoffs": "Erveon Cup Playoffs",
    "Season 1 Intermediate Play-In Tournament": "Intermediate Play-In",
    "Underdog Cup - Playoffs": "Underdog Cup Playoffs",
    "Vs Disbanded Teams": "Vs Disbanded Teams",
    "WEST DIVISION - PLAYOFFS": "Pacific Cup Playoffs",
    "WEST DIVISION PLAYOFFS": "Pacific Cup Playoffs",
    "West - Contenders Division": "Contenders Division",
    "West Division": "West Division",
    "West Division - Playoffs": "Pacific Cup Playoffs"
  };

  return DIVISION_DISPLAY_NAMES[division] || division || "Unknown";
}

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

function renderPlayer(player) {
  document.title = `${player.player_name} | SPLStats`;

  document.querySelector("#playerName").textContent =
    player.player_name;

  document.querySelector("#careerTitle").textContent =
    `${player.player_name}'s Career Totals`;

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
      [
        "Save %",
        career.save_percent
          ? (career.save_percent / 100).toFixed(3).replace(/^0/, "")
          : ".000"
      ],
      ["GAA", career.gaa ? career.gaa.toFixed(2) : "0.00"],
      ["Saves", career.saves],
      ["Blocks", career.blocks]
    ],

    [
      ["Shots Against", career.shots_against],
      ["Goals Against", career.goals_against],
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
      ["Passes", career.passes],
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