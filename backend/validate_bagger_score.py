import json
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

INPUT_FILE = DATA_DIR / "bagger_scores.json"


def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def main():

    print("=" * 70)
    print("MODULE 8.3 — BAGGER SCORE VALIDATION")
    print("=" * 70)

    data = load_json(INPUT_FILE)

    df = pd.DataFrame(data)

    print(f"\nProduction records: {len(df)}")

    # =========================================================
    # BASIC VALIDATION
    # =========================================================

    required_columns = [
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
    ]

    missing_columns = [
        c for c in required_columns
        if c not in df.columns
    ]

    if missing_columns:

        raise ValueError(
            f"Missing columns: {missing_columns}"
        )

    print("PASS: Required columns tersedia.")

    # =========================================================
    # SYMBOL VALIDATION
    # =========================================================

    if df["symbol"].isna().any():

        raise ValueError(
            "Ada symbol kosong."
        )

    if df["symbol"].duplicated().any():

        duplicates = df.loc[
            df["symbol"].duplicated(),
            "symbol"
        ].tolist()

        raise ValueError(
            f"Duplicate symbols: {duplicates}"
        )

    print("PASS: Tidak ada symbol kosong/duplicate.")

    # =========================================================
    # SCORE RANGE
    # =========================================================

    score_columns = [
        "growth_score",
        "quality_score",
        "valuation_score",
        "momentum_score",
        "risk_score",
        "risk_strength",
        "bagger_score",
    ]

    for column in score_columns:

        values = pd.to_numeric(
            df[column],
            errors="coerce",
        ).dropna()

        if ((values < 0) | (values > 100)).any():

            raise ValueError(
                f"{column} keluar dari range 0-100."
            )

    print(
        "PASS: Semua score numeric berada di 0-100."
    )

    # =========================================================
    # RISK STRENGTH
    # =========================================================

    risk_mask = (
        df["risk_score"].notna()
        & df["risk_strength"].notna()
    )

    expected_risk_strength = (
        100 - df.loc[
            risk_mask,
            "risk_score"
        ]
    )

    actual_risk_strength = df.loc[
        risk_mask,
        "risk_strength"
    ]

    if not np.allclose(
        expected_risk_strength,
        actual_risk_strength,
        atol=0.02,
    ):

        raise ValueError(
            "Risk Strength tidak sama dengan 100 - Risk Score."
        )

    print(
        "PASS: Risk Strength = 100 - Risk Score."
    )

    # =========================================================
    # 5-DIMENSION SCORE FORMULA
    # =========================================================

    complete = (
        df["available_dimensions"] == 5
    )

    expected_score = (
        df.loc[complete, "growth_score"] * 0.25
        + df.loc[complete, "quality_score"] * 0.20
        + df.loc[complete, "valuation_score"] * 0.20
        + df.loc[complete, "momentum_score"] * 0.20
        + df.loc[complete, "risk_strength"] * 0.15
    )

    actual_score = df.loc[
        complete,
        "bagger_score"
    ]

    if not np.allclose(
        expected_score,
        actual_score,
        atol=0.02,
    ):

        differences = pd.DataFrame(
            {
                "symbol": df.loc[
                    complete,
                    "symbol"
                ],
                "expected": expected_score,
                "actual": actual_score,
            }
        )

        differences["difference"] = (
            differences["actual"]
            - differences["expected"]
        )

        raise ValueError(
            "Formula Bagger Score tidak sesuai.\n"
            + differences[
                differences["difference"].abs() > 0.02
            ].head(10).to_string()
        )

    print(
        "PASS: Formula Bagger Score sesuai baseline weights."
    )

    # =========================================================
    # MISSING DATA MUST NOT HAVE SCORE
    # =========================================================

    incomplete = (
        df["available_dimensions"] < 5
    )

    incomplete_with_score = (
        incomplete
        & df["bagger_score"].notna()
    )

    if incomplete_with_score.any():

        print(
            "\nWARNING: Ada incomplete stock "
            "yang memiliki Bagger Score:"
        )

        print(
            df.loc[
                incomplete_with_score,
                [
                    "symbol",
                    "available_dimensions",
                    "bagger_score",
                ],
            ].head(20).to_string(index=False)
        )

        raise ValueError(
            "Incomplete stock tidak boleh memiliki numeric Bagger Score."
        )

    print(
        "PASS: Incomplete stocks tidak memiliki numeric Bagger Score."
    )

    # =========================================================
    # COMPLETE STOCKS MUST HAVE SCORE
    # =========================================================

    complete_without_score = (
        complete
        & df["bagger_score"].isna()
    )

    if complete_without_score.any():

        raise ValueError(
            "Ada stock 5/5 tetapi tidak memiliki Bagger Score."
        )

    print(
        "PASS: Semua stock 5/5 memiliki Bagger Score."
    )

    # =========================================================
    # EVIDENCE LEVEL
    # =========================================================

    evidence_expected = []

    for value in df["available_dimensions"]:

        if value >= 5:
            evidence_expected.append("HIGH")

        elif value >= 4:
            evidence_expected.append("MEDIUM")

        elif value >= 3:
            evidence_expected.append("LOW")

        else:
            evidence_expected.append("INSUFFICIENT")

    if (
        df["evidence_level"].tolist()
        != evidence_expected
    ):

        raise ValueError(
            "Evidence level tidak sesuai available dimensions."
        )

    print(
        "PASS: Evidence level sesuai data completeness."
    )

    # =========================================================
    # SIGNAL VALIDATION
    # =========================================================

    def expected_signal(row):

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

    expected_signals = df.apply(
        expected_signal,
        axis=1,
    )

    if (
        expected_signals
        != df["composite_signal"]
    ).any():

        raise ValueError(
            "Composite Signal tidak sesuai rule."
        )

    print(
        "PASS: Composite Signal sesuai rule."
    )

    # =========================================================
    # TOP 20 COMPONENT ANALYSIS
    # =========================================================

    scored = df[
        df["bagger_score"].notna()
    ].copy()

    scored = scored.sort_values(
        "bagger_score",
        ascending=False,
    )

    top20 = scored.head(20)

    dimensions = [
        "growth_score",
        "quality_score",
        "valuation_score",
        "momentum_score",
        "risk_strength",
    ]

    print("\n" + "-" * 70)
    print("TOP 20 COMPONENT ANALYSIS")
    print("-" * 70)

    print(
        top20[
            [
                "symbol",
                "bagger_score",
                *dimensions,
            ]
        ].round(2).to_string(index=False)
    )

    # =========================================================
    # TOP 20 AVERAGES
    # =========================================================

    print("\nTop 20 average components:")

    top20_avg = (
        top20[dimensions]
        .mean()
        .round(2)
    )

    print(
        top20_avg.to_string()
    )

    # =========================================================
    # FULL UNIVERSE AVERAGES
    # =========================================================

    print("\nFull scored universe averages:")

    universe_avg = (
        scored[dimensions]
        .mean()
        .round(2)
    )

    print(
        universe_avg.to_string()
    )

    # =========================================================
    # SCORE CORRELATION
    # =========================================================

    print("\n" + "-" * 70)
    print("BAGGER SCORE CORRELATION")
    print("-" * 70)

    correlation = (
        scored[
            [
                "bagger_score",
                *dimensions,
            ]
        ]
        .corr()["bagger_score"]
        .drop("bagger_score")
        .sort_values(
            ascending=False
        )
    )

    print(
        correlation.round(3).to_string()
    )

    # =========================================================
    # SCORE BUCKETS
    # =========================================================

    print("\n" + "-" * 70)
    print("BAGGER SCORE BUCKETS")
    print("-" * 70)

    bins = [
        -np.inf,
        20,
        35,
        50,
        65,
        80,
        np.inf,
    ]

    labels = [
        "<20",
        "20-35",
        "35-50",
        "50-65",
        "65-80",
        "80+",
    ]

    scored["score_bucket"] = pd.cut(
        scored["bagger_score"],
        bins=bins,
        labels=labels,
        right=False,
    )

    bucket_summary = (
        scored["score_bucket"]
        .value_counts()
        .sort_index()
    )

    print(
        bucket_summary.to_string()
    )

    # =========================================================
    # HIGH SCORE SANITY CHECK
    # =========================================================

    high_score = scored[
        scored["bagger_score"] >= 65
    ]

    print("\n" + "-" * 70)
    print("HIGH SCORE SANITY CHECK")
    print("-" * 70)

    print(
        f"Score >=65: {len(high_score)} stocks"
    )

    if len(high_score) > 0:

        print(
            "\nAverage dimensions for Score >=65:"
        )

        print(
            high_score[
                dimensions
            ]
            .mean()
            .round(2)
            .to_string()
        )

    # =========================================================
    # VALIDATION SUMMARY
    # =========================================================

    print("\n" + "=" * 70)
    print("MODULE 8.3 VALIDATION SUMMARY")
    print("=" * 70)

    print(
        f"Total records       : {len(df)}"
    )

    print(
        f"Scored stocks       : {len(scored)}"
    )

    print(
        f"High score >=65     : {len(high_score)}"
    )

    print(
        "Formula validation  : PASS"
    )

    print(
        "Missing data policy : PASS"
    )

    print(
        "Evidence validation : PASS"
    )

    print(
        "Signal validation   : PASS"
    )

    print(
        "\nMODULE 8.3 STATUS: PASS"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()