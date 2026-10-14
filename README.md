# Financial Markets ETL

![CI](https://github.com/RTorres1980/Financial-Market-ETL/actions/workflows/ci.yml/badge.svg)

A config-driven ETL pipeline that pulls daily price history from Yahoo Finance, adds common indicators, and loads the results into CSV files and a SQLite database. It runs locally, in Docker, or on a schedule with GitHub Actions.

## What it does

**Extract** (`etl/extract.py`)
- Daily OHLCV data for each ticker from Yahoo Finance via `yfinance`, adjusted for splits and dividends
- A `sample` source that generates a reproducible random walk, so the pipeline and tests run without network access
- A ticker that fails is logged and skipped, so one bad symbol doesn't stop the run

**Transform** (`etl/transform.py`), calculated separately for each ticker
- Cleaning: removes duplicate dates and rows with missing or non-positive prices
- Daily return
- 20-day and 50-day simple moving averages, and a trend flag (`UP` when the 20-day is above the 50-day)
- 20-day annualized volatility of daily returns
- 20-day average volume

**Load** (`etl/load.py`)
- One CSV per ticker in `output/csv/`
- A single `prices` table in `output/market_data.db` keyed on ticker and date. Rows are upserted, so re-running over the same dates never creates duplicates.
- `output/summary.csv` with the latest close, period return, volatility and trend for each ticker

## Run it

Requires Python 3.10+.

```bash
pip install -r requirements.txt
python -m etl.etl --config config.yaml                    # live data from Yahoo Finance
python -m etl.etl --config config.yaml --source sample    # offline sample data
pytest -q
```

Edit `config.yaml` to change the tickers, date range or output folder:

```yaml
tickers: [SPY, QQQ, AAPL, MSFT, JPM, TLT]
start_date: "2024-01-01"
end_date:            # blank = today
source: yahoo
output_dir: output
```

Example query:

```bash
sqlite3 output/market_data.db \
  "SELECT ticker, date, close, ROUND(volatility_20d*100, 1) AS vol_pct, trend
   FROM prices WHERE date = (SELECT MAX(date) FROM prices);"
```

### Docker

```bash
docker build -t market-etl .
docker run --rm -v "$PWD/output:/app/output" market-etl
```

### Scheduled runs

`.github/workflows/etl.yml` runs the pipeline every weekday after the US market close and uploads the database and CSVs as a workflow artifact. You can also start it by hand from the Actions tab. A separate CI workflow runs lint and tests on every push.

## Tests

The tests check the indicator math against hand calculations, that indicators never carry over from one ticker to the next, the cleaning rules, column handling for the Yahoo source (using a mocked response), skipping a failed ticker, and that re-running the pipeline doesn't duplicate rows.

## License

MIT
