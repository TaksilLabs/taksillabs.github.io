const NEWS_INDEX_PATH = "data/news/articles.json";

let articles = [];
let activeSearch = "";
let activeRegion = "all";
let activeStatus = "published";

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

function formatDate(value) {
  if (!value) return "No date";

  const date = new Date(`${value}T12:00:00`);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric"
  });
}

function getArticleUrl(article) {
  return `article.html?id=${encodeURIComponent(article.id)}`;
}

function articlePassesFilters(article) {
  const haystack = [
    article.title,
    article.subtitle,
    article.author,
    ...(article.tags || []),
    ...(article.region_tags || [])
  ].join(" ").toLowerCase();

  if (activeSearch && !haystack.includes(activeSearch.toLowerCase())) {
    return false;
  }

  if (activeRegion !== "all") {
    const regionTags = article.region_tags || [];
    const tags = article.tags || [];

    if (!regionTags.includes(activeRegion) && !tags.includes(activeRegion)) {
      return false;
    }
  }

  if (activeStatus !== "all" && article.status !== activeStatus) {
    return false;
  }

  return true;
}

function getFilteredArticles() {
  return articles.filter(articlePassesFilters);
}

function renderTag(tag) {
  return `<span class="news-tag">${escapeHtml(tag)}</span>`;
}

function renderFeaturedArticle(article) {
  if (!article) {
    return "";
  }

  const tags = article.tags || [];

  return `
    <a class="featured-article-card" href="${getArticleUrl(article)}">
      ${
        article.hero_image
          ? `
            <div class="featured-image">
              <img src="${escapeHtml(article.hero_image)}" alt="">
            </div>
          `
          : `
            <div class="featured-image placeholder">
              SPL
            </div>
          `
      }

      <div class="featured-content">
        <div class="news-tag-row">
          ${tags.slice(0, 4).map(renderTag).join("")}
        </div>

        <h2>${escapeHtml(article.title || "Untitled Article")}</h2>

        ${
          article.subtitle
            ? `<p>${escapeHtml(article.subtitle)}</p>`
            : ""
        }

        <div class="article-card-meta">
          <span>${escapeHtml(article.author || "SPL Media Team")}</span>
          <span>${formatDate(article.published_at)}</span>
        </div>
      </div>
    </a>
  `;
}

function renderArticleCard(article) {
  const tags = article.tags || [];

  return `
    <a class="article-card" href="${getArticleUrl(article)}">
      ${
        article.hero_image
          ? `
            <div class="article-card-image">
              <img src="${escapeHtml(article.hero_image)}" alt="">
            </div>
          `
          : `
            <div class="article-card-image placeholder">
              SPL
            </div>
          `
      }

      <div class="article-card-body">
        <div class="news-tag-row">
          ${tags.slice(0, 3).map(renderTag).join("")}
        </div>

        <h3>${escapeHtml(article.title || "Untitled Article")}</h3>

        ${
          article.subtitle
            ? `<p>${escapeHtml(article.subtitle)}</p>`
            : ""
        }

        <div class="article-card-meta">
          <span>${escapeHtml(article.author || "SPL Media Team")}</span>
          <span>${formatDate(article.published_at)}</span>
        </div>
      </div>
    </a>
  `;
}

function renderNewsPage() {
  const filtered = getFilteredArticles();

  const featured = filtered[0] || null;
  const rest = filtered.slice(1);

  document.querySelector("#featuredArticle").innerHTML = renderFeaturedArticle(featured);

  document.querySelector("#articleGrid").innerHTML = rest.length
    ? rest.map(renderArticleCard).join("")
    : `
      <section class="empty-news-panel">
        No articles match the current filters.
      </section>
    `;
}

function bindFilters() {
  const search = document.querySelector("#newsSearch");
  const region = document.querySelector("#regionFilter");
  const status = document.querySelector("#statusFilter");

  search.addEventListener("input", event => {
    activeSearch = event.target.value;
    renderNewsPage();
  });

  region.addEventListener("change", event => {
    activeRegion = event.target.value;
    renderNewsPage();
  });

  status.addEventListener("change", event => {
    activeStatus = event.target.value;
    renderNewsPage();
  });
}

async function loadNews() {
  const response = await fetch(NEWS_INDEX_PATH);

  if (!response.ok) {
    throw new Error("Could not load news articles.");
  }

  articles = await response.json();

  if (!Array.isArray(articles)) {
    articles = [];
  }

  articles.sort((a, b) => {
    return cleanText(b.published_at).localeCompare(cleanText(a.published_at));
  });

  bindFilters();
  renderNewsPage();
}

loadNews().catch(error => {
  console.error(error);

  document.querySelector("#articleGrid").innerHTML = `
    <section class="empty-news-panel">
      Failed to load news articles.
    </section>
  `;
});