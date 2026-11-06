import json
from pathlib import Path

import pandas as pd


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

INPUT_FILE = DATA_DIR / "momentum_raw_test.json"


def load_data():

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def calculate_momentum(records):

    if not records:
        return None

    df = pd.DataFrame(records)

    df["date"] = pd.to_datetime(
        df["date"]
    )

    df["close"] = pd.to_numeric(
        df["close"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["date", "close"]
    )

    df = df.sort_values(
        "date"
    ).reset_index(
        drop=True
    )

    if len(df) < 20:
        return None

    df["ma20"] = df["close"].rolling(
        window=20
    ).mean()

    df["ma60"] = df["close"].rolling(
        window=60
    ).mean()

    current_price = df.iloc[-1]["close"]

    price_20d_ago = df.iloc[-21]["close"]

    return_20d = (
        current_price / price_20d_ago - 1
    )

    return_60d = None

    if len(df) >= 61:

        price_60d_ago = df.iloc[-61]["close"]

        return_60d = (
            current_price / price_60d_ago - 1
        )

    ma20 = df.iloc[-1]["ma20"]

    ma60 = df.iloc[-1]["ma60"]

    price_vs_ma20 = None

    if pd.notna(ma20) and ma20 != 0:

        price_vs_ma20 = (
            current_price / ma20 - 1
        )

    price_vs_ma60 = None

    if pd.notna(ma60) and ma60 != 0:

        price_vs_ma60 = (
            current_price / ma60 - 1
        )

    return {
        "latest_date": df.iloc[-1]["date"].strftime(
            "%Y-%m-%d"
        ),
        "current_price": float(
            current_price
        ),
        "return_20d": float(
            return_20d
        ),
        "return_60d": (
            float(return_60d)
            if return_60d is not None
            else None
        ),
        "ma20": (
            float(ma20)
            if pd.notna(ma20)
            else None
        ),
        "ma60": (
            float(ma60)
            if pd.notna(ma60)
            else None
        ),
        "price_vs_ma20": (
            float(price_vs_ma20)
            if price_vs_ma20 is not None
            else None
        ),
        "price_vs_ma60": (
            float(price_vs_ma60)
            if price_vs_ma60 is not None
            else None
        )
    }


def main():

    print(
        "=== BAGGER RADAR MOMENTUM CALCULATION TEST ==="
    )

    data = load_data()

    for symbol, records in data.items():

        result = calculate_momentum(
            records
        )

        print(
            f"\n--- {symbol} ---"
        )

        if result is None:

            print(
                "Data tidak cukup."
            )

            continue

        print(
            "Latest date   :",
            result["latest_date"]
        )

        print(
            "Current price :",
            result["current_price"]
        )

        print(
            "20D Return    :",
            f'{result["return_20d"] * 100:.2f}%'
        )

        if result["return_60d"] is not None:

            print(
                "60D Return    :",
                f'{result["return_60d"] * 100:.2f}%'
            )

        else:

            print(
                "60D Return    : NO DATA"
            )

        print(
            "MA20          :",
            f'{result["ma20"]:.2f}'
            if result["ma20"] is not None
            else "NO DATA"
        )

        print(
            "MA60          :",
            f'{result["ma60"]:.2f}'
            if result["ma60"] is not None
            else "NO DATA"
        )

        print(
            "Price vs MA20  :",
            f'{result["price_vs_ma20"] * 100:.2f}%'
            if result["price_vs_ma20"] is not None
            else "NO DATA"
        )

        print(
            "Price vs MA60  :",
            f'{result["price_vs_ma60"] * 100:.2f}%'
            if result["price_vs_ma60"] is not None
            else "NO DATA"
        )


if __name__ == "__main__":

    main()