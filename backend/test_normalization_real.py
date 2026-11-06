import json
from pathlib import Path

from normalization import (
    percentile_score,
    inverse_percentile_score
)


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

QUALITY_FILE = DATA_DIR / "fundamentals_quality.json"


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

        if metric in [
            "pe_ttm",
            "pb_mrq"
        ] and value <= 0:
            continue

        values.append(value)

    return values


def format_score(score):

    if score is None:
        return "INVALID"

    return f"{score:.2f}"


def test_metric(
    data,
    metric,
    symbol
):

    values = get_values(
        data,
        metric
    )

    company = next(
        (
            item
            for item in data
            if item.get("symbol") == symbol
        ),
        None
    )

    if company is None:
        return

    value = company.get(metric)

    if value is None:
        print(
            f"{symbol:8} "
            f"{metric:35} "
            f"value=None "
            f"score=NO DATA"
        )
        return

    if metric in [
        "pe_ttm",
        "pb_mrq"
    ]:

        score = inverse_percentile_score(
            value,
            values
        )

    else:

        score = percentile_score(
            value,
            values
        )

    print(
        f"{symbol:8} "
        f"{metric:35} "
        f"value={value:12.4f} "
        f"score={format_score(score)}"
    )


if __name__ == "__main__":

    print(
        "=== BAGGER RADAR REAL NORMALIZATION TEST ==="
    )

    data = load_data()

    test_symbols = [
        "BBRI.JK",
        "BMRI.JK",
        "BBCA.JK",
        "ARTI.JK",
        "LMSH.JK"
    ]

    metrics = [
        "yoy_quarter_revenue_growth",
        "yoy_quarter_earnings_growth",
        "roe_ttm",
        "roa_ttm",
        "pe_ttm",
        "pb_mrq"
    ]

    for symbol in test_symbols:

        print(
            f"\n--- {symbol} ---"
        )

        for metric in metrics:

            test_metric(
                data,
                metric,
                symbol
            )