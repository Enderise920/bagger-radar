import json
from pathlib import Path

from yahoo_provider import daily_records


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

FUNDAMENTALS_FILE = DATA_DIR / "fundamentals.json"

CACHE_FILE = DATA_DIR / "daily_cache.json"


START_DATE = "2026-06-01"


def load_companies():

    with open(
        FUNDAMENTALS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def load_existing_cache():

    if not CACHE_FILE.exists():

        return {}

    with open(
        CACHE_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def save_cache(data):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    temp_file = DATA_DIR / "daily_cache.tmp.json"

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )

    temp_file.replace(
        CACHE_FILE
    )


def fetch_daily_data(
    client,
    symbol
):
    return daily_records(symbol, period="1y")


def main():

    print(
        "=== BAGGER RADAR DAILY CACHE ==="
    )

    companies = load_companies()

    cache = load_existing_cache()

    print(
        f"Total companies: {len(companies)}"
    )

    print(
        f"Existing cache : {len(cache)}"
    )

    client = None

    processed = 0
    successful = 0
    failed = 0

    for company in companies:

        symbol = company.get(
            "symbol"
        )

        if not symbol:
            continue

        processed += 1

        # Skip jika sudah ada
        if symbol in cache:

            print(
                f"[{processed}/{len(companies)}] "
                f"{symbol} - cached"
            )

            continue

        print(
            f"[{processed}/{len(companies)}] "
            f"{symbol} - fetching..."
        )

        try:

            records = fetch_daily_data(
                client,
                symbol
            )

            if not isinstance(
                records,
                list
            ):

                print(
                    "  WARNING: response bukan list"
                )

                failed += 1

                continue

            cache[symbol] = records

            successful += 1

            print(
                f"  Records: {len(records)}"
            )

            # Simpan setiap saham
            # agar progress tidak hilang
            save_cache(
                cache
            )

        except Exception as error:

            failed += 1

            print(
                f"  ERROR: {error}"
            )

    print(
        "\n=== CACHE SUMMARY ==="
    )

    print(
        "Processed :",
        processed
    )

    print(
        "Successful:",
        successful
    )

    print(
        "Failed    :",
        failed
    )

    print(
        "Cached    :",
        len(cache)
    )

    print(
        "\nCache disimpan ke:"
    )

    print(
        CACHE_FILE
    )


if __name__ == "__main__":

    main()
