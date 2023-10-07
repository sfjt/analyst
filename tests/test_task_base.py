from mongomock import MongoClient

from analyst.task_base import AnalystTaskBase


class TestAnalystTaskBase:
    def setup_method(self):
        db_name = AnalystTaskBase.DB_NAME
        task_collection_name = AnalystTaskBase.TASK_COLLECTION_NAME
        client = MongoClient()
        self.mock_db_client = client
        self.task_collection = client[db_name][task_collection_name]

    def test_mark_start(self):
        task = AnalystTaskBase("Test Incomplete", self.mock_db_client)
        task.mark_start()
        doc = self.task_collection.find_one({"taskId": task.task_id})
        assert not doc["complete"]
        assert doc["description"] == task.description
        assert doc["started"] == task.timestamp
        assert doc["ended"] is None

    def test_complete(self):
        task = AnalystTaskBase("Test Complete", self.mock_db_client)
        task.mark_start()
        task.mark_complete()
        doc = self.task_collection.find_one({"taskId": task.task_id})
        assert doc["complete"]
        assert doc["description"] == task.description
        assert doc["taskType"] == task.task_type
        assert doc["started"] == task.timestamp
        assert isinstance(doc["ended"], str)
