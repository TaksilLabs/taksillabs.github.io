import json
from pathlib import Path
from datetime import datetime

LOGS_DIR = Path("../logs")
OUT_FILE = Path("../data/game_stats.json")


def parse_created_timestamp(file_path):
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


def choose_best_report(reports):
    return max(
        reports,
        key=lambda r: (r["period"], r["created_dt"] or datetime.min)
    )


def main():
    game_stats = []
    bad_json_files = []
    total_json_files = 0
    games_used = 0

    folders = [p for p in LOGS_DIR.iterdir() if p.is_dir()]

    for folder in folders:
        reports = []

        for file_path in folder.glob("*.json"):
            total_json_files += 1

            try:
                with file_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                bad_json_files.append({"file": str(file_path), "error": str(e)})
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
            current_game_reports.append(report)

            if report["period"] >= 3:
                chosen = choose_best_report(current_game_reports)
                game_id = f"{folder.name}__game_{folder_game_number:03d}"

                for player in chosen["data"].get("players", []):
                    row = {
                        "game_id": game_id,
                        "date": chosen["date"],
                        "timestamp": chosen["timestamp"],
                        "folder_name": folder.name,
                        "chosen_file": chosen["file_name"],
                        "report_complete": chosen["period"] >= 3,
                        "highest_period_found": chosen["period"],
                        "winner": chosen["data"].get("winner"),
                        "slap_id": str(player.get("game_user_id")).strip(),
                        "username": player.get("username"),
                        "team": player.get("team")
                    }

                    for stat, value in player.get("stats", {}).items():
                        row[stat] = value

                    game_stats.append(row)

                games_used += 1
                folder_game_number += 1
                current_game_reports = []

        if current_game_reports:
            chosen = choose_best_report(current_game_reports)
            game_id = f"{folder.name}__game_{folder_game_number:03d}"

            for player in chosen["data"].get("players", []):
                row = {
                    "game_id": game_id,
                    "date": chosen["date"],
                    "timestamp": chosen["timestamp"],
                    "folder_name": folder.name,
                    "chosen_file": chosen["file_name"],
                    "report_complete": chosen["period"] >= 3,
                    "highest_period_found": chosen["period"],
                    "winner": chosen["data"].get("winner"),
                    "slap_id": str(player.get("game_user_id")).strip(),
                    "username": player.get("username"),
                    "team": player.get("team")
                }

                for stat, value in player.get("stats", {}).items():
                    row[stat] = value

                game_stats.append(row)

            games_used += 1

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(game_stats, f, indent=2, ensure_ascii=False)

    print(f"Folders scanned: {len(folders)}")
    print(f"JSON files found: {total_json_files}")
    print(f"Games used: {games_used}")
    print(f"Player-game rows: {len(game_stats)}")
    print(f"Bad JSON files: {len(bad_json_files)}")
    print(f"Wrote: {OUT_FILE.resolve()}")


if __name__ == "__main__":
    main()