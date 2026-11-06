import json
from pathlib import Path

import pandas as pd


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

CACHE_FILE = DATA_DIR / "daily_cache.json"


def load_cache():

    with open(
        CACHE_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def analyze_liquidity(records):

    if not records:
        return None

    df = pd.DataFrame(records)

    required_columns = [
        "date",
        "close",
        "volume"
    ]

    for column in required_columns:

        if column not in df.columns:
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
        subset=[
            "date",
            "close",
            "volume"
        ]
    )

    df = df.sort_values(
        "date"
    ).reset_index(
        drop=True
    )

    if len(df) < 20:
        return None

    # Daily price change
    df["price_change"] = (
        df["close"]
        .pct_change()
    )

    # Count days where price did not change
    zero_return_days = (
        df["price_change"]
        .fillna(0)
        .abs()
        .eq(0)
        .sum()
    )

    total_days = len(df)

    zero_return_ratio = (
        zero_return_days /
        total_days
    )

    # Average daily volume
    average_volume = (
        df["volume"]
        .mean()
    )

    median_volume = (
        df["volume"]
        .median()
    )

    # Days with actual trading volume
    positive_volume_days = (
        (df["volume"] > 0)
        .sum()
    )

    trading_day_ratio = (
        positive_volume_days /
        total_days
    )

    # Number of unique closing prices
    unique_close_prices = (
        df["close"]
        .nunique()
    )

    unique_price_ratio = (
        unique_close_prices /
        total_days
    )

    # Recent 20-day stale ratio
    recent = df.tail(20)

    recent_zero_return_ratio = (
        recent["price_change"]
        .fillna(0)
        .abs()
        .eq(0)
        .mean()
    )

    return {
        "observations": int(
            total_days
        ),
        "average_volume": float(
            average_volume
        ),
        "median_volume": float(
            median_volume
        ),
        "trading_day_ratio": float(
            trading_day_ratio
        ),
        "zero_return_ratio": float(
            zero_return_ratio
        ),
        "recent_zero_return_ratio": float(
            recent_zero_return_ratio
        ),
        "unique_close_prices": int(
            unique_close_prices
        ),
        "unique_price_ratio": float(
            unique_price_ratio
        )
    }


def analyze_universe(cache):

    results = []

    for symbol, records in cache.items():

        result = analyze_liquidity(
            records
        )

        if result is None:
            continue

        results.append({
            "symbol": symbol,
            **result
        })

    return results


def print_distribution(
    df,
    metric
):

    series = pd.to_numeric(
        df[metric],
        errors="coerce"
    ).dropna()

    if series.empty:
        return

    print(
        f"\n{metric}"
    )

    print(
        "Count :",
        len(series)
    )

    print(
        "Min   :",
        f"{series.min():.4f}"
    )

    print(
        "P10   :",
        f"{series.quantile(0.10):.4f}"
    )

    print(
        "P25   :",
        f"{series.quantile(0.25):.4f}"
    )

    print(
        "Median:",
        f"{series.median():.4f}"
    )

    print(
        "P75   :",
        f"{series.quantile(0.75):.4f}"
    )

    print(
        "P90   :",
        f"{series.quantile(0.90):.4f}"
    )

    print(
        "Max   :",
        f"{series.max():.4f}"
    )


def print_summary(results):

    df = pd.DataFrame(
        results
    )

    print(
        "\n=== LIQUIDITY ANALYSIS ==="
    )

    print(
        "Stocks analyzed:",
        len(df)
    )

    if df.empty:
        return

    metrics = [
        "average_volume",
        "median_volume",
        "trading_day_ratio",
        "zero_return_ratio",
        "recent_zero_return_ratio",
        "unique_price_ratio"
    ]

    for metric in metrics:

        print_distribution(
            df,
            metric
        )

    print(
        "\n=== POTENTIAL STALE PRICES ==="
    )

    stale = df[
        df[
            "recent_zero_return_ratio"
        ] >= 0.50
    ].copy()

    print(
        "Stocks with >=50% "
        "zero-return days in recent 20 days:",
        len(stale)
    )

    if not stale.empty:

        stale = stale.sort_values(
            "recent_zero_return_ratio",
            ascending=False
        )

        print(
            "\nTop 20:"
        )

        for _, row in stale.head(20).iterrows():

            print(
                f"{row['symbol']:10}"
                f"recent_zero="
                f"{row['recent_zero_return_ratio'] * 100:6.1f}% "
                f"unique_price="
                f"{row['unique_price_ratio'] * 100:6.1f}% "
                f"avg_volume="
                f"{row['average_volume']:,.0f}"
            )


def main():

    print(
        "=== BAGGER RADAR LIQUIDITY ANALYSIS ==="
    )

    cache = load_cache()

    print(
        "Cached stocks:",
        len(cache)
    )

    results = analyze_universe(
        cache
    )

    print_summary(
        results
    )


if __name__ == "__main__":

    main()