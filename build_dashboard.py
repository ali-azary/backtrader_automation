import argparse
import html
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
from jinja2 import Template


parser = argparse.ArgumentParser()
parser.add_argument("--results", default="results")
parser.add_argument("--out", default="dashboard.html")
args = parser.parse_args()

results = Path(args.results)
metric_files = list(results.glob("*/*/metrics.csv"))

rows = []
for file in metric_files:
    rows.append(pd.read_csv(file).iloc[0].to_dict())

df = pd.DataFrame(rows)

if df.empty:
    raise ValueError("No metrics.csv files found.")

df = df.sort_values(["symbol", "total_return_pct"], ascending=[True, False])

summary = df.to_html(index=False, classes="table", border=0)

bar = px.bar(
    df,
    x="strategy",
    y="total_return_pct",
    color="symbol",
    title="Strategy Returns by Asset",
    barmode="group",
).to_html(full_html=False, include_plotlyjs="cdn")

dd = px.bar(
    df,
    x="strategy",
    y="max_drawdown_pct",
    color="symbol",
    title="Max Drawdown by Strategy",
    barmode="group",
).to_html(full_html=False, include_plotlyjs=False)

sharpe = px.bar(
    df,
    x="strategy",
    y="sharpe",
    color="symbol",
    title="Sharpe Ratio by Strategy",
    barmode="group",
).to_html(full_html=False, include_plotlyjs=False)

plot_sections = ""
dashboard_dir = Path(args.out).resolve().parent
plot_files = [
    ("Equity vs Benchmark", "equity_vs_benchmark.png"),
    ("Drawdown vs Benchmark", "drawdown_vs_benchmark.png"),
    ("Rolling Return vs Benchmark", "rolling_return_vs_benchmark.png"),
    ("Daily Returns", "daily_returns_hist.png"),
]

for symbol_dir in results.iterdir():
    if symbol_dir.is_dir():
        plot_sections += f"<h2>{html.escape(symbol_dir.name)}</h2>"
        for strat_dir in symbol_dir.iterdir():
            if not strat_dir.is_dir():
                continue

            images = ""
            for title, filename in plot_files:
                image_file = strat_dir / filename
                if image_file.exists():
                    rel_path = os.path.relpath(image_file.resolve(), dashboard_dir)
                    rel_path = rel_path.replace(os.sep, "/")
                    images += (
                        f'<figure><img src="{html.escape(rel_path)}" '
                        f'alt="{html.escape(title)}"><figcaption>{html.escape(title)}</figcaption></figure>'
                    )

            if images:
                plot_sections += (
                    f'<section class="strategy-plots"><h3>{html.escape(strat_dir.name)}</h3>'
                    f'<div class="plot-grid">{images}</div></section>'
                )

template = Template(
    """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Backtest Dashboard</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f6f8fb;
            color: #111827;
            margin: 40px;
        }
        h1 {
            font-size: 34px;
        }
        h2 {
            margin-top: 50px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 8px;
        }
        .card {
            background: white;
            padding: 24px;
            border-radius: 8px;
            box-shadow: 0 4px 18px rgba(0,0,0,0.08);
            margin-bottom: 28px;
        }
        .table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        .table th {
            background: #111827;
            color: white;
            padding: 10px;
        }
        .table td {
            padding: 10px;
            border-bottom: 1px solid #e5e7eb;
        }
        .table tr:nth-child(even) {
            background: #f9fafb;
        }
        .strategy-plots {
            margin-top: 28px;
        }
        .strategy-plots h3 {
            margin: 0 0 16px;
        }
        .plot-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
            gap: 18px;
        }
        figure {
            margin: 0;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            overflow: hidden;
            background: #fff;
        }
        img {
            display: block;
            width: 100%;
            height: auto;
        }
        figcaption {
            padding: 8px 10px;
            font-size: 13px;
            color: #4b5563;
            border-top: 1px solid #e5e7eb;
        }
    </style>
</head>
<body>
    <h1>Backtest Dashboard</h1>

    <div class="card">
        <h2>Summary Table</h2>
        {{ summary }}
    </div>

    <div class="card">
        {{ bar }}
    </div>

    <div class="card">
        {{ dd }}
    </div>

    <div class="card">
        {{ sharpe }}
    </div>

    <div class="card">
        <h2>Saved Matplotlib Plots</h2>
        {{ plot_sections }}
    </div>
</body>
</html>
"""
)

html = template.render(
    summary=summary,
    bar=bar,
    dd=dd,
    sharpe=sharpe,
    plot_sections=plot_sections,
)

Path(args.out).write_text(html, encoding="utf-8")

print(f"Dashboard created: {args.out}")
