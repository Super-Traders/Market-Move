python chart.py RELIANCE --timeframe daily --years 5
python chart.py TCS -t weekly --years 3
python chart.py "IDX:NIFTY 50" -t monthly --output output/nifty50_monthly.html


# SUPER MOmentum 

python current_stock_picks.py --as-of 2026-09-25 --include-below-200dma

python portfolio_smallcase_tracker.py --start-date 2026-04-25 --as-of-date 2026-11-25 --excel-output .\smallcase_portfolio_tracker_from_2026-04-25.xlsx

python portfolio_smallcase_tracker.py --start-date 2026-09-25 --as-of-date 2026-10-25 --excel-output .\smallcase_portfolio_tracker_from_2026-09-25.xlsx



python portfolio_strategy_backtest_rank.py --years 10 --top-n 20 --exit-rank 60 --initial-capital  1000000

python portfolio_strategy_backtest_rank.py --years 3 --sweep --sweep-top-n 5,10,15,20,25,30 --sweep-exit-ranks 60,70,80

python portfolio_strategy_backtest_rank.py --years 5 --sweep --sweep-top-n 5,10,15,20,25,30 --sweep-exit-ranks 60,70,80

python portfolio_strategy_backtest_rank.py --years 10 --sweep --sweep-top-n 10,15,20,25,30 --sweep-exit-ranks 60,70,80

## ARCHIVE 
# Export
python cli.py update
python data/cache_archive.py export
git add .
git commit -m "update "
git push
 # Import
# python data\cache_archive.py import --replace

# Backtest for Anuslsos 
# OLD 
python portfolio_strategy_backtest.py --years 1 --top-n 20 --exit-rank 60 --initial-capital  1000000

python portfolio_strategy_backtest.py --years 3 --sweep --sweep-top-n 5,10,15,20,25,30 --sweep-exit-ranks 60,70,80

python portfolio_strategy_backtest.py --years 5 --sweep --sweep-top-n 5,6,7,8,9,10 --sweep-exit-ranks 60,65,70


python portfolio_strategy_backtest.py --years 1 --top-n 20 --exit-rank 60 --initial-capital  1000000

python portfolio_strategy_backtest.py --years 10 --top-n 20 --exit-rank 60 --initial-capital  1000000



# FIND SWEET Stock Count

python portfolio_strategy_backtest.py --years 3 --sweep --sweep-top-n 15,20,25,30 --sweep-exit-ranks 60,70,80



# Warm the cache once (parallel fetch; first cold run is the slow one).
.venv/bin/python cli.py update

# RUN APP
streamlit run app.py --server.port 8502

# BACKTEST
 python backtest_research.py


 ==============================================================================
RESEARCH BACKTEST — survivorship-biased (upward), ~6yr window, NOT advice
==============================================================================

  Timeframe: weekly  |  top-20  |  quarterly rebalance  |  cost 30bps/turnover
  Period: 2020-09-30 -> 2026-09-30  (24 quarters, 6.0 yrs)
  metric              STRATEGY   NIFTY 500
  CAGR                   37.3%       15.4%
  Total return          569.2%      136.3%
  Max drawdown          -20.2%      -15.3%
  Volatility             34.8%       17.9%
  Sharpe                  1.10        0.90
  Alpha (CAGR vs bench): +21.9%   |   quarters beating bench: 70.8%   |   positive quarters: 66.7%
  Indicative POST-TAX CAGR (20% STCG, conservative): 26.9%   vs benchmark 15.4%


  Timeframe: monthly  |  top-20  |  quarterly rebalance  |  cost 30bps/turnover
  Period: 2020-09-30 -> 2026-09-30  (24 quarters, 6.0 yrs)
  metric              STRATEGY   NIFTY 500
  CAGR                   44.0%       15.4%
  Total return          792.6%      136.3%
  Max drawdown          -16.0%      -15.3%
  Volatility             30.6%       17.9%
  Sharpe                  1.38        0.90
  Alpha (CAGR vs bench): +28.6%   |   quarters beating bench: 75.0%   |   positive quarters: 66.7%
  Indicative POST-TAX CAGR (20% STCG, conservative): 32.9%   vs benchmark 15.4%

Reminder: today's-Nifty-500 universe overstates returns vs a true point-in-time test.


  Timeframe: weekly  |  top-20  |  quarterly rebalance  |  cost 30bps/turnover
  Period: 2020-09-30 -> 2026-09-30  (24 quarters, 2.0 yrs)
  metric              STRATEGY   NIFTY 500
  CAGR                  158.7%       53.7%
  Total return          569.2%      136.3%
  Max drawdown          -20.2%      -15.3%
  Volatility             60.3%       31.0%
  Sharpe                  1.90        1.56
  Alpha (CAGR vs bench): +105.0%   |   quarters beating bench: 70.8%   |   positive quarters: 66.7%
  Indicative POST-TAX CAGR (20% STCG, conservative): 104.5%   vs benchmark 53.7%

 Timeframe: monthly  |  top-20  |  quarterly rebalance  |  cost 30bps/turnover
  Period: 2020-09-30 -> 2026-09-30  (24 quarters, 2.0 yrs)
  metric              STRATEGY   NIFTY 500
  CAGR                  198.8%       53.7%
  Total return          792.6%      136.3%
  Max drawdown          -16.0%      -15.3%
  Volatility             53.0%       31.0%
  Sharpe                  2.39        1.56
  Alpha (CAGR vs bench): +145.1%   |   quarters beating bench: 75.0%   |   positive quarters: 66.7%
  Indicative POST-TAX CAGR (20% STCG, conservative): 134.8%   vs benchmark 53.7%

Reminder: today's-Nifty-500 universe overstates returns vs a true point-in-time test.


##

python -c "import sqlite3; from config import DB_PATH; conn = sqlite3.connect(DB_PATH); cursor = conn.cursor(); indices = ['IDX:NIFTY 50', 'IDX:NIFTY 500', 'IDX:NIFTY MIDCAP 150']; print('Index Data Summary:\n'); for idx in indices: cursor.execute('SELECT COUNT(*), MIN(date), MAX(date) FROM ohlcv WHERE symbol = ?', (idx,)); result = cursor.fetchone(); print(f'{idx}: {result[0]} records from {result[1]} to {result[2]}'); conn.close()"




# Top stocks across all sectors

python cli.py scan --timeframe daily --top 20
python cli.py scan --timeframe weekly --top 20
python cli.py scan --timeframe monthly --top 20

# Interactive OHLCV chart (opens in browser; use --no-open to only save HTML)
python chart.py RELIANCE --timeframe daily --years 5
python chart.py TCS -t weekly --years 3
python chart.py "IDX:NIFTY 50" -t monthly --output output/nifty50_monthly.html

python cli.py scan --timeframe monthly --top 100   --export out100.csv 

# BENCHMARK NIFTY 50

python cli.py scan -t daily  -b "NIFTY 50" --top 10
python cli.py scan -t weekly  -b "NIFTY 50" --top 10
python cli.py scan -t monthly  -b "NIFTY 50" --top 10


python cli.py scan -t daily  -b "NIFTY MIDCAP 150"
python cli.py scan -t daily  -b "NIFTY 50"
python cli.py scan -t daily  -b "BANKNIFTY"



# SECTOR 
python cli.py sectors --timeframe daily  
python cli.py sectors --timeframe weekly
python cli.py sectors --timeframe monthly

python cli.py sectors --timeframe daily  -b "NIFTY 50"   
python cli.py sectors --timeframe weekly    -b "NIFTY 50"   
python cli.py sectors --timeframe monthly   -b "NIFTY 50"   



 python cli.py scan -t weekly -n 50 --export out.csv 
 python cli.py scan -t daily  -n 50 --export out.csv 


# Warm the cache once (parallel fetch; first cold run is the slow one).
 python cli.py update

# Top stocks across all sectors
 python cli.py scan -t weekly --top 30
 python cli.py scan -t weekly -n 50 --export out.csv      # + CSV export

# Sector-level rotation map
 python cli.py sectors --timeframe monthly

# Drill into one sector (partial names match, e.g. "Defence", "Bank")

# Available: Automobile and Auto Components, Capital Goods, Chemicals, Construction, Construction Materials, Consumer Durables, Consumer Services, Diversified, Fast Moving Consumer Goods, Financial Services, Healthcare, Information Technology, Media Entertainment & Publication, Metals & Mining, Oil Gas & Consumable Fuels, Power, Realty, Services, Telecommunication, Textiles

 python cli.py sector "Nifty Bank" -t weekly

# Single-stock full profile
 python cli.py stock RELIANCE -t weekly

# Override the benchmark on any command
 python cli.py scan -b "NIFTY 50"

 python cli.py scan -b "NIFTY 50"  -t daily

#      