import subprocess
import sys
import colorsys
import json
from collections import Counter
from pathlib import Path

from PIL import Image


BASE_DIR = Path(__file__).resolve().parent.parent
TEAM_METADATA_FILE = BASE_DIR / "data" / "team_metadata.json"
TEAM_IMAGES_DIR = BASE_DIR / "assets" / "images" / "teams"

SUPPORTED_EXTENSIONS = [
    ".png",
    ".jpg",
    ".jpeg",
    ".webp"
]


def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def color_distance(a, b):
    return sum((a[i] - b[i]) ** 2 for i in range(3)) ** 0.5


def saturation(rgb):
    r, g, b = [x / 255 for x in rgb]
    _, s, _ = colorsys.rgb_to_hsv(r, g, b)
    return s


def brightness(rgb):
    r, g, b = [x / 255 for x in rgb]
    _, _, v = colorsys.rgb_to_hsv(r, g, b)
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


def iter_image_pixels(image):
    if hasattr(image, "get_flattened_data"):
        return image.get_flattened_data()

    return image.getdata()


def extract_palette_from_image(image, max_colors=8):
    image = image.convert("RGBA")
    image.thumbnail((220, 220))

    pixels = []

    for pixel in iter_image_pixels(image):
        if len(pixel) == 4 and pixel[3] < 40:
            continue

        rgb = pixel[:3]
        pixels.append(round_rgb(rgb, 16))

    counts = Counter(pixels)

    meaningful = []

    for rgb, _count in counts.most_common(250):
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
        for rgb, _count in counts.most_common(250):
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


def make_theme_from_logo(logo_path):
    with Image.open(logo_path) as image:
        palette = extract_palette_from_image(image)
        return make_theme_from_palette(palette)


def find_logo_for_team_id(team_id):
    for extension in SUPPORTED_EXTENSIONS:
        logo_path = TEAM_IMAGES_DIR / f"{team_id}{extension}"

        if logo_path.exists():
            return logo_path

    return None


def path_for_site(path):
    return str(
        path.relative_to(BASE_DIR)
    ).replace("\\", "/")


def load_team_metadata():
    with TEAM_METADATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_team_metadata(metadata):
    with TEAM_METADATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2, ensure_ascii=False)
        file.write("\n")


def main():
    metadata = load_team_metadata()

    updated = 0
    missing = 0

    for team in metadata:
        team_id = team.get("team_id")

        if not team_id:
            continue

        logo_path = find_logo_for_team_id(team_id)

        if not logo_path:
            missing += 1
            print(f"Missing logo: {team_id}")
            continue

        theme = make_theme_from_logo(logo_path)

        team["logo"] = path_for_site(logo_path)
        team["theme"] = theme

        updated += 1

        print(
            f"Updated {team_id}: "
            f"{team['logo']} "
            f"{theme['primary']} / {theme['secondary']} / {theme['accent']}"
        )

    save_team_metadata(metadata)

    print()
    print(f"Done.")
    print(f"Updated teams: {updated}")
    print(f"Missing logos: {missing}")


if __name__ == "__main__":
    main()