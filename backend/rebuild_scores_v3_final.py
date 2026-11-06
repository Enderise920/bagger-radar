"""Rebuild RowletAI scoring outputs with the audited V3 engine.

Default behavior is NON-DESTRUCTIVE: outputs are written to data/scoring_v3.
The existing canonical scoring files are never overwritten unless --overwrite
is explicitly supplied after review.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve()
if str(HERE.parent) not in sys.path:
    sys.path.insert(0,str(HERE.parent))
from scoring_engine_v3_final import score_universe


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def as_df(payload):
    if isinstance(payload, dict):
        return pd.DataFrame(payload.values())
    return pd.DataFrame(payload)


def clean_records(df: pd.DataFrame):
    return json.loads(df.to_json(orient="records", force_ascii=False))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",default=None,help="Project data directory")
    ap.add_argument("--out",default=None,help="Output directory; defaults to <data>/scoring_v3")
    ap.add_argument("--overwrite",action="store_true",help="Replace canonical bagger_scores.json after explicit review")
    args=ap.parse_args()

    # Supports both project layout C:\\Gio-AI-Team and this standalone audit folder.
    data=Path(args.data) if args.data else HERE.parent / "gio_data"
    if not data.exists():
        data=HERE.parent.parent / "data"
    out=Path(args.out) if args.out else data / "scoring_v3"
    out.mkdir(parents=True,exist_ok=True)

    fund=as_df(load_json(data/"fundamentals.json"))
    mom=as_df(load_json(data/"momentum_scores.json"))
    risk=as_df(load_json(data/"risk_metrics.json"))
    profiles=as_df(load_json(data/"company_profiles.json")) if (data/"company_profiles.json").exists() else pd.DataFrame()

    scores=score_universe(fund,mom,risk,profiles)
    if scores.empty:
        raise SystemExit("No scores produced.")
    scores=scores.sort_values("bagger_score",ascending=False,na_position="last")

    (out/"bagger_scores_v3.json").write_text(json.dumps(clean_records(scores),ensure_ascii=False,indent=2),encoding="utf-8")
    summary={
        "companies":int(len(scores)),
        "bagger_scored":int(scores.bagger_score.notna().sum()),
        "mean_bagger":float(scores.bagger_score.mean()) if scores.bagger_score.notna().any() else None,
        "evidence_high":int((scores.evidence_level=="HIGH").sum()),
        "evidence_medium":int((scores.evidence_level=="MEDIUM").sum()),
        "evidence_low":int((scores.evidence_level=="LOW").sum()),
        "evidence_insufficient":int((scores.evidence_level=="INSUFFICIENT").sum()),
        "dividend_scored":int(scores.dividend_score.notna().sum()),
    }
    (out/"scoring_v3_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2))

    if args.overwrite:
        canonical=data/"bagger_scores.json"
        backup=canonical.with_suffix(".pre_v3_audit_backup.json")
        if canonical.exists(): canonical.replace(backup)
        canonical.write_text(json.dumps(clean_records(scores),ensure_ascii=False,indent=2),encoding="utf-8")
        print(f"Canonical bagger_scores.json replaced; backup: {backup}")

if __name__=="__main__": main()
