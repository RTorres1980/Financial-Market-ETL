"""Load transformed prices to CSV (one file per ticker) and SQLite (one table, keyed by ticker and date)."""
import os
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    ticker TEXT NOT NULL,
    date   TEXT NOT NULL,
    open REAL, high REAL, low REAL, close REAL, volume INTEGER,
    daily_return REAL, sma_20 REAL, sma_50 REAL, volatility_20d REAL, avg_volume_20d REAL, trend TEXT,
    PRIMARY KEY (ticker, date)
);
"""


def to_csv(df, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for ticker, part in df.groupby("ticker"):
        path = os.path.join(out_dir, f"{ticker}.csv")
        part.to_csv(path, index=False)
        paths.append(path)
    return paths


def to_sqlite(df, db_path):
    """Upsert rows so re-running the pipeline over overlapping dates never duplicates data."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    out = df.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    cols = list(out.columns)
    rows = [tuple(None if v != v else v for v in r) for r in out.itertuples(index=False)]  # NaN -> NULL
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.executemany(
            f"INSERT OR REPLACE INTO prices ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", rows)
        return conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
