from pathlib import Path
import json

from mongomock import MongoClient

from analyst.screener import ScreenerTask

DB_NAME = ScreenerTask.DB_NAME
TICKER_COLLECTION_NAME = ScreenerTask.TICKER_COLLECTION_NAME


def return_true(df):
    return True, df


def return_false(df):
    return False, df


class DummyTicker:
    def __init__(self, ticker: str):
        self.ticker = ticker


class DummyAgg:
    def __init__(self, data: dict):
        self.high = data["high"]
        self.low = data["low"]
        self.timestamp = data["timestamp"]


class TestScreenerTask:
    def setup_method(self):
        self.mock_client = MongoClient()
        self.ticker_collection = self.mock_client[DB_NAME][TICKER_COLLECTION_NAME]
        self.snapshot_file_path = (
            Path.cwd() / "tests/fixtures/polygon_rest/aggregates.json"
        )
        self.dummy_tickers = [
            DummyTicker("A"),
            DummyTicker("B"),
            DummyTicker("C"),
        ]

        self.dummy_aggs = []
        with open(self.snapshot_file_path, "r", encoding="utf-8") as f:
            aggs_snapshot = json.load(f)
        for a in aggs_snapshot:
            self.dummy_aggs.append(DummyAgg(a))

    def teardown_method(self):
        self.mock_client.close()

    def test_single_get_and_filter_true(self, mocker):
        mocker.patch(
            "analyst.screener.polygon_rest.list_aggs", return_value=self.dummy_aggs
        )
        task = ScreenerTask("Filter Tickers", [], return_true, self.mock_client)
        task.single_get_and_filter("A")
        filter_ = {"task_id": task.task_id}
        count = self.ticker_collection.count_documents(filter_)
        assert count == 1

    def test_single_get_and_filter_false(self, mocker):
        mocker.patch(
            "analyst.screener.polygon_rest.list_aggs", return_value=self.dummy_aggs
        )
        task = ScreenerTask("Filter Tickers", [], return_false, self.mock_client)
        task.single_get_and_filter("B")
        filter_ = {"task_id": task.task_id}
        count = self.ticker_collection.count_documents(filter_)
        assert count == 0

    def test_get_tickers(self, mocker):
        mocker.patch(
            "analyst.screener.polygon_rest.list_tickers",
            return_value=self.dummy_tickers,
        )
        task = ScreenerTask("Filter Tickers", [], return_true, self.mock_client)
        task.get_tickers()
        for t in self.dummy_tickers:
            assert t.ticker in task.tickers

    def test_run_success(self, mocker):
        mocker.patch(
            "analyst.screener.polygon_rest.list_tickers",
            return_value=self.dummy_tickers,
        )
        mocker.patch(
            "analyst.screener.polygon_rest.list_aggs", return_value=self.dummy_aggs
        )
        task = ScreenerTask("Filter Tickers", [], return_true, self.mock_client)
        task.run()
        filter_ = {"task_id": task.task_id}
        count = self.ticker_collection.count_documents(filter_)
        assert count == 3
