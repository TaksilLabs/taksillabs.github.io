let players = [];
let sortKey = "points";
let sortDirection = "desc";

const tbody = document.querySelector("#leaderboard tbody");
const searchInput = document.querySelector("#searchInput");

async function loadData() {
  const response = await fetch("data/all_time_players.json");
  players = await response.json();
  renderTable();
}

function getStat(player, key) {
  if (key === "player_name") return player.player_name || "";
  return player.career?.[key] ?? 0;
}

function renderTable() {
  const search = searchInput.value.toLowerCase();

  let filtered = players.filter(player =>
    player.player_name.toLowerCase().includes(search)
  );

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
    const c = player.career;

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

loadData();