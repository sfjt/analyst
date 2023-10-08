import re

import pytest

from analyst.helpers import mongo_uri, date_window


def test_uri():
    uri = mongo_uri()
    assert re.fullmatch(r"mongodb://.+:.+@.+:[0-9]+/.+", uri)


@pytest.mark.parametrize(
    "args,expected",
    [
        [("2020-10-10", 365), ("2019-10-11", "2020-10-10")],
        [("2020-10-10", 0), ("2020-10-10", "2020-10-10")],
        [("2020-10-10", -1), ("2020-10-11", "2020-10-10")],
        [("2024-03-01", 1), ("2024-02-29", "2024-03-01")],
    ],
)
def test_date_window(args, expected):
    assert date_window(*args) == expected
