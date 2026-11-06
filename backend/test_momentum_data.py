import json
from pathlib import Path

from sectors_client import SectorsClient


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

OUTPUT_FILE = DATA_DIR / "momentum_raw_test.json"


TEST_SYMBOLS = [
    "BBRI.JK",
    "BMRI.JK",
    "BBCA.JK",
    "ARTI.JK",
    "LMSH.JK"
]


START_DATE = "2026-06-01"


def load_daily_data():

    client = SectorsClient()

    all_data = {}

    for symbol in TEST_SYMBOLS:

        print(
            f"Mengambil daily data: {symbol}"
        )

        try:

            results = client.get_daily(
                symbol,
                start=START_DATE
            )

            # get_daily() sudah mengembalikan list
            all_data[symbol] = results

            print(
                f"  Records: {len(results)}"
            )

        except Exception as error:

            print(
                f"  ERROR: {error}"
            )

            all_data[symbol] = []

    return all_data


def print_summary(data):

    print(
        "\n=== DAILY DATA SUMMARY ==="
    )

    for symbol, records in data.items():

        print(
            f"\n--- {symbol} ---"
        )

        print(
            "Records:",
            len(records)
        )

        if not records:

            print(
                "Tidak ada data."
            )

            continue

        first = records[0]
        last = records[-1]

        print(
            "First date:",
            first.get("date")
        )

        print(
            "Last date :",
            last.get("date")
        )

        print(
            "First close:",
            first.get("close")
        )

        print(
            "Last close :",
            last.get("close")
        )


def save_data(data):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        "\nRaw daily test data disimpan ke:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":

    print(
        "=== BAGGER RADAR MOMENTUM DATA TEST ==="
    )

    data = load_daily_data()

    print_summary(
        data
    )

    save_data(
        data
    )