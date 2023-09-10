import logging.config
import os
from typing import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from pandas import DataFrame
from pymongo import MongoClient
from polygon import RESTClient
from dotenv import load_dotenv

from .task_base import AnalystTaskBase
from .helpers import date_window, mongo_uri
from .algo.filter import up_x_times_from_lowest
from .algo.preprocess import find_peak_and_trough

load_dotenv()

logging.config.fileConfig("logging.ini")
logger = logging.getLogger("analyst")

polygon_rest = RESTClient(os.getenv("POLYGON_API_KEY"), num_pools=100)


class ScreenerTask(AnalystTaskBase):
    TICKER_COLLECTION_NAME = "ticker"

    def __init__(
        self,
        description: str,
        params: list,
        filter_fn: Callable,
        client: MongoClient,
    ):
        """Represents a task that gets ticker names,
        filter them using the given filter function,
        and save the result to the DB.

        :param description: A description of the task.
        :param params: Parameters to query stock price move data from Polygon API
            A list of multiplier, timespan, from_, to arguments of RestClient.list_aggs
        :param filter_fn: A filtering function.
        :param client: A MongoClient instance.
        """
        super().__init__(description, client)
        self.tickers = []
        self._filter_fn = filter_fn
        self._params = params

    def single_get_and_filter(self, ticker: str):
        """Gets a single ticker chart data from Polygon API
        and apply the filter function to it.

        :param ticker: A ticker symbol.
        """
        aggregates = []
        for a in polygon_rest.list_aggs(ticker, *self._params):
            aggregates.append(vars(a))
        df = DataFrame(aggregates)
        try:
            filter_result, df = self._filter_fn(df)
        except Exception as err:
            raise Exception(
                f"Exception while applying the filter function to {ticker}"
            ) from err

        if filter_result:
            data = df.to_dict("records")
            self.ticker_collection.insert_one(
                {
                    "task_id": self.task_id,
                    "ticker": ticker,
                    "data": data,
                }
            )

    def get_tickers(self):
        """Gets a list of tickers from Polygon API."""
        for t in polygon_rest.list_tickers(type="CS", limit=1000):
            self.tickers.append(t.ticker)

    def run(self):
        """Screens the tickers with give filter function
        and save the result to the DB asynchronously."""
        logger.info("Getting tickers.")
        self.get_tickers()
        logger.info(f"Screening tickers. Total: {len(self.tickers)}")
        with ThreadPoolExecutor() as e:
            futures = []
            for t in self.tickers:
                futures.append(e.submit(self.single_get_and_filter, t))
            e.shutdown(wait=True)
            for f in futures:
                error = f.exception()
                if error:
                    logger.error(error)
        logger.info("Done.")

    @property
    def ticker_collection(self):
        db_name = ScreenerTask.DB_NAME
        ticker_collection_name = ScreenerTask.TICKER_COLLECTION_NAME
        return self._client[db_name][ticker_collection_name]


def filter_(df: DataFrame) -> tuple[bool, DataFrame]:
    """A filtering function.

    :param df: A DataFrame of a price movement data.
    :return: Whether the given DataFrame satisfies the criteria: True/False.
        And a new DataFrame preprocessed and transformed while filtering.
    """
    df = find_peak_and_trough(df)
    return up_x_times_from_lowest(df, 2.0, 20.0)


def screen() -> None:
    """Executes a screener task."""
    today = date.today().isoformat()
    window = date_window(today, 500)
    params = [1, "day", *window]
    task = ScreenerTask("Screener", params, filter_, MongoClient(mongo_uri()))
    task.mark_start()
    task.run()
    task.mark_complete()
