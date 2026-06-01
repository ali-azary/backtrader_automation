# Backtrader Strategy Automation Suite

Run a folder of Backtrader strategies across one or more assets, export per-strategy metrics, save custom Matplotlib plots, and build an HTML dashboard.

## What Is Included

- `strategies/` - Backtrader strategy modules.
- `run_backtest.py` - Batch runner for one asset and all strategies.
- `build_dashboard.py` - HTML dashboard generator.
- `run_all.bat` - Windows batch launcher.
- `run_all.sh` - macOS/Linux shell launcher.
- `results/` - Output folder created by runs.

The runner suppresses Backtrader plotting and popup windows. It saves custom Matplotlib PNG files instead.

## Install

```bash
pip install -r requirements.txt
```

## Run One Asset

```bash
python run_backtest.py --symbol AAPL --period 2y --interval 1d --benchmark SPY
```

## Run All Configured Assets

Windows:

```bat
run_all.bat
```

macOS/Linux:

```bash
bash run_all.sh
```

## Build The Dashboard

```bash
python build_dashboard.py --results results --out dashboard.html
```

## Outputs

Each strategy run creates:

- `metrics.csv`
- `equity.csv`
- `comparison.csv`
- `equity_vs_benchmark.png`
- `drawdown_vs_benchmark.png`
- `rolling_return_vs_benchmark.png`
- `daily_returns_hist.png`

Each asset folder also gets:

- `all_metrics.csv`
- `skipped_strategies.csv`

## Notes

This software is for research and education. It is not financial advice. Always validate strategy behavior, data quality, costs, slippage, and risk before using any trading system.
