import argparse
import contextlib
import importlib.util
import os
import sys
from pathlib import Path

import backtrader as bt
import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf


def disable_interactive_plotting():
    matplotlib.use = lambda *args, **kwargs: None
    plt.ioff()
    plt.show = lambda *args, **kwargs: None

    try:
        from matplotlib.figure import Figure

        Figure.show = lambda self, *args, **kwargs: None
    except Exception:
        pass

    def disabled_backtrader_plot(self, *args, **kwargs):
        fig = plt.figure(figsize=kwargs.get("figsize", (12, 6)))
        plt.close(fig)
        return [[fig]]

    bt.Cerebro.plot = disabled_backtrader_plot


disable_interactive_plotting()


@contextlib.contextmanager
def maybe_suppress_output(verbose):
    if verbose:
        yield
        return

    with open(os.devnull, "w", encoding="utf-8") as devnull:
        with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
            yield


class EquityAnalyzer(bt.Analyzer):
    def start(self):
        self.rows = []

    def next(self):
        dt = self.strategy.datas[0].datetime.date(0)
        self.rows.append(
            {
                "date": dt,
                "equity": self.strategy.broker.getvalue(),
            }
        )

    def get_analysis(self):
        return self.rows


def normalize_yfinance_columns(data):
    if isinstance(data.columns, pd.MultiIndex):
        data = data.droplevel(1, axis=1)

    rename_map = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "adj close": "Adj Close",
        "volume": "Volume",
    }
    data.columns = [rename_map.get(str(column).lower(), str(column)) for column in data.columns]
    return data


def download_price_data(symbol, args):
    if args.period:
        data = yf.download(
            symbol,
            period=args.period,
            interval=args.interval,
            auto_adjust=False,
            progress=False,
        )
    else:
        data = yf.download(
            symbol,
            start=args.start,
            end=args.end,
            interval=args.interval,
            auto_adjust=False,
            progress=False,
        )

    data = normalize_yfinance_columns(data).dropna()
    data.index = pd.to_datetime(data.index)
    return data


def drawdown_pct(series):
    peak = series.cummax()
    return (series / peak - 1) * 100


def save_backtest_plots(equity, data, benchmark_data, args, strategy_name, run_dir):
    comparison = equity.copy()
    comparison["date"] = pd.to_datetime(comparison["date"])
    comparison = comparison.set_index("date")
    comparison["strategy_equity"] = comparison["equity"]

    asset_close = data["Close"].reindex(comparison.index).ffill()
    comparison["asset_buy_hold_equity"] = args.cash * asset_close / asset_close.dropna().iloc[0]

    benchmark_label = args.benchmark or f"{args.symbol} Buy & Hold"
    if benchmark_data is not None and not benchmark_data.empty:
        benchmark_close = benchmark_data["Close"].reindex(comparison.index).ffill()
        comparison["benchmark_equity"] = args.cash * benchmark_close / benchmark_close.dropna().iloc[0]
    else:
        comparison["benchmark_equity"] = comparison["asset_buy_hold_equity"]

    comparison = comparison.dropna()
    comparison["strategy_return_pct"] = (comparison["strategy_equity"] / args.cash - 1) * 100
    comparison["asset_buy_hold_return_pct"] = (
        comparison["asset_buy_hold_equity"] / args.cash - 1
    ) * 100
    comparison["benchmark_return_pct"] = (comparison["benchmark_equity"] / args.cash - 1) * 100
    comparison.to_csv(run_dir / "comparison.csv")

    if comparison.empty:
        raise ValueError("No overlapping strategy, asset, and benchmark dates to plot.")

    plt.figure(figsize=(12, 6))
    plt.plot(comparison.index, comparison["strategy_equity"], label=strategy_name, linewidth=2)
    plt.plot(comparison.index, comparison["benchmark_equity"], label=benchmark_label, linewidth=2)
    plt.plot(
        comparison.index,
        comparison["asset_buy_hold_equity"],
        label=f"{args.symbol} Buy & Hold",
        linewidth=1.6,
        alpha=0.8,
    )
    plt.title(f"{args.symbol} - {strategy_name} Equity vs Benchmark")
    plt.xlabel("Date")
    plt.ylabel("Equity")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(run_dir / "equity_vs_benchmark.png", dpi=150)
    plt.savefig(run_dir / "equity.png", dpi=150)
    plt.close()

    plt.figure(figsize=(12, 6))
    plt.plot(
        comparison.index,
        drawdown_pct(comparison["strategy_equity"]),
        label=strategy_name,
        linewidth=2,
    )
    plt.plot(
        comparison.index,
        drawdown_pct(comparison["benchmark_equity"]),
        label=benchmark_label,
        linewidth=2,
    )
    plt.plot(
        comparison.index,
        drawdown_pct(comparison["asset_buy_hold_equity"]),
        label=f"{args.symbol} Buy & Hold",
        linewidth=1.6,
        alpha=0.8,
    )
    plt.title(f"{args.symbol} - {strategy_name} Drawdown vs Benchmark")
    plt.xlabel("Date")
    plt.ylabel("Drawdown (%)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(run_dir / "drawdown_vs_benchmark.png", dpi=150)
    plt.close()

    returns = comparison[["strategy_equity", "benchmark_equity"]].pct_change().dropna()
    returns.columns = [strategy_name, benchmark_label]
    plt.figure(figsize=(12, 6))
    plt.hist(returns[strategy_name] * 100, bins=40, alpha=0.65, label=strategy_name)
    plt.hist(returns[benchmark_label] * 100, bins=40, alpha=0.45, label=benchmark_label)
    plt.title(f"{args.symbol} - {strategy_name} Daily Returns")
    plt.xlabel("Daily Return (%)")
    plt.ylabel("Frequency")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(run_dir / "daily_returns_hist.png", dpi=150)
    plt.close()

    rolling_window = min(63, max(5, len(comparison) // 4))
    rolling = comparison[["strategy_equity", "benchmark_equity"]].pct_change(rolling_window) * 100
    plt.figure(figsize=(12, 6))
    plt.plot(comparison.index, rolling["strategy_equity"], label=strategy_name, linewidth=2)
    plt.plot(comparison.index, rolling["benchmark_equity"], label=benchmark_label, linewidth=2)
    plt.title(f"{args.symbol} - {strategy_name} Rolling Return vs Benchmark")
    plt.xlabel("Date")
    plt.ylabel(f"{rolling_window}-Bar Return (%)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(run_dir / "rolling_return_vs_benchmark.png", dpi=150)
    plt.close()

    benchmark_return_pct = (
        comparison["benchmark_equity"].iloc[-1] / comparison["benchmark_equity"].iloc[0] - 1
    ) * 100
    asset_buy_hold_return_pct = (
        comparison["asset_buy_hold_equity"].iloc[-1]
        / comparison["asset_buy_hold_equity"].iloc[0]
        - 1
    ) * 100
    return benchmark_return_pct, asset_buy_hold_return_pct


parser = argparse.ArgumentParser()
parser.add_argument("--symbol", required=True)
parser.add_argument("--period", default=None)
parser.add_argument("--start", default=None)
parser.add_argument("--end", default=None)
parser.add_argument("--interval", default="1d")
parser.add_argument("--benchmark", default="SPY")
parser.add_argument("--strategies", default="strategies")
parser.add_argument("--cash", type=float, default=10000)
parser.add_argument("--commission", type=float, default=0.001)
parser.add_argument("--out", default="results")
parser.add_argument("--strict", action="store_true")
parser.add_argument("--verbose", action="store_true")
args = parser.parse_args()

symbol_safe = args.symbol.replace("/", "_").replace("=", "_")
out_root = Path(args.out) / symbol_safe
out_root.mkdir(parents=True, exist_ok=True)

data = download_price_data(args.symbol, args)

if data.empty:
    raise ValueError("No data downloaded. Check symbol, period/start/end, and interval.")

benchmark_data = None
if args.benchmark:
    benchmark_data = download_price_data(args.benchmark, args)
    if benchmark_data.empty:
        raise ValueError(f"No benchmark data downloaded for {args.benchmark}.")

all_metrics = []
skipped = []

for strategy_file in Path(args.strategies).glob("*.py"):
    try:
        spec = importlib.util.spec_from_file_location(strategy_file.stem, strategy_file)
        module = importlib.util.module_from_spec(spec)
        sys.modules[strategy_file.stem] = module
        old_argv = sys.argv[:]
        sys.argv = [str(strategy_file)]
        try:
            with maybe_suppress_output(args.verbose):
                spec.loader.exec_module(module)
        finally:
            sys.argv = old_argv
    except BaseException as exc:
        if args.strict:
            raise
        skipped.append(
            {
                "file": strategy_file.name,
                "strategy": "",
                "stage": "import",
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
        continue

    strategy_classes = [
        obj
        for obj in module.__dict__.values()
        if (
            isinstance(obj, type)
            and issubclass(obj, bt.Strategy)
            and obj is not bt.Strategy
            and obj.__module__ == module.__name__
        )
    ]

    if not strategy_classes:
        skipped.append(
            {
                "file": strategy_file.name,
                "strategy": "",
                "stage": "discover",
                "error": "No Backtrader Strategy subclass found.",
            }
        )
        continue

    for strategy_class in strategy_classes:
        strategy_name = strategy_class.__name__
        run_dir = out_root / strategy_name
        run_dir.mkdir(parents=True, exist_ok=True)

        try:
            cerebro = bt.Cerebro()
            cerebro.broker.setcash(args.cash)
            cerebro.broker.setcommission(commission=args.commission)

            feed = bt.feeds.PandasData(dataname=data)
            cerebro.adddata(feed)
            cerebro.addstrategy(strategy_class)

            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
            cerebro.addanalyzer(EquityAnalyzer, _name="equity")

            with maybe_suppress_output(args.verbose):
                result = cerebro.run()[0]
        except Exception as exc:
            if args.strict:
                raise
            skipped.append(
                {
                    "file": strategy_file.name,
                    "strategy": strategy_name,
                    "stage": "run",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue

        final_value = cerebro.broker.getvalue()
        total_return_pct = (final_value / args.cash - 1) * 100

        sharpe = result.analyzers.sharpe.get_analysis().get("sharperatio", None)
        drawdown = result.analyzers.drawdown.get_analysis()
        max_drawdown_pct = drawdown.get("max", {}).get("drawdown", None)

        trades = result.analyzers.trades.get_analysis()
        total_trades = trades.get("total", {}).get("closed", 0)
        won = trades.get("won", {}).get("total", 0)
        lost = trades.get("lost", {}).get("total", 0)
        win_rate = won / total_trades * 100 if total_trades else 0

        equity = pd.DataFrame(result.analyzers.equity.get_analysis())
        if equity.empty:
            equity = pd.DataFrame(
                {
                    "date": data.index,
                    "equity": [final_value] * len(data.index),
                }
            )
        equity.to_csv(run_dir / "equity.csv", index=False)

        try:
            benchmark_return_pct, asset_buy_hold_return_pct = save_backtest_plots(
                equity,
                data,
                benchmark_data,
                args,
                strategy_name,
                run_dir,
            )
        except Exception as exc:
            if args.strict:
                raise
            skipped.append(
                {
                    "file": strategy_file.name,
                    "strategy": strategy_name,
                    "stage": "plot",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue

        metrics = {
            "symbol": args.symbol,
            "strategy": strategy_name,
            "period": args.period,
            "start": args.start,
            "end": args.end,
            "interval": args.interval,
            "benchmark": args.benchmark,
            "cash": args.cash,
            "final_value": final_value,
            "total_return_pct": total_return_pct,
            "benchmark_return_pct": benchmark_return_pct,
            "asset_buy_hold_return_pct": asset_buy_hold_return_pct,
            "excess_return_vs_benchmark_pct": total_return_pct - benchmark_return_pct,
            "excess_return_vs_asset_buy_hold_pct": total_return_pct - asset_buy_hold_return_pct,
            "sharpe": sharpe,
            "max_drawdown_pct": max_drawdown_pct,
            "total_trades": total_trades,
            "won": won,
            "lost": lost,
            "win_rate_pct": win_rate,
        }

        pd.DataFrame([metrics]).to_csv(run_dir / "metrics.csv", index=False)
        all_metrics.append(metrics)

pd.DataFrame(all_metrics).to_csv(out_root / "all_metrics.csv", index=False)
pd.DataFrame(skipped, columns=["file", "strategy", "stage", "error"]).to_csv(
    out_root / "skipped_strategies.csv",
    index=False,
)

print(f"Done: {out_root}")
