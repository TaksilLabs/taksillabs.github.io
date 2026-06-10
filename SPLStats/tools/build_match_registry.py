import json
from pathlib import Path
from datetime import datetime

LOGS_DIR = Path("../logs")
OUT_FILE = Path("../data/match_registry.json")
ISSUES_FILE = Path("../data/match_registry_issues.json")


def parse_created_timestamp(file_path):
    # Example:
    # 20260607_012840_334537409134067723_2026-06-06-21-05-18.json
    try:
        date_part = file_path.stem.split("_")[-1]
        dt = datetime.strptime(date_part, "%Y-%m-%d-%H-%M-%S")
        return dt, dt.strftime("%Y-%m-%dT%H:%M:%S"), dt.strftime("%Y-%m-%d")
    except Exception:
        return None, None, None


def safe_period(data):
    try:
        return int(data.get("current_period", 0))
    except Exception:
        return 0


def load_json(file_path):
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_game_entry(game_id, folder_name, reports):
    reports.sort(key=lambda r: (r["created_dt"] or datetime.min, r["period"]))

    chosen = max(
        reports,
        key=lambda r: (r["period"], r["created_dt"] or datetime.min)
    )

    data = chosen["data"]
    players = data.get("players", [])

    slap_ids = sorted({
        str(p.get("game_user_id")).strip()
        for p in players
        if p.get("game_user_id")
    })

    entry = {
        "game_id": game_id,
        "folder_name": folder_name,
        "date": chosen["date"],
        "timestamp": chosen["timestamp"],
        "chosen_file": chosen["file_name"],
        "highest_period_found": chosen["period"],
        "report_complete": chosen["period"] >= 3,
        "reports_found": len(reports),
        "report_match_ids": [
            r["data"].get("match_id")
            for r in reports
            if r["data"].get("match_id")
        ],
        "files": [
            {
                "file_name": r["file_name"],
                "period": r["period"],
                "timestamp": r["timestamp"],
                "report_match_id": r["data"].get("match_id")
            }
            for r in reports
        ],
        "arena": data.get("arena"),
        "winner": data.get("winner"),
        "end_reason": data.get("end_reason"),
        "home_score": data.get("score", {}).get("home"),
        "away_score": data.get("score", {}).get("away"),
        "player_count": len(slap_ids),
        "slap_ids": slap_ids,
        "teams": {
            "home": [],
            "away": []
        }
    }

    for p in players:
        slap_id = str(p.get("game_user_id")).strip()
        team = p.get("team")

        if team in ["home", "away"] and slap_id:
            entry["teams"][team].append(slap_id)

    return entry


def main():
    registry = {}
    issues = {
        "bad_json_files": [],
        "incomplete_games": {},
        "weird_game_groups": {}
    }

    folders = [p for p in LOGS_DIR.iterdir() if p.is_dir()]
    total_json_files = 0
    total_valid_reports = 0
    game_count = 0

    for folder in folders:
        reports = []

        for file_path in folder.glob("*.json"):
            total_json_files += 1

            try:
                data = load_json(file_path)
            except Exception as e:
                issues["bad_json_files"].append({
                    "file": str(file_path),
                    "error": str(e)
                })
                continue

            created_dt, timestamp, date = parse_created_timestamp(file_path)

            reports.append({
                "file_path": file_path,
                "file_name": file_path.name,
                "folder_name": folder.name,
                "data": data,
                "period": safe_period(data),
                "created_dt": created_dt,
                "timestamp": timestamp,
                "date": date
            })

        reports.sort(key=lambda r: (r["created_dt"] or datetime.min, r["period"]))

        current_game_reports = []
        folder_game_number = 1

        for report in reports:
            total_valid_reports += 1
            current_game_reports.append(report)

            if report["period"] >= 3:
                game_id = f"{folder.name}__game_{folder_game_number:03d}"

                entry = build_game_entry(game_id, folder.name, current_game_reports)
                registry[game_id] = entry

                if not entry["report_complete"]:
                    issues["incomplete_games"][game_id] = entry

                if entry["reports_found"] != 3:
                    issues["weird_game_groups"][game_id] = {
                        "reports_found": entry["reports_found"],
                        "highest_period_found": entry["highest_period_found"],
                        "files": entry["files"]
                    }

                game_count += 1
                folder_game_number += 1
                current_game_reports = []

        # Anything left over after the loop is an incomplete game.
        if current_game_reports:
            game_id = f"{folder.name}__game_{folder_game_number:03d}"

            entry = build_game_entry(game_id, folder.name, current_game_reports)
            registry[game_id] = entry
            issues["incomplete_games"][game_id] = entry
            issues["weird_game_groups"][game_id] = {
                "reports_found": entry["reports_found"],
                "highest_period_found": entry["highest_period_found"],
                "files": entry["files"]
            }

            game_count += 1

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    with ISSUES_FILE.open("w", encoding="utf-8") as f:
        json.dump(issues, f, indent=2, ensure_ascii=False)

    print(f"Folders scanned: {len(folders)}")
    print(f"JSON files found: {total_json_files}")
    print(f"Valid reports used: {total_valid_reports}")
    print(f"Games in registry: {len(registry)}")
    print(f"Incomplete games: {len(issues['incomplete_games'])}")
    print(f"Weird game groups: {len(issues['weird_game_groups'])}")
    print(f"Bad JSON files: {len(issues['bad_json_files'])}")
    print(f"Wrote: {OUT_FILE.resolve()}")
    print(f"Wrote issues: {ISSUES_FILE.resolve()}")


if __name__ == "__main__":
    main()