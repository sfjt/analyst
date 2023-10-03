import io

import pandas as pd
from pandas import DataFrame
import mplfinance
import matplotlib
from matplotlib import pyplot

matplotlib.use("Agg")


def prep_chart_dataframe(df: DataFrame) -> DataFrame:
    """Update column names and the index of a DataFrame
    so mplfinance can plot a candlestick chart.

    :param df: A Dataframe of historical price moves.
    """
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    df = df.sort_index(ascending=True)
    return df


def simple_plot(df: DataFrame, days: int, w: int, h: int) -> bytes:
    """Plots simple candlestick chart.

    :param df: A DataFrame of price moves.
    :param days: Days to display.
    :param w: The figsize width.
    :param h: The figsize height.
    :return: The chart image.
    """
    df = prep_chart_dataframe(df)
    idx = -1 * days
    df = df[idx:]
    image_bytes = io.BytesIO()
    mplfinance.plot(df, type="candle", volume=True, savefig=image_bytes, figsize=(w, h))
    pyplot.savefig(image_bytes, format="jpg")
    return image_bytes.getvalue()
