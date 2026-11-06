import json
from pathlib import Path

import pandas as pd


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

CACHE_FILE = DATA_DIR / "daily_cache.json"
OUTPUT_FILE = DATA_DIR / "liquidity_flags.json"


def load_cache():
    with open(CACHE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def analyze_stock(symbol, records):

    if not records:
        return None

    df = pd.DataFrame(records)

    required = ["date", "close", "volume"]

    if not all(column in df.columns for column in required):
        return None

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    df["close"] = pd.to_numeric(
        df["close"],
        errors="coerce"
    )

    df["volume"] = pd.to_numeric(
        df["volume"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["date", "close", "volume"]
    )

    df = df.sort_values("date").reset_index(drop=True)

    if len(df) < 20:
        return None

    df["return"] = df["close"].pct_change()

    total_days = len(df)

    recent = df.tail(20)

    trading_day_ratio = (
        (df["volume"] > 0).sum()
        / total_days
    )

    zero_return_ratio = (
        df["return"]
        .fillna(0)
        .abs()
        .eq(0)
        .mean()
    )

    recent_zero_return_ratio = (
        recent["return"]
        .fillna(0)
        .abs()
        .eq(0)
        .mean()
    )

    unique_price_ratio = (
        df["close"].nunique()
        / total_days
    )

    average_volume = df["volume"].mean()

    median_volume = df["volume"].median()

    # -------------------------------------------------
    # Liquidity / stale-price classification
    # -------------------------------------------------

    if (
        trading_day_ratio == 0
        and recent_zero_return_ratio >= 0.80
    ):
        liquidity_state = "NO_TRADING_EVIDENCE"

    elif (
        recent_zero_return_ratio >= 0.80
        or unique_price_ratio <= 0.10
    ):
        liquidity_state = "STALE"

    elif (
        recent_zero_return_ratio >= 0.50
        or unique_price_ratio <= 0.20
    ):
        liquidity_state = "LOW_ACTIVITY"

    elif (
        recent_zero_return_ratio >= 0.30
        or unique_price_ratio <= 0.30
    ):
        liquidity_state = "CAUTION"

    else:
        liquidity_state = "ACTIVE"

    # Whether momentum calculations should be trusted normally
    if liquidity_state in [
        "NO_TRADING_EVIDENCE",
        "STALE"
    ]:
        momentum_evidence = "INSUFFICIENT"

    elif liquidity_state == "LOW_ACTIVITY":
        momentum_evidence = "LIMITED"

    elif liquidity_state == "CAUTION":
        momentum_evidence = "MODERATE"

    else:
        momentum_evidence = "GOOD"

    return {
        "symbol": symbol,
        "observations": total_days,
        "average_volume": round(
            float(average_volume),
            2
        ),
        "median_volume": round(
            float(median_volume),
            2
        ),
        "trading_day_ratio": round(
            float(trading_day_ratio),
            4
        ),
        "zero_return_ratio": round(
            float(zero_return_ratio),
            4
        ),
        "recent_zero_return_ratio": round(
            float(recent_zero_return_ratio),
            4
        ),
        "unique_price_ratio": round(
            float(unique_price_ratio),
            4
        ),
        "liquidity_state": liquidity_state,
        "momentum_evidence": momentum_evidence
    }


def main():

    print(
        "=== BAGGER RADAR LIQUIDITY FLAGS ==="
    )

    cache = load_cache()

    results = {}

    for symbol, records in cache.items():

        result = analyze_stock(
            symbol,
            records
        )

        if result is not None:
            results[symbol] = result

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            results,
            file,
            indent=2,
            ensure_ascii=False
        )

    df = pd.DataFrame(
        results.values()
    )

    print(
        "\nStocks analyzed:",
        len(df)
    )

    print(
        "\n=== LIQUIDITY STATE ==="
    )

    print(
        df["liquidity_state"]
        .value_counts()
        .to_string()
    )

    print(
        "\n=== MOMENTUM EVIDENCE ==="
    )

    print(
        df["momentum_evidence"]
        .value_counts()
        .to_string()
    )

    print(
        "\nSaved:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()