import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

INPUT_FILE = DATA_DIR / "bagger_scores.json"


def load_data():

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
    ) as f:

        df = pd.DataFrame(
            json.load(f)
        )

    return df


def screen_stocks(
    df,
    min_bagger_score=None,
    min_evidence=None,
    min_growth=None,
    min_quality=None,
    min_valuation=None,
    min_momentum=None,
    max_risk=None,
    liquidity=None,
):
    """
    Explainable stock screener.

    All filters are optional.
    """

    result = df.copy()

    # =====================================================
    # ONLY NUMERIC BAGGER SCORE
    # =====================================================

    result = result[
        result["bagger_score"].notna()
    ]

    # =====================================================
    # BAGGER SCORE
    # =====================================================

    if min_bagger_score is not None:

        result = result[
            result["bagger_score"]
            >= min_bagger_score
        ]

    # =====================================================
    # EVIDENCE
    # =====================================================

    if min_evidence is not None:

        evidence_order = {
            "INSUFFICIENT": 0,
            "LOW": 1,
            "MEDIUM": 2,
            "HIGH": 3,
        }

        minimum_level = evidence_order[
            min_evidence
        ]

        result = result[
            result["evidence_level"]
            .map(evidence_order)
            >= minimum_level
        ]

    # =====================================================
    # GROWTH
    # =====================================================

    if min_growth is not None:

        result = result[
            result["growth_score"]
            >= min_growth
        ]

    # =====================================================
    # QUALITY
    # =====================================================

    if min_quality is not None:

        result = result[
            result["quality_score"]
            >= min_quality
        ]

    # =====================================================
    # VALUATION
    # =====================================================

    if min_valuation is not None:

        result = result[
            result["valuation_score"]
            >= min_valuation
        ]

    # =====================================================
    # MOMENTUM
    # =====================================================

    if min_momentum is not None:

        result = result[
            result["momentum_score"]
            >= min_momentum
        ]

    # =====================================================
    # RISK
    #
    # Lower Risk Score = lower risk
    # =====================================================

    if max_risk is not None:

        result = result[
            result["risk_score"]
            <= max_risk
        ]

    # =====================================================
    # LIQUIDITY
    # =====================================================

    if liquidity is not None:

        result = result[
            result["liquidity_flag"]
            == liquidity
        ]

    # =====================================================
    # SORT
    # =====================================================

    result = result.sort_values(
        "bagger_score",
        ascending=False,
    )

    return result.reset_index(
        drop=True
    )


def print_screener_result(
    result,
):

    print("\n" + "=" * 100)
    print("BAGGER RADAR — EXPLAINABLE SCREENER")
    print("=" * 100)

    print(
        f"Result count: {len(result)}"
    )

    if result.empty:

        print(
            "\nTidak ada saham yang memenuhi filter."
        )

        return

    columns = [
        "symbol",
        "bagger_score",
        "growth_score",
        "quality_score",
        "valuation_score",
        "momentum_score",
        "risk_score",
        "evidence_level",
        "liquidity_flag",
    ]

    display = result[
        columns
    ].copy()

    numeric_columns = [
        "bagger_score",
        "growth_score",
        "quality_score",
        "valuation_score",
        "momentum_score",
        "risk_score",
    ]

    display[
        numeric_columns
    ] = display[
        numeric_columns
    ].round(2)

    print(
        display.to_string(
            index=False
        )
    )

    print("=" * 100)


def main():

    df = load_data()

    # =====================================================
    # DEMO SCREENER
    #
    # Baseline:
    # - Bagger >= 65
    # - Evidence HIGH
    # =====================================================

    result = screen_stocks(
        df,
        min_bagger_score=65,
        min_evidence="HIGH",
    )

    print_screener_result(
        result
    )


if __name__ == "__main__":
    main()