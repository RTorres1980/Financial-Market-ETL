import sqlite3
import sys
import types

import numpy as np
import pandas as pd
import pytest

from etl import extract, load, transform
from etl.etl import run


def test_sample_source_is_reproducible():
    a = extract.from_sample("SPY", "2024-01-01", "2024-03-01")
    b = extract.from_sample("SPY", "2024-01-01", "2024-03-01")
    pd.testing.assert_frame_equal(a, b)
    assert list(a.columns) == extract.COLUMNS


def test_yahoo_source_normalizes_columns(monkeypatch):
    idx = pd.DatetimeIndex(["2024-01-02", "2024-01-03"], tz="America/New_York", name="Date")
    hist = pd.DataFrame({"Open": [1.0, 2.0], "High": [1.5, 2.5], "Low": [0.5, 1.5], "Close": [1.2, 2.2],
                         "Volume": [100, 200], "Dividends": [0.0, 0.0], "Stock Splits": [0.0, 0.0]}, index=idx)
    fake = types.SimpleNamespace(Ticker=lambda t: types.SimpleNamespace(history=lambda **kw: hist))
    monkeypatch.setitem(sys.modules, "yfinance", fake)
    df = extract.from_yahoo("XYZ", "2024-01-01")
    assert list(df.columns) == extract.COLUMNS
    assert df["date"].dt.tz is None
    assert df["date"].iloc[0] == pd.Timestamp("2024-01-02")


def test_failed_ticker_is_skipped(monkeypatch):
    real = extract.from_sample

    def flaky(t, start, end=None):
        if t == "BAD":
            raise ValueError("no data")
        return real(t, start, end)
    monkeypatch.setattr(extract, "from_sample", flaky)
    df = extract.extract(["SPY", "BAD"], "2024-01-01", "2024-02-01", source="sample")
    assert set(df["ticker"]) == {"SPY"}


def test_clean_drops_duplicates_and_bad_prices():
    df = extract.from_sample("A", "2024-01-01", "2024-01-10")
    dirty = pd.concat([df, df.iloc[[0]]])
    dirty.loc[dirty.index[1], "close"] = -1
    out = transform.clean(dirty)
    assert out.duplicated(["ticker", "date"]).sum() == 0
    assert (out["close"] > 0).all()


def test_indicators_match_hand_calculation():
    close = pd.Series(np.linspace(100, 160, 60))
    df = pd.DataFrame({"date": pd.bdate_range("2024-01-01", periods=60), "ticker": "T",
                       "open": close, "high": close, "low": close, "close": close, "volume": 1000})
    out = transform.add_indicators(df)
    assert out["sma_20"].iloc[19] == pytest.approx(close.iloc[:20].mean())
    assert pd.isna(out["sma_50"].iloc[48]) and not pd.isna(out["sma_50"].iloc[49])
    rets = close.pct_change()
    assert out["volatility_20d"].iloc[30] == pytest.approx(rets.iloc[11:31].std() * np.sqrt(252))
    assert out["trend"].iloc[-1] == "UP"


def test_indicators_do_not_leak_across_tickers():
    a = extract.from_sample("A", "2024-01-01", "2024-04-01")
    b = extract.from_sample("B", "2024-01-01", "2024-04-01")
    out = transform.add_indicators(pd.concat([a, b]))
    first_b = out[out["ticker"] == "B"].iloc[0]
    assert pd.isna(first_b["daily_return"])


def test_full_run_is_idempotent(tmp_path):
    cfg = {"tickers": ["SPY", "QQQ"], "start_date": "2024-01-01", "end_date": "2024-06-28",
           "output_dir": str(tmp_path)}
    df, snap = run(cfg, source="sample")
    run(cfg, source="sample")
    with sqlite3.connect(tmp_path / "market_data.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0] == len(df)
    assert sorted(p.name for p in (tmp_path / "csv").iterdir()) == ["QQQ.csv", "SPY.csv"]
    assert set(snap["ticker"]) == {"SPY", "QQQ"}


def test_nan_becomes_null(tmp_path):
    df = transform.add_indicators(extract.from_sample("A", "2024-01-01", "2024-02-01"))
    load.to_sqlite(df, str(tmp_path / "x.db"))
    with sqlite3.connect(tmp_path / "x.db") as conn:
        assert conn.execute("SELECT sma_50 FROM prices LIMIT 1").fetchone()[0] is None
