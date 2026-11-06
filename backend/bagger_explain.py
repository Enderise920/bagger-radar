import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

INPUT_FILE = DATA_DIR / "bagger_scores.json"


WEIGHTS = {
    "growth_score": 0.25,
    "quality_score": 0.20,
    "valuation_score": 0.20,
    "momentum_score": 0.20,
    "risk_strength": 0.15,
}


DISPLAY_NAMES = {
    "growth_score": "Growth",
    "quality_score": "Quality",
    "valuation_score": "Valuation",
    "momentum_score": "Momentum",
    "risk_strength": "Risk Strength",
}


def load_data():

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
    ) as f:

        return pd.DataFrame(
            json.load(f)
        )


def explain_stock(
    df,
    symbol,
):

    row = df[
        df["symbol"] == symbol
    ]

    if row.empty:

        return {
            "symbol": symbol,
            "status": "NOT_FOUND",
        }

    row = row.iloc[0]

    # =====================================================
    # INSUFFICIENT EVIDENCE
    # =====================================================

    if pd.isna(row["bagger_score"]):

        return {
            "symbol": symbol,
            "status": "INSUFFICIENT_EVIDENCE",
            "available_dimensions": int(
                row["available_dimensions"]
            ),
            "evidence_level": row[
                "evidence_level"
            ],
            "composite_signal": row[
                "composite_signal"
            ],
        }

    # =====================================================
    # COMPONENT CONTRIBUTIONS
    # =====================================================

    contributions = []

    for column, weight in WEIGHTS.items():

        value = row[column]

        contribution = (
            value * weight
        )

        contributions.append(
            {
                "dimension": DISPLAY_NAMES[
                    column
                ],
                "score": round(
                    float(value),
                    2,
                ),
                "weight": round(
                    weight * 100,
                    1,
                ),
                "contribution": round(
                    float(contribution),
                    2,
                ),
            }
        )

    contribution_df = pd.DataFrame(
        contributions
    )

    # =====================================================
    # RANK CONTRIBUTIONS
    # =====================================================

    strongest = (
        contribution_df
        .sort_values(
            "contribution",
            ascending=False,
        )
    )

    # =====================================================
    # RELATIVE STRENGTH
    # =====================================================

    strong_dimensions = (
        contribution_df[
            contribution_df["score"] >= 70
        ]
        .sort_values(
            "score",
            ascending=False,
        )
    )

    weak_dimensions = (
        contribution_df[
            contribution_df["score"] < 50
        ]
        .sort_values(
            "score",
            ascending=True,
        )
    )

    # =====================================================
    # BUILD EXPLANATION
    # =====================================================

    strongest_names = (
        strongest
        .head(3)["dimension"]
        .tolist()
    )

    strong_names = (
        strong_dimensions[
            "dimension"
        ].tolist()
    )

    weak_names = (
        weak_dimensions[
            "dimension"
        ].tolist()
    )

    explanation = {
        "symbol": symbol,
        "status": "SCORED",
        "bagger_score": round(
            float(row["bagger_score"]),
            2,
        ),
        "evidence_level": row[
            "evidence_level"
        ],
        "available_dimensions": int(
            row["available_dimensions"]
        ),
        "composite_signal": row[
            "composite_signal"
        ],

        "components": contributions,

        "strongest_contributors":
            strongest_names,

        "strong_dimensions":
            strong_names,

        "watchpoints":
            weak_names,

        "risk_evidence":
            row["risk_evidence"],

        "liquidity_flag":
            row["liquidity_flag"],
    }

    return explanation


def print_explanation(
    explanation,
):

    print("\n" + "=" * 70)
    print(
        f"WHY THIS SCORE? — "
        f"{explanation['symbol']}"
    )
    print("=" * 70)

    if explanation["status"] != "SCORED":

        print(
            f"Status             : "
            f"{explanation['status']}"
        )

        print(
            f"Available dimensions: "
            f"{explanation.get('available_dimensions')}"
        )

        print(
            f"Evidence level     : "
            f"{explanation.get('evidence_level')}"
        )

        return

    print(
        f"Bagger Score       : "
        f"{explanation['bagger_score']:.2f}"
    )

    print(
        f"Evidence level     : "
        f"{explanation['evidence_level']}"
    )

    print(
        f"Dimensions         : "
        f"{explanation['available_dimensions']}/5"
    )

    print(
        f"Composite Signal   : "
        f"{explanation['composite_signal']}"
    )

    print("\nComponent breakdown:")
    print(
        "-" * 70
    )

    component_df = pd.DataFrame(
        explanation["components"]
    )

    print(
        component_df.to_string(
            index=False
        )
    )

    print(
        "\nStrongest contributors:"
    )

    for item in explanation[
        "strongest_contributors"
    ]:

        print(
            f"  • {item}"
        )

    print(
        "\nStrong dimensions (score >=70):"
    )

    if explanation[
        "strong_dimensions"
    ]:

        for item in explanation[
            "strong_dimensions"
        ]:

            print(
                f"  • {item}"
            )

    else:

        print(
            "  None"
        )

    print(
        "\nWatchpoints (score <50):"
    )

    if explanation[
        "watchpoints"
    ]:

        for item in explanation[
            "watchpoints"
        ]:

            print(
                f"  • {item}"
            )

    else:

        print(
            "  None"
        )

    print(
        "\nRisk evidence:"
    )

    print(
        f"  {explanation['risk_evidence']}"
    )

    print(
        "\nLiquidity:"
    )

    print(
        f"  {explanation['liquidity_flag']}"
    )

    print("=" * 70)


def main():

    df = load_data()

    print(
        "BAGGER RADAR — EXPLAINABLE SCORE"
    )

    # =====================================================
    # DEMO STOCKS
    # =====================================================

    symbols = [
        "CINT.JK",
        "OILS.JK",
        "AMOR.JK",
        "CARS.JK",
        "INDR.JK",
    ]

    for symbol in symbols:

        explanation = explain_stock(
            df,
            symbol,
        )

        print_explanation(
            explanation
        )


if __name__ == "__main__":
    main()