"""Rebuild RowletAI scoring outputs with Scoring Engine V2.

Usage from the project root:
    python app/rebuild_scores_v2.py

The script writes:
    data/bagger_scores_v2.json
    data/scoring_validation_v2.csv
It does NOT overwrite the existing bagger_scores.json.
"""
from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

try:
    from scoring_engine_v2 import run_engine, validation_report
except ImportError:
    from app.scoring_engine_v2 import run_engine, validation_report

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"

def load(name):
    with open(DATA / name, "r", encoding="utf-8") as f:
        return json.load(f)

def ddf(x):
    if isinstance(x, dict):
        return pd.DataFrame([{**(v if isinstance(v, dict) else {}), "symbol": k} for k, v in x.items()])
    return pd.DataFrame(x)

def clean(x):
    x=x.copy()
    x.columns=[str(c) for c in x.columns]
    if "symbol" in x:
        x["symbol"]=x["symbol"].astype(str).str.upper().str.strip()
    return x.loc[:,~x.columns.duplicated()]

def load_reports():
    path=DATA / "journal_report_cache.json"
    if not path.exists():
        return {}
    try:
        payload=json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out={}
    if isinstance(payload,dict):
        for sym,item in payload.items():
            if isinstance(item,dict) and isinstance(item.get("report"),dict):
                out[str(sym).upper()]=item["report"]
    return out

def main():
    old=clean(pd.DataFrame(load("bagger_scores.json")))
    fund=clean(pd.DataFrame(load("fundamentals.json")))
    mom=clean(ddf(load("momentum_scores.json")))
    risk=clean(ddf(load("risk_metrics.json")))
    profiles=clean(pd.DataFrame(load("company_profiles.json")))
    reports=load_reports()

    new=run_engine(fund,mom,risk,profiles,reports=reports,existing=old)

    output_cols=[
        "symbol","growth_score","quality_score","valuation_score","momentum_score",
        "risk_score","risk_strength","bagger_score","available_dimensions",
        "evidence_level","composite_signal","risk_evidence","liquidity_flag",
        "valuation_evidence","valuation_relative_to","growth_evidence",
        "momentum_evidence","revenue_cagr_multi","earnings_cagr_multi","eps_cagr_multi",
    ]
    result=new[[c for c in output_cols if c in new.columns]].copy()
    result=result.where(pd.notna(result),None)
    records=result.to_dict("records")
    (DATA/"bagger_scores_v2.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")

    audit=validation_report(old,new)
    audit.to_csv(DATA/"scoring_validation_v2.csv",index=False)

    print(f"Scored companies: {len(result):,}")
    print(f"Full 5D Bagger scores: {int(result.bagger_score.notna().sum()):,}")
    print(f"Reports used: {len(reports):,}")
    print(f"Wrote: {DATA/'bagger_scores_v2.json'}")
    print(f"Wrote: {DATA/'scoring_validation_v2.csv'}")
    print("Existing data/bagger_scores.json was NOT overwritten.")

if __name__ == "__main__":
    main()
