"""Clean prices and add indicators, computed separately for each ticker."""
import numpy as np
import pandas as pd

TRADING_DAYS = 252


def clean(df):
    """Drop duplicate dates and rows with missing or non-positive prices."""
    df = df.drop_duplicates(subset=["ticker", "date"], keep="last")
    price_cols = ["open", "high", "low", "close"]
    df = df.dropna(subset=price_cols)
    df = df[(df[price_cols] > 0).all(axis=1)]
    return df.sort_values(["ticker", "date"]).reset_index(drop=True)


def add_indicators(df, short_window=20, long_window=50, vol_window=20):
    df = clean(df)
    g = df.groupby("ticker", group_keys=False)["close"]
    df["daily_return"] = g.pct_change()
    df[f"sma_{short_window}"] = g.transform(lambda s: s.rolling(short_window).mean())
    df[f"sma_{long_window}"] = g.transform(lambda s: s.rolling(long_window).mean())
    # Annualized volatility of daily returns over the window.
    df[f"volatility_{vol_window}d"] = (
        df.groupby("ticker")["daily_return"].transform(lambda r: r.rolling(vol_window).std())
        * np.sqrt(TRADING_DAYS)
    )
    df["avg_volume_20d"] = df.groupby("ticker")["volume"].transform(lambda v: v.rolling(20).mean())
    short, long_ = df[f"sma_{short_window}"], df[f"sma_{long_window}"]
    df["trend"] = np.where(long_.isna(), None, np.where(short > long_, "UP", "DOWN"))
    return df


def summary(df):
    """Latest snapshot per ticker."""
    last = df.sort_values("date").groupby("ticker").tail(1).set_index("ticker")
    first = df.sort_values("date").groupby("ticker").head(1).set_index("ticker")
    out = pd.DataFrame({
        "as_of": last["date"].dt.date,
        "close": last["close"],
        "period_return_pct": (100 * (last["close"] / first["close"] - 1)).round(2),
        "volatility_20d_pct": (100 * last.filter(like="volatility").iloc[:, 0]).round(2),
        "trend": last["trend"],
    })
    return out.reset_index()
