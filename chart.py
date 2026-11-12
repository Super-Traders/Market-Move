#!/usr/bin/env python3
"""Create an interactive OHLCV chart for a cached NSE stock or index."""

import argparse
import re
import webbrowser
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import TIMEFRAME_CONFIGS
from data.fetcher import fetch_index, fetch_stock


def _resample_ohlcv(data, timeframe):
    """Aggregate daily bars into complete OHLCV bars for the requested timeframe."""
    frequency = TIMEFRAME_CONFIGS[timeframe]["resample"]
    if timeframe == "daily":
        return data

    bars = data.resample(frequency).agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }).dropna(subset=["Close"])

    if timeframe == "semi-annual":
        bars = bars[bars.index.month.isin([6, 12])]
    return bars


def _create_chart(symbol, data, timeframe, output_path):
    data = _resample_ohlcv(data, timeframe)
    if data.empty:
        raise ValueError(f"No {timeframe} bars available for {symbol}.")

    data["SMA 20"] = data["Close"].rolling(20).mean()
    data["SMA 50"] = data["Close"].rolling(50).mean()

    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.75, 0.25],
    )
    figure.add_trace(go.Candlestick(
        x=data.index,
        open=data["Open"],
        high=data["High"],
        low=data["Low"],
        close=data["Close"],
        name=symbol,
    ), row=1, col=1)
    for column, color in (("SMA 20", "#e67e22"), ("SMA 50", "#2471a3")):
        figure.add_trace(go.Scatter(
            x=data.index,
            y=data[column],
            mode="lines",
            name=column,
            line={"color": color, "width": 1.5},
        ), row=1, col=1)

    colors = [
        "#168a64" if close >= open_ else "#cf5148"
        for open_, close in zip(data["Open"], data["Close"])
    ]
    figure.add_trace(go.Bar(
        x=data.index,
        y=data["Volume"],
        marker_color=colors,
        name="Volume",
    ), row=2, col=1)
    figure.update_layout(
        title=f"{symbol} | {timeframe.title()}",
        template="plotly_white",
        height=800,
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
        legend={"orientation": "h", "y": 1.02, "x": 0},
        margin={"l": 55, "r": 25, "t": 90, "b": 40},
    )
    figure.update_yaxes(title_text="Price", row=1, col=1)
    figure.update_yaxes(title_text="Volume", row=2, col=1)
    figure.update_xaxes(title_text="Date", row=2, col=1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(output_path, include_plotlyjs="cdn", auto_open=False)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Create an interactive OHLCV chart.")
    parser.add_argument("symbol", help="NSE symbol (e.g. RELIANCE) or IDX:NIFTY 50")
    parser.add_argument(
        "--timeframe", "-t", choices=TIMEFRAME_CONFIGS, default="daily",
        help="Chart timeframe (default: daily)",
    )
    parser.add_argument(
        "--years", type=int, default=5,
        help="Years of history to load (default: 5)",
    )
    parser.add_argument(
        "--output", "-o", type=Path,
        help="HTML output path (default: output/<symbol>_<timeframe>.html)",
    )
    parser.add_argument(
        "--no-open", action="store_true",
        help="Save the chart without opening it in a browser",
    )
    args = parser.parse_args()

    if args.years < 1:
        parser.error("--years must be at least 1")

    symbol = args.symbol.strip()
    is_index = symbol.upper().startswith("IDX:")
    fetch_symbol = symbol[4:].strip() if is_index else symbol.upper().removesuffix(".NS")
    label = f"IDX:{fetch_symbol.upper()}" if is_index else fetch_symbol

    data = (
        fetch_index(fetch_symbol.upper(), years_back=args.years)
        if is_index
        else fetch_stock(fetch_symbol, years_back=args.years)
    )
    if data.empty:
        parser.error(f"No data found for {label}. Check the symbol or your connection.")

    safe_symbol = re.sub(r"[^A-Za-z0-9_-]+", "_", label).strip("_")
    output_path = args.output or Path("output") / f"{safe_symbol}_{args.timeframe}.html"
    try:
        output_path = _create_chart(label, data, args.timeframe, output_path)
    except ValueError as error:
        parser.error(str(error))

    print(f"Saved {len(_resample_ohlcv(data, args.timeframe))} bars to {output_path}")
    if not args.no_open:
        webbrowser.open(output_path.resolve().as_uri())


if __name__ == "__main__":
    main()