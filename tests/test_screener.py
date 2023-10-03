from pathlib import Path
import json
from copy import deepcopy

from mongomock import MongoClient

from analyst.screener import ScreenerTask

DB_NAME = ScreenerTask.DB_NAME
STOCK_DATA_COLLECTION_NAME = ScreenerTask.STOCK_DATA_COLLECTION_NAME
SCREENER_COLLECTION_NAME = ScreenerTask.SCREENER_COLLECTION_NAME
TASK_COLLECTION_NAME = ScreenerTask.TASK_COLLECTION_NAME

snapshot_file_path = Path.cwd() / "tests/fixtures/stock_snapshot.json"
with open(snapshot_file_path, "r", encoding="utf-8") as f:
    stock_snapshot = json.load(f)


def pass_one(data):
    if data["symbol"]["symbol"] == "ONE":
        data_updated = deepcopy(data)
        data_updated["updated"] = True
        return True, data_updated
    return False, None


class TestScreenerTask:
    def setup_method(self):
        client = MongoClient()
        self.mock_client = client
        self.stock_data_collection = client[DB_NAME][STOCK_DATA_COLLECTION_NAME]
        self.screener_collection = client[DB_NAME][SCREENER_COLLECTION_NAME]
        self.task_collection = client[DB_NAME][TASK_COLLECTION_NAME]
        self.dummy_task_id = "dummyTaskId"
        dummy_symbol_names = [
            {"symbol": "ONE"},
            {"symbol": "TWO"},
            {"symbol": "THREE"},
            {"symbol": "FOUR"},
        ]
        for s in dummy_symbol_names:
            copy_symbol = deepcopy(stock_snapshot["symbol"])
            copy_symbol["symbol"] = s["symbol"]
            self.stock_data_collection.insert_one(
                {
                    "taskId": self.dummy_task_id,
                    "symbol": copy_symbol,
                    "data": stock_snapshot["data"],
                }
            )
        self.screener_collection.insert_one(
            {
                "taskId": self.dummy_task_id,
                "description": "SOURCE",
                "tickerSymbols": [s["symbol"] for s in dummy_symbol_names],
            }
        )

    def teardown_method(self):
        self.mock_client.close()

    def test_get_symbols_list_from_db(self):
        task = ScreenerTask("TEST", self.dummy_task_id, pass_one, self.mock_client)
        source_symbols = task.get_symbols_list_from_db()
        assert len(source_symbols) == 4

    def test_get_stock_data_from_db(self):
        task = ScreenerTask("TEST", self.dummy_task_id, pass_one, self.mock_client)
        stock_data = task.get_stock_data_from_db("ONE")
        assert "data" in stock_data
        assert "symbol" in stock_data

    def test_save_filter_result(self):
        task = ScreenerTask("TEST", self.dummy_task_id, pass_one, self.mock_client)
        task.filtered_symbols = ["ONE", "TWO"]
        task.save_filter_result()
        filter_ = {"taskId": task.task_id}
        count = self.screener_collection.count_documents(filter_)
        doc = self.screener_collection.find_one(filter_)
        assert count == 1
        assert len(doc["tickerSymbols"]) == 2

    def test_single_get_and_filter(self):
        task = ScreenerTask("TEST", self.dummy_task_id, pass_one, self.mock_client)
        task.single_get_and_filter("ONE")
        task.single_get_and_filter("TWO")
        assert len(task.filtered_symbols) == 1
        assert task.filtered_symbols[0] == "ONE"

    def test_run(self):
        task = ScreenerTask("TEST", self.dummy_task_id, pass_one, self.mock_client)
        task.run()
        filter_ = {"taskId": task.task_id}
        count_screener = self.screener_collection.count_documents(filter_)
        doc_screener = self.screener_collection.find_one(filter_)
        doc_task = self.task_collection.find_one(filter_)
        assert count_screener == 1
        assert len(doc_screener["tickerSymbols"]) == 1
        assert doc_task["taskType"] == "screener"
