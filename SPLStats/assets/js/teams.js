let teams = [];
let teamRecords = {};
let franchises = [];

const searchInput = document.querySelector("#teamSearch");
const results = document.querySelector("#teamResults");

async function loadTeams() {
  const [
    teamsResponse,
    recordsResponse,
    franchisesResponse
  ] = await Promise.all([
    fetch("data/teams.json"),
    fetch("data/team_records.json"),
    fetch("data/franchises.json")
  ]);

  teams = await teamsResponse.json();
  const records = await recordsResponse.json();
  franchises = await franchisesResponse.json();

  teamRecords = {};

  records.forEach(record => {
    teamRecords[cleanTeamName(record.team)] = record;
  });

  renderTeams();
}

function cleanTeamName(teamName) {
  return String(teamName)
    .replace(/\s*\([^)]*\)$/, "")
    .trim()
    .toLowerCase();
}

function findFranchiseForTeam(teamName, franchises) {
  const teamKey = cleanTeamName(teamName);

  for (const franchise of franchises) {
    const membership = (franchise.memberships || []).find(m =>
      cleanTeamName(m.team) === teamKey
    );

    if (membership) {
      return {
        franchise,
        membership
      };
    }
  }

  return null;
}

function renderTeams() {
  const query = searchInput.value.toLowerCase().trim();

  const filtered = teams
    .filter(team =>
      query === "" ||
      team.team_name.toLowerCase().includes(query)
    )
    .sort((a, b) => {
      const aRecord = teamRecords[cleanTeamName(a.team_name)] || {};
      const bRecord = teamRecords[cleanTeamName(b.team_name)] || {};

      return (
        (bRecord.wins || 0)
        - (aRecord.wins || 0)
      );
    });

  results.innerHTML = filtered.map(team => {
    const record =
      teamRecords[cleanTeamName(team.team_name)] || {};

    const franchiseResult =
      findFranchiseForTeam(team.team_name, franchises);

    const franchise =
      franchiseResult?.franchise || null;

    const theme =
      franchise?.theme || {};

    const isFranchiseTeam =
      Boolean(franchise);

    const logoHTML =
      franchise?.logo
        ? `
          <img
            class="team-hub-logo-bg"
            src="${franchise.logo}"
            alt=""
            aria-hidden="true"
          >
        `
        : "";

    return `
      <a
        class="team-hub-card ${isFranchiseTeam ? "franchise-linked-team" : ""}"
        href="team.html?team=${encodeURIComponent(team.team_name)}"
        style="
          --franchise-primary: ${theme.primary || "#00b3b3"};
          --franchise-secondary: ${theme.secondary || "#ffffff"};
          --franchise-accent: ${theme.accent || "#ffd166"};
          --franchise-background: ${theme.background || "#050505"};
          --franchise-card: ${theme.card || "#0c141c"};
          --franchise-surface: ${theme.surface || "#111"};
        "
      >
        ${logoHTML}

        <div class="team-hub-card-content">
          <h2>${team.team_name}</h2>

          <div class="team-hub-bottom">
            ${
              franchise
                ? `<div class="team-franchise-pill">${franchise.franchise_name}</div>`
                : ""
            }

            <div class="team-hub-record">
              ${record.wins ?? 0}-${record.losses ?? 0}
            </div>

            <div class="team-hub-substats">
              ${record.games_played ?? 0} GP ·
              ${record.goals_for ?? 0} GF ·
              ${record.goals_against ?? 0} GA
            </div>

            <small>
              ${(team.seasons || []).length} Seasons
            </small>
          </div>
        </div>
      </a>
    `;
  }).join("");
}

searchInput.addEventListener("input", renderTeams);

loadTeams();