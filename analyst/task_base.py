from datetime import datetime
from uuid import uuid4

from pymongo import MongoClient
from bson import ObjectId


class AnalystTaskBase:
    DB_NAME = "polygon"
    TASK_COLLECTION_NAME = "tasks"

    def __init__(self, description: str, client: MongoClient):
        """Represents a batch of time-consuming tasks.

        :param client: A MongoClient where a PolygonTask instance saves its task status.
        """
        self.task_id = str(uuid4())
        self.timestamp = datetime.now().isoformat()
        self._client = client
        self.description = description
        self.document_id: None | ObjectId = None

    @property
    def task_collection(self):
        db_name = AnalystTaskBase.DB_NAME
        task_collection_name = AnalystTaskBase.TASK_COLLECTION_NAME
        return self._client[db_name][task_collection_name]

    def mark_start(self):
        """Starts a task and saves its status to the DB."""
        inserted = self.task_collection.insert_one(
            {
                "task_id": self.task_id,
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
