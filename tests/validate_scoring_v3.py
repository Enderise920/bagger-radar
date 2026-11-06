"""RowletAI Scoring V3 representative-company validation.

Usage (from project root):
    python tests\\validate_scoring_v3.py

The script reads the local data/ folder, recalculates V3 scores, selects a
small deterministic set of representative cases, and writes:
    data/scoring_v3/validation_representative.csv
    data/scoring_v3/validation_representative.md

It does not modify dashboard.py or any source data file.
"""
from __future__ import annotations

import json
import math
import sys
import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Allow the script to be run from tests/ while the engine lives in backend/.
DEFAULT_ROOT = Path(__file__).resolve().parents[1]

ROOT = DEFAULT_ROOT
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from scoring_engine_v3_final import (  # noqa: E402
    BAGGER_WEIGHTS,
    infer_liquidity_state,
    score_universe,
)

DATA = ROOT / "data"
OUT = DATA / "scoring_v3"


def load_table(name: str) -> pd.DataFrame:
    path = DATA / name
    with path.open("r", encoding="utf-8") as fh:
        obj = json.load(fh)
    if isinstance(obj, list):
        return pd.DataFrame(obj)
    if isinstance(obj, dict):
        rows = []
        for symbol, value in obj.items():
            row = dict(value) if isinstance(value, dict) else {"value": value}
            row.setdefault("symbol", symbol)
            rows.append(row)
        return pd.DataFrame(rows)
    raise ValueError(f"Unsupported JSON structure: {name}")


def n(x: Any) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else np.nan
    except (TypeError, ValueError):
        return np.nan


def fmt(x: Any) -> str:
    v = n(x)
    return "N/A" if not np.isfinite(v) else f"{v:.2f}"


def choose_first(df: pd.DataFrame, mask: pd.Series, sort_by: str | None = None, ascending: bool = False) -> str | None:
    q = df.loc[mask].copy()
    if q.empty:
        return None
    if sort_by and sort_by in q.columns:
        q[sort_by] = pd.to_numeric(q[sort_by], errors="coerce")
        q = q.sort_values(sort_by, ascending=ascending, na_position="last")
    return str(q.iloc[0]["symbol"])


def add_reason(row: pd.Series, case: str) -> str:
    if case == "AADI_JK":
        return "Fixed Company Journal regression test case; static universe currently lacks momentum/risk evidence."
    if case == "ACTIVE_LIQUID":
        return "Representative active-trading company with complete five-dimension evidence."
    if case == "STALE_OR_LOW_ACTIVITY":
        return "Checks that flat/stale price series cannot receive an artificially strong Risk Strength."
    if case == "NEGATIVE_PE":
        return "Checks that negative TTM P/E is excluded from valuation and does not become a valid PE signal."
    if case == "PB_ONLY":
        return "Checks valuation fallback using positive P/B when usable PE evidence is absent."
    if case == "GROWTH_VS_RISK":
        return "Checks that strong growth does not overwhelm weak risk evidence in the composite."
    if case == "HIGH_YIELD":
        return "Checks the >8% dividend-yield reliability gate."
    if case == "INCOMPLETE":
        return "Checks that missing dimensions remain missing and do not produce a fabricated Bagger Score."
    return "Representative validation case."


def main() -> int:
    global ROOT, BACKEND, DATA, OUT
    parser = argparse.ArgumentParser(description="Validate RowletAI Scoring V3 on a project data directory.")
    parser.add_argument("--project-root", type=Path, default=DEFAULT_ROOT, help="Project root containing data/ and backend/ (default: repository root).")
    args = parser.parse_args()
    ROOT = args.project_root.resolve()
    BACKEND = ROOT / "backend"
    DATA = ROOT / "data"
    OUT = DATA / "scoring_v3"
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    OUT.mkdir(parents=True, exist_ok=True)

    fundamentals = load_table("fundamentals.json")
    momentum = load_table("momentum_scores.json")
    risk = load_table("risk_metrics.json")
    profiles = load_table("company_profiles.json")

    scores = score_universe(fundamentals, momentum, risk, profiles)

    raw = fundamentals.copy()
    raw = raw.merge(momentum, on="symbol", how="left", suffixes=("", "_momentum"))
    raw = raw.merge(risk, on="symbol", how="left", suffixes=("", "_risk"))
    raw = raw.merge(profiles[[c for c in profiles.columns if c in {"symbol", "sector", "industry", "company_name"}]], on="symbol", how="left", suffixes=("", "_profile"))
    raw["liquidity_state_inferred"] = raw.apply(infer_liquidity_state, axis=1)

    # Merge score output with explicit suffix to avoid hiding raw momentum fields.
    all_df = raw.merge(scores, on="symbol", how="left", suffixes=("", "_score"))
    all_df["company_name"] = all_df.get("company_name", all_df["symbol"])
    if "company_name_profile" in all_df.columns:
        all_df["company_name"] = all_df["company_name"].fillna(all_df["company_name_profile"])

    # Normalize numeric fields used by selectors.
    numeric_cols = [
        "market_cap", "pe_ttm", "forward_pe", "pb_mrq", "yield_ttm",
        "yoy_quarter_revenue_growth", "yoy_quarter_earnings_growth",
        "growth_score", "quality_score", "valuation_score", "momentum_score_score",
        "risk_strength", "dividend_score", "bagger_score", "zero_return_ratio_20d",
        "unique_price_ratio_20d",
    ]
    for col in numeric_cols:
        if col in all_df.columns:
            all_df[col] = pd.to_numeric(all_df[col], errors="coerce")

    # Deterministic selection rules. Duplicates are removed in priority order.
    selected: list[tuple[str, str]] = []
    used: set[str] = set()

    def add(case: str, symbol: str | None) -> None:
        if symbol and symbol not in used:
            selected.append((case, symbol))
            used.add(symbol)

    # 1. AADI is mandatory for the Company Journal regression path.
    add("AADI_JK", "AADI.JK" if "AADI.JK" in set(all_df.symbol.astype(str)) else None)

    # 2. Active/liquid and complete.
    complete = all_df[all_df["bagger_score"].notna()].copy()
    add(
        "ACTIVE_LIQUID",
        choose_first(complete, complete["liquidity_state_inferred"].eq("ACTIVE"), "market_cap"),
    )

    # 3. Stale / low activity. Prefer the most stale zero-return profile.
    stale_mask = all_df["liquidity_state_inferred"].isin(["STALE", "LOW_ACTIVITY"])
    add("STALE_OR_LOW_ACTIVITY", choose_first(all_df, stale_mask, "zero_return_ratio_20d"))

    # 4. Negative TTM P/E with a usable valuation result.
    neg_pe = all_df["pe_ttm"].lt(0) & all_df["valuation_score"].notna()
    add("NEGATIVE_PE", choose_first(all_df, neg_pe, "market_cap"))

    # 5. P/B-only: no positive forward/TTM PE but positive P/B.
    no_pe = ((all_df["forward_pe"] <= 0) | all_df["forward_pe"].isna()) & ((all_df["pe_ttm"] <= 0) | all_df["pe_ttm"].isna())
    pb_only = no_pe & all_df["pb_mrq"].gt(0) & all_df["valuation_score"].notna()
    add("PB_ONLY", choose_first(all_df, pb_only, "market_cap"))

    # 6. Growth-vs-risk conflict: high growth with weak risk, if available.
    conflict = all_df["growth_score"].ge(75) & all_df["risk_strength"].le(35) & all_df["bagger_score"].notna()
    if conflict.any():
        q = all_df.loc[conflict].copy()
        q["gap"] = q["growth_score"] - q["risk_strength"]
        add("GROWTH_VS_RISK", choose_first(q, pd.Series(True, index=q.index), "gap"))
    else:
        # Fallback: strongest growth among complete names with below-median risk.
        median_risk = all_df["risk_strength"].median(skipna=True)
        conflict2 = all_df["growth_score"].ge(70) & all_df["risk_strength"].le(median_risk) & all_df["bagger_score"].notna()
        add("GROWTH_VS_RISK", choose_first(all_df, conflict2, "growth_score"))

    # 7. High yield >8%.
    high_yield = all_df["yield_ttm"].gt(0.08) & all_df["dividend_score"].notna()
    add("HIGH_YIELD", choose_first(all_df, high_yield, "yield_ttm"))

    # 8. Incomplete: at least one of the five Bagger dimensions missing.
    incomplete = all_df["bagger_score"].isna()
    add("INCOMPLETE", choose_first(all_df, incomplete, "market_cap"))

    rows = []
    checks = []
    for case, symbol in selected:
        r = all_df.loc[all_df.symbol.astype(str).eq(symbol)].iloc[0]
        bagger = n(r.get("bagger_score"))
        growth = n(r.get("growth_score"))
        quality = n(r.get("quality_score"))
        valuation = n(r.get("valuation_score"))
        momentum_v = n(r.get("momentum_score_score"))
        risk_v = n(r.get("risk_strength"))
        expected_bagger = np.nan
        if all(np.isfinite(v) for v in [growth, quality, valuation, momentum_v, risk_v]):
            expected_bagger = sum([
                growth * BAGGER_WEIGHTS["growth_score"],
                quality * BAGGER_WEIGHTS["quality_score"],
                valuation * BAGGER_WEIGHTS["valuation_score"],
                momentum_v * BAGGER_WEIGHTS["momentum_score"],
                risk_v * BAGGER_WEIGHTS["risk_strength"],
            ])
        valuation_relative = str(r.get("valuation_relative_to", "NONE"))
        state = str(r.get("liquidity_state_inferred", ""))
        evidence = str(r.get("evidence_level", ""))

        passed = True
        check_notes = []
        if case == "STALE_OR_LOW_ACTIVITY":
            passed = passed and (not np.isfinite(risk_v) or risk_v <= 65)
            check_notes.append(f"Risk Strength={fmt(risk_v)}; state={state}")
        elif case == "NEGATIVE_PE":
            # Negative TTM PE must not be used as the valuation PE signal.
            passed = passed and ("P/E TTM" not in valuation_relative)
            check_notes.append(f"PE TTM={fmt(r.get('pe_ttm'))}; valuation basis={valuation_relative}")
        elif case == "PB_ONLY":
            passed = passed and ("P/B" in valuation_relative)
            check_notes.append(f"valuation basis={valuation_relative}")
        elif case == "GROWTH_VS_RISK":
            passed = passed and np.isfinite(bagger) and np.isfinite(risk_v) and risk_v <= 35
            check_notes.append(f"Growth={fmt(growth)} vs Risk Strength={fmt(risk_v)}; Bagger={fmt(bagger)}")
        elif case == "HIGH_YIELD":
            payout = n(r.get("payout_ratio"))
            if not np.isfinite(payout):
                passed = passed and (not np.isfinite(n(r.get("yield_ttm"))) or n(r.get("yield_ttm")) <= 0.08 or n(r.get("dividend_score")) <= 75)
                check_notes.append(f"Yield={fmt(n(r.get('yield_ttm')))}; payout unavailable; dividend cap check")
            elif payout > 1.0:
                passed = passed and (n(r.get("dividend_score")) <= 45)
                check_notes.append(f"Yield={fmt(n(r.get('yield_ttm')))}; payout={fmt(payout)}; stressed-yield cap check")
            else:
                check_notes.append(f"Yield={fmt(n(r.get('yield_ttm')))}; payout={fmt(payout)}")
        elif case == "INCOMPLETE":
            passed = passed and not np.isfinite(bagger) and evidence == "INSUFFICIENT"
            check_notes.append(f"Bagger={fmt(bagger)}; evidence={evidence}")
        elif case == "AADI_JK":
            passed = passed and (not np.isfinite(bagger) or int(r.get("available_dimensions", 0) or 0) < 5)
            check_notes.append(f"Bagger={fmt(bagger)}; available dimensions={r.get('available_dimensions')}")
        elif case == "ACTIVE_LIQUID":
            passed = passed and state == "ACTIVE"
            check_notes.append(f"state={state}; Bagger={fmt(bagger)}")

        if np.isfinite(expected_bagger) and np.isfinite(bagger):
            formula_ok = abs(expected_bagger - bagger) < 1e-8
            passed = passed and formula_ok
            check_notes.append(f"5-weight formula delta={abs(expected_bagger-bagger):.8f}")
        elif np.isfinite(bagger):
            passed = False
            check_notes.append("Bagger exists without all five dimensions — investigate")

        rows.append({
            "case": case,
            "symbol": symbol,
            "company_name": r.get("company_name", symbol),
            "liquidity_state": state,
            "growth": growth,
            "quality": quality,
            "valuation": valuation,
            "momentum": momentum_v,
            "risk_strength": risk_v,
            "dividend": n(r.get("dividend_score")),
            "bagger": bagger,
            "evidence": evidence,
            "composite_signal": r.get("composite_signal", ""),
            "valuation_basis": valuation_relative,
            "pe_ttm": n(r.get("pe_ttm")),
            "forward_pe": n(r.get("forward_pe")),
            "pb_mrq": n(r.get("pb_mrq")),
            "yield_ttm": n(r.get("yield_ttm")),
            "zero_return_ratio_20d": n(r.get("zero_return_ratio_20d")),
            "unique_price_ratio_20d": n(r.get("unique_price_ratio_20d")),
            "validation_pass": passed,
            "validation_notes": "; ".join(check_notes),
            "reason": add_reason(r, case),
        })
        checks.append(passed)

    result = pd.DataFrame(rows)
    csv_path = OUT / "validation_representative.csv"
    md_path = OUT / "validation_representative.md"
    result.to_csv(csv_path, index=False, encoding="utf-8-sig")

    pass_count = int(sum(checks))
    total = len(checks)
    lines = [
        "# RowletAI Scoring V3 — Representative Validation",
        "",
        f"Generated from `{DATA}`. Companies scored with `scoring_engine_v3_final.py`.",
        "This validation does not modify `dashboard.py` or source JSON files.",
        "",
        f"**Cases selected:** {total}  ",
        f"**Validation checks passed:** {pass_count}/{total}  ",
        f"**Overall status:** {'PASS' if pass_count == total else 'REVIEW REQUIRED'}",
        "",
        "## Representative cases",
        "",
    ]
    if not result.empty:
        display_cols = ["case", "symbol", "liquidity_state", "growth", "quality", "valuation", "momentum", "risk_strength", "dividend", "bagger", "evidence", "validation_pass"]
        lines.append(result[display_cols].to_markdown(index=False))
        lines += ["", "## Interpretation", ""]
        for _, rr in result.iterrows():
            status = "PASS" if rr.validation_pass else "REVIEW"
            lines.append(f"- **{rr['case']} / {rr['symbol']} — {status}:** {rr['reason']} {rr['validation_notes']}")

    lines += [
        "",
        "## What this test does not prove",
        "",
        "1. It does not prove live Sectors API freshness.",
        "2. It does not prove the Streamlit Company Journal renders every field correctly.",
        "3. It does not prove Market Intelligence STEP 1/2 UI behavior.",
        "4. Those are the next integration-validation stages before merging V3 into MASTER.",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Representative validation: {pass_count}/{total} checks passed")
    print(f"CSV: {csv_path}")
    print(f"Report: {md_path}")
    return 0 if pass_count == total else 2


if __name__ == "__main__":
    raise SystemExit(main())
