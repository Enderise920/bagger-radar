import json
from pathlib import Path

import pandas as pd


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

MOMENTUM_FILE = DATA_DIR / "momentum_scores.json"


def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def main():

    print(
        "=== BAGGER RADAR MOMENTUM VALIDATION ==="
    )

    data = load_json(
        MOMENTUM_FILE
    )

    df = pd.DataFrame(
        data.values()
    )

    print(
        "\nStocks validated:",
        len(df)
    )

    # -----------------------------------------
    # 1. Score by liquidity state
    # -----------------------------------------

    print(
        "\n=== SCORE BY LIQUIDITY STATE ==="
    )

    summary = (
        df.groupby(
            "liquidity_state"
        )[
            "momentum_score"
        ]
        .agg(
            [
                "count",
                "mean",
                "median",
                "min",
                "max"
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

    # -----------------------------------------
    # 2. Evidence distribution
    # -----------------------------------------

    print(
        "\n=== SCORE BY MOMENTUM EVIDENCE ==="
    )

    evidence = (
        df.groupby(
            "momentum_evidence"
        )[
            "momentum_score"
        ]
        .agg(
            [
                "count",
                "mean",
                "median",
                "max"
            ]
        )
        .sort_values(
            "median",
            ascending=False
        )
    )

    print(
        evidence.to_string(
            float_format=lambda x:
                f"{x:.2f}"
        )
    )

    # -----------------------------------------
    # 3. Top 20 evidence check
    # -----------------------------------------

    print(
        "\n=== TOP 20 EVIDENCE CHECK ==="
    )

    top20 = df.sort_values(
        "momentum_score",
        ascending=False
    ).head(20)

    print(
        top20[
            [
                "symbol",
                "momentum_score",
                "momentum_evidence",
                "liquidity_state",
                "return_20d",
                "return_60d"
            ]
        ].to_string(
            index=False,
            float_format=lambda x:
                f"{x:.4f}"
        )
    )

    # -----------------------------------------
    # 4. High score but negative returns
    # -----------------------------------------

    print(
        "\n=== HIGH SCORE + NEGATIVE RETURN CHECK ==="
    )

    suspicious = df[
        (
            df["momentum_score"] >= 80
        )
        &
        (
            df["return_20d"] < 0
        )
    ].sort_values(
        "momentum_score",
        ascending=False
    )

    print(
        "Score >=80 but negative 20D return:",
        len(suspicious)
    )

    if not suspicious.empty:

        print(
            suspicious[
                [
                    "symbol",
                    "momentum_score",
                    "return_20d",
                    "return_60d",
                    "price_vs_ma20",
                    "price_vs_ma60",
                    "liquidity_state"
                ]
            ].head(20).to_string(
                index=False,
                float_format=lambda x:
                    f"{x:.4f}"
            )
        )

    # -----------------------------------------
    # 5. Correlation
    # -----------------------------------------

    print(
        "\n=== SCORE / RETURN CORRELATION ==="
    )

    print(
        "Momentum Score vs 20D return:",
        f"{df['momentum_score'].corr(df['return_20d']):.4f}"
    )

    print(
        "Momentum Score vs 60D return:",
        f"{df['momentum_score'].corr(df['return_60d']):.4f}"
    )

    # -----------------------------------------
    # 6. Score buckets
    # -----------------------------------------

    df["score_bucket"] = pd.cut(
        df["momentum_score"],
        bins=[
            -1,
            20,
            40,
            60,
            80,
            101
        ],
        labels=[
            "0-20",
            "20-40",
            "40-60",
            "60-80",
            "80-100"
        ]
    )

    print(
        "\n=== SCORE BUCKETS ==="
    )

    buckets = (
        df.groupby(
            "score_bucket",
            observed=False
        )[
            [
                "return_20d",
                "return_60d"
            ]
        ]
        .mean()
    )

    print(
        buckets.to_string(
            float_format=lambda x:
                f"{x * 100:.2f}%"
        )
    )


if __name__ == "__main__":

    main()