import logging.config
from typing import Callable
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from copy import deepcopy

from pymongo import MongoClient
from dotenv import load_dotenv
from pandas import DataFrame

from .task_base import AnalystTaskBase
from .helpers import mongo_uri
from .algo.filter import latest_yoy_growth_ratio

load_dotenv()

logging.config.fileConfig("logging.ini")
logger = logging.getLogger("analyst")


class ScreenerTask(AnalystTaskBase):
    TASK_TYPE = "screener"

    def __init__(
        self,
        description: str,
        target_task_id: str,
        filter_fn: Callable,
        db_client: MongoClient,
    ):
        """A task filters the stock data saved in the database.
        [Side Effect] It will update the source stock data on running.

        :param description: A description of the task.
        :param target_task_id: The task id of a ScreenerTask.
        :param filter_fn: A filtering function.
        :param db_client: A MongoClient instance.
        """
        super().__init__(description, db_client)
        self.source_symbols = []
        self._q_filtered_symbols = Queue()
        self._filter_fn = filter_fn
        self._target_task_id = target_task_id

    @property
    def task_type(self):
        return ScreenerTask.TASK_TYPE

    @property
    def filtered_symbols(self):
        return list(self._q_filtered_symbols.queue)

    def single_get_and_filter(self, symbol_name: str):
        """Gets a single stock data from the database
        and applies filter_fn.
        Then saves the symbol name to self.filtered_symbols list
        if it matches the given criteria.

        :param symbol_name: A ticker symbol.
        """
        data = self.get_stock_data_from_db(symbol_name)
        try:
            filter_result, updated = self._filter_fn(data)
        except Exception as err:
            logger.error(
                f"Exception while applying the filter function to {symbol_name}"
            )
            logger.exception(err)
            return
        filter_ = {
            "taskId": self._target_task_id,
            "symbol.symbol": symbol_name,
        }
        self.stock_data_collection.update_one(
            filter_, {"$set": {"data": updated["data"]}}
        )
        if filter_result:
            self._q_filtered_symbols.put(symbol_name)

    def get_stock_data_from_db(self, symbol_name: str) -> dict:
        """Gets a single stock data from the database.

        :param symbol_name: A ticker symbol name.
        """
        filter_ = {
            "taskId": self._target_task_id,
            "symbol.symbol": symbol_name,
        }
        return self.stock_data_collection.find_one(filter_)

    def get_symbols_list_from_db(self) -> list[str]:
        """Gets a ticker symbols lisf of a preceding
        screener task (target_task_id).
        """
        filter_ = {"taskId": self._target_task_id}
        symbols = self.screener_collection.find_one(filter_)
        return symbols["tickerSymbols"]

    def save_filter_result(self):
        """Saves the filter result (self.filtered_symbols) to the database."""
        self.screener_collection.insert_one(
            {
                "taskId": self.task_id,
                "tickerSymbols": self.filtered_symbols,
            }
        )

    def run(self):
        """Gets a target ticker symbols list from a preceding screener task
        then apply filter_fn to the stock data stored in the database.
        Requires the GetStockDataTask result saved in the database.
        """
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


def run_screener_task(args):
    """Runs a screener task"""

    def fn(data):
        q_financials = data["data"]["financial_statements"]["quarter"]
        df = DataFrame.from_records(q_financials)
        filter_result, updated_df = latest_yoy_growth_ratio(df, "epsdiluted", 0.2)
        updated = deepcopy(data)
        updated["data"]["financial_statements"]["quarter"] = updated_df.to_dict(
            "records"
        )
        return filter_result, updated

    with MongoClient(mongo_uri()) as mongo_client:
        task = ScreenerTask("Screener", args.target_task_id, fn, mongo_client)
        task.run()
        logger.info(f"Complete. Task ID: {task.task_id}")
