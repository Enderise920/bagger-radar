import json
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

RISK_SCORES_FILE = DATA_DIR / "risk_scores.json"


def fail(message):
    print(f"FAIL: {message}")
    return False


def main():

    print("=" * 70)
    print("MODULE 7.5 — RISK EVIDENCE VALIDATION")
    print("=" * 70)

    # =========================================================
    # LOAD PRODUCTION OUTPUT
    # =========================================================

    with open(RISK_SCORES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("FAIL: risk_scores.json bukan list of records.")
        return

    df = pd.DataFrame(data)

    print(f"Production records: {len(df)}")

    all_passed = True

    # =========================================================
    # TEST 1 — RECORD COUNT
    # =========================================================

    if len(df) == 0:
        all_passed = fail("risk_scores.json kosong.")
    else:
        print("PASS: Production output tidak kosong.")

    # =========================================================
    # TEST 2 — REQUIRED COLUMNS
    # =========================================================

    required_columns = [
        "symbol",
        "volatility_20d",
        "volatility_60d",
        "max_drawdown_60d",
        "max_daily_loss_20d",
        "volatility_score",
        "drawdown_score",
        "extreme_loss_score",
        "risk_score_raw",
        "liquidity_modifier",
        "risk_score",
        "liquidity_flag",
        "risk_evidence",
        "risk_interpretation",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        all_passed = fail(
            f"Missing columns: {missing_columns}"
        )
    else:
        print("PASS: Semua required columns tersedia.")

    # =========================================================
    # TEST 3 — SYMBOL QUALITY
    # =========================================================

    missing_symbols = df["symbol"].isna().sum()

    duplicate_symbols = df["symbol"].duplicated().sum()

    if missing_symbols > 0:
        all_passed = fail(
            f"{missing_symbols} records memiliki symbol kosong."
        )
    else:
        print("PASS: Tidak ada symbol kosong.")

    if duplicate_symbols > 0:
        all_passed = fail(
            f"{duplicate_symbols} duplicate symbols ditemukan."
        )
    else:
        print("PASS: Tidak ada duplicate symbol.")

    # =========================================================
    # TEST 4 — RISK SCORE RANGE
    # =========================================================

    numeric_risk = pd.to_numeric(
        df["risk_score"],
        errors="coerce",
    )

    invalid_low = (
        numeric_risk.dropna() < 0
    ).sum()

    invalid_high = (
        numeric_risk.dropna() > 100
    ).sum()

    if invalid_low > 0:
        all_passed = fail(
            f"{invalid_low} Risk Score < 0."
        )
    else:
        print("PASS: Tidak ada Risk Score < 0.")

    if invalid_high > 0:
        all_passed = fail(
            f"{invalid_high} Risk Score > 100."
        )
    else:
        print("PASS: Tidak ada Risk Score > 100.")

    # =========================================================
    # TEST 5 — NO_TRADING_EVIDENCE
    #
    # Must have:
    #   risk_score = NaN
    #   risk_score_raw = NaN
    #   risk_evidence = INSUFFICIENT
    # =========================================================

    no_evidence = (
        df["liquidity_flag"]
        == "NO_TRADING_EVIDENCE"
    )

    no_evidence_count = no_evidence.sum()

    no_evidence_numeric_score = (
        df.loc[
            no_evidence,
            "risk_score"
        ]
        .notna()
        .sum()
    )

    no_evidence_numeric_raw = (
        df.loc[
            no_evidence,
            "risk_score_raw"
        ]
        .notna()
        .sum()
    )

    no_evidence_wrong_evidence = (
        df.loc[
            no_evidence,
            "risk_evidence"
        ]
        != "INSUFFICIENT"
    ).sum()

    print(
        f"\nNO_TRADING_EVIDENCE records: "
        f"{no_evidence_count}"
    )

    if no_evidence_numeric_score == 0:
        print(
            "PASS: Semua NO_TRADING_EVIDENCE "
            "memiliki Risk Score = N/A."
        )
    else:
        all_passed = fail(
            f"{no_evidence_numeric_score} "
            "NO_TRADING_EVIDENCE memiliki "
            "Risk Score numerik."
        )

    if no_evidence_numeric_raw == 0:
        print(
            "PASS: Semua NO_TRADING_EVIDENCE "
            "memiliki raw score = N/A."
        )
    else:
        all_passed = fail(
            f"{no_evidence_numeric_raw} "
            "NO_TRADING_EVIDENCE memiliki "
            "raw Risk Score."
        )

    if no_evidence_wrong_evidence == 0:
        print(
            "PASS: Evidence NO_TRADING_EVIDENCE "
            "semuanya INSUFFICIENT."
        )
    else:
        all_passed = fail(
            f"{no_evidence_wrong_evidence} "
            "NO_TRADING_EVIDENCE memiliki "
            "evidence yang salah."
        )

    # =========================================================
    # TEST 6 — LIQUIDITY → EVIDENCE MAPPING
    # =========================================================

    expected_evidence = {
        "ACTIVE": "GOOD",
        "CAUTION": "MODERATE",
        "LOW_ACTIVITY": "LIMITED",
        "STALE": "INSUFFICIENT",
        "NO_TRADING_EVIDENCE": "INSUFFICIENT",
    }

    mapping_errors = []

    for liquidity_state, expected in expected_evidence.items():

        mask = (
            df["liquidity_flag"]
            == liquidity_state
        )

        actual_values = (
            df.loc[
                mask,
                "risk_evidence"
            ]
            .dropna()
            .unique()
            .tolist()
        )

        if len(actual_values) == 0:
            continue

        if actual_values != [expected] and not (
            len(actual_values) == 1
            and actual_values[0] == expected
        ):
            mapping_errors.append(
                f"{liquidity_state}: "
                f"expected {expected}, "
                f"got {actual_values}"
            )

    if mapping_errors:
        all_passed = fail(
            "Liquidity → Evidence mapping error: "
            + "; ".join(mapping_errors)
        )
    else:
        print(
            "\nPASS: Liquidity → Evidence mapping benar."
        )

    # =========================================================
    # TEST 7 — EXPECTED LIQUIDITY STATES
    # =========================================================

    expected_states = {
        "ACTIVE",
        "CAUTION",
        "LOW_ACTIVITY",
        "STALE",
        "NO_TRADING_EVIDENCE",
    }

    actual_states = set(
        df["liquidity_flag"]
        .dropna()
        .unique()
    )

    unexpected_states = (
        actual_states
        - expected_states
    )

    if unexpected_states:
        all_passed = fail(
            f"Unexpected liquidity states: "
            f"{unexpected_states}"
        )
    else:
        print(
            "PASS: Semua liquidity state valid."
        )

    # =========================================================
    # TEST 8 — COMPONENT SCORE RANGE
    # =========================================================

    component_columns = [
        "volatility_score",
        "drawdown_score",
        "extreme_loss_score",
        "risk_score_raw",
    ]

    component_errors = []

    for column in component_columns:

        values = pd.to_numeric(
            df[column],
            errors="coerce",
        ).dropna()

        invalid = (
            (values < 0)
            | (values > 100)
        ).sum()

        if invalid > 0:
            component_errors.append(
                f"{column}: {invalid} invalid values"
            )

    if component_errors:
        all_passed = fail(
            "Component score error: "
            + "; ".join(component_errors)
        )
    else:
        print(
            "PASS: Semua component score berada "
            "di range 0–100."
        )

    # =========================================================
    # TEST 9 — LIQUIDITY MODIFIER
    # =========================================================

    expected_modifiers = {
        "ACTIVE": 0,
        "CAUTION": 5,
        "LOW_ACTIVITY": 10,
        "STALE": 15,
        "NO_TRADING_EVIDENCE": 0,
    }

    modifier_errors = []

    for state, expected in expected_modifiers.items():

        mask = (
            df["liquidity_flag"]
            == state
        )

        values = (
            pd.to_numeric(
                df.loc[
                    mask,
                    "liquidity_modifier"
                ],
                errors="coerce",
            )
            .dropna()
            .unique()
        )

        if len(values) == 0:
            continue

        if not np.allclose(
            values,
            expected
        ):
            modifier_errors.append(
                f"{state}: expected {expected}, "
                f"got {values.tolist()}"
            )

    if modifier_errors:
        all_passed = fail(
            "Liquidity modifier error: "
            + "; ".join(modifier_errors)
        )
    else:
        print(
            "PASS: Liquidity modifier sesuai rule."
        )

    # =========================================================
    # TEST 10 — FINAL SCORE FORMULA
    #
    # For scored stocks:
    #
    # risk_score =
    # risk_score_raw + liquidity_modifier
    #
    # clipped at 100
    # =========================================================

    scored = df[
        df["risk_score"].notna()
    ].copy()

    expected_final_score = (
        scored["risk_score_raw"]
        + scored["liquidity_modifier"]
    ).clip(0, 100)

    formula_difference = (
        scored["risk_score"]
        - expected_final_score
    ).abs()

    formula_errors = (
        formula_difference > 0.00001
    ).sum()

    if formula_errors == 0:
        print(
            "PASS: Formula Final Risk Score benar."
        )
    else:
        all_passed = fail(
            f"{formula_errors} records "
            "tidak mengikuti formula Risk Score."
        )

    # =========================================================
    # TEST 11 — RISK INTERPRETATION
    # =========================================================

    insufficient_interpretation_errors = (
        df.loc[
            no_evidence,
            "risk_interpretation"
        ]
        != "INSUFFICIENT_EVIDENCE"
    ).sum()

    if insufficient_interpretation_errors == 0:
        print(
            "PASS: Interpretation "
            "NO_TRADING_EVIDENCE benar."
        )
    else:
        all_passed = fail(
            f"{insufficient_interpretation_errors} "
            "NO_TRADING_EVIDENCE memiliki "
            "interpretation salah."
        )

    # =========================================================
    # SUMMARY
    # =========================================================

    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    print(
        f"Total production records : {len(df)}"
    )

    print(
        f"Scored stocks            : "
        f"{df['risk_score'].notna().sum()}"
    )

    print(
        f"Insufficient evidence    : "
        f"{no_evidence_count}"
    )

    print(
        f"Risk score median        : "
        f"{numeric_risk.median():.2f}"
    )

    print(
        f"Risk score P90           : "
        f"{numeric_risk.quantile(0.90):.2f}"
    )

    print(
        f"Risk score max           : "
        f"{numeric_risk.max():.2f}"
    )

    print("\n" + "=" * 70)

    if all_passed:
        print(
            "MODULE 7.5 VALIDATION: PASS"
        )
        print(
            "MODULE 7.5 STATUS: COMPLETE"
        )
    else:
        print(
            "MODULE 7.5 VALIDATION: FAIL"
        )
        print(
            "MODULE 7.5 STATUS: NEEDS FIX"
        )

    print("=" * 70)


if __name__ == "__main__":
    main()