from __future__ import annotations

import argparse
import html
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def fmt_pct(value):
    if pd.isna(value):
        return "n/a"
    return f"{float(value):+.2f}%"


def fmt_num(value, digits=2):
    if pd.isna(value):
        return "n/a"
    return f"{float(value):,.{digits}f}"


def fmt_int(value):
    if pd.isna(value):
        return "n/a"
    return f"{int(float(value)):,}"


def plot_html(fig, div_id):
    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        div_id=div_id,
        config={"displayModeBar": False, "responsive": True},
    )


def load_metrics(metric_files, dashboard_dir):
    rows = []

    for file in metric_files:
        row = pd.read_csv(file).iloc[0].to_dict()
        row["metrics_file"] = str(file)
        row["run_dir"] = str(file.parent)

        plot_file = file.parent / "equity_vs_benchmark.png"
        row["plot"] = (
            os.path.relpath(plot_file.resolve(), dashboard_dir).replace(os.sep, "/")
            if plot_file.exists()
            else ""
        )

        rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    numeric_cols = [
        "final_value",
        "total_return_pct",
        "benchmark_return_pct",
        "asset_buy_hold_return_pct",
        "excess_return_vs_benchmark_pct",
        "excess_return_vs_asset_buy_hold_pct",
        "sharpe",
        "max_drawdown_pct",
        "total_trades",
        "won",
        "lost",
        "win_rate_pct",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.sort_values(["symbol", "total_return_pct"], ascending=[True, False]).reset_index(
        drop=True
    )


def make_top_return_chart(df):
    top = df.sort_values("total_return_pct", ascending=False).head(30).copy()
    top["label"] = top["strategy"].astype(str)
    if df["symbol"].nunique() > 1:
        top["label"] = top["symbol"].astype(str) + " - " + top["label"]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=top["label"],
            y=top["total_return_pct"],
            name="Strategy return",
            marker_color="#0f766e",
            hovertemplate="%{x}<br>Return: %{y:.2f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=top["label"],
            y=top["benchmark_return_pct"],
            name="Benchmark",
            mode="lines+markers",
            line=dict(color="#d97706", width=3, dash="dash"),
            hovertemplate="%{x}<br>Benchmark: %{y:.2f}%<extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_white",
        height=440,
        margin=dict(l=40, r=20, t=25, b=120),
        yaxis_title="Return (%)",
        xaxis_tickangle=-35,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return plot_html(fig, "top_return_chart")


def make_risk_chart(df):
    chart = df.copy()
    chart["total_trades"] = chart["total_trades"].fillna(0)

    fig = px.scatter(
        chart,
        x="max_drawdown_pct",
        y="total_return_pct",
        size="total_trades",
        color="sharpe",
        hover_name="strategy",
        hover_data=["symbol", "benchmark_return_pct", "win_rate_pct"],
        color_continuous_scale="Viridis",
        labels={
            "max_drawdown_pct": "Max drawdown (%)",
            "total_return_pct": "Total return (%)",
            "sharpe": "Sharpe",
            "total_trades": "Trades",
        },
        height=440,
    )
    fig.add_hline(y=0, line_dash="dot", line_color="#64748b")
    fig.update_layout(template="plotly_white", margin=dict(l=40, r=20, t=25, b=45))
    return plot_html(fig, "risk_chart")


def make_summary_chart(df):
    if df["symbol"].nunique() > 1:
        grouped = (
            df.groupby("symbol", as_index=False)
            .agg(
                avg_return=("total_return_pct", "mean"),
                best_return=("total_return_pct", "max"),
                runs=("strategy", "count"),
            )
            .sort_values("best_return", ascending=False)
        )
        x = grouped["symbol"]
        best = grouped["best_return"]
        avg = grouped["avg_return"]
        x_title = "Asset"
    else:
        grouped = df.sort_values("total_return_pct", ascending=False).head(20).copy()
        x = grouped["strategy"]
        best = grouped["total_return_pct"]
        avg = grouped["benchmark_return_pct"]
        x_title = "Strategy"

    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=best, name="Strategy / best return", marker_color="#0f766e"))
    fig.add_trace(go.Bar(x=x, y=avg, name="Average / benchmark", marker_color="#94a3b8"))
    fig.update_layout(
        template="plotly_white",
        height=390,
        barmode="group",
        margin=dict(l=40, r=20, t=25, b=90),
        yaxis_title="Return (%)",
        xaxis_title=x_title,
        xaxis_tickangle=-35,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return plot_html(fig, "summary_chart")


def make_heatmap(df):
    top = df.sort_values("total_return_pct", ascending=False).head(30).copy()
    top["label"] = top["strategy"].astype(str)
    if df["symbol"].nunique() > 1:
        top["label"] = top["symbol"].astype(str) + " - " + top["label"]

    metrics = [
        "total_return_pct",
        "excess_return_vs_benchmark_pct",
        "sharpe",
        "win_rate_pct",
        "max_drawdown_pct",
    ]

    existing = [col for col in metrics if col in top.columns]
    matrix = top.set_index("label")[existing]
    normalized = matrix.copy()

    for col in normalized.columns:
        series = normalized[col].replace([np.inf, -np.inf], np.nan)
        low = series.min()
        high = series.max()
        normalized[col] = 0 if pd.isna(low) or pd.isna(high) or low == high else (series - low) / (high - low)

    if "max_drawdown_pct" in normalized.columns:
        normalized["max_drawdown_pct"] = 1 - normalized["max_drawdown_pct"]

    fig = px.imshow(
        normalized.T,
        aspect="auto",
        color_continuous_scale="Teal",
        labels=dict(x="Run", y="Metric", color="Normalized"),
        height=410,
    )
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=40, r=20, t=25, b=120),
        xaxis_tickangle=-35,
    )
    return plot_html(fig, "metric_heatmap")


def make_table(df):
    ranked = df.sort_values("total_return_pct", ascending=False).copy().reset_index(drop=True)
    rows = []

    for idx, row in ranked.iterrows():
        rows.append(
            "<tr>"
            f"<td>{idx + 1}</td>"
            f"<td>{html.escape(str(row.get('symbol', '')))}</td>"
            f"<td class='strategy-cell'>{html.escape(str(row.get('strategy', '')))}</td>"
            f"<td class='pos'>{fmt_pct(row.get('total_return_pct'))}</td>"
            f"<td>{fmt_pct(row.get('benchmark_return_pct'))}</td>"
            f"<td>{fmt_pct(row.get('excess_return_vs_benchmark_pct'))}</td>"
            f"<td>{fmt_num(row.get('sharpe'))}</td>"
            f"<td>{fmt_pct(-abs(row.get('max_drawdown_pct')) if pd.notna(row.get('max_drawdown_pct')) else np.nan)}</td>"
            f"<td>{fmt_int(row.get('total_trades'))}</td>"
            f"<td>{fmt_pct(row.get('win_rate_pct'))}</td>"
            f"<td>${fmt_num(row.get('final_value'))}</td>"
            "</tr>"
        )

    return "\n".join(rows)


def make_gallery(df):
    cards = []
    gallery_df = df[df["plot"] != ""].sort_values("total_return_pct", ascending=False).head(36)

    for _, row in gallery_df.iterrows():
        title = f"{row['symbol']} - {row['strategy']}"
        cards.append(
            "<article class='plot-card'>"
            f"<div class='plot-card-head'><strong>{html.escape(str(title))}</strong><span>{fmt_pct(row['total_return_pct'])}</span></div>"
            f"<img src='{html.escape(str(row['plot']))}' alt='{html.escape(str(title))} equity curve'>"
            "</article>"
        )

    return "\n".join(cards)


def write_skipped_summary(results_dir):
    skipped_files = list(results_dir.glob("skipped_strategies.csv"))
    if not skipped_files:
        skipped_files = list(results_dir.glob("*/skipped_strategies.csv"))

    skipped_rows = []
    for file in skipped_files:
        skipped = pd.read_csv(file)
        if skipped.empty:
            continue
        skipped["symbol"] = file.parent.name
        skipped_rows.append(skipped)

    if not skipped_rows:
        return "0"

    skipped_df = pd.concat(skipped_rows, ignore_index=True)
    skipped_df.to_csv(results_dir / "all_skipped_strategies.csv", index=False)
    return str(len(skipped_df))


def render_dashboard(results_dir, dashboard_file, metric_pattern, title):
    dashboard_dir = dashboard_file.resolve().parent
    metric_files = sorted(results_dir.glob(metric_pattern))
    df = load_metrics(metric_files, dashboard_dir)

    if df.empty:
        raise ValueError(f"No metrics.csv files found under {results_dir}. Run backtests first.")

    dashboard_file.parent.mkdir(parents=True, exist_ok=True)

    best = df.sort_values("total_return_pct", ascending=False).iloc[0]
    symbols = sorted(df["symbol"].dropna().unique())
    strategy_count = df["strategy"].nunique()
    run_count = len(df)
    positive_count = int((df["total_return_pct"] > 0).sum())
    plot_count = int((df["plot"] != "").sum())
    best_return = best["total_return_pct"]
    avg_return = df["total_return_pct"].mean()
    avg_sharpe = df["sharpe"].mean()
    failure_count = write_skipped_summary(results_dir)

    html_out = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root {{
      --bg: #f7faf8;
      --ink: #10201d;
      --muted: #64746f;
      --line: #dbe6e1;
      --panel: #ffffff;
      --teal: #0f766e;
      --amber: #d97706;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    header {{
      padding: 34px 40px 24px;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(180deg, #ffffff 0%, #f2f7f5 100%);
    }}
    h1 {{ margin: 0; font-size: 30px; line-height: 1.15; }}
    .subtitle {{ margin-top: 8px; color: var(--muted); font-size: 15px; }}
    main {{ padding: 28px 40px 44px; max-width: 1550px; margin: 0 auto; }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(6, minmax(150px, 1fr));
      gap: 14px;
      margin-bottom: 22px;
    }}
    .kpi {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 16px;
      min-height: 104px;
    }}
    .kpi span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
      margin-bottom: 9px;
    }}
    .kpi strong {{ display: block; font-size: 22px; line-height: 1.15; word-break: break-word; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 20px; }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 18px;
      margin-bottom: 20px;
    }}
    h2 {{ margin: 0 0 14px; font-size: 17px; line-height: 1.2; }}
    .table-wrap {{ overflow: auto; border: 1px solid var(--line); border-radius: 8px; max-height: 720px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; background: #fff; }}
    th, td {{
      padding: 11px 12px;
      border-bottom: 1px solid var(--line);
      text-align: right;
      white-space: nowrap;
    }}
    th {{
      position: sticky;
      top: 0;
      background: #eef6f3;
      color: #203b36;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .03em;
      z-index: 2;
    }}
    th:nth-child(2), td:nth-child(2), th:nth-child(3), td:nth-child(3) {{ text-align: left; }}
    tr:hover td {{ background: #f6fbf9; }}
    .strategy-cell {{ font-weight: 650; }}
    .pos {{ color: var(--teal); font-weight: 750; }}
    .gallery {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
    .plot-card {{ border: 1px solid var(--line); border-radius: 10px; overflow: hidden; background: #fff; }}
    .plot-card-head {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: center;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      font-size: 13px;
    }}
    .plot-card-head span {{ color: var(--teal); font-weight: 750; }}
    .plot-card img {{ display: block; width: 100%; height: auto; }}
    .footnote {{ color: var(--muted); font-size: 12px; margin-top: 18px; }}
    @media (max-width: 1100px) {{
      header, main {{ padding-left: 18px; padding-right: 18px; }}
      .kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .grid {{ grid-template-columns: 1fr; }}
      .gallery {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>{html.escape(title)}</h1>
    <div class="subtitle">Results for {len(symbols)} asset(s), {strategy_count} strategy class(es), and {run_count} completed run(s).</div>
  </header>
  <main>
    <div class="kpis">
      <div class="kpi"><span>Best Run</span><strong>{html.escape(str(best["symbol"]))} / {html.escape(str(best["strategy"]))}</strong></div>
      <div class="kpi"><span>Best Return</span><strong>{fmt_pct(best_return)}</strong></div>
      <div class="kpi"><span>Average Return</span><strong>{fmt_pct(avg_return)}</strong></div>
      <div class="kpi"><span>Average Sharpe</span><strong>{fmt_num(avg_sharpe)}</strong></div>
      <div class="kpi"><span>Positive Runs</span><strong>{positive_count}/{run_count}</strong></div>
      <div class="kpi"><span>Equity Plots</span><strong>{plot_count}</strong></div>
    </div>
    <div class="grid">
      <section><h2>Top Strategy Returns</h2>{make_top_return_chart(df)}</section>
      <section><h2>Return vs Drawdown</h2>{make_risk_chart(df)}</section>
    </div>
    <div class="grid">
      <section><h2>Summary</h2>{make_summary_chart(df)}</section>
      <section><h2>Metric Heatmap</h2>{make_heatmap(df)}</section>
    </div>
    <section>
      <h2>Ranked Results</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Rank</th><th>Symbol</th><th>Strategy</th><th>Total Return</th>
              <th>Benchmark</th><th>Excess</th><th>Sharpe</th><th>Max DD</th>
              <th>Trades</th><th>Win Rate</th><th>Final Value</th>
            </tr>
          </thead>
          <tbody>{make_table(df)}</tbody>
        </table>
      </div>
    </section>
    <section>
      <h2>Equity Curve Gallery</h2>
      <div class="gallery">{make_gallery(df)}</div>
    </section>
    <div class="footnote">Skipped or failed strategy records: {failure_count}. If any exist, see all_skipped_strategies.csv in this results folder.</div>
  </main>
</body>
</html>
"""

    dashboard_file.write_text(html_out, encoding="utf-8")
    print(f"Dashboard created: {dashboard_file}")


def build_asset_dashboards(results_root):
    asset_dirs = sorted(
        path
        for path in results_root.iterdir()
        if path.is_dir() and list(path.glob("*/metrics.csv"))
    )

    if not asset_dirs:
        raise ValueError(f"No asset result folders with metrics.csv found under {results_root}.")

    for asset_dir in asset_dirs:
        render_dashboard(
            asset_dir,
            asset_dir / "dashboard.html",
            "*/metrics.csv",
            f"{asset_dir.name} Strategy Dashboard",
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="results")
    parser.add_argument("--out", default="dashboard.html")
    parser.add_argument(
        "--mode",
        choices=["assets", "combined", "both"],
        default="assets",
        help="assets writes results/SYMBOL/dashboard.html. combined writes one dashboard to --out.",
    )
    args = parser.parse_args()

    results = Path(args.results)

    if args.mode in {"assets", "both"}:
        build_asset_dashboards(results)

    if args.mode in {"combined", "both"}:
        render_dashboard(
            results,
            Path(args.out),
            "*/*/metrics.csv",
            "Backtrader Strategy Dashboard",
        )


if __name__ == "__main__":
    main()
