from pathlib import Path
import ast

TARGET = Path(r"C:\Gio-AI-Team\app\dashboard_scoring_v3_2_dada_final_ui_consistency_v2.py")

# This local test is intended to be copied to C:\Gio-AI-Team\tests\
# and run there. It validates the regression guard structurally without
# requiring Streamlit to start.

def read_target():
    return TARGET.read_text(encoding="utf-8")

def main():
    src = read_target()
    tree = ast.parse(src)

    assert "dividend_score=n(row.get('dividend_score'))" in src, \
        "Section 05 dividend_score local binding is missing"
    assert "Dividend Score" in src
    assert "Separate dividend-quality score; does not feed the five Bagger dimensions." in src
    assert "Price & momentum" in src
    assert "Risk metrics" in src

    # The Section 05 block must bind dividend_score before its HTML render.
    marker = "# Verified dividend evidence + existing RowletAI illustrative forecast."
    start = src.index(marker)
    end = src.index("    # 06 — VALUATION & PRICE SIMULATION", start)
    section05 = src[start:end]
    assert section05.index("dividend_score=n(row.get('dividend_score'))") < section05.index("Dividend Score")

    ast.parse(src)
    print("ALL DADA FINAL UI CONSISTENCY V2 CHECKS PASSED")
    print(f"Candidate: {TARGET}")

if __name__ == "__main__":
    main()
