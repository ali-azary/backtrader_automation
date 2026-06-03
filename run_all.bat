@echo off

set ASSETS=BTC-USD
set PERIOD=1y
set INTERVAL=1d
set BENCHMARK=BTC-USD
set STAKE_PERCENT=95

for %%A in (%ASSETS%) do (
    python run_backtest.py --symbol %%A --period %PERIOD% --interval %INTERVAL% --benchmark %BENCHMARK% --stake-percent %STAKE_PERCENT% --strategies strategies --out results
)

python build_dashboard.py --results results --mode assets

echo Done.
