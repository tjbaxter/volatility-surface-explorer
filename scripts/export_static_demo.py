"""
Build static, interactive Plotly demo pages for GitHub Pages.

This script exports a lightweight interactive demo from the core analytics:
- 3D implied volatility surface
- Volatility smile for nearest expiry
- Term structure (ATM IV vs DTE)
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_loader import (
    fetch_spy_options_chain,
    preprocess_options_data,
    generate_synthetic_current_data,
)
from src.surface_builder import build_surface
from src.visualizations import plot_3d_volatility_surface, plot_volatility_smile


REPO_URL = "https://github.com/tjbaxter/volatility-surface-explorer"
PAGES_ROOT = "https://tjbaxter.github.io/volatility-surface-explorer"


def _build_term_structure_figure(surface: dict) -> go.Figure:
    """Create ATM IV term structure figure from fitted surface."""
    strikes = surface["surface_grid"]["strikes"]
    iv_grid = surface["surface_grid"]["iv"]
    times = np.array(surface["surface_grid"]["times"])
    spot = float(surface["spot_price"])
    atm_idx = int(np.argmin(np.abs(strikes - spot)))

    atm_iv = iv_grid[:, atm_idx] * 100.0
    dte = times * 365.0

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=dte,
            y=atm_iv,
            mode="lines+markers",
            name="ATM IV",
            line=dict(color="#0f62fe", width=3),
            marker=dict(size=7),
            hovertemplate="<b>DTE:</b> %{x:.0f} days<br><b>ATM IV:</b> %{y:.2f}%<extra></extra>",
        )
    )
    fig.update_layout(
        title="ATM IV Term Structure",
        xaxis_title="Days to Expiry",
        yaxis_title="ATM Implied Volatility (%)",
        template="plotly_white",
        height=520,
        margin=dict(l=40, r=20, t=60, b=40),
    )
    return fig


def _write_html_shell(output_dir: Path, metadata: dict) -> None:
    """Write the landing page that links embedded interactive charts."""
    generated_at = metadata["generated_at"]
    quote_date = metadata["quote_date"]
    spot_price = metadata["spot_price"]
    rows = metadata["num_options"]
    expiries = metadata["num_expiries"]

    index_html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Volatility Surface Explorer - Interactive Demo</title>
  <style>
    :root {{
      --bg: #070b12;
      --panel: #101826;
      --text: #f2f5f9;
      --muted: #9fb0c7;
      --accent: #4ea8ff;
      --accent-2: #68e1fd;
      --border: #21324a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: radial-gradient(circle at top right, #122038 0%, var(--bg) 48%);
      color: var(--text);
      line-height: 1.5;
    }}
    .wrap {{
      max-width: 1240px;
      margin: 0 auto;
      padding: 32px 20px 56px;
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: clamp(1.8rem, 4vw, 2.8rem);
      letter-spacing: 0.01em;
    }}
    .subtitle {{
      margin: 0 0 20px;
      color: var(--muted);
      max-width: 840px;
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 24px;
    }}
    .btn {{
      color: #021427;
      background: linear-gradient(120deg, var(--accent), var(--accent-2));
      text-decoration: none;
      font-weight: 600;
      padding: 10px 14px;
      border-radius: 10px;
      transition: transform .12s ease;
    }}
    .btn.secondary {{
      color: var(--text);
      background: #17263a;
      border: 1px solid var(--border);
    }}
    .btn:hover {{ transform: translateY(-1px); }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
      margin-bottom: 22px;
    }}
    .card {{
      background: rgba(16, 24, 38, 0.72);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 12px 14px;
    }}
    .k {{
      display: block;
      font-size: 0.82rem;
      color: var(--muted);
      margin-bottom: 3px;
      letter-spacing: .02em;
      text-transform: uppercase;
    }}
    .v {{
      font-size: 1.05rem;
      font-weight: 600;
    }}
    .panel {{
      background: rgba(16, 24, 38, 0.76);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 12px;
      margin: 14px 0;
    }}
    h2 {{
      margin: 0 0 6px;
      font-size: 1.12rem;
    }}
    p.note {{
      margin: 0 0 10px;
      font-size: 0.92rem;
      color: var(--muted);
    }}
    iframe {{
      width: 100%;
      min-height: 560px;
      border: 0;
      border-radius: 10px;
      background: white;
    }}
    footer {{
      margin-top: 28px;
      color: var(--muted);
      font-size: 0.86rem;
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <h1>Volatility Surface Explorer</h1>
    <p class="subtitle">
      Interactive quant demo for SPY options analytics: SVI surface calibration, smile diagnostics, and term-structure behavior.
      Use your mouse to rotate, zoom, and inspect values.
    </p>

    <div class="actions">
      <a class="btn" href="{REPO_URL}" target="_blank" rel="noopener noreferrer">View Source on GitHub</a>
      <a class="btn secondary" href="{PAGES_ROOT}" target="_blank" rel="noopener noreferrer">Open Demo Root</a>
    </div>

    <section class="meta">
      <article class="card"><span class="k">Quote Date</span><span class="v">{quote_date}</span></article>
      <article class="card"><span class="k">Spot</span><span class="v">${spot_price:.2f}</span></article>
      <article class="card"><span class="k">Options Rows</span><span class="v">{rows:,}</span></article>
      <article class="card"><span class="k">Expiries</span><span class="v">{expiries}</span></article>
      <article class="card"><span class="k">Generated</span><span class="v">{generated_at}</span></article>
    </section>

    <section class="panel">
      <h2>3D Implied Volatility Surface</h2>
      <p class="note">Rotate and zoom to inspect skew and term dynamics across strike and expiry.</p>
      <iframe src="./surface.html" title="3D implied volatility surface"></iframe>
    </section>

    <section class="panel">
      <h2>Volatility Smile (Nearest Expiry)</h2>
      <p class="note">Call/put smile with spot reference line for quick skew inspection.</p>
      <iframe src="./smile.html" title="Volatility smile"></iframe>
    </section>

    <section class="panel">
      <h2>ATM IV Term Structure</h2>
      <p class="note">ATM implied volatility vs days to expiry from fitted slices.</p>
      <iframe src="./term_structure.html" title="ATM IV term structure"></iframe>
    </section>

    <footer>
      Built with Python, Plotly, and SVI-based volatility surface modeling.
    </footer>
  </main>
</body>
</html>
"""
    (output_dir / "index.html").write_text(index_html, encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output_dir = root / "docs"
    output_dir.mkdir(parents=True, exist_ok=True)

    options = fetch_spy_options_chain(use_cache=True)
    options = preprocess_options_data(options)

    # Some live chains can fail strict filters (e.g., stale quotes/spreads).
    # Fall back to deterministic synthetic data so demo export always succeeds.
    if options.empty:
        options = preprocess_options_data(generate_synthetic_current_data())

    surface = build_surface(options)

    spot = float(options["underlying_price"].iloc[0])
    nearest_expiry = pd.to_datetime(options["expiry"].min())

    fig_surface = plot_3d_volatility_surface(surface, spot)
    fig_smile = plot_volatility_smile(options, nearest_expiry, spot)
    fig_term = _build_term_structure_figure(surface)

    fig_surface.write_html(
        output_dir / "surface.html",
        include_plotlyjs="cdn",
        full_html=True,
        config={"displaylogo": False},
    )
    fig_smile.write_html(
        output_dir / "smile.html",
        include_plotlyjs="cdn",
        full_html=True,
        config={"displaylogo": False},
    )
    fig_term.write_html(
        output_dir / "term_structure.html",
        include_plotlyjs="cdn",
        full_html=True,
        config={"displaylogo": False},
    )

    metadata = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "quote_date": pd.to_datetime(options["quote_date"].iloc[0]).strftime("%Y-%m-%d"),
        "spot_price": spot,
        "num_options": int(len(options)),
        "num_expiries": int(options["expiry"].nunique()),
    }
    _write_html_shell(output_dir, metadata)

    print(f"Exported interactive demo to {output_dir}")


if __name__ == "__main__":
    main()
