import logging.config
from typing import Callable
from concurrent.futures import ThreadPoolExecutor

from pymongo import MongoClient
from dotenv import load_dotenv

from .task_base import AnalystTaskBase

load_dotenv()

logging.config.fileConfig("logging.ini")
logger = logging.getLogger("analyst")


class ScreenerTask(AnalystTaskBase):
    def __init__(
        self,
        description: str,
        target_task_id: str,
        filter_fn: Callable,
        db_client: MongoClient,
    ):
        """A task filters the stock data saved in the database.

        :param description: A description of the task.
        :param target_task_id: The task id of GetStockDataTask
        or ScreenerTask.
        :param filter_fn: A filtering function.
        :param db_client: A MongoClient instance.
        """
        super().__init__(description, db_client)
        self.source_symbols = []
        self.filtered_symbols = []
        self.task_type = "screener"
        self._filter_fn = filter_fn
        self._target_task_id = target_task_id

    def single_get_and_filter(self, symbol_name: str):
        """
        :param symbol_name: A ticker symbol.
        """
        data = self.get_stock_data_from_db(symbol_name)
        try:
            filter_result, data_updated = self._filter_fn(data)
        except Exception as err:
            logger.error(
                f"Exception while applying the filter function to {symbol_name}"
            )
            logger.exception(err)
            return

        if filter_result:
            self.filtered_symbols.append(symbol_name)

    def get_stock_data_from_db(self, symbol_name: str):
        filter_ = {
            "taskId": self._target_task_id,
            "symbol.symbol": symbol_name,
        }
        return self.stock_data_collection.find_one(filter_)

    def get_symbols_list_from_db(self):
        filter_ = {"taskId": self._target_task_id}
        symbols = self.screener_collection.find_one(filter_)
        return symbols["tickerSymbols"]

    def save_filter_result(self):
        self.screener_collection.insert_one(
            {
                "taskId": self.task_id,
                "description": self.description,
                "tickerSymbols": self.filtered_symbols,
            }
        )

    def run(self):
        self.mark_start()
        logger.info("Getting ticker symbols.")
        self.source_symbols = self.get_symbols_list_from_db()
        logger.info(f"Screening tickers. Total: {len(self.source_symbols)}")
        with ThreadPoolExecutor() as e:
            futures = []
            for s in self.source_symbols:
                futures.append(e.submit(self.single_get_and_filter, s))
            e.shutdown(wait=True)
            for f in futures:
                error = f.exception()
                if error:
                    logger.error(error)
        logger.info("Saving the filter result.")
        self.save_filter_result()
        logger.info("Done.")
        self.mark_complete()
