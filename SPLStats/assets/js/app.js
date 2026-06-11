let players = [];
let sortKey = "points";
let sortDirection = "desc";
let activeRegion = "all";
let activeSeasonType = "combined";
let activeDivision = "all";

const tbody = document.querySelector("#leaderboard tbody");
const searchInput = document.querySelector("#searchInput");

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
      "underdog cup",
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
      "central b"
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

    Object.entries(row.stats || {}).forEach(([stat, value]) => {
      if (stat.endsWith("_percent")) return;
      career[stat] = (career[stat] || 0) + Number(value || 0);
    });
  });

  career.points = (career.goals || 0) + (career.assists || 0);

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
  if (key === "player_name") return player.player_name || "";

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
      player.player_name.toLowerCase().includes(search) &&
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
      <td><a href="player.html?id=${encodeURIComponent(player.player_name.toLowerCase())}">${player.player_name}</a></td>
      <td>${c.games_played ?? 0}</td>
      <td>${c.goals ?? 0}</td>
      <td>${c.assists ?? 0}</td>
      <td>${c.points ?? 0}</td>
      <td>${c.shots ?? 0}</td>
      <td>${c.saves ?? 0}</td>
      <td>${c.blocks ?? 0}</td>
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

renderDivisionButtons();
loadData();