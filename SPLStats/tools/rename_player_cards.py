from pathlib import Path

from player_identity import load_player_identities, get_player_id_from_name


PLAYER_CARDS_DIR = Path("../assets/images/player_cards")
DRY_RUN = False


SKIP_FILES = {
    "fallback.webp",
    "default.webp",
}


def main():
    alias_lookup, _ = load_player_identities()

    if not PLAYER_CARDS_DIR.exists():
        print(f"Player cards folder not found: {PLAYER_CARDS_DIR.resolve()}")
        return

    webp_files = sorted(PLAYER_CARDS_DIR.glob("*.webp"))

    renamed = 0
    skipped = 0
    conflicts = 0

    for card_file in webp_files:
        if card_file.name.lower() in SKIP_FILES:
            print(f"SKIP reserved file: {card_file.name}")
            skipped += 1
            continue

        raw_name = card_file.stem.strip()

        if not raw_name:
            print(f"SKIP empty filename: {card_file.name}")
            skipped += 1
            continue

        player_id = get_player_id_from_name(raw_name, alias_lookup)
        target_file = card_file.with_name(f"{player_id}.webp")

        if target_file == card_file:
            print(f"OK already named: {card_file.name}")
            skipped += 1
            continue

        if target_file.exists():
            print(f"CONFLICT: {card_file.name} -> {target_file.name} already exists")
            conflicts += 1
            continue

        print(f"RENAME: {card_file.name} -> {target_file.name}")

        if not DRY_RUN:
            card_file.rename(target_file)

        renamed += 1

    print()
    print(f"Dry run: {DRY_RUN}")
    print(f"Renamed: {renamed}")
    print(f"Skipped: {skipped}")
    print(f"Conflicts: {conflicts}")
    print(f"Folder: {PLAYER_CARDS_DIR.resolve()}")


if __name__ == "__main__":
    main()