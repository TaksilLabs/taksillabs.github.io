import json
from pathlib import Path

REGISTRY_FILE = Path("../data/player_registry.json")
OUT_FILE = Path("../data/slap_id_lookup.json")


def main():
    with REGISTRY_FILE.open("r", encoding="utf-8") as f:
        registry = json.load(f)

    output = []

    from collections import Counter

    for slap_id, info in registry.items():

        display_name = (
            info.get("preferred_name")
            or info.get("display_name")
            or (
                max(
                    info.get("alias_counts", {}),
                    key=info.get("alias_counts", {}).get
                )
                if info.get("alias_counts")
                else ""
            )
        )

        names = [
            {"name": name, "count": count}
            for name, count in info.get("alias_counts", {}).items()
        ]

        names.sort(key=lambda x: (-x["count"], x["name"].lower()))

        output.append({
            "slap_id": str(slap_id),
            "display_name": display_name,
            "player_names": names
        })

    output.sort(
        key=lambda x:
            x["player_names"][0].get("name", "").lower()
            if x["player_names"]
            else ""
    )

    with OUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Slap IDs written: {len(output)}")
    print(f"Wrote: {OUT_FILE.resolve()}")


if __name__ == "__main__":
    main()