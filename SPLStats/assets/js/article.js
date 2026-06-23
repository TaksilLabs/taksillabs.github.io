const ARTICLE_BASE_PATH = "data/news/articles";
const TEAM_METADATA_PATH = "data/team_metadata.json";
const MATCH_SCHEDULE_PATH = "data/live_season/summer_2026/preseason/schedule.json";

let teamsById = {};
let matchesById = {};

function cleanText(value) {
  return String(value || "").trim();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function getArticleIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return cleanText(params.get("id") || "");
}

function formatDate(value) {
  if (!value) return "No date";

  const date = new Date(`${value}T12:00:00`);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric"
  });
}

function getTeamDisplayName(team) {
  return (
    team?.team_display_name
    || team?.team_name
    || team?.name
    || team?.team_id
    || "Unknown Team"
  );
}

function getTheme(teamId) {
  return teamsById[teamId]?.theme || {};
}

function getThemeValue(teamId, key, fallback) {
  return getTheme(teamId)[key] || fallback;
}

function renderTag(tag) {
  return `<span class="news-tag">${escapeHtml(tag)}</span>`;
}

function renderArticleBody(article) {
  const blocks = article.body || [];

  if (!blocks.length) {
    return `<p>No article body found.</p>`;
  }

  return blocks.map(block => {
    if (block.type === "heading") {
      return `<h2>${escapeHtml(block.text || "")}</h2>`;
    }

    if (block.type === "quote") {
        const quoteColor = block.color || "#ffd166";

        return `
            <blockquote
            class="article-quote-card"
            style="--quote-color: ${escapeHtml(quoteColor)};"
            >
            <p>${escapeHtml(block.text || "")}</p>
            ${
                block.credit
                ? `<cite>- ${escapeHtml(block.credit)}</cite>`
                : ""
            }
            </blockquote>
        `;
    }

    if (block.type === "image") {
      return `
        <figure>
          <img src="${escapeHtml(block.src || "")}" alt="">
          ${
            block.caption
              ? `<figcaption>${escapeHtml(block.caption)}</figcaption>`
              : ""
          }
        </figure>
      `;
    }

    if (block.type === "match_embed") {
      return renderMatchEmbed(block.match_id);
    }

    if (block.type === "team_embed") {
      return renderTeamEmbed(block.team_id);
    }

    return `<p>${escapeHtml(block.text || "")}</p>`;
  }).join("");
}

function renderTeamEmbed(teamId) {
  const team = teamsById[teamId];

  if (!team) {
    return "";
  }

  const primary = getThemeValue(teamId, "primary", "#7bdff2");
  const accent = getThemeValue(teamId, "accent", "#ffffff");
  const card = getThemeValue(teamId, "card", "#111111");

  return `
    <a
      class="article-team-embed"
      href="team.html?id=${encodeURIComponent(teamId)}"
      style="
        --team-primary: ${primary};
        --team-accent: ${accent};
        --team-card: ${card};
      "
    >
      ${
        team.logo
          ? `<img src="${escapeHtml(team.logo)}" alt="">`
          : `<div class="article-team-placeholder">${escapeHtml(getTeamDisplayName(team).slice(0, 1))}</div>`
      }

      <div>
        <span>Related Team</span>
        <strong>${escapeHtml(getTeamDisplayName(team))}</strong>
      </div>
    </a>
  `;
}

function renderMatchEmbed(matchId) {
  const match = matchesById[matchId];

  if (!match) {
    return "";
  }

  return `
    <a
      class="article-match-embed"
      href="match.html?id=${encodeURIComponent(matchId)}"
    >
      <span>
        ${escapeHtml(match.schedule_id || "Match")}
        · ${escapeHtml(match.region || "")}
      </span>

      <strong>
        ${escapeHtml(match.home_team || "Home")}
        ${
          match.status === "final"
            ? `${escapeHtml(match.home_score)} - ${escapeHtml(match.away_score)}`
            : "vs"
        }
        ${escapeHtml(match.away_team || "Away")}
      </strong>

      <em>${escapeHtml(match.status || "scheduled")}</em>
    </a>
  `;
}

function renderRelatedTeams(article) {
  const teamIds = article.related_teams || [];

  if (!teamIds.length) {
    return "";
  }

  return `
    <section class="article-related-section">
      <h2>Related Teams</h2>
      <div class="article-related-grid">
        ${teamIds.map(renderTeamEmbed).join("")}
      </div>
    </section>
  `;
}

function renderRelatedMatches(article) {
  const matchIds = article.related_matches || [];

  if (!matchIds.length) {
    return "";
  }

  return `
    <section class="article-related-section">
      <h2>Related Matches</h2>
      <div class="article-related-grid">
        ${matchIds.map(renderMatchEmbed).join("")}
      </div>
    </section>
  `;
}

function renderPlainRelated(title, items, baseUrl) {
  if (!items || !items.length) {
    return "";
  }

  return `
    <section class="article-related-section">
      <h2>${escapeHtml(title)}</h2>

      <div class="article-link-pill-row">
        ${items.map(item => `
          <a href="${baseUrl}${encodeURIComponent(item)}">
            ${escapeHtml(item)}
          </a>
        `).join("")}
      </div>
    </section>
  `;
}

function renderArticlePage(article) {
  document.title = `${article.title || "Article"} | SPLStats`;

  const tags = article.tags || [];

  document.querySelector("#articlePage").innerHTML = `
    <article class="article-shell">
      <header class="article-hero">
        <a class="back-link" href="news.html">← Back to News</a>

        <div class="news-tag-row">
          ${tags.map(renderTag).join("")}
        </div>

        <h1>${escapeHtml(article.title || "Untitled Article")}</h1>

        ${
          article.subtitle
            ? `<p class="article-subtitle">${escapeHtml(article.subtitle)}</p>`
            : ""
        }

        <div class="article-byline">
          <span>${escapeHtml(article.author || "SPL Media Team")}</span>
          <span>${formatDate(article.published_at)}</span>
          <span>${escapeHtml(article.status || "draft")}</span>
        </div>
      </header>

      ${
        article.hero_image
          ? `
            <figure class="article-hero-image">
              <img src="${escapeHtml(article.hero_image)}" alt="">
            </figure>
          `
          : ""
      }

      <section class="article-body">
        ${renderArticleBody(article)}
      </section>

      ${renderRelatedTeams(article)}
      ${renderRelatedMatches(article)}
      ${renderPlainRelated("Related Players", article.related_players, "player.html?id=")}
      ${renderPlainRelated("Related Franchises", article.related_franchises, "franchise.html?id=")}
    </article>
  `;
}

async function loadSupportData() {
  const [teamsResponse, matchesResponse] = await Promise.all([
    fetch(TEAM_METADATA_PATH).catch(() => null),
    fetch(MATCH_SCHEDULE_PATH).catch(() => null)
  ]);

  if (teamsResponse && teamsResponse.ok) {
    let teams = await teamsResponse.json();

    if (teams && !Array.isArray(teams)) {
      teams = teams.teams || teams.team_metadata || [];
    }

    teamsById = {};

    (teams || []).forEach(team => {
      if (team.team_id) {
        teamsById[team.team_id] = team;
      }
    });
  }

  if (matchesResponse && matchesResponse.ok) {
    const matches = await matchesResponse.json();

    matchesById = {};

    (matches || []).forEach(match => {
      if (match.match_id) {
        matchesById[match.match_id] = match;
      }
    });
  }
}

async function loadArticle() {
  const articleId = getArticleIdFromUrl();

  if (!articleId) {
    document.querySelector("#articlePage").innerHTML = `
      <section class="article-loading">
        No article ID was provided.
      </section>
    `;
    return;
  }

  await loadSupportData();

  const response = await fetch(`${ARTICLE_BASE_PATH}/${encodeURIComponent(articleId)}.json`);

  if (!response.ok) {
    throw new Error("Article not found.");
  }

  const article = await response.json();

  renderArticlePage(article);
}

loadArticle().catch(error => {
  console.error(error);

  document.querySelector("#articlePage").innerHTML = `
    <section class="article-loading">
      Failed to load article.
    </section>
  `;
});