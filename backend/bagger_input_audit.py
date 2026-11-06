import json
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DIMENSION_FILE = DATA_DIR / "dimension_scores.json"
MOMENTUM_FILE = DATA_DIR / "momentum_scores.json"
RISK_FILE = DATA_DIR / "risk_scores.json"


def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def to_dataframe(data):
    """
    Supports both:
    - list of records
    - dictionary keyed by symbol
    """

    if isinstance(data, list):
        return pd.DataFrame(data)

    if isinstance(data, dict):
        return pd.DataFrame(list(data.values()))

    raise ValueError("Unsupported JSON structure")


def describe_dimension(df, column):
    values = pd.to_numeric(
        df[column],
        errors="coerce",
    ).dropna()

    if len(values) == 0:
        return None

    return {
        "count": len(values),
        "coverage": len(values) / len(df),
        "mean": values.mean(),
        "median": values.median(),
        "std": values.std(),
        "p10": values.quantile(0.10),
        "p25": values.quantile(0.25),
        "p75": values.quantile(0.75),
        "p90": values.quantile(0.90),
        "min": values.min(),
        "max": values.max(),
    }


def main():

    print("=" * 70)
    print("MODULE 8.1 — BAGGER SCORE INPUT AUDIT")
    print("=" * 70)

    # =========================================================
    # LOAD
    # =========================================================

    dimension_data = load_json(DIMENSION_FILE)
    momentum_data = load_json(MOMENTUM_FILE)
    risk_data = load_json(RISK_FILE)

    dimension_df = to_dataframe(dimension_data)
    momentum_df = to_dataframe(momentum_data)
    risk_df = to_dataframe(risk_data)

    print("\nInput records:")
    print(f"Dimension scores : {len(dimension_df)}")
    print(f"Momentum scores  : {len(momentum_df)}")
    print(f"Risk scores      : {len(risk_df)}")

    # =========================================================
    # REQUIRED DIMENSION COLUMNS
    # =========================================================

    required_dimension_columns = [
        "symbol",
        "growth_score",
        "quality_score",
        "valuation_score",
    ]

    missing = [
        c
        for c in required_dimension_columns
        if c not in dimension_df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing dimension columns: {missing}"
        )

    if "symbol" not in momentum_df.columns:
        raise ValueError(
            "symbol tidak ditemukan di momentum_scores.json"
        )

    if "symbol" not in risk_df.columns:
        raise ValueError(
            "symbol tidak ditemukan di risk_scores.json"
        )

    if "momentum_score" not in momentum_df.columns:
        raise ValueError(
            "momentum_score tidak ditemukan"
        )

    if "risk_score" not in risk_df.columns:
        raise ValueError(
            "risk_score tidak ditemukan"
        )

    # =========================================================
    # MERGE
    # =========================================================

    df = dimension_df[
        [
            "symbol",
            "growth_score",
            "quality_score",
            "valuation_score",
        ]
    ].merge(
        momentum_df[
            [
                "symbol",
                "momentum_score",
            ]
        ],
        on="symbol",
        how="outer",
    ).merge(
        risk_df[
            [
                "symbol",
                "risk_score",
                "risk_evidence",
                "liquidity_flag",
            ]
        ],
        on="symbol",
        how="outer",
    )

    print(
        f"\nCombined universe: {len(df)}"
    )

    # =========================================================
    # COVERAGE
    # =========================================================

    dimensions = [
        "growth_score",
        "quality_score",
        "valuation_score",
        "momentum_score",
        "risk_score",
    ]

    print("\n" + "-" * 70)
    print("DIMENSION COVERAGE")
    print("-" * 70)

    audit_rows = []

    for dimension in dimensions:

        stats = describe_dimension(
            df,
            dimension,
        )

        if stats is None:

            print(
                f"{dimension:20s} "
                "NO DATA"
            )

            continue

        audit_rows.append(
            {
                "dimension": dimension,
                **stats,
            }
        )

        print(
            f"{dimension:20s} "
            f"count={stats['count']:4d} "
            f"coverage={stats['coverage'] * 100:6.2f}% "
            f"mean={stats['mean']:6.2f} "
            f"median={stats['median']:6.2f} "
            f"p10={stats['p10']:6.2f} "
            f"p90={stats['p90']:6.2f} "
            f"min={stats['min']:6.2f} "
            f"max={stats['max']:6.2f}"
        )

    # =========================================================
    # RISK EVIDENCE
    # =========================================================

    print("\n" + "-" * 70)
    print("RISK EVIDENCE")
    print("-" * 70)

    print(
        df["risk_evidence"]
        .value_counts(dropna=False)
        .to_string()
    )

    print("\nLiquidity:")
    print(
        df["liquidity_flag"]
        .value_counts(dropna=False)
        .to_string()
    )

    # =========================================================
    # COMPLETE CASES
    # =========================================================

    complete_mask = df[dimensions].notna().all(axis=1)

    complete_count = complete_mask.sum()

    print("\n" + "-" * 70)
    print("COMPLETE SCORE COVERAGE")
    print("-" * 70)

    print(
        f"All 5 dimensions available: "
        f"{complete_count}/{len(df)} "
        f"({complete_count / len(df) * 100:.2f}%)"
    )

    # =========================================================
    # PARTIAL CASES
    # =========================================================

    df["available_dimensions"] = (
        df[dimensions]
        .notna()
        .sum(axis=1)
    )

    print("\nAvailable dimensions per stock:")

    print(
        df["available_dimensions"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    # =========================================================
    # DIMENSION CORRELATION
    # =========================================================

    print("\n" + "-" * 70)
    print("DIMENSION CORRELATION")
    print("-" * 70)

    correlation = df[dimensions].corr()

    print(
        correlation.round(3).to_string()
    )

    # =========================================================
    # RISK DIRECTION CHECK
    #
    # Risk is different:
    # higher risk = worse
    #
    # For Bagger Score we will later need:
    #
    # risk_strength = 100 - risk_score
    # =========================================================

    if "risk_score" in df.columns:

        risk_values = df["risk_score"].dropna()

        if len(risk_values) > 0:

            risk_strength = (
                100 - risk_values
            )

            print("\n" + "-" * 70)
            print("RISK DIRECTION CHECK")
            print("-" * 70)

            print(
                f"Risk Score mean       : "
                f"{risk_values.mean():.2f}"
            )

            print(
                f"Risk Strength mean    : "
                f"{risk_strength.mean():.2f}"
            )

            print(
                "Interpretation: "
                "higher Risk Score = more risk, "
                "therefore lower contribution to Bagger Score."
            )

    # =========================================================
    # POTENTIAL 5-DIMENSION UNIVERSE
    # =========================================================

    usable_mask = (
        df["growth_score"].notna()
        & df["quality_score"].notna()
        & df["valuation_score"].notna()
        & df["momentum_score"].notna()
    )

    usable_count = usable_mask.sum()

    print("\n" + "-" * 70)
    print("PRELIMINARY USABLE UNIVERSE")
    print("-" * 70)

    print(
        "Stocks with Growth + Quality + "
        f"Valuation + Momentum: "
        f"{usable_count}/{len(df)} "
        f"({usable_count / len(df) * 100:.2f}%)"
    )

    usable_with_risk = (
        usable_mask
        & df["risk_score"].notna()
    ).sum()

    print(
        "Stocks with all 5 numeric dimensions: "
        f"{usable_with_risk}/{len(df)} "
        f"({usable_with_risk / len(df) * 100:.2f}%)"
    )

    # =========================================================
    # SAVE AUDIT
    # =========================================================

    audit_output = DATA_DIR / "bagger_input_audit.json"

    output = {
        "total_universe": int(len(df)),
        "complete_5_dimension": int(
            complete_count
        ),
        "complete_5_dimension_pct": float(
            complete_count / len(df) * 100
        ),
        "dimension_stats": audit_rows,
    }

    with open(
        audit_output,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            output,
            f,
            indent=2,
        )

    print(
        f"\nAudit saved to: {audit_output}"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()