let teams = [];

const searchInput = document.querySelector("#teamSearch");
const results = document.querySelector("#teamResults");

async function loadTeams() {
  const response = await fetch("data/teams.json");
  teams = await response.json();
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

  results.innerHTML = filtered.map(team => `
    <a class="team-hub-card" href="team.html?team=${encodeURIComponent(team.team_name)}">
      <h2>${team.team_name}</h2>
      <div>${team.career?.games_played ?? 0} GP</div>
      <div>${team.career?.points ?? 0} PTS</div>
      <small>${(team.seasons || []).length} Seasons</small>
    </a>
  `).join("");
}

searchInput.addEventListener("input", renderTeams);

loadTeams();