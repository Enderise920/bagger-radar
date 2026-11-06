import json
from pathlib import Path

import pandas as pd


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RISK_FILE = DATA_DIR / "risk_scores.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def main():

    print("=== BAGGER RADAR RISK VALIDATION ===")

    data = load_json(RISK_FILE)

    df = pd.DataFrame(data.values())

    print("\nStocks validated:", len(df))

    # =========================
    # 1. RISK BY LIQUIDITY
    # =========================

    print("\n=== RISK SCORE BY LIQUIDITY STATE ===")

    liquidity = (
        df.groupby("liquidity_state")["risk_score"]
        .agg(
            [
                "count",
                "mean",
                "median",
                "min",
                "max",
            ]
        )
        .sort_values(
            "median",
            ascending=False,
        )
    )

    print(
        liquidity.to_string(
            float_format=lambda x: f"{x:.2f}"
        )
    )

    # =========================
    # 2. RISK EVIDENCE
    # =========================

    print("\n=== RISK SCORE COMPONENTS ===")

    print(
        df[
            [
                "volatility_score",
                "drawdown_score",
                "extreme_loss_score",
                "risk_score",
            ]
        ]
        .describe(
            percentiles=[
                0.10,
                0.25,
                0.50,
                0.75,
                0.90,
            ]
        )
        .to_string()
    )

    # =========================
    # 3. TOP RISK CHECK
    # =========================

    print("\n=== TOP 20 RISK EVIDENCE CHECK ===")

    top20 = (
        df.sort_values(
            "risk_score",
            ascending=False,
        )
        .head(20)
    )

    print(
        top20[
            [
                "symbol",
                "risk_score",
                "volatility_score",
                "drawdown_score",
                "extreme_loss_score",
                "liquidity_state",
            ]
        ].to_string(
            index=False,
            float_format=lambda x: f"{x:.2f}"
        )
    )

    # =========================
    # 4. LOW RISK CHECK
    # =========================

    print("\n=== LOW RISK CHECK ===")

    low_risk = (
        df.sort_values(
            "risk_score",
            ascending=True,
        )
        .head(20)
    )

    print(
        low_risk[
            [
                "symbol",
                "risk_score",
                "volatility_20d",
                "max_drawdown_60d",
                "max_daily_loss_20d",
                "liquidity_state",
            ]
        ].to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}"
        )
    )

    # =========================
    # 5. EXTREME RISK
    # =========================

    print("\n=== EXTREME RISK ===")

    extreme = df[
        df["risk_score"] >= 80
    ]

    print(
        "Risk Score >=80:",
        len(extreme),
    )

    print(
        "Risk Score >=90:",
        len(
            df[df["risk_score"] >= 90]
        ),
    )

    print(
        "Risk Score >=95:",
        len(
            df[df["risk_score"] >= 95]
        ),
    )

    # =========================
    # 6. ZERO-VOLATILITY CHECK
    # =========================

    print("\n=== ZERO VOLATILITY CHECK ===")

    zero_vol = df[
        df["volatility_20d"] == 0
    ]

    print(
        "Zero volatility stocks:",
        len(zero_vol),
    )

    if not zero_vol.empty:

        print(
            zero_vol[
                [
                    "symbol",
                    "risk_score",
                    "max_drawdown_60d",
                    "max_daily_loss_20d",
                    "liquidity_state",
                ]
            ]
            .sort_values(
                "risk_score"
            )
            .head(20)
            .to_string(
                index=False,
                float_format=lambda x: f"{x:.4f}"
            )
        )

    # =========================
    # 7. NO TRADING EVIDENCE
    # =========================

    print("\n=== NO TRADING EVIDENCE CHECK ===")

    no_trade = df[
        df["liquidity_state"]
        == "NO_TRADING_EVIDENCE"
    ]

    print(
        "Stocks:",
        len(no_trade),
    )

    if not no_trade.empty:

        print(
            no_trade[
                [
                    "symbol",
                    "risk_score",
                    "volatility_score",
                    "drawdown_score",
                    "extreme_loss_score",
                ]
            ]
            .head(20)
            .to_string(
                index=False,
                float_format=lambda x: f"{x:.2f}"
            )
        )

    # =========================
    # 8. RISK CORRELATION
    # =========================

    print("\n=== RISK / RAW METRIC CORRELATION ===")

    print(
        "Risk vs Volatility 20D:",
        f"{df['risk_score'].corr(df['volatility_20d']):.4f}",
    )

    print(
        "Risk vs Drawdown Magnitude:",
        f"{df['risk_score'].corr(df['max_drawdown_60d'].abs()):.4f}",
    )

    print(
        "Risk vs Extreme Daily Loss:",
        f"{df['risk_score'].corr(df['max_daily_loss_20d'].abs()):.4f}",
    )


if __name__ == "__main__":
    main()