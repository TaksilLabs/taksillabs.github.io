function setTeamFavicon(team) {
  const logo = getTeamLogo(team);

  if (!logo) return;

  let favicon = document.querySelector("#dynamicFavicon");

  if (!favicon) {
    favicon = document.createElement("link");
    favicon.id = "dynamicFavicon";
    favicon.rel = "icon";
    favicon.type = "image/png";
    document.head.appendChild(favicon);
  }

  favicon.href = logo;
}

function getPlayerUrlId(player) {
  return (
    player.player_id
    || player.player_name
    || player.player_display_name
    || ""
  );
}

function getPlayerDisplayName(player) {
  return (
    player.player_display_name
    || player.player_name
    || player.player_id
    || "Unknown Player"
  );
}

const LIVE_SEASON_ID = "summer_2026";

const LIVE_DATA_PATHS = {
  activeRosters: `data/live_season/${LIVE_SEASON_ID}/active_rosters.json`,
  preseasonSchedule: `data/live_season/${LIVE_SEASON_ID}/preseason/schedule.json`,
  preseasonMatches: `data/live_season/${LIVE_SEASON_ID}/preseason/matches.json`
};

let teamScheduleExpanded = false;

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

function normalizeTeamId(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[_\-\s]+/g, "_");
}

function getTeamIdFromUrl() {
  const params = new URLSearchParams(window.location.search);

  return (
    params.get("id")
    || params.get("team")
    || ""
  );
}

function teamMatchesUrlId(team, urlId) {
  const target = normalizeTeamId(urlId);

  if (normalizeTeamId(team.team_id) === target) return true;
  if (normalizeTeamId(team.team_name) === target) return true;
  if (normalizeTeamId(team.team_display_name) === target) return true;
  if (normalizeTeamId(team.team) === target) return true;

  return [
    ...(team.team_aliases || []),
    ...(team.aliases || [])
  ].some(alias =>
    normalizeTeamId(alias) === target
  );
}

function getTeamDisplayName(team) {
  return (
    team.team_display_name
    || team.team_name
    || team.team
    || team.team_id
    || "Unknown Team"
  );
}

function getTeamTheme(team) {
  return team.theme || {};
}

function getTeamLogo(team) {
  return team.logo || "";
}

function applyTeamTheme(team) {
  const theme = getTeamTheme(team);

  document.documentElement.style.setProperty("--team-primary", theme.primary || "#2ecc71");
  document.documentElement.style.setProperty("--team-secondary", theme.secondary || "#111111");
  document.documentElement.style.setProperty("--team-accent", theme.accent || "#ffffff");
  document.documentElement.style.setProperty("--team-background", theme.background || "#050505");
  document.documentElement.style.setProperty("--team-card", theme.card || "#111111");
  document.documentElement.style.setProperty("--team-surface", theme.surface || "#1a1a1a");
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
                <a href="player.html?id=${encodeURIComponent(getPlayerUrlId(p))}">
                    ${getPlayerDisplayName(p)}
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

function findTeamFranchise(team, franchises) {
  const teamId = normalizeTeamId(team.team_id);
  const teamName = normalizeTeamId(getTeamDisplayName(team));

  for (const franchise of franchises) {
    const membership = (franchise.memberships || []).find(m => {
      if (normalizeTeamId(m.team_id) === teamId) {
        return true;
      }

      return normalizeTeamId(m.team) === teamName;
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

function renderTeamFranchise(team, franchises) {
  const result = findTeamFranchise(team, franchises);

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

function findTeamRecord(team, teamRecords) {
  const teamId = normalizeTeamId(team.team_id);
  const teamName = normalizeTeamId(getTeamDisplayName(team));

  return teamRecords.find(record => {
    if (normalizeTeamId(record.team_id) === teamId) return true;
    if (normalizeTeamId(record.team) === teamName) return true;
    if (normalizeTeamId(record.team_display_name) === teamName) return true;

    return false;
  }) || null;
}

function mergeTeamMetadataForProfile(builtTeams, metadataTeams) {
  const merged = new Map();

  builtTeams.forEach(team => {
    const teamId = normalizeTeamId(
      team.team_id
      || team.team_display_name
      || team.team_name
      || team.team
    );

    merged.set(teamId, {
      ...team,
      team_id: team.team_id || teamId,
      team_display_name:
        team.team_display_name
        || team.team_name
        || team.team
        || teamId,
      has_stats: true
    });
  });

  metadataTeams.forEach(meta => {
    const teamId = normalizeTeamId(meta.team_id);

    if (!teamId) return;

    const existing = merged.get(teamId) || {};

    merged.set(teamId, {
      ...existing,

      team_id: meta.team_id,
      team_name:
        meta.team_display_name
        || existing.team_name
        || existing.team_display_name
        || meta.team_id,

      team_display_name:
        meta.team_display_name
        || existing.team_display_name
        || existing.team_name
        || meta.team_id,

      team_aliases:
        meta.aliases
        || existing.team_aliases
        || [],

      logo:
        meta.logo
        || existing.logo
        || "",

      theme:
        meta.theme
        || existing.theme
        || {},

      name_history:
        meta.name_history
        || existing.name_history
        || [],

      career: existing.career || {},
      seasons: existing.seasons || [],
      divisions: existing.divisions || [],
      players: existing.players || [],
      has_stats: Boolean(existing.has_stats)
    });
  });

  return [...merged.values()];
}

async function loadTeam() {
  const teamUrlId = getTeamIdFromUrl();

  const [
    builtTeams,
    metadataTeams,
    franchises,
    teamRecords,
    championships,
    activeRosters,
    preseasonSchedule,
    preseasonMatches
  ] = await Promise.all([
    fetchJsonOrFallback("data/teams.json", []),
    fetchJsonOrFallback("data/team_metadata.json", []),
    fetchJsonOrFallback("data/franchises.json", []),
    fetchJsonOrFallback("data/team_records.json", []),
    fetchJsonOrFallback("data/championships.json", []),
    fetchJsonOrFallback(LIVE_DATA_PATHS.activeRosters, { teams: [] }),
    fetchJsonOrFallback(LIVE_DATA_PATHS.preseasonSchedule, []),
    fetchJsonOrFallback(LIVE_DATA_PATHS.preseasonMatches, [])
  ]);

  const teams = mergeTeamMetadataForProfile(builtTeams, metadataTeams);

  const team = teams.find(t =>
    teamMatchesUrlId(t, teamUrlId)
  );

  if (!team) {
    document.querySelector("#teamName").textContent = "Team Not Found";
    return;
  }

  const teamRecord = findTeamRecord(
    team,
    teamRecords
  );

  renderTeam(team, teamRecord, championships);
  renderTeamFranchise(team, franchises);

  renderActiveRoster(team, activeRosters);
  renderLiveTeamSchedule(team, preseasonSchedule, preseasonMatches, metadataTeams);
}

function normalizeTeamNameForCompare(name) {
  return String(name || "")
    .replace(/\s*\([^)]*\)$/, "")
    .trim()
    .toLowerCase();
}

function getTeamChampionships(team, championships = []) {
  const teamId = normalizeTeamId(team.team_id);
  const teamName = normalizeTeamId(getTeamDisplayName(team));

  return championships.filter(champ => {
    if (normalizeTeamId(champ.winner_team_id) === teamId) {
      return true;
    }

    return normalizeTeamId(champ.winner_team) === teamName;
  });
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

function normalizeLiveTeamValue(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/['’]/g, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_|_$/g, "");
}

function getActiveRosterTeams(activeRosters) {
  if (Array.isArray(activeRosters)) {
    return activeRosters;
  }

  if (Array.isArray(activeRosters?.teams)) {
    return activeRosters.teams;
  }

  if (activeRosters && typeof activeRosters === "object") {
    return Object.values(activeRosters);
  }

  return [];
}

function activeRosterMatchesTeam(rosterTeam, team) {
  const targets = [
    team.team_id,
    team.team_name,
    team.team_display_name,
    team.team,
    ...(team.team_aliases || []),
    ...(team.aliases || [])
  ]
    .map(normalizeLiveTeamValue)
    .filter(Boolean);

  const rosterValues = [
    rosterTeam.team_id,
    rosterTeam.team_name,
    rosterTeam.team_display_name,
    rosterTeam.team
  ]
    .map(normalizeLiveTeamValue)
    .filter(Boolean);

  return rosterValues.some(value => targets.includes(value));
}

function findActiveRosterForTeam(team, activeRosters) {
  return getActiveRosterTeams(activeRosters).find(rosterTeam =>
    activeRosterMatchesTeam(rosterTeam, team)
  ) || null;
}

function roleSortValue(role) {
  const cleanRole = String(role || "").toLowerCase();

  if (cleanRole === "gm") return 1;
  if (cleanRole === "captain") return 2;

  return 3;
}

function roleLabel(role) {
  const cleanRole = String(role || "").toLowerCase();

  if (cleanRole === "gm") return "GM";
  if (cleanRole === "captain") return "Captain";

  return "Player";
}

function getRosterPlayerName(player) {
  return (
    player.steam_name
    || player.player_name
    || player.name
    || player.slap_id
    || "Unknown Player"
  );
}

function getRosterPlayerUrlId(player) {
  return (
    player.player_id
    || player.player_name
    || player.player_display_name
    || player.name
    || player.steam_name
    || player.slap_id
    || ""
  );
}

function renderActiveRoster(team, activeRosters) {
  const section = document.querySelector("#teamActiveRosterSection");
  const container = document.querySelector("#teamActiveRoster");

  if (!section || !container) {
    return;
  }

  const activeRoster = findActiveRosterForTeam(team, activeRosters);

  if (!activeRoster || !(activeRoster.players || []).length) {
    section.style.display = "none";
    container.innerHTML = "";
    return;
  }

  section.style.display = "";

  const players = [...(activeRoster.players || [])]
    .sort((a, b) =>
      roleSortValue(a.role) - roleSortValue(b.role)
      || getRosterPlayerName(a).localeCompare(getRosterPlayerName(b))
    );

  container.innerHTML = players.map(player => {
    const name = getRosterPlayerName(player);
    const urlId = getRosterPlayerUrlId(player);

    return `
      <a class="active-roster-chip" href="player.html?id=${encodeURIComponent(urlId)}">
        <span>${roleLabel(player.role)}</span>
        <strong>${name}</strong>
      </a>
    `;
  }).join("");
}

function getMatchArray(data) {
  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data?.matches)) {
    return data.matches;
  }

  if (Array.isArray(data?.schedule)) {
    return data.schedule;
  }

  if (data && typeof data === "object") {
    return Object.values(data);
  }

  return [];
}

function getMatchTeamNames(match) {
  return {
    home:
      match.home_team
      || match.home
      || match.home_team_name
      || "",
    away:
      match.away_team
      || match.away
      || match.away_team_name
      || ""
  };
}

function matchIncludesTeam(match, team) {
  const teamValues = [
    team.team_id,
    team.team_name,
    team.team_display_name,
    team.team,
    ...(team.team_aliases || []),
    ...(team.aliases || [])
  ]
    .map(normalizeLiveTeamValue)
    .filter(Boolean);

  const { home, away } = getMatchTeamNames(match);

  const matchValues = [
    match.home_team_id,
    match.away_team_id,
    home,
    away
  ]
    .map(normalizeLiveTeamValue)
    .filter(Boolean);

  return matchValues.some(value => teamValues.includes(value));
}

function getMatchStatus(match) {
  return String(match.status || match.match_status || "").toLowerCase();
}

function isFinalMatch(match) {
  const status = getMatchStatus(match);

  return (
    status === "final"
    || status === "completed"
    || status === "complete"
  );
}

function isScheduledMatch(match) {
  const status = getMatchStatus(match);

  return (
    status === "scheduled"
    || status === "pending"
    || status === "upcoming"
    || !status
  );
}

function getRegularSeasonSortParts(match) {
  const text = String(
    match.schedule_id
    || match.match_code
    || match.match_id
    || ""
  );

  const prefixMatch = text.match(/^(\d+)\.(\d+)/);

  if (!prefixMatch) {
    return {
      week: Number(match.week || 0),
      matchNumber: Number(match.match_number || 0)
    };
  }

  return {
    week: Number(prefixMatch[1]),
    matchNumber: Number(prefixMatch[2])
  };
}

function getMatchSortValue(match) {
  const parts = getRegularSeasonSortParts(match);

  return (
    (parts.week || 0) * 1000
    + (parts.matchNumber || 0)
  );
}

function combineLiveMatches(scheduleData, matchesData) {
  const combined = new Map();

  [...getMatchArray(scheduleData), ...getMatchArray(matchesData)].forEach(match => {
    const key =
      match.match_id
      || match.schedule_id
      || match.match_code
      || `${match.home_team || match.home || ""}_${match.away_team || match.away || ""}_${match.datetime_utc || match.date || ""}`;

    if (!key) {
      return;
    }

    combined.set(key, {
      ...(combined.get(key) || {}),
      ...match
    });
  });

  return [...combined.values()];
}

function getTeamScore(match, team) {
  const teamValues = [
    team.team_id,
    team.team_name,
    team.team_display_name,
    team.team,
    ...(team.team_aliases || []),
    ...(team.aliases || [])
  ]
    .map(normalizeLiveTeamValue)
    .filter(Boolean);

  const homeName =
    match.home_team
    || match.home
    || match.home_team_name
    || "";

  const awayName =
    match.away_team
    || match.away
    || match.away_team_name
    || "";

  const homeValues = [
    match.home_team_id,
    homeName
  ]
    .map(normalizeLiveTeamValue)
    .filter(Boolean);

  const awayValues = [
    match.away_team_id,
    awayName
  ]
    .map(normalizeLiveTeamValue)
    .filter(Boolean);

  if (homeValues.some(value => teamValues.includes(value))) {
    return {
      teamScore:
        match.home_score
        ?? match.home_goals
        ?? match.home_team_score
        ?? null,
      opponentScore:
        match.away_score
        ?? match.away_goals
        ?? match.away_team_score
        ?? null,
      opponent: awayName,
      side: "home"
    };
  }

  if (awayValues.some(value => teamValues.includes(value))) {
    return {
      teamScore:
        match.away_score
        ?? match.away_goals
        ?? match.away_team_score
        ?? null,
      opponentScore:
        match.home_score
        ?? match.home_goals
        ?? match.home_team_score
        ?? null,
      opponent: homeName,
      side: "away"
    };
  }

  return {
    teamScore: null,
    opponentScore: null,
    opponent: "",
    side: ""
  };
}

function getMatchDisplayCode(match) {
  return (
    match.schedule_id
    || match.match_code
    || match.match_id
    || "—"
  );
}

function getMatchDisplayDate(match) {
  const raw =
    match.datetime_utc
    || match.scheduled_utc
    || match.match_time
    || match.date
    || "";

  if (!raw) {
    return "";
  }

  const date = new Date(raw);

  if (Number.isNaN(date.getTime())) {
    return raw;
  }

  return date.toLocaleString([], {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

function getResultClass(score) {
  const teamScore = Number(score.teamScore);
  const opponentScore = Number(score.opponentScore);

  if (!Number.isFinite(teamScore) || !Number.isFinite(opponentScore)) {
    return "";
  }

  if (teamScore > opponentScore) return "team-match-win";
  if (teamScore < opponentScore) return "team-match-loss";

  return "team-match-tie";
}

function getTeamMetadataList(teamMetadata) {
  if (Array.isArray(teamMetadata)) {
    return teamMetadata;
  }

  if (Array.isArray(teamMetadata?.teams)) {
    return teamMetadata.teams;
  }

  if (teamMetadata && typeof teamMetadata === "object") {
    return Object.values(teamMetadata);
  }

  return [];
}

function findTeamMetadataByName(teamName, teamMetadata = []) {
  const target = normalizeLiveTeamValue(teamName);

  return getTeamMetadataList(teamMetadata).find(team => {
    const values = [
      team.team_id,
      team.team_display_name,
      team.team_name,
      team.team,
      ...(team.aliases || []),
      ...(team.team_aliases || [])
    ]
      .map(normalizeLiveTeamValue)
      .filter(Boolean);

    return values.includes(target);
  }) || null;
}

function getOpponentLogo(metadata) {
  return (
    metadata?.logo
    || metadata?.team_logo
    || metadata?.logo_path
    || ""
  );
}

function getOpponentThemeValue(metadata, key, fallback) {
  return (
    metadata?.theme?.[key]
    || metadata?.colors?.[key]
    || metadata?.[key]
    || fallback
  );
}

function getMatchHomeAwayLabel(match, team) {
  const score = getTeamScore(match, team);

  if (score.side === "home") return "VS";
  if (score.side === "away") return "@";

  return "VS";
}

function renderTeamMatchRow(match, team, type, teamMetadata = []) {
  const score = getTeamScore(match, team);
  const opponent = score.opponent || "TBD";
  const dateText = getMatchDisplayDate(match);

  const opponentMetadata = findTeamMetadataByName(opponent, teamMetadata);
  const opponentLogo = getOpponentLogo(opponentMetadata);

  const opponentPrimary = getOpponentThemeValue(
    opponentMetadata,
    "primary",
    "rgba(255, 255, 255, 0.16)"
  );

  const opponentAccent = getOpponentThemeValue(
    opponentMetadata,
    "accent",
    "rgba(255, 255, 255, 0.44)"
  );

  const locationLabel = getMatchHomeAwayLabel(match, team);

  const resultLabel =
    type === "result"
      ? `${score.teamScore ?? 0} - ${score.opponentScore ?? 0}`
      : "Scheduled";

  const matchId =
    match.match_id
    || match.id
    || "";

  const href = matchId
    ? `match.html?id=${encodeURIComponent(matchId)}`
    : "#";

  return `
    <a
      class="team-match-row ${type} ${getResultClass(score)}"
      href="${href}"
      style="
        --opponent-primary: ${opponentPrimary};
        --opponent-accent: ${opponentAccent};
      "
    >
      <div class="team-match-location">${locationLabel}</div>

      <div class="team-match-opponent-logo-wrap">
        ${
          opponentLogo
            ? `<img class="team-match-opponent-logo" src="${opponentLogo}" alt="">`
            : `<div class="team-match-opponent-placeholder">${opponent.slice(0, 1)}</div>`
        }
      </div>

      <div class="team-match-main">
        <strong>${opponent}</strong>
        <span>${type === "result" ? "Final" : dateText || "Upcoming"}</span>
      </div>

      <div class="team-match-score">
        ${resultLabel}
      </div>
    </a>
  `;
}

function renderLiveTeamSchedule(team, scheduleData, matchesData, teamMetadata = []) {
  const section = document.querySelector("#teamLiveScheduleSection");
  const recentContainer = document.querySelector("#teamRecentResults");
  const upcomingContainer = document.querySelector("#teamUpcomingMatches");
  const toggleButton = document.querySelector("#teamScheduleToggle");

  if (!section || !recentContainer || !upcomingContainer) {
    return;
  }

  const teamMatches = combineLiveMatches(scheduleData, matchesData)
    .filter(match => matchIncludesTeam(match, team))
    .sort((a, b) => getMatchSortValue(a) - getMatchSortValue(b));

  const recent = teamMatches
    .filter(isFinalMatch)
    .sort((a, b) => getMatchSortValue(b) - getMatchSortValue(a));

  const upcoming = teamMatches
    .filter(isScheduledMatch)
    .sort((a, b) => getMatchSortValue(a) - getMatchSortValue(b));

  if (!recent.length && !upcoming.length) {
    section.style.display = "none";
    return;
  }

  section.style.display = "";

  const recentLimit = teamScheduleExpanded ? recent.length : 6;
  const upcomingLimit = teamScheduleExpanded ? upcoming.length : 6;

  recentContainer.innerHTML = recent.length
    ? recent.slice(0, recentLimit).map(match =>
        renderTeamMatchRow(match, team, "result", teamMetadata)
      ).join("")
    : `<div class="team-empty-live">No recent results.</div>`;

  upcomingContainer.innerHTML = upcoming.length
    ? upcoming.slice(0, upcomingLimit).map(match =>
        renderTeamMatchRow(match, team, "scheduled", teamMetadata)
      ).join("")
    : `<div class="team-empty-live">No upcoming matches.</div>`;

  const canExpand = recent.length > 6 || upcoming.length > 6;

  if (toggleButton) {
    toggleButton.style.display = canExpand ? "" : "none";
    toggleButton.textContent = teamScheduleExpanded ? "Show Less" : "Show More";

    toggleButton.onclick = () => {
      teamScheduleExpanded = !teamScheduleExpanded;
      renderLiveTeamSchedule(team, scheduleData, matchesData, teamMetadata);
    };
  }
}

function renderTeam(team, teamRecord, championships = []) {
  const displayName = getTeamDisplayName(team);
  const logo = getTeamLogo(team);

  applyTeamTheme(team);
  setTeamFavicon(team);

  document.title = `${displayName} | SPLStats`;

  document.querySelector("#teamName").textContent =
    displayName;

  const logoEl = document.querySelector("#teamLogo");

  if (logoEl) {
    if (logo) {
      logoEl.src = logo;
      logoEl.alt = `${displayName} logo`;
      logoEl.style.display = "";
    } else {
      logoEl.style.display = "none";
    }
  }

  renderTeamLeaders(team.players || []);
  renderTeamChampionships(team, championships);
  renderCareer(team.career || {}, teamRecord);
  renderSeasons(team.seasons || []);
  renderDivisions(team.divisions || []);
  renderRoster(team.players || []);
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
        <a href="player.html?id=${encodeURIComponent(getPlayerUrlId(player))}">
          ${getPlayerDisplayName(player)}
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