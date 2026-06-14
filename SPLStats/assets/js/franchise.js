function getFranchiseIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("id");
}

async function loadFranchise() {
  const id = getFranchiseIdFromUrl();

  const [metaRes, statsRes] = await Promise.all([
    fetch("data/franchises.json"),
    fetch("data/franchise_stats.json")
  ]);

  const meta = await metaRes.json();
  const stats = await statsRes.json();

  const metaFranchise = meta.find(f => f.franchise_id === id);
  const statsFranchise = stats.find(f => f.franchise_id === id);

  if (!metaFranchise && !statsFranchise) {
    document.querySelector("#franchiseName").textContent = "Franchise Not Found";
    return;
  }

  // 🔥 Merge them
  const franchise = {
    ...metaFranchise,
    ...statsFranchise
  };

  renderFranchise(franchise);
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

function renderFranchiseLeaders(franchise) {
  const all = franchise.stats?.all_divisions?.leaders || {};
  const pro = franchise.stats?.pro || {};

  renderLeaderGroup("#leadersAll", all);

  if (pro.has_data) {
    renderLeaderGroup("#leadersPro", pro.leaders || {});
  } else {
    document.querySelector("#franchiseLeadersPro").style.display = "none";
  }
}

function renderLeaderGroup(selector, leaders) {
  const container = document.querySelector(selector);

  container.innerHTML = LEADER_CATEGORIES.map(([label, stat]) => {
    const list = leaders[stat] || [];

    return `
      <div class="leader-card">
        <h3>${label}</h3>

        ${list.map((p, i) => `
          <div class="leader-row">
            <span>
              ${i + 1}.
              <a href="player.html?id=${encodeURIComponent(p.player_name.toLowerCase())}">
                ${p.player_name}
              </a>
            </span>
            <strong>${formatLeaderValue(p.value, stat)}</strong>
          </div>
        `).join("")}
      </div>
    `;
  }).join("");
}

function formatLeaderValue(value, stat) {
  if (value === null || value === undefined) {
    return "—";
  }

  if (stat === "faceoff_percent") {
    return `${Number(value).toFixed(1)}%`;
  }

  return Math.round(Number(value));
}

function renderFranchise(franchise) {
  document.title = `${franchise.franchise_name} | SPLStats`;
  document.querySelector("#franchiseName").textContent = franchise.franchise_name;

  applyFranchiseTheme(franchise.theme);

  function applyFranchiseTheme(theme) {
    if (!theme) return;

    const root = document.documentElement;

    if (theme.primary) {
        root.style.setProperty("--franchise-primary", theme.primary);
    }

    if (theme.secondary) {
        root.style.setProperty("--franchise-secondary", theme.secondary);
    }

    if (theme.accent) {
        root.style.setProperty("--franchise-accent", theme.accent);
    }

    if (theme.background) {
        root.style.setProperty("--franchise-background", theme.background);
    }

    if (theme.card) {
        root.style.setProperty("--franchise-card", theme.card);
    }

    if (theme.surface) {
        root.style.setProperty("--franchise-surface", theme.surface);
    }

    }

    renderFranchiseHeaderStats(franchise);
    renderInfo(franchise);
    renderTeams(franchise.memberships || []);
    renderHallOfFame(franchise.hall_of_fame || []);
    renderFranchiseLeaders(franchise);
}

function renderFranchiseHeaderStats(franchise) {
  const allStats = franchise.stats?.all_divisions || {};

  document.querySelector("#franchiseStatus").textContent =
    franchise.status
      ? franchise.status.toUpperCase()
      : "STATUS UNKNOWN";

  const stats = [
    ["Teams", allStats.teams?.length || 0],
    ["Seasons", allStats.seasons?.length || 0],
    ["Hall of Fame", franchise.hall_of_fame?.length || 0],
    ["Founders", franchise.founders?.length || 0],
    ["Owners", franchise.owners?.length || 0]
  ];

  document.querySelector("#franchiseHeaderStats").innerHTML =
    stats.map(([label, value]) => `
      <div class="stat-box">
        <span>${label}</span>
        <strong>${value}</strong>
      </div>
    `).join("");
}

function renderPeopleCards(title, people) {
  if (!people || !people.length) return "";

  return `
    <div class="franchise-people-section">
      <h3>${title}</h3>
      <div class="franchise-people-grid">
        ${people.map(name => `
          <a class="franchise-person-card"
          href="player.html?id=${encodeURIComponent(name.toLowerCase())}"
          >
            ${name}
          </a>
        `).join("")}
      </div>
    </div>
  `;
}

function renderInfo(franchise) {
  document.querySelector("#franchiseInfo").innerHTML = `
    ${franchise.description ? `<p>${franchise.description}</p>` : ""}

    ${renderPeopleCards("Founders", franchise.founders)}
    ${renderPeopleCards("Owners", franchise.owners)}
    ${renderPeopleCards("Part Owners", franchise.part_owners)}
    ${renderPeopleCards("Coaches", franchise.coaches)}
  `;
}

function formatSeason(seasonId) {
  if (!seasonId) return "";

  const [season, year] = seasonId.split("_");

  return (
    season.charAt(0).toUpperCase() +
    season.slice(1) +
    " " +
    year
  );
}

function renderTeams(memberships) {
  const sorted = [...memberships].sort((a, b) => (a.order || 999) - (b.order || 999));

    document.querySelector("#franchiseTeams").innerHTML = sorted.map(m => `
        <a class="team-hub-card franchise-team-card"
        href="team.html?team=${encodeURIComponent(m.team)}">

        <div class="franchise-team-name">
            ${m.team}
        </div>

        <div class="franchise-team-spacer"></div>

        <div class="franchise-team-years">
            ${formatSeason(m.start_season)}
            →
            ${m.end_season
            ? formatSeason(m.end_season)
            : "Present"}
        </div>

    </a>
    `).join("");
}

function renderHallOfFame(entries) {
  const container = document.querySelector("#franchiseHOF");

  if (!entries.length) {
    container.innerHTML = "No Hall of Fame entries listed.";
    return;
  }

  container.innerHTML = entries.map(entry => `
    <div class="player-card">
        <h3>
            <a href="player.html?id=${encodeURIComponent(entry.player.toLowerCase())}">
                ${entry.player}
            </a>
        </h3>
        <p><strong>Retired Number:</strong> ${entry.retired_number || entry.jno || "N/A"}</p>
        <p><strong>Retired Date:</strong> ${entry.retired_date || "Unknown"}</p>
        <p>${entry.induction_speech || entry.induction_speach || ""}</p>
    </div>
  `).join("");
}

loadFranchise();