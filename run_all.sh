#!/bin/bash

ASSETS=("AAPL" "MSFT" "TSLA" "SPY")
PERIOD="2y"
INTERVAL="1d"
BENCHMARK="SPY"

for ASSET in "${ASSETS[@]}"
do
  python run_backtest.py --symbol "$ASSET" --period "$PERIOD" --interval "$INTERVAL" --benchmark "$BENCHMARK" --strategies strategies --out results
done

python build_dashboard.py --results results --out dashboard.html

echo "Done."
