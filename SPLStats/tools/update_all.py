import subprocess
import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).parent.resolve()

SCRIPTS = [
    # Raw CSV → season player JSONs
    "build_lr_season.py",

    # Season JSONs → all-time player totals
    "build_all_time.py",

    # Team records / team pages
    "build_team_records.py",
    "build_teams.py",

    # Franchise stats should run after players + team records
    "build_franchises.py",

    # Slap ID lookup can be near the end
    "build_slap_id_lookup.py",
]


def run_script(script_name):
    script_path = TOOLS_DIR / script_name

    if not script_path.exists():
        print(f"SKIP: {script_name} not found")
        return True

    print()
    print("=" * 70)
    print(f"RUNNING: {script_name}")
    print("=" * 70)

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=TOOLS_DIR
    )

    if result.returncode != 0:
        print()
        print(f"FAILED: {script_name}")
        print(f"Exit code: {result.returncode}")
        return False

    print(f"DONE: {script_name}")
    return True


def main():
    print("Updating SPLStats data...")
    print(f"Tools folder: {TOOLS_DIR}")

    for script in SCRIPTS:
        success = run_script(script)

        if not success:
            print()
            print("Update stopped because a script failed.")
            sys.exit(1)

    print()
    print("=" * 70)
    print("ALL DONE")
    print("=" * 70)
    print("SPLStats data has been rebuilt successfully.")


if __name__ == "__main__":
    main()