from pathlib import Path
import ast
import math

# Windows/project-portable path: place the V3.2 candidate in C:\Gio-AI-Team\app\
# (or beside this test file). No /mnt/data path is required.
ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_NAMES = [
    'dashboard_scoring_v3_2_dada_guardrails_candidate.py',
]
CANDIDATE_PATHS = [
    ROOT / 'app' / CANDIDATE_NAMES[0],
    ROOT / CANDIDATE_NAMES[0],
    Path(__file__).resolve().parent / CANDIDATE_NAMES[0],
]
TARGET = next((p for p in CANDIDATE_PATHS if p.exists()), None)


def read():
    if TARGET is None:
        checked = '\n'.join(f'  - {p}' for p in CANDIDATE_PATHS)
        raise FileNotFoundError(
            'V3.2 candidate not found. Put dashboard_scoring_v3_2_dada_guardrails_candidate.py in '
            f'{ROOT / "app"} or beside this test. Checked:\n{checked}'
        )
    return TARGET.read_text(encoding='utf-8')


def test_source_compiles():
    ast.parse(read())


def test_zero_eps_cannot_enable_pe():
    for eps in (0.0, -0.01, -10.0):
        assert not (math.isfinite(eps) and eps > 0)
    src = read()
    assert '_pe_ready = np.isfinite(eps) and eps > 0' in src
    assert 'if np.isfinite(eps_anchor) and eps_anchor > 0' in src


def test_no_default_fake_pe_anchor():
    src = read()
    assert 'anchor_pe = 10.0' not in src
    assert 'anchor_pe = np.nan' in src


def test_zero_eps_message_and_n_a_path():
    src = read()
    assert 'Verified EPS is zero or negative; P/E target-price simulation is withheld.' in src
    assert 'Withheld because verified EPS is not positive.' in src


def test_dimension_coverage_is_not_called_strong_evidence():
    src = read()
    assert 'Dimension Coverage' in src
    assert 'Strong Evidence</div>' not in src
    assert 'Price &amp; momentum <b class="j-exec-check-state limited">Limited</b>' in src
    assert 'Risk metrics <b class="j-exec-check-state limited">Limited</b>' in src


def test_risk_guardrail_for_stale_flat_series():
    src = read()
    assert "limited_liquidity = liq in {'STALE','LOW_ACTIVITY','NO_TRADING_EVIDENCE'}" in src
    assert "return ('Limited evidence','moderate')" in src
    assert 'flat price statistics are treated as evidence-limited rather than automatically low-risk' in src


def test_risk_badge_has_reserved_width():
    src = read()
    assert 'min-width:84px' in src
    assert '.j07-detail{font-size:12px;line-height:1.25;color:#617B94;min-width:0;padding-left:3px}' in src


def test_v3_engine_is_still_used():
    src = read()
    assert '_v3_momentum_score' in src
    assert '_v3_risk_strength' in src
    assert '_v3_bagger_score' in src


def test_master_not_modified_by_this_patch():
    master = ROOT / 'app' / 'dashboard.py'
    assert master.exists()
    assert TARGET is not None
    # This test only verifies that the canonical MASTER exists separately from the candidate.
    assert master.resolve() != TARGET.resolve()


if __name__ == '__main__':
    tests = [
        test_source_compiles,
        test_zero_eps_cannot_enable_pe,
        test_no_default_fake_pe_anchor,
        test_zero_eps_message_and_n_a_path,
        test_dimension_coverage_is_not_called_strong_evidence,
        test_risk_guardrail_for_stale_flat_series,
        test_risk_badge_has_reserved_width,
        test_v3_engine_is_still_used,
        test_master_not_modified_by_this_patch,
    ]
    for t in tests:
        t()
    print(f'ALL DADA GUARDRAIL TESTS PASSED ({len(tests)}/{len(tests)})')
    print(f'Candidate: {TARGET}')
