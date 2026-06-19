const SEASON_ORDER = {
  winter: 1,
  spring: 2,
  summer: 3,
  fall: 4
};

function seasonValue(seasonIdOrName) {
  const text = String(seasonIdOrName || "").trim().toLowerCase();

  let match = text.match(/^([a-z]+)_(\d{4})$/);

  if (match) {
    const season = match[1];
    const year = Number(match[2]);

    return year * 10 + (SEASON_ORDER[season] || 0);
  }

  match = text.match(/^([a-z]+)\s+(\d{4})$/);

  if (match) {
    const season = match[1];
    const year = Number(match[2]);

    return year * 10 + (SEASON_ORDER[season] || 0);
  }

  return 0;
}

function getRegionKey(region) {
  const text = String(region || "").trim().toLowerCase();

  if (text === "east") return "east";
  if (text === "central") return "central";
  if (text === "west") return "west";

  return null;
}

function getChampionshipClass(championship) {
  const cup = String(championship || "").toLowerCase();

  if (cup.includes("erveon")) return "champ-east";
  if (cup.includes("gazz")) return "champ-central";
  if (cup.includes("pacific")) return "champ-west";

  return "";
}

function renderChampionCell(champ) {
  if (!champ) {
    return `<span class="champion-empty">—</span>`;
  }

  const champClass = getChampionshipClass(champ.championship);
  const team = champ.winner_team || "Unknown Champion";
  const runnerUp = champ.runner_up_team || "";
  const result = champ.series_result || "";
  const cup = champ.championship || "";

  const teamLink = champ.winner_team
    ? `team.html?team=${encodeURIComponent(champ.winner_team)}`
    : null;

  const franchiseLink = champ.winner_franchise_id
    ? `franchise.html?id=${encodeURIComponent(champ.winner_franchise_id)}`
    : null;

  return `
    <div class="champion-cell ${champClass}">
      <div class="champion-cup">${cup}</div>

      ${
        teamLink
          ? `
            <a href="${teamLink}" class="champion-team">
              ${team}
            </a>
          `
          : `
            <span class="champion-team">
              ${team}
            </span>
          `
      }

      ${
        franchiseLink
          ? `
            <div class="champion-franchise-link">
              <a href="${franchiseLink}">View Franchise</a>
            </div>
          `
          : ""
      }

      ${
        runnerUp
          ? `
            <div class="champion-runner-up">
              def. ${runnerUp}${result ? ` (${result})` : ""}
            </div>
          `
          : ""
      }
    </div>
  `;
}

async function loadChampionshipHistory() {
  const tbody = document.querySelector("#championshipHistoryTable tbody");
  if (!tbody) return;

  try {
    const response = await fetch("data/championships.json");

    if (!response.ok) {
      throw new Error(`Could not load championships.json: ${response.status}`);
    }

    const championships = await response.json();
    const seasons = new Map();

    championships.forEach(champ => {
      const seasonLabel =
        champ.season
        || champ.season_id
        || "Unknown Season";

      const seasonId =
        champ.season_id
        || seasonLabel;

      const regionKey = getRegionKey(champ.region);

      if (!regionKey) return;

      if (!seasons.has(seasonLabel)) {
        seasons.set(seasonLabel, {
          season: seasonLabel,
          season_id: seasonId,
          east: null,
          central: null,
          west: null
        });
      }

      seasons.get(seasonLabel)[regionKey] = champ;
    });

    const rows = [...seasons.values()].sort((a, b) =>
      seasonValue(b.season_id || b.season) -
      seasonValue(a.season_id || a.season)
    );

    if (!rows.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="4">No championship history listed yet.</td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = rows.map(row => `
      <tr>
        <td class="season-cell">${row.season}</td>
        <td>${renderChampionCell(row.east)}</td>
        <td>${renderChampionCell(row.central)}</td>
        <td>${renderChampionCell(row.west)}</td>
      </tr>
    `).join("");

  } catch (error) {
    console.error(error);

    tbody.innerHTML = `
      <tr>
        <td colspan="4">Could not load championship history.</td>
      </tr>
    `;
  }
}

loadChampionshipHistory();