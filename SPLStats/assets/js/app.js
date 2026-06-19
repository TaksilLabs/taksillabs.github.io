let players = [];
let sortKey = "games_played";
let sortDirection = "desc";
let activeRegion = "all";
let activeSeasonType = "regular_season";
let activeDivision = "all";

const tbody = document.querySelector("#leaderboard tbody");
const searchInput = document.querySelector("#searchInput");

const PLAYER_TABLE_COLUMNS = [
  "seasons_played",
  "games_played",
  "periods_played",

  "goals",
  "assists",
  "points",
  "shots",

  "save_percent",
  "gaa",
  "saves",
  "blocks",

  "shots_against",
  "goals_against",

  "takeaways",
  "turnovers",

  "faceoff_win_percent",
  "faceoffs_won",
  "faceoffs_lost",

  "post_hits",
  "passes",
  "possession_time_sec"
];

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

function formatLeaderboardStat(value, statKey) {
  value = Number(value || 0);

  if (statKey === "save_percent") {
    return value
      ? (value / 100).toFixed(3).replace(/^0/, "")
      : ".000";
  }

  if (statKey === "gaa") {
    return value
      ? value.toFixed(2)
      : "0.00";
  }

  if (statKey === "faceoff_win_percent") {
    return value
      ? `${value.toFixed(1)}%`
      : "0.0%";
  }

  if (statKey === "possession_time_sec") {
    return formatTime(value);
  }

  return Math.round(value || 0);
}

const DIVISION_GROUPS = {
  east: ["pro", "challenger", "intermediate", "prospect", "open"],
  central: ["central a", "central b", "central c", "central d"],
  west: ["masters", "contenders"]
};

const DIVISION_LABELS = {
  pro: "Pro",
  challenger: "Challenger",
  intermediate: "Intermediate",
  prospect: "Prospect",
  open: "Open",
  "central a": "Central A",
  "central b": "Central B",
  "central c": "Central C",
  "central d": "Central D",
  masters: "Masters",
  contenders: "Contenders"
};

function divisionBelongsToTier(division, tier) {
  if (!tier || tier === "all") return true;

  const text = String(division || "").toLowerCase();

  const tierPatterns = {

    // EAST REGION
    pro: [
      "pro division",
      "pro playoffs",
      "erveon"
    ],

    challenger: [
      "challenger",
      "blade",
      "pro play-in",
      "pro promotional"
    ],

    intermediate: [
      "intermediate",
      "im cross-play",
      "challenger promotional",
      "minor league"
    ],

    prospect: [
      "prospect"
    ],

    open: [
      "open",
      "intermediate promotional",
      "genesis"
    ],

      // CENTRAL REGION
    "central a": [
      "central a",
      "gazz"
    ],

    "central b": [
      "central b",
      "b bowl"
    ],

    "central c": [
      "central c"
    ],

    "central d": [
      "central d"
    ],

      // WEST REGION
    masters: [
      "masters",
      "pacific cup",
      "west division"
    ],

    contenders: [
      "contenders",
      "bome cup"
    ]
  };

  return (tierPatterns[tier] || []).some(pattern =>
    text.includes(pattern)
  );
}

async function loadData() {
  const response = await fetch("data/all_time_players.json");
  players = await response.json();
  renderTable();
}

function buildFilteredCareer(player) {
  const rows = player.by_season || [];
  const career = {};
  const seasonsPlayed = new Set();

  rows.forEach(row => {
    const type = row.season_type || "regular_season";

    if (activeSeasonType !== "combined" && type !== activeSeasonType) {
      return;
    }

    if (activeSeasonType === "combined" && type === "preseason") {
      return;
    }

    if (!divisionBelongsToRegion(row.division || "", activeRegion)) {
      return;
    }

    if (!divisionBelongsToTier(row.division || "", activeDivision)) {
      return;
    }

    if (row.season_id || row.season) {
      seasonsPlayed.add(row.season_id || row.season);
    }

    Object.entries(row.stats || {}).forEach(([stat, value]) => {
      const numberValue = Number(value || 0);

      // Skip derived percentage/rate stats.
      // We recalculate them below from raw totals.
      if (
        stat.endsWith("_percent") ||
        stat === "gaa" ||
        stat === "save_percent" ||
        stat === "shot_percent" ||
        stat === "faceoff_win_percent"
      ) {
        return;
      }

      career[stat] = (career[stat] || 0) + numberValue;
    });
  });

  const goals = Number(career.goals || 0);
  const assists = Number(career.assists || 0);
  const shots = Number(career.shots || 0);
  const saves = Number(career.saves || 0);
  const shotsAgainst = Number(career.shots_against || 0);
  const goalsAgainst = Number(career.goals_against || 0);
  const gamesPlayed = Number(career.games_played || 0);
  const faceoffsWon = Number(career.faceoffs_won || 0);
  const faceoffsLost = Number(career.faceoffs_lost || 0);

  career.points = goals + assists;

  career.seasons_played = seasonsPlayed.size;

  career.shot_percent =
    shots ? (goals / shots) * 100 : 0;

  career.save_percent =
    shotsAgainst ? (saves / shotsAgainst) * 100 : 0;

  career.gaa =
    gamesPlayed ? goalsAgainst / gamesPlayed : 0;

  career.faceoffs_total =
    faceoffsWon + faceoffsLost;

  career.faceoff_win_percent =
    career.faceoffs_total
      ? (faceoffsWon / career.faceoffs_total) * 100
      : 0;

  return career;
}

// Set Division Regions
const REGION_PATTERNS = {
  east: [
    "erveon",
    "blade",
    "genesis",
    "pro division",
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
    "pacific",
    "bome",
    "contenders"
  ]
};

function divisionBelongsToRegion(division, region) {
  if (!region || region === "all") return true;

  const patterns = REGION_PATTERNS[region];

  if (!patterns) return true;

  const text = String(division || "").toLowerCase();

  return patterns.some(pattern =>
    text.includes(pattern)
  );
}

function playerInRegion(player, region) {
  if (!region || region === "all") return true;

  const rows = player.by_season || [];

  return rows.some(row =>
    divisionBelongsToRegion(row.division || "", region)
  );
}

function renderDivisionButtons() {
  const container = document.querySelector("#divisionButtons");
  container.innerHTML = "";

  if (activeRegion === "all") {
    activeDivision = "all";
    return;
  }

  const allButton = document.createElement("button");
  allButton.textContent = "All Divisions";
  allButton.dataset.division = "all";
  allButton.classList.add("active");
  container.appendChild(allButton);

  (DIVISION_GROUPS[activeRegion] || []).forEach(tier => {
    const button = document.createElement("button");
    button.textContent = DIVISION_LABELS[tier] || tier;
    button.dataset.division = tier;
    container.appendChild(button);
  });

  container.querySelectorAll("button").forEach(button => {
    button.addEventListener("click", () => {
      activeDivision = button.dataset.division;

      container.querySelectorAll("button").forEach(btn => {
        btn.classList.remove("active");
      });

      button.classList.add("active");

      renderTable();
    });
  });
}

function getStat(player, key) {
  if (key === "player_name") {
    return getPlayerDisplayName(player).toLowerCase();
  }

  const career = buildFilteredCareer(player);
  return career?.[key] ?? 0;
}

function renderTable() {
  console.log("Players loaded:", players.length);
  console.log("Region:", activeRegion);
  console.log("Season Type:", activeSeasonType);
  const search = searchInput.value.toLowerCase();

  let filtered = players.filter(player => {
    const career = buildFilteredCareer(player);

    return (
      [
        player.player_name,
        player.player_display_name,
        player.player_id,
        ...(player.aliases || [])
      ].some(name =>
        String(name || "").toLowerCase().includes(search)
      ) &&
      Object.keys(career).some(key => career[key] > 0)
    );
  });

  console.log("Filtered players:", filtered.length);
  filtered.sort((a, b) => {
    const aVal = getStat(a, sortKey);
    const bVal = getStat(b, sortKey);

    if (typeof aVal === "string") {
      return sortDirection === "asc"
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal);
    }

    return sortDirection === "asc" ? aVal - bVal : bVal - aVal;
  });

  tbody.innerHTML = "";

  filtered.forEach((player, index) => {
    const c = buildFilteredCareer(player);

    const row = document.createElement("tr");

    row.innerHTML = `
      <td>${index + 1}</td>
      <td>
        <a href="player.html?id=${encodeURIComponent(getPlayerUrlId(player))}">
          ${getPlayerDisplayName(player)}
        </a>
      </td>

      ${PLAYER_TABLE_COLUMNS.map(statKey => `
        <td>${formatLeaderboardStat(c[statKey], statKey)}</td>
      `).join("")}
    `;

    tbody.appendChild(row);
  });
}

document.querySelectorAll(".season-type-buttons button").forEach(button => {
  button.addEventListener("click", () => {
    activeSeasonType = button.dataset.seasonType;

    document.querySelectorAll(".season-type-buttons button").forEach(btn => {
      btn.classList.remove("active");
    });

    button.classList.add("active");

    renderTable();
  });
});

document.querySelectorAll(".region-buttons button").forEach(button => {
  button.addEventListener("click", () => {
    activeRegion = button.dataset.region;
    activeDivision = "all";

    document.querySelectorAll(".region-buttons button").forEach(btn => {
      btn.classList.remove("active");
    });

    button.classList.add("active");

    renderDivisionButtons();
    renderTable();
  });
});

document.querySelectorAll("th").forEach(th => {
  th.addEventListener("click", () => {
    const key = th.dataset.stat;
    if (!key || key === "rank") return;

    if (sortKey === key) {
      sortDirection = sortDirection === "asc" ? "desc" : "asc";
    } else {
      sortKey = key;
      sortDirection = key === "player_name" ? "asc" : "desc";
    }

    renderTable();
  });
});

searchInput.addEventListener("input", renderTable);

// Fake Sticky Header for Players.html
let floatingHeader = null;

function setupFloatingLeaderboardHeader() {
  const table = document.querySelector("#leaderboard");
  const tableWrap = document.querySelector(".table-wrap");

  if (!table || !tableWrap || floatingHeader) return;

  floatingHeader = document.createElement("div");
  floatingHeader.className = "floating-leaderboard-header";

  const clonedTable = document.createElement("table");
  const clonedThead = table.querySelector("thead").cloneNode(true);

  clonedTable.appendChild(clonedThead);
  floatingHeader.appendChild(clonedTable);
  document.body.appendChild(floatingHeader);

  function syncFloatingHeader() {
    const tableRect = table.getBoundingClientRect();
    const wrapRect = tableWrap.getBoundingClientRect();
    const thead = table.querySelector("thead");
    const originalHeaders = table.querySelectorAll("thead th");
    const clonedHeaders = floatingHeader.querySelectorAll("th");

    if (!thead || !originalHeaders.length || !clonedHeaders.length) return;

    const headerHeight = thead.getBoundingClientRect().height;
    const shouldShow =
      tableRect.top < 0 &&
      tableRect.bottom > headerHeight;

    floatingHeader.style.display = shouldShow ? "block" : "none";

    if (!shouldShow) return;

    floatingHeader.style.left = `${wrapRect.left}px`;
    floatingHeader.style.width = `${wrapRect.width}px`;

    const clonedTable = floatingHeader.querySelector("table");

    clonedTable.style.width = `${table.offsetWidth}px`;
    clonedTable.style.marginLeft = `${-tableWrap.scrollLeft}px`;

    originalHeaders.forEach((th, index) => {
      const cloned = clonedHeaders[index];
      const width = th.getBoundingClientRect().width;

      cloned.style.width = `${width}px`;
      cloned.style.minWidth = `${width}px`;
      cloned.style.maxWidth = `${width}px`;
      cloned.style.boxSizing = "border-box";
    });
  }

  window.addEventListener("scroll", syncFloatingHeader);
  window.addEventListener("resize", syncFloatingHeader);
  tableWrap.addEventListener("scroll", syncFloatingHeader);

  syncFloatingHeader();
}

renderDivisionButtons();
setupFloatingLeaderboardHeader();
loadData();