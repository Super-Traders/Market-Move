#!/usr/bin/env python3
"""Rank current stock candidates using the research backtest's selection rules.

Run `python current_stock_picks.py` to print the top 20 using monthly indicators.
This reads the local cache only; it does not place trades or fetch fresh market data.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from backtest_research import _load_panel
from config import SECTORS, TIMEFRAME_CONFIGS
from indicators.breadth import calculate_sector_breadth
from indicators.rrg import calculate_rrg
from indicators.rs_ranking import calculate_rs_score, rank_universe
from indicators.trend_filter import check_trend
from scoring.composite import compute_rotation_score

_SECTOR_OF = {symbol: sector for sector, symbols in SECTORS.items() for symbol in symbols}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rank current candidates using the research backtest scoring rules."
    )
    parser.add_argument(
        "--top-n", type=int, default=20,
        help="Number of candidates to show (default: 20).",
    )
    parser.add_argument(
        "--timeframe", choices=TIMEFRAME_CONFIGS, default="monthly",
        help="Indicator timeframe (default: monthly, as used by the backtest run).",
    )
    parser.add_argument(
        "--as-of", "--as-of-date", dest="as_of_date",
        help="Rank using data available on or before this date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--include-below-200dma", action="store_true",
        help="Include stocks below their 200-day moving average.",
    )
    parser.add_argument(
        "--csv", type=Path,
        help="Optional path to save the ranked candidates as a CSV file.",
    )
    return parser.parse_args()


def rank_current_stocks(timeframe: str = "monthly", top_n: int = 20,
                        require_uptrend: bool = True,
                        as_of_date: str | pd.Timestamp | None = None) -> tuple[pd.Timestamp, pd.DataFrame]:
    """Score stocks using data available by the selected benchmark trading date."""
    if top_n < 1:
        raise ValueError("top_n must be at least 1")

    daily, benchmark = _load_panel()
    if not daily or benchmark.empty:
        raise ValueError("No cached stock or Nifty 500 benchmark data was found.")

    if as_of_date is None:
        requested_date = pd.Timestamp(benchmark.index[-1])
    else:
        try:
            requested_date = pd.Timestamp(as_of_date).normalize()
        except (TypeError, ValueError) as exc:
            raise ValueError("as_of_date must be a valid date in YYYY-MM-DD format.") from exc

    available_benchmark = benchmark.loc[:requested_date].dropna()
    if available_benchmark.empty:
        raise ValueError(f"No cached benchmark data is available on or before {requested_date.date()}.")

    # Resolve weekends, holidays, and non-trading dates to the preceding session.
    as_of = pd.Timestamp(available_benchmark.index[-1])
    settings = TIMEFRAME_CONFIGS[timeframe]
    benchmark_history = benchmark.loc[:as_of].dropna()
    benchmark_resampled = benchmark_history.resample(settings["resample"]).last().dropna()
    if len(benchmark_resampled) < settings["sma_window"] + 5:
        raise ValueError(f"Not enough benchmark history for the {timeframe} indicators.")

    relative_strength = {}
    resampled_prices = {}
    daily_prices = {}
    for symbol, prices in daily.items():
        history = prices.loc[:as_of].dropna()
        if len(history) < 260:
            continue
        resampled = history.resample(settings["resample"]).last().dropna()
        resampled_prices[symbol] = resampled
        daily_prices[symbol] = history
        score = calculate_rs_score(
            resampled, benchmark_resampled, settings["rs_periods"]
        )
        if score:
            relative_strength[symbol] = score

    ranked_rs = rank_universe(relative_strength)

    # Calculate each sector's breadth from the same as-of daily price histories.
    sector_breadth = {}
    for sector, symbols in SECTORS.items():
        members = {
            symbol: pd.DataFrame({"Close": daily_prices[symbol]})
            for symbol in symbols if symbol in daily_prices
        }
        if members:
            sector_breadth[sector] = calculate_sector_breadth(members)

    rows = []
    for symbol, prices in resampled_prices.items():
        trend = check_trend(daily_prices[symbol])
        above_200dma = bool(trend and trend["above_200dma"])
        if require_uptrend and not above_200dma:
            continue

        sector = _SECTOR_OF.get(symbol, "")
        breadth = sector_breadth.get(sector, {})
        rrg = calculate_rrg(
            prices,
            benchmark_resampled,
            settings["sma_window"],
            settings["roc_lookback"],
            settings["tail_length"],
        )
        rotation_score = compute_rotation_score(
            rrg, ranked_rs.get(symbol), trend, breadth
        )
        close = daily_prices[symbol]
        last_price = float(close.iloc[-1])
        rows.append({
            "Symbol": symbol,
            "Sector": sector,
            "Rotation score": rotation_score,
            "RRG quadrant": rrg["quadrant"] if rrg else "N/A",
            "RRG direction": rrg["direction"] if rrg else "N/A",
            "RS percentile": ranked_rs.get(symbol, {}).get("percentile"),
            "Last price": round(last_price, 2),
            "200-DMA": round(float(trend["dma_200"]), 2) if trend else None,
            "% vs 200-DMA": round(float(trend["pct_from_dma"]), 2) if trend else None,
            "Sector breadth above 200-DMA (%)": breadth.get("breadth_200"),
            "Price date": close.index[-1].date().isoformat(),
        })

    rows.sort(key=lambda row: row["Rotation score"], reverse=True)
    result = pd.DataFrame(rows[:top_n])
    return as_of, result


def main() -> None:
    args = parse_args()
    try:
        as_of, picks = rank_current_stocks(
            timeframe=args.timeframe,
            top_n=args.top_n,
            require_uptrend=not args.include_below_200dma,
            as_of_date=args.as_of_date,
        )
    except (ValueError, KeyError) as exc:
        raise SystemExit(f"[ERROR] {exc}") from exc

    print("CURRENT STOCK CANDIDATES (research backtest scoring rules)")
    print(f"Data as of benchmark date: {as_of.date().isoformat()}")
    print(f"Indicator timeframe: {args.timeframe}")
    print(f"Above 200-DMA filter: {'off' if args.include_below_200dma else 'on'}")
    print("Candidates only; this report does not place orders or make a personalized recommendation.\n")
    if picks.empty:
        print("No stocks passed the selected filters.")
        return

    display = picks.copy()
    display.insert(0, "Rank", range(1, len(display) + 1))
    print(display.to_string(index=False, na_rep="-"))

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        picks.to_csv(args.csv, index=False)
        print(f"\nSaved {len(picks)} candidates to: {args.csv.resolve()}")


if __name__ == "__main__":
    main()
