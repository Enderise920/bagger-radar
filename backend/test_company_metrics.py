from sectors_client import SectorsClient


client = SectorsClient()


metrics = [
    "market_cap",
    "roe_ttm",
    "roa_ttm",
    "pe_ttm",
    "pb_mrq",
    "forward_pe",
    "yield_ttm",
    "dividend_ttm",
    "yoy_quarter_revenue_growth",
    "yoy_quarter_earnings_growth"
]


order_by = ",".join(metrics)


offsets = [
    0,
    400,
    800
]


for offset in offsets:

    print("\n===================================")
    print(f"OFFSET {offset}")
    print("===================================")

    result = client.get_companies(
        order_by=order_by,
        limit=200,
        offset=offset,
        include_query_values=True
    )

    results = result.get("results", [])

    print(
        f"Jumlah perusahaan: {len(results)}"
    )

    print("\nDATA COVERAGE")

    for metric in metrics:

        available = 0
        missing = 0

        for company in results:

            value = company.get(
                "query_values",
                {}
            ).get(metric)

            if value is None:
                missing += 1
            else:
                available += 1

        print(
            f"{metric:35} "
            f"available={available:3} "
            f"missing={missing:3}"
        )

    print("\nContoh perusahaan:")

    for company in results[:3]:

        print(
            company.get("symbol"),
            "|",
            company.get("company_name")
        )

    print("\nPagination:")

    print(
        result.get("pagination")
    )