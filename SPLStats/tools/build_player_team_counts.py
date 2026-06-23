import csv
import json
import re
import unicodedata
from pathlib import Path
from collections import defaultdict


BASE_DIR = Path(__file__).resolve().parents[1]
OUT_FILE = BASE_DIR / "data" / "player_team_counts.json"


def clean_text(value):
    return str(value or "").strip()


def strip_accents(value):
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", clean_text(value))
        if not unicodedata.combining(char)
    )


def make_id(value):
    value = strip_accents(value).lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value


def find_lr_csv_files():
    csv_files = []

    for path in BASE_DIR.rglob("*.csv"):
        normalized = str(path).replace("\\", "/").lower()

        # Skip generated/data/admin inputs that are not LR stat exports.
        if "/data/" in normalized:
            continue

        if "/raw_signups/" in normalized:
            continue

        if ".git/" in normalized:
            continue

        # We only keep files that look like LR stat exports by header.
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as file:
                reader = csv.DictReader(file)
                headers = set(reader.fieldnames or [])

            required = {
                "Fixture Group",
                "Fixture Date",
                "First Name",
                "Last Name",
                "Team",
                "Stat Desc",
                "Stat Value",
            }

            if required.issubset(headers):
                csv_files.append(path)

        except Exception:
            continue

    return sorted(csv_files)


def get_season_from_filename(path):
    name = path.stem
    name = name.replace("_", " ").replace("-", " ")
    return " ".join(name.split())


def main():
    player_data = defaultdict(lambda: {
        "player": "",
        "player_id": "",
        "teams": {},
        "seasons": set(),
        "rows": 0,
    })

    csv_files = find_lr_csv_files()

    for csv_file in csv_files:
        season = get_season_from_filename(csv_file)

        with csv_file.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            for row in reader:
                player_name = clean_text(row.get("Last Name"))
                team_name = clean_text(row.get("Team"))
                team_abbr = clean_text(row.get("First Name"))
                fixture_group = clean_text(row.get("Fixture Group"))

                if not player_name:
                    continue

                # Prefer full team name. Fall back to LR First Name/team abbreviation.
                team_display = team_name or team_abbr

                if not team_display:
                    continue

                player_id = make_id(player_name)
                team_id = make_id(team_display)

                if not player_id or not team_id:
                    continue

                entry = player_data[player_id]

                entry["player"] = player_name
                entry["player_id"] = player_id
                entry["rows"] += 1
                entry["seasons"].add(season)

                if team_id not in entry["teams"]:
                    entry["teams"][team_id] = {
                        "team_id": team_id,
                        "team": team_display,
                        "team_abbreviation": team_abbr,
                        "seasons": set(),
                        "fixture_groups": set(),
                    }

                entry["teams"][team_id]["seasons"].add(season)

                if fixture_group:
                    entry["teams"][team_id]["fixture_groups"].add(fixture_group)

    output = []

    for player_id, entry in player_data.items():
        teams = []

        for team in entry["teams"].values():
            teams.append({
                "team_id": team["team_id"],
                "team": team["team"],
                "team_abbreviation": team["team_abbreviation"],
                "seasons": sorted(team["seasons"]),
                "fixture_groups": sorted(team["fixture_groups"]),
            })

        teams.sort(key=lambda team: team["team"].lower())

        output.append({
            "player_id": player_id,
            "player": entry["player"],
            "team_count": len(teams),
            "teams": teams,
            "seasons": sorted(entry["seasons"]),
            "row_count": entry["rows"],
        })

    output.sort(
        key=lambda player: (
            -player["team_count"],
            player["player"].lower()
        )
    )

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(output, file, indent=2, ensure_ascii=False)

    print(f"CSV files scanned: {len(csv_files)}")
    print(f"Players found: {len(output)}")
    print(f"Wrote: {OUT_FILE}")

    print()
    print("Top 10 players by unique teams:")
    for player in output[:10]:
        print(f"{player['team_count']:>2} teams - {player['player']}")


if __name__ == "__main__":
    main()