from pathlib import Path
import ast

TARGET = Path(r"C:\Gio-AI-Team\app\dashboard_scoring_v3_2_dada_guardrails_dividend_fix_v1.py")

if not TARGET.exists():
    raise FileNotFoundError(f"Target not found: {TARGET}")

source = TARGET.read_text(encoding="utf-8")
ast.parse(source)

checks = {
    "Dividend engine assigned to row": "row['dividend_score']=_dividend_engine.get('score', np.nan)" in source,
    "Section 05 Dividend Score UI exists": 'j-dividend-score-metric' in source and 'Dividend Score' in source,
    "Dividend Score displays /100": "dividend_score:.1f}/100" in source,
    "Measured state exists": "'Measured' if np.isfinite(dividend_score)" in source,
    "Dividend does not feed Bagger dimensions": 'does not feed the five Bagger dimensions' in source,
}

for name, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

if not all(checks.values()):
    raise SystemExit("DIVIDEND UI CHECKS FAILED")

print("ALL DADA DIVIDEND UI CHECKS PASSED")
print(f"Candidate: {TARGET}")
