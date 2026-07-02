import json
import re
import zipfile
from pathlib import Path

TEAM_METADATA_FILE = Path("../data/team_metadata.json")
LIVE_SEASON_DIR = Path("../data/live_season")
LOGOS_DIR = Path("../assets/images/teams")
OUTPUT_ZIP = Path("../downloads/slapshot-clubs-pack.zip")


# ----------------------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------------------

def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def current_season():
    # live_season/ always contains exactly one folder: whichever season is
    # currently in progress. Unlike team_records.json's `seasons` field
    # (only populated once a season's stats are aggregated), this is never
    # stale while a season is still being played.
    seasons = [p.name for p in LIVE_SEASON_DIR.iterdir() if p.is_dir()]

    if len(seasons) != 1:
        raise RuntimeError(f"Expected exactly one live_season directory, found: {seasons}")

    return seasons[0]


def active_team_ids(season):
    rosters = load_json(LIVE_SEASON_DIR / season / "active_rosters.json")
    return [t["team_id"] for t in rosters["teams"] if t.get("team_id")]


def initials_acronym(name):
    # Cosmetic only (lobby UI / scorebug) — clubs.json's `key` is the real
    # unique identifier, so acronym collisions are fine (the source data
    # itself has duplicates, e.g. "BBPA" and "YETI" each used by two teams).
    words = re.findall(r"[A-Za-z0-9]+", name)
    return "".join(w[0] for w in words).upper()[:5] or "TEAM"


def build_club_entry(team_id, meta):
    theme = meta.get("theme") or {}
    primary = theme.get("primary", "#ffffff")
    secondary = theme.get("secondary", "#111111")
    name = meta.get("team_display_name") or team_id

    return {
        "key": team_id,
        "acronym": meta.get("abbreviation") or initials_acronym(name),
        "name": name,
        "logo": f"logos/{team_id}.png",
        "goal_horn": "",
        "colors": {
            "home": {
                "primary": primary,
                "secondary": secondary,
                "scorebug": primary,
                "nametag": primary
            },
            "away": {
                "primary": secondary,
                "secondary": primary,
                "scorebug": secondary,
                "nametag": secondary
            }
        }
    }


# ----------------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------------

def main():
    metadata_by_id = {t["team_id"]: t for t in load_json(TEAM_METADATA_FILE) if t.get("team_id")}

    season = current_season()
    team_ids = sorted(
        tid for tid in active_team_ids(season)
        if metadata_by_id.get(tid, {}).get("logo")
    )

    OUTPUT_ZIP.parent.mkdir(parents=True, exist_ok=True)

    clubs = []
    skipped = []

    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for team_id in team_ids:
            meta = metadata_by_id[team_id]
            logo_path = LOGOS_DIR / Path(meta["logo"]).name

            if not logo_path.exists():
                skipped.append(team_id)
                continue

            clubs.append(build_club_entry(team_id, meta))
            zf.write(logo_path, f"logos/{team_id}.png")

        zf.writestr("clubs.json", json.dumps(clubs, indent=2))

    print(f"Season: {season}")
    print(f"Clubs packed: {len(clubs)}")
    if skipped:
        print(f"Skipped (logo file missing on disk): {skipped}")
    print(f"Wrote: {OUTPUT_ZIP.resolve()}")


if __name__ == "__main__":
    main()
