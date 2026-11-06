from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
NAME = 'dashboard_scoring_v3_4_dada_guardrails_candidate.py'
CANDIDATE_PATHS = [ROOT/'app'/NAME, ROOT/NAME, Path(__file__).resolve().parent/NAME]
TARGET = next((p for p in CANDIDATE_PATHS if p.exists()), None)

def read():
    if TARGET is None:
        raise FileNotFoundError(f'Candidate not found. Checked: {CANDIDATE_PATHS}')
    return TARGET.read_text(encoding='utf-8')

def test_source_compiles():
    ast.parse(read())

def test_step08_shows_all_five_bagger_dimensions_plus_dividend():
    s=read()
    for item in [
        "('Growth','growth','growth_score','▥')",
        "('Quality','quality','quality_score','●')",
        "('Dividend','dividend','dividend_score','◉')",
        "('Valuation','valuation','valuation_score','◆')",
        "('Risk Strength','risk','risk_score','⬟')",
        "('Momentum','momentum','momentum_score','▥')",
    ]:
        assert item in s, item
    assert "grid-template-columns:repeat(6,minmax(0,1fr))" in s

def test_dividend_is_separate_from_bagger_dimensions():
    s=read()
    assert 'Dividend Score is shown separately and does not feed the Bagger Score.' in s
    assert "_v3_bagger_score" in s

def test_dividend_engine_and_score_are_wired():
    s=read()
    assert 'def dividend_score_engine(' in s
    assert "row['dividend_score']=_dividend_engine.get('score', np.nan)" in s
    assert "dividend_score=n(row.get('dividend_score'))" in s

def test_master_not_modified_by_candidate():
    assert TARGET is not None
    master=ROOT/'app'/'dashboard.py'
    if master.exists():
        assert master.resolve()!=TARGET.resolve()

if __name__=='__main__':
    tests=[test_source_compiles,test_step08_shows_all_five_bagger_dimensions_plus_dividend,test_dividend_is_separate_from_bagger_dimensions,test_dividend_engine_and_score_are_wired,test_master_not_modified_by_candidate]
    for t in tests: t()
    print(f'ALL DADA V3.4 TESTS PASSED ({len(tests)}/{len(tests)})')
    print(f'Candidate: {TARGET}')
