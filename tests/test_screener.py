from pathlib import Path
import json
from copy import deepcopy

from mongomock import MongoClient

from analyst.screener import ScreenerTask
from analyst.task_base import AnalystTaskBase

snapshot_file_path = Path.cwd() / "tests/fixtures/stock_snapshot.json"
with open(snapshot_file_path, "r", encoding="utf-8") as f:
    stock_data_snapshot = json.load(f)


def pass_one(data):
    updated = deepcopy(data)
    updated["data"]["updated"] = True
    result = False
    if updated["symbol"]["symbol"] == "ONE":
        result = True
    return result, updated


class TestScreenerTask:
    def setup_method(self):
        db_name = AnalystTaskBase.DB_NAME
        stock_data_collection_name = AnalystTaskBase.STOCK_DATA_COLLECTION_NAME
        screener_collection_name = AnalystTaskBase.SCREENER_COLLECTION_NAME
        task_collection_name = AnalystTaskBase.TASK_COLLECTION_NAME
        client = MongoClient()
        self.mock_db_client = client
        self.stock_data_collection = client[db_name][stock_data_collection_name]
        self.screener_collection = client[db_name][screener_collection_name]
        self.task_collection = client[db_name][task_collection_name]
        self.dummy_task_id = "dummyTaskId"
        dummy_symbol_names = [
            {"symbol": "ONE"},
            {"symbol": "TWO"},
            {"symbol": "THREE"},
            {"symbol": "FOUR"},
        ]
        for s in dummy_symbol_names:
            copy_symbol = deepcopy(stock_data_snapshot["symbol"])
            copy_symbol["symbol"] = s["symbol"]
            self.stock_data_collection.insert_one(
                {
                    "taskId": self.dummy_task_id,
                    "symbol": copy_symbol,
                    "data": stock_data_snapshot["data"],
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
        self.mock_db_client.close()

    def test_get_symbols_list_from_db(self):
        task = ScreenerTask("TEST", self.dummy_task_id, pass_one, self.mock_db_client)
        source_symbols = task.get_symbols_list_from_db()
        assert len(source_symbols) == 4

    def test_get_stock_data_from_db(self):
        task = ScreenerTask("TEST", self.dummy_task_id, pass_one, self.mock_db_client)
        stock_data = task.get_stock_data_from_db("ONE")
        assert "data" in stock_data
        assert "symbol" in stock_data

    def test_save_filter_result(self):
        task = ScreenerTask("TEST", self.dummy_task_id, pass_one, self.mock_db_client)
        _ = [task._q_filtered_symbols.put(s) for s in ["ONE", "TWO"]]
        task.save_filter_result()
        filter_ = {"taskId": task.task_id}
        count = self.screener_collection.count_documents(filter_)
        doc = self.screener_collection.find_one(filter_)
        assert count == 1
        assert len(doc["tickerSymbols"]) == 2

    def test_single_get_and_filter(self):
        task = ScreenerTask("TEST", self.dummy_task_id, pass_one, self.mock_db_client)
        task.single_get_and_filter("ONE")
        task.single_get_and_filter("TWO")
        assert len(task.filtered_symbols) == 1
        assert task.filtered_symbols[0] == "ONE"
        one = self.stock_data_collection.find_one({"symbol.symbol": "ONE"})
        two = self.stock_data_collection.find_one({"symbol.symbol": "TWO"})
        assert one["data"]["updated"]
        assert two["data"]["updated"]

    def test_run(self):
        task = ScreenerTask("TEST", self.dummy_task_id, pass_one, self.mock_db_client)
        task.run()
        filter_ = {"taskId": task.task_id}
        count_screener = self.screener_collection.count_documents(filter_)
        doc_screener = self.screener_collection.find_one(filter_)
        doc_task = self.task_collection.find_one(filter_)
        assert count_screener == 1
        assert len(doc_screener["tickerSymbols"]) == 1
        assert doc_task["taskType"] == "screener"
