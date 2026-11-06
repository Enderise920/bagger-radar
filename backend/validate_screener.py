import json
from pathlib import Path

import pandas as pd

from screener import load_data, screen_stocks


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def check(condition, message):
    if condition:
        print(f"[PASS] {message}")
    else:
        print(f"[FAIL] {message}")
        raise AssertionError(message)


def main():
    df = load_data()

    print("=" * 100)
    print("BAGGER RADAR — SCREENER VALIDATION")
    print("=" * 100)

    # ------------------------------------------------------------------
    # 1. Basic input validation
    # ------------------------------------------------------------------

    required_columns = [
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

    for column in required_columns:
        check(
            column in df.columns,
            f"Required column exists: {column}"
        )

    check(
        df["symbol"].notna().all(),
        "No empty symbols"
    )

    check(
        df["symbol"].duplicated().sum() == 0,
        "No duplicate symbols"
    )

    # ------------------------------------------------------------------
    # 2. Baseline screener
    # ------------------------------------------------------------------

    result = screen_stocks(
        df,
        min_bagger_score=65,
        min_evidence="HIGH",
    )

    check(
        len(result) == 34,
        "Baseline filter returns exactly 34 stocks"
    )

    # ------------------------------------------------------------------
    # 3. Every result must satisfy all filters
    # ------------------------------------------------------------------

    check(
        (result["bagger_score"] >= 65).all(),
        "All results have Bagger Score >= 65"
    )

    check(
        (result["evidence_level"] == "HIGH").all(),
        "All results have HIGH evidence"
    )

    check(
        result["bagger_score"].notna().all(),
        "No result has missing Bagger Score"
    )

    # ------------------------------------------------------------------
    # 4. Bagger Score ordering
    # ------------------------------------------------------------------

    check(
        result["bagger_score"].is_monotonic_decreasing,
        "Results are sorted by Bagger Score descending"
    )

    # ------------------------------------------------------------------
    # 5. Evidence filter tests
    # ------------------------------------------------------------------

    high = screen_stocks(
        df,
        min_evidence="HIGH",
    )

    medium = screen_stocks(
        df,
        min_evidence="MEDIUM",
    )

    low = screen_stocks(
        df,
        min_evidence="LOW",
    )

    check(
        len(high) <= len(medium),
        "HIGH evidence is a subset of MEDIUM-or-better universe"
    )

    check(
        len(medium) <= len(low),
        "MEDIUM evidence is a subset of LOW-or-better universe"
    )

    # ------------------------------------------------------------------
    # 6. Dimension filter tests
    # ------------------------------------------------------------------

    growth_70 = screen_stocks(
        df,
        min_growth=70,
    )

    check(
        (growth_70["growth_score"] >= 70).all(),
        "Growth filter works correctly"
    )

    quality_70 = screen_stocks(
        df,
        min_quality=70,
    )

    check(
        (quality_70["quality_score"] >= 70).all(),
        "Quality filter works correctly"
    )

    valuation_70 = screen_stocks(
        df,
        min_valuation=70,
    )

    check(
        (valuation_70["valuation_score"] >= 70).all(),
        "Valuation filter works correctly"
    )

    momentum_70 = screen_stocks(
        df,
        min_momentum=70,
    )

    check(
        (momentum_70["momentum_score"] >= 70).all(),
        "Momentum filter works correctly"
    )

    # ------------------------------------------------------------------
    # 7. Risk filter
    # ------------------------------------------------------------------

    risk_50 = screen_stocks(
        df,
        max_risk=50,
    )

    check(
        (risk_50["risk_score"] <= 50).all(),
        "Risk filter works correctly"
    )

    # ------------------------------------------------------------------
    # 8. Liquidity filter
    # ------------------------------------------------------------------

    active = screen_stocks(
        df,
        liquidity="ACTIVE",
    )

    check(
        (active["liquidity_flag"] == "ACTIVE").all(),
        "Liquidity filter works correctly"
    )

    # ------------------------------------------------------------------
    # 9. Combined filter
    # ------------------------------------------------------------------

    combined = screen_stocks(
        df,
        min_bagger_score=65,
        min_evidence="HIGH",
        min_growth=70,
        min_quality=60,
        min_valuation=60,
        min_momentum=50,
        max_risk=60,
        liquidity="ACTIVE",
    )

    check(
        (
            (combined["bagger_score"] >= 65)
            & (combined["growth_score"] >= 70)
            & (combined["quality_score"] >= 60)
            & (combined["valuation_score"] >= 60)
            & (combined["momentum_score"] >= 50)
            & (combined["risk_score"] <= 60)
            & (combined["evidence_level"] == "HIGH")
            & (combined["liquidity_flag"] == "ACTIVE")
        ).all(),
        "Combined filters work correctly"
    )

    # ------------------------------------------------------------------
    # 10. Missing-data protection
    # ------------------------------------------------------------------

    incomplete = df[df["bagger_score"].isna()]

    check(
        len(incomplete) > 0,
        "Incomplete stocks exist in source dataset"
    )

    incomplete_result = screen_stocks(
        df,
        min_bagger_score=0,
    )

    check(
        incomplete_result["bagger_score"].notna().all(),
        "Stocks without Bagger Score are excluded"
    )

    # ------------------------------------------------------------------
    # 11. Impossible filter should return zero
    # ------------------------------------------------------------------

    impossible = screen_stocks(
        df,
        min_bagger_score=101,
    )

    check(
        len(impossible) == 0,
        "Impossible Bagger Score filter returns zero results"
    )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("SCREENER VALIDATION SUMMARY")
    print("=" * 100)

    print(f"Universe:                 {len(df)}")
    print(f"Bagger Score >= 65:      {len(result)}")
    print(f"HIGH Evidence:           {len(high)}")
    print(f"Growth >= 70:             {len(growth_70)}")
    print(f"Quality >= 70:            {len(quality_70)}")
    print(f"Valuation >= 70:          {len(valuation_70)}")
    print(f"Momentum >= 70:            {len(momentum_70)}")
    print(f"Risk <= 50:                {len(risk_50)}")
    print(f"Liquidity ACTIVE:          {len(active)}")
    print(f"Combined filter:           {len(combined)}")

    print()
    print("=" * 100)
    print("ALL SCREENER VALIDATIONS PASSED")
    print("=" * 100)


if __name__ == "__main__":
    main()