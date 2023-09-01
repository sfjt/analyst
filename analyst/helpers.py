import os
from datetime import date, timedelta

from dotenv import load_dotenv

load_dotenv()


def mongo_uri() -> str:
    """Generates a Mongo DB connection string in the URI format.

    :return: A connection string URI.
    """
    host = os.getenv("MONGO_HOST")
    port = int(os.getenv("MONGO_PORT"))
    username = os.getenv("MONGO_USERNAME")
    password = os.getenv("MONGO_PASSWORD")
    return f"mongodb://{username}:{password}@{host}:{port}"


def date_window(close_date_iso: str, n_days: int) -> tuple[str, str]:
    """Opening and closing dates of a time window.
    The opening date will be n_days before close_date_iso.

    :param close_date_iso: The date where the window closes, in ISO format.
    :param n_days: The length of the window, days.
    :return: A tuple of the starting and closing dates of the window.
    """
    close_date = date.fromisoformat(close_date_iso)
    open_date = close_date - timedelta(days=n_days)
    return open_date.isoformat(), close_date.isoformat()
