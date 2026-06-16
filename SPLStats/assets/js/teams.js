let teams = [];
let teamRecords = {};

const searchInput = document.querySelector("#teamSearch");
const results = document.querySelector("#teamResults");

async function loadTeams() {

  const [
    teamsResponse,
    recordsResponse
  ] = await Promise.all([
    fetch("data/teams.json"),
    fetch("data/team_records.json")
  ]);

  teams = await teamsResponse.json();

  const records =
    await recordsResponse.json();

  teamRecords = {};

  records.forEach(record => {
    const normalizedName =
      record.team.replace(/\s*\([^)]*\)$/, "");

    teamRecords[normalizedName] = record;
  });

  renderTeams();
}

function renderTeams() {
  const query = searchInput.value.toLowerCase().trim();

  const filtered = teams
    .filter(team =>
      query === "" ||
      team.team_name.toLowerCase().includes(query)
    )
    .sort((a, b) =>
      (b.career?.games_played || 0) - (a.career?.games_played || 0)
    );

  results.innerHTML = filtered.map(team => {

    const record =
      teamRecords[team.team_name] || {};

    const wins =
      record.wins ?? 0;

    const losses =
      record.losses ?? 0;

    const winPercent =
      ((record.win_percent ?? 0) * 100)
        .toFixed(1);

    const gf =
      record.goals_for ?? 0;

    const ga =
      record.goals_against ?? 0;

    const seasons =
      record.seasons?.length
      ?? 0;

    return `
      <a
        class="team-hub-card"
        href="team.html?team=${encodeURIComponent(
          team.team_name
        )}"
      >

        <h2>${team.team_name}</h2>

        <div class="team-record">
          ${wins}-${losses}
        </div>

        <div class="team-winpct">
          ( ${winPercent}% )
        </div>

        <div class="team-goals">
          ${gf} GF
          &nbsp;|&nbsp;
          ${ga} GA
        </div>

        <small>
          ${seasons} Seasons
        </small>

      </a>
    `;

  }).join("");
}

searchInput.addEventListener("input", renderTeams);

loadTeams();