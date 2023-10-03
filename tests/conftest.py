import os
from pathlib import Path
from datetime import date, timedelta
import json

import requests

from analyst.web_api import API_KEY


def pytest_configure():
    snapshot_file_path = Path.cwd() / "tests/fixtures/stock_snapshot.json"
    if os.path.isfile(snapshot_file_path):
        return

    r = requests.get(
        "https://financialmodelingprep.com/api/v3/income-statement/AAPL",
        {"apikey": API_KEY, "period": "quarter", "limit": 10},
    )
    financials_quarter = r.json()
    if type(financials_quarter) is dict and financials_quarter["Error Message"]:
        message = (
            "Test code will send request to Polygon API and save response to file"
            " if local snapshot does not exist."
            " Make sure a valid API key is set to .env file."
        )
        raise Exception(message)

    today = date.today()
    ten_days_ago = today - timedelta(days=10)
    r = requests.get(
        "https://financialmodelingprep.com/api/v3/historical-price-full/AAPL",
        {
            "apikey": API_KEY,
            "from": ten_days_ago.isoformat(),
            "to": today.isoformat(),
        },
    )
    prices = r.json()

    r = requests.get(
        "https://financialmodelingprep.com/api/v3/stock/list",
        {
            "apikey": API_KEY,
        },
    )
    symbols = r.json()
    symbol = [s for s in symbols if s["symbol"] == "AAPL"]

    snapshot = {
        "symbol": symbol[0],
        "data": {
            "financial_statements": {"quarter": financials_quarter},
            "prices": prices,
        },
    }
    with open(snapshot_file_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=4)


pytest_configure()
