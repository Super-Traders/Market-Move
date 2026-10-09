#!/usr/bin/env python3
"""Rank NSE stocks from locally saved CSV files using multi-horizon momentum and volatility-adjusted scoring.

This script scans a directory of local Yahoo Finance CSV exports, filters for usable stock history,
and ranks each stock by a composite score built from:

- 1W, 1M, 3M, 6M, and 12M returns
- 6M and 12M volatility
- 6M and 12M risk-adjusted scores
- final composite score based on the average of the 6M and 12M normalized scores

The script prints the top-ranked stocks to the console and exports the full table to
nifty_momentum_scored.csv.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from config import DB_PATH
from data.cache import load_ohlcv


HORIZONS = {
    "1W": 5,
    "1M": 21,
    "3M": 63,
    "6M": 126,
    "12M": 252,
}


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Rank cached NSE stock symbols using multi-horizon momentum and volatility-adjusted scoring.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--data-dir",
        "--db-path",
        dest="db_path",
        type=str,
        default=str(DB_PATH),
        help="SQLite cache DB path containing the stock OHLCV data (for example: ./data/cache.db).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./nifty_momentum_scored.csv",
        help="Path to the output CSV for the full ranked table.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=15,
        help="Number of top-ranked stocks to print to the console.",
    )
    parser.add_argument(
        "--as-of-date",
        type=date.fromisoformat,
        default=date.today(),
        metavar="YYYY-MM-DD",
        help="Rank using price history through this date. Defaults to today.",
    )
    return parser.parse_args()


def calculate_return_pct(prices: pd.Series, lookback_days: int) -> float:
    """Calculate a return over a specified lookback window in percent terms."""
    if len(prices) < lookback_days:
        return np.nan

    start_idx = max(0, len(prices) - lookback_days)
    start_price = float(prices.iloc[start_idx])
    end_price = float(prices.iloc[-1])

    if pd.isna(start_price) or pd.isna(end_price) or start_price == 0:
        return np.nan

    return ((end_price / start_price) - 1.0) * 100.0


def calculate_volatility_pct(daily_returns: pd.Series, lookback_days: int) -> float:
    """Compute the standard deviation of daily returns over a lookback window, in percent terms."""
    if len(daily_returns) < lookback_days:
        return np.nan

    vol = daily_returns.tail(lookback_days).std(ddof=1)
    if pd.isna(vol) or vol <= 0:
        return np.nan

    return vol * 100.0


def score_stock(symbol: str, df: pd.DataFrame) -> dict | None:
    """Compute all metrics for a single cached stock symbol. Return None if it is unusable."""
    if df is None or df.empty:
        return None

    if symbol.startswith("IDX:"):
        return None

    close_prices = df["Close"].astype(float).reset_index(drop=True)

    # Minimum requirement: at least 252 observations to compute the full 12M window.
    if len(close_prices) < HORIZONS["12M"]:
        return None

    returns = close_prices.pct_change().dropna()
    if returns.empty:
        return None

    # Multi-horizon returns.
    ret_1w = calculate_return_pct(close_prices, HORIZONS["1W"])
    ret_1m = calculate_return_pct(close_prices, HORIZONS["1M"])
    ret_3m = calculate_return_pct(close_prices, HORIZONS["3M"])
    ret_6m = calculate_return_pct(close_prices, HORIZONS["6M"])
    ret_12m = calculate_return_pct(close_prices, HORIZONS["12M"])

    # Volatility over 6M and 12M windows.
    vol_3m = calculate_volatility_pct(returns, HORIZONS["3M"])
    vol_6m = calculate_volatility_pct(returns, HORIZONS["6M"])
    vol_12m = calculate_volatility_pct(returns, HORIZONS["12M"])

    if pd.isna(vol_3m) or pd.isna(vol_6m) or pd.isna(vol_12m) or vol_3m <= 0 or vol_6m <= 0 or vol_12m <= 0:
        return None

    # Risk-adjusted scores.
    score_3m = ret_3m / vol_3m if vol_3m > 0 else np.nan
    score_6m = ret_6m / vol_6m if vol_6m > 0 else np.nan
    score_12m = ret_12m / vol_12m if vol_12m > 0 else np.nan

    if pd.isna(score_3m) or pd.isna(score_6m) or pd.isna(score_12m):
        return None

    composite_score = (score_3m + score_6m + score_12m) / 3.0

    return {
        "Symbol": symbol,
        "Price": round(float(close_prices.iloc[-1]), 2),
        "1W Return %": round(float(ret_1w), 2) if not pd.isna(ret_1w) else np.nan,
        "1M Return %": round(float(ret_1m), 2) if not pd.isna(ret_1m) else np.nan,
        "3M Return %": round(float(ret_3m), 2) if not pd.isna(ret_3m) else np.nan,
        "6M Return %": round(float(ret_6m), 2) if not pd.isna(ret_6m) else np.nan,
        "12M Return %": round(float(ret_12m), 2) if not pd.isna(ret_12m) else np.nan,
        "3M Volatility %": round(float(vol_3m), 4),
        "6M Volatility %": round(float(vol_6m), 4),
        "12M Volatility %": round(float(vol_12m), 4),
        "3M Score": round(float(score_3m), 4),
        "6M Score": round(float(score_6m), 4),
        "12M Score": round(float(score_12m), 4),
        "Composite Score": round(float(composite_score), 4),
    }


def scan_stock_directory(data_dir: Path, as_of_date: date | None = None) -> pd.DataFrame:
    """Read all stock symbols from the SQLite cache DB and compute ranking metrics."""
    as_of_date = as_of_date or date.today()
    db_path = Path(data_dir)
    if not db_path.exists():
        raise FileNotFoundError(f"Cache DB does not exist: {db_path}")

    conn = sqlite3.connect(str(db_path), timeout=30)
    try:
        symbols = [
            row[0] for row in conn.execute(
                "SELECT DISTINCT symbol FROM ohlcv WHERE symbol NOT LIKE 'IDX:%' ORDER BY symbol"
            ).fetchall()
        ]
    finally:
        conn.close()

    if not symbols:
        raise ValueError(f"No stock symbols found in the cache DB: {db_path}")

    rows = []
    skipped = 0

    for symbol in symbols:
        try:
            symbol_conn = sqlite3.connect(str(db_path), timeout=30)
            try:
                df = load_ohlcv(symbol_conn, symbol)
                if not df.empty:
                    # Do not let rows after the requested date affect prices, returns, or ranks.
                    df = df.loc[df.index <= pd.Timestamp(as_of_date)]
                result = score_stock(symbol, df)
                if result is not None:
                    result["As Of Date"] = as_of_date.isoformat()
                    rows.append(result)
                else:
                    skipped += 1
            finally:
                symbol_conn.close()
        except Exception as exc:  # Defensive handling for any unexpected database issue.
            print(f"[WARN] Skipping {symbol}: {exc}", file=sys.stderr)
            skipped += 1

    if not rows:
        raise ValueError(
            "No valid cached stock symbols were processed. Check the cache database and data quality."
        )

    ranking_df = pd.DataFrame(rows).sort_values("Composite Score", ascending=False).reset_index(drop=True)
    ranking_df.insert(0, "Rank", np.arange(1, len(ranking_df) + 1))

    print(f"\nProcessed {len(rows)} valid cached stock symbols from {len(symbols)} total symbols.")
    print(f"Skipped {skipped} symbols due to insufficient history, invalid data, or zero volatility.\n")

    return ranking_df


def print_top_rankings(df: pd.DataFrame, top_n: int) -> None:
    """Display the top N rows in a clean, readable console format."""
    top_df = df.head(top_n).copy()
    print(top_df.to_string(index=False, justify="center", float_format=lambda x: f"{x:,.4f}"))
    print()


def save_output(df: pd.DataFrame, output_path: str | Path) -> None:
    """Persist the ranked output table to a CSV file."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    print(f"Saved full ranking output to: {output.resolve()}\n")


def main() -> None:
    """Entry-point for the stock ranking workflow."""
    args = parse_args()

    try:
        db_path = Path(args.db_path).resolve()
        output_path = Path(args.output).resolve()
        ranked_df = scan_stock_directory(db_path, args.as_of_date)
        print(f"Ranking as of: {args.as_of_date.isoformat()}\n")
        print_top_rankings(ranked_df, args.top)
        save_output(ranked_df, output_path)
    except Exception as exc:  # Clean top-level exception handling.
        print(f"[ERROR] {exc}", file=sys.stderr)
        print("\nUsage example:")
        print("  python nifty_momentum_ranker.py --db-path ./data/cache.db --as-of-date 2026-09-25 --output ./nifty_momentum_scored.csv --top 15")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
