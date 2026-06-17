let franchisePlayers = [];
let teamRecordMap = {};

let currentSort = "points";
let sortDescending = true;

function getFranchiseIdFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get("id");
}

async function loadFranchise() {
    const id = getFranchiseIdFromUrl();

     const [
        metaRes,
        statsRes,
        recordsRes,
        championshipsResponse
    ] = await Promise.all([
        fetch("data/franchises.json"),
        fetch("data/franchise_stats.json"),
        fetch("data/team_records.json"),
        fetch("data/championships.json")
    ]);

    const meta = await metaRes.json();
    const stats = await statsRes.json();
    const teamRecords =
        await recordsRes.json();
    const championships = await championshipsResponse.json();

    teamRecordMap = {};

    teamRecords.forEach(record => {

        teamRecordMap[record.team] = record;

        const normalized =
            record.team.replace(
                /\s*\([^)]*\)$/,
                ""
            );

        teamRecordMap[normalized] = record;
    });    

    const metaFranchise = meta.find(f => f.franchise_id === id);
    const statsFranchise = stats.find(f => f.franchise_id === id);

    const playersRes =
    await fetch("data/all_time_players.json");

    const allPlayers =
        await playersRes.json();

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

    renderFranchisePlayerStats(
        franchise,
        allPlayers
    );

    renderFranchiseChampionships(franchise, championships);
}

function getFranchiseChampionships(franchise, championships = []) {
  const franchiseId = String(franchise.franchise_id || "").trim();

  return championships.filter(champ =>
    String(champ.winner_franchise_id || "").trim() === franchiseId
  );
}

function getChampionshipClass(championship) {
  const cup = String(championship || "").toLowerCase();

  if (cup.includes("erveon")) return "champ-east";
  if (cup.includes("gazz")) return "champ-central";
  if (cup.includes("pacific")) return "champ-west";

  return "";
}

function getFranchiseChampionshipCounts(franchiseChamps) {
  const counts = {
    total: franchiseChamps.length,
    east: 0,
    central: 0,
    west: 0
  };

  franchiseChamps.forEach(champ => {
    const region = String(champ.region || "").toLowerCase();

    if (region === "east") counts.east += 1;
    if (region === "central") counts.central += 1;
    if (region === "west") counts.west += 1;
  });

  return counts;
}

function renderFranchiseChampionships(franchise, championships = []) {
  const card = document.querySelector("#franchiseChampionshipsCard");
  const container = document.querySelector("#franchiseChampionships");
  const countsContainer = document.querySelector("#franchiseChampionshipCounts");

  if (!card || !container) return;

  const franchiseChamps = getFranchiseChampionships(franchise, championships);

  if (!franchiseChamps.length) {
    card.style.display = "none";
    container.innerHTML = "";
    container.classList.remove("championship-carousel-centered");

    if (countsContainer) {
      countsContainer.innerHTML = "";
    }

    return;
  }

  card.style.display = "";

  container.classList.toggle(
    "championship-carousel-centered",
    franchiseChamps.length <= 4
  );

  const counts = getFranchiseChampionshipCounts(franchiseChamps);

  container.innerHTML = franchiseChamps.map(champ => {
    const champClass = getChampionshipClass(champ.championship);

    return `
      <div class="championship-card ${champClass}">
        <div class="championship-ring">🏆</div>

        <div class="championship-season">
          ${champ.season}
        </div>

        <div class="championship-card-main">
          <div class="championship-title">
            ${champ.championship}
          </div>

          <div class="championship-team">
            ${champ.winner_team}
          </div>

          <div class="championship-series">
            def. ${champ.runner_up_team}
            ${champ.series_result ? `(${champ.series_result})` : ""}
          </div>
        </div>

        <div class="championship-qualifier">
          ${champ.championship_roster?.length || 0} Qualified Players
        </div>
      </div>
    `;
  }).join("");

  if (countsContainer) {
    countsContainer.innerHTML = `
      <div class="championship-count championship-count-total">
        <span>Total</span>
        <strong>${counts.total}</strong>
      </div>

      <div class="championship-count champ-east">
        <span>East</span>
        <strong>${counts.east}</strong>
      </div>

      <div class="championship-count champ-central">
        <span>Central</span>
        <strong>${counts.central}</strong>
      </div>

      <div class="championship-count champ-west">
        <span>West</span>
        <strong>${counts.west}</strong>
      </div>
    `;
  }
}

function seasonValue(seasonId) {
    if (!seasonId) return 0;

    const SEASON_ORDER = {
        winter: 1,
        spring: 2,
        summer: 3,
        fall: 4
    };

    const [season, year] =
        seasonId.toLowerCase().split("_");

    return (
        Number(year) * 10 +
        (SEASON_ORDER[season] || 0)
    );
}

function seasonInRange(
    seasonId,
    startSeason,
    endSeason
) {
    const value = seasonValue(seasonId);

    const start = seasonValue(startSeason);

    const end =
        endSeason
            ? seasonValue(endSeason)
            : 999999;

    return value >= start &&
           value <= end;
}

function rowBelongsToFranchise(
    row,
    franchise
) {
    return franchise.memberships.some(
        membership => {

            if (
                membership.team !== row.team
            ) {
                return false;
            }

            return seasonInRange(
                row.season_id,
                membership.start_season,
                membership.end_season
            );
        }
    );
}

function buildFranchisePlayers(
    franchise,
    allPlayers
) {
    const players = {};

    allPlayers.forEach(player => {

        player.by_season.forEach(row => {

            if (
                !rowBelongsToFranchise(
                    row,
                    franchise
                )
            ) {
                return;
            }

            const name =
                player.player_name;

            if (!players[name]) {
                players[name] = {
                    player_name: name,

                    games_played: 0,
                    periods_played: 0,

                    goals: 0,
                    assists: 0,
                    points: 0,

                    shots: 0,
                    saves: 0,

                    faceoffs_won: 0,
                    faceoffs_lost: 0,

                    takeaways: 0,
                    turnovers: 0,

                    post_hits: 0,
                    passes: 0,
                    blocks: 0,

                    possession_time_sec: 0,

                    seasons: new Set()
                };
            }

            const stats =
                row.stats || {};

            players[name].games_played +=
                stats.games_played || 0;

            players[name].goals +=
                stats.goals || 0;

            players[name].assists +=
                stats.assists || 0;

            players[name].points +=
                stats.points || 0;

            players[name].shots +=
                stats.shots || 0;

            players[name].saves +=
                stats.saves || 0;

            players[name].takeaways +=
                stats.takeaways || 0;

            players[name].blocks +=
                stats.blocks || 0;

            players[name].periods_played +=
                stats.periods_played || 0;

            players[name].faceoffs_won +=
                stats.faceoffs_won || 0;

            players[name].faceoffs_lost +=
                stats.faceoffs_lost || 0;

            players[name].turnovers +=
                stats.turnovers || 0;

            players[name].post_hits +=
                stats.post_hits || 0;

            players[name].passes +=
                stats.passes || 0;

            players[name].possession_time_sec +=
                stats.possession_time_sec || 0;

            players[name].seasons.add(
                row.season_id
            );
        });
    });

    const result =
        Object.values(players);

    result.forEach(player => {
        player.seasons_played =
            player.seasons.size;
    });

    return result.sort(
        (a, b) =>
            b.points - a.points
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

function renderFranchiseTable() {

    const rows =
        [...franchisePlayers]
        .sort((a, b) => {

            const aVal =
                a[currentSort] ?? 0;

            const bVal =
                b[currentSort] ?? 0;

            return sortDescending
                ? bVal - aVal
                : aVal - bVal;
        });

    const tbody =
        document.querySelector(
            "#franchisePlayerTable tbody"
        );

    tbody.innerHTML =
    rows.map((p, index) => `
        <tr>
            <td>${index + 1}</td>

            <td>
                <a href="player.html?id=${encodeURIComponent(
                    p.player_name.toLowerCase()
                )}">
                    ${p.player_name}
                </a>
            </td>

            <td>${p.games_played}</td>
            <td>${p.periods_played}</td>
            <td>${p.seasons_played}</td>

            <td>${p.goals}</td>
            <td>${p.assists}</td>
            <td>${p.points}</td>
            <td>${p.shots}</td>
            <td>${p.saves}</td>
            <td>${p.blocks}</td>

            <td>${p.faceoffs_won}</td>
            <td>${p.faceoffs_lost}</td>

            <td>${p.takeaways}</td>
            <td>${p.turnovers}</td>

            <td>${p.post_hits}</td>
            <td>${p.passes}</td>

            <td>${formatTime(
                p.possession_time_sec
            )}</td>
        </tr>
    `).join("");
}

function setupFranchiseSorting() {

    document
        .querySelectorAll(
            "#franchisePlayerTable th[data-sort]"
        )
        .forEach(th => {

            th.addEventListener(
                "click",
                () => {

                    const stat =
                        th.dataset.sort;

                    if (
                        currentSort === stat
                    ) {
                        sortDescending =
                            !sortDescending;
                    }
                    else {
                        currentSort = stat;
                        sortDescending = true;
                    }

                    renderFranchiseTable();
                }
            );
        });
}

function renderFranchisePlayerStats(
    franchise,
    allPlayers
) {
    franchisePlayers =
        buildFranchisePlayers(
            franchise,
            allPlayers
        );

    renderFranchiseStats(
        franchise,
        franchisePlayers
    );

    renderFranchiseTable();
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

function renderFranchise(franchise, championships =[]) {
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
    renderTeams(
        franchise.memberships,
        teamRecordMap
    );
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

function renderTeams(
    memberships,
    teamRecordMap
) {

    const sorted =
        [...memberships].sort(
            (a, b) =>
                (a.order || 999)
                - (b.order || 999)
        );

    document.querySelector(
        "#franchiseTeams"
    ).innerHTML = sorted.map(m => {

        const record =
            teamRecordMap[m.team]
            || teamRecordMap[
                m.team.replace(
                    /\s*\([^)]*\)$/,
                    ""
                )
            ]
            || {};

        const wins =
            record.wins ?? 0;

        const losses =
            record.losses ?? 0;

        const gd =
            record.goal_differential ?? 0;

        const winPct =
            ((record.win_percent ?? 0) * 100)
                .toFixed(1);

        return `
            <a
                class="team-hub-card franchise-team-card"
                href="team.html?team=${encodeURIComponent(
                    m.team
                )}"
            >

                <div class="franchise-team-name">
                    ${m.team}
                </div>

                <div class="franchise-team-record">
                    ${wins}-${losses}
                </div>

                <div class="franchise-team-winpct">
                    ( ${winPct}% )
                </div>

                <div class="franchise-team-gd">
                    ${gd >= 0 ? "+" : ""}${gd} GD
                </div>

                <div class="franchise-team-spacer"></div>

                <div class="franchise-team-years">
                    ${formatSeason(
                        m.start_season
                    )}
                    →
                    ${
                        m.end_season
                            ? formatSeason(
                                m.end_season
                            )
                            : "Present"
                    }
                </div>

            </a>
        `;

    }).join("");
}



// Franchise Stat Section

function calculateFranchisePlayerTotals(players) {
  const totals = {
    games_played: 0,
    goals: 0,
    assists: 0,
    points: 0,
    shots: 0,
    saves: 0,
    blocks: 0
  };

  for (const player of players || []) {
    totals.games_played += Number(player.stats?.games_played || 0);
    totals.goals += Number(player.stats?.goals || 0);
    totals.assists += Number(player.stats?.assists || 0);
    totals.points += Number(player.stats?.points || 0);
    totals.shots += Number(player.stats?.shots || 0);
    totals.saves += Number(player.stats?.saves || 0);
    totals.blocks += Number(player.stats?.blocks || 0);
  }

  return totals;
}

function renderFranchiseStats(franchise) {
  const container = document.querySelector("#franchiseStats");

  if (!container) return;

  const teamTotals = franchise.team_totals || {};

  const career =
    franchise.stats?.all_divisions?.career || {};

  const franchiseStats = [
    ["Games Played", teamTotals.games_played ?? 0],
    ["Wins", teamTotals.wins ?? 0],
    ["Losses", teamTotals.losses ?? 0],
    ["Goals For", teamTotals.goals_for ?? 0],
    ["Goals Against", teamTotals.goals_against ?? 0]
  ];

  const playerStats = [
    ["Man Games", career.games_played ?? 0],
    ["Goals", career.goals ?? 0],
    ["Assists", career.assists ?? 0],
    ["Points", career.points ?? 0],
    ["Shots", career.shots ?? 0],
    ["Saves", career.saves ?? 0],
    ["Blocks", career.blocks ?? 0]
  ];

  const renderCard = ([label, value]) => `
    <div class="stat-box">
      <span>${label}</span>
      <strong>${value ?? 0}</strong>
    </div>
  `;

  container.innerHTML = `
    <div class="franchise-stat-row franchise-record-row">
      ${franchiseStats.map(renderCard).join("")}
    </div>

    <div class="franchise-stat-row franchise-player-total-row">
      ${playerStats.map(renderCard).join("")}
    </div>
  `;
}

// end Franchise Stat Section





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

setupFranchiseSorting();
loadFranchise();