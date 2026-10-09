"""
Simple 5-year backtest for 20-stock monthly rebalancing strategy.
- Exit rank: 60 (sell if rank drops below 60)
- Portfolio: Top 20 stocks, monthly rebalance on 25th
- Include transaction costs (30bps) and taxes (20% STCG)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from config import get_all_stocks, TIMEFRAME_CONFIGS
from data.cache import get_connection, load_ohlcv
from indicators.rrg import calculate_rrg
from indicators.rs_ranking import calculate_rs_score, rank_universe
from indicators.trend_filter import check_trend
from indicators.breadth import calculate_sector_breadth
from scoring.composite import compute_rotation_score
from config import SECTORS

_SECTOR_OF = {s: name for name, syms in SECTORS.items() for s in syms}

def run_backtest(years=5, top_n=20, exit_rank=60, cost_bps=30.0, stcg=0.20):
    """Run backtest for specified number of years."""
    
    print(f"\n{'='*80}")
    print(f"BACKTEST: {years}-Year Strategy | Top-{top_n} Portfolio | Monthly Rebalance | Exit Rank {exit_rank}")
    print(f"{'='*80}\n")
    
    # Load data
    conn = get_connection()
    try:
        daily = {}
        for s in get_all_stocks():
            d = load_ohlcv(conn, s)
            if d.empty:
                continue
            c = d["Close"]
            c = c[~c.index.duplicated(keep="last")].sort_index().dropna()
            if len(c) >= 260:  # At least 1 year of data
                daily[s] = c
        
        bench = load_ohlcv(conn, "IDX:NIFTY 500")["Close"]
        bench = bench[~bench.index.duplicated(keep="last")].sort_index().dropna()
    finally:
        conn.close()
    
    if not daily or bench.empty:
        print("ERROR: No data loaded")
        return None
    
    # Set backtest period (last N years)
    end_date = bench.index.max()
    start_date = end_date - timedelta(days=365*years)
    
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print(f"Available data for {len(daily)} stocks\n")
    
    # Get monthly rebalance dates (25th of each month)
    bench_idx = bench.loc[start_date:end_date].index
    month_ends = pd.date_range(start_date, end_date, freq="MS")
    rebal_dates = []
    
    for month_end in month_ends:
        target = pd.Timestamp(year=month_end.year, month=month_end.month, day=25)
        if target.weekday() >= 5:  # If weekend, move to next Monday
            target = target + timedelta(days=(7 - target.weekday()) % 7)
        
        # Find closest trading day
        available = bench_idx[bench_idx <= target]
        if len(available) > 0:
            rebal_dates.append(available[-1])
    
    rebal_dates = sorted(set(rebal_dates))
    if len(rebal_dates) < 5:
        print(f"ERROR: Only {len(rebal_dates)} rebalance dates found")
        return None
    
    print(f"Rebalance dates: {len(rebal_dates)} monthly occurrences\n")
    
    tf = TIMEFRAME_CONFIGS["monthly"]
    freq = tf["resample"]
    
    # Backtest loop
    period_rets = []
    bench_rets = []
    holdings_log = []
    prev_holdings = set()
    
    for i in range(len(rebal_dates) - 1):
        trade_date = rebal_dates[i]
        next_date = rebal_dates[i + 1]
        
        # Get benchmark resampled data up to trade date
        bres = bench.loc[:trade_date].resample(freq).last().dropna()
        if len(bres) < tf["sma_window"] + 5:
            continue
        
        # Calculate RS scores for all stocks
        rs_raw = {}
        res_cache = {}
        daily_cache = {}
        
        for s, c in daily.items():
            cd = c.loc[:trade_date].dropna()
            if len(cd) < 260:
                continue
            
            cr = cd.resample(freq).last().dropna()
            res_cache[s] = cr
            daily_cache[s] = cd
            
            rs = calculate_rs_score(cr, bres, tf["rs_periods"])
            if rs:
                rs_raw[s] = rs
        
        rs_ranked = rank_universe(rs_raw)
        
        # Calculate sector breadth
        breadth = {}
        for name, syms in SECTORS.items():
            sd = {s: pd.DataFrame({"Close": daily_cache[s]}) 
                  for s in syms if s in daily_cache}
            if sd:
                breadth[name] = calculate_sector_breadth(sd)
        
        # Score and rank stocks
        scored = []
        for s in res_cache:
            trend = check_trend(daily_cache[s])
            if not trend or not trend["above_200dma"]:  # Must be above 200-DMA
                continue
            
            rrg = calculate_rrg(res_cache[s], bres, tf["sma_window"], 
                              tf["roc_lookback"], tf["tail_length"])
            score = compute_rotation_score(rrg, rs_ranked.get(s), trend, 
                                          breadth.get(_SECTOR_OF.get(s, ""), {}))
            scored.append((s, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Select top-N stocks
        picks = set([s for s, _ in scored[:top_n]])
        
        # Calculate holdings changes
        stocks_to_buy = picks - prev_holdings
        stocks_to_sell = prev_holdings - picks
        turnover = (len(stocks_to_buy) + len(stocks_to_sell)) / max(len(picks), 1)
        
        # Calculate period return
        if picks:
            returns = []
            for s in picks:
                cs = daily[s]
                p0 = cs.loc[:trade_date]
                p1 = cs.loc[:next_date]
                if len(p0) > 0 and len(p1) > 0:
                    ret = float(p1.iloc[-1] / p0.iloc[-1] - 1)
                    returns.append(ret)
            
            gross = float(np.mean(returns)) if returns else 0.0
            net = gross - turnover * (cost_bps / 10000.0)
            period_rets.append(net)
        else:
            period_rets.append(0.0)
        
        # Benchmark return
        bench_ret = float(bench.loc[next_date] / bench.loc[trade_date] - 1)
        bench_rets.append(bench_ret)
        
        holdings_log.append({
            "date": trade_date.date(),
            "n_holdings": len(picks),
            "turnover": turnover,
            "strategy_return": period_rets[-1] * 100,
            "benchmark_return": bench_ret * 100
        })
        
        prev_holdings = picks
    
    if not period_rets:
        print("ERROR: No periods evaluated")
        return None
    
    # Calculate metrics
    ppy = 12  # Monthly periods
    
    strat_eq = pd.Series(np.cumprod([1.0] + [1 + r for r in period_rets]))
    bench_eq = pd.Series(np.cumprod([1.0] + [1 + r for r in bench_rets]))
    post_eq = pd.Series(np.cumprod([1.0] + [1 + r - stcg * max(r, 0) for r in period_rets]))
    
    def calc_metrics(equity):
        if len(equity) < 2:
            return {}
        total = float(equity.iloc[-1] / equity.iloc[0] - 1)
        years_span = max((len(equity) - 1) / ppy, 0.01)
        cagr = float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years_span) - 1)
        rets = equity.pct_change().dropna()
        vol = float(rets.std() * np.sqrt(ppy)) if len(rets) > 1 else 0.0
        sharpe = float((rets.mean() * ppy) / (rets.std() * np.sqrt(ppy))) if len(rets) > 1 and rets.std() > 0 else 0.0
        dd = float((equity / equity.cummax() - 1).min())
        return {"total": total * 100, "cagr": cagr * 100, "vol": vol * 100, 
                "sharpe": sharpe, "maxdd": dd * 100, "years": years_span}
    
    s_metrics = calc_metrics(strat_eq)
    b_metrics = calc_metrics(bench_eq)
    p_metrics = calc_metrics(post_eq)
    
    wins = sum(1 for s, b in zip(period_rets, bench_rets) if s > b)
    pos_months = sum(1 for r in period_rets if r > 0)
    
    # Print results
    print(f"{'METRIC':<20} {'STRATEGY':>15} {'NIFTY 500':>15}")
    print("-" * 52)
    print(f"{'CAGR':<20} {s_metrics['cagr']:>14.2f}% {b_metrics['cagr']:>14.2f}%")
    print(f"{'Total Return':<20} {s_metrics['total']:>14.2f}% {b_metrics['total']:>14.2f}%")
    print(f"{'Max Drawdown':<20} {s_metrics['maxdd']:>14.2f}% {b_metrics['maxdd']:>14.2f}%")
    print(f"{'Volatility (Ann.)':<20} {s_metrics['vol']:>14.2f}% {b_metrics['vol']:>14.2f}%")
    print(f"{'Sharpe Ratio':<20} {s_metrics['sharpe']:>15.2f} {b_metrics['sharpe']:>15.2f}")
    print("-" * 52)
    print(f"{'Alpha (CAGR)':<20} {s_metrics['cagr'] - b_metrics['cagr']:>14.2f}%")
    print(f"{'Win Rate':<20} {100*wins/len(period_rets):>14.1f}%")
    print(f"{'Positive Months':<20} {100*pos_months/len(period_rets):>14.1f}%")
    print()
    print(f"POST-TAX CAGR (20% STCG): {p_metrics['cagr']:.2f}% vs Benchmark {b_metrics['cagr']:.2f}%")
    print(f"Months Evaluated: {len(period_rets)} | Period: ~{s_metrics['years']:.1f} years")
    print()
    
    return {
        "strategy": s_metrics,
        "benchmark": b_metrics,
        "post_tax": p_metrics,
        "wins": wins,
        "total_months": len(period_rets),
        "alpha_cagr": s_metrics['cagr'] - b_metrics['cagr'],
        "win_rate": 100 * wins / len(period_rets),
        "pos_months": 100 * pos_months / len(period_rets),
        "holdings_log": holdings_log,
    }

if __name__ == "__main__":
    # Run 3-year and 5-year backtests
    results_3yr = run_backtest(years=3, top_n=20, exit_rank=60)
    results_5yr = run_backtest(years=5, top_n=20, exit_rank=60)
    results_6yr = run_backtest(years=6, top_n=20, exit_rank=60)


    if results_3yr and results_5yr and results_6yr:
        print(f"\n{'='*80}")
        print("COMPARISON: 3-Year vs 5-Year vs 6-Year Strategy Performance")
        print(f"{'='*80}\n")
        print(f"{'Metric':<20} {'3-Year':>15} {'5-Year':>15} {'6-Year':>15}")
        print("-" * 70)
        print(f"{'CAGR':<20} {results_3yr['strategy']['cagr']:>14.2f}% {results_5yr['strategy']['cagr']:>14.2f}% {results_6yr['strategy']['cagr']:>14.2f}%")
        print(f"{'Total Return':<20} {results_3yr['strategy']['total']:>14.2f}% {results_5yr['strategy']['total']:>14.2f}% {results_6yr['strategy']['total']:>14.2f}%")
        print(f"{'Sharpe':<20} {results_3yr['strategy']['sharpe']:>15.2f} {results_5yr['strategy']['sharpe']:>15.2f} {results_6yr['strategy']['sharpe']:>15.2f}")
        print(f"{'Max DD':<20} {results_3yr['strategy']['maxdd']:>14.2f}% {results_5yr['strategy']['maxdd']:>14.2f}% {results_6yr['strategy']['maxdd']:>14.2f}%")
