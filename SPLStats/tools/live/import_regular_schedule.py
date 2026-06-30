import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path


SEASON_ID = "summer_2026"
SEASON_TYPE = "regular_season"

BASE_DIR = Path(__file__).resolve().parents[2]

LIVE_SEASON_DIR = BASE_DIR / "data" / "live_season" / SEASON_ID
ACTIVE_ROSTERS_FILE = LIVE_SEASON_DIR / "active_rosters.json"

REGULAR_SEASON_DIR = LIVE_SEASON_DIR / "regular_season"
SOURCE_SCHEDULE_DIR = REGULAR_SEASON_DIR / "source" / "schedules"
OUTPUT_FILE = REGULAR_SEASON_DIR / "schedule.json"
TEAM_ALIASES_FILE = LIVE_SEASON_DIR / "team_aliases.json"


def clean(value):
    return str(value or "").strip()


def normalize_team_id(value):
    text = clean(value).lower()

    text = text.replace("&", "and")
    text = text.replace("'", "")
    text = text.replace("’", "")

    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    text = text.strip("_")

    return text


def normalize_division(value):
    text = clean(value).lower()

    text = text.replace("-", "_")
    text = text.replace(" ", "_")
    text = re.sub(r"_+", "_", text)
    text = text.strip("_")

    return text


def load_json(path, fallback):
    if not path.exists():
        return fallback

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def get_active_roster_teams(active_rosters):
    if isinstance(active_rosters, list):
        return active_rosters

    if isinstance(active_rosters, dict) and isinstance(active_rosters.get("teams"), list):
        return active_rosters["teams"]

    return []


def build_active_team_lookup(active_rosters, team_aliases=None):
    lookup = {}

    for team in get_active_roster_teams(active_rosters):
        keys = [
            team.get("team_id"),
            team.get("team_name"),
            team.get("team_display_name"),
            team.get("team"),
            team.get("name"),
        ]

        for alias in team.get("aliases", []) or []:
            keys.append(alias)

        for alias in team.get("team_aliases", []) or []:
            keys.append(alias)

        for key in keys:
            normalized = normalize_team_id(key)

            if normalized:
                lookup[normalized] = team

    team_aliases = team_aliases or {}

    for lr_name, real_name in team_aliases.items():
        lr_key = normalize_team_id(lr_name)
        real_key = normalize_team_id(real_name)

        if lr_key and real_key and real_key in lookup:
            lookup[lr_key] = lookup[real_key]
    
    return lookup


def get_team_display_name(team, fallback):
    if not team:
        return clean(fallback)

    return (
        team.get("team_display_name")
        or team.get("team_name")
        or team.get("team")
        or team.get("name")
        or team.get("team_id")
        or clean(fallback)
    )


def get_active_team_info(team_name, active_team_lookup):
    key = normalize_team_id(team_name)
    team = active_team_lookup.get(key)

    if not team:
        return {
            "matched": False,
            "team_id": key,
            "team": clean(team_name),
            "division": "",
            "conference": "",
            "region": "",
        }

    return {
        "matched": True,
        "team_id": team.get("team_id") or key,
        "team": get_team_display_name(team, team_name),
        "division": normalize_division(team.get("division")),
        "conference": clean(team.get("conference")),
        "region": clean(team.get("region")).lower(),
    }


def parse_source_id(value):
    text = clean(value)

    if "." not in text:
        return 0, 0

    week_text, match_text = text.split(".", 1)

    try:
        week = int(week_text)
    except ValueError:
        week = 0

    try:
        match_number = int(match_text)
    except ValueError:
        match_number = 0

    return week, match_number


def classify_match_scope(home_info, away_info):
    home_division = home_info.get("division") or ""
    away_division = away_info.get("division") or ""

    home_conference = clean(home_info.get("conference"))
    away_conference = clean(away_info.get("conference"))

    if not home_division or not away_division:
        return "unknown"

    if home_division != away_division:
        return "outer-division"

    if not home_conference or not away_conference:
        return "same-division"

    if home_conference == away_conference:
        return "inner-conference"

    return "cross-conference"


def get_match_division(home_info, away_info, fallback_division):
    home_division = home_info.get("division") or ""
    away_division = away_info.get("division") or ""

    if home_division and home_division == away_division:
        return home_division

    if home_division and not away_division:
        return home_division

    if away_division and not home_division:
        return away_division

    return normalize_division(fallback_division)


def make_match_id(division, week, match_number):
    return f"{SEASON_ID}_{SEASON_TYPE}_{division}_{week}_{match_number}"


def normalize_status(state):
    text = clean(state).lower()

    if text in {"complete", "completed", "final", "done"}:
        return "final"

    if text in {"cancelled", "canceled"}:
        return "cancelled"

    if text in {"forfeit", "ff"}:
        return "forfeit"

    return "scheduled"


def read_schedule_csv(path, active_team_lookup):
    fallback_division = normalize_division(path.stem)
    matches = []
    warnings = []

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        required_headers = {"Home Team", "Away Team", "Id", "Thread Name"}

        missing = sorted(required_headers - set(reader.fieldnames or []))

        if missing:
            raise ValueError(
                f"{path} is missing required headers: {', '.join(missing)}"
            )

        for row_number, row in enumerate(reader, start=2):
            home_name = clean(row.get("Home Team"))
            away_name = clean(row.get("Away Team"))
            source_id = clean(row.get("Id"))

            if not home_name and not away_name:
                continue

            week, match_number = parse_source_id(source_id)

            if not week or not match_number:
                warnings.append(
                    f"{path.name} row {row_number}: could not parse Id '{source_id}'"
                )

            home_info = get_active_team_info(home_name, active_team_lookup)
            away_info = get_active_team_info(away_name, active_team_lookup)

            if not home_info["matched"]:
                warnings.append(
                    f"{path.name} row {row_number}: unmatched home team '{home_name}'"
                )

            if not away_info["matched"]:
                warnings.append(
                    f"{path.name} row {row_number}: unmatched away team '{away_name}'"
                )

            division = get_match_division(home_info, away_info, fallback_division)
            match_scope = classify_match_scope(home_info, away_info)

            if match_scope == "outer-division":
                warnings.append(
                    f"{path.name} row {row_number}: outer-division match: "
                    f"{home_name} ({home_info.get('division')}) vs "
                    f"{away_name} ({away_info.get('division')})"
                )

            match_id = make_match_id(division, week, match_number)

            matches.append({
                "match_id": match_id,
                "source_id": source_id,
                "season_id": SEASON_ID,
                "season_type": SEASON_TYPE,

                "division": division,
                "week": week,
                "match_number": match_number,
                "lr_group": clean(row.get("LR DATE")),

                "home_team": home_info["team"],
                "home_team_id": home_info["team_id"],
                "home_division": home_info["division"],
                "home_conference": home_info["conference"],
                "home_region": home_info["region"],

                "away_team": away_info["team"],
                "away_team_id": away_info["team_id"],
                "away_division": away_info["division"],
                "away_conference": away_info["conference"],
                "away_region": away_info["region"],

                "match_scope": match_scope,
                "thread_name": clean(row.get("Thread Name")),
                "status": normalize_status(row.get("State")),

                "source": {
                    "file": path.name,
                    "row": row_number,
                    "home_gm": clean(row.get("Home GM")),
                    "away_gm": clean(row.get("Away GM")),
                    "week": clean(row.get("Week")),
                    "lr_date": clean(row.get("LR DATE")),
                    "state": clean(row.get("State")),
                }
            })

    return matches, warnings


def sort_matches(matches):
    return sorted(
        matches,
        key=lambda match: (
            match.get("division") or "",
            int(match.get("week") or 0),
            int(match.get("match_number") or 0),
            match.get("match_id") or "",
        )
    )


def import_regular_schedule(source_dir=SOURCE_SCHEDULE_DIR, output_file=OUTPUT_FILE):
    active_rosters = load_json(ACTIVE_ROSTERS_FILE, {"teams": []})
    team_aliases = load_json(TEAM_ALIASES_FILE, {})
    active_team_lookup = build_active_team_lookup(active_rosters, team_aliases)

    csv_files = sorted(source_dir.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {source_dir}")

    all_matches = []
    all_warnings = []

    for csv_file in csv_files:
        matches, warnings = read_schedule_csv(csv_file, active_team_lookup)

        all_matches.extend(matches)
        all_warnings.extend(warnings)

    all_matches = sort_matches(all_matches)

    seen_ids = set()
    duplicate_ids = []

    for match in all_matches:
        match_id = match["match_id"]

        if match_id in seen_ids:
            duplicate_ids.append(match_id)

        seen_ids.add(match_id)

    for match_id in sorted(set(duplicate_ids)):
        all_warnings.append(f"Duplicate match_id generated: {match_id}")

    output = {
        "season_id": SEASON_ID,
        "season_type": SEASON_TYPE,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(source_dir.relative_to(BASE_DIR)),
        "match_count": len(all_matches),
        "matches": all_matches,
        "warnings": all_warnings,
    }

    write_json(output_file, output)

    return output


def main():
    parser = argparse.ArgumentParser(
        description="Import SPL regular-season schedule CSVs into schedule.json"
    )

    parser.add_argument(
        "--source-dir",
        default=str(SOURCE_SCHEDULE_DIR),
        help="Folder containing regular-season schedule CSV files",
    )

    parser.add_argument(
        "--output",
        default=str(OUTPUT_FILE),
        help="Output schedule.json path",
    )

    args = parser.parse_args()

    output = import_regular_schedule(
        source_dir=Path(args.source_dir),
        output_file=Path(args.output),
    )

    print(f"Imported {output['match_count']} regular-season matches")
    print(f"Wrote {Path(args.output)}")

    if output["warnings"]:
        print()
        print(f"Warnings: {len(output['warnings'])}")
        for warning in output["warnings"]:
            print(f"- {warning}")


if __name__ == "__main__":
    main()