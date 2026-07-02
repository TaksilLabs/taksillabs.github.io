const SEASON_ID = "summer_2026";
const PAGE_SIZE = 10;
const ROSTER_LOCK_AT = "2026-07-26T23:59:00-04:00";

const DATA_PATHS = {
  transactions: `data/live_season/${SEASON_ID}/roster_transactions.json`,
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

let allTransactions = [];
let allGroups = [];
let filteredGroups = [];
let visibleCount = PAGE_SIZE;

let activeRegion = "all";
let activeDivision = "all";

let teamMetadata = {};

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

function getTransactions(data) {
  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data?.transactions)) {
    return data.transactions;
  }

  return [];
}

function getTeamMetadataMap(data) {
  if (!data) return {};

  if (Array.isArray(data)) {
    const map = {};

    data.forEach(team => {
      const teamId = normalizeKey(team.team_id || team.id || team.name);
      if (teamId) map[teamId] = team;
    });

    return map;
  }

  if (data.teams && Array.isArray(data.teams)) {
    const map = {};

    data.teams.forEach(team => {
      const teamId = normalizeKey(team.team_id || team.id || team.name);
      if (teamId) map[teamId] = team;
    });

    return map;
  }

  return data;
}

function getTransactionDayKey(transaction) {
  const createdAt = cleanText(transaction.created_at_utc);

  if (createdAt.includes("T")) {
    return createdAt.split("T", 1)[0];
  }

  return createdAt.slice(0, 10) || "unknown-date";
}

function getDraftIdForGroup(dayKey, teamId) {
  return `${dayKey}_${teamId || "unknown_team"}_roster_moves`;
}

function groupTransactions(transactions) {
  const groups = new Map();

  transactions.forEach(transaction => {
    const dayKey = getTransactionDayKey(transaction);
    const teamId = normalizeKey(transaction.team_id || transaction.team_display_name || "unknown_team");
    const groupKey = `${dayKey}__${teamId}`;
    const draftId = getDraftIdForGroup(dayKey, teamId);

    if (!groups.has(groupKey)) {
      groups.set(groupKey, {
        group_key: groupKey,
        draft_id: draftId,
        press_release_url: `press_release.html?id=${encodeURIComponent(draftId)}`,

        day_key: dayKey,
        created_at_utc: cleanText(transaction.created_at_utc),

        team_id: teamId,
        team_abbreviation: cleanText(transaction.team_abbreviation),
        team_display_name: cleanText(transaction.team_display_name),

        division: normalizeKey(transaction.division),
        region: cleanText(transaction.region),

        transactions: []
      });
    }

    const group = groups.get(groupKey);

    group.transactions.push(transaction);

    if (Date.parse(transaction.created_at_utc || "") > Date.parse(group.created_at_utc || "")) {
      group.created_at_utc = cleanText(transaction.created_at_utc);
    }

    if (!group.division && transaction.division) {
      group.division = normalizeKey(transaction.division);
    }

    if (!group.region && transaction.region) {
      group.region = cleanText(transaction.region);
    }
  });

  return [...groups.values()]
    .map(group => {
      group.transactions.sort((a, b) => {
        return Date.parse(b.created_at_utc || "") - Date.parse(a.created_at_utc || "");
      });

      return group;
    })
    .sort((a, b) => {
      return Date.parse(b.created_at_utc || "") - Date.parse(a.created_at_utc || "");
    });
}

function getDivisionLabel(division) {
  const key = normalizeKey(division);
  return DIVISION_LABELS[key] || cleanText(division) || "Unknown Division";
}

function getDivisionRegion(division) {
  const key = normalizeKey(division);
  return DIVISION_REGIONS[key] || "";
}

function getDivisionShield(division) {
  const key = normalizeKey(division);
  return DIVISION_SHIELDS[key] || "";
}

function getTeamMeta(teamId) {
  const key = normalizeKey(teamId);

  return teamMetadata[key]
    || teamMetadata[teamId]
    || {};
}

function getTeamLogo(teamId) {
  const meta = getTeamMeta(teamId);

  return cleanText(
    meta.logo
    || meta.logo_url
    || meta.logo_path
    || meta.image
    || meta.image_path
    || ""
  );
}

function getTeamPrimary(teamId) {
  const meta = getTeamMeta(teamId);

  return cleanText(
    meta.primary
    || meta.primary_color
    || meta.colors?.primary
    || meta.theme?.primary
    || "#00d1d1"
  );
}

function getTeamSecondary(teamId) {
  const meta = getTeamMeta(teamId);

  return cleanText(
    meta.secondary
    || meta.secondary_color
    || meta.colors?.secondary
    || meta.theme?.secondary
    || "#ffffff"
  );
}

function getTeamDisplayName(group) {
  const meta = getTeamMeta(group.team_id);

  return cleanText(
    group.team_display_name
    || meta.display_name
    || meta.team_display_name
    || meta.name
    || group.team_id
    || "Unknown Team"
  );
}

function formatDate(value) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return cleanText(value);
  }

  return date.toLocaleDateString(undefined, {
    month: "long",
    day: "numeric",
    year: "numeric"
  });
}

function getTransactionType(transaction) {
  return cleanText(transaction.type).toLowerCase();
}

function getTransactionSymbol(transaction) {
  const type = getTransactionType(transaction);

  if (type === "add") return "+";
  if (type === "remove") return "−";

  return "•";
}

function getPlayerName(transaction) {
  return cleanText(
    transaction.player_display_name
    || transaction.player_name
    || transaction.player_id
    || "Unknown Player"
  );
}

function getPlayerMeta(transaction) {
  const pieces = [];

  if (cleanText(transaction.jersey_number)) {
    pieces.push(`#${transaction.jersey_number}`);
  }

  if (cleanText(transaction.slap_id)) {
    pieces.push(`Slap ID ${transaction.slap_id}`);
  }

  return pieces.join(" · ");
}

function getGroupCounts(group) {
  let adds = 0;
  let removes = 0;
  let other = 0;

  group.transactions.forEach(transaction => {
    const type = getTransactionType(transaction);

    if (type === "add") {
      adds += 1;
    } else if (type === "remove") {
      removes += 1;
    } else {
      other += 1;
    }
  });

  return { adds, removes, other };
}

function renderRegionFilters() {
  const container = document.querySelector("#regionFilters");

  if (!container) return;

  const regions = ["all", "East", "Central", "West"];

  container.innerHTML = regions.map(region => {
    const value = normalizeKey(region);
    const label = region === "all" ? "All Regions" : region;

    return `
      <button
        type="button"
        class="filter-button ${normalizeKey(activeRegion) === value ? "is-active" : ""}"
        onclick="setRegionFilter('${escapeAttr(region)}')"
      >
        ${escapeHtml(label)}
      </button>
    `;
  }).join("");
}

function renderDivisionFilters() {
  const container = document.querySelector("#divisionFilters");

  if (!container) return;

  const divisionKeys = Object.keys(DIVISION_LABELS);

  container.innerHTML = [
    `
      <button
        type="button"
        class="filter-button ${activeDivision === "all" ? "is-active" : ""}"
        onclick="setDivisionFilter('all')"
      >
        All Divisions
      </button>
    `,
    ...divisionKeys.map(key => {
      const shield = getDivisionShield(key);
      const region = getDivisionRegion(key);
      const hiddenByRegion = activeRegion !== "all"
        && normalizeKey(region) !== normalizeKey(activeRegion);

      if (hiddenByRegion) {
        return "";
      }

      return `
        <button
          type="button"
          class="filter-button ${activeDivision === key ? "is-active" : ""}"
          onclick="setDivisionFilter('${escapeAttr(key)}')"
        >
          ${shield ? `<img src="${escapeAttr(shield)}" alt="">` : ""}
          ${escapeHtml(getDivisionLabel(key))}
        </button>
      `;
    })
  ].join("");
}

function setRegionFilter(region) {
  activeRegion = region;
  activeDivision = "all";
  visibleCount = PAGE_SIZE;

  applyFilters();
}

function setDivisionFilter(division) {
  activeDivision = division;
  visibleCount = PAGE_SIZE;

  applyFilters();
}

function groupMatchesFilters(group) {
  const division = normalizeKey(group.division);
  const region = normalizeKey(group.region || getDivisionRegion(division));

  if (activeRegion !== "all" && region !== normalizeKey(activeRegion)) {
    return false;
  }

  if (activeDivision !== "all" && division !== normalizeKey(activeDivision)) {
    return false;
  }

  return true;
}

function applyFilters() {
  filteredGroups = allGroups.filter(groupMatchesFilters);

  renderRegionFilters();
  renderDivisionFilters();
  renderTimeline();
}

function renderTransactionLine(transaction) {
  const type = getTransactionType(transaction);
  const symbol = getTransactionSymbol(transaction);
  const name = getPlayerName(transaction);
  const meta = getPlayerMeta(transaction);

  const lineClass = type === "add"
    ? "add"
    : type === "remove"
      ? "remove"
      : "other";

  return `
    <div class="roster-wire-player-line ${lineClass}">
      <span class="roster-wire-symbol">${symbol}</span>
      <span>
        ${escapeHtml(name)}
        ${meta ? `<span class="roster-wire-player-meta"> ${escapeHtml(meta)}</span>` : ""}
      </span>
    </div>
  `;
}

function renderTimelineRow(group, index) {
  const teamName = getTeamDisplayName(group);
  const teamLogo = getTeamLogo(group.team_id);
  const primary = getTeamPrimary(group.team_id);
  const secondary = getTeamSecondary(group.team_id);
  const divisionLabel = getDivisionLabel(group.division);
  const divisionShield = getDivisionShield(group.division);
  const region = cleanText(group.region || getDivisionRegion(group.division));
  const counts = getGroupCounts(group);

  return `
    <a
      class="roster-wire-row"
      href="${escapeAttr(group.press_release_url)}"
      style="--team-primary: ${escapeAttr(primary)}; --team-secondary: ${escapeAttr(secondary)};"
    >
      <div class="roster-wire-dot"></div>

      <article class="roster-wire-card">
        <div class="roster-wire-top">
          <div class="roster-wire-team">
            ${
              teamLogo
                ? `<img class="roster-wire-team-logo" src="${escapeAttr(teamLogo)}" alt="">`
                : `<div class="roster-wire-team-logo"></div>`
            }

            <div class="roster-wire-team-text">
              <strong>${escapeHtml(teamName)}</strong>
              <span class="roster-wire-date">${escapeHtml(formatDate(group.created_at_utc))}</span>
            </div>
          </div>

          <div class="roster-wire-division">
            <span>
              ${escapeHtml(divisionLabel)}
              ${region ? `<br>${escapeHtml(region)}` : ""}
            </span>
            ${divisionShield ? `<img src="${escapeAttr(divisionShield)}" alt="">` : ""}
          </div>
        </div>

        <div class="roster-wire-lines">
          ${group.transactions.map(renderTransactionLine).join("")}
        </div>

        <div class="roster-wire-summary">
          ${counts.adds ? `<span class="roster-wire-pill">+${counts.adds} Add${counts.adds === 1 ? "" : "s"}</span>` : ""}
          ${counts.removes ? `<span class="roster-wire-pill">−${counts.removes} Drop${counts.removes === 1 ? "" : "s"}</span>` : ""}
          ${counts.other ? `<span class="roster-wire-pill">${counts.other} Move${counts.other === 1 ? "" : "s"}</span>` : ""}
          <span class="roster-wire-pill">View Release</span>
        </div>

        <div class="roster-wire-ghost-number">${String(index + 1).padStart(2, "0")}</div>
      </article>
    </a>
  `;
}

function renderTimeline() {
  const container = document.querySelector("#rosterWireTimeline");

  if (!container) return;

  const visibleGroups = filteredGroups.slice(0, visibleCount);

  if (!visibleGroups.length) {
    container.innerHTML = `
      <div class="roster-wire-empty">
        No roster transactions match these filters.
      </div>
    `;
    return;
  }

  container.innerHTML = visibleGroups
    .map((group, index) => renderTimelineRow(group, index))
    .join("");

  if (visibleCount < filteredGroups.length) {
    container.insertAdjacentHTML(
      "beforeend",
      `<div class="roster-wire-loading">Scroll for more roster moves...</div>`
    );
  } else {
    container.insertAdjacentHTML(
      "beforeend",
      `<div class="roster-wire-end">End of roster wire.</div>`
    );
  }
}

function loadMoreGroups() {
  if (visibleCount >= filteredGroups.length) return;

  visibleCount += PAGE_SIZE;
  renderTimeline();
}

function setupInfiniteScroll() {
  const sentinel = document.querySelector("#rosterWireSentinel");

  if (!sentinel) return;

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        loadMoreGroups();
      }
    });
  }, {
    rootMargin: "600px"
  });

  observer.observe(sentinel);
}

function padCountdownValue(value) {
  return String(value).padStart(2, "0");
}

function setCountdownText(id, value) {
  const element = document.querySelector(id);

  if (!element) return;

  element.textContent = value;
}

function updateRosterLockCountdown() {
  const countdown = document.querySelector("#rosterLockCountdown");

  if (!countdown) return;

  const lockTime = new Date(ROSTER_LOCK_AT).getTime();
  const now = Date.now();
  const remaining = lockTime - now;

  if (remaining <= 0) {
    countdown.classList.add("is-locked");

    setCountdownText("#rosterLockDays", "00");
    setCountdownText("#rosterLockHours", "00");
    setCountdownText("#rosterLockMinutes", "00");
    setCountdownText("#rosterLockSeconds", "00");

    const label = countdown.querySelector(".roster-lock-label");
    const date = countdown.querySelector(".roster-lock-date");

    if (label) {
      label.textContent = "Roster Lock Active";
    }

    if (date) {
      date.textContent = "Rosters locked Sunday, July 26 at 11:59 PM Eastern";
    }

    return;
  }

  const totalSeconds = Math.floor(remaining / 1000);

  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  setCountdownText("#rosterLockDays", padCountdownValue(days));
  setCountdownText("#rosterLockHours", padCountdownValue(hours));
  setCountdownText("#rosterLockMinutes", padCountdownValue(minutes));
  setCountdownText("#rosterLockSeconds", padCountdownValue(seconds));
}

function startRosterLockCountdown() {
  updateRosterLockCountdown();
  window.setInterval(updateRosterLockCountdown, 1000);
}

async function loadRosterWire() {
  const [transactionData, metadataData] = await Promise.all([
    fetchJsonOrFallback(DATA_PATHS.transactions, { transactions: [] }),
    fetchJsonOrFallback(DATA_PATHS.teamMetadata, {})
  ]);

  allTransactions = getTransactions(transactionData);
  teamMetadata = getTeamMetadataMap(metadataData);

  allGroups = groupTransactions(allTransactions);
  filteredGroups = allGroups;

  renderRegionFilters();
  renderDivisionFilters();
  renderTimeline();
  setupInfiniteScroll();
}

startRosterLockCountdown();
loadRosterWire();