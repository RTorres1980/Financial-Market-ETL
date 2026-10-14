"""Extract daily OHLCV price history.

Sources:
  yahoo   Yahoo Finance via yfinance (prices adjusted for splits and dividends)
  sample  a reproducible random walk, for offline runs and tests
"""
import logging
import zlib

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)
COLUMNS = ["date", "ticker", "open", "high", "low", "close", "volume"]


def from_yahoo(ticker, start, end=None):
    import yfinance as yf

    hist = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=True)
    if hist.empty:
        raise ValueError(f"No data returned for {ticker}")
    df = hist.reset_index().rename(columns=str.lower)
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    df["ticker"] = ticker
    return df[COLUMNS]


def from_sample(ticker, start, end=None, seed=None):
    dates = pd.bdate_range(start, end or pd.Timestamp.today().normalize())
    rng = np.random.default_rng(seed if seed is not None else zlib.crc32(ticker.encode()))
    close = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, len(dates))))
    open_ = close * (1 + rng.normal(0, 0.003, len(dates)))
    high = np.maximum(open_, close) * (1 + rng.uniform(0, 0.01, len(dates)))
    low = np.minimum(open_, close) * (1 - rng.uniform(0, 0.01, len(dates)))
    return pd.DataFrame({
        "date": dates, "ticker": ticker, "open": open_.round(2), "high": high.round(2),
        "low": low.round(2), "close": close.round(2),
        "volume": rng.integers(1_000_000, 50_000_000, len(dates)),
    })[COLUMNS]


def extract(tickers, start, end=None, source="yahoo"):
    """Return one frame for all tickers. A ticker that fails is logged and skipped."""
    fetch = from_yahoo if source == "yahoo" else from_sample
    frames = []
    for t in tickers:
        try:
            frames.append(fetch(t, start, end))
            log.info("Extracted %s rows for %s", len(frames[-1]), t)
        except Exception as exc:  # one bad ticker should not stop the run
            log.error("Skipping %s: %s", t, exc)
    if not frames:
        raise RuntimeError("No data extracted for any ticker")
    return pd.concat(frames, ignore_index=True)
