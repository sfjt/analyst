from pathlib import Path
import json

import pytest
from mongomock import MongoClient
from requests import HTTPError

from analyst.web_api import (
    GetStockDataTask,
    get,
    get_ticker_symbols,
    get_daily_prices,
    get_financial_statements,
    preprocess_financials,
    NoDataError,
    API_KEY,
)
from analyst.task_base import AnalystTaskBase

snapshot_file_path = Path.cwd() / "tests/fixtures/stock_snapshot.json"
with open(snapshot_file_path, "r", encoding="utf-8") as f:
    stock_snapshot = json.load(f)

mock_financials_quarter = stock_snapshot["data"]["financial_statements"]["quarter"]
mock_daily_prices = stock_snapshot["data"]["prices"]
mock_ticker_symbols = [
    {"symbol": "AMEX", "type": "stock", "exchange": "American Stock Exchange"},
    {"symbol": "T1", "type": "trust"},
    {"symbol": "NASDAQ", "type": "stock", "exchange": "NASDAQ Capital Market"},
    {"symbol": "NASDAQ2", "type": "stock", "exchange": "NASDAQ Global Market"},
    {"symbol": "NYSE", "type": "stock", "exchange": "New York Stock Exchange Arca"},
    {"symbol": "S2", "type": "stock", "exchange": "London Stock Exchange"},
    {"symbol": "E1", "type": "etf"},
]
mock_filtered_ticker_symbols = [
    {"symbol": "AMEX", "type": "stock", "exchange": "American Stock Exchange"},
    {"symbol": "NASDAQ", "type": "stock", "exchange": "NASDAQ Global Market"},
    {"symbol": "NASDAQ2", "type": "stock", "exchange": "Nasdaq capital Market"},
    {"symbol": "NYSE", "type": "stock", "exchange": "New York Stock Exchange Arca"},
]


def mock_response(data: dict | list, status_code: int):
    class MockResponse:
        def __init__(self, data_: dict | list, status_code_: int):
            self.data = data_
            self.status_code = status_code_

        def json(self):
            return self.data

        def raise_for_status(self):
            if 200 <= self.status_code < 300:
                return
            raise HTTPError(f"TEST ERROR: {self.status_code}")

    return MockResponse(data, status_code)


class TestGetStockDataTask:
    def setup_method(self):
        client = MongoClient()
        self.mock_db_client = client
        db_name = AnalystTaskBase.DB_NAME
        task_collection_name = AnalystTaskBase.TASK_COLLECTION_NAME
        stock_data_collection_name = AnalystTaskBase.STOCK_DATA_COLLECTION_NAME
        screener_collection_name = AnalystTaskBase.SCREENER_COLLECTION_NAME
        self.task_collection = client[db_name][task_collection_name]
        self.stock_data_collection = client[db_name][stock_data_collection_name]
        self.screener_collection = client[db_name][screener_collection_name]

    def teardown_method(self):
        self.mock_db_client.close()

    def test_get_single_stock_data_and_save(self, mocker):
        mocker.patch(
            "analyst.web_api.get_financial_statements",
            return_value=mock_financials_quarter,
        )
        mocker.patch("analyst.web_api.get_daily_prices", return_value=mock_daily_prices)
        task = GetStockDataTask("TEST", self.mock_db_client)
        task.get_single_stock_data_and_save({"symbol": "TEST"})
        filter_ = {"symbol.symbol": "TEST"}
        count = self.stock_data_collection.count_documents(filter_)
        assert count == 1

    def test_save_ticker_symbol_names(self):
        task = GetStockDataTask("TEST", self.mock_db_client)
        task.save_ticker_symbol_names(mock_filtered_ticker_symbols)
        filter_ = {"taskId": task.task_id}
        count = self.screener_collection.count_documents(filter_)
        doc = self.screener_collection.find_one(filter_)
        assert count == 1
        assert len(doc["tickerSymbols"]) == len(mock_filtered_ticker_symbols)

    def test_run(self, mocker):
        mocker.patch(
            "analyst.web_api.get_ticker_symbols",
            return_value=mock_filtered_ticker_symbols,
        )
        mocker.patch(
            "analyst.web_api.get_financial_statements",
            return_value=mock_financials_quarter,
        )
        mocker.patch("analyst.web_api.get_daily_prices", return_value=mock_daily_prices)
        task = GetStockDataTask("TEST", self.mock_db_client)
        task.run()
        filter_ = {"taskId": task.task_id}
        count_stock_data = self.stock_data_collection.count_documents(filter_)
        count_screener = self.screener_collection.count_documents(filter_)
        doc_task = self.task_collection.find_one(filter_)
        assert count_stock_data == 4
        assert count_screener == 1
        assert doc_task["taskType"] == "get_stock_data"


class TestGet:
    def test_get_success(self, mocker):
        m = mocker.patch(
            "requests.Session.get", return_value=mock_response(mock_daily_prices, 200)
        )
        data = get(
            "https://financialmodelingprep.com/api/v3/historical-price-full/TEST",
            {"test": "test"},
        )
        m.assert_called_once_with(
            "https://financialmodelingprep.com/api/v3/historical-price-full/TEST",
            params={"apikey": API_KEY, "test": "test"},
        )
        assert type(data) is dict

    def test_det_daily_prices_no_data_error(self, mocker):
        mocker.patch("requests.Session.get", return_value=mock_response([], 200))
        url = "https://financialmodelingprep.com/api/v3/historical-price-full/TEST"
        with pytest.raises(NoDataError) as e:
            get("https://financialmodelingprep.com/api/v3/historical-price-full/TEST")
        assert str(e.value) == f"No data returned: {url}"


class TestGetDailyPrices:
    def test_det_daily_prices_success_default(self, mocker):
        m = mocker.patch("analyst.web_api.get", return_value=mock_daily_prices)
        prices = get_daily_prices("TEST")
        m.assert_called_once_with(
            "https://financialmodelingprep.com/api/v3/historical-price-full/TEST",
            {},
        )
        assert type(prices) is dict

    def test_det_daily_prices_success(self, mocker):
        m = mocker.patch("analyst.web_api.get", return_value=mock_daily_prices)
        prices = get_daily_prices("TEST", "2023-01-01", "2023-01-02")
        m.assert_called_once_with(
            "https://financialmodelingprep.com/api/v3/historical-price-full/TEST",
            {"from": "2023-01-01", "to": "2023-01-02"},
        )
        assert type(prices) is dict

    def test_det_daily_prices_http_error(self, mocker):
        mocker.patch("analyst.web_api.get", side_effect=HTTPError("TEST"))
        prices = get_daily_prices("TEST", "2023-01-01", "2023-01-02")
        assert prices is None

    def test_det_daily_prices_no_data_error(self, mocker):
        mocker.patch("requests.Session.get", return_value=mock_response([], 200))
        prices = get_daily_prices("TEST", "2023-01-01", "2023-01-02")
        assert prices is None


class TestGetFinancialStatements:
    def test_det_daily_prices_success_default(self, mocker):
        m = mocker.patch("analyst.web_api.get", return_value=mock_financials_quarter)
        financials = get_financial_statements("TEST")
        m.assert_called_once_with(
            "https://financialmodelingprep.com/api/v3/income-statement/TEST",
            {"limit": 10, "period": "quarter"},
        )
        assert type(financials) is list

    def test_det_daily_prices_success(self, mocker):
        m = mocker.patch("analyst.web_api.get", return_value=mock_financials_quarter)
        financials = get_financial_statements("TEST", 20, "annual")
        m.assert_called_once_with(
            "https://financialmodelingprep.com/api/v3/income-statement/TEST",
            {"limit": 20, "period": "annual"},
        )
        assert type(financials) is list

    def test_det_daily_prices_http_error(self, mocker):
        mocker.patch("analyst.web_api.get", side_effect=HTTPError("TEST"))
        financials = get_financial_statements("TEST")
        assert financials is None

    def test_det_daily_prices_no_data_error(self, mocker):
        mocker.patch("requests.Session.get", return_value=mock_response([], 200))
        financials = get_financial_statements("TEST")
        assert financials is None


def test_get_ticker_symbols(mocker):
    mocker.patch("requests.get", return_value=mock_response(mock_ticker_symbols, 200))
    sym = get_ticker_symbols()
    assert len(sym) == 4
    assert [s["symbol"] for s in sym] == ["AMEX", "NASDAQ", "NASDAQ2", "NYSE"]


def test_preprocess_financials():
    financial_statements = stock_snapshot["data"]["financial_statements"]["quarter"]
    preprocessed = preprocess_financials(financial_statements)
    assert "revenueYoYChange" in preprocessed[-1]
    assert "epsdilutedYoYChange" in preprocessed[-1]
    assert "netIncomeYoYChange" in preprocessed[-1]
