from portfolio_strategy_backtest import run_backtest

res = run_backtest(r'data/cache.db', years=2, top_n=10, exit_rank=60, buffer_start=31, initial_capital=1000000.0)
first = res['rebal_report'][0]
print('rebal_count=', len(res['rebal_report']))
print('date=', first['date'])
print('cash=', first['cash_balance'])
print('positions=', {k: v['weight_pct'] for k, v in first['positions'].items()})
print('sum_weights=', round(sum(v['weight_pct'] for v in first['positions'].values()), 4))
print('trade_count=', len(first['trade_log']))
print('first_trade=', first['trade_log'][0])
print('last_trade=', first['trade_log'][-1])
