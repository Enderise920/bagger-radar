import json
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

RISK_METRICS_FILE = DATA_DIR / "risk_metrics.json"
LIQUIDITY_FILE = DATA_DIR / "liquidity_flags.json"
OUTPUT_FILE = DATA_DIR / "risk_scores.json"


def percentile_score(value, values):
    """Convert a value into a 0-100 percentile score."""

    if value is None or pd.isna(value):
        return None

    clean_values = [
        float(v)
        for v in values
        if v is not None and not pd.isna(v)
    ]

    if not clean_values:
        return None

    return float(
        np.sum(
            np.array(clean_values) <= float(value)
        )
        / len(clean_values)
        * 100
    )


def load_json_dict_as_dataframe(filepath):
    """
    Load a JSON file structured as:

    {
        "SBAT.JK": {
            "symbol": "SBAT.JK",
            ...
        },
        "MKNT.JK": {
            ...
        }
    }

    and convert it into a DataFrame.
    """

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(
            f"{filepath.name} harus berupa dictionary."
        )

    records = list(data.values())

    if not records:
        raise ValueError(
            f"{filepath.name} kosong."
        )

    return pd.DataFrame(records)


def calculate_risk_scores():

    print("=" * 60)
    print("MODULE 7.5 — RISK EVIDENCE & LIQUIDITY TREATMENT")
    print("=" * 60)

    # =========================================================
    # LOAD DATA
    # =========================================================

    risk_df = load_json_dict_as_dataframe(
        RISK_METRICS_FILE
    )

    liquidity_df = load_json_dict_as_dataframe(
        LIQUIDITY_FILE
    )

    print(
        f"Risk metric stocks: {len(risk_df)}"
    )

    print(
        f"Liquidity stocks:   {len(liquidity_df)}"
    )

    # =========================================================
    # VALIDATE RISK COLUMNS
    # =========================================================

    required_risk_columns = [
        "symbol",
        "volatility_20d",
        "max_drawdown_60d",
        "max_daily_loss_20d",
    ]

    for column in required_risk_columns:

        if column not in risk_df.columns:
            raise ValueError(
                f"Kolom '{column}' tidak ditemukan "
                f"di risk_metrics.json"
            )

    # =========================================================
    # VALIDATE LIQUIDITY COLUMNS
    # =========================================================

    required_liquidity_columns = [
        "symbol",
        "liquidity_state",
        "momentum_evidence",
    ]

    for column in required_liquidity_columns:

        if column not in liquidity_df.columns:
            raise ValueError(
                f"Kolom '{column}' tidak ditemukan "
                f"di liquidity_flags.json"
            )

    # =========================================================
    # MERGE
    # =========================================================

    df = risk_df.merge(
        liquidity_df[
            [
                "symbol",
                "liquidity_state",
                "momentum_evidence",
            ]
        ],
        on="symbol",
        how="left",
    )

    print(
        f"Merged stocks:      {len(df)}"
    )

    # =========================================================
    # PREPARE DISTRIBUTIONS
    # =========================================================

    volatility_values = (
        pd.to_numeric(
            df["volatility_20d"],
            errors="coerce",
        )
        .dropna()
        .tolist()
    )

    drawdown_values = (
        pd.to_numeric(
            df["max_drawdown_60d"],
            errors="coerce",
        )
        .abs()
        .dropna()
        .tolist()
    )

    extreme_loss_values = (
        pd.to_numeric(
            df["max_daily_loss_20d"],
            errors="coerce",
        )
        .abs()
        .dropna()
        .tolist()
    )

    # =========================================================
    # COMPONENT SCORES
    # =========================================================

    df["volatility_score"] = (
        df["volatility_20d"]
        .apply(
            lambda x: percentile_score(
                x,
                volatility_values,
            )
        )
    )

    df["drawdown_score"] = (
        df["max_drawdown_60d"]
        .abs()
        .apply(
            lambda x: percentile_score(
                x,
                drawdown_values,
            )
        )
    )

    df["extreme_loss_score"] = (
        df["max_daily_loss_20d"]
        .abs()
        .apply(
            lambda x: percentile_score(
                x,
                extreme_loss_values,
            )
        )
    )

    # =========================================================
    # RAW RISK SCORE
    #
    # Equal weight:
    #
    # Volatility       1/3
    # Drawdown         1/3
    # Extreme Loss     1/3
    # =========================================================

    risk_components = [
        "volatility_score",
        "drawdown_score",
        "extreme_loss_score",
    ]

    df["risk_score_raw"] = (
        df[risk_components]
        .mean(
            axis=1,
            skipna=True,
        )
    )

    # =========================================================
    # EVIDENCE
    # =========================================================

    df["liquidity_flag"] = (
        df["liquidity_state"]
        .fillna("UNKNOWN")
    )

    evidence_mapping = {
        "ACTIVE": "GOOD",
        "CAUTION": "MODERATE",
        "LOW_ACTIVITY": "LIMITED",
        "STALE": "INSUFFICIENT",
        "NO_TRADING_EVIDENCE": "INSUFFICIENT",
    }

    df["risk_evidence"] = (
        df["liquidity_flag"]
        .map(evidence_mapping)
        .fillna("INSUFFICIENT")
    )

    # =========================================================
    # LIQUIDITY MODIFIER
    # =========================================================

    liquidity_modifier_mapping = {
        "ACTIVE": 0,
        "CAUTION": 5,
        "LOW_ACTIVITY": 10,
        "STALE": 15,
        "NO_TRADING_EVIDENCE": 0,
    }

    df["liquidity_modifier"] = (
        df["liquidity_flag"]
        .map(
            liquidity_modifier_mapping
        )
        .fillna(0)
    )

    # =========================================================
    # FINAL RISK SCORE
    # =========================================================

    df["risk_score"] = (
        df["risk_score_raw"]
        + df["liquidity_modifier"]
    ).clip(0, 100)

    # =========================================================
    # CRITICAL RULE
    #
    # NO_TRADING_EVIDENCE:
    #
    # Risk Score = N/A
    # Risk Evidence = INSUFFICIENT
    #
    # Zero price movement must NEVER be interpreted
    # as low risk.
    # =========================================================

    no_evidence_mask = (
        df["liquidity_flag"]
        == "NO_TRADING_EVIDENCE"
    )

    df.loc[
        no_evidence_mask,
        "risk_score"
    ] = np.nan

    df.loc[
        no_evidence_mask,
        "risk_score_raw"
    ] = np.nan

    # =========================================================
    # RISK INTERPRETATION
    # =========================================================

    def interpret_risk(row):

        flag = row["liquidity_flag"]
        evidence = row["risk_evidence"]
        score = row["risk_score"]

        if flag == "NO_TRADING_EVIDENCE":
            return "INSUFFICIENT_EVIDENCE"

        if pd.isna(score):
            return "INSUFFICIENT_EVIDENCE"

        if score >= 80:
            base = "HIGH_RISK"

        elif score >= 60:
            base = "ELEVATED_RISK"

        elif score >= 40:
            base = "MODERATE_RISK"

        else:
            base = "LOWER_RISK"

        if evidence == "INSUFFICIENT":
            return (
                base
                + "_INSUFFICIENT_EVIDENCE"
            )

        if evidence == "LIMITED":
            return (
                base
                + "_LIMITED_EVIDENCE"
            )

        if evidence == "MODERATE":
            return (
                base
                + "_MODERATE_EVIDENCE"
            )

        return base

    df["risk_interpretation"] = (
        df.apply(
            interpret_risk,
            axis=1,
        )
    )

    # =========================================================
    # OUTPUT COLUMNS
    # =========================================================

    output_columns = [
        "symbol",

        # Risk metrics
        "volatility_20d",
        "volatility_60d",
        "max_drawdown_60d",
        "zero_return_ratio_20d",
        "unique_price_ratio_20d",
        "max_daily_gain_20d",
        "max_daily_loss_20d",

        # Components
        "volatility_score",
        "drawdown_score",
        "extreme_loss_score",

        # Risk calculation
        "risk_score_raw",
        "liquidity_modifier",
        "risk_score",

        # Evidence
        "liquidity_flag",
        "risk_evidence",
        "risk_interpretation",

        # Original liquidity evidence
        "momentum_evidence",
    ]

    output_columns = [
        column
        for column in output_columns
        if column in df.columns
    ]

    result = df[
        output_columns
    ].copy()

    # =========================================================
    # ROUND NUMBERS
    # =========================================================

    text_columns = [
        "symbol",
        "liquidity_flag",
        "risk_evidence",
        "risk_interpretation",
        "momentum_evidence",
    ]

    numeric_columns = [
        column
        for column in result.columns
        if column not in text_columns
    ]

    for column in numeric_columns:

        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        ).round(6)

    # =========================================================
    # SAVE
    # =========================================================

    result.to_json(
        OUTPUT_FILE,
        orient="records",
        indent=2,
    )

    # =========================================================
    # SUMMARY
    # =========================================================

    print("\nRisk Evidence:")
    print(
        result["risk_evidence"]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print("\nLiquidity State:")
    print(
        result["liquidity_flag"]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    numeric_risk = (
        result["risk_score"]
        .dropna()
    )

    print("\nNumeric Risk Score:")

    if len(numeric_risk) > 0:

        print(
            f"Scored : {len(numeric_risk)}"
        )

        print(
            f"Mean   : {numeric_risk.mean():.2f}"
        )

        print(
            f"Median : {numeric_risk.median():.2f}"
        )

        print(
            f"P75    : {numeric_risk.quantile(0.75):.2f}"
        )

        print(
            f"P90    : {numeric_risk.quantile(0.90):.2f}"
        )

        print(
            f"Max    : {numeric_risk.max():.2f}"
        )

    # =========================================================
    # CRITICAL VALIDATION
    # =========================================================

    no_evidence_with_score = (
        result.loc[
            result["liquidity_flag"]
            == "NO_TRADING_EVIDENCE",
            "risk_score",
        ]
        .notna()
        .sum()
    )

    no_evidence_count = (
        result["liquidity_flag"]
        .eq("NO_TRADING_EVIDENCE")
        .sum()
    )

    print(
        "\nNO_TRADING_EVIDENCE stocks:"
        f" {no_evidence_count}"
    )

    print(
        "NO_TRADING_EVIDENCE "
        "with numeric score:"
        f" {no_evidence_with_score}"
    )

    if no_evidence_with_score == 0:

        print(
            "PASS: NO_TRADING_EVIDENCE "
            "stocks have no numeric risk score."
        )

    else:

        print(
            "FAIL: Some NO_TRADING_EVIDENCE "
            "stocks still have numeric risk scores."
        )

    print(
        f"\nSaved to: {OUTPUT_FILE}"
    )

    print("=" * 60)


if __name__ == "__main__":
    calculate_risk_scores()