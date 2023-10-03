import json
from pathlib import Path

from mongomock import MongoClient

from analyst.server import app, mongo
from analyst.screener import ScreenerTask
from analyst.web_api import GetStockDataTask

DB_NAME = ScreenerTask.DB_NAME
TASK_COLLECTION_NAME = ScreenerTask.TASK_COLLECTION_NAME
STOCK_DATA_COLLECTION_NAME = ScreenerTask.STOCK_DATA_COLLECTION_NAME

snapshot_file_path = Path.cwd() / "tests/fixtures/stock_snapshot.json"
with open(snapshot_file_path, "r", encoding="utf-8") as f:
    stock_snapshot = json.load(f)


def pass_all(data):
    return True, data


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

        get_stock_data_task = GetStockDataTask("Test Get Data Task", self.mongo_client)
        get_stock_data_task.mark_start()
        get_stock_data_task.mark_complete()
        screener_task_complete = ScreenerTask(
            "Test Screener Task",
            get_stock_data_task.task_id,
            pass_all,
            self.mongo_client,
        )
        screener_task_complete.mark_start()
        screener_task_complete.mark_complete()
        screener_task_incomplete = ScreenerTask(
            "Test Screener Task 2",
            get_stock_data_task.task_id,
            pass_all,
            self.mongo_client,
        )
        screener_task_incomplete.mark_start()
        resp = self.app.get("/screener")
        assert resp.text.find("Test Get Data Task (complete,") > -1
        assert resp.text.find("Test Screener Task (complete,") > -1
        assert resp.text.find("Test Screener Task 2 (incomplete,") > -1

    def test_screener_result(self):
        num_per_page = 5
        num_pages = 3
        stock_data_collection = self.mongo_client[DB_NAME][STOCK_DATA_COLLECTION_NAME]
        task_id = "TEST"
        docs = []
        for i in range(0, num_pages * num_per_page):
            docs.append(
                {
                    "taskId": task_id,
                    "symbol": stock_snapshot["symbol"],
                    "data": stock_snapshot["data"],
                }
            )
        stock_data_collection.insert_many(docs)
        resp = self.app.get(f"/screener/{task_id}/1")
        assert resp.text.find("prev") == -1
        assert resp.text.find("next") > -1
        assert resp.text.count("<img") == num_per_page
        resp = self.app.get(f"/screener/{task_id}/2")
        assert resp.text.find("prev") > -1
        assert resp.text.find("next") > -1
        resp = self.app.get(f"/screener/{task_id}/3")
        assert resp.text.find("prev") > -1
        assert resp.text.find("next") == -1

    def test_simple_candlestick_chart(self):
        collection = self.mongo_client[DB_NAME][STOCK_DATA_COLLECTION_NAME]
        with open(snapshot_file_path, "r", encoding="utf-8") as f:
            stock_data_snapshot = json.load(f)
        task_id = "dummyId"
        symbol = "TEST"
        stock_data_snapshot["symbol"]["symbol"] = symbol
        collection.insert_one(
            {
                "task_id": task_id,
                "symbol": stock_data_snapshot["symbol"],
                "data": stock_data_snapshot["data"],
            }
        )

        resp = self.app.get(f"/chart/simple/{symbol}")
        assert resp.content_type == "image/jpeg"
