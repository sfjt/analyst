import json
from pathlib import Path

from mongomock import MongoClient

from analyst.server import app, mongo
from analyst.screener import ScreenerTask

snapshot_file_path = Path.cwd() / "tests/fixtures/polygon_rest/aggregates.json"


def dummy_filter(df):
    return True, df.copy()


class TestServer:
    def setup_method(self):
        app.config["TESTING"] = True
        self.app = app.test_client()
        mongo.cx = MongoClient()
        self.mongo_client = mongo.cx

    def test_root(self):
        resp = self.app.get("/")
        assert resp.status == "200 OK"

    def test_screener_tasks(self):
        resp = self.app.get("/screener")
        assert resp.text.find("No tasks found.") > -1

        t1 = ScreenerTask("Test Screener 1", [], dummy_filter, self.mongo_client)
        t1.mark_start()
        t1.mark_complete()
        t2 = ScreenerTask("Test Screener 2", [], dummy_filter, self.mongo_client)
        t2.mark_start()
        t2.mark_complete()
        resp = self.app.get("/screener")
        assert resp.text.find("Test Screener 1") > -1
        assert resp.text.find("Test Screener 2") > -1

    def test_screener_result(self):
        num_limit = 5
        num_pages = 3
        db_name = ScreenerTask.DB_NAME
        ticker_collection_name = ScreenerTask.TICKER_COLLECTION_NAME
        ticker_collection = self.mongo_client[db_name][ticker_collection_name]
        with open(snapshot_file_path, "r", encoding="utf-8") as f:
            aggs_snapshot = json.load(f)
        task_id = "t1"
        for i in range(0, num_pages * num_limit):
            ticker_collection.insert_one(
                {
                    "task_id": task_id,
                    "ticker": "TEST",
                    "data": aggs_snapshot,
                }
            )

        resp = self.app.get(f"/screener/{task_id}/1")
        assert resp.text.find("prev") == -1
        assert resp.text.find("next") > -1
        assert resp.text.count("<img") == num_limit
        resp = self.app.get(f"/screener/{task_id}/2")
        assert resp.text.find("prev") > -1
        assert resp.text.find("next") > -1
        resp = self.app.get(f"/screener/{task_id}/3")
        assert resp.text.find("prev") > -1
        assert resp.text.find("next") == -1

    def test_simple_candlestick_chart(self):
        db_name = ScreenerTask.DB_NAME
        ticker_collection_name = ScreenerTask.TICKER_COLLECTION_NAME
        ticker_collection = self.mongo_client[db_name][ticker_collection_name]
        with open(snapshot_file_path, "r", encoding="utf-8") as f:
            aggs_snapshot = json.load(f)
        task_id = "t2"
        ticker = "TEST"
        ticker_collection.insert_one(
            {
                "task_id": task_id,
                "ticker": ticker,
                "data": aggs_snapshot,
            }
        )

        resp = self.app.get(f"/charts/simple/{task_id}/{ticker}")
        assert resp.content_type == "image/jpeg"
