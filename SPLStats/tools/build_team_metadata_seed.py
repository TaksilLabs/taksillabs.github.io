import csv
import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_CSV_DIR = BASE_DIR.parent / "SPLStats/raw_csv"
OUTPUT_FILE = BASE_DIR / "data" / "team_metadata.json"


TEAM_COLUMNS = [
    "Team",
    "Home Team",
    "Away Team"
]


def make_team_id(name):
    text = clean_team_name(name).lower()

    # Remove trailing region/duplicate suffixes for ID generation guesses.
    text = re.sub(r"\s+-\s+(east|central|west)$", "", text)

    text = re.sub(r"[^a-z0-9_\-\s]", "", text)
    text = re.sub(r"[\s\-]+", "_", text)
    text = re.sub(r"_+", "_", text)

    return text.strip("_") or "unknown_team"


def clean_team_name(name):
    text = str(name or "").strip()

    # Remove trailing LeagueRepublic code tags like:
    # "Maui Monkeys (DCUW)"
    # "Example Team (ABC)"
    text = re.sub(r"\s*\([A-Z0-9]{2,8}\)\s*$", "", text)

    return text.strip()


def load_existing_metadata():
    if not OUTPUT_FILE.exists():
        return []

    with OUTPUT_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def collect_existing_aliases(existing_entries):
    aliases = set()

    for entry in existing_entries:
        for alias in entry.get("aliases", []):
            aliases.add(alias.lower().strip())

        display_name = entry.get("team_display_name")
        if display_name:
            aliases.add(display_name.lower().strip())

    return aliases


def scan_csv_teams():
    teams = set()

    csv_files = sorted(RAW_CSV_DIR.glob("*.csv"))

    if not csv_files:
        print(f"No CSV files found in: {RAW_CSV_DIR}")
        return teams

    for csv_file in csv_files:
        print(f"Scanning {csv_file.name}")

        with csv_file.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                for column in TEAM_COLUMNS:
                    value = clean_team_name(row.get(column, ""))

                    if value:
                        teams.add(value)

    return teams


def build_seed_entry(team_name):
    team_id = make_team_id(team_name)

    return {
        "team_id": team_id,
        "team_display_name": team_name,
        "aliases": [
            team_name
        ],
        "logo": "",
        "theme": {
            "primary": "#ffffff",
            "secondary": "#111111",
            "accent": "#ffd166",
            "background": "#050505",
            "card": "#111111",
            "surface": "#1a1a1a"
        },
        "name_history": [
            {
                "name": team_name,
                "start_season": None,
                "end_season": None
            }
        ]
    }


def main():
    existing_entries = load_existing_metadata()
    existing_aliases = collect_existing_aliases(existing_entries)

    raw_teams = scan_csv_teams()

    new_entries = []

    for team_name in sorted(raw_teams, key=lambda name: name.lower()):
        key = team_name.lower().strip()

        if key in existing_aliases:
            continue

        new_entries.append(build_seed_entry(team_name))

    combined = existing_entries + new_entries

    combined.sort(
        key=lambda entry: entry.get("team_display_name", "").lower()
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    print()
    print(f"Existing entries kept: {len(existing_entries)}")
    print(f"New entries added: {len(new_entries)}")
    print(f"Total entries written: {len(combined)}")
    print(f"Wrote: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()