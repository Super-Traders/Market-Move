#!/usr/bin/env python3
"""Backtest the monthly 25th rebalancing portfolio strategy.

Strategy summary
----------------
- Start from 5 years of cached OHLCV data.
- Rank all stocks monthly on the 25th of each month using the RRG rotation score,
    cross-universe relative strength, sector breadth, and 200-DMA filter.
- Build the initial portfolio with the top 30 ranked stocks in equal weight.
- On each monthly rebalance:
    * Stocks ranked 31..60 are kept (buffer zone).
    * Stocks ranked below 60 are sold.
    * Replacement buys come from the highest-ranked unowned names inside the top 30.
- Optional crash protection can be toggled on:
    * Nifty 50 6M return < 0 => 0% equity weight / 100% cash
    * Nifty Midcap 150 3M return < 0 => 50% equity exposure
    * India VIX > 25 => 50% equity exposure
    * Portfolio NAV < 10-month moving average => 0% equity weight
"""

from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from config import DB_PATH, SECTORS, TIMEFRAME_CONFIGS, get_all_stocks
from data.cache import load_ohlcv
from indicators.breadth import calculate_sector_breadth
from indicators.rrg import calculate_rrg
from indicators.rs_ranking import calculate_rs_score, rank_universe
from indicators.trend_filter import check_trend
from scoring.composite import compute_rotation_score

_SECTOR_OF = {symbol: sector for sector, symbols in SECTORS.items() for symbol in symbols}
_STOCK_UNIVERSE = set(get_all_stocks())


@dataclass
class TradeResult:
    date: str
    equity_curve: float
    portfolio_return: float
    holdings: List[str]
    cash_weight: float


@dataclass
class RebalanceEntry:
    rebal_date: str
    rank_snapshot: Dict[str, int]
    previous_holdings: List[str]
    new_holdings: List[str]
    stocks_in: List[str]
    stocks_out: List[str]
    retained: List[str]
    portfolio_return_pct: float
    cash_weight: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backtest the monthly 25th rank-buffer portfolio strategy using the local SQLite cache.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--db-path", default=str(DB_PATH), help="Path to the SQLite cache DB.")
    parser.add_argument("--years", type=int, default=5, help="Historical period to test, in years.")
    parser.add_argument("--top-n", type=int, default=30, help="Initial portfolio size.")
    parser.add_argument("--exit-rank", type=int, default=60, help="Exit threshold: sell if rank falls below this number.")
    parser.add_argument("--buffer-start", type=int, default=31, help="Buffer band: keep ranks 31..60.")
    parser.add_argument("--enable-crash-protection", action="store_true", help="Activate crash protection toggles.")
    parser.add_argument("--vix-symbol", default="INDIAVIX", help="VIX symbol in the cache (if available).")
    parser.add_argument(
        "--initial-capital",
        type=float,
        default=1000000.0,
        help="Starting portfolio capital in rupees for equal-weight position sizing.",
    )
    parser.add_argument(
        "--excel-output",
        type=str,
        default="./portfolio_monthly_report.xlsx",
        help="Excel file path for the detailed monthly rebalance report.",
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="Run a parameter sweep over portfolio sizes and exit ranks instead of one backtest.",
    )
    parser.add_argument(
        "--sweep-top-n",
        default="5,10,15,20,25,30",
        help="Comma-separated portfolio sizes to test in sweep mode.",
    )
    parser.add_argument(
        "--sweep-exit-ranks",
        default="60,65,70,75,80",
        help="Comma-separated exit ranks to test in sweep mode.",
    )
    parser.add_argument(
        "--sweep-output",
        default="./portfolio_parameter_sweep.csv",
        help="CSV path for sweep results, sorted by CAGR.",
    )
    return parser.parse_args()


def _safe_float(value):
    try:
        return float(value)
    except Exception:
        return np.nan


def score_stock(
    symbol: str,
    daily_history: pd.DataFrame,
    resampled_history: pd.Series,
    benchmark_history: pd.Series,
    rs_result: dict | None,
    sector_breadth: dict,
    timeframe: str = "monthly",
) -> dict | None:
    """Score one stock with the same RRG composite used by current_stock_picks."""
    if daily_history is None or daily_history.empty or symbol.startswith("IDX:"):
        return None

    settings = TIMEFRAME_CONFIGS[timeframe]
    trend = check_trend(daily_history["Close"].astype(float))
    # Match the current-picks default: do not rank stocks below their 200-DMA.
    if trend is None or not trend["above_200dma"]:
        return None

    rrg = calculate_rrg(
        resampled_history,
        benchmark_history,
        settings["sma_window"],
        settings["roc_lookback"],
        settings["tail_length"],
    )
    rotation_score = compute_rotation_score(rrg, rs_result, trend, sector_breadth)
    close_prices = daily_history["Close"].astype(float)
    return {
        "Symbol": symbol,
        "Price": round(float(close_prices.iloc[-1]), 2),
        "Composite Score": rotation_score,
        "RRG Quadrant": rrg["quadrant"] if rrg else "N/A",
        "RRG Direction": rrg["direction"] if rrg else "N/A",
        "RS Percentile": rs_result.get("percentile") if rs_result else None,
        "Above 200-DMA": trend["above_200dma"],
        "% vs 200-DMA": trend["pct_from_dma"],
    }


def get_trade_day_for_month(year: int, month: int) -> date:
    """Return the 25th of the month, adjusted to the next valid trading day if it falls on a weekend."""
    d = date(year, month, 25)
    if d.weekday() >= 5:
        # Move to next Monday if Saturday/Sunday.
        offset = (7 - d.weekday()) % 7
        d = d + timedelta(days=offset or 7)
    return d


def get_monthly_trade_dates(start_date: date, end_date: date) -> List[date]:
    dates: List[date] = []
    year = start_date.year
    month = start_date.month
    while date(year, month, 1) < start_date:
        month += 1
        if month > 12:
            month = 1
            year += 1
    current_year = year
    current_month = month
    while True:
        d = get_trade_day_for_month(current_year, current_month)
        if d < start_date:
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1
            continue
        if d > end_date:
            break
        dates.append(d)
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1
    return dates


def load_cache_symbols(db_path: str | Path) -> tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
    db_path = Path(db_path)
    conn = sqlite3.connect(str(db_path), timeout=30)
    try:
        symbols = [
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT symbol FROM ohlcv WHERE symbol NOT LIKE 'IDX:%' ORDER BY symbol"
            ).fetchall()
        ]
        panel: Dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            df = load_ohlcv(conn, symbol)
            if not df.empty:
                df = df[~df.index.duplicated(keep="last")].sort_index()
                panel[symbol] = df

        index_panel: Dict[str, pd.DataFrame] = {}
        for idx_key in ["IDX:NIFTY 50", "IDX:NIFTY MIDCAP 150", "IDX:NIFTY 500"]:
            df = load_ohlcv(conn, idx_key)
            if not df.empty:
                df = df[~df.index.duplicated(keep="last")].sort_index()
                index_panel[idx_key] = df
    finally:
        conn.close()
    return panel, index_panel


def get_last_price(series: pd.Series, as_of_date: date):
    idx = series.index[series.index <= pd.Timestamp(as_of_date)]
    if len(idx) == 0:
        return np.nan
    return float(series.loc[idx[-1]])


def compute_ranked_stocks(
    panel: Dict[str, pd.DataFrame],
    index_panel: Dict[str, pd.DataFrame],
    as_of_date: date,
    timeframe: str = "monthly",
) -> Dict[str, int]:
    """Rank point-in-time stocks using the current-picks RRG selection method."""
    benchmark_frame = index_panel.get("IDX:NIFTY 500")
    if benchmark_frame is None or benchmark_frame.empty:
        return {}

    settings = TIMEFRAME_CONFIGS[timeframe]
    cutoff = pd.Timestamp(as_of_date)
    benchmark_daily = benchmark_frame.loc[:cutoff, "Close"].dropna()
    benchmark_resampled = benchmark_daily.resample(settings["resample"]).last().dropna()

    daily_history = {}
    resampled_history = {}
    rs_scores = {}
    for symbol, frame in panel.items():
        if symbol not in _STOCK_UNIVERSE:
            continue
        # Match current_stock_picks: ignore rows without a valid close before
        # computing trend, relative strength, and sector breadth.
        history = frame.loc[:cutoff].dropna(subset=["Close"]).copy()
        if history.empty or len(history) < 260:
            continue
        daily_history[symbol] = history
        resampled = history["Close"].resample(settings["resample"]).last().dropna()
        resampled_history[symbol] = resampled
        rs_score = calculate_rs_score(
            resampled, benchmark_resampled, settings["rs_periods"]
        )
        if rs_score:
            rs_scores[symbol] = rs_score

    rs_ranked = rank_universe(rs_scores)

    # Sector breadth is measured only from prices available on this rebalance date.
    sector_breadth = {}
    for sector, symbols in SECTORS.items():
        members = {
            symbol: daily_history[symbol]
            for symbol in symbols if symbol in daily_history
        }
        if members:
            sector_breadth[sector] = calculate_sector_breadth(members)

    ranked_rows = []
    for symbol, history in daily_history.items():
        sector = _SECTOR_OF.get(symbol, "")
        scored = score_stock(
            symbol,
            history,
            resampled_history[symbol],
            benchmark_resampled,
            rs_ranked.get(symbol),
            sector_breadth.get(sector, {}),
            timeframe,
        )
        if scored is not None:
            ranked_rows.append((symbol, float(scored["Composite Score"])))
    if not ranked_rows:
        return {}
    ranked_rows.sort(key=lambda x: x[1], reverse=True)
    return {symbol: rank + 1 for rank, (symbol, _) in enumerate(ranked_rows)}


def build_initial_portfolio(ranked: Dict[str, int], top_n: int) -> List[str]:
    ordered = [symbol for symbol, _ in sorted(ranked.items(), key=lambda kv: kv[1])]  # ascending rank is best
    return ordered[:top_n]


def built_target_portfolio(
    current_holding: List[str],
    ranked: Dict[str, int],
    top_n: int,
    exit_rank: int,
    buffer_start: int,
) -> List[str]:
    """Return the target portfolio using the exit-rank rule.

    Rule:
    - Any holding with rank > exit_rank is sold.
    - Holdings with rank <= exit_rank remain eligible.
    - The portfolio is then filled with the best available names up to top_n.
    - Buffer range is retained only as an optional watchlist if the strategy wants it.
    """
    target_set = set()

    # Sell any holding whose rank is worse than the exit threshold.
    # Lower numeric rank is better; `exit_rank` is the worst rank we are willing to keep.
    for symbol in current_holding:
        rank = ranked.get(symbol, exit_rank + 1)
        if rank <= exit_rank:
            target_set.add(symbol)

    # Fill the portfolio with the best available names up to top_n.
    ranked_order = [
        symbol for symbol, rank in sorted(ranked.items(), key=lambda kv: kv[1])
        if rank <= top_n or (buffer_start <= rank < exit_rank)
    ]

    for symbol in ranked_order:
        if symbol in target_set:
            continue
        if len(target_set) >= top_n:
            break
        target_set.add(symbol)

    final = [symbol for symbol in sorted(target_set, key=lambda s: ranked.get(s, exit_rank + 1))]
    if not final:
        final = ranked_order[:top_n]
    return final[:top_n]


def get_position_market_value(symbol: str, position: Dict[str, float], price_lookup: Dict[str, pd.Series], as_of_date: date) -> float:
    qty = int(position.get("qty", 0))
    price = get_last_price(price_lookup.get(symbol, pd.Series([], dtype=float)), as_of_date)
    if pd.isna(price) or price <= 0:
        return float(position.get("entry_value", 0.0))
    return float(qty) * float(price)


def get_portfolio_total_value(positions: Dict[str, Dict[str, float]], cash_balance: float, price_lookup: Dict[str, pd.Series] | None = None, as_of_date: date | None = None) -> float:
    """Return the total portfolio value including cash and current market value of all holdings."""
    market_value = float(sum(float(v.get("entry_value", 0.0)) for v in positions.values()))
    if price_lookup is not None and as_of_date is not None:
        market_value = sum(
            get_position_market_value(symbol, position, price_lookup, as_of_date)
            for symbol, position in positions.items()
        )
    return max(float(market_value) + float(cash_balance), 1e-9)


def compute_position_weight_pct(symbol: str, positions: Dict[str, Dict[str, float]], price_lookup: Dict[str, pd.Series], as_of_date: date, cash_balance: float = 0.0) -> float:
    """Basic weight for a stock as a % of the total portfolio value including cash."""
    portfolio_total = get_portfolio_total_value(positions, cash_balance, price_lookup, as_of_date)
    if symbol not in positions:
        return 0.0
    pos_value = get_position_market_value(symbol, positions[symbol], price_lookup, as_of_date)
    return (pos_value / max(portfolio_total, 1e-9)) * 100.0


def compute_portfolio_return(portfolio: List[str], start_date: date, next_date: date, panel: Dict[str, pd.DataFrame]) -> tuple[float, List[str]]:
    if not portfolio:
        return 0.0, []
    returns = []
    for symbol in portfolio:
        s = panel.get(symbol)
        if s is None or s.empty:
            continue
        start_val = get_last_price(s["Close"], start_date)
        end_val = get_last_price(s["Close"], next_date)
        if pd.isna(start_val) or pd.isna(end_val) or start_val == 0:
            continue
        returns.append((end_val / start_val) - 1.0)
    if not returns:
        return 0.0, portfolio
    return float(np.mean(returns)), portfolio


def compute_protection_factor(
    as_of_date: date,
    equity_curve: List[float],
    index_panel: Dict[str, pd.DataFrame],
    enable: bool,
) -> float:
    if not enable:
        return 1.0

    # NIFTY 50 6-month return < 0 => no equity
    nifty = index_panel.get("IDX:NIFTY 50")
    if nifty is not None:
        hist = nifty.loc[:pd.Timestamp(as_of_date)].copy()
        if len(hist) >= 126:
            p0 = get_last_price(hist["Close"], as_of_date - timedelta(days=180))
            p1 = get_last_price(hist["Close"], as_of_date)
            if not np.isnan(p0) and p0 > 0 and p1 > 0:
                if (p1 / p0) - 1.0 < 0:
                    return 0.0

    # Midcap 150, 3M return < 0 => 50% exposure
    midcap = index_panel.get("IDX:NIFTY MIDCAP 150")
    if midcap is not None:
        hist = midcap.loc[:pd.Timestamp(as_of_date)].copy()
        if len(hist) >= 63:
            p0 = get_last_price(hist["Close"], as_of_date - timedelta(days=90))
            p1 = get_last_price(hist["Close"], as_of_date)
            if not np.isnan(p0) and p0 > 0 and p1 > 0 and ((p1 / p0) - 1.0 < 0):
                return 0.5

    # VIX > 25 => 50% exposure
    vix = index_panel.get("IDX:INDIAVIX")
    if vix is not None:
        value = get_last_price(vix["Close"], as_of_date)
        if not np.isnan(value) and value > 25:
            return 0.5

    # NAV below 10-month moving average => 0% equity exposure
    if len(equity_curve) >= 10:
        nav = pd.Series(equity_curve)
        ma_10 = nav.tail(10).mean()
        if nav.iloc[-1] < ma_10:
            return 0.0

    return 1.0


def run_backtest(
    db_path: str | Path,
    years: int = 5,
    top_n: int = 30,
    exit_rank: int = 60,
    buffer_start: int = 31,
    enable_crash_protection: bool = True,
    initial_capital: float = 1000000.0,
    cached_market_data: tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]] | None = None,
) -> dict:
    end_date = date.today()
    start_date = end_date - timedelta(days=years * 365)

    panel, index_panel = cached_market_data or load_cache_symbols(db_path)
    if not panel:
        raise ValueError(f"No stock cache data found in {db_path}.")

    price_lookup = {
        symbol: df["Close"].copy()
        for symbol, df in panel.items()
        if "Close" in df.columns and not df.empty
    }

    trade_dates = get_monthly_trade_dates(start_date, end_date)
    if len(trade_dates) < 2:
        raise ValueError("Not enough historical data to run the backtest.")

    holdings: List[str] = []
    equity_curve = [1.0]
    nav_history = [1.0]
    rebal_report: List[dict] = []
    positions: Dict[str, Dict[str, float]] = {}
    last_month_positions: Dict[str, Dict[str, float]] = {}
    historical_positions: Dict[str, Dict[str, float]] = {}
    portfolio_value = float(initial_capital)
    cash_balance = float(initial_capital)

    # Include the latest scheduled rebalance even when the next monthly date has
    # not arrived yet. Its return is measured through end_date (a partial period).
    for i in range(len(trade_dates)):
        trade_date = trade_dates[i]
        next_trade_date = trade_dates[i + 1] if i + 1 < len(trade_dates) else end_date
        ranked = compute_ranked_stocks(panel, index_panel, trade_date)
        if not ranked:
            continue

        previous_holdings = list(holdings)
        previous_set = set(previous_holdings)

        if i == 0:
            holdings = build_initial_portfolio(ranked, top_n)
        else:
            holdings = built_target_portfolio(holdings, ranked, top_n, exit_rank, buffer_start)

        previous_positions = last_month_positions.copy()
        if not previous_positions:
            for symbol in previous_set:
                if symbol in historical_positions:
                    previous_positions[symbol] = historical_positions[symbol].copy()
        current_set = set(holdings)
        retained = sorted(symbol for symbol in previous_set & current_set if ranked.get(symbol, exit_rank + 1) <= exit_rank)
        stocks_in = sorted(symbol for symbol in current_set - previous_set if ranked.get(symbol, exit_rank + 1) <= exit_rank)
        stocks_out = sorted(
            set(symbol for symbol in previous_set if ranked.get(symbol, exit_rank + 1) > exit_rank)
            | set(symbol for symbol in previous_set - current_set)
        )
        trade_log = []

        weight = 1.0
        if enable_crash_protection:
            weight = compute_protection_factor(trade_date, nav_history, index_panel, True)

        # Reset/refresh the live positions to the target portfolio on each monthly rebalance.
        # Strict rule: no entry without exit. New entries must be funded only by exit proceeds.
        if i == 0:
            cash_balance = initial_capital
            positions = {}
            if holdings:
                valid_prices = []
                for symbol in holdings:
                    price = get_last_price(price_lookup.get(symbol, pd.Series([], dtype=float)), trade_date)
                    if pd.isna(price) or price <= 0:
                        continue
                    valid_prices.append((symbol, float(price)))

                if valid_prices:
                    target_value = initial_capital / float(len(valid_prices))
                    for symbol, price in valid_prices:
                        if cash_balance <= 0:
                            break
                        if price > cash_balance:
                            continue
                        qty = max(1, int(target_value // price))
                        cost = qty * price
                        if cost > cash_balance:
                            qty = max(1, int(cash_balance // price))
                            cost = qty * price
                        if qty <= 0 or cost <= 0:
                            continue
                        cash_balance -= cost
                        positions[symbol] = {"qty": int(qty), "entry_price": float(price), "entry_value": float(cost)}
                        trade_log.append({
                            "date": trade_date.isoformat(),
                            "Symbol": symbol,
                            "Action": "INITIAL_ENTRY",
                            "Qty": int(qty),
                            "Price": round(float(price), 4),
                            "Cost": round(float(cost), 2),
                            "Weight_%": round(float(compute_position_weight_pct(symbol, positions, price_lookup, trade_date, cash_balance)), 4),
                            "Portfolio_Value": round(float(get_portfolio_total_value(positions, cash_balance, price_lookup, trade_date)), 2),
                        })

                    if cash_balance > 0:
                        for symbol, price in valid_prices:
                            if symbol in positions or price <= 0 or price > cash_balance:
                                continue
                            qty = max(1, int(cash_balance // price))
                            cost = qty * price
                            if cost <= 0:
                                continue
                            if cost > cash_balance:
                                qty = max(1, int((cash_balance - 1e-9) // price))
                                cost = qty * price
                            if cost <= 0:
                                continue
                            cash_balance -= cost
                            positions[symbol] = {"qty": int(qty), "entry_price": float(price), "entry_value": float(cost)}
                            trade_log.append({
                                "date": trade_date.isoformat(),
                                "Symbol": symbol,
                                "Action": "INITIAL_ENTRY",
                                "Qty": int(qty),
                                "Price": round(float(price), 4),
                                "Cost": round(float(cost), 2),
                                "Weight_%": round(float(compute_position_weight_pct(symbol, positions, price_lookup, trade_date, cash_balance)), 4),
                                "Portfolio_Value": round(float(get_portfolio_total_value(positions, cash_balance, price_lookup, trade_date)), 2),
                            })
                            if cash_balance <= 0:
                                break
        else:
            positions = {
                symbol: previous_positions[symbol].copy()
                for symbol in previous_positions
                if symbol not in stocks_out and symbol in current_set
            }
            exit_total = 0.0
            for symbol in stocks_out:
                pos = previous_positions.get(symbol) or historical_positions.get(symbol)
                qty = int(pos.get("qty", 0)) if pos else 0

                series = price_lookup.get(symbol, pd.Series([], dtype=float))
                exit_price = get_last_price(series, trade_date)
                if pos is not None and (pd.isna(exit_price) or exit_price <= 0):
                    exit_price = float(pos.get("entry_price", 0.0) or 0.0)
                if pd.isna(exit_price) or exit_price <= 0:
                    exit_price = 0.0

                if pos is not None and qty <= 0 and float(pos.get("entry_value", 0.0) or 0.0) > 0 and exit_price > 0:
                    qty = max(1, int(round(float(pos.get("entry_value", 0.0)) / float(exit_price))))

                if pos is not None and qty > 0:
                    exit_value = float(qty) * float(exit_price) if exit_price > 0 else float(pos.get("entry_value", 0.0) or 0.0)
                else:
                    exit_value = float(pos.get("entry_value", 0.0) or 0.0) if pos is not None else 0.0

                exit_total += float(exit_value)
                cash_balance += float(exit_value)
                if pos is not None:
                    positions.pop(symbol, None)
                trade_log.append({
                    "date": trade_date.isoformat(),
                    "Symbol": symbol,
                    "Action": "EXIT",
                    "Qty": int(qty),
                    "Price": round(float(exit_price), 4),
                    "Cost": round(float(exit_value), 2),
                    "Weight_%": round((exit_value / max(get_portfolio_total_value(positions, cash_balance, price_lookup, trade_date), 1e-9)) * 100.0, 4),
                    "Portfolio_Value": round(float(get_portfolio_total_value(positions, cash_balance, price_lookup, trade_date)), 2),
                })

            new_symbols = [symbol for symbol in holdings if symbol not in positions and symbol not in previous_set]
            if stocks_out and new_symbols and exit_total > 0:
                alloc_per_symbol = float(exit_total) / float(len(new_symbols))
                for symbol in new_symbols:
                    if alloc_per_symbol <= 0:
                        break
                    price = get_last_price(price_lookup.get(symbol, pd.Series([], dtype=float)), trade_date)
                    if pd.isna(price) or price <= 0:
                        continue
                    qty = max(0, int(alloc_per_symbol // price))
                    if qty <= 0:
                        continue
                    cost = qty * price
                    if cost <= 0:
                        continue
                    if cost > cash_balance:
                        qty = max(0, int(cash_balance // price))
                        if qty <= 0:
                            continue
                        cost = qty * price
                    cash_balance -= cost
                    positions[symbol] = {"qty": int(qty), "entry_price": float(price), "entry_value": float(cost)}
                    trade_log.append({
                        "date": trade_date.isoformat(),
                        "Symbol": symbol,
                        "Action": "ENTRY",
                        "Qty": int(qty),
                        "Price": round(float(price), 4),
                        "Cost": round(float(cost), 2),
                        "Weight_%": round(float(compute_position_weight_pct(symbol, positions, price_lookup, trade_date, cash_balance)), 4),
                        "Portfolio_Value": round(float(get_portfolio_total_value(positions, cash_balance, price_lookup, trade_date)), 2),
                    })

        for sym, pos in positions.items():
            historical_positions[sym] = pos.copy()
        last_month_positions = positions.copy()

        portfolio_return, _ = compute_portfolio_return(holdings, trade_date, next_trade_date, panel)
        updated_equity = float(equity_curve[-1] * (1.0 + (portfolio_return * weight)))
        equity_curve.append(updated_equity)
        nav_history.append(float(updated_equity))
        portfolio_value = updated_equity
        portfolio_total_value = get_portfolio_total_value(positions, cash_balance, price_lookup, trade_date)

        rebal_report.append({
            "date": trade_date.isoformat(),
            "rank_snapshot": {k: int(v) for k, v in sorted(ranked.items(), key=lambda kv: kv[1])[:top_n]},
            "previous_holdings": previous_holdings,
            "new_holdings": list(holdings),
            "stocks_in": stocks_in,
            "stocks_out": stocks_out,
            "retained": retained,
            "portfolio_return_pct": round(portfolio_return * 100.0, 4),
            "cash_weight": round(1.0 - weight, 4),
            "cash_balance": round(float(cash_balance), 2),
            "portfolio_total_value": round(float(portfolio_total_value), 2),
            "portfolio_equity_value": round(float(portfolio_value * initial_capital), 2),
            "trade_log": trade_log,
            "positions": {sym: {
                "qty": int(v["qty"]),
                "entry_price": round(float(v["entry_price"]), 4),
                "entry_value": round(float(v["entry_value"]), 2),
                "weight_pct": round(float(compute_position_weight_pct(sym, positions, price_lookup, trade_date, cash_balance)), 4),
            } for sym, v in positions.items()},
        })

    final_equity = equity_curve[-1] if equity_curve else 1.0
    total_return = (final_equity - 1.0) * 100.0
    returns = [
        (equity_curve[i] / equity_curve[i - 1]) - 1.0 for i in range(1, len(equity_curve))
    ]
    annualized = float((final_equity ** (1 / max(len(returns) / 12, 1e-9))) - 1.0) * 100.0
    max_dd_pct, peak_val, trough_val = compute_max_drawdown(equity_curve)
    current_value = float(initial_capital) * float(final_equity)
    invested_amount = float(initial_capital)
    cagr_pct = compute_cagr(invested_amount, current_value, max(1, len(returns) * 1))

    final_portfolio_value = float(get_portfolio_total_value(positions, cash_balance, price_lookup, end_date))
    # Stock purchases and sales are internal portfolio activity, not investor
    # deposits or withdrawals. The investment starts on the first rebalance date;
    # use the marked value of actual positions plus cash as the terminal value.
    investment_date = (
        date.fromisoformat(rebal_report[0]["date"])
        if rebal_report
        else start_date
    )
    xirr_pct = compute_xirr(
        [-invested_amount, final_portfolio_value],
        [investment_date, end_date],
    )
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "rebal_dates": len(trade_dates),
        "initial_portfolio": holdings,
        "initial_capital": float(initial_capital),
        "invested_amount": invested_amount,
        "current_value": round(current_value, 2),
        "final_portfolio_value": round(final_portfolio_value, 2),
        "final_equity": round(final_equity, 4),
        "total_return_pct": round(total_return, 2),
        "annualized_return_pct": round(annualized, 2),
        "cagr_pct": round(cagr_pct, 2),
        "xirr_pct": round(float(xirr_pct), 2) if not np.isnan(xirr_pct) else np.nan,
        "max_drawdown_pct": round(max_dd_pct, 2),
        "peak_value": round(float(peak_val * initial_capital), 2),
        "trough_value": round(float(trough_val * initial_capital), 2),
        "num_periods": len(returns),
        "equity_curve": equity_curve,
        "rebal_report": rebal_report,
        "price_lookup": price_lookup,
    }


def print_rebalance_report(report: List[dict]) -> None:
    if not report:
        print("No monthly rebalances were generated.")
        return

    for item in report:
        portfolio_value = float(item.get("portfolio_total_value", 0.0))
        initial_capital = float(item.get("initial_capital", 0.0)) if "initial_capital" in item else 0.0
        profit_rupees = portfolio_value - initial_capital
        profit_pct = ((portfolio_value / max(initial_capital, 1e-9)) - 1.0) * 100.0 if initial_capital > 0 else 0.0

        print("\n" + "=" * 120)
        print(f"MONTHLY REBALANCE REPORT - {item['date']}")
        print("=" * 120)
        print(f"Portfolio value: ₹{portfolio_value:,.2f}")
        print(f"Initial capital: ₹{initial_capital:,.2f}")
        print(f"Absolute profit: ₹{profit_rupees:,.2f}")
        print(f"Return since initial investment: {profit_pct:.2f}%")
        print(f"Monthly portfolio return: {item['portfolio_return_pct']:.2f}%")
        print(f"Cash weight: {item['cash_weight'] * 100:.2f}%")
        print(f"Cash balance: ₹{item.get('cash_balance', 0.0):,.2f}")
        print(f"Previous holdings: {', '.join(item['previous_holdings']) if item['previous_holdings'] else 'None'}")
        print(f"New portfolio: {', '.join(item['new_holdings']) if item['new_holdings'] else 'None'}")
        print(f"Stocks retained: {', '.join(item['retained']) if item['retained'] else 'None'}")
        print(f"Stocks IN: {', '.join(item['stocks_in']) if item['stocks_in'] else 'None'}")
        print(f"Stocks OUT: {', '.join(item['stocks_out']) if item['stocks_out'] else 'None'}")
        print("Top rank snapshot (ranked names):")
        for symbol, rank in item["rank_snapshot"].items():
            print(f"  Rank {rank}: {symbol}")


def compute_xirr(cashflows: List[float], dates: List[date]) -> float:
    """Calculate annualized XIRR; solve two-flow investments directly."""
    if len(cashflows) < 2 or len(dates) != len(cashflows):
        return np.nan

    nonzero_flows = [(float(flow), flow_date) for flow, flow_date in zip(cashflows, dates) if flow]
    if len(nonzero_flows) == 2:
        initial_flow, initial_date = nonzero_flows[0]
        terminal_flow, terminal_date = nonzero_flows[1]
        elapsed_days = (terminal_date - initial_date).days
        if initial_flow < 0 < terminal_flow and elapsed_days > 0:
            years = elapsed_days / 365.25
            return float(((terminal_flow / -initial_flow) ** (1.0 / years) - 1.0) * 100.0)

    t0 = dates[0]
    fvals = []
    rates = np.linspace(-0.99, 3.0, 25000)
    for rate in rates:
        val = 0.0
        for cf, d in zip(cashflows, dates):
            years = (d - t0).days / 365.25
            val += cf / ((1.0 + rate) ** years)
        fvals.append(abs(val))
    best_rate = rates[int(np.argmin(fvals))]
    return float(best_rate * 100.0)


def compute_max_drawdown(equity_curve: List[float]) -> tuple[float, float, float]:
    """Return (drawdown_pct, peak_value, trough_value)."""
    if not equity_curve:
        return 0.0, 0.0, 0.0
    peak = equity_curve[0]
    trough = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
            trough = value
    return float(max_dd * 100.0), float(peak), float(trough)


def compute_cagr(start_value: float, end_value: float, months: int) -> float:
    """Annualized compounded growth rate over the elapsed months."""
    if months <= 0 or start_value <= 0:
        return 0.0
    years = max(months / 12.0, 1e-9)
    return float(((end_value / start_value) ** (1.0 / years)) - 1.0) * 100.0


def export_monthly_excel_report(result: dict, output_path: str | Path) -> str:
    """Export a detailed monthly report to Excel with summary, monthly return, rank, trade ledger and XIRR sheets."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    price_lookup = result.get("price_lookup", {})
    summary_rows = []
    monthly_return_rows = []
    rank_rows = []
    trade_rows = []
    xirr_rows = []
    overview_rows = []

    if result.get("rebal_report"):
        initial_capital = float(result.get("initial_capital", 0.0))
        previous_portfolio_value = initial_capital

        for idx, item in enumerate(result.get("rebal_report", [])):
            equity_value = result["equity_curve"][idx + 1] if idx + 1 < len(result["equity_curve"]) else result["equity_curve"][-1]
            cumulative_return_pct = (equity_value - 1.0) * 100.0
            months_elapsed = max(idx + 1, 1)
            cagr_to_date_pct = ((equity_value ** (1 / (months_elapsed / 12.0))) - 1.0) * 100.0
            portfolio_total_value = float(item.get("portfolio_total_value", result.get("current_value", 0.0)))
            absolute_profit = portfolio_total_value - initial_capital
            growth_pct = ((portfolio_total_value / max(initial_capital, 1e-9)) - 1.0) * 100.0 if initial_capital > 0 else 0.0
            month_change = portfolio_total_value - previous_portfolio_value
            month_change_pct = ((portfolio_total_value / max(previous_portfolio_value, 1e-9)) - 1.0) * 100.0 if previous_portfolio_value > 0 else 0.0

            # Keep the overview sheet useful as a month-by-month portfolio dashboard,
            # while retaining the all-period summary row at the end of the sheet.
            overview_rows.append({
                "Period": item["date"][0:7],
                "Rebalance_Date": item["date"],
                "Opening_Portfolio_Value": round(previous_portfolio_value, 2),
                "Closing_Portfolio_Value": round(portfolio_total_value, 2),
                "Monthly_Profit_Loss": round(month_change, 2),
                "Monthly_Return_%": round(month_change_pct, 4),
                "Cumulative_Profit_Loss": round(absolute_profit, 2),
                "Cumulative_Return_%": round(growth_pct, 4),
                "Cash_Balance": round(float(item.get("cash_balance", 0.0)), 2),
                "Cash_Weight_%": round(float(item.get("cash_weight", 0.0)) * 100.0, 4),
                "Holdings_Count": len(item.get("new_holdings", [])),
                "Initial_Capital": round(initial_capital, 2),
            })

            summary_rows.append({
                "Rebalance_Date": item["date"],
                "Portfolio_Return_%": round(item["portfolio_return_pct"], 4),
                "Monthly_Change_₹": round(month_change, 2),
                "Monthly_Change_%": round(month_change_pct, 4),
                "Cumulative_Return_%": round(cumulative_return_pct, 4),
                "CAGR_To_Date_%": round(cagr_to_date_pct, 4),
                "Initial_Capital": round(initial_capital, 2),
                "Invested_Amount": round(float(result.get("initial_capital", 0.0)), 2),
                "Portfolio_Total_Value": round(portfolio_total_value, 2),
                "Absolute_Profit_₹": round(absolute_profit, 2),
                "Profit_vs_Initial_%": round(growth_pct, 4),
                "Current_Value": round(float(result.get("current_value", 0.0)), 2),
                "Cash_Weight_%": round(item["cash_weight"] * 100.0, 4),
                "Cash_Balance": item.get("cash_balance", 0.0),
                "Max_Drawdown_%": round(float(result.get("max_drawdown_pct", 0.0)), 2),
                "Previous_Holdings": "; ".join(item["previous_holdings"]),
                "New_Holdings": "; ".join(item["new_holdings"]),
                "Stocks_In": "; ".join(item["stocks_in"]),
                "Stocks_Out": "; ".join(item["stocks_out"]),
                "Retained": "; ".join(item["retained"]),
                "Top_30_Rank_Snapshot": "; ".join(f"{symbol}:{rank}" for symbol, rank in item["rank_snapshot"].items()),
            })

            monthly_return_rows.append({
                "Rebalance_Date": item["date"],
                "Month": item["date"][0:7],
                "Portfolio_Value": round(portfolio_total_value, 2),
                "Absolute_Profit_₹": round(absolute_profit, 2),
                "Portfolio_Return_%": round(item["portfolio_return_pct"], 4),
                "Monthly_Change_₹": round(month_change, 2),
                "Monthly_Change_%": round(month_change_pct, 4),
                "Cumulative_Return_%": round(cumulative_return_pct, 4),
                "CAGR_To_Date_%": round(cagr_to_date_pct, 4),
                "Cash_Weight_%": round(item["cash_weight"] * 100.0, 4),
                "Cash_Balance": item.get("cash_balance", 0.0),
            })

            previous_portfolio_value = portfolio_total_value

            for symbol, rank in item["rank_snapshot"].items():
                price = get_last_price(price_lookup.get(symbol, pd.Series([], dtype=float)), date.fromisoformat(item["date"]))
                pos = item.get("positions", {}).get(symbol, {})
                cost_value = float(pos.get("entry_value", 0.0)) if pos else np.nan
                rank_rows.append({
                    "Rebalance_Date": item["date"],
                    "Rank": rank,
                    "Symbol": symbol,
                    "Price": round(float(price), 4) if not pd.isna(price) else np.nan,
                    "Cost": round(float(cost_value), 2) if not pd.isna(cost_value) else np.nan,
                })

            for trade in item.get("trade_log", []):
                row = {
                    "Rebalance_Date": trade["date"],
                    "Symbol": trade["Symbol"],
                    "Action": trade["Action"],
                    "Qty": int(trade["Qty"]),
                    "Price": float(trade.get("Price", 0.0)),
                    "Cost": float(trade.get("Cost", 0.0)),
                    "Weight_%": float(trade.get("Weight_%", 0.0)),
                    "Cash_Balance": float(item.get("cash_balance", 0.0)),
                    "Portfolio_Value": float(trade.get("Portfolio_Value", 0.0)),
                    "Entry_Qty": 0,
                    "Entry_Price": None,
                    "Entry_Cost": 0.0,
                    "Exit_Qty": 0,
                    "Exit_Price": None,
                    "Exit_Proceeds": 0.0,
                    "Net_Cashflow": 0.0,
                }
                if trade["Action"] in {"ENTRY", "INITIAL_ENTRY"}:
                    row["Entry_Qty"] = int(trade["Qty"])
                    row["Entry_Price"] = float(trade.get("Price", 0.0))
                    row["Entry_Cost"] = float(trade.get("Cost", 0.0))
                    row["Net_Cashflow"] = -float(trade.get("Cost", 0.0))
                elif trade["Action"] == "EXIT":
                    row["Exit_Qty"] = int(trade["Qty"])
                    row["Exit_Price"] = float(trade.get("Price", 0.0))
                    row["Exit_Proceeds"] = float(trade.get("Cost", 0.0))
                    row["Net_Cashflow"] = float(trade.get("Cost", 0.0))
                trade_rows.append(row)

            trade_rows = sorted(trade_rows, key=lambda row: (row.get("Rebalance_Date", ""), row.get("Symbol", ""), row.get("Action", "")))

        xirr_rows.append({
            "Portfolio_XIRR_%": round(float(result.get("xirr_pct", np.nan)), 4),
            "CAGR_%": round(float(result.get("cagr_pct", 0.0)), 4),
            "Max_Drawdown_%": round(float(result.get("max_drawdown_pct", 0.0)), 4),
            "Final_Equity": round(result["final_equity"], 4),
            "Final_Portfolio_Value": round(float(result.get("final_portfolio_value", result.get("current_value", 0.0))), 2),
            "Current_Value": round(float(result.get("current_value", 0.0)), 2),
            "Invested_Amount": round(float(result.get("invested_amount", 0.0)), 2),
            "Total_Return_%": round(result["total_return_pct"], 4),
            "Annualized_Return_%": round(result["annualized_return_pct"], 4),
            "Initial_Capital": float(result.get("initial_capital", 0.0)),
        })

    overview_rows.append({
        "Period": "Overall",
        "Rebalance_Date": result.get("end_date", ""),
        "Opening_Portfolio_Value": round(float(result.get("initial_capital", 0.0)), 2),
        "Closing_Portfolio_Value": round(float(result.get("final_portfolio_value", result.get("current_value", 0.0))), 2),
        "Monthly_Profit_Loss": np.nan,
        "Monthly_Return_%": np.nan,
        "Cumulative_Profit_Loss": round(float(result.get("final_portfolio_value", result.get("current_value", 0.0))) - float(result.get("initial_capital", 0.0)), 2),
        "Cumulative_Return_%": round(float(result.get("total_return_pct", 0.0)), 2),
        "Cash_Balance": np.nan,
        "Cash_Weight_%": np.nan,
        "Holdings_Count": len(result.get("rebal_report", [])[-1].get("new_holdings", [])) if result.get("rebal_report") else 0,
        "Initial_Capital": round(float(result.get("initial_capital", 0.0)), 2),
        "Final_Portfolio_Value": round(float(result.get("final_portfolio_value", result.get("current_value", 0.0))), 2),
        "Absolute_Profit_₹": round(float(result.get("final_portfolio_value", result.get("current_value", 0.0))) - float(result.get("initial_capital", 0.0)), 2),
        "Total_Return_%": round(float(result.get("total_return_pct", 0.0)), 2),
        "CAGR_%": round(float(result.get("cagr_pct", 0.0)), 2),
        "XIRR_%": round(float(result.get("xirr_pct", 0.0)), 2),
        "Max_Drawdown_%": round(float(result.get("max_drawdown_pct", 0.0)), 2),
        "Annualized_Return_%": round(float(result.get("annualized_return_pct", 0.0)), 2),
        "Rebalance_Count": len(result.get("rebal_report", [])),
    })

    summary_df = pd.DataFrame(summary_rows)
    monthly_return_df = pd.DataFrame(monthly_return_rows)
    rank_df = pd.DataFrame(rank_rows)
    trade_df = pd.DataFrame(trade_rows)
    xirr_df = pd.DataFrame(xirr_rows)
    overview_df = pd.DataFrame(overview_rows)

    ledger_columns = [
        "Rebalance_Date",
        "Symbol",
        "Action",
        "Entry_Qty",
        "Entry_Price",
        "Entry_Cost",
        "Exit_Qty",
        "Exit_Price",
        "Exit_Proceeds",
        "Net_Cashflow",
        "Weight_%",
        "Cash_Balance",
        "Portfolio_Value",
    ]
    if not trade_df.empty:
        trade_df = trade_df.reindex(columns=ledger_columns)

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        overview_df.to_excel(writer, index=False, sheet_name="Portfolio_Overview")
        summary_df.to_excel(writer, index=False, sheet_name="Monthly_Summary")
        monthly_return_df.to_excel(writer, index=False, sheet_name="Monthly_Return")
        rank_df.to_excel(writer, index=False, sheet_name="Rank_Snapshot")
        trade_df.to_excel(writer, index=False, sheet_name="Trade_Ledger")
        xirr_df.to_excel(writer, index=False, sheet_name="Portfolio_XIRR")

    return str(output.resolve())


def main() -> None:
    args = parse_args()
    try:
        if args.sweep:
            top_values = sorted(set(int(value.strip()) for value in args.sweep_top_n.split(",") if value.strip()))
            exit_values = sorted(set(int(value.strip()) for value in args.sweep_exit_ranks.split(",") if value.strip()))
            if not top_values or not exit_values or min(top_values) <= 0 or min(exit_values) <= 0:
                raise ValueError("Sweep portfolio sizes and exit ranks must be positive comma-separated integers.")

            cached_market_data = load_cache_symbols(args.db_path)
            results = []
            total = len(top_values) * len(exit_values)
            for run_number, (top_n, exit_rank) in enumerate(
                ((top_n, exit_rank) for top_n in top_values for exit_rank in exit_values), start=1
            ):
                print(f"[{run_number}/{total}] Testing top-n={top_n}, exit-rank={exit_rank}...")
                result = run_backtest(
                    db_path=args.db_path,
                    years=args.years,
                    top_n=top_n,
                    exit_rank=exit_rank,
                    buffer_start=top_n + 1,
                    enable_crash_protection=args.enable_crash_protection,
                    initial_capital=args.initial_capital,
                    cached_market_data=cached_market_data,
                )
                results.append({
                    "Top_N": top_n,
                    "Exit_Rank": exit_rank,
                    "Years": args.years,
                    "Initial_Capital": args.initial_capital,
                    "Final_Portfolio_Value": result["final_portfolio_value"],
                    "Total_Return_%": result["total_return_pct"],
                    "CAGR_%": result["cagr_pct"],
                    "XIRR_%": result["xirr_pct"],
                    "Max_Drawdown_%": result["max_drawdown_pct"],
                    "Periods": result["num_periods"],
                })

            sweep_df = pd.DataFrame(results).sort_values(
                ["CAGR_%", "Max_Drawdown_%"], ascending=[False, True], na_position="last"
            )
            sweep_path = Path(args.sweep_output)
            sweep_path.parent.mkdir(parents=True, exist_ok=True)
            sweep_df.to_csv(sweep_path, index=False)
            print("\nParameter sweep results (best CAGR first):")
            print(sweep_df.to_string(index=False, float_format=lambda value: f"{value:,.2f}"))
            print(f"\nSaved sweep results to: {sweep_path.resolve()}")
            return

        result = run_backtest(
            db_path=args.db_path,
            years=args.years,
            top_n=args.top_n,
            exit_rank=args.exit_rank,
            buffer_start=args.buffer_start,
            enable_crash_protection=args.enable_crash_protection,
            initial_capital=args.initial_capital,
        )
        print("=" * 80)
        print("MONTHLY 25TH PORTFOLIO BACKTEST")
        print("=" * 80)
        print(f"Start date: {result['start_date']}")
        print(f"End date:   {result['end_date']}")
        print(f"Rebalance dates: {result['rebal_dates']}")
        print(f"Initial portfolio (top {args.top_n}): {', '.join(result['initial_portfolio'][:10])}")
        print(f"Invested amount: {result.get('invested_amount', 0):,.2f}")
        print(f"Current value: {result.get('current_value', 0):,.2f}")
        print(f"Final portfolio value: {result.get('final_portfolio_value', 0):,.2f}")
        print(f"Final equity: {result['final_equity']:.4f}")
        print(f"Total return: {result['total_return_pct']:.2f}%")
        print(f"CAGR: {result.get('cagr_pct', 0):.2f}%")
        print(f"XIRR: {result.get('xirr_pct', 0):.2f}%")
        print(f"Max drawdown: {result.get('max_drawdown_pct', 0):.2f}%")
        print(f"Annualized return: {result['annualized_return_pct']:.2f}%")
        print(f"Periods evaluated: {result['num_periods']}")
        excel_path = export_monthly_excel_report(result, args.excel_output)
        print(f"Excel report saved to: {excel_path}")
        print("\nDetailed monthly rebalance report:\n")
        # print_rebalance_report(result.get("rebal_report", []))
        print("=" * 80)
    except Exception as exc:
        raise SystemExit(f"[ERROR] {exc}") from exc


if __name__ == "__main__":
    main()
