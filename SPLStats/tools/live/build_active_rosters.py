from pathlib import Path

from live_helpers import (
    load_signup_active_rosters,
    write_json,
)


BASE_DIR = Path(__file__).resolve().parents[2]

SEASON_ID = "summer_2026"
SEASON_NAME = "Summer 2026"

SIGNUPS_FILE = BASE_DIR / "raw_signups" / "SPL-Summer2026-Signups.csv"

OUT_FILE = (
    BASE_DIR
    / "data"
    / "live_season"
    / SEASON_ID
    / "active_rosters.json"
)


def main():
    rosters_by_team = load_signup_active_rosters(SIGNUPS_FILE)

    output = {
        "season_id": SEASON_ID,
        "season_name": SEASON_NAME,
        "source_file": str(
            SIGNUPS_FILE.relative_to(BASE_DIR)
        ).replace("\\", "/"),
        "teams": sorted(
            rosters_by_team.values(),
            key=lambda team: team["team_display_name"].lower()
        )
    }

    write_json(OUT_FILE, output)

    print(f"Teams with rosters: {len(output['teams'])}")
    print(
        "Players listed: "
        f"{sum(len(team['players']) for team in output['teams'])}"
    )
    print(
        "Slap IDs listed: "
        f"{sum(len(team['slap_ids']) for team in output['teams'])}"
    )
    print(f"Wrote: {OUT_FILE}")


if __name__ == "__main__":
    main()