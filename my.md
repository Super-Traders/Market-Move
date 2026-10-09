SUPER MOmentum 

python current_stock_picks.py --as-of 2026-09-25




python portfolio_strategy_backtest_rank.py --years 3 --top-n 20 --exit-rank 60 --initial-capital  1000000

python portfolio_strategy_backtest_rank.py --years 3 --sweep --sweep-top-n 5,10,15,20,25,30 --sweep-exit-ranks 60,70,80

python portfolio_strategy_backtest_rank.py --years 5 --sweep --sweep-top-n 5,10,15,20,25,30 --sweep-exit-ranks 60,70,80




# Backtest for Anuslsos 
OLD 
python portfolio_strategy_backtest.py --years 1 --top-n 20 --exit-rank 60 --initial-capital  1000000

python portfolio_strategy_backtest.py --years 3 --sweep --sweep-top-n 5,10,15,20,25,30 --sweep-exit-ranks 60,70,80

python portfolio_strategy_backtest.py --years 5 --sweep --sweep-top-n 5,6,7,8,9,10 --sweep-exit-ranks 60,65,70


python portfolio_strategy_backtest.py --years 1 --top-n 20 --exit-rank 60 --initial-capital  1000000


FIND SWEET Stock Count

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

python cli.py scan --timeframe monthly --top 100   --export out100.csv 

# BENCHMARK NIFTY 50

python cli.py scan -t daily  -b "NIFTY 50" --top 10
python cli.py scan -t weekly  -b "NIFTY 50" --top 10
python cli.py scan -t monthly  -b "NIFTY 50" --top 10


pyt


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

# benchmark NIFTY 50...
                                              Rotation Scan — daily                                               
┏━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┓
┃ #    ┃ Stock        ┃ Sector                   ┃ Quadrant     ┃  RS Rank ┃ 200-DMA      ┃    Breadth ┃   Score ┃
┡━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━┩
│ 1    │ LAURUSLABS   │ Healthcare               │ Leading      │      99% │ ✓ +48.2%     │        73% │      94 │
│ 2    │ CPPLUS       │ Capital Goods            │ Leading      │      99% │ ✓ +48.9%     │        52% │      90 │
│ 3    │ EMCURE       │ Healthcare               │ Leading      │      86% │ ✓ +20.4%     │        73% │      90 │
│ 4    │ SONACOMS     │ Automobile and Auto      │ Leading      │      96% │ ✓ +32.7%     │        53% │      89 │
│      │              │ Components               │              │          │              │            │         │
│ 5    │ POLYMED      │ Healthcare               │ Leading      │      83% │ ✓ +10.1%     │        73% │      89 │
│ 6    │ FIVESTAR     │ Financial Services       │ Leading      │      89% │ ✓ +10.8%     │        47% │      86 │
│ 7    │ WOCKPHARMA   │ Healthcare               │ Leading      │      95% │ ✓ +27.9%     │        73% │      85 │
│ 8    │ ACMESOLAR    │ Power                    │ Leading      │      97% │ ✓ +41.8%     │        29% │      85 │
│ 9    │ NH           │ Healthcare               │ Leading      │      72% │ ✓ +2.2%      │        73% │      85 │
│ 10   │ APOLLOHOSP   │ Healthcare               │ Leading      │      71% │ ✓ +9.7%      │        73% │      84 │
└──────┴──────────────┴──────────────────────────┴──────────────┴──────────┴──────────────┴────────────┴─────────┘



                                              Rotation Scan — weekly                                              
┏━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┓
┃ #    ┃ Stock        ┃ Sector                   ┃ Quadrant     ┃  RS Rank ┃ 200-DMA      ┃    Breadth ┃   Score ┃
┡━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━┩
│ 1    │ VIJAYA       │ Healthcare               │ Leading      │      93% │ ✓ +28.6%     │        73% │      92 │
│ 2    │ AJANTPHARM   │ Healthcare               │ Leading      │      85% │ ✓ +15.1%     │        73% │      89 │
│ 3    │ LALPATHLAB   │ Healthcare               │ Leading      │      85% │ ✓ +22.6%     │        73% │      89 │
│ 4    │ MEDANTA      │ Healthcare               │ Leading      │      81% │ ✓ +18.7%     │        73% │      88 │
│ 5    │ LAURUSLABS   │ Healthcare               │ Leading      │      99% │ ✓ +48.2%     │        73% │      87 │
│ 6    │ NYKAA        │ Consumer Services        │ Leading      │      92% │ ✓ +23.3%     │        46% │      86 │
│ 7    │ GLAND        │ Healthcare               │ Leading      │      96% │ ✓ +39.0%     │        73% │      86 │
│ 8    │ DIVISLAB     │ Healthcare               │ Leading      │      95% │ ✓ +34.1%     │        73% │      85 │
│ 9    │ SHYAMMETL    │ Capital Goods            │ Leading      │      84% │ ✓ +19.5%     │        52% │      85 │
│ 10   │ WOCKPHARMA   │ Healthcare               │ Leading      │      93% │ ✓ +27.9%     │        73% │      85 │
└──────┴──────────────┴──────────────────────────┴──────────────┴──────────┴──────────────┴────────────┴─────────┘


                                             Rotation Scan — monthly                                              
┏━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┓
┃ #    ┃ Stock        ┃ Sector                   ┃ Quadrant     ┃  RS Rank ┃ 200-DMA      ┃    Breadth ┃   Score ┃
┡━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━┩
│ 1    │ LAURUSLABS   │ Healthcare               │ Leading      │      99% │ ✓ +48.2%     │        73% │      94 │
│ 2    │ CAPLIPOINT   │ Healthcare               │ Leading      │      90% │ ✓ +24.2%     │        73% │      91 │
│ 3    │ MEDANTA      │ Healthcare               │ Leading      │      82% │ ✓ +18.7%     │        73% │      88 │
│ 4    │ NAVINFLUOR   │ Chemicals                │ Leading      │      94% │ ✓ +24.7%     │        46% │      87 │
│ 5    │ CARTRADE     │ Consumer Services        │ Leading      │      93% │ ✓ +27.0%     │        46% │      87 │
│ 6    │ SAREGAMA     │ Media Entertainment &    │ Leading      │      84% │ ✓ +25.2%     │        60% │      86 │
│      │              │ Publication              │              │          │              │            │         │
│ 7    │ ACUTAAS      │ Healthcare               │ Leading      │      98% │ ✓ +26.2%     │        73% │      86 │
│ 8    │ DIVISLAB     │ Healthcare               │ Leading      │      96% │ ✓ +34.1%     │        73% │      86 │
│ 9    │ VIJAYA       │ Healthcare               │ Leading      │      94% │ ✓ +28.6%     │        73% │      85 │
│ 10   │ WOCKPHARMA   │ Healthcare               │ Leading      │      93% │ ✓ +27.9%     │        73% │      85 │
└──────┴──────────────┴──────────────────────────┴──────────────┴──────────┴──────────────┴────────────┴─────────┘

# benchmark NIFTY 500

                                              Rotation Scan — daily                                               
┏━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┓
┃ #    ┃ Stock        ┃ Sector                   ┃ Quadrant     ┃  RS Rank ┃ 200-DMA      ┃    Breadth ┃   Score ┃
┡━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━┩
│ 1    │ LAURUSLABS   │ Healthcare               │ Leading      │      99% │ ✓ +46.9%     │        69% │      93 │
│ 2    │ SUNTV        │ Media Entertainment &    │ Leading      │      92% │ ✓ +12.1%     │        80% │      93 │
│      │              │ Publication              │              │          │              │            │         │
│ 3    │ LALPATHLAB   │ Healthcare               │ Leading      │      94% │ ✓ +21.1%     │        69% │      92 │
│ 4    │ FINCABLES    │ Capital Goods            │ Leading      │      99% │ ✓ +45.9%     │        54% │      90 │
│ 5    │ AJANTPHARM   │ Healthcare               │ Leading      │      89% │ ✓ +16.9%     │        69% │      90 │
│ 6    │ RRKABEL      │ Capital Goods            │ Leading      │      97% │ ✓ +30.3%     │        54% │      90 │
│ 7    │ ACE          │ Capital Goods            │ Leading      │      95% │ ✓ +28.2%     │        54% │      89 │
│ 8    │ CARBORUNIV   │ Capital Goods            │ Leading      │      95% │ ✓ +28.7%     │        54% │      89 │
│ 9    │ REDINGTON    │ Services                 │ Leading      │      99% │ ✓ +47.6%     │        43% │      88 │
│ 10   │ AEGISLOG     │ Oil Gas & Consumable     │ Leading      │      99% │ ✓ +49.8%     │        41% │      88 │
│      │              │ Fuels                    │              │          │              │            │         │
└──────┴──────────────┴──────────────────────────┴──────────────┴──────────┴──────────────┴────────────┴─────────┘

                                               Rotation Scan — weekly                                              
┏━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┓
┃ #    ┃ Stock        ┃ Sector                   ┃ Quadrant     ┃  RS Rank ┃ 200-DMA      ┃    Breadth ┃   Score ┃
┡━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━┩
│ 1    │ PFOCUS       │ Media Entertainment &    │ Leading      │      93% │ ✓ +16.0%     │        80% │      94 │
│      │              │ Publication              │              │          │              │            │         │
│ 2    │ ACUTAAS      │ Healthcare               │ Leading      │      97% │ ✓ +22.2%     │        69% │      93 │
│ 3    │ GLAND        │ Healthcare               │ Leading      │      96% │ ✓ +34.6%     │        69% │      92 │
│ 4    │ VIJAYA       │ Healthcare               │ Leading      │      93% │ ✓ +19.9%     │        69% │      92 │
│ 5    │ SAREGAMA     │ Media Entertainment &    │ Leading      │      86% │ ✓ +22.9%     │        80% │      91 │
│      │              │ Publication              │              │          │              │            │         │
│ 6    │ AJANTPHARM   │ Healthcare               │ Leading      │      91% │ ✓ +16.7%     │        69% │      91 │
│ 7    │ KIRLOSENG    │ Capital Goods            │ Leading      │      99% │ ✓ +31.8%     │        54% │      90 │
│ 8    │ PVRINOX      │ Media Entertainment &    │ Leading      │      84% │ ✓ +18.4%     │        80% │      90 │
│      │              │ Publication              │              │          │              │            │         │
│ 9    │ APARINDS     │ Capital Goods            │ Leading      │      98% │ ✓ +37.7%     │        54% │      90 │
│ 10   │ IPCALAB      │ Healthcare               │ Leading      │      89% │ ✓ +18.2%     │        69% │      90 │
└──────┴──────────────┴──────────────────────────┴──────────────┴──────────┴──────────────┴────────────┴─────────┘

                                             Rotation Scan — monthly                                              
┏━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┓
┃ #    ┃ Stock        ┃ Sector                   ┃ Quadrant     ┃  RS Rank ┃ 200-DMA      ┃    Breadth ┃   Score ┃
┡━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━┩
│ 1    │ LAURUSLABS   │ Healthcare               │ Leading      │      99% │ ✓ +45.8%     │        69% │      94 │
│ 2    │ ACUTAAS      │ Healthcare               │ Leading      │      97% │ ✓ +22.2%     │        69% │      93 │
│ 3    │ CAPLIPOINT   │ Healthcare               │ Leading      │      94% │ ✓ +28.2%     │        69% │      92 │
│ 4    │ SAREGAMA     │ Media Entertainment &    │ Leading      │      84% │ ✓ +22.9%     │        80% │      90 │
│      │              │ Publication              │              │          │              │            │         │
│ 5    │ FINCABLES    │ Capital Goods            │ Leading      │      98% │ ✓ +44.6%     │        54% │      90 │
│ 6    │ AJANTPHARM   │ Healthcare               │ Leading      │      89% │ ✓ +16.7%     │        69% │      90 │
│ 7    │ SUNTV        │ Media Entertainment &    │ Leading      │      78% │ ✓ +12.2%     │        80% │      88 │
│      │              │ Publication              │              │          │              │            │         │
│ 8    │ CARBORUNIV   │ Capital Goods            │ Leading      │      93% │ ✓ +28.4%     │        54% │      88 │
│ 9    │ SONACOMS     │ Automobile and Auto      │ Leading      │      98% │ ✓ +35.1%     │        45% │      88 │
│      │              │ Components               │              │          │              │            │         │
│ 10   │ ZYDUSLIFE    │ Healthcare               │ Leading      │      80% │ ✓ +14.8%     │        69% │      87 │
└──────┴──────────────┴──────────────────────────┴──────────────┴──────────┴──────────────┴────────────┴─────────┘



 # Sector Rotation 

                                                 Sector Rotation — daily                                                 
┏━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ #    ┃ Sector                       ┃ Quadrant     ┃   RS-Ratio ┃     RS-Mom ┃  Breadth 200 ┃   Breadth 50 ┃ Signal   ┃
┡━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ 1    │ Healthcare                   │ Leading      │     104.00 │     101.75 │          73% │          48% │ Strong   │
│ 2    │ Media Entertainment &        │ Leading      │     102.62 │     101.67 │          60% │          60% │ Mixed    │
│      │ Publication                  │              │            │            │              │              │          │
│ 3    │ Services                     │ Leading      │     101.61 │     101.62 │          43% │          29% │ Mixed    │
│ 4    │ Consumer Durables            │ Leading      │     102.76 │     101.09 │          38% │          25% │ Weak     │
│ 5    │ Fast Moving Consumer Goods   │ Leading      │     102.96 │     102.83 │          32% │          14% │ Weak     │
│ 6    │ Power                        │ Leading      │     101.51 │     101.38 │          29% │           6% │ Weak     │
│ 7    │ Consumer Services            │ Weakening    │     101.42 │      99.41 │          46% │          41% │ Mixed    │
│ 8    │ Diversified                  │ Improving    │      98.63 │     101.16 │          33% │           0% │ Weak     │
│ 9    │ Construction                 │ Weakening    │     101.38 │      98.78 │          23% │          15% │ Weak     │
│ 10   │ Textiles                     │ Lagging      │      96.38 │      98.59 │          60% │          20% │ Mixed    │
│ 11   │ Automobile and Auto          │ Lagging      │      95.97 │      97.31 │          53% │          26% │ Mixed    │
│      │ Components                   │              │            │            │              │              │          │
│ 12   │ Capital Goods                │ Lagging      │      96.71 │      98.11 │          52% │          27% │ Mixed    │
│ 13   │ Metals & Mining              │ Weakening    │     100.50 │      99.48 │          28% │           6% │ Weak     │
│ 14   │ Oil Gas & Consumable Fuels   │ Lagging      │      99.39 │      99.03 │          47% │          41% │ Mixed    │
│ 15   │ Financial Services           │ Lagging      │      96.36 │      96.59 │          47% │          27% │ Mixed    │
│ 16   │ Chemicals                    │ Lagging      │      99.82 │      98.68 │          46% │          23% │ Mixed    │
│ 17   │ Telecommunication            │ Lagging      │      95.96 │      97.03 │          40% │          20% │ Mixed    │
│ 18   │ Realty                       │ Lagging      │      98.50 │      98.56 │          27% │           9% │ Weak     │
│ 19   │ Information Technology       │ Lagging      │      95.82 │      97.43 │          33% │          18% │ Weak     │
│ 20   │ Construction Materials       │ Lagging      │      95.82 │      99.21 │           9% │           0% │ Weak     │
└──────┴──────────────────────────────┴──────────────┴────────────┴────────────┴──────────────┴──────────────┴──────────┘




                                                Sector Rotation — weekly                                                 
┏━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ #    ┃ Sector                       ┃ Quadrant     ┃   RS-Ratio ┃     RS-Mom ┃  Breadth 200 ┃   Breadth 50 ┃ Signal   ┃
┡━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ 1    │ Healthcare                   │ Leading      │     103.01 │     102.80 │          73% │          48% │ Strong   │
│ 2    │ Media Entertainment &        │ Leading      │     102.76 │     101.52 │          60% │          60% │ Mixed    │
│      │ Publication                  │              │            │            │              │              │          │
│ 3    │ Consumer Services            │ Leading      │     102.67 │     102.00 │          46% │          41% │ Mixed    │
│ 4    │ Services                     │ Leading      │     103.25 │     103.04 │          43% │          29% │ Mixed    │
│ 5    │ Consumer Durables            │ Leading      │     102.85 │     100.96 │          38% │          25% │ Weak     │
│ 6    │ Fast Moving Consumer Goods   │ Leading      │     101.28 │     102.94 │          32% │          14% │ Weak     │
│ 7    │ Metals & Mining              │ Leading      │     101.44 │     100.62 │          28% │           6% │ Weak     │
│ 8    │ Chemicals                    │ Leading      │     100.94 │     100.56 │          46% │          23% │ Mixed    │
│ 9    │ Construction                 │ Improving    │      99.93 │     101.46 │          23% │          15% │ Weak     │
│ 10   │ Oil Gas & Consumable Fuels   │ Weakening    │     100.03 │      97.84 │          47% │          41% │ Mixed    │
│ 11   │ Textiles                     │ Lagging      │      96.61 │      98.35 │          60% │          20% │ Mixed    │
│ 12   │ Automobile and Auto          │ Lagging      │      96.57 │      97.11 │          53% │          26% │ Mixed    │
│      │ Components                   │              │            │            │              │              │          │
│ 13   │ Capital Goods                │ Lagging      │      96.75 │      97.70 │          52% │          27% │ Mixed    │
│ 14   │ Financial Services           │ Lagging      │      97.54 │      98.07 │          47% │          27% │ Mixed    │
│ 15   │ Diversified                  │ Lagging      │      98.65 │      99.60 │          33% │           0% │ Weak     │
│ 16   │ Telecommunication            │ Lagging      │      96.83 │      97.53 │          40% │          20% │ Mixed    │
│ 17   │ Power                        │ Lagging      │      99.60 │      98.65 │          29% │           6% │ Weak     │
│ 18   │ Information Technology       │ Lagging      │      96.90 │      96.95 │          33% │          18% │ Weak     │
│ 19   │ Realty                       │ Lagging      │      99.33 │      98.70 │          27% │           9% │ Weak     │
│ 20   │ Construction Materials       │ Lagging      │      96.62 │      97.87 │           9% │           0% │ Weak     │
└──────┴──────────────────────────────┴──────────────┴────────────┴────────────┴──────────────┴──────────────┴──────────┘



                                                Sector Rotation — monthly                                                
┏━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ #    ┃ Sector                       ┃ Quadrant     ┃   RS-Ratio ┃     RS-Mom ┃  Breadth 200 ┃   Breadth 50 ┃ Signal   ┃
┡━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ 1    │ Healthcare                   │ Leading      │     102.31 │     101.38 │          73% │          48% │ Strong   │
│ 2    │ Media Entertainment &        │ Leading      │     102.44 │     101.23 │          60% │          60% │ Mixed    │
│      │ Publication                  │              │            │            │              │              │          │
│ 3    │ Consumer Services            │ Leading      │     101.35 │     102.16 │          46% │          41% │ Mixed    │
│ 4    │ Chemicals                    │ Leading      │     101.11 │     102.05 │          46% │          23% │ Mixed    │
│ 5    │ Services                     │ Leading      │     100.78 │     101.04 │          43% │          29% │ Mixed    │
│ 6    │ Consumer Durables            │ Leading      │     102.04 │     101.34 │          38% │          25% │ Weak     │
│ 7    │ Fast Moving Consumer Goods   │ Leading      │     100.11 │     102.23 │          32% │          14% │ Weak     │
│ 8    │ Power                        │ Leading      │     100.39 │     100.30 │          29% │           6% │ Weak     │
│ 9    │ Textiles                     │ Improving    │      97.25 │     100.50 │          60% │          20% │ Mixed    │
│ 10   │ Realty                       │ Leading      │     100.31 │     100.81 │          27% │           9% │ Weak     │
│ 11   │ Financial Services           │ Improving    │      98.25 │     100.47 │          47% │          27% │ Mixed    │
│ 12   │ Oil Gas & Consumable Fuels   │ Weakening    │     101.17 │      99.57 │          47% │          41% │ Mixed    │
│ 13   │ Construction                 │ Weakening    │     100.51 │      99.64 │          23% │          15% │ Weak     │
│ 14   │ Automobile and Auto          │ Lagging      │      97.22 │      98.06 │          53% │          26% │ Mixed    │
│      │ Components                   │              │            │            │              │              │          │
│ 15   │ Capital Goods                │ Lagging      │      98.93 │      98.48 │          52% │          27% │ Mixed    │
│ 16   │ Metals & Mining              │ Weakening    │     100.89 │      98.23 │          28% │           6% │ Weak     │
│ 17   │ Diversified                  │ Lagging      │      98.88 │      98.85 │          33% │           0% │ Weak     │
│ 18   │ Telecommunication            │ Lagging      │      97.60 │      98.81 │          40% │          20% │ Mixed    │
│ 19   │ Construction Materials       │ Improving    │      97.21 │     100.66 │           9% │           0% │ Weak     │
│ 20   │ Information Technology       │ Lagging      │      97.70 │      98.94 │          33% │          18% │ Weak     │
└──────┴──────────────────────────────┴──────────────┴────────────┴────────────┴──────────────┴──────────────┴──────────┘



