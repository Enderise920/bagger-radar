import os
import requests
from dotenv import load_dotenv


load_dotenv()


class SectorsClient:
    BASE_URL = "https://api.sectors.app/v2"

    def __init__(self):
        self.api_key = os.getenv("SECTORS_API_KEY")

        if not self.api_key:
            raise ValueError(
                "SECTORS_API_KEY belum ditemukan di .env"
            )

        self.headers = {
            "Authorization": self.api_key
        }

    def get_companies(
        self,
        where=None,
        order_by="symbol",
        limit=50,
        offset=0,
        include_query_values=False
    ):
        """
        Mengambil daftar perusahaan dari Sectors API v2.
        """

        url = f"{self.BASE_URL}/companies/"

        params = {
            "order_by": order_by,
            "limit": limit,
            "offset": offset,
            "include_query_values": str(
                include_query_values
            ).lower()
        }

        if where:
            params["where"] = where

        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        return response.json()

    def get_company_fundamentals(
        self,
        symbol,
        metrics
    ):
        """
        Mengambil beberapa metric fundamental perusahaan
        dalam satu request Sectors API v2.
        """

        url = f"{self.BASE_URL}/companies/"

        order_by = ",".join(metrics)

        params = {
            "where": f"symbol='{symbol}'",
            "order_by": order_by,
            "limit": 1,
            "offset": 0,
            "include_query_values": "true"
        }

        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        results = data.get("results", [])

        if not results:
            return None

        result = results[0]

        query_values = result.get(
            "query_values",
            {}
        )

        return {
            "symbol": result.get("symbol"),
            "company_name": result.get("company_name"),
            **query_values
        }

    def get_daily(
        self,
        ticker,
        start=None,
        end=None
    ):
        """
        Mengambil data harga harian dari Sectors API v2.
        """

        url = f"{self.BASE_URL}/daily/{ticker}/"

        params = {}

        if start:
            params["start"] = start

        if end:
            params["end"] = end

        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        return response.json()