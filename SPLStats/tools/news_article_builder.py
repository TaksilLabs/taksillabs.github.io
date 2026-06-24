from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
import json
import mimetypes
import re
import shutil
from datetime import date

BUILDER_DIR = Path(__file__).resolve().parent / "news_builder"
BUILDER_INDEX_FILE = BUILDER_DIR / "index.html"

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

    def send_file(self, file_path):
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

    def serve_builder_static(self, url_path):
      decoded = unquote(url_path).replace("/builder/", "", 1)
      file_path = (BUILDER_DIR / decoded).resolve()

      try:
          file_path.relative_to(BUILDER_DIR)
      except ValueError:
          return self.send_text(403, "Forbidden")

      return self.send_file(file_path)

    def do_GET(self):
      parsed = urlparse(self.path)
      path = parsed.path

      if path == "/" or path == "/index.html":
          return self.send_file(BUILDER_INDEX_FILE)

      if path.startswith("/builder/"):
          return self.serve_builder_static(path)

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