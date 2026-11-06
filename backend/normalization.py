import numpy as np


def percentile_score(
    value,
    values
):
    """
    Mengubah nilai menjadi percentile score 0-100.

    Semakin tinggi nilai,
    semakin tinggi score.

    Contoh:
    nilai tertinggi -> mendekati 100
    nilai terendah  -> mendekati 0
    """

    if value is None:
        return None

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    clean_values = []

    for item in values:

        if item is None:
            continue

        try:
            item = float(item)
        except (TypeError, ValueError):
            continue

        if not np.isfinite(item):
            continue

        clean_values.append(item)

    if not clean_values:
        return None

    arr = np.array(
        clean_values,
        dtype=float
    )

    score = np.mean(
        arr <= value
    ) * 100

    return round(
        float(score),
        2
    )


def inverse_percentile_score(
    value,
    values
):
    """
    Mengubah nilai menjadi percentile score 0-100
    dengan arah terbalik.

    Semakin rendah nilai,
    semakin tinggi score.

    Cocok untuk:
    - PE
    - PB

    Nilai <= 0 dianggap INVALID
    dan tidak mendapatkan score.
    """

    if value is None:
        return None

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    # PE/PB <= 0 tidak valid
    if value <= 0:
        return None

    clean_values = []

    for item in values:

        if item is None:
            continue

        try:
            item = float(item)
        except (TypeError, ValueError):
            continue

        if not np.isfinite(item):
            continue

        # Hanya valuation metric positif
        if item <= 0:
            continue

        clean_values.append(item)

    if not clean_values:
        return None

    arr = np.array(
        clean_values,
        dtype=float
    )

    score = np.mean(
        arr >= value
    ) * 100

    return round(
        float(score),
        2
    )


def test_normalization():

    values = [
        10,
        20,
        30,
        40,
        50
    ]

    print(
        "=== TEST NORMALIZATION ==="
    )

    print(
        "Value 10:",
        percentile_score(
            10,
            values
        )
    )

    print(
        "Value 30:",
        percentile_score(
            30,
            values
        )
    )

    print(
        "Value 50:",
        percentile_score(
            50,
            values
        )
    )

    print(
        "\n=== TEST INVERSE ==="
    )

    print(
        "Value 10:",
        inverse_percentile_score(
            10,
            values
        )
    )

    print(
        "Value 30:",
        inverse_percentile_score(
            30,
            values
        )
    )

    print(
        "Value 50:",
        inverse_percentile_score(
            50,
            values
        )
    )

    print(
        "\n=== TEST INVALID VALUES ==="
    )

    print(
        "Negative value:",
        inverse_percentile_score(
            -10,
            values
        )
    )

    print(
        "Zero value:",
        inverse_percentile_score(
            0,
            values
        )
    )

    print(
        "None value:",
        inverse_percentile_score(
            None,
            values
        )
    )


if __name__ == "__main__":

    test_normalization()