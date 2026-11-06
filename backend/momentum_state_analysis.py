import json
from pathlib import Path

import pandas as pd


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

CACHE_FILE = DATA_DIR / "daily_cache.json"


def load_cache():

    with open(
        CACHE_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def calculate_momentum(records):

    if not records:
        return None

    df = pd.DataFrame(records)

    if "date" not in df.columns:
        return None

    if "close" not in df.columns:
        return None

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    df["close"] = pd.to_numeric(
        df["close"],
        errors="coerce"
    )

    df = df.dropna(
        subset=[
            "date",
            "close"
        ]
    )

    df = df.sort_values(
        "date"
    ).reset_index(
        drop=True
    )

    if len(df) < 20:
        return None

    current_price = df.iloc[-1]["close"]

    price_20d_ago = df.iloc[-21]["close"]

    return_20d = (
        current_price /
        price_20d_ago
    ) - 1

    return_60d = None

    if len(df) >= 61:

        price_60d_ago = df.iloc[-61]["close"]

        return_60d = (
            current_price /
            price_60d_ago
        ) - 1

    df["ma20"] = (
        df["close"]
        .rolling(20)
        .mean()
    )

    df["ma60"] = (
        df["close"]
        .rolling(60)
        .mean()
    )

    ma20 = df.iloc[-1]["ma20"]

    ma60 = df.iloc[-1]["ma60"]

    price_vs_ma20 = None

    if pd.notna(ma20) and ma20 != 0:

        price_vs_ma20 = (
            current_price /
            ma20
        ) - 1

    price_vs_ma60 = None

    if pd.notna(ma60) and ma60 != 0:

        price_vs_ma60 = (
            current_price /
            ma60
        ) - 1

    return {
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


def calculate_state_flags(momentum):

    if momentum is None:
        return None

    flags = {}

    return_20d = momentum.get(
        "return_20d"
    )

    return_60d = momentum.get(
        "return_60d"
    )

    price_vs_ma20 = momentum.get(
        "price_vs_ma20"
    )

    price_vs_ma60 = momentum.get(
        "price_vs_ma60"
    )

    flags["return_20d_positive"] = (
        return_20d is not None
        and return_20d > 0
    )

    flags["return_60d_positive"] = (
        return_60d is not None
        and return_60d > 0
    )

    flags["above_ma20"] = (
        price_vs_ma20 is not None
        and price_vs_ma20 > 0
    )

    flags["above_ma60"] = (
        price_vs_ma60 is not None
        and price_vs_ma60 > 0
    )

    positive_count = sum(
        flags.values()
    )

    flags["positive_count"] = (
        positive_count
    )

    return flags


def classify_state(flags):

    if flags is None:
        return "NO_DATA"

    positive_count = flags[
        "positive_count"
    ]

    if positive_count == 4:
        return "STRONG_POSITIVE"

    if positive_count == 3:
        return "POSITIVE"

    if positive_count == 2:
        return "MIXED"

    if positive_count == 1:
        return "WEAK"

    return "NEGATIVE"


def analyze_universe(cache):

    results = []

    for symbol, records in cache.items():

        momentum = calculate_momentum(
            records
        )

        if momentum is None:
            continue

        flags = calculate_state_flags(
            momentum
        )

        state = classify_state(
            flags
        )

        results.append({
            "symbol": symbol,
            **momentum,
            **flags,
            "momentum_state": state
        })

    return results


def print_summary(results):

    df = pd.DataFrame(
        results
    )

    print(
        "\n=== MOMENTUM STATE SUMMARY ==="
    )

    print(
        "Stocks analyzed:",
        len(df)
    )

    if df.empty:
        return

    print(
        "\nMomentum states:"
    )

    state_counts = (
        df[
            "momentum_state"
        ]
        .value_counts()
    )

    for state, count in state_counts.items():

        percentage = (
            count /
            len(df) *
            100
        )

        print(
            f"{state:20}"
            f"{count:5}"
            f" ({percentage:5.1f}%)"
        )

    print(
        "\n=== RETURN DISTRIBUTION ==="
    )

    for metric in [
        "return_20d",
        "return_60d",
        "price_vs_ma20",
        "price_vs_ma60"
    ]:

        series = pd.to_numeric(
            df[metric],
            errors="coerce"
        ).dropna()

        if series.empty:
            continue

        print(
            f"\n{metric}"
        )

        print(
            "Count :",
            len(series)
        )

        print(
            "Min   :",
            f"{series.min():.4f}"
        )

        print(
            "P10   :",
            f"{series.quantile(0.10):.4f}"
        )

        print(
            "P25   :",
            f"{series.quantile(0.25):.4f}"
        )

        print(
            "Median:",
            f"{series.median():.4f}"
        )

        print(
            "P75   :",
            f"{series.quantile(0.75):.4f}"
        )

        print(
            "P90   :",
            f"{series.quantile(0.90):.4f}"
        )

        print(
            "Max   :",
            f"{series.max():.4f}"
        )


def main():

    print(
        "=== BAGGER RADAR MOMENTUM STATE ANALYSIS ==="
    )

    cache = load_cache()

    print(
        "Cached stocks:",
        len(cache)
    )

    results = analyze_universe(
        cache
    )

    print_summary(
        results
    )


if __name__ == "__main__":

    main()