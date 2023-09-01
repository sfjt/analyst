import os
from pathlib import Path
from datetime import date, timedelta
import json

import dotenv

from polygon.exceptions import BadResponse
from polygon import RESTClient

dotenv.load_dotenv()

client = RESTClient(os.getenv("POLYGON_API_KEY"))


def pytest_configure():
    snapshot_file_path = Path.cwd() / "tests/fixtures/polygon_rest/aggregates.json"
    today = date.today()
    ten_days_ago = today - timedelta(days=10)
    request_params = [1, "day", ten_days_ago.isoformat(), today.isoformat()]
    snapshot = []
    if not os.path.isfile(snapshot_file_path):
        try:
            for a in client.list_aggs("AAPL", *request_params):
                snapshot.append(vars(a))
        except BadResponse:
            message = (
                "Test code will send request to Polygon API and save response to file"
                " if local snapshot does not exist."
                " Make sure a valid API key is set to .env file."
            )
            raise Exception(message)
        with open(snapshot_file_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=4)
