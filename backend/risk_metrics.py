import json
from pathlib import Path

import numpy as np
import pandas as pd


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_FILE = DATA_DIR / "daily_cache.json"
OUTPUT_FILE = DATA_DIR / "risk_metrics.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def calculate_risk_metrics(records):
    df = pd.DataFrame(records)

    if df.empty or "close" not in df.columns:
        return None

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    df["close"] = pd.to_numeric(
        df["close"],
        errors="coerce"
    )

    df = df.dropna(subset=["close"])

    if len(df) < 20:
        return None

    # =========================
    # DAILY RETURN
    # =========================

    df["daily_return"] = df["close"].pct_change()

    returns_20 = (
        df["daily_return"]
        .tail(20)
        .dropna()
    )

    returns_60 = (
        df["daily_return"]
        .tail(60)
        .dropna()
    )

    # =========================
    # VOLATILITY
    # =========================

    volatility_20d = (
        returns_20.std(ddof=1)
        if len(returns_20) >= 10
        else np.nan
    )

    volatility_60d = (
        returns_60.std(ddof=1)
        if len(returns_60) >= 30
        else np.nan
    )

    # =========================
    # MAX DRAWDOWN
    # =========================

    prices_60 = df["close"].tail(60)

    running_max = prices_60.cummax()

    drawdown = (
        prices_60 / running_max
    ) - 1

    max_drawdown_60d = drawdown.min()

    # =========================
    # PRICE STABILITY
    # =========================

    zero_return_ratio_20d = (
        (returns_20.abs() < 1e-12).mean()
        if len(returns_20) > 0
        else np.nan
    )

    prices_20 = df["close"].tail(20)

    unique_price_ratio_20d = (
        prices_20.nunique() / len(prices_20)
        if len(prices_20) >= 20
        else np.nan
    )

    # =========================
    # EXTREME DAILY MOVE
    # =========================

    max_daily_gain_20d = (
        returns_20.max()
        if len(returns_20)
        else np.nan
    )

    max_daily_loss_20d = (
        returns_20.min()
        if len(returns_20)
        else np.nan
    )

    return {
        "volatility_20d": float(volatility_20d)
        if pd.notna(volatility_20d)
        else None,

        "volatility_60d": float(volatility_60d)
        if pd.notna(volatility_60d)
        else None,

        "max_drawdown_60d": float(max_drawdown_60d)
        if pd.notna(max_drawdown_60d)
        else None,

        "zero_return_ratio_20d": float(
            zero_return_ratio_20d
        )
        if pd.notna(zero_return_ratio_20d)
        else None,

        "unique_price_ratio_20d": float(
            unique_price_ratio_20d
        )
        if pd.notna(unique_price_ratio_20d)
        else None,

        "max_daily_gain_20d": float(
            max_daily_gain_20d
        )
        if pd.notna(max_daily_gain_20d)
        else None,

        "max_daily_loss_20d": float(
            max_daily_loss_20d
        )
        if pd.notna(max_daily_loss_20d)
        else None,
    }


def main():

    print("=== BAGGER RADAR RISK METRICS ===")

    data = load_json(CACHE_FILE)

    print("Cached stocks:", len(data))

    results = {}

    for symbol, records in data.items():

        metrics = calculate_risk_metrics(records)

        if metrics is None:
            continue

        results[symbol] = {
            "symbol": symbol,
            **metrics,
        }

    print("Stocks analyzed:", len(results))

    # =========================
    # SAVE
    # =========================

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            results,
            file,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )

    print(
        f"\nSaved to: {OUTPUT_FILE}"
    )

    # =========================
    # QUICK CHECK
    # =========================

    df = pd.DataFrame(results.values())

    print("\n=== QUICK CHECK ===")

    print(
        df[
            [
                "symbol",
                "volatility_20d",
                "volatility_60d",
                "max_drawdown_60d",
                "max_daily_loss_20d",
            ]
        ]
        .head(10)
        .to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}"
        )
    )


if __name__ == "__main__":
    main()