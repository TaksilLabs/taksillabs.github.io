(() => {
  const SEASON_ID = "summer_2026";

  const DATA_PATHS = {
    transactions: `data/live_season/${SEASON_ID}/roster_transactions.json`
  };

  function cleanText(value) {
    return String(value || "").trim();
  }

  async function fetchJsonOrFallback(url, fallback) {
    try {
      const response = await fetch(url);

      if (!response.ok) {
        return fallback;
      }

      return await response.json();
    } catch (error) {
      console.warn(`Could not load ${url}`, error);
      return fallback;
    }
  }

  function getTransactions(data) {
    if (Array.isArray(data)) {
      return data;
    }

    if (Array.isArray(data?.transactions)) {
      return data.transactions;
    }

    return [];
  }

  function formatTransactionDate(value) {
    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return "";
    }

    return date.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric"
    });
  }

  function getTransactionSymbol(transaction) {
    const type = cleanText(transaction.type).toLowerCase();

    if (type === "add") return "+";
    if (type === "remove") return "−";

    return "•";
  }

  function getTransactionVerb(transaction) {
    const type = cleanText(transaction.type).toLowerCase();

    if (type === "add") return "Added";
    if (type === "remove") return "Removed";

    return "Updated";
  }

  function getTransactionDayKey(value) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "unknown_date";
  }

  return date.toISOString().slice(0, 10);
}

function groupTransactionsByTeamAndDay(transactions) {
  const groups = new Map();

  transactions.forEach(transaction => {
    const dayKey = getTransactionDayKey(transaction.created_at_utc);
    const teamKey = cleanText(transaction.team_id || transaction.team_display_name || "unknown_team");
    const groupKey = `${dayKey}__${teamKey}`;
    const draftId = `${dayKey}_${teamKey}_roster_moves`;

    if (!groups.has(groupKey)) {
        groups.set(groupKey, {
            group_key: groupKey,
            draft_id: draftId,
            press_release_url: `press_release.html?id=${encodeURIComponent(draftId)}`,

            created_at_utc: transaction.created_at_utc,
            day_key: dayKey,

            team_id: transaction.team_id,
            team_abbreviation: transaction.team_abbreviation,
            team_display_name: transaction.team_display_name,

            transactions: [],
        });
    }

    const group = groups.get(groupKey);

    group.transactions.push(transaction);

    if (Date.parse(transaction.created_at_utc || "") > Date.parse(group.created_at_utc || "")) {
      group.created_at_utc = transaction.created_at_utc;
    }
  });

  return [...groups.values()]
    .sort((a, b) => {
      return Date.parse(b.created_at_utc || "") - Date.parse(a.created_at_utc || "");
    });
}

  function renderTransactionCard(group) {
    const teamAbbreviation = cleanText(group.team_abbreviation) || "TBD";
    const teamName = cleanText(group.team_display_name || group.team_id) || "Unknown Team";
    const dateLabel = formatTransactionDate(group.created_at_utc);

    const transactions = Array.isArray(group.transactions)
        ? group.transactions
        : [];

    const hasAdd = transactions.some(transaction => cleanText(transaction.type).toLowerCase() === "add");
    const hasRemove = transactions.some(transaction => cleanText(transaction.type).toLowerCase() === "remove");

    const cardClass = hasAdd && hasRemove
        ? "transaction-mixed"
        : hasAdd
        ? "transaction-add"
        : hasRemove
            ? "transaction-remove"
            : "transaction-other";

    const jerseyNumbers = transactions
        .map(transaction => cleanText(transaction.jersey_number))
        .filter(Boolean);

    const watermarkNumber = jerseyNumbers[0] || "";

    const href = cleanText(group.press_release_url) || "#";

    return `
        <a class="transaction-wire-card ${cardClass}" href="${href}">
        ${
            watermarkNumber
            ? `<div class="transaction-wire-number">${watermarkNumber}</div>`
            : ""
        }

        <div class="transaction-wire-date">${dateLabel}</div>

        <div class="transaction-wire-team">
            <strong>${teamAbbreviation}</strong>
            <span>- ${teamName}</span>
        </div>

        <div class="transaction-wire-lines">
            ${transactions.map(transaction => {
                const symbol = getTransactionSymbol(transaction);
                const type = cleanText(transaction.type).toLowerCase();

                const lineClass = type === "add"
                ? "transaction-line-add"
                : type === "remove"
                    ? "transaction-line-remove"
                    : "transaction-line-other";

                const playerName = cleanText(
                transaction.player_display_name
                || transaction.player_id
                || "Unknown Player"
                );

                return `
                <div class="transaction-wire-player ${lineClass}">
                    <span class="transaction-wire-symbol">${symbol}</span>
                    <span>${playerName}</span>
                </div>
                `;
            }).join("")}
        </div>
        </a>
    `;
    }

  function renderTransactionWire(transactions) {
    const container = document.querySelector("#rosterTransactionWire");

    if (!container) return;

    const latest = groupTransactionsByTeamAndDay(transactions)
        .slice(0, 20);

    if (!latest.length) {
        container.innerHTML = `
        <div class="transaction-wire-empty">
            No roster transactions yet.
        </div>
        `;
        return;
    }

    const cards = latest.map(renderTransactionCard).join("");

    // Duplicate the cards so the ticker can loop cleanly.
    container.innerHTML = cards + cards;

    requestAnimationFrame(() => {
        const totalWidth = container.scrollWidth;
        const loopDistance = totalWidth / 2;

        container.style.setProperty("--transaction-scroll-distance", `${loopDistance}px`);

        // Rough speed: larger number = slower scroll.
        const duration = Math.max(30, loopDistance / 35);
        container.style.setProperty("--transaction-scroll-duration", `${duration}s`);

        container.classList.toggle("is-scrolling", latest.length > 2);
    });
  }

  async function loadRosterTransactionWire() {
    const data = await fetchJsonOrFallback(DATA_PATHS.transactions, {
      transactions: []
    });

    renderTransactionWire(getTransactions(data));
  }

  loadRosterTransactionWire();
})();