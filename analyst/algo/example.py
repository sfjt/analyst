from __future__ import annotations
import io

import pandas as pd
from pandas import DataFrame
import numpy as np
import mplfinance
import matplotlib
from matplotlib import pyplot
import dotenv

dotenv.load_dotenv()

matplotlib.use("Agg")


def find_peak_and_trough(df: DataFrame) -> DataFrame:
    """Find the local minimum and the local maximum in price move
    and add new data columns: peak and trough.

    :param df: Polygon aggregates data as a DataFrame.
    :return: A new DataFrame.
    """
    high_low_cols = ("high", "low")
    df = df.copy()
    pivots = df.loc[:, high_low_cols]
    for col in high_low_cols:
        pivots[f"{col}_diff"] = pivots[col].diff()
        pivots[f"{col}_diff_next"] = pivots[f"{col}_diff"].shift(-1)

    def find_peak(row):
        if row["high_diff_next"] < 0 < row["high_diff"]:
            return row["high"]
        else:
            return np.nan

    def find_trough(row):
        if row["low_diff"] < 0 < row["low_diff_next"]:
            return row["low"]
        else:
            return np.nan

    df["peak"] = pivots.apply(find_peak, axis=1)
    df["trough"] = pivots.apply(find_trough, axis=1)

    return df


def smoothen_peak_and_trough(df: DataFrame, threshold_pct: float) -> DataFrame:
    """Adds a smoothened pivot data columns: smooth_peak and smooth_trough.
    It will ignore (1) price moves below threshold
    and (2) consecutive peaks/troughs to smoothen data.

    :param df: Polygon aggregates data as a DataFrame.
        It must be preprocessed by the function find_peak_and_trough.
    :param threshold_pct: The price move threshold in percentage.
        For example, 0.03 for 3%.
    :return: A new DataFrame.
    """

    class Pivot:
        threshold = threshold_pct

        def __init__(self, pivot_type: str, row: int | float, price: float):
            self.type = pivot_type
            self.row = row
            self.price = price

        def is_valid(self, prev: Pivot) -> bool:
            if np.isnan(self.price):
                return False
            if prev.type == "":
                return True
            if self.type == "peak" == prev.type:
                return self.price > prev.price
            if self.type == "trough" == prev.type:
                return self.price < prev.price

            diff_pct = self.price / prev.price
            return diff_pct > 1 + self.threshold or diff_pct < 1 - self.threshold

    df = df.copy()
    peaks = df["peak"].copy()
    troughs = df["trough"].copy()
    prev_pivot = Pivot("", np.nan, np.nan)
    for i in range(0, len(df)):
        p = Pivot("peak", i, peaks.iat[i])
        if p.is_valid(prev_pivot):
            if prev_pivot.type == "peak":
                peaks.iloc[prev_pivot.row] = np.nan
            prev_pivot = p
        else:
            peaks.iloc[p.row] = np.nan

        t = Pivot("trough", i, troughs.iat[i])
        if t.is_valid(prev_pivot):
            if prev_pivot.type == "trough":
                troughs.iloc[prev_pivot.row] = np.nan
            prev_pivot = t
        else:
            troughs.iloc[t.row] = np.nan

    df["smooth_peak"] = peaks
    df["smooth_trough"] = troughs
    return df


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


def up_x_times_from_lowest(
    df: DataFrame, x: float, min_: float = -1.0
) -> tuple[bool, DataFrame]:
    """Checks if the data has an x times+ up price move.

    :param df: Polygon aggregates data as a DataFrame.
        It must be preprocessed by the function find_peak_and_trough.
    :param x: The threshold value.
    :param min_: The minimum price of price moves being evaluated.
    :return: Whether it has an x times+ up price move or not: True/False.
    """
    df = df.query("peak.notna() or trough.notna()").reset_index()
    troughs = df["trough"]
    peaks = df["peak"]
    num_records = len(df)
    for i in range(0, num_records):
        trough_price = troughs.iat[i]
        if trough_price < min_:
            continue
        if np.isnan(trough_price):
            continue
        threshold = trough_price * x
        next_i = i + 1
        if next_i >= num_records:
            break
        peaks_2x = peaks[next_i:] >= threshold
        if peaks_2x.any():
            return True, df
    return False, df
