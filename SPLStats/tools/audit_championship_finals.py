import csv
import json
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime


RAW_CSV_DIR = Path("../raw_csv")
DIVISION_NAMES_FILE = Path("../data/division_display_names.json")


CHAMPIONSHIPS = {
    "Erveon Cup Playoffs": {
        "region": "East",
        "championship": "Erveon Cup",
        "regular_divisions": [
            "Pro Division"
        ]
    },

    "Gazz Cup Playoffs": {
        "region": "Central",
        "championship": "Gazz Cup",
        "regular_divisions": [
            "Central A"
        ]
    },

    "Pacific Cup Playoffs": {
        "region": "West",
        "championship": "Pacific Cup",
        "regular_divisions": [
            "West Division",
            "Masters Division"
        ]
    }
}


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def season_from_filename(path):
    stem = path.stem
    raw = stem.replace("SPL-", "")

    match = re.match(r"([A-Za-z]+)(\d{4})", raw)

    if not match:
        return raw, raw.lower()

    season_word = match.group(1)
    year = match.group(2)

    return (
        f"{season_word} {year}",
        f"{season_word.lower()}_{year}"
    )


def clean_team_name(team_name):
    return re.sub(
        r"\s*\([^)]*\)\s*$",
        "",
        str(team_name).strip()
    ).strip()


def normalize_division_name(division, division_map):
    return (
        division_map.get(division)
        or division
        or "Unknown"
    )


def safe_int(value):
    try:
        return int(float(value))
    except Exception:
        return 0


def parse_date(value):
    text = str(value or "").strip()

    formats = [
        "%a %d %b %Y %I:%M %p",      # Mon 23 Feb 2026 12:00 PM
        "%A %d %b %Y %I:%M %p",      # Monday 23 Feb 2026 12:00 PM
        "%a %d %B %Y %I:%M %p",      # Mon 23 February 2026 12:00 PM
        "%A %d %B %Y %I:%M %p",      # Monday 23 February 2026 12:00 PM

        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%d/%m/%Y",
        "%d/%m/%y"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            pass

    print(f"WARNING: Could not parse date: {text}")
    return datetime.min


def fixture_id(row, season_id):
    return "|".join([
        season_id,
        row.get("Fixture Group", "").strip(),
        row.get("Fixture Date", "").strip(),
        clean_team_name(row.get("Home Team", "")),
        clean_team_name(row.get("Away Team", "")),
    ])


def main():
    division_map = load_json(DIVISION_NAMES_FILE)

    finals_by_season_cup = defaultdict(dict)

    csv_files = sorted(RAW_CSV_DIR.glob("SPL-*.csv"))

    for csv_file in csv_files:
        season_name, season_id = season_from_filename(csv_file)

        matches = {}

        with csv_file.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                stat_desc = row.get("Stat Desc", "").strip().lower()

                if stat_desc != "goals":
                    continue

                raw_group = row.get("Fixture Group", "").strip()
                division = normalize_division_name(raw_group, division_map)

                if division not in CHAMPIONSHIPS:
                    continue

                fid = fixture_id(row, season_id)

                if fid not in matches:
                    matches[fid] = {
                        "fixture_id": fid,
                        "season": season_name,
                        "season_id": season_id,
                        "division": division,
                        "region": CHAMPIONSHIPS[division]["region"],
                        "championship": CHAMPIONSHIPS[division]["championship"],
                        "fixture_date": row.get("Fixture Date", "").strip(),
                        "home_team": clean_team_name(row.get("Home Team", "")),
                        "away_team": clean_team_name(row.get("Away Team", "")),
                        "scores": defaultdict(int),
                    }

                team = clean_team_name(row.get("Team", ""))
                goals = safe_int(row.get("Stat Value", 0))

                matches[fid]["scores"][team] += goals

        for match in matches.values():
            home = match["home_team"]
            away = match["away_team"]

            match["home_score"] = match["scores"].get(home, 0)
            match["away_score"] = match["scores"].get(away, 0)

            key = (
                match["season_id"],
                match["championship"]
            )

            current = finals_by_season_cup.get(key)

            if (
                not current
                or parse_date(match["fixture_date"]) > parse_date(current["fixture_date"])
            ):
                finals_by_season_cup[key] = match

    print()
    print("=" * 80)
    print("DETECTED CHAMPIONSHIP FINALS")
    print("=" * 80)

    for key, match in sorted(finals_by_season_cup.items()):
        home = match["home_team"]
        away = match["away_team"]

        home_score = match["home_score"]
        away_score = match["away_score"]

        if home_score > away_score:
            winner = home
            loser = away
        elif away_score > home_score:
            winner = away
            loser = home
        else:
            winner = "TIED / UNKNOWN"
            loser = "TIED / UNKNOWN"

        print()
        print(
            f"{match['season']} | "
            f"{match['region']} | "
            f"{match['championship']}"
        )

        print(
            f"  Date: {match['fixture_date']}"
        )

        print(
            f"  {home} {home_score} - "
            f"{away_score} {away}"
        )

        print(
            f"  Winner: {winner}"
        )

        if loser != "TIED / UNKNOWN":
            print(
                f"  Runner-up: {loser}"
            )


if __name__ == "__main__":
    main()