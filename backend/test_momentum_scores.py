import json
from pathlib import Path

from test_momentum_calculation import calculate_momentum
from normalization import percentile_score


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

INPUT_FILE = DATA_DIR / "momentum_raw_test.json"


MOMENTUM_METRICS = [
    "return_20d",
    "return_60d",
    "price_vs_ma20",
    "price_vs_ma60"
]


def load_data():

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def calculate_raw_momentum(data):

    results = {}

    for symbol, records in data.items():

        momentum = calculate_momentum(
            records
        )

        if momentum is not None:

            results[symbol] = momentum

    return results


def build_reference_values(
    momentum_data
):

    references = {}

    for metric in MOMENTUM_METRICS:

        references[metric] = []

        for data in momentum_data.values():

            value = data.get(metric)

            if value is None:
                continue

            references[metric].append(
                value
            )

    return references


def calculate_scores(
    momentum_data,
    references
):

    results = {}

    for symbol, data in momentum_data.items():

        scores = {}

        for metric in MOMENTUM_METRICS:

            value = data.get(metric)

            if value is None:

                scores[metric] = None

                continue

            scores[metric] = percentile_score(
                value,
                references[metric]
            )

        results[symbol] = scores

    return results


def average_score(scores):

    valid_scores = [
        value
        for value in scores.values()
        if value is not None
    ]

    if not valid_scores:

        return None

    return round(
        sum(valid_scores)
        / len(valid_scores),
        2
    )


def main():

    print(
        "=== BAGGER RADAR MOMENTUM SCORE TEST ==="
    )

    raw_data = load_data()

    momentum_data = calculate_raw_momentum(
        raw_data
    )

    references = build_reference_values(
        momentum_data
    )

    scores = calculate_scores(
        momentum_data,
        references
    )

    print(
        "\n=== MOMENTUM SCORES ==="
    )

    for symbol in scores:

        print(
            f"\n--- {symbol} ---"
        )

        for metric in MOMENTUM_METRICS:

            score = scores[symbol].get(
                metric
            )

            if score is None:

                print(
                    f"{metric:20}"
                    "NO DATA"
                )

            else:

                print(
                    f"{metric:20}"
                    f"{score:.2f}"
                )

        total = average_score(
            scores[symbol]
        )

        print(
            f"{'Momentum Score':20}"
            f"{total:.2f}"
        )


if __name__ == "__main__":

    main()