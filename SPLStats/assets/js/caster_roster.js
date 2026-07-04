const SEASON_ID = "summer_2026";
const SEASON_TYPE = "regular_season";

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
const SPL_LOGO = "assets/images/spl_logo.png";

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

function getRosterStaffForTeam(rosterData, teamId, role) {
  const targetRole = normalizeKey(role);

  return getRosterPlayersForTeam(rosterData, teamId).filter(player => {
    return normalizeKey(player.role) === targetRole;
  });
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

function getPlayerJerseyNumber(player) {
  return cleanText(
    player.jersey_number
    || player.jerseyNumber
    || player.number
    || player.sweater_number
    || player.sweaterNumber
    || ""
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

function makeRosterRows(rosterData, leaderData, teamId) {
  const rosterPlayers = getRosterPlayersForTeam(rosterData, teamId).filter(player => {
    const role = normalizeKey(player.role);

    return role !== "gm" && role !== "general_manager";
  });

  return rosterPlayers.map(player => {
    const stats = getStatsForPlayer(leaderData, teamId, player);
    const role = normalizeKey(player.role);

    return {
      player_id: getPlayerId(player),
      player_display_name: getPlayerDisplayName(player),
      slap_id: cleanText(player.slap_id || player.slapshot_id || player.slapId),
      jerseyNumber: getPlayerJerseyNumber(player),
      isCaptain: role === "captain",
      games_played: Number(stats.games_played || stats.gp || 0),
      goals: Number(stats.goals || 0),
      points: Number(stats.points || 0),
      saves: Number(stats.saves || 0)
    };
  }).sort((a, b) => {
    return b.games_played - a.games_played
      || b.points - a.points
      || b.goals - a.goals
      || a.player_display_name.localeCompare(b.player_display_name);
  });
}

function getGeneralManagerLine(rosterData, teamId) {
  const generalManagers = [
    ...getRosterStaffForTeam(rosterData, teamId, "gm"),
    ...getRosterStaffForTeam(rosterData, teamId, "general_manager")
  ];

  const names = generalManagers
    .map(getPlayerDisplayName)
    .filter(Boolean);

  if (!names.length) return "";

  const label = names.length === 1 ? "General Manager" : "General Managers";

  return `${label} - ${names.join(", ")}`;
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
    return normalizeKey(row.team_id || row.team || row.team_name || row.display_name) === target;
  }) || {};
}

function formatRecord(standingsData, teamId) {
  const row = getTeamStanding(standingsData, teamId);

  const wins = Number(row.wins || row.w || 0);
  const losses = Number(row.losses || row.l || 0);
  const otl = Number(row.overtime_losses || row.otl || row.ot_losses || 0);

  return `${wins} - ${losses} - ${otl}`;
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

function getRosterTeam(rosterData, teamId) {
  const target = normalizeKey(teamId);

  return getRosterTeams(rosterData).find(row => {
    return normalizeKey(row.team_id || row.id || row.team_name || row.name) === target;
  }) || {};
}

function getTeamGeneralManager(teamMetadata, rosterData, teamId) {
  const meta = getTeamMeta(teamMetadata, teamId);
  const rosterTeam = getRosterTeam(rosterData, teamId);

  const rawValue = cleanText(
    rosterTeam.general_manager
    || rosterTeam.generalManager
    || rosterTeam.gm
    || rosterTeam.manager
    || meta.general_manager
    || meta.generalManager
    || meta.gm
    || meta.manager
    || ""
  );

  if (rawValue) return rawValue;

  const rawList =
    rosterTeam.general_managers
    || rosterTeam.generalManagers
    || rosterTeam.gms
    || meta.general_managers
    || meta.generalManagers
    || meta.gms
    || [];

  if (Array.isArray(rawList)) {
    return rawList
      .map(name => cleanText(name?.name || name?.display_name || name))
      .filter(Boolean)
      .join(", ");
  }

  return "";
}

function getTeamCaptainIds(teamMetadata, rosterData, teamId) {
  const meta = getTeamMeta(teamMetadata, teamId);
  const rosterTeam = getRosterTeam(rosterData, teamId);

  const rawCaptains =
    rosterTeam.captains
    || rosterTeam.captain_ids
    || rosterTeam.captainIds
    || meta.captains
    || meta.captain_ids
    || meta.captainIds
    || [];

  const captainIds = new Set();

  if (Array.isArray(rawCaptains)) {
    rawCaptains.forEach(captain => {
      const value = cleanText(
        captain?.player_id
        || captain?.id
        || captain?.name
        || captain?.display_name
        || captain
      );

      if (value) {
        captainIds.add(normalizeKey(value));
      }
    });
  } else {
    const value = cleanText(rawCaptains);

    if (value) {
      captainIds.add(normalizeKey(value));
    }
  }

  const singleCaptain = cleanText(
    rosterTeam.captain
    || rosterTeam.captain_id
    || rosterTeam.captainId
    || meta.captain
    || meta.captain_id
    || meta.captainId
    || ""
  );

  if (singleCaptain) {
    captainIds.add(normalizeKey(singleCaptain));
  }

  return captainIds;
}

function isPlayerCaptain(player, captainIds) {
  if (
    player.is_captain
    || player.isCaptain
    || player.captain
    || player.role === "captain"
    || player.role === "Captain"
  ) {
    return true;
  }

  const possibleIds = [
    player.player_id,
    player.id,
    player.name,
    player.display_name,
    player.player_display_name,
    player.player_name,
    player.steam_name,
    player.slap_id,
    player.slapshot_id,
    player.slapId
  ];

  return possibleIds.some(value => captainIds.has(normalizeKey(value)));
}

function makeTeamView(match, side, data, fallbackColor) {
  const teamMetadata = data.teamMetadata;

  const teamId = getTeamIdFromMatch(match, side);
  const matchName = getTeamNameFromMatch(match, side);
  const meta = getTeamMeta(teamMetadata, teamId);
  const captainIds = getTeamCaptainIds(teamMetadata, data.rosters, teamId);

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
    generalManager: getTeamGeneralManager(teamMetadata, data.rosters, teamId),
    record: formatRecord(data.standings, teamId),
    generalManagerLine: getGeneralManagerLine(data.rosters, teamId),
    rosterRows: makeRosterRows(data.rosters, data.leaders, teamId)
  };
}

function renderBroadcastTopbar(match) {
  const division = getDivisionKey(match);
  const divisionLabel = getDivisionLabel(division);
  const week = getMatchWeek(match);

  return `
    <header class="broadcast-topbar">
      <div class="broadcast-brand">
        <img class="broadcast-brand-logo" src="${escapeAttr(SPL_LOGO)}" alt="SPL">
      </div>

      <div class="broadcast-title">Active Rosters</div>

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
  const badge = getDivisionShield(division);

  return `
    <section class="matchup-center">
      ${
        badge
          ? `<img class="matchup-division-watermark" src="${escapeAttr(badge)}" alt="">`
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

function renderRosterRow(player) {
  return `
    <div class="roster-row">
      <div class="roster-jersey-number">${escapeHtml(player.jerseyNumber)}</div>

      <div class="roster-player-name">
        <span class="roster-player-text">${escapeHtml(player.player_display_name)}</span>
        ${player.isCaptain ? `<span class="captain-marker">C</span>` : ""}
      </div>

      <div class="roster-stat">${escapeHtml(player.games_played)}</div>
      <div class="roster-stat">${escapeHtml(player.goals)}</div>
      <div class="roster-stat">${escapeHtml(player.points)}</div>
      <div class="roster-stat">${escapeHtml(player.saves)}</div>
    </div>
  `;
}

function renderRosterBoard(team, side) {
  const rows = team.rosterRows.slice(0, 8);
  const sideClass = side === "home" ? "home" : "away";

  return `
    <section class="roster-board ${sideClass}">
      ${
        team.logo
          ? `<div class="roster-watermark" style="background-image: url('${escapeAttr(team.logo)}');"></div>`
          : ""
      }

      ${
        team.generalManagerLine
          ? `<div class="roster-staff-line">${escapeHtml(team.generalManagerLine)}</div>`
          : `<div class="roster-staff-line roster-staff-spacer" aria-hidden="true"></div>`
      }

      ${renderRosterTable(rows)}
    </section>
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

      ${
        rows.length
          ? rows.map(renderRosterRow).join("")
          : `<div class="caster-error">No roster</div>`
      }
    </div>
  `;
}

function renderRosterSection(away, home) {
  return `
    <section class="roster-section">
      ${renderRosterBoard(away, "away")}
      ${renderRosterBoard(home, "home")}
    </section>
  `;
}

function renderBroadcastFooter(away, home) {
  return `
    <footer class="broadcast-footer">
      <div class="footer-away">${escapeHtml(away.name)}</div>
      <div class="footer-center">ACTIVE ROSTERS</div>
      <div class="footer-home">${escapeHtml(home.name)}</div>
    </footer>
  `;
}

function renderRosterSource(match, data) {
  const container = document.querySelector("#casterRosterSource");

  if (!container) return;

  if (!match) {
    container.innerHTML = `
      <div class="caster-error">Match not found</div>
    `;
    return;
  }

  const away = makeTeamView(match, "away", data, DEFAULT_AWAY_COLOR);
  const home = makeTeamView(match, "home", data, DEFAULT_HOME_COLOR);

  container.style.setProperty("--away-primary", away.primary);
  container.style.setProperty("--away-secondary", away.secondary);
  container.style.setProperty("--home-primary", home.primary);
  container.style.setProperty("--home-secondary", home.secondary);

  container.innerHTML = `
    ${
      away.logo
        ? `<div class="caster-background-logo away-bg" style="background-image: url('${escapeAttr(away.logo)}');"></div>`
        : ""
    }

    ${
      home.logo
        ? `<div class="caster-background-logo home-bg" style="background-image: url('${escapeAttr(home.logo)}');"></div>`
        : ""
    }

    <div class="broadcast-frame">
      ${renderBroadcastTopbar(match)}
      ${renderMatchupStrip(match, away, home)}
      ${renderRosterSection(away, home)}
      ${renderBroadcastFooter(away, home)}
    </div>
  `;
}

async function loadCasterRoster() {
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

loadCasterRoster();