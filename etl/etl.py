"""Run the market data ETL: extract -> transform -> load.

Usage:
    python -m etl.etl --config config.yaml
    python -m etl.etl --config config.yaml --source sample   # offline, no network needed
"""
import argparse
import logging
import os

import yaml

from etl import extract, load, transform

log = logging.getLogger("etl")


def run(config, source=None):
    tickers = config["tickers"]
    source = source or config.get("source", "yahoo")
    out_dir = config.get("output_dir", "output")

    raw = extract.extract(tickers, config["start_date"], config.get("end_date"), source=source)
    df = transform.add_indicators(raw)
    csvs = load.to_csv(df, os.path.join(out_dir, "csv"))
    total = load.to_sqlite(df, os.path.join(out_dir, "market_data.db"))

    snap = transform.summary(df)
    snap.to_csv(os.path.join(out_dir, "summary.csv"), index=False)
    log.info("Loaded %d rows for %d tickers (%d rows in database)", len(df), len(csvs), total)
    print(snap.to_string(index=False))
    return df, snap


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--source", choices=["yahoo", "sample"], help="override the config's source")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with open(args.config) as f:
        run(yaml.safe_load(f), args.source)


if __name__ == "__main__":
    main()
