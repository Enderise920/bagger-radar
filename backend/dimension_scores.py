import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

FEATURE_SCORE_FILE = DATA_DIR / "feature_scores.json"

OUTPUT_FILE = DATA_DIR / "dimension_scores.json"


def load_feature_scores():

    with open(
        FEATURE_SCORE_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def average_available(values):

    valid_values = [
        value
        for value in values
        if value is not None
    ]

    if not valid_values:
        return None

    return round(
        sum(valid_values) / len(valid_values),
        2
    )


def calculate_dimensions(company):

    scores = company.get(
        "scores",
        {}
    )

    growth_score = average_available(
        [
            scores.get(
                "yoy_quarter_revenue_growth"
            ),
            scores.get(
                "yoy_quarter_earnings_growth"
            )
        ]
    )

    quality_score = average_available(
        [
            scores.get(
                "roe_ttm"
            ),
            scores.get(
                "roa_ttm"
            )
        ]
    )

    valuation_score = average_available(
        [
            scores.get(
                "pe_ttm"
            ),
            scores.get(
                "pb_mrq"
            )
        ]
    )

    return {
        "growth_score": growth_score,
        "quality_score": quality_score,
        "valuation_score": valuation_score
    }


def build_dimension_dataset(data):

    results = []

    for company in data:

        dimensions = calculate_dimensions(
            company
        )

        result = {
            "symbol": company.get(
                "symbol"
            ),
            "company_name": company.get(
                "company_name"
            ),
            "data_confidence": company.get(
                "data_confidence"
            ),
            **dimensions
        }

        results.append(
            result
        )

    return results


def save_data(data):

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
        "\nDimension scores disimpan ke:"
    )

    print(
        OUTPUT_FILE
    )


def print_coverage(data):

    total = len(data)

    print(
        "\n=== DIMENSION SCORE COVERAGE ==="
    )

    metrics = [
        "growth_score",
        "quality_score",
        "valuation_score"
    ]

    for metric in metrics:

        available = sum(
            1
            for company in data
            if company.get(metric) is not None
        )

        percentage = (
            available / total * 100
            if total
            else 0
        )

        print(
            f"{metric:20}"
            f"{available:4}/{total:<4}"
            f"({percentage:5.1f}%)"
        )


def print_sample(data):

    symbols = [
        "BBRI.JK",
        "BMRI.JK",
        "BBCA.JK",
        "ARTI.JK",
        "LMSH.JK"
    ]

    print(
        "\n=== SAMPLE DIMENSION SCORES ==="
    )

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
            "Confidence      :",
            company["data_confidence"]
        )

        print(
            "Growth Score    :",
            company["growth_score"]
        )

        print(
            "Quality Score   :",
            company["quality_score"]
        )

        print(
            "Valuation Score :",
            company["valuation_score"]
        )


if __name__ == "__main__":

    print(
        "=== BAGGER RADAR DIMENSION SCORING ==="
    )

    feature_data = load_feature_scores()

    dimension_data = build_dimension_dataset(
        feature_data
    )

    print_coverage(
        dimension_data
    )

    print_sample(
        dimension_data
    )

    save_data(
        dimension_data
    )