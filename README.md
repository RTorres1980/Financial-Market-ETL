# 📈 Financial Markets ETL

A lightweight **Extract-Transform-Load (ETL)** pipeline for pulling financial market data, transforming it with indicators, and saving results into CSV and SQLite for further analysis.  

This project is **Docker-ready**, making it easy to deploy, schedule, and run anywhere (local, GitHub Actions, cloud).  

---

## 🚀 Features
- **Extract**: Historical OHLCV data from Yahoo Finance via `yfinance`.
- **Transform**:
  - Daily returns (% change)
  - 20-day and 50-day moving averages
  - 20-day rolling volatility (std. dev of volume)
- **Load**:
  - CSV files (one per ticker)
  - SQLite database (`market_data.db` with one table per ticker)
- **Config-driven** (tickers, dates, output location in `config.yaml`).
- **GitHub Actions Workflow** included for scheduled runs.
- **Dockerized** for portability and easy deployment.

---

## 📦 Installation & Usage

### Option 1: Run Locally (Python Virtual Environment)
```bash
# Clone repo
git clone https://github.com/YOUR_USERNAME/financial-markets-etl.git
cd financial-markets-etl

# Set up environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run ETL
python etl/etl.py --config config.yaml
