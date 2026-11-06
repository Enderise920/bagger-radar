import json
from pathlib import Path

import numpy as np
import pandas as pd


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DAILY_CACHE = DATA_DIR / "daily_cache.json"
LIQUIDITY_FILE = DATA_DIR / "liquidity_flags.json"


def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def percentile_score(
    value,
    values
):

    if value is None:
        return None

    if not np.isfinite(value):
        return None

    clean = [
        x for x in values
        if x is not None
        and np.isfinite(x)
    ]

    if not clean:
        return None

    return (
        sum(
            x <= value
            for x in clean
        )
        / len(clean)
    ) * 100


def calculate_momentum(symbol, records):

    if not records:
        return None

    df = pd.DataFrame(records)

    required = [
        "date",
        "close"
    ]

    if not all(
        column in df.columns
        for column in required
    ):
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

    if len(df) < 60:
        return None

    current_price = df["close"].iloc[-1]

    price_20d = df["close"].iloc[-21]
    price_60d = df["close"].iloc[-61]

    return_20d = (
        current_price / price_20d
    ) - 1

    return_60d = (
        current_price / price_60d
    ) - 1

    ma20 = (
        df["close"]
        .tail(20)
        .mean()
    )

    ma60 = (
        df["close"]
        .tail(60)
        .mean()
    )

    price_vs_ma20 = (
        current_price / ma20
    ) - 1

    price_vs_ma60 = (
        current_price / ma60
    ) - 1

    return {
        "symbol": symbol,
        "return_20d": return_20d,
        "return_60d": return_60d,
        "price_vs_ma20": price_vs_ma20,
        "price_vs_ma60": price_vs_ma60
    }


def main():

    print(
        "=== BAGGER RADAR PRODUCTION MOMENTUM DIAGNOSTIC ==="
    )

    cache = load_json(
        DAILY_CACHE
    )

    liquidity = load_json(
        LIQUIDITY_FILE
    )

    results = []

    for symbol, records in cache.items():

        momentum = calculate_momentum(
            symbol,
            records
        )

        if momentum is None:
            continue

        liquidity_data = liquidity.get(
            symbol
        )

        if liquidity_data is None:
            continue

        momentum.update({
            "liquidity_state":
                liquidity_data[
                    "liquidity_state"
                ],
            "momentum_evidence":
                liquidity_data[
                    "momentum_evidence"
                ]
        })

        results.append(
            momentum
        )

    df = pd.DataFrame(
        results
    )

    print(
        "\nStocks with complete momentum data:",
        len(df)
    )

    # -------------------------------------------------
    # Relative percentile scores
    # -------------------------------------------------

    metrics = [
        "return_20d",
        "return_60d",
        "price_vs_ma20",
        "price_vs_ma60"
    ]

    for metric in metrics:

        values = df[metric].tolist()

        df[
            f"{metric}_percentile"
        ] = df[metric].apply(
            lambda x:
                percentile_score(
                    x,
                    values
                )
        )

    percentile_columns = [
        f"{metric}_percentile"
        for metric in metrics
    ]

    df[
        "raw_momentum_percentile"
    ] = df[
        percentile_columns
    ].mean(
        axis=1
    )

    print(
        "\n=== MOMENTUM BY LIQUIDITY STATE ==="
    )

    summary = (
        df.groupby(
            "liquidity_state"
        )[
            "raw_momentum_percentile"
        ]
        .agg(
            [
                "count",
                "mean",
                "median"
            ]
        )
        .sort_values(
            "median",
            ascending=False
        )
    )

    print(
        summary.to_string(
            float_format=lambda x:
                f"{x:.2f}"
        )
    )

    print(
        "\n=== TOP 20 RAW MOMENTUM ==="
    )

    top = df.sort_values(
        "raw_momentum_percentile",
        ascending=False
    ).head(20)

    columns = [
        "symbol",
        "raw_momentum_percentile",
        "return_20d",
        "return_60d",
        "price_vs_ma20",
        "price_vs_ma60",
        "liquidity_state",
        "momentum_evidence"
    ]

    print(
        top[columns].to_string(
            index=False,
            float_format=lambda x:
                f"{x:.4f}"
        )
    )


if __name__ == "__main__":
    main()