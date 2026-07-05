import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

SEASON_ID = "summer_2026"
SEASON_TYPE = "regular_season"


STEPS = [
    # ---------------------------------------------------------------------
    # Live-Season Updates
    # ---------------------------------------------------------------------
    {
        "name": "Import incoming regular logs",
        "script": "tools/live/import_incoming_regular_logs.py",
    },
    {
        "name": "Build regular matches",
        "script": "tools/live/build_regular_matches.py",
    },
    {
        "name": "Build regular standings",
        "script": "tools/live/build_regular_standings.py",
    },
    {
        "name": "Build regular leaders",
        "script": "tools/live/build_regular_leaders.py",
    },

    # ---------------------------------------------------------------------
    # Site-wide stat rebuilds
    # ---------------------------------------------------------------------
    {
        "name": "Build live season stats",
        "script": "tools/build_live_season.py",
        "cwd": "tools",
        "args": [
            "--season",
            SEASON_ID,
            "--season-type",
            SEASON_TYPE,
        ],
    },
    {
        "name": "Build LR season stats",
        "script": "tools/build_lr_season.py",
        "cwd": "tools",
    },
    {
        "name": "Build all-time players",
        "script": "tools/build_all_time.py",
        "cwd": "tools",
    },
    {
        "name": "Build franchises",
        "script": "tools/build_franchises.py",
        "cwd": "tools",
    },
    {
        "name": "Build team records",
        "script": "tools/build_team_records.py",
        "cwd": "tools",
    },
    {
        "name": "Build teams",
        "script": "tools/build_teams.py",
        "cwd": "tools",
    },
]


def run_step(step):
    script_path = BASE_DIR / step["script"]

    if not script_path.exists():
        print()
        print(f"ERROR: Missing script: {script_path}")
        return False

    args = step.get("args", [])

    cwd = BASE_DIR / step.get("cwd", ".")

    print()
    print("=" * 72)
    print(step["name"])
    print("=" * 72)
    print(f"Script: {step['script']}")
    print(f"Working dir: {cwd}")

    if args:
        print(f"Args: {' '.join(args)}")

    command = [
        sys.executable,
        str(script_path),
        *args,
    ]

    result = subprocess.run(
        command,
        cwd=cwd,
    )

    if result.returncode != 0:
        print()
        print(f"ERROR: Step failed: {step['name']}")
        print(f"Exit code: {result.returncode}")
        return False

    print()
    print(f"Done: {step['name']}")
    return True


def main():
    print("SPL regular season update starting...")
    print(f"Project root: {BASE_DIR}")
    print(f"Season: {SEASON_ID}")
    print(f"Season type: {SEASON_TYPE}")

    for step in STEPS:
        success = run_step(step)

        if not success:
            print()
            print("Regular season update stopped early.")
            sys.exit(1)

    print()
    print("=" * 72)
    print("Regular season update complete.")
    print("=" * 72)
    print()
    print("Updated files should include:")
    print(f"- data/live_season/{SEASON_ID}/{SEASON_TYPE}/matches.json")
    print(f"- data/live_season/{SEASON_ID}/{SEASON_TYPE}/match_details/*.json")
    print(f"- data/live_season/{SEASON_ID}/{SEASON_TYPE}/standings.json")
    print(f"- data/live_season/{SEASON_ID}/{SEASON_TYPE}/leaders.json")
    print(f"- data/seasons/{SEASON_ID}_live.json")
    print("- data/seasons/*.json")
    print("- data/all_time_players.json")
    print("- data/franchises.json")
    print("- data/team_records.json")
    print("- data/teams.json")


if __name__ == "__main__":
    main()