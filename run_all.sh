#!/bin/bash

ASSETS=("AAPL" "MSFT" "TSLA" "SPY")
PERIOD="2y"
INTERVAL="1d"
BENCHMARK="SPY"
STAKE_PERCENT="95"

for ASSET in "${ASSETS[@]}"
do
  python run_backtest.py --symbol "$ASSET" --period "$PERIOD" --interval "$INTERVAL" --benchmark "$BENCHMARK" --stake-percent "$STAKE_PERCENT" --strategies strategies --out results
done

python build_dashboard.py --results results --mode assets

echo "Done."
