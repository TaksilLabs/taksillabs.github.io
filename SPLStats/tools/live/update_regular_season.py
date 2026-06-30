import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


SEASON_ID = "summer_2026"
SEASON_TYPE = "regular_season"

BASE_DIR = Path(__file__).resolve().parents[2]

LIVE_SEASON_DIR = BASE_DIR / "data" / "live_season" / SEASON_ID
REGULAR_SEASON_DIR = LIVE_SEASON_DIR / "regular_season"

ACTIVE_ROSTERS_FILE = LIVE_SEASON_DIR / "active_rosters.json"

SCHEDULE_FILE = REGULAR_SEASON_DIR / "schedule.json"
MATCHES_FILE = REGULAR_SEASON_DIR / "matches.json"
BROADCASTS_FILE = REGULAR_SEASON_DIR / "broadcasts.json"
DIVISION_SUMMARY_FILE = REGULAR_SEASON_DIR / "division_summary.json"
STANDINGS_FILE = REGULAR_SEASON_DIR / "standings.json"
LEADERS_FILE = REGULAR_SEASON_DIR / "leaders.json"


DIVISION_LABELS = {
    "pro": "Pro",
    "challenger": "Challenger",
    "intermediate": "Intermediate",
    "prospect": "Prospect",
    "open": "Open",

    "central_a": "Central A",
    "central_b": "Central B",
    "central_c": "Central C",
    "central_d": "Central D",

    "masters": "Masters",
    "contenders": "Contenders",
}


DIVISION_REGIONS = {
    "pro": "east",
    "challenger": "east",
    "intermediate": "east",
    "prospect": "east",
    "open": "east",

    "central_a": "central",
    "central_b": "central",
    "central_c": "central",
    "central_d": "central",

    "masters": "west",
    "contenders": "west",
}


def clean(value):
    return str(value or "").strip()


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


def get_roster_teams(active_rosters):
    if isinstance(active_rosters, list):
        return active_rosters

    if isinstance(active_rosters, dict) and isinstance(active_rosters.get("teams"), list):
        return active_rosters["teams"]

    return []


def get_schedule_matches(schedule_data):
    if isinstance(schedule_data, list):
        return schedule_data

    if isinstance(schedule_data, dict) and isinstance(schedule_data.get("matches"), list):
        return schedule_data["matches"]

    return []


def get_completed_match_ids(matches_data):
    matches = []

    if isinstance(matches_data, list):
        matches = matches_data
    elif isinstance(matches_data, dict) and isinstance(matches_data.get("matches"), list):
        matches = matches_data["matches"]

    return {
        match.get("match_id")
        for match in matches
        if match.get("match_id") and clean(match.get("status")).lower() in {"final", "completed", "complete"}
    }


def run_import_regular_schedule():
    script = BASE_DIR / "tools" / "live" / "import_regular_schedule.py"

    if not script.exists():
        raise FileNotFoundError(f"Missing importer script: {script}")

    print("Importing regular-season schedule...")

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=BASE_DIR,
        text=True,
        capture_output=True,
    )

    if result.stdout:
        print(result.stdout.strip())

    if result.stderr:
        print(result.stderr.strip())

    if result.returncode != 0:
        raise RuntimeError("Regular-season schedule import failed")


def ensure_matches_file():
    if MATCHES_FILE.exists():
        return

    print("Creating matches.json...")

    write_json(MATCHES_FILE, {
        "season_id": SEASON_ID,
        "season_type": SEASON_TYPE,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "matches": []
    })


def ensure_broadcasts_file():
    if BROADCASTS_FILE.exists():
        return

    print("Creating broadcasts.json...")

    write_json(BROADCASTS_FILE, {})


def ensure_standings_file():
    if STANDINGS_FILE.exists():
        return

    print("Creating standings.json placeholder...")

    write_json(STANDINGS_FILE, {
        "season_id": SEASON_ID,
        "season_type": SEASON_TYPE,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "divisions": {}
    })


def ensure_leaders_file():
    if LEADERS_FILE.exists():
        return

    print("Creating leaders.json placeholder...")

    write_json(LEADERS_FILE, {
        "season_id": SEASON_ID,
        "season_type": SEASON_TYPE,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "divisions": {}
    })


def build_division_summary():
    print("Building division_summary.json...")

    active_rosters = load_json(ACTIVE_ROSTERS_FILE, {"teams": []})
    schedule_data = load_json(SCHEDULE_FILE, {"matches": []})
    matches_data = load_json(MATCHES_FILE, {"matches": []})

    roster_teams = get_roster_teams(active_rosters)
    schedule_matches = get_schedule_matches(schedule_data)
    completed_match_ids = get_completed_match_ids(matches_data)

    teams_by_division = defaultdict(list)
    conferences_by_division = defaultdict(set)
    matches_by_division = defaultdict(list)

    for team in roster_teams:
        division = clean(team.get("division")).lower()

        if not division:
            continue

        teams_by_division[division].append(team)

        conference = clean(team.get("conference"))

        if conference:
            conferences_by_division[division].add(conference)

    for match in schedule_matches:
        division = clean(match.get("division")).lower()

        if not division:
            continue

        matches_by_division[division].append(match)

    divisions = []

    for division in sorted(teams_by_division.keys()):
        division_matches = matches_by_division.get(division, [])

        completed = [
            match for match in division_matches
            if match.get("match_id") in completed_match_ids
            or clean(match.get("status")).lower() in {"final", "completed", "complete"}
        ]

        upcoming = [
            match for match in division_matches
            if match not in completed
        ]

        weeks = sorted({
            int(match.get("week") or 0)
            for match in division_matches
            if int(match.get("week") or 0) > 0
        })

        conferences = sorted(conferences_by_division.get(division, set()))

        divisions.append({
            "division": division,
            "display_name": DIVISION_LABELS.get(division, division),
            "region": DIVISION_REGIONS.get(division, ""),
            "team_count": len(teams_by_division[division]),
            "conference_count": len(conferences),
            "conferences": conferences,
            "scheduled_matches": len(division_matches),
            "completed_matches": len(completed),
            "upcoming_matches": len(upcoming),
            "weeks": weeks,
            "first_week": weeks[0] if weeks else None,
            "last_week": weeks[-1] if weeks else None,
        })

    output = {
        "season_id": SEASON_ID,
        "season_type": SEASON_TYPE,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "division_count": len(divisions),
        "divisions": divisions,
    }

    write_json(DIVISION_SUMMARY_FILE, output)

    return output


def main():
    print(f"Updating {SEASON_ID} regular season...")
    print()

    run_import_regular_schedule()
    ensure_matches_file()
    ensure_broadcasts_file()
    ensure_standings_file()
    ensure_leaders_file()

    summary = build_division_summary()

    print()
    print("Regular season update complete.")
    print(f"Divisions: {summary['division_count']}")
    print(f"Wrote {DIVISION_SUMMARY_FILE.relative_to(BASE_DIR)}")

    print()
    for division in summary["divisions"]:
        print(
            f"- {division['display_name']}: "
            f"{division['team_count']} teams, "
            f"{division['scheduled_matches']} matches, "
            f"{division['conference_count']} conferences"
        )


if __name__ == "__main__":
    main()