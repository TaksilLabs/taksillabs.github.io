async function loadFranchises() {

    const [metaRes, statsRes] =
        await Promise.all([
            fetch("data/franchises.json"),
            fetch("data/franchise_stats.json")
        ]);

    const meta =
        await metaRes.json();

    const stats =
        await statsRes.json();

    const franchises =
        meta.map(franchise => {

            const statEntry =
                stats.find(
                    s =>
                    s.franchise_id ===
                    franchise.franchise_id
                ) || {};

            return {
                ...franchise,
                ...statEntry
            };
        });

    franchises.sort((a, b) => {

        const aTeams =
            a.stats?.all_divisions?.teams?.length || 0;

        const bTeams =
            b.stats?.all_divisions?.teams?.length || 0;

        return bTeams - aTeams;
    });

    renderFranchises(franchises);
}

function renderFranchises(franchises) {

    const hub =
        document.querySelector(
            "#franchiseHub"
        );

    hub.innerHTML =
        franchises.map(franchise => {

            const teams =
                franchise.stats
                ?.all_divisions
                ?.teams
                ?.length || 0;

            const seasons =
                franchise.stats
                ?.all_divisions
                ?.seasons
                ?.length || 0;

            return `
                <a
                    class="franchise-hub-card"
                    href="franchise.html?id=${franchise.franchise_id}"

                    style="
                        --franchise-primary:${franchise.theme?.primary || "#00bcd4"};
                        --franchise-secondary:${franchise.theme?.secondary || "#ffffff"};
                        --franchise-accent:${franchise.theme?.accent || "#ffffff"};
                        --franchise-background:${franchise.theme?.background || "#111"};
                    "
                >

                    <div class="franchise-card-name">
                        ${franchise.franchise_name}
                    </div>

                    <div class="franchise-card-stats">

                        <div class="franchise-stat">
                            <div class="franchise-card-label">
                                Teams
                            </div>

                            <div class="franchise-card-value">
                                ${teams}
                            </div>
                        </div>

                        <div class="franchise-stat">
                            <div class="franchise-card-label">
                                Seasons
                            </div>
                            
                            <div class="franchise-card-value">
                                ${seasons}
                            </div>
                        </div>

                    </div>

                    <div class="franchise-card-founded">
                        Founded: ${franchise.founded || "Unknown"}
                    </div>

                </a>
            `;
        }).join("");
}

function formatSeason(seasonId) {

    if (!seasonId)
        return "Unknown";

    const [season, year] =
        seasonId.split("_");

    return (
        season.charAt(0).toUpperCase() +
        season.slice(1) +
        " " +
        year
    );
}

loadFranchises();