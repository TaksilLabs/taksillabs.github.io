const SEASON_ID = "summer_2026";
const SEASON_TYPE = "regular_season";

const SPL_LOGO = "assets/images/spl-logo.png";

// Edit this if your player cards live somewhere else.
// Default expected format:
// assets/images/player_cards/865092.webp
const PLAYER_CARD_BASE_PATH = "assets/images/player_cards";
const PLAYER_CARD_EXT = "webp";

const DATA_PATHS = {
  schedule: `data/live_season/${SEASON_ID}/${SEASON_TYPE}/schedule.json`,
  matches: `data/live_season/${SEASON_ID}/${SEASON_TYPE}/matches.json`,
  standings: `data/live_season/${SEASON_ID}/${SEASON_TYPE}/standings.json`,
  leaders: `data/live_season/${SEASON_ID}/${SEASON_TYPE}/leaders.json`,
  rosters: `data/live_season/${SEASON_ID}/active_rosters.json`,
  teamMetadata: "data/team_metadata.json"
};

const DIVISION_LABELS = {
  pro: "Pro",
  challenger: "Challenger",
  intermediate: "Intermediate",
  prospect: "Prospect",
  open: "Open",
  central_a: "Central A",
  central_b: "Central B",
  central_c: "Central C",
  central_d: "Central D",
  masters: "Masters",
  contenders: "Contenders"
};

const DIVISION_SHIELDS = {
  pro: "assets/images/divisions/pro.png",
  challenger: "assets/images/divisions/challenger.png",
  intermediate: "assets/images/divisions/intermediate.png",
  prospect: "assets/images/divisions/prospect.png",
  open: "assets/images/divisions/open.png",

  central_a: "assets/images/divisions/central-a.png",
  central_b: "assets/images/divisions/central-b.png",
  central_c: "assets/images/divisions/central-c.png",
  central_d: "assets/images/divisions/central-d.png",

  masters: "assets/images/divisions/masters.png",
  contenders: "assets/images/divisions/contenders.png"
};

const DEFAULT_AWAY_COLOR = "#1262be"; // SPL Blue
const DEFAULT_HOME_COLOR = "#d63730"; // SPL Red

function cleanText(value) {
  return String(value || "").trim();
}

function normalizeKey(value) {
  return cleanText(value)
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function escapeAttr(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function fetchJsonOrFallback(url, fallback) {
  try {
    const response = await fetch(url);

    if (!response.ok) {
      return fallback;
    }

    return await response.json();
  } catch (error) {
    console.warn(`Could not load ${url}`, error);
    return fallback;
  }
}

function getMatchIdFromUrl() {
  const params = new URLSearchParams(window.location.search);

  return cleanText(
    params.get("match")
    || params.get("id")
    || ""
  );
}

function getArrayFromData(data, keys) {
  if (Array.isArray(data)) return data;

  for (const key of keys) {
    if (Array.isArray(data?.[key])) {
      return data[key];
    }
  }

  return [];
}

function getMatchId(match) {
  return cleanText(
    match.match_id
    || match.id
    || match.schedule_id
    || match.source_id
  );
}

function getTeamIdFromMatch(match, side) {
  if (side === "away") {
    return normalizeKey(
      match.away_team_id
      || match.away_id
      || match.away_team
      || match.team_a_id
      || match.team_a
    );
  }

  return normalizeKey(
    match.home_team_id
    || match.home_id
    || match.home_team
    || match.team_b_id
    || match.team_b
  );
}

function getTeamNameFromMatch(match, side) {
  if (side === "away") {
    return cleanText(
      match.away_team_display_name
      || match.away_team_name
      || match.away_team
      || match.team_a_display_name
      || match.team_a
    );
  }

  return cleanText(
    match.home_team_display_name
    || match.home_team_name
    || match.home_team
    || match.team_b_display_name
    || match.team_b
  );
}

function findMatch(scheduleData, matchesData, targetId) {
  const schedule = getArrayFromData(scheduleData, ["matches", "schedule"]);
  const matches = getArrayFromData(matchesData, ["matches"]);

  const byId = new Map();

  schedule.forEach(match => {
    const id = getMatchId(match);

    if (id) {
      byId.set(id, match);
    }
  });

  matches.forEach(match => {
    const id = getMatchId(match);

    if (!id) return;

    byId.set(id, {
      ...(byId.get(id) || {}),
      ...match
    });
  });

  return byId.get(targetId) || null;
}

function getTeamMetadataMap(data) {
  if (!data) return {};

  if (Array.isArray(data)) {
    const map = {};

    data.forEach(team => {
      const id = normalizeKey(team.team_id || team.id || team.name);

      if (id) {
        map[id] = team;
      }
    });

    return map;
  }

  if (Array.isArray(data.teams)) {
    const map = {};

    data.teams.forEach(team => {
      const id = normalizeKey(team.team_id || team.id || team.name);

      if (id) {
        map[id] = team;
      }
    });

    return map;
  }

  return data;
}

function getTeamMeta(teamMetadata, teamId) {
  const key = normalizeKey(teamId);

  return teamMetadata[key]
    || teamMetadata[teamId]
    || {};
}

function getTeamLogo(teamMetadata, teamId) {
  const meta = getTeamMeta(teamMetadata, teamId);

  return cleanText(
    meta.logo
    || meta.logo_url
    || meta.logo_path
    || meta.image
    || meta.image_path
    || ""
  );
}

function getTeamThemeColor(teamMetadata, teamId, slot, fallback) {
  const meta = getTeamMeta(teamMetadata, teamId);

  return cleanText(
    meta[slot]
    || meta[`${slot}_color`]
    || meta.colors?.[slot]
    || meta.theme?.[slot]
    || fallback
  );
}

function getTeamAccentColor(teamMetadata, teamId, fallback) {
  const meta = getTeamMeta(teamMetadata, teamId);

  return cleanText(
    meta.accent
    || meta.accent_color
    || meta.colors?.accent
    || meta.theme?.accent
    || meta.secondary
    || meta.secondary_color
    || meta.colors?.secondary
    || meta.theme?.secondary
    || fallback
  );
}

function getDivisionKey(match) {
  return normalizeKey(match.division || match.fixture_group || "");
}

function getDivisionLabel(division) {
  const key = normalizeKey(division);

  return DIVISION_LABELS[key] || cleanText(division) || "SPL";
}

function getDivisionShield(division) {
  return DIVISION_SHIELDS[normalizeKey(division)] || "";
}

function getMatchWeek(match) {
  return cleanText(match.week || match.match_week || "");
}

function formatSeasonLabel() {
  return SEASON_ID
    .replace(/_/g, " ")
    .replace(/\b\w/g, letter => letter.toUpperCase());
}

function getShortTeamName(name) {
  const text = cleanText(name);
  const words = text.split(/\s+/);

  if (words.length <= 1) return text;

  return words.slice(-1)[0];
}

function getRosterTeams(rosterData) {
  if (Array.isArray(rosterData)) return rosterData;
  if (Array.isArray(rosterData?.teams)) return rosterData.teams;
  return [];
}

function getRosterPlayersForTeam(rosterData, teamId) {
  const target = normalizeKey(teamId);

  const team = getRosterTeams(rosterData).find(row => {
    return normalizeKey(row.team_id || row.id || row.team_name || row.name) === target;
  });

  if (!team) return [];

  return Array.isArray(team.players)
    ? team.players
    : [];
}

function getPlayerId(player) {
  return normalizeKey(
    player.player_id
    || player.id
    || player.name
    || player.display_name
    || player.steam_name
  );
}

function getPlayerDisplayName(player) {
  return cleanText(
    player.player_display_name
    || player.display_name
    || player.player_name
    || player.name
    || player.steam_name
    || player.player_id
    || "Unknown Player"
  );
}

function getLeaderPlayers(leaderData) {
  if (Array.isArray(leaderData)) return leaderData;
  if (Array.isArray(leaderData?.players)) return leaderData.players;
  return [];
}

function getStatsForPlayer(leaderData, teamId, player) {
  const targetTeam = normalizeKey(teamId);
  const targetPlayer = getPlayerId(player);
  const targetSlapId = cleanText(player.slap_id || player.slapshot_id || player.slapId);

  return getLeaderPlayers(leaderData).find(row => {
    const rowTeam = normalizeKey(row.team_id || row.team || row.team_name);
    const rowPlayer = normalizeKey(row.player_id || row.steam_name || row.player_name || row.player_display_name);
    const rowSlapId = cleanText(row.slap_id || row.slapshot_id || row.slapId);

    const sameTeam = rowTeam === targetTeam;
    const samePlayer = rowPlayer === targetPlayer || (targetSlapId && rowSlapId === targetSlapId);

    return sameTeam && samePlayer;
  }) || {};
}

function getStatNumber(row, keys) {
  for (const key of keys) {
    const value = row?.[key];

    if (value !== undefined && value !== null && value !== "") {
      const number = Number(value);

      if (Number.isFinite(number)) {
        return number;
      }
    }
  }

  return 0;
}

function getScorerGoals(stats) {
  return getStatNumber(stats, ["goals", "g"]);
}

function getScorerAssists(stats) {
  return getStatNumber(stats, ["assists", "a"]);
}

function getScorerPoints(stats) {
  const explicit = getStatNumber(stats, ["points", "pts"]);

  if (explicit) return explicit;

  return getScorerGoals(stats) + getScorerAssists(stats);
}

function getScorerShots(stats) {
  return getStatNumber(stats, ["shots", "sog", "shot_count"]);
}

function getScorerGamesPlayed(stats) {
  return getStatNumber(stats, [
    "games_played",
    "gamesPlayed",
    "gp"
  ]);
}

function formatInteger(value) {
  const number = Number(value || 0);

  if (!number) return "—";

  return number.toLocaleString("en-US");
}

function getOrdinalSuffix(number) {
  const value = Math.abs(Number(number || 0));
  const mod100 = value % 100;

  if (mod100 >= 11 && mod100 <= 13) return "th";

  switch (value % 10) {
    case 1:
      return "st";
    case 2:
      return "nd";
    case 3:
      return "rd";
    default:
      return "th";
  }
}

function formatRank(rankInfo) {
  if (!rankInfo || !rankInfo.rank) return "—";

  const prefix = rankInfo.tied ? "T-" : "";
  return `${prefix}${rankInfo.rank}${getOrdinalSuffix(rankInfo.rank)}`;
}

function rowMatchesDivision(row, division) {
  const target = normalizeKey(division);

  if (!target) return false;

  const possibleDivisionValues = [
    row.division,
    row.division_key,
    row.divisionKey,
    row.fixture_group,
    row.fixtureGroup,
    row.group,
    row.group_key
  ];

  return possibleDivisionValues.some(value => normalizeKey(value) === target);
}

function getDivisionLeaderRows(leaderData, division) {
  const rows = getLeaderPlayers(leaderData);
  const filtered = rows.filter(row => rowMatchesDivision(row, division));

  // If leaders.json is already scoped to this division, or does not carry division fields,
  // fall back to all leader rows instead of producing empty rankings.
  return filtered.length ? filtered : rows;
}

function getLeaderRowPlayerKey(row) {
  const slapId = cleanText(row.slap_id || row.slapshot_id || row.slapId);

  if (slapId) {
    return `slap:${slapId}`;
  }

  return `player:${normalizeKey(
    row.player_id
    || row.steam_name
    || row.player_name
    || row.player_display_name
    || row.name
  )}`;
}

function getScorerMetricValue(row, metric) {
  if (metric === "goals") return getScorerGoals(row);
  if (metric === "points") return getScorerPoints(row);
  if (metric === "shots") return getScorerShots(row);
  if (metric === "gamesPlayed") return getScorerGamesPlayed(row);

  return 0;
}

function makeRankMap(rows, metric, direction = "desc") {
  const rankedRows = rows
    .map(row => {
      return {
        key: getLeaderRowPlayerKey(row),
        value: getScorerMetricValue(row, metric)
      };
    })
    .filter(row => row.key && Number.isFinite(row.value) && row.value > 0)
    .sort((a, b) => {
      if (direction === "asc") {
        return a.value - b.value;
      }

      return b.value - a.value;
    });

  const rankMap = new Map();
  let previousValue = null;
  let previousRank = 0;

  rankedRows.forEach((row, index) => {
    const rank = previousValue === row.value
      ? previousRank
      : index + 1;

    previousValue = row.value;
    previousRank = rank;

    rankMap.set(row.key, {
      rank,
      tied: false
    });
  });

  const countsByRank = new Map();

  rankMap.forEach(info => {
    countsByRank.set(info.rank, (countsByRank.get(info.rank) || 0) + 1);
  });

  rankMap.forEach(info => {
    info.tied = (countsByRank.get(info.rank) || 0) > 1;
  });

  return rankMap;
}

function makeDivisionScorerRankings(leaderData, division) {
  const rows = getDivisionLeaderRows(leaderData, division);

  return {
    goals: makeRankMap(rows, "goals", "desc"),
    points: makeRankMap(rows, "points", "desc"),
    shots: makeRankMap(rows, "shots", "desc"),
    gamesPlayed: makeRankMap(rows, "gamesPlayed", "desc")
  };
}

function getScorerRankKey(scorer) {
  if (scorer.slap_id) {
    return `slap:${scorer.slap_id}`;
  }

  return `player:${normalizeKey(scorer.player_display_name)}`;
}

function getScorerRankingsForPlayer(scorer, divisionRankings) {
  const key = getScorerRankKey(scorer);

  return {
    goals: divisionRankings.goals.get(key) || null,
    points: divisionRankings.points.get(key) || null,
    shots: divisionRankings.shots.get(key) || null,
    gamesPlayed: divisionRankings.gamesPlayed.get(key) || null
  };
}

function getPlayerCardCandidates(player) {
  const slapId = cleanText(player.slap_id || player.slapshot_id || player.slapId);
  const displayName = getPlayerDisplayName(player);
  const normalizedName = normalizeKey(displayName);

  const candidates = [];

  if (slapId) {
    candidates.push(`${PLAYER_CARD_BASE_PATH}/${slapId}.${PLAYER_CARD_EXT}`);
  }

  if (normalizedName) {
    candidates.push(`${PLAYER_CARD_BASE_PATH}/${normalizedName}.${PLAYER_CARD_EXT}`);
  }

  if (displayName) {
    candidates.push(`${PLAYER_CARD_BASE_PATH}/${encodeURIComponent(displayName)}.${PLAYER_CARD_EXT}`);
  }

  return [...new Set(candidates)];
}

window.loadNextScorerCard = function loadNextScorerCard(img) {
  const candidates = String(img.dataset.cardCandidates || "")
    .split("|")
    .filter(Boolean);

  const currentIndex = Number(img.dataset.cardIndex || 0);
  const nextIndex = currentIndex + 1;

  if (candidates[nextIndex]) {
    img.dataset.cardIndex = String(nextIndex);
    img.src = candidates[nextIndex];
    return;
  }

  const card = img.closest(".scorer-player-card");

  if (card) {
    card.classList.add("missing-card");
  }

  img.remove();
};

function makeTopGoalscorer(rosterData, leaderData, teamId, divisionRankings) {
  const rosterPlayers = getRosterPlayersForTeam(rosterData, teamId).filter(player => {
    const role = normalizeKey(player.role);

    return role !== "gm" && role !== "general_manager";
  });

  const scorerRows = rosterPlayers.map(player => {
    const stats = getStatsForPlayer(leaderData, teamId, player);
    const goals = getScorerGoals(stats);
    const points = getScorerPoints(stats);
    const shots = getScorerShots(stats);
    const gamesPlayed = getScorerGamesPlayed(stats);
    const cardCandidates = getPlayerCardCandidates(player);

    return {
      player_id: getPlayerId(player),
      player_display_name: getPlayerDisplayName(player),
      slap_id: cleanText(player.slap_id || player.slapshot_id || player.slapId),
      cardCandidates,
      goals,
      points,
      shots,
      gamesPlayed,
      ranks: {}
    };
  });

  const scorer = scorerRows.sort((a, b) => {
    return b.goals - a.goals
      || b.points - a.points
      || b.shots - a.shots
      || b.gamesPlayed - a.gamesPlayed
      || a.player_display_name.localeCompare(b.player_display_name);
  })[0] || null;

  if (scorer && divisionRankings) {
    scorer.ranks = getScorerRankingsForPlayer(scorer, divisionRankings);
  }

  return scorer;
}

function getStandingsRows(standingsData) {
  if (Array.isArray(standingsData)) return standingsData;
  if (Array.isArray(standingsData?.standings)) return standingsData.standings;
  if (Array.isArray(standingsData?.teams)) return standingsData.teams;
  return [];
}

function getTeamStanding(standingsData, teamId) {
  const target = normalizeKey(teamId);

  return getStandingsRows(standingsData).find(row => {
    const possibleIds = [
      row.team_id,
      row.id,
      row.team,
      row.team_name,
      row.display_name,
      row.name,
      row.abbreviation,
      row.short_name
    ];

    return possibleIds.some(value => normalizeKey(value) === target);
  }) || {};
}

function formatRecord(standingsData, teamId) {
  const row = getTeamStanding(standingsData, teamId);

  const wins = Number(row.wins ?? row.w ?? row.win ?? 0);
  const losses = Number(
    row.regulation_losses
    ?? row.regulationLosses
    ?? row.losses
    ?? row.l
    ?? row.loss
    ?? 0
  );
  const otl = Number(
    row.overtime_losses
    ?? row.overtimeLosses
    ?? row.ot_losses
    ?? row.otLosses
    ?? row.otl
    ?? 0
  );

  return `${wins} - ${losses} - ${otl}`;
}

function makeTeamView(match, side, data, fallbackColor) {
  const teamMetadata = data.teamMetadata;
  const division = getDivisionKey(match);
  const divisionRankings = makeDivisionScorerRankings(data.leaders, division);

  const teamId = getTeamIdFromMatch(match, side);
  const matchName = getTeamNameFromMatch(match, side);
  const meta = getTeamMeta(teamMetadata, teamId);

  const name = cleanText(
    matchName
    || meta.display_name
    || meta.team_display_name
    || meta.name
    || teamId
    || "Unknown Team"
  );

  const logo = getTeamLogo(teamMetadata, teamId);

  return {
    teamId,
    name,
    shortName: cleanText(meta.short_name || meta.abbreviation || getShortTeamName(name)),
    abbreviation: cleanText(meta.abbreviation || ""),
    logo,
    primary: getTeamThemeColor(teamMetadata, teamId, "primary", fallbackColor),
    secondary: getTeamThemeColor(teamMetadata, teamId, "secondary", "#f4f4f4"),
    accent: getTeamAccentColor(teamMetadata, teamId, fallbackColor),
    record: formatRecord(data.standings, teamId),
    scorer: makeTopGoalscorer(data.rosters, data.leaders, teamId, divisionRankings)
  };
}

function renderBroadcastTopbar(match) {
  const division = getDivisionKey(match);
  const divisionLabel = getDivisionLabel(division);
  const week = getMatchWeek(match);

  return `
    <header class="broadcast-topbar">
      <div class="broadcast-brand">
        <img class="broadcast-brand-logo" src="${escapeAttr(SPL_LOGO)}" alt="SPL" onerror="this.remove();">
        <span class="broadcast-brand-fallback">SPL</span>
      </div>

      <div class="broadcast-title">Top Goalscorers</div>

      <div class="broadcast-meta">
        <span>${escapeHtml(formatSeasonLabel())}</span>
        <span>${escapeHtml(divisionLabel)}</span>
        ${week ? `<span>Week ${escapeHtml(week)}</span>` : ""}
      </div>
    </header>
  `;
}

function renderTeamLogo(logo, name) {
  return `
    <div class="team-logo-frame">
      ${logo ? `<img src="${escapeAttr(logo)}" alt="${escapeAttr(name)}">` : ""}
    </div>
  `;
}

function renderMatchupTeam(team, side) {
  const logo = renderTeamLogo(team.logo, team.name);

  if (side === "home") {
    return `
      <section class="matchup-team home">
        <div class="matchup-team-copy">
          <span class="team-side-label">Home</span>
          <strong>${escapeHtml(team.name)}</strong>
          <div class="team-record-line">( ${escapeHtml(team.record)} )</div>
        </div>

        ${logo}
      </section>
    `;
  }

  return `
    <section class="matchup-team away">
      ${logo}

      <div class="matchup-team-copy">
        <span class="team-side-label">Away</span>
        <strong>${escapeHtml(team.name)}</strong>
        <div class="team-record-line">( ${escapeHtml(team.record)} )</div>
      </div>
    </section>
  `;
}

function renderMatchupCenter(match) {
  const division = getDivisionKey(match);
  const shield = getDivisionShield(division);

  return `
    <section class="matchup-center">
      ${
        shield
          ? `<img class="matchup-division-watermark" src="${escapeAttr(shield)}" alt="">`
          : ""
      }

      <div class="matchup-vs">VS</div>
    </section>
  `;
}

function renderMatchupStrip(match, away, home) {
  return `
    <section class="matchup-strip">
      ${renderMatchupTeam(away, "away")}
      ${renderMatchupCenter(match)}
      ${renderMatchupTeam(home, "home")}
    </section>
  `;
}

function renderScorerStat(label, value, rankInfo, featured = false) {
  return `
    <div class="scorer-stat ${featured ? "featured" : ""}">
      <span class="scorer-stat-label">${escapeHtml(label)}</span>
      <strong class="scorer-stat-value">${escapeHtml(value)}</strong>
      <span class="scorer-stat-rank">(${escapeHtml(formatRank(rankInfo))})</span>
    </div>
  `;
}

function renderScorerImage(scorer) {
  const candidates = scorer.cardCandidates || [];
  const firstCard = candidates[0] || "";

  return `
    <div class="scorer-player-card ${firstCard ? "" : "missing-card"}">
      ${
        firstCard
          ? `
            <img
              src="${escapeAttr(firstCard)}"
              alt="${escapeAttr(scorer.player_display_name)}"
              data-card-index="0"
              data-card-candidates="${escapeAttr(candidates.join("|"))}"
              onerror="window.loadNextScorerCard(this);"
            >
          `
          : ""
      }

      <div class="scorer-card-fallback">
        ${escapeHtml(scorer.player_display_name)}
      </div>
    </div>
  `;
}

function renderScorerCard(team, side) {
  const scorer = team.scorer;
  const sideClass = side === "home" ? "home" : "away";

  if (!scorer) {
    return `
      <section class="scorer-board ${sideClass}">
        ${
          team.logo
            ? `<div class="scorer-watermark" style="background-image: url('${escapeAttr(team.logo)}');"></div>`
            : ""
        }

        <div class="scorer-empty">No scorer data</div>
      </section>
    `;
  }

  return `
    <section class="scorer-board ${sideClass}">
      ${
        team.logo
          ? `<div class="scorer-watermark" style="background-image: url('${escapeAttr(team.logo)}');"></div>`
          : ""
      }

      <div class="scorer-card-wrap">
        <div class="scorer-name-bar">
          <strong>${escapeHtml(scorer.player_display_name)}</strong>
        </div>

        <div class="scorer-content">
          ${renderScorerImage(scorer)}

          <div class="scorer-stat-grid">
            ${renderScorerStat("Goals", formatInteger(scorer.goals), scorer.ranks?.goals, true)}
            ${renderScorerStat("Points", formatInteger(scorer.points), scorer.ranks?.points, true)}
            ${renderScorerStat("Shots", formatInteger(scorer.shots), scorer.ranks?.shots)}
            ${renderScorerStat("Games Played", formatInteger(scorer.gamesPlayed), scorer.ranks?.gamesPlayed)}
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderScorerSection(away, home) {
  return `
    <section class="scorer-section">
      ${renderScorerCard(away, "away")}
      ${renderScorerCard(home, "home")}
    </section>
  `;
}

function renderBroadcastFooter(away, home) {
  return `
    <footer class="broadcast-footer">
      <div class="footer-away">${escapeHtml(away.name)}</div>
      <div class="footer-center">TOP GOALSCORERS</div>
      <div class="footer-home">${escapeHtml(home.name)}</div>
    </footer>
  `;
}

function renderTopGoalscorersSource(match, data) {
  const container = document.querySelector("#topGoalscorersSource");

  if (!container) return;

  if (!match) {
    container.innerHTML = `
      <div class="source-error">Match not found</div>
    `;
    return;
  }

  const away = makeTeamView(match, "away", data, DEFAULT_AWAY_COLOR);
  const home = makeTeamView(match, "home", data, DEFAULT_HOME_COLOR);

  container.style.setProperty("--away-primary", away.primary);
  container.style.setProperty("--away-secondary", away.secondary);
  container.style.setProperty("--away-accent", away.accent);
  container.style.setProperty("--home-primary", home.primary);
  container.style.setProperty("--home-secondary", home.secondary);
  container.style.setProperty("--home-accent", home.accent);

  container.innerHTML = `
    ${
      away.logo
        ? `<div class="source-background-logo away-bg" style="background-image: url('${escapeAttr(away.logo)}');"></div>`
        : ""
    }

    ${
      home.logo
        ? `<div class="source-background-logo home-bg" style="background-image: url('${escapeAttr(home.logo)}');"></div>`
        : ""
    }

    <div class="broadcast-frame">
      ${renderBroadcastTopbar(match)}
      ${renderMatchupStrip(match, away, home)}
      ${renderScorerSection(away, home)}
      ${renderBroadcastFooter(away, home)}
    </div>
  `;
}

async function loadTopGoalscorers() {
  const matchId = getMatchIdFromUrl();

  if (!matchId) {
    renderTopGoalscorersSource(null, {});
    return;
  }

  const [
    schedule,
    matches,
    standings,
    leaders,
    rosters,
    metadata
  ] = await Promise.all([
    fetchJsonOrFallback(DATA_PATHS.schedule, { matches: [] }),
    fetchJsonOrFallback(DATA_PATHS.matches, { matches: [] }),
    fetchJsonOrFallback(DATA_PATHS.standings, { standings: [] }),
    fetchJsonOrFallback(DATA_PATHS.leaders, { players: [] }),
    fetchJsonOrFallback(DATA_PATHS.rosters, { teams: [] }),
    fetchJsonOrFallback(DATA_PATHS.teamMetadata, {})
  ]);

  const data = {
    schedule,
    matches,
    standings,
    leaders,
    rosters,
    teamMetadata: getTeamMetadataMap(metadata)
  };

  const match = findMatch(schedule, matches, matchId);

  renderTopGoalscorersSource(match, data);
}

loadTopGoalscorers();