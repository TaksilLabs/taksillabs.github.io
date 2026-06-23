import colorsys
import json
import mimetypes
import re
import shutil
from collections import Counter
from io import BytesIO
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote

from PIL import Image


PORT = 8770
HOST = "localhost"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TEAM_METADATA_FILE = DATA_DIR / "team_metadata.json"
TEAM_IMAGES_DIR = BASE_DIR / "assets" / "images" / "teams"

THEME_KEYS = [
    "primary",
    "secondary",
    "accent",
    "background",
    "card",
    "surface",
]


def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def hex_to_rgb(hex_color):
    text = hex_color.strip().lstrip("#")
    return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))


def color_distance(a, b):
    return sum((a[i] - b[i]) ** 2 for i in range(3)) ** 0.5


def is_transparent(pixel):
    return len(pixel) == 4 and pixel[3] < 40


def is_near_white(rgb):
    r, g, b = rgb
    return r > 235 and g > 235 and b > 235


def is_near_black(rgb):
    r, g, b = rgb
    return r < 28 and g < 28 and b < 28


def saturation(rgb):
    r, g, b = [x / 255 for x in rgb]
    _h, s, _v = colorsys.rgb_to_hsv(r, g, b)
    return s


def brightness(rgb):
    r, g, b = [x / 255 for x in rgb]
    _h, _s, v = colorsys.rgb_to_hsv(r, g, b)
    return v


def round_rgb(rgb, step=16):
    return tuple(
        max(0, min(255, round(channel / step) * step))
        for channel in rgb
    )


def extract_palette(image_bytes, max_colors=6):
    image = Image.open(BytesIO(image_bytes)).convert("RGBA")
    image.thumbnail((220, 220))

    pixels = []

    for pixel in image.getdata():
        if is_transparent(pixel):
            continue

        rgb = pixel[:3]
        pixels.append(round_rgb(rgb, 16))

    counts = Counter(pixels)

    has_white = any(
        is_near_white(rgb)
        for rgb, _count in counts.most_common(200)
    )

    meaningful = []

    for rgb, _count in counts.most_common(200):
        if is_near_white(rgb):
            continue

        if is_near_black(rgb):
            continue

        if saturation(rgb) < 0.12:
            continue

        if all(color_distance(rgb, existing) > 38 for existing in meaningful):
            meaningful.append(rgb)

        if len(meaningful) >= max_colors:
            break

    if not meaningful:
        for rgb, _count in counts.most_common(200):
            if not is_near_white(rgb) and not is_near_black(rgb):
                if all(color_distance(rgb, existing) > 38 for existing in meaningful):
                    meaningful.append(rgb)

            if len(meaningful) >= max_colors:
                break

    if has_white:
        meaningful.append((255, 255, 255))

    return meaningful


def make_theme(palette):
    if not palette:
        palette = [
            (214, 169, 53),
            (255, 255, 255),
            (17, 17, 17),
        ]

    def is_colorful(rgb):
        return (
            saturation(rgb) > 0.18
            and brightness(rgb) > 0.20
            and brightness(rgb) < 0.88
        )

    def is_bright_color(rgb):
        return (
            saturation(rgb) > 0.25
            and brightness(rgb) > 0.55
        )

    primary_candidates = [
        rgb for rgb in palette
        if is_colorful(rgb)
        and not is_near_white(rgb)
        and not is_near_black(rgb)
    ]

    primary = primary_candidates[0] if primary_candidates else palette[0]

    secondary_candidates = [
        rgb for rgb in palette
        if brightness(rgb) < 0.35
        and color_distance(rgb, primary) > 35
    ]

    secondary_rgb = secondary_candidates[0] if secondary_candidates else (17, 17, 17)

    accent_candidates = [
        rgb for rgb in palette
        if is_bright_color(rgb)
        and color_distance(rgb, primary) > 45
        and color_distance(rgb, secondary_rgb) > 35
        and not is_near_white(rgb)
    ]

    accent_rgb = accent_candidates[0] if accent_candidates else primary

    return {
        "primary": rgb_to_hex(primary),
        "secondary": rgb_to_hex(secondary_rgb),
        "accent": rgb_to_hex(accent_rgb),
        "background": "#050505",
        "card": "#111111",
        "surface": "#1a1a1a",
    }


def list_team_logos():
    if not TEAM_IMAGES_DIR.exists():
        return []

    files = []

    for path in sorted(TEAM_IMAGES_DIR.iterdir()):
        if path.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
            files.append({
                "name": path.name,
                "path": str(path.relative_to(BASE_DIR)).replace("\\", "/"),
            })

    return files


def read_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def normalize_metadata_payload(data):
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        if isinstance(data.get("teams"), list):
            return data["teams"]

        if isinstance(data.get("team_metadata"), list):
            return data["team_metadata"]

    raise ValueError("team_metadata.json must be a list, or an object containing a teams list.")


def write_metadata_preserving_shape(path, current_raw_data, teams):
    backup_path = path.with_suffix(".json.bak")

    if path.exists():
        shutil.copy2(path, backup_path)

    if isinstance(current_raw_data, list):
        output = teams
    elif isinstance(current_raw_data, dict):
        output = dict(current_raw_data)

        if isinstance(output.get("teams"), list):
            output["teams"] = teams
        elif isinstance(output.get("team_metadata"), list):
            output["team_metadata"] = teams
        else:
            output["teams"] = teams
    else:
        output = teams

    with path.open("w", encoding="utf-8") as file:
        json.dump(output, file, indent=2, ensure_ascii=False)
        file.write("\n")

    return backup_path


APP_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SPLStats Team Theme Builder</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">

  <style>
    :root {
      --bg: #05080c;
      --panel: #0b121a;
      --surface: #111d28;
      --text: #f4f4f4;
      --muted: #9fb3c8;
      --teal: #00d1d1;
      --gold: #ffd166;
      --green: #5cff9d;
      --red: #ff5d73;
      --line: rgba(255, 255, 255, 0.13);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(0, 209, 209, 0.13), transparent 34%),
        radial-gradient(circle at top right, rgba(255, 209, 102, 0.10), transparent 30%),
        var(--bg);
      color: var(--text);
      font-family: Arial, sans-serif;
    }

    button,
    input,
    select,
    textarea {
      font: inherit;
    }

    header {
      padding: 22px 24px;
      background: #080f14;
      border-bottom: 1px solid var(--line);

      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
    }

    h1 {
      margin: 0;
      color: var(--teal);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-size: 1.3rem;
    }

    header p {
      margin: 5px 0 0;
      color: var(--muted);
      font-size: 0.9rem;
      font-weight: 700;
    }

    .top-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    main {
      max-width: 1660px;
      margin: 20px auto;
      padding: 0 20px;

      display: grid;
      grid-template-columns: 300px 410px minmax(560px, 1fr);
      gap: 18px;
      align-items: start;
    }

    .panel {
      background:
        linear-gradient(135deg, rgba(17, 29, 40, 0.96), rgba(7, 14, 21, 0.96));
      border: 1px solid var(--line);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 14px 30px rgba(0, 0, 0, 0.32);
    }

    .panel-head {
      padding: 14px 15px;
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
      padding: 15px;
    }

    label {
      display: block;
      margin-top: 13px;
      margin-bottom: 6px;
      color: var(--muted);
      font-size: 0.74rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 900;
    }

    input,
    select,
    textarea {
      width: 100%;
      border-radius: 10px;
      border: 1px solid rgba(255, 255, 255, 0.16);
      background: #071017;
      color: white;
      padding: 10px;
      font-size: 0.92rem;
      font-weight: 800;
    }

    input[readonly] {
      color: #9fb3c8;
      cursor: not-allowed;
    }

    textarea {
      min-height: 170px;
      font-family: Consolas, monospace;
      resize: vertical;
      font-weight: 700;
    }

    button {
      border-radius: 10px;
      border: 1px solid rgba(0, 209, 209, 0.55);
      background: rgba(0, 209, 209, 0.16);
      color: #cfffff;
      padding: 10px 12px;
      font-weight: 950;
      text-transform: uppercase;
      letter-spacing: 0.045em;
      cursor: pointer;
    }

    button:hover {
      background: rgba(0, 209, 209, 0.26);
    }

    button.save {
      border-color: rgba(92, 255, 157, 0.55);
      background: rgba(92, 255, 157, 0.13);
      color: #dfffee;
    }

    button.reload {
      border-color: rgba(255, 209, 102, 0.44);
      background: rgba(255, 209, 102, 0.12);
      color: #fff0c7;
    }

    .team-search {
      margin-bottom: 10px;
    }

    .team-list {
      max-height: calc(100vh - 188px);
      overflow: auto;
      display: grid;
      gap: 7px;
      padding-right: 4px;
    }

    .team-button {
      width: 100%;
      text-align: left;
      text-transform: none;
      letter-spacing: 0;
      border-color: rgba(255, 255, 255, 0.08);
      background: rgba(255, 255, 255, 0.04);
      color: #fff;
    }

    .team-button strong {
      display: block;
      font-size: 0.88rem;
    }

    .team-button span {
      display: block;
      margin-top: 3px;
      color: var(--muted);
      font-size: 0.73rem;
      font-weight: 800;
    }

    .team-button.active {
      border-color: var(--teal);
      background:
        linear-gradient(135deg, rgba(0, 209, 209, 0.22), rgba(255, 255, 255, 0.045));
    }

    .button-row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 14px;
    }

    .button-row button {
      flex: 1;
    }

    .color-grid {
      display: grid;
      gap: 9px;
      margin-top: 4px;
    }

    .color-row {
      display: grid;
      grid-template-columns: 1fr 50px 112px;
      gap: 9px;
      align-items: end;
    }

    .color-row label {
      margin: 0 0 6px;
    }

    .color-row input[type="color"] {
      height: 40px;
      padding: 3px;
      cursor: pointer;
    }

    .color-row input[type="text"] {
      font-family: Consolas, monospace;
      font-weight: 950;
    }

    .note {
      color: #8aa0b5;
      font-size: 0.82rem;
      line-height: 1.45;
      font-weight: 700;
    }

    .status {
      min-height: 22px;
      margin-top: 12px;
      color: var(--muted);
      font-weight: 800;
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

    .team-page-preview {
      min-height: 640px;
      border-radius: 16px;
      overflow: hidden;

      background: var(--preview-background, #050505);
      border: 1px solid color-mix(in srgb, var(--preview-primary, #00d1d1) 32%, rgba(255, 255, 255, 0.12));
      box-shadow:
        0 18px 40px rgba(0, 0, 0, 0.44),
        inset 0 0 30px rgba(255, 255, 255, 0.03);
    }

    .preview-hero {
      position: relative;
      min-height: 275px;
      padding: 28px;

      display: grid;
      grid-template-columns: 150px 1fr;
      gap: 24px;
      align-items: center;

      background:
        radial-gradient(circle at top right, color-mix(in srgb, var(--preview-primary, #00d1d1) 42%, transparent), transparent 44%),
        radial-gradient(circle at bottom left, color-mix(in srgb, var(--preview-accent, #ffffff) 18%, transparent), transparent 36%),
        linear-gradient(135deg, var(--preview-card, #111111), var(--preview-surface, #1a1a1a));
      border-bottom: 1px solid color-mix(in srgb, var(--preview-primary, #00d1d1) 45%, transparent);
    }

    .preview-logo-card {
      width: 150px;
      height: 150px;

      border-radius: 24px;
      border: 2px solid color-mix(in srgb, var(--preview-primary, #00d1d1) 68%, #ffffff);
      background:
        linear-gradient(135deg, rgba(0, 0, 0, 0.26), rgba(255, 255, 255, 0.045));

      display: grid;
      place-items: center;

      box-shadow:
        0 0 24px color-mix(in srgb, var(--preview-primary, #00d1d1) 40%, transparent),
        inset 0 0 22px rgba(0, 0, 0, 0.34);
    }

    .preview-logo-card img {
      max-width: 116px;
      max-height: 116px;
      object-fit: contain;
    }

    .preview-logo-fallback {
      color: var(--preview-accent, #ffffff);
      font-size: 3.1rem;
      font-weight: 1000;
      text-shadow: -2px 2px 0 #000;
    }

    .preview-kicker {
      display: inline-block;
      margin-bottom: 10px;
      padding: 5px 9px;

      border: 1px solid color-mix(in srgb, var(--preview-primary, #00d1d1) 54%, transparent);
      border-radius: 999px;

      color: var(--preview-primary, #00d1d1);
      background: rgba(0, 0, 0, 0.22);

      font-size: 0.72rem;
      font-weight: 1000;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .preview-team-name {
      margin: 0;
      color: var(--preview-accent, #ffffff);

      font-size: clamp(2.1rem, 5vw, 4.4rem);
      line-height: 0.95;
      text-transform: uppercase;
      letter-spacing: 0.03em;

      text-shadow:
        -3px 3px 0 #000,
        0 0 18px rgba(0, 0, 0, 0.78);
    }

    .preview-description {
      margin: 12px 0 0;
      max-width: 660px;
      color: color-mix(in srgb, var(--preview-accent, #ffffff) 72%, #9fb3c8);
      font-weight: 850;
      line-height: 1.4;
    }

    .preview-body {
      padding: 22px;
      background:
        linear-gradient(
          180deg,
          color-mix(in srgb, var(--preview-surface, #1a1a1a) 76%, transparent),
          rgba(0, 0, 0, 0.12)
        );
    }

    .preview-tabs {
      display: flex;
      gap: 9px;
      flex-wrap: wrap;
      margin-bottom: 18px;
    }

    .preview-tab {
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid color-mix(in srgb, var(--preview-primary, #00d1d1) 35%, rgba(255, 255, 255, 0.10));
      background: color-mix(in srgb, var(--preview-secondary, #111111) 76%, rgba(255, 255, 255, 0.06));
      color: #ffffff;

      font-size: 0.72rem;
      font-weight: 1000;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }

    .preview-tab.active {
      border-color: var(--preview-primary, #00d1d1);
      background: color-mix(in srgb, var(--preview-primary, #00d1d1) 25%, rgba(0, 0, 0, 0.34));
      color: var(--preview-accent, #ffffff);
    }

    .preview-stat-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }

    .preview-stat-card {
      min-height: 110px;
      padding: 14px;

      border: 1px solid color-mix(in srgb, var(--preview-primary, #00d1d1) 25%, rgba(255, 255, 255, 0.10));
      border-radius: 16px;

      background:
        linear-gradient(135deg, var(--preview-card, #111111), color-mix(in srgb, var(--preview-surface, #1a1a1a) 85%, #000));

      box-shadow: 0 8px 18px rgba(0, 0, 0, 0.30);
    }

    .preview-stat-card span {
      display: block;
      color: var(--preview-primary, #00d1d1);
      font-size: 0.72rem;
      font-weight: 1000;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }

    .preview-stat-card strong {
      display: block;
      margin-top: 10px;

      color: var(--preview-accent, #ffffff);
      font-size: 1.55rem;
      font-weight: 1000;
      text-shadow: -1px 1px 0 #000;
    }

    .preview-match-card,
    .preview-player-row {
      margin-top: 14px;
      padding: 13px 14px;

      border-radius: 14px;
      border: 1px solid color-mix(in srgb, var(--preview-primary, #00d1d1) 28%, rgba(255, 255, 255, 0.08));
      background: color-mix(in srgb, var(--preview-surface, #1a1a1a) 70%, rgba(0, 0, 0, 0.22));
    }

    .preview-player-row {
      display: flex;
      justify-content: space-between;
      gap: 12px;
    }

    .preview-player-row strong {
      color: #ffffff;
    }

    .preview-player-row span {
      color: var(--preview-primary, #00d1d1);
      font-weight: 1000;
    }

    .preview-match-card h4 {
      margin: 0 0 8px;
      color: var(--preview-accent, #ffffff);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .preview-match-score {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      color: #d7f7ff;
      font-weight: 950;
    }

    .preview-match-score strong {
      color: var(--preview-primary, #00d1d1);
    }

    .swatches {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 14px;
    }

    .swatch {
      width: 94px;
      min-height: 62px;
      border-radius: 10px;
      border: 1px solid rgba(255, 255, 255, 0.18);
      display: flex;
      align-items: flex-end;
      padding: 8px;
      font-size: 0.68rem;
      font-family: Consolas, monospace;
      text-shadow: 0 1px 2px #000;
    }

    @media (max-width: 1230px) {
      main {
        grid-template-columns: 280px 1fr;
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

      .team-list {
        max-height: 360px;
      }

      .preview-hero {
        grid-template-columns: 1fr;
      }

      .preview-stat-grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>

<body>
  <header>
    <div>
      <h1>SPLStats Team Theme Builder</h1>
      <p>Edit team metadata, generate colors from logos, and preview a team-page-style layout.</p>
    </div>

    <div class="top-actions">
      <button class="reload" id="reloadButton">Reload JSON</button>
      <button class="save" id="saveButton">Save Metadata</button>
    </div>
  </header>

  <main>
    <aside class="panel">
      <div class="panel-head">
        <h2>Teams</h2>
      </div>

      <div class="panel-body">
        <input class="team-search" id="teamSearch" placeholder="Search teams...">
        <div class="team-list" id="teamList"></div>
      </div>
    </aside>

    <section class="panel">
      <div class="panel-head">
        <h2>Metadata Editor</h2>
      </div>

      <div class="panel-body">
        <label>Team ID</label>
        <input id="teamIdInput" readonly>

        <label>Team Display Name</label>
        <input id="teamNameInput">

        <label>Logo Path</label>
        <input id="logoPathInput">

        <label>Upload Logo to Generate Theme</label>
        <input id="logoInput" type="file" accept="image/*">

        <div class="button-row">
          <button id="generateButton">Generate Theme</button>
        </div>

        <label>Theme Colors</label>
        <div class="color-grid" id="colorGrid"></div>

        <div class="button-row">
          <button id="applyButton">Apply</button>
          <button id="copyButton">Copy Theme</button>
        </div>

        <label>Theme JSON Preview</label>
        <textarea id="jsonOutput" readonly></textarea>

        <p class="note">
          Save writes directly to <code>data/team_metadata.json</code> and creates a backup.
          Uploading a logo only previews/generates colors; make sure the logo file exists in
          <code>assets/images/teams</code>.
        </p>

        <div class="status" id="statusText"></div>
      </div>
    </section>

    <section class="preview-shell panel">
      <div class="panel-head">
        <h2>Team Page Preview</h2>
      </div>

      <div class="team-page-preview" id="previewPage">
        <section class="preview-hero">
          <div class="preview-logo-card" id="previewLogoCard"></div>

          <div>
            <span class="preview-kicker">SPLStats Team Page</span>
            <h3 class="preview-team-name" id="previewTeamName">Example Team</h3>
            <p class="preview-description">
              This preview uses the same theme fields the live site uses:
              primary, secondary, accent, background, card, and surface.
            </p>
          </div>
        </section>

        <section class="preview-body">
          <div class="preview-tabs">
            <div class="preview-tab active">Overview</div>
            <div class="preview-tab">Roster</div>
            <div class="preview-tab">Matches</div>
            <div class="preview-tab">History</div>
          </div>

          <div class="preview-stat-grid">
            <article class="preview-stat-card">
              <span>Record</span>
              <strong>7-2</strong>
            </article>

            <article class="preview-stat-card">
              <span>Goals For</span>
              <strong>43</strong>
            </article>

            <article class="preview-stat-card">
              <span>Division Rank</span>
              <strong>#2</strong>
            </article>
          </div>

          <div class="preview-player-row">
            <strong>Example Player</strong>
            <span>24 PTS</span>
          </div>

          <div class="preview-player-row">
            <strong>Example Goalie</strong>
            <span>0.812 SV%</span>
          </div>

          <article class="preview-match-card">
            <h4>Recent Match</h4>
            <div class="preview-match-score">
              <span id="previewMatchTeam">Example Team</span>
              <strong>5 - 3</strong>
              <span>Opponent</span>
            </div>
          </article>

          <div class="swatches" id="swatches"></div>
        </section>
      </div>
    </section>
  </main>

  <script>
    const THEME_KEYS = [
      "primary",
      "secondary",
      "accent",
      "background",
      "card",
      "surface"
    ];

    let metadata = [];
    let selectedIndex = -1;
    let visibleIndexes = [];
    let uploadedPreviewSrc = "";

    const els = {
      teamSearch: document.querySelector("#teamSearch"),
      teamList: document.querySelector("#teamList"),
      teamIdInput: document.querySelector("#teamIdInput"),
      teamNameInput: document.querySelector("#teamNameInput"),
      logoPathInput: document.querySelector("#logoPathInput"),
      logoInput: document.querySelector("#logoInput"),
      generateButton: document.querySelector("#generateButton"),
      colorGrid: document.querySelector("#colorGrid"),
      jsonOutput: document.querySelector("#jsonOutput"),
      applyButton: document.querySelector("#applyButton"),
      copyButton: document.querySelector("#copyButton"),
      saveButton: document.querySelector("#saveButton"),
      reloadButton: document.querySelector("#reloadButton"),
      statusText: document.querySelector("#statusText"),
      previewPage: document.querySelector("#previewPage"),
      previewLogoCard: document.querySelector("#previewLogoCard"),
      previewTeamName: document.querySelector("#previewTeamName"),
      previewMatchTeam: document.querySelector("#previewMatchTeam"),
      swatches: document.querySelector("#swatches")
    };

    const colorInputs = {};

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

    function normalizeHex(value, fallback = "#000000") {
      let text = cleanText(value);

      if (!text) return fallback;
      if (!text.startsWith("#")) text = `#${text}`;

      if (/^#[0-9a-fA-F]{3}$/.test(text)) {
        text = "#" + text.slice(1).split("").map(char => char + char).join("");
      }

      if (!/^#[0-9a-fA-F]{6}$/.test(text)) {
        return fallback;
      }

      return text.toLowerCase();
    }

    function getDefaultColor(key) {
      return {
        primary: "#00d1d1",
        secondary: "#111111",
        accent: "#ffffff",
        background: "#050505",
        card: "#111111",
        surface: "#1a1a1a"
      }[key] || "#000000";
    }

    function getTeamName(team) {
      return (
        team.team_display_name
        || team.team_id
        || "Unknown Team"
      );
    }

    function getTeamId(team) {
      return team.team_id || team.id || team.slug || "";
    }

    function buildColorGrid() {
      els.colorGrid.innerHTML = "";

      THEME_KEYS.forEach(key => {
        const row = document.createElement("div");
        row.className = "color-row";

        const label = document.createElement("label");
        label.textContent = key;

        const picker = document.createElement("input");
        picker.type = "color";

        const text = document.createElement("input");
        text.type = "text";

        picker.addEventListener("input", () => {
          text.value = picker.value;
          updatePreview();
        });

        text.addEventListener("input", () => {
          const normalized = normalizeHex(text.value, picker.value);

          if (/^#[0-9a-f]{6}$/.test(normalized)) {
            picker.value = normalized;
          }

          updatePreview();
        });

        colorInputs[key] = { picker, text };

        row.appendChild(label);
        row.appendChild(picker);
        row.appendChild(text);

        els.colorGrid.appendChild(row);
      });
    }

    async function loadMetadata() {
      const response = await fetch("/api/metadata");

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || "Could not load metadata.");
      }

      metadata = await response.json();
      selectedIndex = -1;

      renderTeamList();

      if (metadata.length) {
        selectTeam(0);
      }

      setStatus("Loaded team_metadata.json.", "good");
    }

    function renderTeamList() {
      const query = cleanText(els.teamSearch.value).toLowerCase();

      visibleIndexes = [];
      els.teamList.innerHTML = "";

      metadata.forEach((team, index) => {
        const name = getTeamName(team);
        const id = getTeamId(team);
        const haystack = `${name} ${id}`.toLowerCase();

        if (query && !haystack.includes(query)) {
          return;
        }

        visibleIndexes.push(index);

        const button = document.createElement("button");
        button.type = "button";
        button.className = `team-button ${index === selectedIndex ? "active" : ""}`;
        button.innerHTML = `
          <strong>${escapeHtml(name)}</strong>
          <span>${escapeHtml(id)}</span>
        `;

        button.addEventListener("click", () => {
          applyFormToMemory();
          selectTeam(index);
        });

        els.teamList.appendChild(button);
      });
    }

    function selectTeam(index) {
      selectedIndex = index;
      uploadedPreviewSrc = "";

      const team = metadata[selectedIndex];
      const theme = team.theme || {};

      els.teamIdInput.value = getTeamId(team);
      els.teamNameInput.value = getTeamName(team);
      els.logoPathInput.value = team.logo || "";

      THEME_KEYS.forEach(key => {
        const value = normalizeHex(theme[key], getDefaultColor(key));
        colorInputs[key].picker.value = value;
        colorInputs[key].text.value = value;
      });

      renderTeamList();
      updatePreview();
      setStatus(`Editing ${getTeamName(team)}.`, "");
    }

    function getFormTheme() {
      const theme = {};

      THEME_KEYS.forEach(key => {
        theme[key] = normalizeHex(colorInputs[key].text.value, getDefaultColor(key));
      });

      return theme;
    }

    function applyFormToMemory() {
      if (selectedIndex < 0 || !metadata[selectedIndex]) return;

      const team = metadata[selectedIndex];

      team.team_display_name = cleanText(els.teamNameInput.value);
      team.logo = cleanText(els.logoPathInput.value);

      if (!team.theme || typeof team.theme !== "object") {
        team.theme = {};
      }

      const theme = getFormTheme();

      THEME_KEYS.forEach(key => {
        team.theme[key] = theme[key];
      });
    }

    function updatePreview() {
      const theme = getFormTheme();
      const teamName = cleanText(els.teamNameInput.value) || "Example Team";
      const logoPath = cleanText(els.logoPathInput.value);

      els.previewPage.style.setProperty("--preview-primary", theme.primary);
      els.previewPage.style.setProperty("--preview-secondary", theme.secondary);
      els.previewPage.style.setProperty("--preview-accent", theme.accent);
      els.previewPage.style.setProperty("--preview-background", theme.background);
      els.previewPage.style.setProperty("--preview-card", theme.card);
      els.previewPage.style.setProperty("--preview-surface", theme.surface);

      els.previewTeamName.textContent = teamName;
      els.previewMatchTeam.textContent = teamName;

      renderPreviewLogo(teamName, logoPath);
      renderSwatches(theme);

      els.jsonOutput.value = JSON.stringify({
        logo: logoPath,
        theme
      }, null, 2);
    }

    function renderPreviewLogo(teamName, logoPath) {
      const firstLetter = escapeHtml(teamName.slice(0, 1).toUpperCase() || "?");

      if (uploadedPreviewSrc) {
        els.previewLogoCard.innerHTML = `
          <img src="${uploadedPreviewSrc}" alt="">
        `;
        return;
      }

      if (logoPath) {
        const src = "/" + logoPath.replace(/^\/+/, "");

        els.previewLogoCard.innerHTML = `
          <img
            src="${escapeHtml(src)}"
            alt=""
            onerror="this.remove(); this.parentElement.innerHTML='<div class=&quot;preview-logo-fallback&quot;>${firstLetter}</div>';"
          >
        `;
        return;
      }

      els.previewLogoCard.innerHTML = `
        <div class="preview-logo-fallback">${firstLetter}</div>
      `;
    }

    function renderSwatches(theme) {
      els.swatches.innerHTML = Object.entries(theme).map(([name, color]) => `
        <div class="swatch" style="background:${color};">
          ${escapeHtml(name)}<br>${escapeHtml(color)}
        </div>
      `).join("");
    }

    async function generateTheme() {
      const file = els.logoInput.files[0];

      if (!file) {
        alert("Pick a logo first.");
        return;
      }

      const logoPath = `assets/images/teams/${file.name}`;
      els.logoPathInput.value = logoPath;

      const reader = new FileReader();

      reader.onload = () => {
        uploadedPreviewSrc = reader.result;
        updatePreview();
      };

      reader.readAsDataURL(file);

      const formData = new FormData();
      formData.append("logo", file);

      const response = await fetch("/generate", {
        method: "POST",
        body: formData
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || "Theme generation failed.");
      }

      const data = await response.json();

      THEME_KEYS.forEach(key => {
        const value = normalizeHex(data.theme[key], getDefaultColor(key));
        colorInputs[key].picker.value = value;
        colorInputs[key].text.value = value;
      });

      updatePreview();
      setStatus("Generated theme from uploaded logo.", "good");
    }

    async function saveMetadata() {
      applyFormToMemory();

      const response = await fetch("/api/metadata", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(metadata)
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || "Save failed.");
      }

      setStatus(`Saved team_metadata.json. Backup: ${data.backup}`, "good");
    }

    async function copyTheme() {
      await navigator.clipboard.writeText(els.jsonOutput.value);
      setStatus("Copied theme JSON.", "good");
    }

    function setStatus(message, type = "") {
      els.statusText.textContent = message;
      els.statusText.className = `status ${type}`;
    }

    function bindEvents() {
      els.teamSearch.addEventListener("input", renderTeamList);
      els.teamNameInput.addEventListener("input", updatePreview);
      els.logoPathInput.addEventListener("input", () => {
        uploadedPreviewSrc = "";
        updatePreview();
      });

      els.logoInput.addEventListener("change", () => {
        const file = els.logoInput.files[0];
        if (!file) return;

        els.logoPathInput.value = `assets/images/teams/${file.name}`;

        const reader = new FileReader();
        reader.onload = () => {
          uploadedPreviewSrc = reader.result;
          updatePreview();
        };
        reader.readAsDataURL(file);
      });

      els.generateButton.addEventListener("click", async () => {
        try {
          await generateTheme();
        } catch (error) {
          console.error(error);
          setStatus(error.message, "bad");
          alert(error.message);
        }
      });

      els.applyButton.addEventListener("click", () => {
        applyFormToMemory();
        renderTeamList();
        setStatus("Applied changes in memory. Save Metadata when ready.", "good");
      });

      els.copyButton.addEventListener("click", copyTheme);

      els.saveButton.addEventListener("click", async () => {
        try {
          await saveMetadata();
        } catch (error) {
          console.error(error);
          setStatus(error.message, "bad");
          alert(error.message);
        }
      });

      els.reloadButton.addEventListener("click", async () => {
        if (!confirm("Reload team_metadata.json from disk? Unsaved changes will be lost.")) {
          return;
        }

        try {
          await loadMetadata();
        } catch (error) {
          console.error(error);
          setStatus(error.message, "bad");
          alert(error.message);
        }
      });
    }

    buildColorGrid();
    bindEvents();

    loadMetadata().catch(error => {
      console.error(error);
      setStatus(error.message, "bad");
      alert(error.message);
    });
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def send_text(self, text, content_type="text/html; charset=utf-8", status=200):
        body = text.encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, data, status=200):
        self.send_text(
            json.dumps(data, ensure_ascii=False),
            "application/json; charset=utf-8",
            status
        )

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            return self.send_text(APP_HTML)

        if path == "/api/metadata":
            try:
                raw_data = read_json(TEAM_METADATA_FILE)
                teams = normalize_metadata_payload(raw_data)
            except Exception as error:
                return self.send_json({"error": str(error)}, status=500)

            return self.send_json(teams)

        if path == "/api/logos":
            return self.send_json(list_team_logos())

        return self.serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/generate":
            return self.handle_generate()

        if path == "/api/metadata":
            return self.handle_save_metadata()

        return self.send_json({"error": "Not found"}, status=404)

    def handle_save_metadata(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            teams = json.loads(body)

            if not isinstance(teams, list):
                return self.send_json(
                    {"error": "Metadata payload must be a JSON list."},
                    status=400
                )

            current_raw_data = read_json(TEAM_METADATA_FILE)
            backup_path = write_metadata_preserving_shape(
                TEAM_METADATA_FILE,
                current_raw_data,
                teams
            )

        except Exception as error:
            return self.send_json({"error": str(error)}, status=500)

        return self.send_json({
            "ok": True,
            "backup": backup_path.name
        })

    def handle_generate(self):
        content_type = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        boundary_match = re.search(r"boundary=(.+)", content_type)

        if not boundary_match:
            return self.send_json(
                {"error": "Missing multipart boundary"},
                status=400
            )

        boundary = boundary_match.group(1).encode()
        parts = body.split(b"--" + boundary)

        image_bytes = None

        for part in parts:
            if b'name="logo"' not in part:
                continue

            header_end = part.find(b"\r\n\r\n")

            if header_end == -1:
                continue

            image_bytes = part[header_end + 4:]
            image_bytes = image_bytes.rstrip(b"\r\n--")

        if not image_bytes:
            return self.send_json(
                {"error": "No logo uploaded"},
                status=400
            )

        try:
            palette = extract_palette(image_bytes)
            theme = make_theme(palette)
        except Exception as error:
            return self.send_json({"error": str(error)}, status=500)

        return self.send_json({
            "palette": [rgb_to_hex(rgb) for rgb in palette],
            "theme": theme
        })

    def serve_static(self, url_path):
        decoded = unquote(url_path).lstrip("/")
        file_path = (BASE_DIR / decoded).resolve()

        try:
            file_path.relative_to(BASE_DIR)
        except ValueError:
            return self.send_text("Forbidden", "text/plain; charset=utf-8", status=403)

        if not file_path.exists() or not file_path.is_file():
            return self.send_text("Not found", "text/plain; charset=utf-8", status=404)

        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"

        with file_path.open("rb") as file:
            body = file.read()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[team-theme-builder] {self.address_string()} - {format % args}")


def main():
    if not TEAM_METADATA_FILE.exists():
        raise FileNotFoundError(f"Could not find {TEAM_METADATA_FILE}")

    print("SPLStats Team Theme Builder")
    print(f"Root: {BASE_DIR}")
    print(f"Metadata: {TEAM_METADATA_FILE}")
    print(f"Team logos: {TEAM_IMAGES_DIR}")
    print(f"Open: http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop.")

    server = ThreadingHTTPServer((HOST, PORT), Handler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Team Theme Builder.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()