python cli.py scan --timeframe daily --top 20  > outdaily.MD
python cli.py scan --timeframe weekly --top 20  >> outdaily.MD
python cli.py scan --timeframe monthly --top 20  >> outdaily.MD

@REM  python cli.py scan --timeframe monthly --top 100   --export out100.csv 

# BENCHMARK NIFTY 50

python cli.py scan -t daily  -b "NIFTY 50" --top 10      >> outdaily.MD
python cli.py scan -t weekly  -b "NIFTY 50" --top 10     >> outdaily.MD
python cli.py scan -t monthly  -b "NIFTY 50" --top 10    >> outdaily.MD

