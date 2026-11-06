import json
from pathlib import Path

import numpy as np
import pandas as pd


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_FILE = DATA_DIR / "daily_cache.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def calculate_risk_metrics(records):
    df = pd.DataFrame(records)

    if df.empty or "close" not in df.columns:
        return None

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # Pastikan close numerik
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"])

    if len(df) < 20:
        return None

    # Daily return
    df["daily_return"] = df["close"].pct_change()

    # =========================
    # 1. VOLATILITY
    # =========================

    returns_20 = df["daily_return"].tail(20).dropna()
    returns_60 = df["daily_return"].tail(60).dropna()

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
    # 2. MAXIMUM DRAWDOWN
    # =========================

    prices_60 = df["close"].tail(60)

    running_max = prices_60.cummax()
    drawdown = prices_60 / running_max - 1

    max_drawdown_60d = drawdown.min()

    # =========================
    # 3. PRICE STABILITY
    # =========================

    returns_20_abs = returns_20.abs()

    zero_return_ratio_20d = (
        (returns_20_abs < 1e-12).mean()
        if len(returns_20) > 0
        else np.nan
    )

    unique_price_ratio_20d = (
        prices_60.tail(20).nunique() / len(prices_60.tail(20))
        if len(prices_60) >= 20
        else np.nan
    )

    # =========================
    # 4. EXTREME MOVE
    # =========================

    max_daily_gain_20d = returns_20.max() if len(returns_20) else np.nan
    max_daily_loss_20d = returns_20.min() if len(returns_20) else np.nan

    return {
        "volatility_20d": volatility_20d,
        "volatility_60d": volatility_60d,
        "max_drawdown_60d": max_drawdown_60d,
        "zero_return_ratio_20d": zero_return_ratio_20d,
        "unique_price_ratio_20d": unique_price_ratio_20d,
        "max_daily_gain_20d": max_daily_gain_20d,
        "max_daily_loss_20d": max_daily_loss_20d,
    }


def main():

    print("=== BAGGER RADAR RISK CALCULATION ===")

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

    df = pd.DataFrame(results.values())

    print("Stocks analyzed:", len(df))

    if df.empty:
        print("Tidak ada data risk yang dapat dihitung.")
        return

    # =========================
    # DISTRIBUTION
    # =========================

    print("\n=== VOLATILITY 20D ===")

    print(
        df["volatility_20d"]
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

    print("\n=== VOLATILITY 60D ===")

    print(
        df["volatility_60d"]
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

    print("\n=== MAX DRAWDOWN 60D ===")

    print(
        df["max_drawdown_60d"]
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

    print("\n=== PRICE STABILITY ===")

    print(
        df[
            [
                "zero_return_ratio_20d",
                "unique_price_ratio_20d",
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
    # TOP RISK EXAMPLES
    # =========================

    print("\n=== HIGHEST VOLATILITY ===")

    top_vol = df.sort_values(
        "volatility_20d",
        ascending=False
    ).head(15)

    print(
        top_vol[
            [
                "symbol",
                "volatility_20d",
                "volatility_60d",
                "max_drawdown_60d",
            ]
        ].to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}"
        )
    )

    print("\n=== WORST DRAWDOWN ===")

    top_drawdown = df.sort_values(
        "max_drawdown_60d",
        ascending=True
    ).head(15)

    print(
        top_drawdown[
            [
                "symbol",
                "max_drawdown_60d",
                "volatility_20d",
                "volatility_60d",
            ]
        ].to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}"
        )
    )

    print("\n=== HIGHEST DAILY LOSS ===")

    top_loss = df.sort_values(
        "max_daily_loss_20d",
        ascending=True
    ).head(15)

    print(
        top_loss[
            [
                "symbol",
                "max_daily_loss_20d",
                "volatility_20d",
                "max_drawdown_60d",
            ]
        ].to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}"
        )
    )


if __name__ == "__main__":
    main()