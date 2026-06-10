import json
from pathlib import Path

ISSUES_FILE = Path("../data/match_registry_issues.json")


def main():
    with ISSUES_FILE.open("r", encoding="utf-8") as f:
        issues = json.load(f)

    print("=== ISSUE SUMMARY ===")
    print(f"Bad JSON files: {len(issues.get('bad_json_files', []))}")
    print(f"Incomplete games: {len(issues.get('incomplete_games', {}))}")
    print(f"Weird game groups: {len(issues.get('weird_game_groups', {}))}")

    print("\n=== FIRST 10 WEIRD GROUPS ===")
    for i, (game_id, info) in enumerate(issues.get("weird_game_groups", {}).items()):
        if i >= 10:
            break

        print(f"\n{game_id}")
        print(f"Reports found: {info.get('reports_found')}")
        print(f"Highest period: {info.get('highest_period_found')}")

        for file in info.get("files", []):
            print(f"  P{file.get('period')} | {file.get('timestamp')} | {file.get('file_name')}")

    print("\n=== FIRST 10 INCOMPLETE GAMES ===")
    for i, (game_id, info) in enumerate(issues.get("incomplete_games", {}).items()):
        if i >= 10:
            break

        print(f"\n{game_id}")
        print(f"Reports found: {info.get('reports_found')}")
        print(f"Highest period: {info.get('highest_period_found')}")

        for file in info.get("files", []):
            print(f"  P{file.get('period')} | {file.get('timestamp')} | {file.get('file_name')}")


if __name__ == "__main__":
    main()