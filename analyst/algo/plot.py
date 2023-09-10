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

    :param df: A DataFrame of price moves.
    """
    df = df.rename(
        columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
    )
    df["Time"] = pd.to_datetime(df["timestamp"], unit="ms", origin="unix")
    df = df.set_index("Time")
    return df


def simple_plot(df: DataFrame) -> bytes:
    """Plots simple candlestick chart.

    :param df: A DataFrame of price moves.
    :return: The chart image.
    """
    df = prep_chart_dataframe(df)
    image_bytes = io.BytesIO()
    mplfinance.plot(
        df, type="candle", volume=True, savefig=image_bytes, figsize=(15, 6)
    )
    pyplot.savefig(image_bytes, format="jpg")

    return image_bytes.getvalue()
