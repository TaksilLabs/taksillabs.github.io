let entries = [];

const searchInput = document.querySelector("#slapSearch");
const resultsContainer = document.querySelector("#results");

async function loadLookup() {
  const response = await fetch("data/slap_id_lookup.json");
  entries = await response.json();

  renderResults();
}

function renderResults() {
  const query = searchInput.value.toLowerCase().trim();

  const results = entries
    .filter(entry => {
      const names = entry.player_names || [];

      return (
        query === "" ||
        String(entry.display_name || "").toLowerCase().includes(query) ||
        String(entry.slap_id || "").includes(query) ||
        names.some(item =>
          String(item.name || "").toLowerCase().includes(query)
        )
      );
    })
    .sort((a, b) => {
      const aTop = a.player_names?.[0]?.count || 0;
      const bTop = b.player_names?.[0]?.count || 0;
      return bTop - aTop;
    });

  resultsContainer.innerHTML = results.map(entry => {
    const title =
      entry.display_name ||
      entry.player_names?.[0]?.name ||
      "Unknown Player";

    return `
      <div class="player-card slap-id-card">
        <h2>
          <a href="player.html?id=${encodeURIComponent(title.toLowerCase())}">
            ${title}
          </a>
        </h2>

        <div class="slap-id-badge">
          Slap ID: ${entry.slap_id}
        </div>

        <h3>Known Usernames</h3>

        <div class="alias-list">
          ${(entry.player_names || []).map(item => `
            <div class="alias-row">
              <span class="alias-count">${item.count}</span>
              <span class="alias-name">
                <a href="player.html?id=${encodeURIComponent(String(item.name || "").toLowerCase())}">
                  ${item.name}
                </a>
              </span>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }).join("");
}

searchInput.addEventListener("input", renderResults);

loadLookup();