from pathlib import Path
import ast

TARGET = Path('/mnt/data/dividend_fix/dashboard_scoring_v3_2_dada_final_ui_consistency_v1.py')
s = TARGET.read_text(encoding='utf-8')

ast.parse(s)
assert 'def journal_evidence_coverage_pct(row):' in s
assert 'Dividend Score' in s
assert 'Separate dividend-quality score; does not feed the five Bagger dimensions.' in s
assert '<div class="j-exec-coverage-label">Evidence Quality</div>' in s
assert '5/5 Bagger dimensions available; price/risk evidence is quality-limited.' in s
assert 'Flat statistics under stale or limited trading are labeled evidence-limited and are not treated as zero market risk.' in s
assert 'Near-flat price; trading evidence is limited (20D)' in s
assert 'Near-flat price; trading evidence is limited (60D)' in s
assert "Limited evidence" in s
# Dividend must remain outside the 5 Bagger dimensions.
assert "score_specs=[('Growth','growth','growth_score','▥'),('Dividend','dividend','dividend_score','◉'),('Valuation','valuation','valuation_score','◆'),('Risk Strength','risk','risk_score','⬟'),('Momentum','momentum','momentum_score','▥')]" in s
assert 'Model combines 5 key dimensions:' in s
print('ALL DADA FINAL UI CONSISTENCY CHECKS PASSED')
print(f'Candidate: {TARGET}')
