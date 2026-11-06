from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_NAMES = ["dashboard_scoring_v3_3_dada_guardrails_candidate.py"]
CANDIDATE_PATHS = [
    ROOT / "app" / CANDIDATE_NAMES[0],
    ROOT / CANDIDATE_NAMES[0],
    Path(__file__).resolve().parent / CANDIDATE_NAMES[0],
]
TARGET = next((p for p in CANDIDATE_PATHS if p.exists()), None)

def read():
    if TARGET is None:
        raise FileNotFoundError(f"Candidate not found. Checked: {CANDIDATE_PATHS}")
    return TARGET.read_text(encoding="utf-8")

def test_source_compiles():
    ast.parse(read())

def test_step08_uses_canonical_five_bagger_dimensions():
    src=read()
    assert "('Growth','growth','growth_score','▥')" in src
    assert "('Quality','quality','quality_score','●')" in src
    assert "('Valuation','valuation','valuation_score','◆')" in src
    assert "('Risk Strength','risk','risk_score','⬟')" in src
    assert "('Momentum','momentum','momentum_score','▥')" in src
    assert "score_specs=[('Growth','growth','growth_score','▥'),('Dividend'" not in src

def test_quality_score_is_wired_to_card():
    src=read()
    assert "quality_score=n(row.get('quality_score'))" in src
    assert "'quality':quality_score,'quality_score':quality_score" in src
    assert "'quality':[f'Quality score" in src

def test_eps_is_not_displayed_as_zero_when_verified_eps_is_small_positive():
    src=read()
    assert "def journal_eps_display(v):" in src
    assert "if abs(x) < 10: return f'Rp {x:,.2f}'" in src
    assert "Verified EPS ({eps_year or \"latest\"})" in src

def test_implied_eps_has_precision():
    src=read()
    assert "journal_eps_display(scenario_metric_values.get(\"Base\",np.nan))" in src

def test_extreme_base_effect_is_flagged_not_capped():
    src=read()
    assert "extreme_base_effect = bool(cagr is not None" in src
    assert "⚠ Extreme base effect" in src
    assert "extreme_growth = any(np.isfinite(v) and abs(v) >= 3.0" in src
    assert "shown without capping" in src

def test_valuation_guardrail_text_is_present():
    src=read()
    assert "Target prices are withheld because the selected valuation method lacks valid verified inputs." in src
    assert "scenario simulation is withheld because verified valuation inputs are insufficient." in src

def test_master_is_not_candidate():
    master=ROOT/"app"/"dashboard.py"
    assert master.exists()
    assert TARGET is not None
    assert master.resolve()!=TARGET.resolve()
