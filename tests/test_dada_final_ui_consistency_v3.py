from pathlib import Path
import ast

TARGET = Path(r"C:\Gio-AI-Team\app\dashboard_scoring_v3_2_dada_final_ui_consistency_v3.py")


def read():
    return TARGET.read_text(encoding="utf-8")


def test_source_compiles():
    ast.parse(read())


def test_section05_dividend_score_and_orange_bar():
    src = read()
    assert "dividend_score=n(row.get('dividend_score'))" in src
    assert "Dividend Score" in src
    assert 'j-dividend-progress orange' in src
    assert '.j-dividend-progress.orange span{background:#f28a18}' in src
    assert 'j-dividend-status amber' in src


def test_section08_uses_quality_not_dividend():
    src = read()
    expected = "score_specs=[('Growth','growth','growth_score','▥'),('Quality','quality','quality_score','●'),('Valuation','valuation','valuation_score','◆'),('Risk Strength','risk','risk_score','⬟'),('Momentum','momentum','momentum_score','▥')]"
    assert expected in src
    assert "quality_score=n(row.get('quality_score'))" in src
    assert "'quality':quality_score,'quality_score':quality_score" in src
    assert "'quality_score':'quality'" in src

    # Section 08 must not use Dividend as one of the five model cards.
    section = src[src.index("# 08 — MODEL SAYS"):src.index("# 09 — CONCLUSION")]
    assert "('Dividend','dividend','dividend_score'" not in section


def test_no_bagger_dividend_dependency():
    src = read()
    section = src[src.index("# 08 — MODEL SAYS"):src.index("# 09 — CONCLUSION")]
    assert "Model combines 5 key dimensions: Growth, Quality, Valuation, Momentum and Risk" in src
    assert "dividend_score" not in section.split("score_specs=",1)[1].split("score_values=",1)[0]


if __name__ == "__main__":
    tests = [
        test_source_compiles,
        test_section05_dividend_score_and_orange_bar,
        test_section08_uses_quality_not_dividend,
        test_no_bagger_dividend_dependency,
    ]
    for t in tests:
        t()
    print(f"ALL DADA FINAL UI CONSISTENCY V3 TESTS PASSED ({len(tests)}/{len(tests)})")
    print(f"Candidate: {TARGET}")
