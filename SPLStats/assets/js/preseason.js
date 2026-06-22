const SEASON_ID = "summer_2026";

const DATA_PATHS = {
  schedule: `data/live_season/${SEASON_ID}/preseason/schedule.json`,
  standings: `data/live_season/${SEASON_ID}/preseason/standings.json`,
  teamMetadata: "data/team_metadata.json"
};

let preseasonMatches = [];
let preseasonStandings = [];
let teamMetadata = {};

let activeRegion = "all";
let activeStatus = "all";

const REGION_ORDER = {
  east: 1,
  central: 2,
  west: 3,
  unknown: 99
};

function getRegionSortValue(region) {
  return REGION_ORDER[cleanText(region).toLowerCase()] || 99;
}

function cleanText(value) {
  return String(value || "").trim();
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

function matchNeedsReview(match) {
  return (
    match.status !== "scheduled"
    && (
      match.status !== "final"
      || (match.warnings || []).length > 0
    )
  );
}

function matchPassesFilters(match) {
  if (activeRegion !== "all" && match.region !== activeRegion) {
    return false;
  }

  if (activeStatus === "needs_review") {
    return matchNeedsReview(match);
  }

  if (activeStatus !== "all" && match.status !== activeStatus) {
    return false;
  }

  return true;
}

function standingsPassesFilters(team) {
  if (activeRegion !== "all" && team.region !== activeRegion) {
    return false;
  }

  return true;
}

function getMatchScoreText(match) {
  if (match.status !== "final") {
    return "vs";
  }

  return `${match.home_score} - ${match.away_score}`;
}

function getWinnerClass(match, side) {
  if (match.status !== "final") return "";

  if (side === "home" && match.winner_team_id === match.home_team_id) {
    return "winner";
  }

  if (side === "away" && match.winner_team_id === match.away_team_id) {
    return "winner";
  }

  return "";
}

function renderStatusText() {
  const total = preseasonMatches.length;
  const finals = preseasonMatches.filter(match => match.status === "final").length;
  const scheduled = preseasonMatches.filter(match => match.status === "scheduled").length;
  const review = preseasonMatches.filter(matchNeedsReview).length;

  const container = document.querySelector("#preseasonStatusText");

  container.textContent =
    `${total} matches · ${finals} final · ${scheduled} scheduled · ${review} needing review`;
}

function getTeamMetadata(teamId) {
  return teamMetadata[teamId] || null;
}

function getTeamStyle(teamId) {
  const meta = getTeamMetadata(teamId);
  const theme = meta?.theme || {};

  return `
    --row-team-primary: ${theme.primary || "#7bdff2"};
    --row-team-secondary: ${theme.secondary || "#111111"};
    --row-team-accent: ${theme.accent || "#ffffff"};
    --row-team-background: ${theme.background || "#050505"};
    --row-team-card: ${theme.card || "#111111"};
    --row-team-surface: ${theme.surface || "#1a1a1a"};
  `;
}

function getTeamLogo(teamId) {
  const meta = getTeamMetadata(teamId);
  return meta?.logo || "";
}

function getMatchCardStyle(match) {
  const homeMeta = getTeamMetadata(match.home_team_id);
  const awayMeta = getTeamMetadata(match.away_team_id);

  const homeTheme = homeMeta?.theme || {};
  const awayTheme = awayMeta?.theme || {};

  return `
    --home-primary: ${homeTheme.primary || "#7bdff2"};
    --home-accent: ${homeTheme.accent || "#ffffff"};
    --home-card: ${homeTheme.card || "#111111"};

    --away-primary: ${awayTheme.primary || "#ffd166"};
    --away-accent: ${awayTheme.accent || "#ffffff"};
    --away-card: ${awayTheme.card || "#111111"};
  `;
}

function getMatchTeamLogo(teamId) {
  const meta = getTeamMetadata(teamId);
  return meta?.logo || "";
}

function renderStandings() {
  const tbody = document.querySelector("#preseasonStandingsTable tbody");

  const rows = preseasonStandings
    .filter(standingsPassesFilters)
    .sort((a, b) => {
      return (
        getRegionSortValue(a.region) - getRegionSortValue(b.region)
        || (a.rank ?? 999) - (b.rank ?? 999)
        || cleanText(a.team_display_name || a.team).localeCompare(
          cleanText(b.team_display_name || b.team)
        )
      );
    });

  tbody.innerHTML = rows.map(team => {
    const logo = getTeamLogo(team.team_id);

    return `
      <tr
        class="themed-standings-row"
        style="${getTeamStyle(team.team_id)}"
      >
        <td>${team.rank ?? ""}</td>

        <td class="team-cell themed-team-cell">
          <span class="region-pill region-${team.region}">
            ${formatRegion(team.region)}
          </span>

          <div class="standings-team-name-wrap">
            <a href="team.html?id=${encodeURIComponent(team.team_id)}">
              ${team.team_display_name || team.team}
            </a>
          </div>

          ${
            logo
              ? `
                <img
                  class="standings-team-logo"
                  src="${logo}"
                  alt=""
                  aria-hidden="true"
                >
              `
              : `
                <span class="standings-team-logo-placeholder"></span>
              `
          }
        </td>

        <td>${team.games_played ?? 0}</td>
        <td>${team.wins ?? 0}</td>
        <td>${team.regulation_losses ?? 0}</td>
        <td>${team.overtime_losses ?? 0}</td>
        <td><strong>${team.points ?? 0}</strong></td>
        <td>${team.goals_for ?? 0}</td>
        <td>${team.goals_against ?? 0}</td>
        <td>${team.goal_diff ?? 0}</td>
        <td>${team.last_5 || "0-0-0"}</td>
      </tr>
    `;
  }).join("");

  if (!rows.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="11" class="empty-row">
          No standings match the current filters.
        </td>
      </tr>
    `;
  }
}

function renderReviewQueue() {
  const section = document.querySelector("#reviewSection");
  const list = document.querySelector("#reviewList");

  const reviewMatches = preseasonMatches
    .filter(match => {
      if (activeRegion !== "all" && match.region !== activeRegion) {
        return false;
      }

      return matchNeedsReview(match);
    })
    .sort((a, b) => {
      return (
        getRegionSortValue(a.region) - getRegionSortValue(b.region)
        || cleanText(a.schedule_id).localeCompare(
          cleanText(b.schedule_id),
          undefined,
          { numeric: true }
        )
      );
    });

  if (!reviewMatches.length) {
    section.style.display = "none";
    list.innerHTML = "";
    return;
  }

  section.style.display = "";

  list.innerHTML = reviewMatches.map(match => `
    <div class="review-item">
      <div class="review-item-head">
        <strong>${match.schedule_id}</strong>
        <span class="region-pill region-${match.region}">
          ${formatRegion(match.region)}
        </span>
        <span class="status-pill status-${match.status}">
          ${formatStatus(match.status)}
        </span>
      </div>

      <div class="review-match-line">
        ${match.home_team}
        <span>vs</span>
        ${match.away_team}
      </div>

      <div class="review-meta">
        Mapping:
        ${match.side_mapping || "unknown"}
        (${match.side_mapping_normal_score ?? 0}
        /
        ${match.side_mapping_swapped_score ?? 0})
      </div>

      <ul>
        ${(match.warnings || []).map(warning => `
          <li>${warning}</li>
        `).join("")}
      </ul>
    </div>
  `).join("");
}

function groupMatchesByRegion(matches) {
  const groups = {
    east: [],
    central: [],
    west: [],
    unknown: []
  };

  matches.forEach(match => {
    const region = match.region || "unknown";

    if (!groups[region]) {
      groups[region] = [];
    }

    groups[region].push(match);
  });

  return groups;
}

function renderMatches() {
  const container = document.querySelector("#matchList");

  const filteredMatches = preseasonMatches
    .filter(matchPassesFilters);

  if (!filteredMatches.length) {
    container.innerHTML = `
      <div class="empty-panel">
        No matches match the current filters.
      </div>
    `;
    return;
  }

  const groups = groupMatchesByRegion(filteredMatches);

  container.innerHTML = Object.entries(groups)
    .filter(([_region, matches]) => matches.length)
    .sort(([regionA], [regionB]) => {
        return getRegionSortValue(regionA) - getRegionSortValue(regionB);
    })
    .map(([region, matches]) => `
      <section class="match-region-group">
        <h3>${formatRegion(region)}</h3>

        <div class="match-card-grid">
          ${matches.map(renderMatchCard).join("")}
        </div>
      </section>
    `).join("");

    attachMatchCardHandlers();
}

function renderMatchCard(match) {
  const needsReview = matchNeedsReview(match);
  const matchUrl = `match.html?id=${encodeURIComponent(match.match_id)}`;

  const homeLogo = getMatchTeamLogo(match.home_team_id);
  const awayLogo = getMatchTeamLogo(match.away_team_id);

  return `
    <article
      class="match-card ${needsReview ? "needs-review" : ""}"
      data-href="${matchUrl}"
      tabindex="0"
      role="link"
      aria-label="Open match ${match.schedule_id}: ${match.home_team} vs ${match.away_team}"
      style="${getMatchCardStyle(match)}"
    >
      <div class="match-card-top">
        <span class="match-id">
          ${match.schedule_id}
        </span>

        <span class="status-pill status-${match.status}">
          ${formatStatus(match.status)}
        </span>
      </div>

      <div class="match-teams">
        <div class="match-team home ${getWinnerClass(match, "home")}">
          ${
            homeLogo
              ? `
                <img
                  class="match-card-team-logo"
                  src="${homeLogo}"
                  alt=""
                  aria-hidden="true"
                >
              `
              : ""
          }

          <span>${match.home_team}</span>
        </div>

        <div class="match-score-block">
          ${
            match.status === "final"
              ? `
                <div class="match-final-score">
                  <span>${match.home_score}</span>
                  <strong>-</strong>
                  <span>${match.away_score}</span>
                </div>

                <div class="match-score-label">
                  Final
                </div>
              `
              : `
                <div class="match-vs">
                  VS
                </div>
              `
          }
        </div>

        <div class="match-team away ${getWinnerClass(match, "away")}">
          <span>${match.away_team}</span>

          ${
            awayLogo
              ? `
                <img
                  class="match-card-team-logo"
                  src="${awayLogo}"
                  alt=""
                  aria-hidden="true"
                >
              `
              : ""
          }
        </div>
      </div>

      ${
        match.status === "final"
          ? `
            <div class="match-meta">
              ${match.overtime ? "Overtime" : "Regulation"}
              ${
                match.side_mapping
                  ? ` · Mapping: ${match.side_mapping}`
                  : ""
              }
            </div>
          `
          : ""
      }

      ${
        needsReview
          ? `
            <div class="match-warning">
              Needs Review
            </div>
          `
          : ""
      }
    </article>
  `;
}

function attachMatchCardHandlers() {
  document.querySelectorAll(".match-card[data-href]").forEach(card => {
    card.addEventListener("click", () => {
      window.location.href = card.dataset.href;
    });

    card.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        window.location.href = card.dataset.href;
      }
    });
  });
}

function renderPage() {
  renderStatusText();
  renderStandings();
  renderReviewQueue();
  renderMatches();
}

async function loadPreseasonData() {
  const [
    scheduleResponse,
    standingsResponse,
    metadataResponse
  ] = await Promise.all([
    fetch(DATA_PATHS.schedule),
    fetch(DATA_PATHS.standings),
    fetch(DATA_PATHS.teamMetadata)
  ]);

  preseasonMatches = await scheduleResponse.json();
  preseasonStandings = await standingsResponse.json();

  const metadataList = await metadataResponse.json();

  teamMetadata = {};

  metadataList.forEach(team => {
    if (!team.team_id) return;
    teamMetadata[team.team_id] = team;
  });

  renderPage();
}

document.querySelector("#regionFilter").addEventListener("change", event => {
  activeRegion = event.target.value;
  renderPage();
});

document.querySelector("#statusFilter").addEventListener("change", event => {
  activeStatus = event.target.value;
  renderPage();
});

loadPreseasonData().catch(error => {
  console.error(error);

  document.querySelector("#preseasonStatusText").textContent =
    "Failed to load preseason data. Run py tools\\live\\build_preseason.py first.";
});