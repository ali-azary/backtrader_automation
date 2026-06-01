# Backtrader Strategy Automation Suite

Automation tools for the **Backtrader Strategies**.

This suite is designed to help users batch-test a large folder of Backtrader strategies, compare them across assets, export per-strategy metrics, save custom Matplotlib plots, and build an HTML dashboard.

It is especially useful with the Mega Backtrader Strategy Pack because the pack contains many individual strategy files. Running them manually one by one across different assets and time periods would take a lot of time.
Get the Mega Backtrader Strategy Pack here:

https://www.pyquantlab.com/bundles/Mega%20Backtrader%20Strategy%20Pack.html

## Why This Exists

The Mega Backtrader Strategy Pack includes a large collection of ready-to-use Backtrader strategies.

Testing strategies one by one is slow. This automation suite turns the strategy pack into a repeatable research workflow:

1. Place strategy files inside `strategies/`.
2. Run one command.
3. Test every strategy against one or more assets.
4. Export metrics and charts.
5. Review everything in a dashboard.

## What Is Included

* `strategies/` - Backtrader strategy modules.
* `run_backtest.py` - Batch runner for one asset and all strategies.
* `build_dashboard.py` - HTML dashboard generator.
* `run_all.bat` - Windows batch launcher.
* `run_all.sh` - macOS/Linux shell launcher.
* `results/` - Output folder created by runs.

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

* `metrics.csv`
* `equity.csv`
* `comparison.csv`
* `equity_vs_benchmark.png`
* `drawdown_vs_benchmark.png`
* `rolling_return_vs_benchmark.png`
* `daily_returns_hist.png`

Each asset folder also gets:

* `all_metrics.csv`
* `skipped_strategies.csv`

## Metrics

Each strategy is evaluated with useful research metrics, including:

* Final portfolio value
* Total return
* Benchmark return
* Buy-and-hold return
* Excess return vs benchmark
* Excess return vs asset buy-and-hold
* Sharpe ratio
* Max drawdown
* Total trades
* Wins and losses
* Win rate

## Dashboard

The dashboard provides a quick way to compare strategies visually.

It includes:

* Summary metrics table
* Strategy return chart
* Max drawdown chart
* Sharpe ratio chart
* Saved equity, drawdown, rolling return, and return distribution plots

Open the generated file in your browser:

```text
dashboard.html
```

## Recommended Workflow

```bash
pip install -r requirements.txt
bash run_all.sh
python build_dashboard.py --results results --out dashboard.html
```

Then open:

```text
dashboard.html
```

## About The Strategy Pack

The Mega Backtrader Strategy Pack is built for traders, quants, developers, and researchers who want a large Backtrader strategy library for testing, learning, and experimentation.

Product page:

https://www.pyquantlab.com/bundles/Mega%20Backtrader%20Strategy%20Pack.html

Use this automation suite to make the pack easier to explore, benchmark, and compare.

## Notes

This software is for research and education. It is not financial advice. Always validate strategy behavior, data quality, costs, slippage, and risk before using any trading system.
