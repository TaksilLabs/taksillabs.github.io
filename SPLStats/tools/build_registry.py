import json
from pathlib import Path
from datetime import datetime

LOGS_DIR = Path("../logs")
OUT_FILE = Path("../data/player_registry.json")


def parse_created_timestamp(file_path):
    try:
        date_part = file_path.stem.split("_")[-1]
        dt = datetime.strptime(date_part, "%Y-%m-%d-%H-%M-%S")
        return dt, dt.strftime("%Y-%m-%d")
    except Exception:
        return None, None


def safe_period(data):
    try:
        return int(data.get("current_period", 0))
    except Exception:
        return 0


def update_player(registry, slap_id, username, match_date):
    slap_id = str(slap_id).strip()
    username = str(username).strip()

    if not slap_id or not username:
        return

    if slap_id not in registry:
        registry[slap_id] = {
            "preferred_name": username,
            "display_name": username,
            "aliases": [username],
            "alias_counts": {},
            "first_seen": match_date,
            "last_seen": match_date,
            "games_found": 0,
            "teams": [],
            "seasons": [],
            "steam_id": None,
            "discord_id": None,
            "notes": ""
        }

    player = registry[slap_id]

    if username not in player["aliases"]:
        player["aliases"].append(username)

    if "alias_counts" not in player:
        player["alias_counts"] = {}

    player["alias_counts"][username] = player["alias_counts"].get(username, 0) + 1

    # Use the most common name as display_name unless preferred_name is manually set.
    most_common_name = max(
        player["alias_counts"],
        key=player["alias_counts"].get
    )

    player["display_name"] = player.get("preferred_name") or most_common_name
    player["games_found"] = player.get("games_found", 0) + 1

    if match_date:
        if not player.get("first_seen") or match_date < player["first_seen"]:
            player["first_seen"] = match_date

        if not player.get("last_seen") or match_date > player["last_seen"]:
            player["last_seen"] = match_date


def choose_best_report(reports):
    return max(
        reports,
        key=lambda r: (r["period"], r["created_dt"] or datetime.min)
    )


def main():
    registry = {}
    bad_json_files = []
    total_json_files = 0
    games_used = 0

    folders = [p for p in LOGS_DIR.iterdir() if p.is_dir()]
    loose_json_files = sorted(LOGS_DIR.glob("*.json"))

    def load_report(file_path):
        nonlocal total_json_files

        total_json_files += 1

        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            bad_json_files.append({
                "file": str(file_path),
                "error": str(e)
            })
            return None

        created_dt, date = parse_created_timestamp(file_path)

        return {
            "file_path": file_path,
            "data": data,
            "period": safe_period(data),
            "created_dt": created_dt,
            "date": date
        }

    def use_chosen_report(chosen):
        nonlocal games_used

        for player in chosen["data"].get("players", []):
            update_player(
                registry,
                player.get("game_user_id"),
                player.get("username"),
                chosen["date"]
            )

        games_used += 1

    def process_reports_group(reports):
        if not reports:
            return

        reports.sort(key=lambda r: (r["created_dt"] or datetime.min, r["period"]))

        current_game_reports = []

        for report in reports:
            current_game_reports.append(report)

            if report["period"] >= 3:
                chosen = choose_best_report(current_game_reports)
                use_chosen_report(chosen)

                current_game_reports = []

        if current_game_reports:
            chosen = choose_best_report(current_game_reports)
            use_chosen_report(chosen)

    # Existing behavior:
    # each folder is treated as a grouped batch of reports.
    for folder in folders:
        reports = []

        for file_path in folder.glob("*.json"):
            report = load_report(file_path)

            if report:
                reports.append(report)

        process_reports_group(reports)

    # New behavior:
    # loose JSON files directly inside logs/ are also scanned.
    # Each loose file is treated as its own game/report.
    for file_path in loose_json_files:
        report = load_report(file_path)

        if report:
            process_reports_group([report])

    PREFERRED_NAMES_FILE = Path("../data/preferred_names.json")

    preferred_names = {}

    if PREFERRED_NAMES_FILE.exists():
        with PREFERRED_NAMES_FILE.open("r", encoding="utf-8") as f:
            preferred_names = json.load(f)

    for slap_id, preferred_name in preferred_names.items():
        if slap_id in registry:
            registry[slap_id]["preferred_name"] = preferred_name
            registry[slap_id]["display_name"] = preferred_name

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    print(f"Folders scanned: {len(folders)}")
    print(f"Loose JSON files scanned: {len(loose_json_files)}")
    print(f"JSON files found: {total_json_files}")
    print(f"Games used for registry: {games_used}")
    print(f"Players in registry: {len(registry)}")
    print(f"Bad JSON files: {len(bad_json_files)}")
    print(f"Wrote: {OUT_FILE.resolve()}")


if __name__ == "__main__":
    main()