const SEASON_ID = "summer_2026";
const SEASON_TYPE = "regular_season";
const DATA_ROOT = "../..";

const SPL_LOGO = `${DATA_ROOT}/assets/images/spl-logo.png`;

const DATA_PATHS = {
  schedule: `${DATA_ROOT}/data/live_season/${SEASON_ID}/${SEASON_TYPE}/schedule.json`,
  matches: `${DATA_ROOT}/data/live_season/${SEASON_ID}/${SEASON_TYPE}/matches.json`,
  standings: `${DATA_ROOT}/data/live_season/${SEASON_ID}/${SEASON_TYPE}/standings.json`,
  leaders: `${DATA_ROOT}/data/live_season/${SEASON_ID}/${SEASON_TYPE}/leaders.json`,
  rosters: `${DATA_ROOT}/data/live_season/${SEASON_ID}/active_rosters.json`,
  teamMetadata: `${DATA_ROOT}/data/team_metadata.json`
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

const DEFAULT_AWAY_COLOR = "#40137e";
const DEFAULT_HOME_COLOR = "#b52228";

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

  const logo = cleanText(
    meta.logo
    || meta.logo_url
    || meta.logo_path
    || meta.image
    || meta.image_path
    || ""
  );

  if (!logo) return "";
  if (logo.startsWith("http") || logo.startsWith("/")) return logo;

  return `${DATA_ROOT}/${logo}`;
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

function makeAbbreviation(name, fallback) {
  const text = cleanText(fallback || "");
  if (text) return text.toUpperCase().slice(0, 5);

  const words = cleanText(name).split(/\s+/).filter(Boolean);
  if (!words.length) return "TEAM";
  if (words.length === 1) return words[0].toUpperCase().slice(0, 5);

  const initials = words.map(word => word[0]).join("").toUpperCase();
  return initials.slice(0, 5);
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

function numberFrom(row, keys) {
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

function makeRosterRows(rosterData, leaderData, teamId) {
  const rosterPlayers = getRosterPlayersForTeam(rosterData, teamId);

  return rosterPlayers
    .filter(player => {
      const role = normalizeKey(player.role);
      return role !== "gm" && role !== "general_manager";
    })
    .map((player, index) => {
      const stats = getStatsForPlayer(leaderData, teamId, player);
      const goals = numberFrom(stats, ["goals", "g"]);
      const assists = numberFrom(stats, ["assists", "a"]);
      const points = numberFrom(stats, ["points", "pts"]) || goals + assists;

      return {
        sortIndex: index,
        player_id: getPlayerId(player),
        player_display_name: getPlayerDisplayName(player),
        jersey_number: cleanText(player.jersey_number || player.jersey || player.number || "—"),
        role: normalizeKey(player.role),
        games_played: numberFrom(stats, ["games_played", "gamesPlayed", "gp"]),
        goals,
        points,
        saves: numberFrom(stats, ["saves", "sv"])
      };
    });
}

function getRosterGm(rosterData, teamId) {
  const gm = getRosterPlayersForTeam(rosterData, teamId).find(player => {
    const role = normalizeKey(player.role);
    return role === "gm" || role === "general_manager";
  });

  return gm ? getPlayerDisplayName(gm) : "";
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

  return `${wins}-${losses}-${otl}`;
}

function makeTeamView(match, side, data, fallbackColor) {
  const teamMetadata = data.teamMetadata;

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

  const abbreviation = makeAbbreviation(
    name,
    meta.scorebug_abbreviation
    || meta.abbreviation
    || meta.short_name
  );

  return {
    teamId,
    name,
    shortName: cleanText(meta.short_name || meta.abbreviation || getShortTeamName(name)),
    abbreviation,
    logo: getTeamLogo(teamMetadata, teamId),
    primary: getTeamThemeColor(teamMetadata, teamId, "primary", fallbackColor),
    secondary: getTeamThemeColor(teamMetadata, teamId, "secondary", "#f3f0e8"),
    accent: getTeamAccentColor(teamMetadata, teamId, fallbackColor),
    record: formatRecord(data.standings, teamId),
    gm: getRosterGm(data.rosters, teamId),
    rosterRows: makeRosterRows(data.rosters, data.leaders, teamId)
  };
}

function renderTeamLogo(team) {
  if (!team.logo) {
    return `<span class="scorebug-logo-fallback">${escapeHtml(team.abbreviation)}</span>`;
  }

  return `<img src="${escapeAttr(team.logo)}" alt="${escapeAttr(team.name)}" onerror="this.replaceWith(document.createTextNode('${escapeAttr(team.abbreviation)}'))">`;
}

function renderScorebugHeader(match, away, home) {
  const division = getDivisionLabel(getDivisionKey(match));
  const week = getMatchWeek(match);

  return `
    <section class="scorebug-main">
      <div class="scorebug-logo-cell">${renderTeamLogo(away)}</div>
      <div class="scorebug-team-cell away">${escapeHtml(away.abbreviation)}</div>
      <div class="scorebug-record-cell">${escapeHtml(away.record)}</div>

      <div class="scorebug-center-cell">
        <div class="scorebug-center-logo">
          <img src="${escapeAttr(SPL_LOGO)}" alt="SPL" onerror="this.remove();">
        </div>
        <div class="scorebug-center-copy">
          <div class="scorebug-title">Active<br>Rosters</div>
          <div class="scorebug-subtitle">${escapeHtml(division)}${week ? ` / W${escapeHtml(week)}` : ""}</div>
        </div>
      </div>

      <div class="scorebug-record-cell">${escapeHtml(home.record)}</div>
      <div class="scorebug-team-cell home">${escapeHtml(home.abbreviation)}</div>
      <div class="scorebug-logo-cell">${renderTeamLogo(home)}</div>
    </section>
  `;
}

function renderScorebugStrip(match, away, home) {
  const division = getDivisionLabel(getDivisionKey(match));
  const week = getMatchWeek(match);
  const middle = [formatSeasonLabel(), division, week ? `Week ${week}` : ""].filter(Boolean).join("  |  ");

  return `
    <section class="scorebug-strip">
      <div class="strip-team away">${escapeHtml(away.name)}</div>
      <div class="strip-center">${escapeHtml(middle)}</div>
      <div class="strip-team home">${escapeHtml(home.name)}</div>
    </section>
  `;
}

function renderRosterRow(player) {
  const captain = player.role === "captain"
    ? `<span class="roster-captain">C</span>`
    : "";

  return `
    <div class="roster-row">
      <div class="roster-number">${escapeHtml(player.jersey_number)}</div>
      <div class="roster-player-name"><span>${escapeHtml(player.player_display_name)}</span>${captain}</div>
      <div class="roster-stat">${escapeHtml(player.games_played)}</div>
      <div class="roster-stat">${escapeHtml(player.goals)}</div>
      <div class="roster-stat">${escapeHtml(player.points)}</div>
      <div class="roster-stat">${escapeHtml(player.saves)}</div>
    </div>
  `;
}

function renderRosterTable(rows) {
  return `
    <div class="roster-table">
      <div class="roster-table-head">
        <span>#</span>
        <span>Player</span>
        <span>GP</span>
        <span>G</span>
        <span>P</span>
        <span>SV</span>
      </div>
      <div class="roster-table-body">
        ${
          rows.length
            ? rows.slice(0, 9).map(renderRosterRow).join("")
            : `<div class="roster-empty">No roster</div>`
        }
      </div>
    </div>
  `;
}

function renderRosterPanel(team, side) {
  const logoStyle = team.logo
    ? `style="--team-logo: url('${escapeAttr(team.logo)}');"`
    : "";

  const gmText = team.gm ? `GM ${team.gm}` : "Active Lineup";

  if (side === "home") {
    return `
      <section class="roster-panel home ${team.logo ? "has-logo" : ""}" ${logoStyle}>
        <div class="roster-panel-head">
          <div class="roster-panel-tag">${escapeHtml(gmText)}</div>
          <div>
            <div class="roster-panel-kicker">Home Roster</div>
            <div class="roster-panel-title">${escapeHtml(team.name)}</div>
          </div>
        </div>
        ${renderRosterTable(team.rosterRows)}
      </section>
    `;
  }

  return `
    <section class="roster-panel away ${team.logo ? "has-logo" : ""}" ${logoStyle}>
      <div class="roster-panel-head">
        <div>
          <div class="roster-panel-kicker">Away Roster</div>
          <div class="roster-panel-title">${escapeHtml(team.name)}</div>
        </div>
        <div class="roster-panel-tag">${escapeHtml(gmText)}</div>
      </div>
      ${renderRosterTable(team.rosterRows)}
    </section>
  `;
}

function renderRosterDrawer(away, home) {
  return `
    <section class="roster-drawer">
      ${renderRosterPanel(away, "away")}
      ${renderRosterPanel(home, "home")}
    </section>
  `;
}

function renderFooter(away, home) {
  return `
    <footer class="scorebug-footer">
      <div class="footer-brand">SPL.GG</div>
      <div class="footer-text">ACTIVE ROSTERS&nbsp;&nbsp; | &nbsp;&nbsp;${escapeHtml(away.abbreviation)} vs ${escapeHtml(home.abbreviation)}</div>
      <div class="footer-clock">CASTER</div>
    </footer>
  `;
}

function renderRosterSource(match, data) {
  const container = document.querySelector("#darthRosterSource");

  if (!container) return;

  if (!match) {
    container.innerHTML = `<div class="bug-error">Match not found</div>`;
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
    <div class="scorebug-package">
      ${renderScorebugHeader(match, away, home)}
      ${renderScorebugStrip(match, away, home)}
      ${renderRosterDrawer(away, home)}
      ${renderFooter(away, home)}
    </div>
  `;
}

async function loadDarthRoster() {
  const matchId = getMatchIdFromUrl();

  if (!matchId) {
    renderRosterSource(null, {});
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

  renderRosterSource(match, data);
}

loadDarthRoster();
