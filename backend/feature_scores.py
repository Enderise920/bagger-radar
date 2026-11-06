import json
from pathlib import Path

from normalization import (
    percentile_score,
    inverse_percentile_score
)


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

QUALITY_FILE = DATA_DIR / "fundamentals_quality.json"
OUTPUT_FILE = DATA_DIR / "feature_scores.json"


NORMAL_SCORE_METRICS = [
    "yoy_quarter_revenue_growth",
    "yoy_quarter_earnings_growth",
    "roe_ttm",
    "roa_ttm"
]


INVERSE_SCORE_METRICS = [
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


def clean_values(
    data,
    metric,
    positive_only=False
):

    values = []

    for company in data:

        value = company.get(metric)

        if value is None:
            continue

        try:
            value = float(value)
        except (TypeError, ValueError):
            continue

        if positive_only and value <= 0:
            continue

        values.append(value)

    return values


def calculate_score(
    value,
    metric,
    reference_values
):

    if value is None:
        return None

    if metric in INVERSE_SCORE_METRICS:

        return inverse_percentile_score(
            value,
            reference_values
        )

    return percentile_score(
        value,
        reference_values
    )


def build_feature_scores(data):

    reference_values = {}

    for metric in NORMAL_SCORE_METRICS:

        reference_values[metric] = clean_values(
            data,
            metric
        )

    for metric in INVERSE_SCORE_METRICS:

        reference_values[metric] = clean_values(
            data,
            metric,
            positive_only=True
        )

    scored_data = []

    for company in data:

        scores = {}

        for metric in (
            NORMAL_SCORE_METRICS
            + INVERSE_SCORE_METRICS
        ):

            value = company.get(metric)

            score = calculate_score(
                value,
                metric,
                reference_values[metric]
            )

            scores[metric] = score

        scored_company = {
            "symbol": company.get("symbol"),
            "company_name": company.get("company_name"),
            "data_confidence": company.get(
                "data_confidence"
            ),
            "scores": scores
        }

        scored_data.append(
            scored_company
        )

    return scored_data


def save_scores(data):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        "\nFeature scores disimpan ke:"
    )

    print(OUTPUT_FILE)


def print_summary(data):

    metrics = (
        NORMAL_SCORE_METRICS
        + INVERSE_SCORE_METRICS
    )

    print(
        "\n=== FEATURE SCORE COVERAGE ==="
    )

    total = len(data)

    for metric in metrics:

        available = 0

        for company in data:

            score = company["scores"].get(
                metric
            )

            if score is not None:
                available += 1

        percentage = (
            available / total * 100
            if total
            else 0
        )

        print(
            f"{metric:35}"
            f"{available:4}/{total:<4}"
            f"({percentage:5.1f}%)"
        )


def print_sample(data):

    print(
        "\n=== SAMPLE FEATURE SCORES ==="
    )

    symbols = [
        "BBRI.JK",
        "BMRI.JK",
        "BBCA.JK",
        "ARTI.JK",
        "LMSH.JK"
    ]

    for symbol in symbols:

        company = next(
            (
                item
                for item in data
                if item["symbol"] == symbol
            ),
            None
        )

        if company is None:
            continue

        print(
            f"\n--- {symbol} ---"
        )

        print(
            "Confidence:",
            company["data_confidence"]
        )

        for metric, score in company[
            "scores"
        ].items():

            if score is None:

                formatted = "INVALID / NO DATA"

            else:

                formatted = f"{score:.2f}"

            print(
                f"{metric:35}"
                f"{formatted}"
            )


if __name__ == "__main__":

    print(
        "=== BAGGER RADAR FEATURE SCORING ==="
    )

    data = load_data()

    scored_data = build_feature_scores(
        data
    )

    print_summary(
        scored_data
    )

    print_sample(
        scored_data
    )

    save_scores(
        scored_data
    )