const DEFAULT_SEASON_ID = "summer_2026";

function cleanText(value) {
  return String(value || "").trim();
}

function getMatchIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return cleanText(params.get("id") || params.get("match") || "");
}

function getMatchContextFromId(matchId) {
  const id = cleanText(matchId);

  if (id.includes("_regular_season_")) {
    return {
      seasonId: id.split("_regular_season_")[0],
      seasonType: "regular_season"
    };
  }

  if (id.includes("_preseason_")) {
    return {
      seasonId: id.split("_preseason_")[0],
      seasonType: "preseason"
    };
  }

  return {
    seasonId: DEFAULT_SEASON_ID,
    seasonType: "preseason"
  };
}

const MATCH_ID = getMatchIdFromUrl();
const MATCH_CONTEXT = getMatchContextFromId(MATCH_ID);

const SEASON_ID = MATCH_CONTEXT.seasonId;
const SEASON_TYPE = MATCH_CONTEXT.seasonType;

const DATA_PATHS = {
  schedule: `data/live_season/${SEASON_ID}/${SEASON_TYPE}/schedule.json`,
  matches: `data/live_season/${SEASON_ID}/${SEASON_TYPE}/matches.json`,
  rosters: `data/live_season/${SEASON_ID}/active_rosters.json`,
  rosterSnapshots: `data/live_season/${SEASON_ID}/${SEASON_TYPE}/roster_snapshots.json`,
  matchDetailsBase: `data/live_season/${SEASON_ID}/${SEASON_TYPE}/match_details`,
  shotMapsBase: `data/live_season/${SEASON_ID}/${SEASON_TYPE}/shot_maps`,
  teamMetadata: "data/team_metadata.json"
};

let matches = [];
let rostersByTeamId = {};
let metadataByTeamId = {};
let rosterSnapshots = {};
let currentMatch = null;
let currentMatchDetail = null;
let currentShotMap = null;

let activeShotTeam = "all";
let activeShotResult = "all";
let activeShotPeriod = "all";

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

  return [];
}

function mergeScheduledAndCompletedMatches(scheduleData, matchesData) {
  const byId = new Map();

  getMatchArray(scheduleData).forEach(match => {
    const id = match.match_id || match.id || match.schedule_id || match.source_id;

    if (!id) return;

    byId.set(id, match);
  });

  getMatchArray(matchesData).forEach(match => {
    const id = match.match_id || match.id || match.schedule_id || match.source_id;

    if (!id) return;

    byId.set(id, {
      ...(byId.get(id) || {}),
      ...match
    });
  });

  return [...byId.values()];
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

function formatSeasonType(value) {
  const text = cleanText(value).toLowerCase();

  if (text === "regular_season") return "Regular Season";
  if (text === "preseason") return "Preseason";
  if (text === "postseason") return "Postseason";

  return cleanText(value) || "Season";
}

function formatRegion(region) {
  const text = cleanText(region).toLowerCase();

  if (text === "east") return "East";
  if (text === "central") return "Central";
  if (text === "west") return "West";

  return "Unknown";
}

function formatStatus(status) {
  if (status === "final") return "Final";
  if (status === "scheduled") return "Scheduled";
  if (status === "uploaded_score_unknown") return "Needs Review";
  if (status === "uploaded_missing_valid_report") return "Needs Review";

  return cleanText(status) || "Unknown";
}

function getSnapshotPlayerDisplayName(player) {
  return (
    player.player_display_name
    || player.player_name
    || player.steam_name
    || player.name
    || player.slap_id
    || "Unknown Player"
  );
}

function getSnapshotPlayerUrlId(player) {
  return (
    player.player_id
    || player.player_name
    || player.player_display_name
    || player.steam_name
    || player.name
    || player.slap_id
    || ""
  );
}

function renderSnapshotPlayerLink(player) {
  const name = getSnapshotPlayerDisplayName(player);
  const urlId = getSnapshotPlayerUrlId(player);

  if (!urlId) {
    return `<span class="snapshot-player-name">${escapeHtml(name)}</span>`;
  }

  return `
    <a
      class="snapshot-player-link"
      href="player.html?id=${encodeURIComponent(urlId)}"
    >
      ${escapeHtml(name)}
    </a>
  `;
}

function getTeamMetadata(teamId) {
  return metadataByTeamId[teamId] || null;
}

function getMatchRoster(match, side) {
  const snapshot = rosterSnapshots[match.match_id];

  if (snapshot) {
    return side === "home"
      ? snapshot.home_roster
      : snapshot.away_roster;
  }

  const teamId = side === "home"
    ? match.home_team_id
    : match.away_team_id;

  return getRoster(teamId);
}

function getRosterSourceLabel(match) {
  if (rosterSnapshots[match.match_id]) {
    return "Roster Snapshot";
  }

  return "Current Active Roster";
}

function getRoster(teamId) {
  return rostersByTeamId[teamId] || {
    players: [],
    slap_ids: []
  };
}

function getTheme(teamId) {
  const meta = getTeamMetadata(teamId);
  return meta?.theme || {};
}

function getLogo(teamId) {
  const meta = getTeamMetadata(teamId);
  return meta?.logo || "";
}

function getThemeValue(teamId, key, fallback) {
  const theme = getTheme(teamId);
  return theme[key] || fallback;
}

function pageStyle(match) {
  const homePrimary = getThemeValue(match.home_team_id, "primary", "#7bdff2");
  const homeCard = getThemeValue(match.home_team_id, "card", "#111111");
  const awayPrimary = getThemeValue(match.away_team_id, "primary", "#ffd166");
  const awayCard = getThemeValue(match.away_team_id, "card", "#111111");

  return `
    --home-primary: ${homePrimary};
    --home-card: ${homeCard};
    --away-primary: ${awayPrimary};
    --away-card: ${awayCard};
  `;
}

function isFinal(match) {
  return match.status === "final";
}

function matchNeedsReview(match) {
  return (
    match.status !== "scheduled"
    && (
      match.status !== "final"
      || (match.warnings || []).length > 0
    )
  );
}

function getScoreDisplay(match) {
  if (!isFinal(match)) {
    return "VS";
  }

  return `${match.home_score} - ${match.away_score}`;
}

function getWinnerSide(match) {
  if (!isFinal(match)) return null;

  if (match.winner_team_id === match.home_team_id) return "home";
  if (match.winner_team_id === match.away_team_id) return "away";

  return null;
}

function getFinalType(match) {
  if (!isFinal(match)) return "";

  return match.overtime ? "Overtime" : "Regulation";
}

function getRoleLabel(role) {
  const value = cleanText(role).toLowerCase();

  if (value === "gm") return "GM";
  if (value === "captain") return "Captain";

  return "Player";
}

function formatStatValue(value, suffix = "") {
  const number = Number(value || 0);

  if (Number.isInteger(number)) {
    return `${number}${suffix}`;
  }

  return `${number.toFixed(1)}${suffix}`;
}

function getDetailTeamStats(side) {
  return currentMatchDetail?.team_stats?.[side] || {};
}

function getStatShare(homeValue, awayValue) {
  const home = Number(homeValue || 0);
  const away = Number(awayValue || 0);
  const total = home + away;

  if (total <= 0) {
    return {
      homePercent: 50,
      awayPercent: 50
    };
  }

  return {
    homePercent: Math.round((home / total) * 1000) / 10,
    awayPercent: Math.round((away / total) * 1000) / 10
  };
}

function renderTeamStatBar(label, key, options = {}) {
  const homeStats = getDetailTeamStats("home");
  const awayStats = getDetailTeamStats("away");

  const suffix = options.suffix || "";
  const homeValue = Number(homeStats[key] || 0);
  const awayValue = Number(awayStats[key] || 0);

  const share = getStatShare(homeValue, awayValue);

  return `
    <div class="hero-stat-row">
      <div class="hero-stat-values">
        <span class="home-stat-value">
          ${formatStatValue(homeValue, suffix)}
        </span>

        <strong>${label}</strong>

        <span class="away-stat-value">
          ${formatStatValue(awayValue, suffix)}
        </span>
      </div>

      <div class="hero-stat-bar">
        <div
          class="hero-stat-bar-home"
          style="width: ${share.homePercent}%"
        ></div>

        <div
          class="hero-stat-bar-away"
          style="width: ${share.awayPercent}%"
        ></div>
      </div>
    </div>
  `;
}

function renderHeroTeamStats(match) {
  if (!isFinal(match) || !currentMatchDetail) {
    return "";
  }

  return `
    <div class="hero-team-stats">
      ${renderTeamStatBar("Shots", "shots")}
      ${renderTeamStatBar("Saves", "saves")}
      ${renderTeamStatBar("Blocks", "blocks")}
      ${renderTeamStatBar("Faceoffs Won", "faceoffs_won")}
      ${renderTeamStatBar("Takeaways", "takeaways")}
      ${renderTeamStatBar("Possession", "possession_percent", { suffix: "%" })}
    </div>
  `;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderTeamLogo(teamId, teamName, side) {
  const logo = getLogo(teamId);

  if (!logo) {
    return `
      <div class="match-logo-placeholder ${side}">
        ${escapeHtml(teamName.slice(0, 1))}
      </div>
    `;
  }

  return `
    <img
      class="match-team-logo ${side}"
      src="${escapeHtml(logo)}"
      alt="${escapeHtml(teamName)} logo"
    >
  `;
}

function renderHero(match) {
  const winnerSide = getWinnerSide(match);
  const needsReview = matchNeedsReview(match);

  return `
    <section
      class="match-hero"
      style="${pageStyle(match)}"
    >
      <div class="match-hero-bg"></div>

      <div class="match-team-side home ${winnerSide === "home" ? "winner" : ""}">
        ${renderTeamLogo(match.home_team_id, match.home_team, "home")}

        <a
          class="match-team-name"
          href="team.html?id=${encodeURIComponent(match.home_team_id)}"
        >
          ${escapeHtml(match.home_team)}
        </a>

        ${
          winnerSide === "home"
            ? `<span class="winner-ribbon">Winner</span>`
            : ""
        }
      </div>

      <div class="match-center">
        <div class="match-score-display">
          ${getScoreDisplay(match)}
        </div>

        <div class="match-status-line">
          <span class="status-pill status-${match.status}">
            ${formatStatus(match.status)}
          </span>

          <span>${formatRegion(match.region || match.home_region || match.away_region)} ${formatSeasonType(match.season_type || SEASON_TYPE)}</span>
          <span>Match ${escapeHtml(match.source_id || match.schedule_id || match.match_id)}</span>

          ${
            isFinal(match)
              ? `<span>${getFinalType(match)}</span>`
              : ""
          }
        </div>

        ${
        needsReview
            ? `<div class="match-review-warning">Needs Review</div>`
            : ""
        }

        ${renderHeroTeamStats(match)}
    </div>

      <div class="match-team-side away ${winnerSide === "away" ? "winner" : ""}">
        ${renderTeamLogo(match.away_team_id, match.away_team, "away")}

        <a
          class="match-team-name"
          href="team.html?id=${encodeURIComponent(match.away_team_id)}"
        >
          ${escapeHtml(match.away_team)}
        </a>

        ${
          winnerSide === "away"
            ? `<span class="winner-ribbon">Winner</span>`
            : ""
        }
      </div>
    </section>
  `;
}

function renderSummaryCard(label, value) {
  return `
    <article class="match-summary-card">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </article>
  `;
}

function renderSummary(match) {
  const summary = [];

  summary.push(renderSummaryCard("Region", formatRegion(match.region || match.home_region || match.away_region)));
  summary.push(renderSummaryCard("Phase", formatSeasonType(match.season_type || SEASON_TYPE)));
  summary.push(renderSummaryCard("Division", match.division || "Unknown"));
  summary.push(renderSummaryCard("Week", match.week || "—"));
  summary.push(renderSummaryCard("Match ID", match.source_id || match.schedule_id || match.match_id));
  summary.push(renderSummaryCard("Status", formatStatus(match.status)));

  if (match.match_scope) {
    summary.push(renderSummaryCard("Scope", match.match_scope));
  }

  if (isFinal(match)) {
    const winner =
      match.winner_team_id === match.home_team_id
        ? match.home_team
        : match.away_team;

    summary.push(renderSummaryCard("Winner", winner));
    summary.push(renderSummaryCard("Final Type", getFinalType(match)));
    summary.push(renderSummaryCard("Side Mapping", match.side_mapping || "Unknown"));
    summary.push(renderSummaryCard("Mapping Confidence", match.side_mapping_confidence ?? 0));
  } else {
    summary.push(renderSummaryCard("Log Status", match.log_folder ? "Uploaded" : "Not Uploaded"));
  }

  return `
    <section class="match-summary-grid">
      ${summary.join("")}
    </section>
  `;
}

function renderRosterPlayer(player) {
  return `
    <div class="roster-player-row">
      <span class="roster-role">${getRoleLabel(player.role)}</span>
      <span class="roster-name">
        ${renderSnapshotPlayerLink(player)}
      </span>
    </div>
  `;
}

function renderRosterCard(match, side) {
  const teamId = side === "home" ? match.home_team_id : match.away_team_id;
  const teamName = side === "home" ? match.home_team : match.away_team;
  const roster = getMatchRoster(match, side);
  const players = roster.players || [];

  return `
    <section
      class="roster-card ${side}"
      style="
        --team-primary: ${getThemeValue(teamId, "primary", "#7bdff2")};
        --team-card: ${getThemeValue(teamId, "card", "#111111")};
        --team-accent: ${getThemeValue(teamId, "accent", "#ffffff")};
      "
    >
      <div class="roster-card-head">
        ${renderTeamLogo(teamId, teamName, side)}
        <div>
          <h2>${escapeHtml(teamName)}</h2>
          <p>
            ${getRosterSourceLabel(match)} · ${players.length} players · ${(roster.slap_ids || []).length} Slap IDs
          </p>
        </div>
      </div>

      <div class="roster-list">
        ${
          players.length
            ? players.map(renderRosterPlayer).join("")
            : `<div class="empty-panel">No roster listed.</div>`
        }
      </div>
    </section>
  `;
}

function renderPreviewMode(match) {
  return `
    <section class="match-section-title">
      <h2>Match Preview</h2>
      <p>Roster and schedule information before the match is finalized.</p>
    </section>

    <section class="match-rosters-grid">
      ${renderRosterCard(match, "home")}
      ${renderRosterCard(match, "away")}
    </section>

    ${renderProcessingPanel(match)}
  `;
}

const SHOT_RESULT_LABELS = {
  goal: "Goal",
  shot_on_goal: "Shot on Goal",
  shot_blocked: "Shot Blocked"
};

function getShotResultLabel(result) {
  return SHOT_RESULT_LABELS[result] || result || "Unknown";
}

function getShotTeamColor(match, shot) {
  const teamId = shot.team_side === "home"
    ? match.home_team_id
    : match.away_team_id;

  return getThemeValue(teamId, "accent", "#ffffff");
}

function shotPassesFilters(shot) {
  if (activeShotTeam !== "all" && shot.team_side !== activeShotTeam) {
    return false;
  }

  if (activeShotResult !== "all" && shot.result !== activeShotResult) {
    return false;
  }

  if (activeShotPeriod !== "all" && shot.period !== activeShotPeriod) {
    return false;
  }

  return true;
}

function getFilteredShots() {
  return (currentShotMap?.shots || []).filter(shotPassesFilters);
}

function renderShotMapSection(match) {
  if (!currentShotMap || !(currentShotMap.shots || []).length) {
    return `
      <section class="match-section-title">
        <h2>Shot Map</h2>
        <p>No shot map has been added for this match yet.</p>
      </section>
    `;
  }

  const shots = getFilteredShots();

  return `
    <section class="match-section-title">
      <h2>Shot Map</h2>
      <p>Manually tracked shot locations from the match.</p>
    </section>

    <section
      class="shot-map-card"
      style="
        --home-primary: ${getThemeValue(match.home_team_id, "primary", "#7bdff2")};
        --home-accent: ${getThemeValue(match.home_team_id, "accent", "#ffffff")};
        --away-primary: ${getThemeValue(match.away_team_id, "primary", "#ffd166")};
        --away-accent: ${getThemeValue(match.away_team_id, "accent", "#ffffff")};
      "
      >
      <div class="shot-map-controls">
        <div>
          <label>Team</label>
          <select id="shotTeamFilter">
            <option value="all">Both Teams</option>
            <option value="home">${escapeHtml(match.home_team)}</option>
            <option value="away">${escapeHtml(match.away_team)}</option>
          </select>
        </div>

        <div>
          <label>Result</label>
          <select id="shotResultFilter">
            <option value="all">All Results</option>
            <option value="goal">Goals</option>
            <option value="shot_on_goal">Shots on Goal</option>
            <option value="shot_blocked">Blocked Shots</option>
          </select>
        </div>

        <div>
          <label>Period</label>
          <select id="shotPeriodFilter">
            <option value="all">All Periods</option>
            <option value="1">1st</option>
            <option value="2">2nd</option>
            <option value="3">3rd</option>
            <option value="OT">OT</option>
          </select>
        </div>
      </div>

      <div class="shot-map-rink-wrap">
      <div class="shot-map-rink-layout">

        ${renderDefendingTeamBar(match, "left")}

        <div class="shot-map-rink">
            <img
              class="shot-map-rink-image"
              src="assets/images/rink/slapshot-rink.png"
              alt=""
              aria-hidden="true"
            >

            <div class="shot-map-pellet-layer">
              ${shots.map(shot => renderShotPellet(match, shot)).join("")}
            </div>
          </div>

          ${renderDefendingTeamBar(match, "right")}
        </div>
      </div>

      <div class="shot-map-legend">
        <span><i class="legend-dot goal"></i> Goal</span>
        <span><i class="legend-dot shot_on_goal"></i> Shot on Goal</span>
        <span><i class="legend-dot shot_blocked"></i> Shot Blocked</span>
      </div>

      <div class="shot-map-summary">
        Showing ${shots.length} of ${(currentShotMap.shots || []).length} tracked shots.
      </div>
    </section>
  `;
}

function getDefendingTeamForSide(match, rinkSide) {
  const orientation = currentShotMap?.rink_orientation || {
    home: "left_to_right",
    away: "right_to_left"
  };

  if (rinkSide === "left") {
    return orientation.home === "left_to_right"
      ? {
          team_id: match.home_team_id,
          team: match.home_team,
          side: "home"
        }
      : {
          team_id: match.away_team_id,
          team: match.away_team,
          side: "away"
        };
  }

  return orientation.home === "left_to_right"
    ? {
        team_id: match.away_team_id,
        team: match.away_team,
        side: "away"
      }
    : {
        team_id: match.home_team_id,
        team: match.home_team,
        side: "home"
      };
}

function renderDefendingTeamBar(match, rinkSide) {
  const defending = getDefendingTeamForSide(match, rinkSide);

  return `
    <div
      class="shot-map-defender-bar ${rinkSide}"
      style="
        --defender-primary: ${getThemeValue(defending.team_id, "primary", "#7bdff2")};
        --defender-accent: ${getThemeValue(defending.team_id, "accent", "#ffffff")};
      "
    >
      <span>${escapeHtml(defending.team)} Defend</span>
    </div>
  `;
}

function renderAttackLabels(match) {
  const orientation = currentShotMap?.rink_orientation || {
    home: "left_to_right",
    away: "right_to_left"
  };

  if (orientation.home === "left_to_right") {
    return `
      <span style="color: var(--home-primary)">
        ${escapeHtml(match.home_team)} attacks →
      </span>

      <span style="color: var(--away-primary)">
        ← ${escapeHtml(match.away_team)} attacks
      </span>
    `;
  }

  return `
    <span style="color: var(--away-primary)">
      ${escapeHtml(match.away_team)} attacks →
    </span>

    <span style="color: var(--home-primary)">
      ← ${escapeHtml(match.home_team)} attacks
    </span>
  `;
}

function renderShotPellet(match, shot) {
  const resultLabel = getShotResultLabel(shot.result);
  const periodLabel = shot.period
    ? formatShotPeriod(shot.period)
    : "Unknown period";

  const timeLabel = shot.time_remaining
    ? shot.time_remaining
    : "Time unknown";

  return `
    <button
      class="shot-map-pellet ${shot.result}"
      style="
        left: ${Number(shot.x || 0)}%;
        top: ${Number(shot.y || 0)}%;
        --shot-team-color: ${getShotTeamColor(match, shot)};
      "
      title="${escapeHtml(shot.player || "Unknown")} — ${resultLabel}"
      type="button"
      aria-label="${escapeHtml(shot.player || "Unknown")} — ${resultLabel}"
    >
      <span class="shot-map-tooltip">
        <strong>${escapeHtml(shot.player || "Unknown Player")}</strong>
        <em>${escapeHtml(resultLabel)}</em>
        <span>${escapeHtml(shot.team || "Unknown Team")}</span>
        <span>${escapeHtml(periodLabel)} · ${escapeHtml(timeLabel)}</span>
      </span>
    </button>
  `;
}

function renderShotListItem(match, shot) {
  const teamColor = getShotTeamColor(match, shot);

  return `
    <div
      class="shot-map-list-item"
      style="--shot-team-color: ${teamColor};"
    >
      <div>
        <strong>${escapeHtml(shot.player || "Unknown Player")}</strong>
        <span>
          ${escapeHtml(shot.team || "")}
          ${
            shot.period
              ? ` · ${escapeHtml(formatShotPeriod(shot.period))}`
              : ""
          }
          ${
            shot.time_remaining
              ? ` · ${escapeHtml(shot.time_remaining)}`
              : ""
          }
        </span>
      </div>

      <em class="${shot.result}">
        ${getShotResultLabel(shot.result)}
      </em>
    </div>
  `;
}

function formatShotPeriod(period) {
  if (period === "1") return "1st";
  if (period === "2") return "2nd";
  if (period === "3") return "3rd";
  if (period === "OT") return "OT";
  return period;
}

function attachShotMapFilters() {
  const teamFilter = document.querySelector("#shotTeamFilter");
  const resultFilter = document.querySelector("#shotResultFilter");
  const periodFilter = document.querySelector("#shotPeriodFilter");

  if (!teamFilter || !resultFilter || !periodFilter) {
    return;
  }

  teamFilter.value = activeShotTeam;
  resultFilter.value = activeShotResult;
  periodFilter.value = activeShotPeriod;

  teamFilter.addEventListener("change", event => {
    activeShotTeam = event.target.value;

    if (currentMatch) {
      renderMatchPage(currentMatch);
    }
  });

  resultFilter.addEventListener("change", event => {
    activeShotResult = event.target.value;

    if (currentMatch) {
      renderMatchPage(currentMatch);
    }
  });

  periodFilter.addEventListener("change", event => {
    activeShotPeriod = event.target.value;

    if (currentMatch) {
      renderMatchPage(currentMatch);
    }
  });
}

function renderResultMode(match) {
  return `
    <section class="match-section-title">
      <h2>Match Result</h2>
      <p>Final score, roster snapshot, and player stat breakdown.</p>
    </section>

    <section class="match-rosters-grid">
      ${renderRosterCard(match, "home")}
      ${renderRosterCard(match, "away")}
    </section>

    ${renderShotMapSection(match)}
    
    ${renderGoalieCards(match)}

    ${renderPlayerStatsSection(match)}

    ${renderProcessingPanel(match)}
  `;
}

function getPlayersForSide(side) {
  return (currentMatchDetail?.players || [])
    .filter(player => player.team_side === side)
    .sort((a, b) => {
      return (
        Number(b.points || 0) - Number(a.points || 0)
        || Number(b.goals || 0) - Number(a.goals || 0)
        || Number(b.score || 0) - Number(a.score || 0)
        || cleanText(a.username).localeCompare(cleanText(b.username))
      );
    });
}

function renderPlayerStatsSection(match) {
  if (!currentMatchDetail) {
    return `
      <section class="player-card">
        <h2>Player Stats</h2>
        <p>No match detail file was found for this result yet.</p>
      </section>
    `;
  }

  return `
    <section class="match-section-title">
      <h2>Player Stats</h2>
      <p>Final-period cumulative stats from the uploaded game report.</p>
    </section>

    <section class="player-stats-grid">
      ${renderPlayerStatsCard(match, "home")}
      ${renderPlayerStatsCard(match, "away")}
    </section>
  `;
}

function renderPlayerStatsCard(match, side) {
  const teamId = side === "home" ? match.home_team_id : match.away_team_id;
  const teamName = side === "home" ? match.home_team : match.away_team;
  const players = getPlayersForSide(side);

  return `
    <section
      class="player-stats-card ${side}"
      style="
        --team-primary: ${getThemeValue(teamId, "primary", "#7bdff2")};
        --team-accent: ${getThemeValue(teamId, "accent", "#ffffff")};
        --team-card: ${getThemeValue(teamId, "card", "#111111")};
      "
    >
      <div class="player-stats-card-head">
        ${renderTeamLogo(teamId, teamName, side)}

        <div>
          <h2>${escapeHtml(teamName)}</h2>
          <p>${players.length} players</p>
        </div>
      </div>

      <div class="player-stats-table-wrap">
        <table class="player-stats-table">
          <thead>
            <tr>
                <th>Player</th>
                <th>G</th>
                <th>A</th>
                <th>P</th>
                <th>SH</th>
                <th>SV</th>
                <th>BLK</th>
                <th>FOW</th>
                <th>FOL</th>
                <th>TA</th>
                <th>TO</th>
                <th>PH</th>
                <th>PASS</th>
                <th>POSS</th>
            </tr>
            </thead>

          <tbody>
            ${
              players.length
                ? players.map(renderPlayerStatRow).join("")
                : `
                  <tr>
                    <td colspan="14">No player stats found.</td>
                  </tr>
                `
            }
          </tbody>
        </table>
      </div>
    </section>
  `;
}

function formatPossessionTime(seconds) {
  const total = Number(seconds || 0);
  const minutes = Math.floor(total / 60);
  const remainingSeconds = Math.round(total % 60);

  return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
}

function renderPlayerStatRow(player) {
  return `
    <tr>
      <td class="player-name-cell">
        ${escapeHtml(player.username || "Unknown")}
      </td>
      <td>${player.goals ?? 0}</td>
      <td>${player.assists ?? 0}</td>
      <td><strong>${player.points ?? 0}</strong></td>
      <td>${player.shots ?? 0}</td>
      <td>${player.saves ?? 0}</td>
      <td>${player.blocks ?? 0}</td>
      <td>${player.faceoffs_won ?? 0}</td>
      <td>${player.faceoffs_lost ?? 0}</td>
      <td>${player.takeaways ?? 0}</td>
      <td>${player.turnovers ?? 0}</td>
      <td>${player.post_hits ?? 0}</td>
      <td>${player.passes ?? 0}</td>
      <td>${formatPossessionTime(player.possession_time_sec)}</td>
    </tr>
  `;
}

function getGoalieForSide(side) {
  const players = getPlayersForSide(side);

  return players
    .slice()
    .sort((a, b) => {
      return (
        Number(b.saves || 0) - Number(a.saves || 0)
        || Number(b.shots_faced || 0) - Number(a.shots_faced || 0)
        || Number(a.conceded_goals || 0) - Number(b.conceded_goals || 0)
        || cleanText(a.username).localeCompare(cleanText(b.username))
      );
    })[0] || null;
}

function renderGoalieCards(match) {
  if (!currentMatchDetail) {
    return "";
  }

  return `
    <section class="match-section-title">
      <h2>Goaltenders</h2>
      <p>Top saves player from each team.</p>
    </section>

    <section class="goalie-card-grid">
      ${renderGoalieCard(match, "home")}
      ${renderGoalieCard(match, "away")}
    </section>
  `;
}

function renderGoalieCard(match, side) {
  const goalie = getGoalieForSide(side);

  const teamId = side === "home" ? match.home_team_id : match.away_team_id;
  const teamName = side === "home" ? match.home_team : match.away_team;

  if (!goalie) {
    return `
      <section class="goalie-card">
        <h3>${escapeHtml(teamName)}</h3>
        <p>No goaltender data found.</p>
      </section>
    `;
  }

  return `
    <section
      class="goalie-card ${side}"
      style="
        --team-primary: ${getThemeValue(teamId, "primary", "#7bdff2")};
        --team-accent: ${getThemeValue(teamId, "accent", "#ffffff")};
        --team-card: ${getThemeValue(teamId, "card", "#111111")};
      "
    >
      <div class="goalie-card-head">
        ${renderTeamLogo(teamId, teamName, side)}

        <div>
          <span>Goaltender</span>
          <h3>${escapeHtml(goalie.username || "Unknown")}</h3>
          <p>${escapeHtml(teamName)}</p>
        </div>
      </div>

      <div class="goalie-stat-grid">
        <div>
          <span>Shots Faced</span>
          <strong>${goalie.shots_faced ?? 0}</strong>
        </div>

        <div>
          <span>Goals Allowed</span>
          <strong>${goalie.conceded_goals ?? 0}</strong>
        </div>

        <div>
          <span>Save %</span>
          <strong>${goalie.save_percent ?? "0.000"}</strong>
        </div>

        <div>
          <span>GAA</span>
          <strong>${goalie.gaa ?? 0}</strong>
        </div>
      </div>
    </section>
  `;
}

function renderProcessingPanel(match) {
  const warnings = match.warnings || [];

  return `
    <section class="processing-panel player-card">
      <h2>Match Processing</h2>

      <div class="processing-grid">
        <div>
          <span>Status</span>
          <strong>${formatStatus(match.status)}</strong>
        </div>

        <div>
          <span>Log Folder</span>
          <strong>${match.log_folder ? "Uploaded" : "Not uploaded"}</strong>
        </div>

        <div>
          <span>Report File</span>
          <strong>${match.report_file ? "Found" : "None"}</strong>
        </div>

        <div>
          <span>Side Mapping</span>
          <strong>${match.side_mapping || "N/A"}</strong>
        </div>
      </div>

      ${
        warnings.length
          ? `
            <div class="warnings-box">
              <h3>Warnings</h3>
              <ul>
                ${warnings.map(warning => `
                  <li>${escapeHtml(warning)}</li>
                `).join("")}
              </ul>
            </div>
          `
          : `
            <div class="no-warnings">
              No warnings.
            </div>
          `
      }
    </section>
  `;
}

function renderMatchPage(match) {
  document.title = `${match.home_team} vs ${match.away_team} | SPLStats`;

  const page = document.querySelector("#matchPage");

  page.innerHTML = `
    ${renderHero(match)}
    ${renderSummary(match)}
    ${
      isFinal(match)
        ? renderResultMode(match)
        : renderPreviewMode(match)
    }
  `;

  attachShotMapFilters();
}

async function loadMatchData() {
  const matchId = MATCH_ID;

  if (!matchId) {
    document.querySelector("#matchPage").innerHTML = `
      <section class="player-card">
        No match ID was provided.
      </section>
    `;
    return;
  }

  const [
    scheduleData,
    matchesData,
    rostersData,
    snapshotsData,
    metadataList
  ] = await Promise.all([
    fetchJsonOrFallback(DATA_PATHS.schedule, { matches: [] }),
    fetchJsonOrFallback(DATA_PATHS.matches, { matches: [] }),
    fetchJsonOrFallback(DATA_PATHS.rosters, { teams: [] }),
    fetchJsonOrFallback(DATA_PATHS.rosterSnapshots, {}),
    fetchJsonOrFallback(DATA_PATHS.teamMetadata, [])
  ]);

  matches = mergeScheduledAndCompletedMatches(scheduleData, matchesData);

  rosterSnapshots = snapshotsData || {};
  rostersByTeamId = {};
  metadataByTeamId = {};

  (rostersData.teams || []).forEach(team => {
    if (!team.team_id) return;
    rostersByTeamId[team.team_id] = team;
  });

  metadataList.forEach(team => {
    if (!team.team_id) return;
    metadataByTeamId[team.team_id] = team;
  });

  const match = matches.find(item => {
    return item.match_id === matchId
      || item.schedule_id === matchId
      || item.source_id === matchId
      || item.id === matchId;
  });

  if (!match) {
    document.querySelector("#matchPage").innerHTML = `
      <section class="player-card">
        Match not found: ${escapeHtml(matchId)}
      </section>
    `;
    return;
  }

  currentMatch = match;
  currentMatchDetail = null;
  currentShotMap = null;

  activeShotTeam = "all";
  activeShotResult = "all";
  activeShotPeriod = "all";

  if (match.status === "final") {
    const detailPath = `${DATA_PATHS.matchDetailsBase}/${encodeURIComponent(match.match_id)}.json`;
    const shotMapPath = `${DATA_PATHS.shotMapsBase}/${encodeURIComponent(match.match_id)}.json`;

    try {
      const detailResponse = await fetch(detailPath);

      if (detailResponse.ok) {
        currentMatchDetail = await detailResponse.json();
      }
    } catch (error) {
      console.warn("Could not load match detail file", error);
    }

    try {
      const shotMapResponse = await fetch(shotMapPath);

      if (shotMapResponse.ok) {
        currentShotMap = await shotMapResponse.json();
      }
    } catch (error) {
      console.warn("Could not load shot map file", error);
    }
  }

  renderMatchPage(match);
}

loadMatchData().catch(error => {
    console.error(error);

    document.querySelector("#matchPage").innerHTML = `
        <section class="player-card">
        Failed to load match data.
        </section>
    `;
});