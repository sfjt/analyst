import os
from datetime import date
from logging import getLogger
from concurrent.futures import ThreadPoolExecutor
from time import sleep

from pymongo import MongoClient
import requests
from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import HTTPError
import dotenv
from pandas import DataFrame

from analyst.task_base import AnalystTaskBase
from analyst.helpers import date_window, mongo_uri

dotenv.load_dotenv()

API_KEY = os.getenv("API_KEY")
BASE_URL = "https://financialmodelingprep.com/api/v3/"
REQUEST_PER_MINUTE = 300

logger = getLogger("analyst")


class GetStockDataTask(AnalystTaskBase):
    TASK_TYPE = "get_stock_data"
    REQUESTS_PER_SYMBOL = 2
    RATE_LIMIT_BUFFER = 10
    DELAY_PER_SYMBOL = 0.2
    DELAY_PER_BATCH = 60

    def __init__(self, description: str, db_client: MongoClient):
        """A task gets all available stock data from the web API.

        :param description: A description of the task.
        :param db_client: A MongoClient instance.
        """
        super().__init__(description, db_client)
        self.symbols = []

    @property
    def task_type(self):
        return GetStockDataTask.TASK_TYPE

    def get_single_stock_data_and_save(self, symbol: dict):
        """Get a single stock data and save it to the database.
        Quarterly financial statements and daily OHLC(+V) prices.

        :param symbol: A ticker symbol information.
        """
        num_quarters = 4
        symbol_name = symbol["symbol"]
        financials_quarter = get_financial_statements(
            symbol_name, limit=num_quarters * 2, period="quarter"
        )
        if financials_quarter is None:
            return
        financials_quarter = preprocess_financials(financials_quarter)
        from_, to = date_window(date.today().isoformat(), 365)
        prices = get_daily_prices(symbol_name, from_, to)
        if prices is None:
            return
        data = {
            "financial_statements": {"quarter": financials_quarter},
            "prices": prices,
        }
        self.stock_data_collection.insert_one(
            {"taskId": self.task_id, "symbol": symbol, "data": data}
        )

    def save_to_screener_collection(self):
        filter_ = {"taskId": self.task_id}
        project = {"symbol": 1}
        cursor = self.stock_data_collection.find(filter_, project)
        symbol_names = []
        for s in cursor:
            symbol_names.append(s["symbol"]["symbol"])
        self.screener_collection.insert_one(
            {
                "taskId": self.task_id,
                "tickerSymbols": symbol_names,
            }
        )

    def run(self, min_price: float):
        """Get US stock ticker symbols and data
        And save it to the database.
        Also saves the list of the ticker symbols
        as a screener result (without filtering)
        so following ScreenerTask can refer to it.

        :param min_price: The minimum price threshold.
        """
        logger.info("A GetStockDataTask started.")
        self.mark_start()

        logger.info("Getting a list of stock ticker symbols.")
        symbols = get_ticker_symbols(min_price)
        logger.info(f"{len(symbols)} symbols.")

        requests_per_symbol = GetStockDataTask.REQUESTS_PER_SYMBOL
        buffer = GetStockDataTask.RATE_LIMIT_BUFFER
        batch_size = (REQUEST_PER_MINUTE - buffer) // requests_per_symbol
        logger.info("Getting stock data.")
        batch_count = 0
        while True:
            batch_count += 1
            symbol_count_from = (batch_count - 1) * batch_size + 1
            symbol_count_to = batch_count * batch_size
            logger.info(
                f"Batch #{batch_count}: {symbol_count_from} - {symbol_count_to}"
            )
            with ThreadPoolExecutor() as e:
                futures = []
                for _ in range(batch_size):
                    try:
                        s = symbols.pop()
                        futures.append(e.submit(self.get_single_stock_data_and_save, s))
                        # It seems the FMP API has an undocumented burst limit.
                        # Added slight delay to avoid the 429 error
                        sleep(GetStockDataTask.DELAY_PER_SYMBOL)
                    except IndexError:
                        # synbols is empty.
                        break
                e.shutdown(wait=True)
            if len(symbols):
                sleep(GetStockDataTask.DELAY_PER_BATCH)
            else:
                break

        logger.info("Saving symbol names that returned valid data.")
        self.save_to_screener_collection()

        logger.info("Done.")
        self.mark_complete()


def get(url: str, params: dict = {}):
    """Get data from the Financial Modeling Prep API.
    https://site.financialmodelingprep.com/developer/docs/

    :param url: The API endpoint URL.
    :param params: Query parameters as a dict.
    :return: The response data as a Dataframe.
    """
    session = requests.session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    params = {
        "apikey": API_KEY,
        **params,
    }
    response = session.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    if not data:
        # The FMP API returns [] with status code 200 if no data.
        raise NoDataError(f"No data returned: {url}")
    return data


def get_financial_statements(symbol: str, limit: int = 10, period: str = "quarter"):
    """https://site.financialmodelingprep.com/developer/docs/#Company-Financial-Statements

    :param symbol: The ticker symbol.
    :param limit: The number of records to request. Defaults to 10.
    :param period: quarter or annual. Defaults to quarter.
    :return: The financial statements as a DataFrame.
    """
    url = f"{BASE_URL}income-statement/{symbol}"
    params = {
        "limit": limit,
        "period": period,
    }
    try:
        return get(url, params)
    except HTTPError as err:
        logger.error(f"Error while getting income statements: {symbol}")
        logger.exception(err)
        return None
    except NoDataError:
        logger.debug(f"No income statement data: {symbol}")
        return None


def get_daily_prices(symbol: str, from_: str = "", to: str = ""):
    """https://site.financialmodelingprep.com/developer/docs/#Stock-Historical-Price

    :param symbol:  The ticker symbol.
    :param from_: An ISO formatted date (YYYY-MM-DD) where the data starts from.
    :param to: An ISO formatted date (YYYY-MM-DD) where the data ends.
    :return: Historical daily stock prices in a Dataframe.
    """
    url = f"{BASE_URL}historical-price-full/{symbol}"
    params = {}
    if from_:
        params["from"] = from_
    if to:
        params["to"] = to
    try:
        return get(url, params)
    except HTTPError as err:
        logger.error(f"Error while getting historical daily stock prices: {symbol}")
        logger.exception(err)
        return None
    except NoDataError:
        logger.debug(f"No historical daily stock data: {symbol}")
        return None


def get_ticker_symbols(min_price: float) -> list[dict]:
    """https://site.financialmodelingprep.com/developer/docs/#Symbols-List

    :param min_price: The minimum price threshold.

    :return: Get US stock ticker symbols.
    """
    url = f"{BASE_URL}stock/list"
    params = {
        "apikey": API_KEY,
    }
    response = requests.get(url, params)
    response.raise_for_status()
    symbols = response.json()

    def filter_stocks(s: dict):
        if not s["type"] == "stock":
            return False
        exchange_name = s["exchange"].lower()
        is_us_stock = (
            exchange_name.startswith("american stock exchange")
            or exchange_name.startswith("nasdaq")
            or exchange_name.startswith("new york stock exchange")
        )
        return is_us_stock and s["price"] >= min_price

    us_stocks = filter(filter_stocks, symbols)
    return list(us_stocks)


def run_get_stock_data_task():
    """Run a single GetStockDataTask."""
    min_price = 20
    with MongoClient(mongo_uri()) as mongo_client:
        task = GetStockDataTask("Get Stock Data", mongo_client)
        logger.info("Dropping existing stock data.")
        task.stock_data_collection.drop()
        task.run(min_price)
        logger.info(f"Complete. Task ID: {task.task_id}")


def preprocess_financials(financials_quarter: dict):
    q_df = DataFrame.from_dict(financials_quarter)
    q_df = q_df.sort_values(by="date", ascending=True)
    target_cols = ["revenue", "netIncome", "epsdiluted"]
    for col in target_cols:
        q_df[col + "YoYChange"] = q_df[col].pct_change(4)
    return q_df.to_dict("records")


class NoDataError(Exception):
    pass
