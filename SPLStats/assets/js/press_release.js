const SEASON_ID = "summer_2026";

const DATA_PATHS = {
  drafts: `data/live_season/${SEASON_ID}/news/press_release_drafts.json`
};

function cleanText(value) {
  return String(value || "").trim();
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function getPressReleaseIdFromUrl() {
  const params = new URLSearchParams(window.location.search);

  return cleanText(
    params.get("id")
    || params.get("draft")
    || ""
  );
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

function getDrafts(data) {
  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data?.drafts)) {
    return data.drafts;
  }

  return [];
}

function findDraft(drafts, targetId) {
  return drafts.find(draft => {
    return cleanText(draft.draft_id) === targetId
      || cleanText(draft.slug) === targetId;
  }) || null;
}

function formatDate(value) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return date.toLocaleDateString(undefined, {
    month: "long",
    day: "numeric",
    year: "numeric"
  });
}


// Start of quote block

function isQuoteBlock(lines) {
  if (lines.length < 3) return false;

  const quoteLine = cleanText(lines[0]);
  const colorLine = cleanText(lines[1]);
  const speakerLine = cleanText(lines[2]);

  return quoteLine.startsWith('"')
    && quoteLine.endsWith('"')
    && colorLine.toLowerCase().startsWith("#color:")
    && speakerLine.startsWith("-");
}

function getSafeQuoteColor(value) {
  const raw = cleanText(value)
    .replace(/^#color:/i, "")
    .replace("#", "");

  if (/^[0-9a-f]{6}$/i.test(raw)) {
    return `#${raw}`;
  }

  return "#00d1d1";
}

function renderQuoteBlock(lines) {
  const quote = cleanText(lines[0]).replace(/^"|"$/g, "");
  const color = getSafeQuoteColor(lines[1]);
  const speaker = cleanText(lines[2]).replace(/^-+/, "").trim();

  return `
    <figure class="press-release-quote" style="--quote-color: ${color};">
      <blockquote>
        “${escapeHtml(quote)}”
      </blockquote>
      <figcaption>
        ${escapeHtml(speaker)}
      </figcaption>
    </figure>
  `;
}

function renderInlineMarkdown(value) {
  let html = escapeHtml(value);

  html = html.replace(
    /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
  );

  return html;
}

function renderTextParagraph(lines) {
  return `<p>${lines.map(line => renderInlineMarkdown(line)).join("<br>")}</p>`;
}

// End of quote block



function markdownToHtml(markdown) {
  const blocks = cleanText(markdown)
    .split(/\n\s*\n/g)
    .map(block => block.trim())
    .filter(Boolean);

  if (!blocks.length) {
    return `<p>No article body available.</p>`;
  }

  return blocks.map(block => {
    const lines = block
      .split("\n")
      .map(line => line.trim())
      .filter(Boolean);

    if (isQuoteBlock(lines)) {
      return renderQuoteBlock(lines);
    }

    return renderTextParagraph(lines);
  }).join("");
}

function renderPlayerRows(draft) {
  const players = Array.isArray(draft.players)
    ? draft.players
    : [];

  if (!players.length) {
    return "";
  }

  return `
    <section class="press-release-players">
      ${players.map(player => {
        const type = cleanText(player.type).toLowerCase();

        const symbol = type === "add"
          ? "+"
          : type === "remove"
            ? "−"
            : "•";

        const jersey = cleanText(player.jersey_number)
          ? `#${escapeHtml(player.jersey_number)} `
          : "";

        const playerName = escapeHtml(
          player.player_display_name
          || player.player_id
          || "Unknown Player"
        );

        return `
          <div class="press-release-player-row ${type}">
            <span class="press-release-symbol">${symbol}</span>
            <span>${jersey}${playerName}</span>
          </div>
        `;
      }).join("")}
    </section>
  `;
}

function renderDraft(draft) {
  const container = document.querySelector("#pressReleaseArticle");

  if (!container) return;

  if (!draft) {
    container.innerHTML = `
      <div class="press-release-empty">
        Press release not found.
      </div>
    `;
    return;
  }

  document.title = `${draft.headline || "Press Release"} | SPLStats`;

  const dateLabel = formatDate(draft.created_at_utc);

  container.innerHTML = `
    <div class="press-release-kicker">Roster Wire</div>

    <h1 class="press-release-title">
      ${escapeHtml(draft.headline || "Untitled Press Release")}
    </h1>

    <p class="press-release-subheadline">
      ${escapeHtml(draft.subheadline || "")}
    </p>

    <div class="press-release-meta">
      ${dateLabel ? `<span class="press-release-pill">${escapeHtml(dateLabel)}</span>` : ""}
      ${draft.team_display_name ? `<span class="press-release-pill">${escapeHtml(draft.team_display_name)}</span>` : ""}
      ${draft.team_abbreviation ? `<span class="press-release-pill">${escapeHtml(draft.team_abbreviation)}</span>` : ""}
      ${draft.division ? `<span class="press-release-pill">${escapeHtml(draft.division)}</span>` : ""}
      ${draft.status ? `<span class="press-release-pill">${escapeHtml(draft.status)}</span>` : ""}
    </div>

    ${renderPlayerRows(draft)}

    <section class="press-release-body">
      ${markdownToHtml(draft.body_markdown || "")}
    </section>
  `;
}

async function loadPressRelease() {
  const targetId = getPressReleaseIdFromUrl();

  if (!targetId) {
    renderDraft(null);
    return;
  }

  const data = await fetchJsonOrFallback(DATA_PATHS.drafts, {
    drafts: []
  });

  const draft = findDraft(getDrafts(data), targetId);

  renderDraft(draft);
}

loadPressRelease();