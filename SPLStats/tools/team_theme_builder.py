import base64
import colorsys
import json
import re
from collections import Counter
from io import BytesIO
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

from PIL import Image


PORT = 8770
BASE_DIR = Path(__file__).resolve().parent.parent
TEAM_IMAGES_DIR = BASE_DIR / "SPLStats" / "assets" / "images" / "teams"


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
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return s


def brightness(rgb):
    r, g, b = [x / 255 for x in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
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
        for rgb, count in counts.most_common(200)
    )

    meaningful = []

    for rgb, count in counts.most_common(200):
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
        for rgb, count in counts.most_common(200):
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
            (17, 17, 17)
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

    # Primary should usually be the most dominant useful color.
    # extract_palette already returns colors in rough dominance order.
    primary_candidates = [
        rgb for rgb in palette
        if is_colorful(rgb)
        and not is_near_white(rgb)
        and not is_near_black(rgb)
    ]

    primary = (
        primary_candidates[0]
        if primary_candidates
        else palette[0]
    )

    # Secondary should be the strongest dark outline/shadow color.
    secondary_candidates = [
        rgb for rgb in palette
        if brightness(rgb) < 0.35
        and color_distance(rgb, primary) > 35
    ]

    secondary_rgb = (
        secondary_candidates[0]
        if secondary_candidates
        else (17, 17, 17)
    )

    # Accent should be a bright, colorful color that is different from primary.
    accent_candidates = [
        rgb for rgb in palette
        if is_bright_color(rgb)
        and color_distance(rgb, primary) > 45
        and color_distance(rgb, secondary_rgb) > 35
        and not is_near_white(rgb)
    ]

    if accent_candidates:
        accent_rgb = accent_candidates[0]
    else:
        accent_rgb = primary

    return {
        "primary": rgb_to_hex(primary),
        "secondary": rgb_to_hex(secondary_rgb),
        "accent": rgb_to_hex(accent_rgb),
        "background": "#050505",
        "card": "#111111",
        "surface": "#1a1a1a"
    }


def slugify_filename(name):
    text = str(name or "").strip().lower()
    text = re.sub(r"[^a-z0-9_\-\s]", "", text)
    text = re.sub(r"[\s\-]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def list_team_logos():
    if not TEAM_IMAGES_DIR.exists():
        return []

    files = []

    for path in sorted(TEAM_IMAGES_DIR.iterdir()):
        if path.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
            files.append({
                "name": path.name,
                "path": str(path.relative_to(BASE_DIR)).replace("\\", "/")
            })

    return files


HTML = r"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>SPLStats Team Theme Builder</title>

  <style>
    body {
      margin: 0;
      background: #05080c;
      color: white;
      font-family: Arial, sans-serif;
    }

    header {
      padding: 28px 24px;
      text-align: center;
      background: #080f14;
      border-bottom: 1px solid rgba(255,255,255,.12);
    }

    h1 {
      margin: 0;
      color: #00d1d1;
      text-transform: uppercase;
      letter-spacing: .05em;
    }

    main {
      max-width: 1200px;
      margin: 30px auto;
      padding: 0 20px;
      display: grid;
      grid-template-columns: 380px 1fr;
      gap: 24px;
    }

    .panel {
      background: rgba(255,255,255,.045);
      border: 1px solid rgba(255,255,255,.13);
      border-radius: 16px;
      padding: 20px;
    }

    label {
      display: block;
      margin-top: 16px;
      margin-bottom: 7px;
      color: #aaa;
      font-size: .82rem;
      text-transform: uppercase;
      letter-spacing: .04em;
      font-weight: 800;
    }

    input,
    select,
    button,
    textarea {
      width: 100%;
      box-sizing: border-box;
      border-radius: 10px;
      border: 1px solid rgba(255,255,255,.18);
      background: #071017;
      color: white;
      padding: 11px;
      font-size: .95rem;
    }

    button {
      margin-top: 18px;
      cursor: pointer;
      background: rgba(0, 209, 209, .18);
      border-color: #00d1d1;
      color: #00f0f0;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: .05em;
    }

    button:hover {
      background: rgba(0, 209, 209, .28);
    }

    textarea {
      min-height: 230px;
      font-family: Consolas, monospace;
      resize: vertical;
    }

    .preview-card {
      position: relative;
      overflow: hidden;
      min-height: 250px;
      border-radius: 18px;
      padding: 26px;
      border: 3px solid var(--primary);
      background:
        radial-gradient(circle at top right, color-mix(in srgb, var(--primary) 30%, transparent), transparent 42%),
        linear-gradient(135deg, var(--background), #020304);
      box-shadow:
        0 18px 40px rgba(0,0,0,.42),
        inset 0 0 24px rgba(255,255,255,.04);
    }

    .preview-logo-bg {
      position: absolute;
      right: -18px;
      bottom: -28px;
      width: 220px;
      height: 220px;
      object-fit: contain;
      opacity: .18;
      pointer-events: none;
    }

    .preview-content {
      position: relative;
      z-index: 2;
    }

    .eyebrow {
      color: var(--accent);
      font-weight: 900;
      letter-spacing: .08em;
      text-transform: uppercase;
      font-size: .82rem;
    }

    .team-name {
      margin-top: 12px;
      font-size: 2.4rem;
      font-weight: 1000;
      text-transform: uppercase;
      text-shadow: -3px 3px 0 #000;
    }

    .sub {
      margin-top: 10px;
      color: #cfcfcf;
      max-width: 450px;
    }

    .swatches {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 20px;
    }

    .swatch {
      width: 88px;
      height: 70px;
      border-radius: 10px;
      border: 1px solid rgba(255,255,255,.18);
      display: flex;
      align-items: flex-end;
      padding: 8px;
      box-sizing: border-box;
      font-size: .72rem;
      font-family: Consolas, monospace;
      text-shadow: 0 1px 2px #000;
    }

    .note {
      color: #888;
      font-size: .85rem;
      line-height: 1.45;
    }

    @media (max-width: 900px) {
      main {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>

<body>
  <header>
    <h1>Team Theme Builder</h1>
    <p class="note">Generate a copy/paste theme from a team logo. This tool does not edit metadata files.</p>
  </header>

  <main>
    <section class="panel">
      <label>Team Name</label>
      <input id="teamName" value="Example Team">

      <label>Logo Path for JSON</label>
      <input id="logoPath" value="assets/images/teams/example_team.png">

      <label>Upload Logo</label>
      <input id="logoInput" type="file" accept="image/*">

      <button onclick="generateTheme()">Generate Theme</button>

      <label>Theme JSON</label>
      <textarea id="jsonOutput" readonly></textarea>

      <button onclick="copyTheme()">Copy JSON</button>

      <p class="note">
        Use the copied block inside a team entry in <code>data/team_metadata.json</code>.
      </p>
    </section>

    <section class="panel">
      <div id="previewCard" class="preview-card" style="--primary:#d6a935;--accent:#ffffff;--background:#050505;">
        <img id="previewLogo" class="preview-logo-bg" src="" alt="">
        <div class="preview-content">
          <div class="eyebrow">SPLStats Theme Preview</div>
          <div id="previewTeamName" class="team-name">Example Team</div>
          <div class="sub">
            This is roughly how the team card could look using the generated theme.
          </div>

          <div id="swatches" class="swatches"></div>
        </div>
      </div>
    </section>
  </main>

  <script>
    let uploadedBase64 = "";
    let currentTheme = {
      primary: "#d6a935",
      secondary: "#111111",
      accent: "#ffffff",
      background: "#050505",
      card: "#111111",
      surface: "#1a1a1a"
    };

    document.getElementById("teamName").addEventListener("input", updatePreviewText);
    document.getElementById("logoPath").addEventListener("input", updateJsonOutput);

    document.getElementById("logoInput").addEventListener("change", () => {
        const file = document.getElementById("logoInput").files[0];
        if (!file) return;

        // Browser security only gives us the filename, not the full local path.
        // Since you're selecting files from SPLStats/assets/images/teams/,
        // we can safely build the website-relative path from the filename.
        const logoPath = `assets/images/teams/${file.name}`;

        document.getElementById("logoPath").value = logoPath;

        const reader = new FileReader();

        reader.onload = () => {
            uploadedBase64 = reader.result;
            document.getElementById("previewLogo").src = uploadedBase64;
            updateJsonOutput();
        };

        reader.readAsDataURL(file);
    });

    function updatePreviewText() {
      document.getElementById("previewTeamName").textContent =
        document.getElementById("teamName").value || "Example Team";

      updateJsonOutput();
    }

    function renderSwatches(theme) {
      const swatches = document.getElementById("swatches");

      swatches.innerHTML = Object.entries(theme).map(([name, color]) => `
        <div class="swatch" style="background:${color};">
          ${name}<br>${color}
        </div>
      `).join("");
    }

    function applyTheme(theme) {
      currentTheme = theme;

      const card = document.getElementById("previewCard");

      card.style.setProperty("--primary", theme.primary);
      card.style.setProperty("--accent", theme.accent);
      card.style.setProperty("--background", theme.background);

      renderSwatches(theme);
      updateJsonOutput();
    }

    function updateJsonOutput() {
      const logoPath = document.getElementById("logoPath").value.trim();

      const output = {
        logo: logoPath,
        theme: currentTheme
      };

      document.getElementById("jsonOutput").value =
        JSON.stringify(output, null, 2);
    }

    async function generateTheme() {
      const file = document.getElementById("logoInput").files[0];

      if (!file) {
        alert("Pick a logo first.");
        return;
      }

      const formData = new FormData();
      formData.append("logo", file);

      const response = await fetch("/generate", {
        method: "POST",
        body: formData
      });

      if (!response.ok) {
        alert("Theme generation failed.");
        return;
      }

      const data = await response.json();

      applyTheme(data.theme);
    }

    async function copyTheme() {
      const text = document.getElementById("jsonOutput").value;

      await navigator.clipboard.writeText(text);

      alert("Copied.");
    }

    applyTheme(currentTheme);
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def send_text(self, text, content_type="text/html", status=200):
        body = text.encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, data, status=200):
        self.send_text(
            json.dumps(data),
            "application/json",
            status
        )

    def do_GET(self):
        self.send_text(HTML)

    def do_POST(self):
        if self.path != "/generate":
            return self.send_json(
                {"error": "Not found"},
                status=404
            )

        content_type = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        boundary_match = re.search(
            r"boundary=(.+)",
            content_type
        )

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

        palette = extract_palette(image_bytes)
        theme = make_theme(palette)

        return self.send_json({
            "palette": [rgb_to_hex(rgb) for rgb in palette],
            "theme": theme
        })


def main():
    print(f"Team Theme Builder running at http://localhost:{PORT}")
    print("This tool only previews/copies JSON. It does not edit metadata files.")

    server = HTTPServer(
        ("localhost", PORT),
        Handler
    )

    server.serve_forever()


if __name__ == "__main__":
    main()