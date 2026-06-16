import csv
from pathlib import Path

for file in [
    Path("../raw_csv/SPL-Winter2021.csv"),
    Path("../raw_csv/SPL-Spring2021.csv"),
]:
    print()
    print(file.name)
    print("-" * 40)

    seen = set()

    with file.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            stat = row.get("Stat Desc", "").strip()

            if "assist" in stat.lower():
                seen.add(stat)

    for stat in sorted(seen):
        print(repr(stat))