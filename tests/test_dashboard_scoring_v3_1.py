from pathlib import Path

# Candidate lives in app/, while this test lives in tests/.
P = Path(__file__).resolve().parents[1] / 'app' / 'dashboard_scoring_v3_1_candidate.py'
if not P.exists():
    raise FileNotFoundError(f'Candidate dashboard not found: {P}')
s = P.read_text(encoding='utf-8')

checks = {
    'unified_research_view_function': 'def journal_research_view(row):' in s,
    'research_view_uses_v3_signal': "if signal == 'STRONG_COMPOSITE':" in s and "if signal == 'BALANCED_COMPOSITE':" in s,
    'executive_uses_unified_view': 'research_label,research_class=journal_research_view(row)' in s,
    'section09_uses_unified_view': 'overall,_overall_class=journal_research_view(row)' in s,
    'quality_card_present': "('Quality','quality','quality_score','●')" in s,
    'dividend_not_in_model_card_specs': "score_specs=[('Growth','growth','growth_score','▥'),('Quality','quality','quality_score','●'),('Valuation','valuation','valuation_score','◆'),('Risk Strength','risk','risk_score','⬟'),('Momentum','momentum','momentum_score','▥')]" in s,
    'quality_css_present': '.j08-card.quality{' in s,
    'scoring_coverage_label': 'SCORING EVIDENCE COVERAGE' in s and 'Complete Scoring Coverage' in s,
    'forecast_label_distinction': 'Compounded forecast levels' in s and 'Section 04 applies separate Bear/Base/Bull scenario bands.' in s,
}

failed = [name for name, ok in checks.items() if not ok]
print(f'Dashboard V3.1 checks: {len(checks)-len(failed)}/{len(checks)} passed')
if failed:
    print('FAILED:', ', '.join(failed))
    raise SystemExit(1)
print('ALL DASHBOARD V3.1 CHECKS PASSED')
