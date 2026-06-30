import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

STEPS = [
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
]


def run_step(step):
    script_path = BASE_DIR / step["script"]

    if not script_path.exists():
        print()
        print(f"ERROR: Missing script: {script_path}")
        return False

    print()
    print("=" * 72)
    print(step["name"])
    print("=" * 72)

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=BASE_DIR,
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
    print("- data/live_season/summer_2026/regular_season/matches.json")
    print("- data/live_season/summer_2026/regular_season/match_details/*.json")
    print("- data/live_season/summer_2026/regular_season/standings.json")
    print("- data/live_season/summer_2026/regular_season/leaders.json")


if __name__ == "__main__":
    main()