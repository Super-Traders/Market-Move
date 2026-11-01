 
#!/usr/bin/env python3
"""Look up NSE company names directly from Yahoo Finance using yfinance."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf


def _yahoo_ticker(symbol: str) -> str:
    cleaned = symbol.strip().upper()
    if not cleaned:
        raise ValueError("Stock symbol cannot be empty.")
    return cleaned if "." in cleaned else f"{cleaned}.NS"


def lookup_stock_name(symbol: str) -> dict[str, object]:
    """Fetch the company name and latest available daily OHLC from Yahoo Finance."""
    yahoo_ticker = _yahoo_ticker(symbol)
    nse_symbol = yahoo_ticker.split(".", maxsplit=1)[0]
    result: dict[str, object] = {
        "Symbol": nse_symbol,
        "Yahoo_Ticker": yahoo_ticker,
        "Stock_Name": "",
        "Provider": "yfinance",
        "Status": "ERROR",
        "OHLC_Date": "",
        "Open": None,
        "High": None,
        "Low": None,
        "Close": None,
        "OHLC_Status": "ERROR",
        "Error": "",
    }

    try:
        ticker = yf.Ticker(yahoo_ticker)
    except Exception as exc:
        result["Error"] = f"Could not create Yahoo Finance ticker: {exc}"
        return result

    try:
        info = ticker.get_info()
        name = ""
        if isinstance(info, dict):
            name = str(info.get("longName") or info.get("shortName") or "").strip()
        if name:
            result["Stock_Name"] = name
            result["Status"] = "OK"
        else:
            result["Status"] = "NOT_FOUND"
            result["Error"] = "Yahoo Finance returned no company name for this ticker."
    except Exception as exc:
        result["Error"] = f"Company name lookup failed: {exc}"

    try:
        history = ticker.history(period="5d", interval="1d", auto_adjust=False)
        if history is None or history.empty:
            result["OHLC_Status"] = "NO_DATA"
            quote_error = "Yahoo Finance returned no daily price history."
        else:
            latest = history.dropna(subset=["Open", "High", "Low", "Close"]).iloc[-1]
            result["OHLC_Date"] = pd.Timestamp(latest.name).date().isoformat()
            for field in ("Open", "High", "Low", "Close"):
                result[field] = float(latest[field])
            result["OHLC_Status"] = "OK"
            quote_error = ""
    except Exception as exc:
        result["OHLC_Status"] = "ERROR"
        quote_error = f"Latest OHLC lookup failed: {exc}"

    if quote_error:
        result["Error"] = "; ".join(
            error for error in (str(result["Error"]), quote_error) if error
        )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch company names for NSE symbols using the yfinance library."
    )
    parser.add_argument(
        "symbols",
        nargs="+",
        help="One or more symbols, such as RELIANCE TCS or RELIANCE.NS.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional CSV output path for the lookup results.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = [lookup_stock_name(symbol) for symbol in args.symbols]
    results = pd.DataFrame(rows)
    print(results.to_string(index=False))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        results.to_csv(args.output, index=False, encoding="utf-8-sig")
        print(f"\nSaved results to: {args.output.resolve()}")

    has_errors = results["Status"].ne("OK") | results["OHLC_Status"].ne("OK")
    return 1 if has_errors.any() else 0


if __name__ == "__main__":
    sys.exit(main())