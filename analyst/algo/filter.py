from pandas import DataFrame
import numpy as np


def latest_yoy_growth_ratio(
    df: DataFrame, col: str, threshold_pct: float
) -> tuple[bool, DataFrame]:
    """Checks if the latest year-over-year growth ratio for the specified column
    is more than or equal to the threshold.

    :param df: A DataFrame for quarterly financials.
    :param col: The target column/data name
        you want to evaluate the year-over-year growth.
    :param threshold_pct: The threshold percent in float.
        For example, 0.2 for 20%.
    :return: Whether the growth ratio is more than or equal to the threshold:
        True/False.
    """
    df = df.sort_values(by="date", ascending=True)
    col_change = f"{col}YoYChangePct"
    col_prev = f"{col}PrevYear"
    q = 4

    df[col_prev] = df[col].shift(q)
    df[col_change] = (df[col] - df[col_prev]) / abs(df[col_prev])

    filter_result = False
    if df.iloc[-1][col_change] >= threshold_pct:
        filter_result = True

    return filter_result, df


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
