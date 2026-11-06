import json
from pathlib import Path

import numpy as np
import pandas as pd


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DAILY_CACHE = DATA_DIR / "daily_cache.json"
LIQUIDITY_FILE = DATA_DIR / "liquidity_flags.json"
OUTPUT_FILE = DATA_DIR / "momentum_scores.json"


EVIDENCE_ADJUSTMENT = {
    "GOOD": 1.00,
    "MODERATE": 0.90,
    "LIMITED": 0.75,
    "INSUFFICIENT": 0.50
}


def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def percentile_score(value, values):

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


def calculate_momentum(
    symbol,
    records
):

    df = pd.DataFrame(records)

    if not all(
        column in df.columns
        for column in ["date", "close"]
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
        subset=["date", "close"]
    )

    df = df.sort_values(
        "date"
    ).reset_index(drop=True)

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
        "=== BAGGER RADAR MOMENTUM SCORE ==="
    )

    cache = load_json(
        DAILY_CACHE
    )

    liquidity = load_json(
        LIQUIDITY_FILE
    )

    raw_results = []

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

        raw_results.append(
            momentum
        )

    df = pd.DataFrame(
        raw_results
    )

    metrics = [
        "return_20d",
        "return_60d",
        "price_vs_ma20",
        "price_vs_ma60"
    ]

    # -----------------------------------------
    # Relative percentile
    # -----------------------------------------

    for metric in metrics:

        values = df[metric].tolist()

        df[
            f"{metric}_percentile"
        ] = df[metric].apply(
            lambda value:
                percentile_score(
                    value,
                    values
                )
        )

    percentile_columns = [
        f"{metric}_percentile"
        for metric in metrics
    ]

    df[
        "raw_momentum_score"
    ] = df[
        percentile_columns
    ].mean(
        axis=1
    )

    # -----------------------------------------
    # Evidence adjustment
    # -----------------------------------------

    df[
        "evidence_adjustment"
    ] = df[
        "momentum_evidence"
    ].map(
        EVIDENCE_ADJUSTMENT
    )

    df[
        "momentum_score"
    ] = (
        df["raw_momentum_score"]
        * df["evidence_adjustment"]
    )

    df[
        "momentum_score"
    ] = df[
        "momentum_score"
    ].clip(
        0,
        100
    )

    # -----------------------------------------
    # Save
    # -----------------------------------------

    output = {}

    for _, row in df.iterrows():

        output[
            row["symbol"]
        ] = {
            "symbol": row["symbol"],

            "return_20d":
                float(row["return_20d"]),

            "return_60d":
                float(row["return_60d"]),

            "price_vs_ma20":
                float(row["price_vs_ma20"]),

            "price_vs_ma60":
                float(row["price_vs_ma60"]),

            "raw_momentum_score":
                round(
                    float(
                        row[
                            "raw_momentum_score"
                        ]
                    ),
                    2
                ),

            "momentum_evidence":
                row[
                    "momentum_evidence"
                ],

            "evidence_adjustment":
                float(
                    row[
                        "evidence_adjustment"
                    ]
                ),

            "momentum_score":
                round(
                    float(
                        row[
                            "momentum_score"
                        ]
                    ),
                    2
                ),

            "liquidity_state":
                row[
                    "liquidity_state"
                ]
        }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False
        )

    # -----------------------------------------
    # Validation output
    # -----------------------------------------

    print(
        "\nStocks scored:",
        len(df)
    )

    print(
        "\n=== MOMENTUM SCORE DISTRIBUTION ==="
    )

    print(
        df[
            "momentum_score"
        ].describe(
            percentiles=[
                0.10,
                0.25,
                0.50,
                0.75,
                0.90
            ]
        ).to_string()
    )

    print(
        "\n=== TOP 20 PRODUCTION MOMENTUM ==="
    )

    top = df.sort_values(
        "momentum_score",
        ascending=False
    ).head(20)

    columns = [
        "symbol",
        "momentum_score",
        "raw_momentum_score",
        "momentum_evidence",
        "liquidity_state",
        "return_20d",
        "return_60d"
    ]

    print(
        top[
            columns
        ].to_string(
            index=False,
            float_format=lambda x:
                f"{x:.4f}"
        )
    )

    print(
        "\nSaved:",
        OUTPUT_FILE
    )


if __name__ == "__main__":

    main()