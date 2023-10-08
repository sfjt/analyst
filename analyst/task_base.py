import os
from datetime import datetime
from uuid import uuid4

from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()


class AnalystTaskBase:
    TASK_TYPE = "task_base"
    DB_NAME = os.getenv("DB_NAME")
    TASK_COLLECTION_NAME = "tasks"
    STOCK_DATA_COLLECTION_NAME = "stockdata"
    SCREENER_COLLECTION_NAME = "screener"

    def __init__(self, description: str, db_client: MongoClient):
        """Represents a time-consuming task.

        :param db_client: A MongoClient where a task instance saves its status.
        """
        self.task_id = str(uuid4())
        self.timestamp = datetime.now().isoformat()
        self._db_client = db_client
        self.description = description
        self.document_id: None | ObjectId = None

    @property
    def task_type(self):
        return AnalystTaskBase.TASK_TYPE

    @property
    def task_collection(self):
        collection_name = AnalystTaskBase.TASK_COLLECTION_NAME
        return self._get_collection(collection_name)

    @property
    def stock_data_collection(self):
        collection_name = AnalystTaskBase.STOCK_DATA_COLLECTION_NAME
        return self._get_collection(collection_name)

    @property
    def screener_collection(self):
        collection_name = AnalystTaskBase.SCREENER_COLLECTION_NAME
        return self._get_collection(collection_name)

    def _get_collection(self, collection_name: str):
        db_name = AnalystTaskBase.DB_NAME
        return self._db_client[db_name][collection_name]

    def mark_start(self):
        """Starts a task and saves its status to the DB."""
        inserted = self.task_collection.insert_one(
            {
                "taskId": self.task_id,
                "taskType": self.task_type,
                "started": self.timestamp,
                "ended": None,
                "description": self.description,
                "complete": False,
            }
        )
        self.document_id = inserted.inserted_id

    def mark_complete(self):
        """Updates the task status in the DB, setting the complete field to True."""
        self.task_collection.update_one(
            {"_id": self.document_id},
            {"$set": {"complete": True, "ended": datetime.now().isoformat()}},
        )

    def run(self):
        pass
