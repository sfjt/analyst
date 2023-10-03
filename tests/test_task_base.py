from mongomock import MongoClient

from analyst.task_base import AnalystTaskBase

DB_NAME = AnalystTaskBase.DB_NAME
TASK_COLLECTION_NAME = AnalystTaskBase.TASK_COLLECTION_NAME


class TestAnalystTaskBase:
    def setup_method(self):
        self.mock_client = MongoClient()
        self.task_collection = self.mock_client[DB_NAME][TASK_COLLECTION_NAME]

    def teardown_method(self):
        self.mock_client.close()

    def test_mark_start(self):
        task = AnalystTaskBase("Test Incomplete", self.mock_client)
        task.mark_start()
        doc = self.task_collection.find_one({"taskId": task.task_id})
        assert not doc["complete"]
        assert doc["description"] == task.description
        assert doc["started"] == task.timestamp
        assert doc["ended"] is None

    def test_complete(self):
        task = AnalystTaskBase("Test Complete", self.mock_client)
        task.mark_start()
        task.mark_complete()
        doc = self.task_collection.find_one({"taskId": task.task_id})
        assert doc["complete"]
        assert doc["description"] == task.description
        assert doc["taskType"] == task.task_type
        assert doc["started"] == task.timestamp
        assert isinstance(doc["ended"], str)
