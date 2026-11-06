import json
from pathlib import Path

import numpy as np


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

QUALITY_FILE = DATA_DIR / "fundamentals_quality.json"


METRICS = [
    "yoy_quarter_revenue_growth",
    "yoy_quarter_earnings_growth",
    "roe_ttm",
    "roa_ttm",
    "pe_ttm",
    "pb_mrq"
]


def load_data():

    with open(
        QUALITY_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def get_values(data, metric):

    values = []

    for company in data:

        value = company.get(metric)

        if value is None:
            continue

        try:
            value = float(value)
        except (TypeError, ValueError):
            continue

        if not np.isfinite(value):
            continue

        # Untuk valuation:
        # hanya PE/PB positif yang valid
        if metric in ["pe_ttm", "pb_mrq"]:
            if value <= 0:
                continue

        values.append(value)

    return values


def print_distribution(metric, values):

    if not values:
        print(f"\n{metric}: NO DATA")
        return

    arr = np.array(values)

    print(
        f"\n=== {metric} ==="
    )

    print(
        f"Count : {len(arr)}"
    )

    print(
        f"Min   : {np.min(arr):.4f}"
    )

    print(
        f"P10   : {np.percentile(arr, 10):.4f}"
    )

    print(
        f"P25   : {np.percentile(arr, 25):.4f}"
    )

    print(
        f"Median: {np.percentile(arr, 50):.4f}"
    )

    print(
        f"P75   : {np.percentile(arr, 75):.4f}"
    )

    print(
        f"P90   : {np.percentile(arr, 90):.4f}"
    )

    print(
        f"P95   : {np.percentile(arr, 95):.4f}"
    )

    print(
        f"Max   : {np.max(arr):.4f}"
    )


if __name__ == "__main__":

    print(
        "=== BAGGER RADAR FEATURE DISTRIBUTION ==="
    )

    data = load_data()

    for metric in METRICS:

        values = get_values(
            data,
            metric
        )

        print_distribution(
            metric,
            values
        )