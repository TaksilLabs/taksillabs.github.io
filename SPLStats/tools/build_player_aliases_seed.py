import json
import re
from pathlib import Path


PLAYERS_FILE = Path("../data/all_time_players.json")
OUTPUT_FILE = Path("../data/player_aliases.json")


def make_player_id(name):
    text = str(name or "").strip().lower()

    # Remove symbols, keep letters/numbers/spaces/underscores/hyphens
    text = re.sub(r"[^a-z0-9_\-\s]", "", text)

    # Convert whitespace/hyphens to underscores
    text = re.sub(r"[\s\-]+", "_", text)

    # Collapse repeated underscores
    text = re.sub(r"_+", "_", text)

    return text.strip("_") or "unknown_player"


def main():
    with PLAYERS_FILE.open("r", encoding="utf-8") as f:
        players = json.load(f)

    aliases = []
    used_ids = {}

    for player in players:
        name = player.get("player_name", "").strip()

        if not name:
            continue

        base_id = make_player_id(name)
        player_id = base_id

        # Prevent duplicate IDs if two names normalize the same way
        if player_id in used_ids:
            used_ids[player_id] += 1
            player_id = f"{base_id}_{used_ids[base_id]}"
        else:
            used_ids[player_id] = 1

        aliases.append({
            "player_id": player_id,
            "player_display_name": name,
            "aliases": [
                name
            ],
            "slap_ids": []
        })

    aliases.sort(
        key=lambda p: p["player_display_name"].lower()
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            aliases,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(f"Players read: {len(players)}")
    print(f"Aliases written: {len(aliases)}")
    print(f"Wrote: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()