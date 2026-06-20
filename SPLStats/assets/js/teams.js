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
    const key = getTeamRecordKey(record);
    teamRecords[key] = record;
  });

  renderTeams();
}

function cleanTeamName(teamName) {
  return String(teamName || "")
    .replace(/\s*\([^)]*\)$/, "")
    .trim()
    .toLowerCase();
}

function getTeamRecordKey(team) {
  return (
    team.team_id
    || cleanTeamName(team.team_display_name)
    || cleanTeamName(team.team_name)
    || cleanTeamName(team.team)
    || "unknown_team"
  );
}

function getTeamDisplayName(team) {
  return (
    team.team_display_name
    || team.team_name
    || team.team
    || team.team_id
    || "Unknown Team"
  );
}

function getTeamUrlId(team) {
  return (
    team.team_id
    || team.team_name
    || team.team
    || ""
  );
}

function getTeamLogo(team) {
  return team.logo || "";
}

function getTeamTheme(team) {
  return team.theme || {};
}

function getFranchisePillStyle(franchise) {
  const theme = franchise?.theme || {};

  return `
    --pill-primary: ${theme.primary || "#ff4646"};
    --pill-secondary: ${theme.secondary || "#111111"};
    --pill-accent: ${theme.accent || "#ffffff"};
    --pill-background: ${theme.background || "#050505"};
  `;
}

function getTeamCardStyle(team) {
  const theme = getTeamTheme(team);

  const primary = theme.primary || "#00b3b3";
  const secondary = theme.secondary || "#ffffff";
  const accent = theme.accent || "#ffd166";
  const background = theme.background || "#050505";
  const card = theme.card || "#0c141c";
  const surface = theme.surface || "#111111";

  return `
    --team-primary: ${primary};
    --team-secondary: ${secondary};
    --team-accent: ${accent};
    --team-background: ${background};
    --team-card: ${card};
    --team-surface: ${surface};

    --franchise-primary: ${primary};
    --franchise-secondary: ${secondary};
    --franchise-accent: ${accent};
    --franchise-background: ${background};
    --franchise-card: ${card};
    --franchise-surface: ${surface};
  `;
}

function teamMatchesSearch(team, query) {
  if (!query) return true;

  const fields = [
    team.team_id,
    team.team_name,
    team.team_display_name,
    team.team,
    ...(team.team_aliases || []),
    ...(team.aliases || [])
  ];

  return fields.some(value =>
    String(value || "").toLowerCase().includes(query)
  );
}

function findFranchiseForTeam(team) {
  const teamId = team.team_id;
  const teamKey = cleanTeamName(getTeamDisplayName(team));

  for (const franchise of franchises) {
    const membership = (franchise.memberships || []).find(m => {
      if (m.team_id && teamId && m.team_id === teamId) {
        return true;
      }

      return cleanTeamName(m.team) === teamKey;
    });

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
    .filter(team => teamMatchesSearch(team, query))
    .sort((a, b) => {
      const aRecord = teamRecords[getTeamRecordKey(a)] || {};
      const bRecord = teamRecords[getTeamRecordKey(b)] || {};

      return (
        (bRecord.wins || 0)
        - (aRecord.wins || 0)
      );
    });

  results.innerHTML = filtered.map(team => {
    const displayName = getTeamDisplayName(team);
    const urlId = getTeamUrlId(team);
    const logo = getTeamLogo(team);

    const record =
      teamRecords[getTeamRecordKey(team)] || {};

    const franchiseResult =
      findFranchiseForTeam(team);

    const franchise =
      franchiseResult?.franchise || null;

    const logoHTML =
      logo
        ? `
          <img
            class="team-hub-logo-bg"
            src="${logo}"
            alt=""
            aria-hidden="true"
          >
        `
        : "";

    return `
      <a
        class="team-hub-card ${logo ? "metadata-team-card" : ""}"
        href="team.html?id=${encodeURIComponent(urlId)}&team=${encodeURIComponent(displayName)}"
        style="${getTeamCardStyle(team)}"
      >
        ${logoHTML}

        <div class="team-hub-card-content">
          <h2>${displayName}</h2>

          <div class="team-hub-bottom">
            ${
              franchise
                ? `
                  <div
                    class="team-franchise-pill"
                    style="${getFranchisePillStyle(franchise)}"
                  >
                    ${franchise.franchise_name}
                  </div>
                `
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