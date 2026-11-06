import json
from pathlib import Path
from datetime import datetime, timezone


FUNDAMENTALS_FILE = Path("data/fundamentals.json")
OUTPUT_FILE = Path("data/company_profiles.json")


def load_fundamentals():
    with open(FUNDAMENTALS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_profiles():
    fundamentals = load_fundamentals()

    profiles = []

    for item in fundamentals:
        symbol = item.get("symbol")
        company_name = item.get("company_name")

        if not symbol:
            continue

        profiles.append(
            {
                "symbol": symbol,
                "company_name": company_name or symbol.replace(".JK", ""),
                "description": "",
                "sector": "",
                "industry": "",
                "source": "Sectors API",
                "source_url": "",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    profiles.sort(key=lambda x: x["symbol"])

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

    print(f"Profiles created: {len(profiles)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    build_profiles()