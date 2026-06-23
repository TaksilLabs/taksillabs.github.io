from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
import json
import mimetypes
import re
import shutil
from datetime import date


HOST = "localhost"
PORT = 8784

BASE_DIR = Path(__file__).resolve().parent.parent

NEWS_DIR = BASE_DIR / "data" / "news"
ARTICLE_DIR = NEWS_DIR / "articles"
ARTICLE_INDEX_FILE = NEWS_DIR / "articles.json"

TEAM_METADATA_FILE = BASE_DIR / "data" / "team_metadata.json"
MATCH_SCHEDULE_FILE = BASE_DIR / "data" / "live_season" / "summer_2026" / "preseason" / "schedule.json"

NEWS_IMAGES_DIR = BASE_DIR / "assets" / "images" / "news"


REGION_TAGS = ["East", "Central", "West"]


def ensure_dirs():
    NEWS_DIR.mkdir(parents=True, exist_ok=True)
    ARTICLE_DIR.mkdir(parents=True, exist_ok=True)
    NEWS_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    if not ARTICLE_INDEX_FILE.exists():
        write_json(ARTICLE_INDEX_FILE, [])


def read_json(path, fallback=None):
    if not path.exists():
        return fallback

    raw = path.read_bytes()

    if not raw.strip():
        return fallback

    for encoding in ("utf-8-sig", "utf-8", "utf-16"):
        try:
            return json.loads(raw.decode(encoding))
        except UnicodeDecodeError:
            continue
        except json.JSONDecodeError as error:
            # If utf-8 hits a BOM, try utf-8-sig before giving up.
            if encoding == "utf-8" and "Unexpected UTF-8 BOM" in str(error):
                continue

            raise

    raise ValueError(f"Could not decode JSON file: {path}")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def slugify(text):
    text = str(text or "").strip().lower()
    text = re.sub(r"['’]", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-") or "untitled-article"


def get_team_display_name(team):
    return (
        team.get("team_display_name")
        or team.get("team_name")
        or team.get("name")
        or team.get("team_id")
        or "Unknown Team"
    )


def load_teams():
    data = read_json(TEAM_METADATA_FILE, [])

    if isinstance(data, dict):
        if isinstance(data.get("teams"), list):
            data = data["teams"]
        elif isinstance(data.get("team_metadata"), list):
            data = data["team_metadata"]
        else:
            data = []

    teams = []

    for team in data:
        team_id = team.get("team_id")

        if not team_id:
            continue

        teams.append({
            "team_id": team_id,
            "team_display_name": get_team_display_name(team),
            "logo": team.get("logo", ""),
            "theme": team.get("theme", {}),
        })

    return sorted(teams, key=lambda item: item["team_display_name"].lower())


def load_matches():
    matches = read_json(MATCH_SCHEDULE_FILE, [])

    if not isinstance(matches, list):
        return []

    items = []

    for match in matches:
        match_id = match.get("match_id")

        if not match_id:
            continue

        score = "VS"

        if match.get("status") == "final":
            score = f"{match.get('home_score', 0)} - {match.get('away_score', 0)}"

        items.append({
            "match_id": match_id,
            "schedule_id": match.get("schedule_id", ""),
            "region": match.get("region", ""),
            "status": match.get("status", ""),
            "home_team_id": match.get("home_team_id", ""),
            "home_team": match.get("home_team", ""),
            "away_team_id": match.get("away_team_id", ""),
            "away_team": match.get("away_team", ""),
            "score": score,
        })

    return items


def load_article_index():
    index = read_json(ARTICLE_INDEX_FILE, [])

    if not isinstance(index, list):
        return []

    return index


def save_article_index(index):
    index = sorted(
        index,
        key=lambda article: (
            article.get("published_at") or "",
            article.get("updated_at") or "",
            article.get("title") or "",
        ),
        reverse=True,
    )

    write_json(ARTICLE_INDEX_FILE, index)


def parse_body_blocks(text):
    blocks = []

    chunks = re.split(r"\n\s*\n", str(text or "").strip())

    for chunk in chunks:
        chunk = chunk.strip()

        if not chunk:
            continue

        if chunk.startswith("## "):
            blocks.append({
                "type": "heading",
                "text": chunk[3:].strip(),
            })
            continue

        if chunk.startswith("> "):
          quote_text = chunk[2:].strip()
          credit = ""
          color = "#ffd166"

          # Optional syntax:
          # > Quote text
          # -- Blue on winning the championship
          # color: #7bdff2
          lines = quote_text.splitlines()
          kept_lines = []

          for line in lines:
              clean_line = line.strip()

              if clean_line.startswith("-- "):
                  credit = clean_line[3:].strip()
                  continue

              if clean_line.lower().startswith("color:"):
                  color = clean_line.split(":", 1)[1].strip()
                  continue

              kept_lines.append(line)

          blocks.append({
              "type": "quote",
              "text": "\n".join(kept_lines).strip(),
              "credit": credit,
              "color": color,
          })
          continue

        blocks.append({
            "type": "paragraph",
            "text": chunk,
        })

    return blocks


def article_to_index_item(article):
    return {
        "id": article["id"],
        "status": article.get("status", "draft"),
        "title": article.get("title", ""),
        "subtitle": article.get("subtitle", ""),
        "author": article.get("author", ""),
        "published_at": article.get("published_at", ""),
        "hero_image": article.get("hero_image", ""),
        "tags": article.get("tags", []),
        "region_tags": article.get("region_tags", []),
        "related_players": article.get("related_players", []),
        "related_teams": article.get("related_teams", []),
        "related_franchises": article.get("related_franchises", []),
        "related_matches": article.get("related_matches", []),
    }


APP_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>SPL News Article Builder</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">

  <style>
    :root {
      --bg: #05080d;
      --panel: #0b121a;
      --surface: #111d28;
      --text: #f4f4f4;
      --muted: #9fb3c8;
      --teal: #7bdff2;
      --gold: #ffd166;
      --green: #5cff9d;
      --red: #ff5d73;
      --line: rgba(123, 223, 242, 0.20);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(123, 223, 242, 0.12), transparent 32%),
        radial-gradient(circle at top right, rgba(255, 209, 102, 0.10), transparent 30%),
        var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
    }

    button,
    input,
    select,
    textarea {
      font: inherit;
    }

    header {
      padding: 18px 22px;
      border-bottom: 1px solid var(--line);
      background: #080f14;
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
    }

    h1 {
      margin: 0;
      color: var(--teal);
      font-size: 1.25rem;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }

    header p {
      margin: 5px 0 0;
      color: var(--muted);
      font-weight: 750;
      font-size: 0.9rem;
    }

    main {
      max-width: 1720px;
      margin: 18px auto;
      padding: 0 18px;
      display: grid;
      grid-template-columns: 330px minmax(520px, 680px) minmax(520px, 1fr);
      gap: 16px;
      align-items: start;
    }

    .panel {
      border: 1px solid var(--line);
      border-radius: 18px;
      background:
        linear-gradient(135deg, rgba(17, 29, 40, 0.96), rgba(7, 14, 21, 0.96));
      overflow: hidden;
      box-shadow: 0 12px 28px rgba(0, 0, 0, 0.34);
    }

    .panel-head {
      padding: 13px 15px;
      border-bottom: 1px solid var(--line);
    }

    .panel-head h2 {
      margin: 0;
      color: var(--teal);
      font-size: 0.9rem;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }

    .panel-body {
      padding: 14px;
    }

    .top-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    button {
      border: 1px solid rgba(123, 223, 242, 0.38);
      border-radius: 10px;
      padding: 10px 12px;
      background: rgba(123, 223, 242, 0.12);
      color: #eaffff;
      font-weight: 950;
      cursor: pointer;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    button:hover {
      border-color: rgba(123, 223, 242, 0.72);
      background: rgba(123, 223, 242, 0.20);
    }

    button.save {
      border-color: rgba(92, 255, 157, 0.50);
      background: rgba(92, 255, 157, 0.13);
      color: #eafff2;
    }

    button.new {
      border-color: rgba(255, 209, 102, 0.50);
      background: rgba(255, 209, 102, 0.12);
      color: #fff0c8;
    }

    label {
      display: block;
      margin: 13px 0 6px;
      color: var(--muted);
      font-size: 0.74rem;
      font-weight: 1000;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    input,
    select,
    textarea {
      width: 100%;
      padding: 10px 11px;
      border: 1px solid rgba(255, 255, 255, 0.14);
      border-radius: 10px;
      background: #071018;
      color: #ffffff;
      font-weight: 800;
    }

    textarea {
      min-height: 420px;
      resize: vertical;
      line-height: 1.45;
      font-weight: 650;
    }

    .article-list {
      display: grid;
      gap: 8px;
      max-height: calc(100vh - 190px);
      overflow: auto;
      padding-right: 4px;
    }

    .article-button {
      width: 100%;
      text-align: left;
      text-transform: none;
      letter-spacing: 0;
      border-color: rgba(255, 255, 255, 0.08);
      background: rgba(255, 255, 255, 0.04);
      color: #ffffff;
    }

    .article-button strong {
      display: block;
      font-size: 0.9rem;
    }

    .article-button span {
      display: block;
      margin-top: 4px;
      color: var(--muted);
      font-size: 0.74rem;
      font-weight: 800;
    }

    .article-button.active {
      border-color: var(--teal);
      background:
        linear-gradient(135deg, rgba(123, 223, 242, 0.18), rgba(255, 255, 255, 0.04));
    }

    .form-grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }

    .check-grid {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }

    .check-pill {
      display: inline-flex;
      gap: 7px;
      align-items: center;
      padding: 8px 10px;
      border: 1px solid rgba(123, 223, 242, 0.22);
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.04);
      color: #d7f7ff;
      font-weight: 900;
      font-size: 0.82rem;
      cursor: pointer;
    }

    .check-pill input {
      width: auto;
    }

    .multi-select {
      height: 142px;
    }

    .note {
      color: var(--muted);
      font-size: 0.82rem;
      line-height: 1.45;
      font-weight: 750;
    }

    .status {
      margin-top: 11px;
      min-height: 22px;
      color: var(--muted);
      font-weight: 850;
      font-size: 0.85rem;
    }

    .status.good {
      color: var(--green);
    }

    .status.bad {
      color: var(--red);
    }

    .preview-shell {
      position: sticky;
      top: 18px;
    }

    .article-preview {
      min-height: 720px;
      background:
        linear-gradient(180deg, rgba(12, 20, 28, 0.96), rgba(5, 8, 12, 0.96));
    }

    .preview-hero {
      padding: 28px;
      background:
        radial-gradient(circle at top left, rgba(123, 223, 242, 0.16), transparent 34%),
        radial-gradient(circle at bottom right, rgba(255, 209, 102, 0.11), transparent 38%),
        #0a121a;
      border-bottom: 1px solid var(--line);
    }

    .preview-tags {
      display: flex;
      gap: 7px;
      flex-wrap: wrap;
      margin-bottom: 13px;
    }

    .tag {
      padding: 5px 8px;
      border-radius: 999px;
      border: 1px solid rgba(123, 223, 242, 0.30);
      background: rgba(123, 223, 242, 0.09);
      color: #d7f7ff;
      font-size: 0.7rem;
      font-weight: 1000;
      text-transform: uppercase;
      letter-spacing: 0.055em;
    }

    .preview-hero h3 {
      margin: 0;
      color: #ffffff;
      font-size: clamp(2rem, 4.4vw, 4rem);
      line-height: 0.98;
      text-transform: uppercase;
      text-shadow: -3px 3px 0 #000;
    }

    .preview-subtitle {
      margin: 12px 0 0;
      color: #c7d6e6;
      font-size: 1.05rem;
      font-weight: 850;
      line-height: 1.45;
    }

    .preview-byline {
      margin-top: 14px;
      color: var(--muted);
      font-size: 0.85rem;
      font-weight: 850;
    }

    .preview-body {
      padding: 24px 28px;
      max-width: 880px;
    }

    .preview-body p {
      color: #e8f0f8;
      font-size: 1rem;
      line-height: 1.65;
      font-weight: 650;
    }

    .preview-body h4 {
      margin: 28px 0 10px;
      color: var(--teal);
      font-size: 1.35rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .preview-inline-link {
      display: inline-flex;
      align-items: center;
      gap: 4px;

      padding: 1px 6px;

      border: 1px solid rgba(123, 223, 242, 0.34);
      border-radius: 999px;

      background: rgba(123, 223, 242, 0.10);
      color: #d7f7ff;

      font-weight: 950;
      text-decoration: none;

      transition:
        border-color 0.14s ease,
        background 0.14s ease,
        color 0.14s ease;
    }

    .preview-inline-link:hover {
      border-color: rgba(255, 209, 102, 0.65);
      background: rgba(255, 209, 102, 0.14);
      color: #fff0c8;
    }

    .preview-inline-link.team {
      border-color: rgba(123, 223, 242, 0.40);
    }

    .preview-inline-link.match {
      border-color: rgba(255, 209, 102, 0.42);
    }

    .preview-inline-link.player {
      border-color: rgba(92, 255, 157, 0.38);
    }

    .preview-inline-link.franchise {
      border-color: rgba(255, 93, 115, 0.38);
    }

    .preview-quote {
      position: relative;
      overflow: hidden;

      margin: 22px 0;
      padding: 18px 20px;

      border-left: 7px solid var(--quote-color, var(--gold));
      border-radius: 14px;

      background:
        color-mix(in srgb, var(--quote-color, var(--gold)) 30%, rgba(5, 8, 12, 0.96));

      color: #ffffff;

      box-shadow:
        0 12px 26px rgba(0, 0, 0, 0.34),
        inset 0 0 22px rgba(255, 255, 255, 0.035);
    }

    .preview-quote {
      position: relative;
      overflow: hidden;
    }

    .preview-quote p {
      margin: 0;

      color: #ffffff;

      font-size: 1.08rem;
      font-weight: 900;
      line-height: 1.5;
    }

    .preview-quote::before {
      content: "“";

      position: absolute;
      left: 18px;
      top: -34px;

      color: var(--quote-color, var(--gold));

      font-family: Georgia, "Times New Roman", serif;
      font-size: 9rem;
      font-weight: 900;
      line-height: 1;

      opacity: 0.18;
      pointer-events: none;
      z-index: 0;
    }

    .preview-quote::after {
      content: "”";

      position: absolute;
      right: 18px;
      bottom: -78px;

      color: var(--quote-color, var(--gold));

      font-family: Georgia, "Times New Roman", serif;
      font-size: 9rem;
      font-weight: 900;
      line-height: 1;

      opacity: 0.10;
      pointer-events: none;
      z-index: 0;
    }

    .preview-quote p,
    .preview-quote cite {
      position: relative;
      z-index: 1;
    }

    .preview-quote cite {
      display: block;
      margin-top: 12px;

      color: rgba(255, 255, 255, 0.72);

      font-size: 0.82rem;
      font-style: normal;
      font-weight: 850;
    }

    .related-grid {
      display: grid;
      gap: 10px;
      margin-top: 18px;
    }

    .related-card {
      padding: 11px 12px;
      border: 1px solid rgba(123, 223, 242, 0.22);
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.045);
    }

    .related-card strong {
      display: block;
      color: #ffffff;
    }

    .related-card span {
      display: block;
      margin-top: 3px;
      color: var(--muted);
      font-size: 0.8rem;
      font-weight: 800;
    }

    @media (max-width: 1280px) {
      main {
        grid-template-columns: 320px 1fr;
      }

      .preview-shell {
        grid-column: 1 / -1;
        position: static;
      }
    }

    @media (max-width: 820px) {
      header {
        flex-direction: column;
        align-items: flex-start;
      }

      main {
        grid-template-columns: 1fr;
      }

      .form-grid-2 {
        grid-template-columns: 1fr;
      }

      .article-list {
        max-height: 360px;
      }
    }
  </style>
</head>

<body>
  <header>
    <div>
      <h1>SPL News Article Builder</h1>
      <p>Create draft/published article JSON for the SPLStats news section.</p>
    </div>

    <div class="top-actions">
      <button class="new" id="newButton">New Article</button>
      <button class="save" id="saveButton">Save Article</button>
      <button id="reloadButton">Reload</button>
    </div>
  </header>

  <main>
    <aside class="panel">
      <div class="panel-head">
        <h2>Articles</h2>
      </div>

      <div class="panel-body">
        <input id="articleSearch" placeholder="Search articles...">
        <div style="height: 10px;"></div>
        <div class="article-list" id="articleList"></div>
      </div>
    </aside>

    <section class="panel">
      <div class="panel-head">
        <h2>Editor</h2>
      </div>

      <div class="panel-body">
        <div class="form-grid-2">
          <div>
            <label>Status</label>
            <select id="statusInput">
              <option value="draft">Draft</option>
              <option value="published">Published</option>
            </select>
          </div>

          <div>
            <label>Publish Date</label>
            <input id="publishedAtInput" type="date">
          </div>
        </div>

        <label>Title</label>
        <input id="titleInput">

        <label>Subtitle</label>
        <input id="subtitleInput">

        <div class="form-grid-2">
          <div>
            <label>Author</label>
            <input id="authorInput" value="SPL Media Team">
          </div>

          <div>
            <label>Hero Image Path</label>
            <input id="heroImageInput" placeholder="assets/images/news/example.png">
          </div>
        </div>

        <label>Region Tags</label>
        <div class="check-grid" id="regionTags"></div>

        <label>Custom Tags</label>
        <input id="customTagsInput" placeholder="Preseason, Match Recap, Power Rankings">

        <div class="form-grid-2">
          <div>
            <label>Related Teams</label>
            <select id="relatedTeamsInput" class="multi-select" multiple></select>
          </div>

          <div>
            <label>Related Matches</label>
            <select id="relatedMatchesInput" class="multi-select" multiple></select>
          </div>
        </div>

        <div class="form-grid-2">
          <div>
            <label>Related Players</label>
            <input id="relatedPlayersInput" placeholder="player_id, player_id">
          </div>

          <div>
            <label>Related Franchises</label>
            <input id="relatedFranchisesInput" placeholder="franchise_id, franchise_id">
          </div>
        </div>

        <label>Article Body</label>
        <textarea id="bodyInput" placeholder="Write article body here.

Use blank lines between paragraphs.

Use ## Heading for headings.

Use > Quote text for quotes."></textarea>

        <p class="note">
          Body formatting: blank lines create paragraphs, <code>##</code> creates headings.
          Quotes can use smart quotes or <code>&gt;</code>.
          Inline links use <code>[[team:team_id]]</code>,
          <code>[[player:player_id]]</code>,
          <code>[[franchise:franchise_id]]</code>,
          or <code>[[match:match_id]]</code>.
          Add custom text with <code>|</code>, like
          <code>[[team:edmonton_bears|the Bears]]</code>.
        </p>

        <div class="status" id="statusText"></div>
      </div>
    </section>

    <section class="preview-shell panel">
      <div class="panel-head">
        <h2>Live Preview</h2>
      </div>

      <article class="article-preview">
        <section class="preview-hero">
          <div class="preview-tags" id="previewTags"></div>
          <h3 id="previewTitle">Untitled Article</h3>
          <p class="preview-subtitle" id="previewSubtitle"></p>
          <div class="preview-byline" id="previewByline"></div>
        </section>

        <section class="preview-body">
          <div id="previewBody"></div>

          <div class="related-grid" id="previewRelated"></div>
        </section>
      </article>
    </section>
  </main>

  <script>
    const REGION_TAGS = ["East", "Central", "West"];

    let articles = [];
    let teams = [];
    let matches = [];
    let currentArticleId = "";

    const els = {
      articleSearch: document.querySelector("#articleSearch"),
      articleList: document.querySelector("#articleList"),
      newButton: document.querySelector("#newButton"),
      saveButton: document.querySelector("#saveButton"),
      reloadButton: document.querySelector("#reloadButton"),
      statusInput: document.querySelector("#statusInput"),
      publishedAtInput: document.querySelector("#publishedAtInput"),
      titleInput: document.querySelector("#titleInput"),
      subtitleInput: document.querySelector("#subtitleInput"),
      authorInput: document.querySelector("#authorInput"),
      heroImageInput: document.querySelector("#heroImageInput"),
      regionTags: document.querySelector("#regionTags"),
      customTagsInput: document.querySelector("#customTagsInput"),
      relatedTeamsInput: document.querySelector("#relatedTeamsInput"),
      relatedMatchesInput: document.querySelector("#relatedMatchesInput"),
      relatedPlayersInput: document.querySelector("#relatedPlayersInput"),
      relatedFranchisesInput: document.querySelector("#relatedFranchisesInput"),
      bodyInput: document.querySelector("#bodyInput"),
      statusText: document.querySelector("#statusText"),
      previewTags: document.querySelector("#previewTags"),
      previewTitle: document.querySelector("#previewTitle"),
      previewSubtitle: document.querySelector("#previewSubtitle"),
      previewByline: document.querySelector("#previewByline"),
      previewBody: document.querySelector("#previewBody"),
      previewRelated: document.querySelector("#previewRelated")
    };

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }

    function cleanText(value) {
      return String(value || "").trim();
    }

    function splitCsv(value) {
      return cleanText(value)
        .split(",")
        .map(item => item.trim())
        .filter(Boolean);
    }

    function todayIso() {
      return new Date().toISOString().slice(0, 10);
    }

    function slugify(text) {
      return cleanText(text)
        .toLowerCase()
        .replace(/['’]/g, "")
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/-+/g, "-")
        .replace(/^-|-$/g, "") || "untitled-article";
    }

    async function loadBootstrap() {
      const response = await fetch("/api/bootstrap");

      if (!response.ok) {
        throw new Error("Could not load news builder data.");
      }

      const data = await response.json();

      articles = data.articles || [];
      teams = data.teams || [];
      matches = data.matches || [];

      renderRegionTags();
      renderEntityPickers();
      renderArticleList();

      if (articles.length) {
        await loadArticle(articles[0].id);
      } else {
        newArticle();
      }

      setStatus("Loaded news builder data.", "good");
    }

    function renderRegionTags() {
      els.regionTags.innerHTML = REGION_TAGS.map(region => `
        <label class="check-pill">
          <input type="checkbox" value="${region}">
          ${region}
        </label>
      `).join("");

      els.regionTags.querySelectorAll("input").forEach(input => {
        input.addEventListener("change", updatePreview);
      });
    }

    function renderEntityPickers() {
      els.relatedTeamsInput.innerHTML = teams.map(team => `
        <option value="${escapeHtml(team.team_id)}">
          ${escapeHtml(team.team_display_name)}
        </option>
      `).join("");

      els.relatedMatchesInput.innerHTML = matches.map(match => `
        <option value="${escapeHtml(match.match_id)}">
          ${escapeHtml(match.schedule_id || match.match_id)} ·
          ${escapeHtml(match.home_team)} ${escapeHtml(match.score)} ${escapeHtml(match.away_team)}
        </option>
      `).join("");
    }

    function renderArticleList() {
      const query = cleanText(els.articleSearch.value).toLowerCase();

      els.articleList.innerHTML = "";

      const filtered = articles.filter(article => {
        const haystack = [
          article.title,
          article.subtitle,
          article.author,
          article.status,
          ...(article.tags || []),
          ...(article.region_tags || [])
        ].join(" ").toLowerCase();

        return !query || haystack.includes(query);
      });

      if (!filtered.length) {
        els.articleList.innerHTML = `<p class="note">No articles found.</p>`;
        return;
      }

      filtered.forEach(article => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `article-button ${article.id === currentArticleId ? "active" : ""}`;
        button.innerHTML = `
          <strong>${escapeHtml(article.title || "Untitled Article")}</strong>
          <span>${escapeHtml(article.status || "draft")} · ${escapeHtml(article.published_at || "No date")}</span>
        `;

        button.addEventListener("click", () => {
          loadArticle(article.id);
        });

        els.articleList.appendChild(button);
      });
    }

    async function loadArticle(id) {
      const response = await fetch(`/api/article?id=${encodeURIComponent(id)}`);

      if (!response.ok) {
        throw new Error("Could not load article.");
      }

      const article = await response.json();
      currentArticleId = article.id;

      fillForm(article);
      renderArticleList();
      updatePreview();
      setStatus(`Loaded ${article.title}.`, "good");
    }

    function fillForm(article) {
      els.statusInput.value = article.status || "draft";
      els.publishedAtInput.value = article.published_at || todayIso();
      els.titleInput.value = article.title || "";
      els.subtitleInput.value = article.subtitle || "";
      els.authorInput.value = article.author || "SPL Media Team";
      els.heroImageInput.value = article.hero_image || "";

      const regionTags = new Set(article.region_tags || []);

      els.regionTags.querySelectorAll("input").forEach(input => {
        input.checked = regionTags.has(input.value);
      });

      const customTags = (article.tags || [])
        .filter(tag => !REGION_TAGS.includes(tag));

      els.customTagsInput.value = customTags.join(", ");

      setMultiSelectValues(els.relatedTeamsInput, article.related_teams || []);
      setMultiSelectValues(els.relatedMatchesInput, article.related_matches || []);

      els.relatedPlayersInput.value = (article.related_players || []).join(", ");
      els.relatedFranchisesInput.value = (article.related_franchises || []).join(", ");

      els.bodyInput.value = blocksToText(article.body || []);
    }

    function setMultiSelectValues(select, values) {
      const set = new Set(values);

      [...select.options].forEach(option => {
        option.selected = set.has(option.value);
      });
    }

    function getMultiSelectValues(select) {
      return [...select.selectedOptions].map(option => option.value);
    }

    function blocksToText(blocks) {
      return blocks.map(block => {
        if (block.type === "heading") {
          return `## ${block.text || ""}`;
        }

        if (block.type === "quote") {
          const lines = [`“${block.text || ""}”`];

          if (block.credit) {
            lines.push(`- ${block.credit}`);
          }

          if (block.color) {
            lines.push(`color: ${normalizeQuoteColor(block.color)}`);
          }

          return lines.join("\n");
        }

        return block.text || "";
      }).join("\n\n");
    }

    function parseBlocks(text) {
      const chunks = cleanText(text)
        .split(/\n\s*\n/g)
        .map(chunk => chunk.trim())
        .filter(Boolean);

      const blocks = [];

      for (let i = 0; i < chunks.length; i += 1) {
        const chunk = chunks[i];

        if (chunk.startsWith("## ")) {
          blocks.push({
            type: "heading",
            text: chunk.slice(3).trim()
          });
          continue;
        }

        const quoteBlock = parseQuoteChunk(chunk);

        if (quoteBlock) {
          blocks.push(quoteBlock);
          continue;
        }

        blocks.push({
          type: "paragraph",
          text: chunk
        });
      }

      return blocks;
    }

    function parseQuoteChunk(chunk) {
      const lines = chunk
        .split(/\n/g)
        .map(line => line.trim())
        .filter(Boolean);

      if (!lines.length) {
        return null;
      }

      let quoteText = "";
      let credit = "";
      let color = "#ffd166";

      const firstLine = lines[0];

      // Style 1:
      // > Quote text
      if (firstLine.startsWith("> ")) {
        quoteText = firstLine.slice(2).trim();

        lines.slice(1).forEach(line => {
          const parsed = parseQuoteMetaLine(line);

          if (parsed.type === "credit") credit = parsed.value;
          if (parsed.type === "color") color = parsed.value;
          if (parsed.type === "text") quoteText += `\n${parsed.value}`;
        });

        return {
          type: "quote",
          text: quoteText.trim(),
          credit,
          color: normalizeQuoteColor(color)
        };
      }

      // Style 2:
      // “Quote text.”
      // - Credit
      // color: #ffd166
      const smartQuoteMatch = firstLine.match(/^[“"]([\s\S]*?)[”"]\s*(?:color:\s*(#[0-9a-fA-F]{3,6}))?\s*$/);

      if (smartQuoteMatch) {
        quoteText = smartQuoteMatch[1].trim();

        if (smartQuoteMatch[2]) {
          color = smartQuoteMatch[2];
        }

        lines.slice(1).forEach(line => {
          const parsed = parseQuoteMetaLine(line);

          if (parsed.type === "credit") credit = parsed.value;
          if (parsed.type === "color") color = parsed.value;
          if (parsed.type === "text") quoteText += `\n${parsed.value}`;
        });

        return {
          type: "quote",
          text: quoteText.trim(),
          credit,
          color: normalizeQuoteColor(color)
        };
      }

      return null;
    }

    function parseQuoteMetaLine(line) {
      const cleanLine = cleanText(line);

      if (
        cleanLine.startsWith("-- ")
        || cleanLine.startsWith("- ")
        || cleanLine.startsWith("— ")
      ) {
        return {
          type: "credit",
          value: cleanLine
            .replace(/^--\s*/, "")
            .replace(/^-\s*/, "")
            .replace(/^—\s*/, "")
            .trim()
        };
      }

      if (cleanLine.toLowerCase().startsWith("color:")) {
        return {
          type: "color",
          value: cleanLine.split(":").slice(1).join(":").trim()
        };
      }

      return {
        type: "text",
        value: cleanLine
      };
    }

    function getSelectedRegionTags() {
      return [...els.regionTags.querySelectorAll("input:checked")]
        .map(input => input.value);
    }

    function buildArticleFromForm() {
      const title = cleanText(els.titleInput.value) || "Untitled Article";
      const id = currentArticleId || slugify(title);

      const regionTags = getSelectedRegionTags();
      const customTags = splitCsv(els.customTagsInput.value);
      const allTags = [...new Set([...regionTags, ...customTags])];

      return {
        id,
        status: els.statusInput.value || "draft",
        title,
        subtitle: cleanText(els.subtitleInput.value),
        author: cleanText(els.authorInput.value) || "SPL Media Team",
        published_at: els.publishedAtInput.value || todayIso(),
        hero_image: cleanText(els.heroImageInput.value),

        tags: allTags,
        region_tags: regionTags,

        related_players: splitCsv(els.relatedPlayersInput.value),
        related_teams: getMultiSelectValues(els.relatedTeamsInput),
        related_franchises: splitCsv(els.relatedFranchisesInput.value),
        related_matches: getMultiSelectValues(els.relatedMatchesInput),

        body: parseBlocks(els.bodyInput.value)
      };
    }

    function newArticle() {
      currentArticleId = "";

      fillForm({
        id: "",
        status: "draft",
        title: "",
        subtitle: "",
        author: "SPL Media Team",
        published_at: todayIso(),
        hero_image: "",
        tags: [],
        region_tags: [],
        related_players: [],
        related_teams: [],
        related_franchises: [],
        related_matches: [],
        body: []
      });

      renderArticleList();
      updatePreview();
      setStatus("Started new article.", "");
    }

    async function saveArticle() {
      const article = buildArticleFromForm();

      const response = await fetch("/api/article", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(article)
      });

      const result = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(result.error || "Save failed.");
      }

      currentArticleId = article.id;
      articles = result.articles || articles;

      renderArticleList();
      setStatus(`Saved ${article.title}.`, "good");
    }

    function getTeamById(teamId) {
      return teams.find(team => team.team_id === teamId);
    }

    function getMatchById(matchId) {
      return matches.find(match => match.match_id === matchId);
    }

    function getInlineEntityLabel(type, id, customLabel = "") {
      if (customLabel) {
        return customLabel;
      }

      if (type === "team") {
        const team = getTeamById(id);

        return team?.team_display_name || id;
      }

      if (type === "match") {
        const match = getMatchById(id);

        if (!match) {
          return id;
        }

        if (match.schedule_id) {
          return match.schedule_id;
        }

        return `${match.home_team} vs ${match.away_team}`;
      }

      return id;
    }

    function getInlineEntityHref(type, id) {
      if (type === "team") {
        return `team.html?id=${encodeURIComponent(id)}`;
      }

      if (type === "player") {
        return `player.html?id=${encodeURIComponent(id)}`;
      }

      if (type === "franchise") {
        return `franchise.html?id=${encodeURIComponent(id)}`;
      }

      if (type === "match") {
        return `match.html?id=${encodeURIComponent(id)}`;
      }

      return "#";
    }

    function renderInlineText(text) {
      const source = String(text || "");
      const tokenPattern = /\[\[(team|player|franchise|match):([^|\]]+)(?:\|([^\]]+))?\]\]/g;

      let output = "";
      let lastIndex = 0;
      let match;

      while ((match = tokenPattern.exec(source)) !== null) {
        const [fullToken, type, rawId, rawLabel] = match;

        output += escapeHtml(source.slice(lastIndex, match.index));

        const id = cleanText(rawId);
        const label = getInlineEntityLabel(type, id, cleanText(rawLabel));
        const href = getInlineEntityHref(type, id);

        output += `
          <a
            class="preview-inline-link ${type}"
            href="${escapeHtml(href)}"
            title="${escapeHtml(type)}: ${escapeHtml(id)}"
          >
            ${escapeHtml(label)}
          </a>
        `;

        lastIndex = match.index + fullToken.length;
      }

      output += escapeHtml(source.slice(lastIndex));

      return output;
    }

    function normalizeQuoteColor(value) {
      const text = cleanText(value);

      if (/^#[0-9a-fA-F]{3}$/.test(text)) {
        return "#" + text.slice(1).split("").map(char => char + char).join("");
      }

      if (/^#[0-9a-fA-F]{6}$/.test(text)) {
        return text;
      }

      return "#ffd166";
    }

    function updatePreview() {
      const article = buildArticleFromForm();

      els.previewTags.innerHTML = article.tags.map(tag => `
        <span class="tag">${escapeHtml(tag)}</span>
      `).join("");

      els.previewTitle.textContent = article.title || "Untitled Article";
      els.previewSubtitle.textContent = article.subtitle || "";
      els.previewByline.textContent = `${article.author} · ${article.published_at || "No date"} · ${article.status}`;

      els.previewBody.innerHTML = article.body.map(block => {
        if (block.type === "heading") {
          return `<h4>${escapeHtml(block.text)}</h4>`;
        }

        if (block.type === "quote") {
          const quoteColor = normalizeQuoteColor(block.color || "#ffd166");

          return `
            <div
              class="preview-quote"
              style="--quote-color: ${escapeHtml(quoteColor)};"
            >
              <p>${renderInlineText(block.text || "")}</p>
              ${
                block.credit
                  ? `<cite>- ${renderInlineText(block.credit)}</cite>`
                  : ""
              }
            </div>
          `;
        }

        return `<p>${renderInlineText(block.text)}</p>`;
      }).join("");

      const related = [];

      article.related_teams.forEach(teamId => {
        const team = getTeamById(teamId);

        related.push(`
          <div class="related-card">
            <strong>${escapeHtml(team?.team_display_name || teamId)}</strong>
            <span>Related Team</span>
          </div>
        `);
      });

      article.related_matches.forEach(matchId => {
        const match = getMatchById(matchId);

        related.push(`
          <div class="related-card">
            <strong>
              ${escapeHtml(match ? `${match.home_team} ${match.score} ${match.away_team}` : matchId)}
            </strong>
            <span>Related Match</span>
          </div>
        `);
      });

      article.related_players.forEach(playerId => {
        related.push(`
          <div class="related-card">
            <strong>${escapeHtml(playerId)}</strong>
            <span>Related Player</span>
          </div>
        `);
      });

      article.related_franchises.forEach(franchiseId => {
        related.push(`
          <div class="related-card">
            <strong>${escapeHtml(franchiseId)}</strong>
            <span>Related Franchise</span>
          </div>
        `);
      });

      els.previewRelated.innerHTML = related.join("");
    }

    function setStatus(message, type = "") {
      els.statusText.textContent = message;
      els.statusText.className = `status ${type}`;
    }

    function bindEvents() {
      els.articleSearch.addEventListener("input", renderArticleList);
      els.newButton.addEventListener("click", newArticle);

      els.reloadButton.addEventListener("click", () => {
        if (!confirm("Reload article data from disk? Unsaved changes will be lost.")) {
          return;
        }

        loadBootstrap().catch(error => {
          console.error(error);
          setStatus(error.message, "bad");
          alert(error.message);
        });
      });

      els.saveButton.addEventListener("click", async () => {
        try {
          await saveArticle();
        } catch (error) {
          console.error(error);
          setStatus(error.message, "bad");
          alert(error.message);
        }
      });

      [
        els.statusInput,
        els.publishedAtInput,
        els.titleInput,
        els.subtitleInput,
        els.authorInput,
        els.heroImageInput,
        els.customTagsInput,
        els.relatedTeamsInput,
        els.relatedMatchesInput,
        els.relatedPlayersInput,
        els.relatedFranchisesInput,
        els.bodyInput
      ].forEach(input => {
        input.addEventListener("input", updatePreview);
        input.addEventListener("change", updatePreview);
      });
    }

    bindEvents();

    loadBootstrap().catch(error => {
      console.error(error);
      setStatus(error.message, "bad");
      alert(error.message);
    });
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def send_text(self, status, text, content_type="text/plain; charset=utf-8"):
        body = text.encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            return self.send_text(200, APP_HTML, "text/html; charset=utf-8")

        if path == "/api/bootstrap":
            return self.handle_bootstrap()

        if path == "/api/article":
            return self.handle_get_article(parsed)

        return self.serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/article":
            return self.handle_save_article()

        return self.send_json(404, {"error": "Not found"})

    def handle_bootstrap(self):
        try:
            payload = {
                "articles": load_article_index(),
                "teams": load_teams(),
                "matches": load_matches(),
                "regions": REGION_TAGS,
            }
        except Exception as error:
            return self.send_json(500, {"error": str(error)})

        return self.send_json(200, payload)

    def handle_get_article(self, parsed):
        query = parse_qs(parsed.query)
        article_id = (query.get("id") or [""])[0]
        article_id = slugify(article_id)

        article_file = ARTICLE_DIR / f"{article_id}.json"

        if not article_file.exists():
            return self.send_json(404, {"error": "Article not found."})

        try:
            article = read_json(article_file, {})
        except Exception as error:
            return self.send_json(500, {"error": str(error)})

        return self.send_json(200, article)

    def handle_save_article(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            article = json.loads(body)

            title = article.get("title", "Untitled Article")
            article_id = slugify(article.get("id") or title)

            article["id"] = article_id

            article_file = ARTICLE_DIR / f"{article_id}.json"

            if article_file.exists():
                backup_file = article_file.with_suffix(".json.bak")
                shutil.copy2(article_file, backup_file)

            write_json(article_file, article)

            index = load_article_index()
            index_item = article_to_index_item(article)

            index = [
                item for item in index
                if item.get("id") != article_id
            ]

            index.append(index_item)
            save_article_index(index)

        except Exception as error:
            return self.send_json(500, {"error": str(error)})

        return self.send_json(200, {
            "ok": True,
            "article": article,
            "articles": load_article_index(),
        })

    def serve_static(self, url_path):
        decoded = unquote(url_path).lstrip("/")
        file_path = (BASE_DIR / decoded).resolve()

        try:
            file_path.relative_to(BASE_DIR)
        except ValueError:
            return self.send_text(403, "Forbidden")

        if not file_path.exists() or not file_path.is_file():
            return self.send_text(404, "Not found")

        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"

        with file_path.open("rb") as file:
            body = file.read()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[news-builder] {self.address_string()} - {format % args}")


def main():
    ensure_dirs()

    print("SPL News Article Builder")
    print(f"Root: {BASE_DIR}")
    print(f"Articles: {ARTICLE_DIR}")
    print(f"Open: http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop.")

    server = ThreadingHTTPServer((HOST, PORT), Handler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping News Article Builder.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()