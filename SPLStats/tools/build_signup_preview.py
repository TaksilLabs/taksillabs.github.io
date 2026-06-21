import csv
import json
import re
import sys
from pathlib import Path

import requests
from PIL import Image, ImageOps
from io import BytesIO

import colorsys
from collections import defaultdict, Counter

BASE_DIR = Path(__file__).resolve().parent.parent

SIGNUPS_DIR = BASE_DIR / "raw_signups"

PLAYER_ALIASES_FILE = BASE_DIR / "data" / "player_aliases.json"
TEAM_METADATA_FILE = BASE_DIR / "data" / "team_metadata.json"

OUT_DIR = BASE_DIR / "data" / "signup_preview"
OUT_NEW_PLAYERS = OUT_DIR / "new_player_aliases.json"
OUT_NEW_TEAMS = OUT_DIR / "new_team_metadata.json"
OUT_ROSTERS = OUT_DIR / "team_rosters.json"

TEAM_IMAGES_DIR = BASE_DIR / "assets" / "images" / "teams"
LOGO_SIZE = 500


TEAM_COLS = {
    "timestamp": 0,
    "region": 2,
    "team_name": 3,
    "team_abbr": 4,
    "venue": 5,
    "logo": 6,
    "uses_gm": 7,
    "gm_discord": 8,
    "gm_steam": 9,
    "gm_slap_id": 10,
    "captain_discord": 11,
    "captain_steam": 12,
    "captain_slap_id": 13,
}


PLAYER_SLOTS = [
    {
        "role": "player",
        "discord": 14,
        "steam": 15,
        "slap_id": 16,
    },
    {
        "role": "player",
        "discord": 17,
        "steam": 18,
        "slap_id": 19,
    },
    {
        "role": "player",
        "discord": 20,
        "steam": 21,
        "slap_id": 22,
    },
    {
        "role": "player",
        "discord": 23,
        "steam": 24,
        "slap_id": 25,
    },
    {
        "role": "player",
        "discord": 26,
        "steam": 27,
        "slap_id": 28,
    },
]

def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def color_distance(a, b):
    return sum((a[i] - b[i]) ** 2 for i in range(3)) ** 0.5


def saturation(rgb):
    r, g, b = [x / 255 for x in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return s


def brightness(rgb):
    r, g, b = [x / 255 for x in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return v


def is_near_white(rgb):
    r, g, b = rgb
    return r > 235 and g > 235 and b > 235


def is_near_black(rgb):
    r, g, b = rgb
    return r < 28 and g < 28 and b < 28


def round_rgb(rgb, step=16):
    return tuple(
        max(0, min(255, round(channel / step) * step))
        for channel in rgb
    )


def extract_palette_from_image(image, max_colors=8):
    image = image.convert("RGBA")
    image.thumbnail((220, 220))

    pixels = []

    for pixel in image.getdata():
        if len(pixel) == 4 and pixel[3] < 40:
            continue

        rgb = pixel[:3]
        pixels.append(round_rgb(rgb, 16))

    counts = Counter(pixels)

    meaningful = []

    for rgb, count in counts.most_common(250):
        if is_near_white(rgb):
            continue

        if is_near_black(rgb):
            continue

        if saturation(rgb) < 0.10:
            continue

        if all(color_distance(rgb, existing) > 34 for existing in meaningful):
            meaningful.append(rgb)

        if len(meaningful) >= max_colors:
            break

    if not meaningful:
        for rgb, count in counts.most_common(250):
            if not is_near_white(rgb) and not is_near_black(rgb):
                if all(color_distance(rgb, existing) > 34 for existing in meaningful):
                    meaningful.append(rgb)

            if len(meaningful) >= max_colors:
                break

    return meaningful


def make_theme_from_palette(palette):
    if not palette:
        return {
            "primary": "#ffffff",
            "secondary": "#111111",
            "accent": "#ffffff",
            "background": "#050505",
            "card": "#111111",
            "surface": "#1a1a1a"
        }

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

    # Primary = dominant useful team color.
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

    # Secondary = dark outline/shadow color.
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

    # Accent = bright colorful highlight different from primary.
    accent_candidates = [
        rgb for rgb in palette
        if is_bright_color(rgb)
        and color_distance(rgb, primary) > 45
        and color_distance(rgb, secondary_rgb) > 35
        and not is_near_white(rgb)
    ]

    accent_rgb = (
        accent_candidates[0]
        if accent_candidates
        else primary
    )

    return {
        "primary": rgb_to_hex(primary),
        "secondary": rgb_to_hex(secondary_rgb),
        "accent": rgb_to_hex(accent_rgb),
        "background": "#050505",
        "card": "#111111",
        "surface": "#1a1a1a"
    }


def make_theme_from_image(image):
    palette = extract_palette_from_image(image)
    return make_theme_from_palette(palette)

def load_json_or_fallback(path, fallback):
    if not path.exists():
        return fallback

    text = path.read_text(encoding="utf-8").strip()

    if not text:
        return fallback

    return json.loads(text)

def extract_google_drive_file_id(url):
    text = clean_text(url)

    if not text:
        return ""

    patterns = [
        r"/file/d/([^/]+)",
        r"id=([^&]+)",
        r"/open\?id=([^&]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return match.group(1)

    return ""


def get_download_url(url):
    file_id = extract_google_drive_file_id(url)

    if file_id:
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    return url


def download_image_bytes(url):
    download_url = get_download_url(url)

    response = requests.get(
        download_url,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()

    if "text/html" in content_type:
        raise ValueError(
            "Downloaded HTML instead of an image. "
            "The Google Drive file may not be publicly accessible."
        )

    return response.content


def normalize_logo_image(image_bytes):
    image = Image.open(BytesIO(image_bytes)).convert("RGBA")

    # Fit into a 500x500 transparent canvas without stretching.
    image.thumbnail(
        (LOGO_SIZE, LOGO_SIZE),
        Image.Resampling.LANCZOS
    )

    canvas = Image.new(
        "RGBA",
        (LOGO_SIZE, LOGO_SIZE),
        (0, 0, 0, 0)
    )

    x = (LOGO_SIZE - image.width) // 2
    y = (LOGO_SIZE - image.height) // 2

    canvas.alpha_composite(image, (x, y))

    return canvas


def save_team_logo_from_url(team_name, logo_url):
    if not logo_url:
        return "", {
            "primary": "#ffffff",
            "secondary": "#111111",
            "accent": "#ffffff",
            "background": "#050505",
            "card": "#111111",
            "surface": "#1a1a1a"
        }

    TEAM_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{make_id(team_name, 'team_logo')}.png"
    output_path = TEAM_IMAGES_DIR / filename

    try:
        image_bytes = download_image_bytes(logo_url)

        image = normalize_logo_image(image_bytes)

        theme = make_theme_from_image(image)

        image.save(output_path, "PNG")

        logo_path = str(
            output_path.relative_to(BASE_DIR)
        ).replace("\\", "/")

        return logo_path, theme

    except Exception as error:
        print()
        print(f"WARNING: Could not download/process logo for {team_name}")
        print(f"  URL: {logo_url}")
        print(f"  Error: {error}")
        print()

        return "", {
            "primary": "#ffffff",
            "secondary": "#111111",
            "accent": "#ffffff",
            "background": "#050505",
            "card": "#111111",
            "surface": "#1a1a1a"
        }

def clean_text(value):
    return str(value or "").strip()


def make_id(value, fallback="unknown"):
    text = clean_text(value).lower()

    text = re.sub(r"[^a-z0-9_\-\s]", "", text)
    text = re.sub(r"[\s\-]+", "_", text)
    text = re.sub(r"_+", "_", text)

    return text.strip("_") or fallback


def clean_slap_id(value):
    text = clean_text(value)

    if not text:
        return ""

    # Keep numeric IDs clean even if Google Sheets made them weird.
    try:
        number = int(float(text))
        return str(number)
    except Exception:
        return text


def get_cell(row, index):
    if index >= len(row):
        return ""

    return clean_text(row[index])


def normalize_key(value):
    return clean_text(value).lower()


def load_existing_player_lookup():
    entries = load_json_or_fallback(PLAYER_ALIASES_FILE, [])

    lookup = set()

    for entry in entries:
        player_id = entry.get("player_id")
        display_name = entry.get("player_display_name")

        if player_id:
            lookup.add(normalize_key(player_id))

        if display_name:
            lookup.add(normalize_key(display_name))

        for alias in entry.get("aliases", []):
            lookup.add(normalize_key(alias))

        for slap_id in entry.get("slap_ids", []):
            lookup.add(f"slap:{clean_slap_id(slap_id)}")

    return lookup


def load_existing_team_lookup():
    entries = load_json_or_fallback(TEAM_METADATA_FILE, [])

    lookup = set()

    for entry in entries:
        team_id = entry.get("team_id")
        display_name = entry.get("team_display_name")

        if team_id:
            lookup.add(normalize_key(team_id))

        if display_name:
            lookup.add(normalize_key(display_name))

        for alias in entry.get("aliases", []):
            lookup.add(normalize_key(alias))

    return lookup


def build_player_entry(steam_name, discord_tag, slap_id):
    steam_name = clean_text(steam_name)
    discord_tag = clean_text(discord_tag)
    slap_id = clean_slap_id(slap_id)

    display_name = steam_name or discord_tag or slap_id

    player_id = make_id(display_name, "unknown_player")

    aliases = []

    for alias in [
        steam_name,
        discord_tag,
    ]:
        if alias and alias not in aliases:
            aliases.append(alias)

    return {
        "player_id": player_id,
        "player_display_name": display_name,
        "aliases": aliases,
        "slap_ids": [slap_id] if slap_id else []
    }


def player_already_exists(player, existing_lookup):
    if normalize_key(player["player_id"]) in existing_lookup:
        return True

    if normalize_key(player["player_display_name"]) in existing_lookup:
        return True

    for alias in player.get("aliases", []):
        if normalize_key(alias) in existing_lookup:
            return True

    for slap_id in player.get("slap_ids", []):
        if f"slap:{clean_slap_id(slap_id)}" in existing_lookup:
            return True

    return False


def build_team_entry(team_name, team_abbr, venue, logo_url):
    team_id = make_id(team_name, "unknown_team")

    logo_path, theme = save_team_logo_from_url(
        team_name,
        logo_url
    )

    return {
        "team_id": team_id,
        "team_display_name": team_name,
        "aliases": [
            team_name
        ],
        "abbreviation": team_abbr,
        "venue": venue,
        "signup_logo_url": logo_url,
        "logo": logo_path,
        "theme": theme,
        "name_history": [
            {
                "name": team_name,
                "start_season": None,
                "end_season": None
            }
        ]
    }


def team_already_exists(team, existing_lookup):
    if normalize_key(team["team_id"]) in existing_lookup:
        return True

    if normalize_key(team["team_display_name"]) in existing_lookup:
        return True

    for alias in team.get("aliases", []):
        if normalize_key(alias) in existing_lookup:
            return True

    return False


def add_unique_player(players_by_key, player):
    slap_ids = player.get("slap_ids", [])

    if slap_ids:
        key = f"slap:{slap_ids[0]}"
    else:
        key = normalize_key(player["player_id"])

    if key not in players_by_key:
        players_by_key[key] = player
        return

    existing = players_by_key[key]

    for alias in player.get("aliases", []):
        if alias and alias not in existing["aliases"]:
            existing["aliases"].append(alias)

    for slap_id in player.get("slap_ids", []):
        if slap_id and slap_id not in existing["slap_ids"]:
            existing["slap_ids"].append(slap_id)


def parse_signup_csv(csv_path):
    existing_players = load_existing_player_lookup()
    existing_teams = load_existing_team_lookup()

    new_players_by_key = {}
    new_teams = []
    rosters = []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)

        headers = next(reader, None)

        for row in reader:
            team_name = get_cell(row, TEAM_COLS["team_name"])

            if not team_name:
                continue

            region = get_cell(row, TEAM_COLS["region"])
            team_abbr = get_cell(row, TEAM_COLS["team_abbr"])
            venue = get_cell(row, TEAM_COLS["venue"])
            logo_url = get_cell(row, TEAM_COLS["logo"])

            team = build_team_entry(
                team_name=team_name,
                team_abbr=team_abbr,
                venue=venue,
                logo_url=logo_url
            )

            if not team_already_exists(team, existing_teams):
                new_teams.append(team)

            roster_players = []

            captain = build_player_entry(
                steam_name=get_cell(row, TEAM_COLS["captain_steam"]),
                discord_tag=get_cell(row, TEAM_COLS["captain_discord"]),
                slap_id=get_cell(row, TEAM_COLS["captain_slap_id"])
            )

            if captain["player_display_name"]:
                captain_roster_entry = {
                    **captain,
                    "role": "captain"
                }

                roster_players.append(captain_roster_entry)

                if not player_already_exists(captain, existing_players):
                    add_unique_player(new_players_by_key, captain)

            uses_gm = get_cell(row, TEAM_COLS["uses_gm"]).lower()

            if uses_gm == "yes":
                gm = build_player_entry(
                    steam_name=get_cell(row, TEAM_COLS["gm_steam"]),
                    discord_tag=get_cell(row, TEAM_COLS["gm_discord"]),
                    slap_id=get_cell(row, TEAM_COLS["gm_slap_id"])
                )

                if gm["player_display_name"]:
                    roster_players.append({
                        **gm,
                        "role": "gm"
                    })

                    if not player_already_exists(gm, existing_players):
                        add_unique_player(new_players_by_key, gm)

            for slot in PLAYER_SLOTS:
                player = build_player_entry(
                    steam_name=get_cell(row, slot["steam"]),
                    discord_tag=get_cell(row, slot["discord"]),
                    slap_id=get_cell(row, slot["slap_id"])
                )

                if not player["player_display_name"]:
                    continue

                roster_players.append({
                    **player,
                    "role": "player"
                })

                if not player_already_exists(player, existing_players):
                    add_unique_player(new_players_by_key, player)

            rosters.append({
                "team_id": team["team_id"],
                "team_display_name": team["team_display_name"],
                "team_abbreviation": team_abbr,
                "region": region,
                "venue": venue,
                "signup_logo_url": logo_url,
                "logo": team.get("logo", ""),
                "players": roster_players
            })

    new_players = sorted(
        new_players_by_key.values(),
        key=lambda p: p["player_display_name"].lower()
    )

    new_teams.sort(
        key=lambda t: t["team_display_name"].lower()
    )

    rosters.sort(
        key=lambda r: r["team_display_name"].lower()
    )

    return new_players, new_teams, rosters


def main():
    csv_files = sorted(SIGNUPS_DIR.glob("*.csv"))

    if not csv_files:
        print(f"No signup CSV files found in:")
        print(f"  {SIGNUPS_DIR}")
        print()
        print("Drop exported Google Form signup CSVs into that folder.")
        return

    all_new_players_by_key = {}
    all_new_teams_by_id = {}
    all_rosters = []

    for csv_path in csv_files:
        print(f"Reading signup CSV: {csv_path.name}")

        new_players, new_teams, rosters = parse_signup_csv(csv_path)

        for player in new_players:
            slap_ids = player.get("slap_ids", [])

            if slap_ids:
                key = f"slap:{slap_ids[0]}"
            else:
                key = normalize_key(player["player_id"])

            if key not in all_new_players_by_key:
                all_new_players_by_key[key] = player
            else:
                existing = all_new_players_by_key[key]

                for alias in player.get("aliases", []):
                    if alias and alias not in existing["aliases"]:
                        existing["aliases"].append(alias)

                for slap_id in player.get("slap_ids", []):
                    if slap_id and slap_id not in existing["slap_ids"]:
                        existing["slap_ids"].append(slap_id)

        for team in new_teams:
            team_id = team["team_id"]

            if team_id not in all_new_teams_by_id:
                all_new_teams_by_id[team_id] = team

        all_rosters.extend(rosters)

    new_players = sorted(
        all_new_players_by_key.values(),
        key=lambda p: p["player_display_name"].lower()
    )

    new_teams = sorted(
        all_new_teams_by_id.values(),
        key=lambda t: t["team_display_name"].lower()
    )

    all_rosters.sort(
        key=lambda r: r["team_display_name"].lower()
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    OUT_NEW_PLAYERS.write_text(
        json.dumps(new_players, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    OUT_NEW_TEAMS.write_text(
        json.dumps(new_teams, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    OUT_ROSTERS.write_text(
        json.dumps(all_rosters, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print()
    print("=" * 70)
    print("SIGNUP PREVIEW BUILT")
    print("=" * 70)
    print(f"Signup CSVs read:  {len(csv_files)}")
    print(f"New players found: {len(new_players)}")
    print(f"New teams found:   {len(new_teams)}")
    print(f"Rosters found:     {len(all_rosters)}")
    print()
    print(f"Wrote: {OUT_NEW_PLAYERS}")
    print(f"Wrote: {OUT_NEW_TEAMS}")
    print(f"Wrote: {OUT_ROSTERS}")


if __name__ == "__main__":
    main()