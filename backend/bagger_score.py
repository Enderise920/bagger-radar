import json
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DIMENSION_FILE = DATA_DIR / "dimension_scores.json"
MOMENTUM_FILE = DATA_DIR / "momentum_scores.json"
RISK_FILE = DATA_DIR / "risk_scores.json"

OUTPUT_FILE = DATA_DIR / "bagger_scores.json"


# =========================================================
# BASELINE WEIGHTS
# =========================================================

WEIGHTS = {
    "growth_score": 0.25,
    "quality_score": 0.20,
    "valuation_score": 0.20,
    "momentum_score": 0.20,
    "risk_strength": 0.15,
}


def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def to_dataframe(data):

    if isinstance(data, list):
        return pd.DataFrame(data)

    if isinstance(data, dict):
        return pd.DataFrame(list(data.values()))

    raise ValueError(
        f"Unsupported JSON structure: {type(data)}"
    )


def validate_score_range(df, columns):

    for column in columns:

        values = pd.to_numeric(
            df[column],
            errors="coerce",
        ).dropna()

        invalid = values[
            (values < 0) |
            (values > 100)
        ]

        if len(invalid) > 0:

            raise ValueError(
                f"{column} memiliki score "
                f"di luar range 0-100."
            )


def calculate_signal(row):

    score = row["bagger_score"]
    evidence = row["evidence_level"]

    if pd.isna(score):

        return "INSUFFICIENT_EVIDENCE"

    if evidence == "LOW":

        return "LIMITED_EVIDENCE"

    if score >= 80:

        return "VERY_STRONG_COMPOSITE"

    if score >= 65:

        return "STRONG_COMPOSITE"

    if score >= 50:

        return "BALANCED_COMPOSITE"

    if score >= 35:

        return "WEAK_COMPOSITE"

    return "LOW_COMPOSITE"


def calculate_evidence_level(row):

    available = int(
        row["available_dimensions"]
    )

    if available >= 5:

        return "HIGH"

    if available >= 4:

        return "MEDIUM"

    if available >= 3:

        return "LOW"

    return "INSUFFICIENT"


def main():

    print("=" * 70)
    print("MODULE 8.2 — BAGGER SCORE ENGINE")
    print("=" * 70)

    # =========================================================
    # LOAD DATA
    # =========================================================

    dimension_data = load_json(
        DIMENSION_FILE
    )

    momentum_data = load_json(
        MOMENTUM_FILE
    )

    risk_data = load_json(
        RISK_FILE
    )

    dimension_df = to_dataframe(
        dimension_data
    )

    momentum_df = to_dataframe(
        momentum_data
    )

    risk_df = to_dataframe(
        risk_data
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

    # =========================================================
    # NUMERIC CONVERSION
    # =========================================================

    score_columns = [
        "growth_score",
        "quality_score",
        "valuation_score",
        "momentum_score",
        "risk_score",
    ]

    for column in score_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    validate_score_range(
        df,
        score_columns,
    )

    # =========================================================
    # RISK STRENGTH
    #
    # Risk Score:
    # higher = more risk
    #
    # Bagger Score:
    # higher = better composite profile
    #
    # Therefore:
    #
    # Risk Strength = 100 - Risk Score
    # =========================================================

    df["risk_strength"] = np.where(
        df["risk_score"].notna(),
        100 - df["risk_score"],
        np.nan,
    )

    # =========================================================
    # AVAILABLE DIMENSIONS
    # =========================================================

    scoring_columns = [
        "growth_score",
        "quality_score",
        "valuation_score",
        "momentum_score",
        "risk_strength",
    ]

    df["available_dimensions"] = (
        df[scoring_columns]
        .notna()
        .sum(axis=1)
    )

    # =========================================================
    # CALCULATE FULL SCORE
    #
    # IMPORTANT:
    # Baseline score is calculated ONLY when
    # all 5 dimensions are available.
    #
    # We do NOT silently renormalize weights
    # for missing dimensions.
    # =========================================================

    df["bagger_score"] = np.nan

    complete_mask = (
        df["available_dimensions"] == 5
    )

    df.loc[
        complete_mask,
        "bagger_score"
    ] = (
        df.loc[complete_mask, "growth_score"]
        * WEIGHTS["growth_score"]
        +
        df.loc[complete_mask, "quality_score"]
        * WEIGHTS["quality_score"]
        +
        df.loc[complete_mask, "valuation_score"]
        * WEIGHTS["valuation_score"]
        +
        df.loc[complete_mask, "momentum_score"]
        * WEIGHTS["momentum_score"]
        +
        df.loc[complete_mask, "risk_strength"]
        * WEIGHTS["risk_strength"]
    )

    # =========================================================
    # EVIDENCE LEVEL
    # =========================================================

    df["evidence_level"] = df.apply(
        calculate_evidence_level,
        axis=1,
    )

    # =========================================================
    # SIGNAL
    # =========================================================

    df["composite_signal"] = df.apply(
        calculate_signal,
        axis=1,
    )

    # =========================================================
    # RISK INFORMATION
    # =========================================================

    df["risk_evidence"] = (
        df["risk_evidence"]
        .fillna("NO_DATA")
    )

    df["liquidity_flag"] = (
        df["liquidity_flag"]
        .fillna("NO_DATA")
    )

    # =========================================================
    # SCORE ROUNDING
    # =========================================================

    df["bagger_score"] = (
        df["bagger_score"]
        .round(2)
    )

    df["risk_strength"] = (
        df["risk_strength"]
        .round(2)
    )

    # =========================================================
    # SORT
    # =========================================================

    df = df.sort_values(
        by="bagger_score",
        ascending=False,
        na_position="last",
    )

    # =========================================================
    # OUTPUT COLUMNS
    # =========================================================

    output_columns = [
        "symbol",
        "growth_score",
        "quality_score",
        "valuation_score",
        "momentum_score",
        "risk_score",
        "risk_strength",
        "bagger_score",
        "available_dimensions",
        "evidence_level",
        "composite_signal",
        "risk_evidence",
        "liquidity_flag",
    ]

    output_df = df[
        output_columns
    ].copy()

    # =========================================================
    # SAVE
    # =========================================================

    records = (
        output_df
        .replace(
            {
                np.nan: None
            }
        )
        .to_dict(
            orient="records"
        )
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            records,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # =========================================================
    # REPORT
    # =========================================================

    print("\nWeights:")

    for name, weight in WEIGHTS.items():

        print(
            f"{name:20s}: "
            f"{weight * 100:.0f}%"
        )

    print("\nUniverse:")
    print(
        f"Total stocks      : {len(df)}"
    )

    print(
        f"5/5 dimensions    : "
        f"{complete_mask.sum()}"
    )

    print(
        f"4/5 dimensions    : "
        f"{(df['available_dimensions'] == 4).sum()}"
    )

    print(
        f"3/5 dimensions    : "
        f"{(df['available_dimensions'] == 3).sum()}"
    )

    print(
        f"2/5 dimensions    : "
        f"{(df['available_dimensions'] == 2).sum()}"
    )

    print(
        f"1/5 dimensions    : "
        f"{(df['available_dimensions'] == 1).sum()}"
    )

    print(
        f"0/5 dimensions    : "
        f"{(df['available_dimensions'] == 0).sum()}"
    )

    print("\nEvidence Level:")
    print(
        df["evidence_level"]
        .value_counts()
        .to_string()
    )

    scored = (
        df["bagger_score"]
        .dropna()
    )

    print("\nBagger Score:")

    if len(scored) > 0:

        print(
            f"Scored stocks     : {len(scored)}"
        )

        print(
            f"Mean              : "
            f"{scored.mean():.2f}"
        )

        print(
            f"Median            : "
            f"{scored.median():.2f}"
        )

        print(
            f"P75               : "
            f"{scored.quantile(.75):.2f}"
        )

        print(
            f"P90               : "
            f"{scored.quantile(.90):.2f}"
        )

        print(
            f"Minimum           : "
            f"{scored.min():.2f}"
        )

        print(
            f"Maximum           : "
            f"{scored.max():.2f}"
        )

    print("\nComposite Signal:")
    print(
        df["composite_signal"]
        .value_counts()
        .to_string()
    )

    print("\nTop 20:")
    print(
        output_df[
            [
                "symbol",
                "bagger_score",
                "evidence_level",
                "composite_signal",
            ]
        ]
        .head(20)
        .to_string(
            index=False
        )
    )

    print(
        f"\nSaved to: {OUTPUT_FILE}"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()