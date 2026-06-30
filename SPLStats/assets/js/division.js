const SEASON_ID = "summer_2026";

const DATA_PATHS = {
  activeRosters: `data/live_season/${SEASON_ID}/active_rosters.json`,
  teamMetadata: "data/team_metadata.json",
  regularSchedule: `data/live_season/${SEASON_ID}/regular_season/schedule.json`,
  regularMatches: `data/live_season/${SEASON_ID}/regular_season/matches.json`,
  standings: `data/live_season/${SEASON_ID}/regular_season/standings.json`,
  leaders: `data/live_season/${SEASON_ID}/regular_season/leaders.json`,
  articles: `data/live_season/${SEASON_ID}/news/articles.json`,
  broadcasts: `data/live_season/${SEASON_ID}/regular_season/broadcasts.json`,
  divisionSummary: `data/live_season/${SEASON_ID}/regular_season/division_summary.json`
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

const DIVISION_REGIONS = {
  pro: "East",
  challenger: "East",
  intermediate: "East",
  prospect: "East",
  open: "East",
  central_a: "Central",
  central_b: "Central",
  central_c: "Central",
  central_d: "Central",
  masters: "West",
  contenders: "West"
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

let appData = {
  activeRosters: { teams: [] },
  teamMetadata: [],
  schedule: [],
  matches: [],
  standings: null,
  leaders: null,
  articles: { articles: [] },
  broadcasts: {}
};

let standingsView = "conference";

function attachStandingsToggle() {
  document.querySelectorAll("[data-standings-view]").forEach(button => {
    button.addEventListener("click", () => {
      standingsView = button.dataset.standingsView || "conference";

      document.querySelectorAll("[data-standings-view]").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.standingsView === standingsView);
      });

      renderStandings(getDivisionFromUrl());
    });
  });
}

function divisionUsesConferences(rows) {
  const conferences = new Set(
    rows
      .map(row => cleanText(row.conference))
      .filter(Boolean)
  );

  return conferences.size > 1;
}

function getConferencePlayoffConfig(teamCount) {
  if (teamCount === 14) {
    return {
      autoPerConference: 3,
      wildcardCount: 2,
      bubbleCount: 4
    };
  }

  if (teamCount === 12) {
    return {
      autoPerConference: 2,
      wildcardCount: 2,
      bubbleCount: 4
    };
  }

  return {
    autoPerConference: 0,
    wildcardCount: 0,
    bubbleCount: 0
  };
}


function getMatchUrl(match) {
  const matchId =
    match.match_id
    || match.id
    || match.schedule_id
    || match.source_id
    || "";

  if (!matchId) return "#";

  return `match.html?id=${encodeURIComponent(matchId)}`;
}


function renderDivisionShield(division) {
  const shieldPath = DIVISION_SHIELDS[division] || "";

  const left = document.querySelector("#divisionShieldLeft");
  const right = document.querySelector("#divisionShieldRight");

  [left, right].forEach(img => {
    if (!img) return;

    if (!shieldPath) {
      img.style.display = "none";
      img.removeAttribute("src");
      return;
    }

    img.src = shieldPath;
    img.alt = `${DIVISION_LABELS[division] || "Division"} shield`;
    img.style.display = "";
  });
}

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

function getDivisionFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return normalizeKey(params.get("division")) || "pro";
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

function getMetadataList() {
  if (Array.isArray(appData.teamMetadata)) return appData.teamMetadata;
  if (Array.isArray(appData.teamMetadata?.teams)) return appData.teamMetadata.teams;
  return [];
}

function findTeamMetadata(teamIdOrName) {
  const target = normalizeKey(teamIdOrName);

  return getMetadataList().find(team => {
    const values = [
      team.team_id,
      team.team_display_name,
      team.team_name,
      team.team,
      ...(team.aliases || []),
      ...(team.team_aliases || [])
    ].map(normalizeKey).filter(Boolean);

    return values.includes(target);
  }) || null;
}

function getRosterTeams() {
  if (Array.isArray(appData.activeRosters)) return appData.activeRosters;
  return appData.activeRosters?.teams || [];
}

function getTeamsForDivision(division) {
  return getRosterTeams()
    .filter(team => normalizeKey(team.division) === normalizeKey(division));
}

function getTeamDisplayName(teamIdOrName) {
  const metadata = findTeamMetadata(teamIdOrName);
  return metadata?.team_display_name || metadata?.team_name || metadata?.team || cleanText(teamIdOrName);
}

function getTeamAbbreviation(teamIdOrName) {
  const rosterTeam = getRosterTeams().find(team => {
    return normalizeKey(team.team_id) === normalizeKey(teamIdOrName)
      || normalizeKey(team.team_display_name) === normalizeKey(teamIdOrName)
      || normalizeKey(team.team) === normalizeKey(teamIdOrName);
  });

  const metadata = findTeamMetadata(teamIdOrName);

  return (
    rosterTeam?.team_abbreviation
    || metadata?.team_abbreviation
    || metadata?.abbreviation
    || getTeamDisplayName(teamIdOrName).slice(0, 3).toUpperCase()
  );
}

function getTeamLogo(teamIdOrName) {
  const metadata = findTeamMetadata(teamIdOrName);
  return metadata?.logo || metadata?.team_logo || metadata?.logo_path || "";
}

function getTeamTheme(teamIdOrName) {
  const metadata = findTeamMetadata(teamIdOrName);
  return metadata?.theme || metadata?.colors || {};
}

function getThemeValue(teamIdOrName, key, fallback) {
  const theme = getTeamTheme(teamIdOrName);
  const metadata = findTeamMetadata(teamIdOrName);

  return (
    theme?.[key]
    || metadata?.[key]
    || fallback
  );
}

function getStandingsArray() {
  if (Array.isArray(appData.standings)) {
    return appData.standings;
  }

  if (Array.isArray(appData.standings?.standings)) {
    return appData.standings.standings;
  }

  return [];
}

function getStandingsRowsForDivision(division) {
  const currentDivision = normalizeKey(division);

  return getStandingsArray()
    .filter(row => normalizeKey(row.division) === currentDivision)
    .sort((a, b) => {
      return (
        Number(a.conference || 0) - Number(b.conference || 0)
        || Number(a.conference_rank || 999) - Number(b.conference_rank || 999)
        || Number(a.division_rank || 999) - Number(b.division_rank || 999)
        || cleanText(a.team_display_name || a.team).localeCompare(
          cleanText(b.team_display_name || b.team)
        )
      );
    });
}

function normalizeStandingsRow(row) {
  return {
    ...row,

    gp: row.gp ?? row.games_played ?? 0,
    losses: row.losses ?? ((row.regulation_losses ?? 0) + (row.overtime_losses ?? 0)),
    gf: row.gf ?? row.goals_for ?? 0,
    ga: row.ga ?? row.goals_against ?? 0,
    diff: row.diff ?? row.goal_diff ?? 0,

    playoff_status:
      row.playoff_status
      || playoffBucketToStatus(row.playoff_bucket),

    playoff_badge:
      row.playoff_badge
      || playoffBucketToBadge(row.playoff_bucket)
  };
}

function playoffBucketToStatus(bucket) {
  if (bucket === "automatic_qualifier") return "auto";
  if (bucket === "wildcard") return "wildcard";
  if (bucket === "bubble") return "bubble";
  if (bucket === "chase") return "";
  return "";
}

function playoffBucketToBadge(bucket) {
  if (bucket === "automatic_qualifier") return "AQ";
  if (bucket === "wildcard") return "WC";
  if (bucket === "bubble") return "BUB";
  if (bucket === "chase") return "";
  return "";
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

  return [];
}

function getAllRegularMatches() {
  const schedule = getMatchArray(appData.schedule);
  const matches = getMatchArray(appData.matches);

  const byId = new Map();

  schedule.forEach(match => {
    const id = match.match_id || match.id || match.schedule_id || match.source_id;

    if (id) {
      byId.set(id, match);
    }
  });

  matches.forEach(match => {
    const id = match.match_id || match.id || match.schedule_id || match.source_id;

    if (!id) return;

    byId.set(id, {
      ...(byId.get(id) || {}),
      ...match
    });
  });

  return [...byId.values()];
}

function matchHasDivision(match, division) {
  const current = normalizeKey(division);

  const values = [
    match.division,
    match.division_id,
    match.home_division,
    match.away_division,
    match.fixture_group,
    match.group
  ].map(normalizeKey).filter(Boolean);

  if (values.includes(current)) {
    return true;
  }

  const divisionTeams = new Set(
    getTeamsForDivision(division)
      .flatMap(team => [
        team.team_id,
        team.team_display_name,
        team.team_name,
        team.team
      ])
      .map(normalizeKey)
      .filter(Boolean)
  );

  const homeId = normalizeKey(match.home_team_id || match.home_team);
  const awayId = normalizeKey(match.away_team_id || match.away_team);

  return divisionTeams.has(homeId) || divisionTeams.has(awayId);
}

function getDivisionMatches(division) {
  return getAllRegularMatches()
    .filter(match => matchHasDivision(match, division));
}

function isFinal(match) {
  const status = cleanText(match.status || match.match_status).toLowerCase();

  return status === "final"
    || status === "completed"
    || status === "complete"
    || (
      match.home_score !== undefined
      && match.away_score !== undefined
      && match.home_score !== null
      && match.away_score !== null
    );
}

function getMatchSortValue(match) {
  const dateValue = Date.parse(match.date || match.datetime || match.played_at || match.scheduled_at || "");

  if (!Number.isNaN(dateValue)) {
    return dateValue;
  }

  const week = Number(match.week || 0);
  const matchNumber = Number(match.match_number || match.match || 0);

  return (week * 1000) + matchNumber;
}

function getRecentResults(division) {
  return getDivisionMatches(division)
    .filter(isFinal)
    .sort((a, b) => getMatchSortValue(b) - getMatchSortValue(a))
    .slice(0, 7);
}

function getUpcomingMatches(division) {
  return getDivisionMatches(division)
    .filter(match => !isFinal(match))
    .sort((a, b) => getMatchSortValue(a) - getMatchSortValue(b))
    .slice(0, 7);
}

function getMatchTeam(match, side) {
  if (side === "home") {
    return {
      id: match.home_team_id || match.home_team,
      name: match.home_team || getTeamDisplayName(match.home_team_id),
      score: match.home_score
    };
  }

  return {
    id: match.away_team_id || match.away_team,
    name: match.away_team || getTeamDisplayName(match.away_team_id),
    score: match.away_score
  };
}

function getBroadcast(match) {
  const id = match.match_id || match.id || match.schedule_id;

  if (match.broadcast?.is_casted || match.broadcast?.channel_name) {
    return match.broadcast;
  }

  return appData.broadcasts?.[id] || null;
}

function formatDateLabel(match) {
  const raw = match.played_at || match.date || match.datetime || match.scheduled_at || "";

  if (raw) {
    const date = new Date(raw);

    if (!Number.isNaN(date.getTime())) {
      return date.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric"
      });
    }
  }

  return "Date TBD";
}

function formatWeekLabel(match) {
  if (match.week) return `Week ${match.week}`;

  const scheduleId = cleanText(
    match.source_id
    || match.schedule_id
    || match.match_code
    || ""
  );

  const weekMatch = scheduleId.match(/^(\d+)\./);

  if (weekMatch) {
    return `Week ${weekMatch[1]}`;
  }

  return "Week TBD";
}

function renderTeamLogo(teamIdOrName, className) {
  const logo = getTeamLogo(teamIdOrName);
  const name = getTeamDisplayName(teamIdOrName);

  if (!logo) {
    return `<div class="${className} placeholder">${name.slice(0, 1)}</div>`;
  }

  return `<img class="${className}" src="${logo}" alt="">`;
}

function renderMatchCard(match, type) {
  const home = getMatchTeam(match, "home");
  const away = getMatchTeam(match, "away");

  const homePrimary = getThemeValue(home.id, "primary", "#ffd166");
  const awayPrimary = getThemeValue(away.id, "primary", "#00d1d1");

  const homeAbbr = getTeamAbbreviation(home.id || home.name);
  const awayAbbr = getTeamAbbreviation(away.id || away.name);

  const scoreText = type === "result"
    ? `${away.score ?? 0} - ${home.score ?? 0}`
    : "@";

  const kicker = type === "result"
    ? formatDateLabel(match)
    : formatWeekLabel(match);

  const href = getMatchUrl(match);

  const broadcast = getBroadcast(match);
  const isCasted = Boolean(broadcast?.channel_name || broadcast?.is_casted);
  const channelName = broadcast?.channel_name || broadcast?.channel || "Twitch Broadcast";

  return `
    <a
      class="division-match-card ${isCasted ? "is-casted" : ""}"
      href="${href}"
      style="
        --away-primary: ${awayPrimary};
        --home-primary: ${homePrimary};
      "
    >
      ${
        isCasted
          ? `<div class="division-match-broadcast">TWITCH · ${channelName}</div>`
          : ""
      }

      <div class="division-match-body">
        <div class="division-match-kicker">${kicker}</div>

        <div class="division-match-line">
          ${renderTeamLogo(away.id || away.name, "division-match-logo")}
          <div class="division-match-abbr">${awayAbbr}</div>
          <div class="division-match-score">${scoreText}</div>
          <div class="division-match-abbr">${homeAbbr}</div>
          ${renderTeamLogo(home.id || home.name, "division-match-logo")}
        </div>
      </div>
    </a>
  `;
}

function renderMatchList(containerId, matches, type) {
  const container = document.querySelector(`#${containerId}`);

  if (!container) return;

  if (!matches.length) {
    container.innerHTML = `
      <div class="division-empty">
        ${type === "result" ? "No recent results yet." : "No upcoming matches scheduled."}
      </div>
    `;
    return;
  }

  container.innerHTML = matches.map(match => renderMatchCard(match, type)).join("");
}


    // Multi Conference Wildcard Renderer
function renderWildcardRace(rows) {
  const config = getConferencePlayoffConfig(rows.length);
  const rowsWithStatus = rows;

  const automatic = rowsWithStatus.filter(row => row.playoff_status === "auto");
  const wildcards = rowsWithStatus.filter(row => row.playoff_status === "wildcard");
  const bubble = rowsWithStatus.filter(row => row.playoff_status === "bubble");

  if (!config.autoPerConference) {
    return renderStandingsTable(rowsWithStatus);
  }

  return `
    <section class="wildcard-section">
      <div>
        <h3 class="wildcard-group-title">Automatic Qualifiers</h3>
        ${renderStandingsTable(automatic)}
      </div>

      <div>
        <h3 class="wildcard-group-title">Wildcard Race</h3>
        ${renderStandingsTable(wildcards)}
      </div>

      <div>
        <h3 class="wildcard-group-title">Bubble / Chase</h3>
        ${
          bubble.length
            ? renderStandingsTable(bubble)
            : `<div class="division-empty">No bubble teams yet.</div>`
        }
      </div>
    </section>
  `;
}

function renderStandingsTable(rows) {
  if (!rows.length) {
    return `<div class="division-empty">No teams found for this division.</div>`;
  }

  return `
    <table class="standings-table">
      <thead>
        <tr>
          <th>Team</th>
          <th>GP</th>
          <th>W</th>
          <th>L</th>
          <th>PTS</th>
          <th>GF</th>
          <th>GA</th>
          <th>DIFF</th>
          <th>Status</th>
        </tr>
      </thead>

      <tbody>
        ${rows.map(row => `
          <tr class="${row.playoff_status ? `standings-row-${row.playoff_status}` : ""}">
            <td>
              <a class="standings-team" href="team.html?id=${encodeURIComponent(row.team_id)}">
                ${renderTeamLogo(row.team_id, "standings-logo-placeholder")}
                <span>${row.team_display_name}</span>
              </a>
            </td>
            <td>${row.gp}</td>
            <td>${row.wins}</td>
            <td>${row.losses}</td>
            <td><strong>${row.points}</strong></td>
            <td>${row.gf}</td>
            <td>${row.ga}</td>
            <td>${row.diff}</td>
            <td>
              ${
                row.playoff_badge
                ? `<span class="playoff-badge ${row.playoff_status}">${row.playoff_badge}</span>`
                : ""
              }
            </td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function renderStandings(division) {
  const container = document.querySelector("#standingsContent");
  const toggle = document.querySelector("#standingsViewToggle");

  if (!container) return;

  let rows = getStandingsRowsForDivision(division)
    .map(normalizeStandingsRow);

  const usesConferences = divisionUsesConferences(rows);

  if (toggle) {
    toggle.style.display = usesConferences ? "" : "none";
  }

  if (usesConferences && standingsView === "wildcard") {
    container.innerHTML = renderWildcardRace(rows);
    return;
  }

  const conferenceGroups = rows.reduce((groups, row) => {
    const key = row.conference || "all";
    groups[key] ||= [];
    groups[key].push(row);
    return groups;
  }, {});

  const conferenceKeys = Object.keys(conferenceGroups)
    .filter(key => key !== "all")
    .sort();

  if (conferenceKeys.length > 1) {
    container.innerHTML = conferenceKeys.map(key => `
      <section class="conference-standings-block">
        <div class="division-panel-head">
          <span>Conference</span>
          <h2>Conference ${key}</h2>
        </div>
        ${renderStandingsTable(conferenceGroups[key])}
      </section>
    `).join("");

    return;
  }

  container.innerHTML = renderStandingsTable(rows);
}

function getLeaderData(statKey, division = getDivisionFromUrl()) {
  const leaders = appData.leaders;

  if (!leaders) return [];

  const divisionKey = normalizeKey(division);

  const players = Array.isArray(leaders.players)
    ? leaders.players
    : [];

  return players
    .filter(player => normalizeKey(player.division) === divisionKey)
    .filter(player => {
      if (statKey === "save_percent") {
        return Number(player.shots_faced || 0) > 0;
      }

      if (statKey === "shooting_percent") {
        return Number(player.shots || 0) > 0;
      }

      if (statKey === "faceoff_percent") {
        return (
          Number(player.faceoffs_won || 0)
          + Number(player.faceoffs_lost || 0)
        ) > 0;
      }

      return Number(player[statKey] || 0) > 0;
    })
    .sort((a, b) => {
      return (
        Number(b[statKey] || 0) - Number(a[statKey] || 0)
        || Number(b.points || 0) - Number(a.points || 0)
        || Number(b.goals || 0) - Number(a.goals || 0)
        || cleanText(a.player_display_name || a.player_name).localeCompare(
          cleanText(b.player_display_name || b.player_name)
        )
      );
    });
}

function renderLeaderRow(player, statKey) {
  const teamId = player.team_id || player.team || "";
  const statValue = player[statKey] ?? player.value ?? 0;
  const gp = player.games_played ?? player.gp ?? 0;

  const teamPrimary = getThemeValue(teamId, "primary", "#00d1d1");

  // URL identity should ONLY use player_id.
  const playerUrlId = cleanText(player.player_id || "");

  // Frontend display should prefer corrected display name.
  const playerDisplayName =
    player.player_display_name
    || player.player_name
    || player.name
    || "Unknown Player";

  const href = playerUrlId
    ? `player.html?id=${encodeURIComponent(playerUrlId)}`
    : "#";

  return `
    <a
      class="leader-row ${playerUrlId ? "" : "is-disabled"}"
      href="${href}"
      style="--team-primary: ${teamPrimary};"
    >
      ${renderTeamLogo(teamId, "leader-logo")}

      <div class="leader-main">
        <strong>${playerDisplayName}</strong>
        <span>${getTeamAbbreviation(teamId)} · ${gp} GP</span>
      </div>

      <div class="leader-stat">${statValue}</div>
    </a>
  `;
}

function renderLeaderList(containerId, statKey, division) {
  const container = document.querySelector(`#${containerId}`);

  if (!container) return;

  const rows = getLeaderData(statKey, division).slice(0, 7);

  if (!rows.length) {
    container.innerHTML = `
      <div class="division-empty">
        Leaders will appear after regular season stats are processed.
      </div>
    `;
    return;
  }

  container.innerHTML = rows.map(player => renderLeaderRow(player, statKey)).join("");
}

function renderArticles(division) {
  const panel = document.querySelector("#divisionNewsPanel");
  const container = document.querySelector("#divisionNewsContent");

  if (!panel || !container) return;

  const articles = appData.articles?.articles || appData.articles || [];

  const divisionArticles = articles.filter(article => {
    const tags = article.division_tags || article.divisions || [];
    return tags.map(normalizeKey).includes(normalizeKey(division));
  });

  if (!divisionArticles.length) {
    panel.style.display = "none";
    container.innerHTML = "";
    return;
  }

  panel.style.display = "";

  container.innerHTML = divisionArticles.slice(0, 4).map(article => `
    <a class="division-news-card" href="${article.url || `article.html?slug=${encodeURIComponent(article.slug || "")}`}">
      <span>${article.published_at || article.date || ""}</span>
      <strong>${article.title}</strong>
      <p>${article.excerpt || ""}</p>
    </a>
  `).join("");
}

function renderPage(division) {
  const label = DIVISION_LABELS[division] || "Pro";
  const region = DIVISION_REGIONS[division] || "East";

  document.title = `${label} Division | SPLStats`;

  document.querySelector("#divisionTitle").textContent = `${label} Division`;
  document.querySelector("#divisionRegionLabel").textContent = `${region} Region`;

  renderDivisionShield(division);

  document.querySelectorAll("[data-division]").forEach(button => {
    button.classList.toggle(
      "active",
      normalizeKey(button.dataset.division) === normalizeKey(division)
    );
  });

  renderMatchList("recentResults", getRecentResults(division), "result");
  renderMatchList("upcomingMatches", getUpcomingMatches(division), "scheduled");
  renderStandings(division);
  renderArticles(division);

  renderLeaderList("goalsLeaders", "goals", division);
  renderLeaderList("pointsLeaders", "points", division);
  renderLeaderList("savesLeaders", "saves", division);
  renderLeaderList("savePercentLeaders", "save_percent", division);
}

function attachDivisionButtons() {
  document.querySelectorAll("[data-division]").forEach(button => {
    button.addEventListener("click", () => {
      const division = normalizeKey(button.dataset.division);

      const url = new URL(window.location.href);
      url.searchParams.set("division", division);
      window.history.pushState({}, "", url);

      renderPage(division);
    });
  });

  window.addEventListener("popstate", () => {
    renderPage(getDivisionFromUrl());
  });
}

async function loadDivisionPage() {
  const [
    activeRosters,
    teamMetadata,
    schedule,
    matches,
    standings,
    leaders,
    articles,
    broadcasts
  ] = await Promise.all([
    fetchJsonOrFallback(DATA_PATHS.activeRosters, { teams: [] }),
    fetchJsonOrFallback(DATA_PATHS.teamMetadata, []),
    fetchJsonOrFallback(DATA_PATHS.regularSchedule, []),
    fetchJsonOrFallback(DATA_PATHS.regularMatches, []),
    fetchJsonOrFallback(DATA_PATHS.standings, null),
    fetchJsonOrFallback(DATA_PATHS.leaders, null),
    fetchJsonOrFallback(DATA_PATHS.articles, { articles: [] }),
    fetchJsonOrFallback(DATA_PATHS.broadcasts, {})
  ]);

  appData = {
    activeRosters,
    teamMetadata,
    schedule,
    matches,
    standings,
    leaders,
    articles,
    broadcasts
  };

  attachDivisionButtons();
  attachStandingsToggle();
  renderPage(getDivisionFromUrl());
}

loadDivisionPage().catch(error => {
  console.error(error);

  document.body.innerHTML = `
    <main class="division-layout">
      <section class="division-panel">
        <div class="division-empty">
          Failed to load division page data.
        </div>
      </section>
    </main>
  `;
});