import json
import re
from pathlib import Path


PLAYERS_FILE = Path("../data/all_time_players.json")
ALIASES_FILE = Path("../data/player_aliases.json")


def normalize_alias(name):
    return str(name or "").strip().lower()


def make_player_id(name):
    text = str(name or "").strip().lower()

    # Remove symbols, keep letters/numbers/spaces/underscores/hyphens
    text = re.sub(r"[^a-z0-9_\-\s]", "", text)

    # Convert whitespace/hyphens to underscores
    text = re.sub(r"[\s\-]+", "_", text)

    # Collapse repeated underscores
    text = re.sub(r"_+", "_", text)

    return text.strip("_") or "unknown_player"


def unique_player_id(base_id, existing_ids):
    if base_id not in existing_ids:
        return base_id

    number = 2

    while f"{base_id}_{number}" in existing_ids:
        number += 1

    return f"{base_id}_{number}"


def load_json(path, fallback):
    if not path.exists():
        return fallback

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    players = load_json(PLAYERS_FILE, [])
    aliases = load_json(ALIASES_FILE, [])

    existing_ids = {
        entry.get("player_id")
        for entry in aliases
        if entry.get("player_id")
    }

    known_aliases = set()

    for entry in aliases:
        for alias in entry.get("aliases", []):
            known_aliases.add(normalize_alias(alias))

        display_name = entry.get("player_display_name")
        if display_name:
            known_aliases.add(normalize_alias(display_name))

    added = []

    for player in players:
        name = str(player.get("player_name", "")).strip()

        if not name:
            continue

        if normalize_alias(name) in known_aliases:
            continue

        base_id = make_player_id(name)
        player_id = unique_player_id(base_id, existing_ids)

        existing_ids.add(player_id)
        known_aliases.add(normalize_alias(name))

        new_entry = {
            "player_id": player_id,
            "player_display_name": name,
            "aliases": [
                name
            ],
            "slap_ids": []
        }

        aliases.append(new_entry)
        added.append(new_entry)

    aliases.sort(
        key=lambda entry: entry.get("player_display_name", "").lower()
    )

    ALIASES_FILE.parent.mkdir(parents=True, exist_ok=True)

    with ALIASES_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            aliases,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(f"Players checked: {len(players)}")
    print(f"Existing alias entries: {len(aliases) - len(added)}")
    print(f"New alias entries added: {len(added)}")

    if added:
        print()
        print("Added:")
        for entry in added:
            print(
                f"  {entry['player_display_name']} "
                f"-> {entry['player_id']}"
            )

    print()
    print(f"Wrote: {ALIASES_FILE.resolve()}")


if __name__ == "__main__":
    main()