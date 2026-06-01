@echo off

set ASSETS=AAPL MSFT TSLA SPY
set PERIOD=2y
set INTERVAL=1d
set BENCHMARK=SPY

for %%A in (%ASSETS%) do (
    python run_backtest.py --symbol %%A --period %PERIOD% --interval %INTERVAL% --benchmark %BENCHMARK% --strategies strategies --out results
)

python build_dashboard.py --results results --mode assets

echo Done.
