# Volatility Surface Explorer

Real-time implied volatility modeling and options strategy research for SPY, with SVI calibration, Greeks analytics, and a delta-hedged backtest.

## Live Links

- Interactive demo (GitHub Pages): `https://tjbaxter.github.io/volatility-surface-explorer/`
- Source code: `https://github.com/tjbaxter/volatility-surface-explorer`

> If the Pages link is not live yet, enable **Settings -> Pages -> Source: GitHub Actions** once, then re-run the latest workflow.

## Why This Project

This project demonstrates practical quant engineering skills:
- Vol surface construction from noisy option chain data
- Parametric calibration (SVI) with no-arbitrage sanity checks
- Derivatives risk analytics (Greeks) for trade selection and monitoring
- Strategy simulation under explicit transaction cost assumptions
- Professional interactive reporting for research communication

## Features

- SVI calibration for implied volatility slices and surface interpolation
- Black-Scholes pricing and Greeks (`delta`, `gamma`, `vega`, `theta`, `rho`)
- Delta-hedged skew-selling backtest with configurable constraints
- Interactive Plotly dashboards for surface, smile, Greeks, and PnL
- Cached data loading with synthetic fallback when live data is unavailable

## Run Locally (Full App)

```bash
git clone https://github.com/tjbaxter/volatility-surface-explorer.git
cd volatility-surface-explorer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Interactive Demo Deployment

This repository ships an automated GitHub Actions workflow that:
1. Builds fresh options/surface outputs
2. Exports standalone Plotly HTML views into `docs/`
3. Deploys those pages to GitHub Pages

Main files:
- `scripts/export_static_demo.py`
- `.github/workflows/deploy-demo-pages.yml`

Run locally if you want to regenerate demo assets:

```bash
python scripts/export_static_demo.py
```

## Project Structure

```text
volatility-surface-explorer/
├── app.py
├── requirements.txt
├── src/
│   ├── data_loader.py
│   ├── surface_builder.py
│   ├── greeks.py
│   ├── strategy.py
│   └── visualizations.py
├── scripts/
│   └── export_static_demo.py
├── .github/workflows/
│   └── deploy-demo-pages.yml
├── tests/
│   └── test_strategy.py
└── data/
```

## Technical Notes

### SVI Vol Surface

Per-expiry total variance is modeled as:

`w(k) = a + b * (rho * (k - m) + sqrt((k - m)^2 + sigma^2))`

with sanity checks for non-negative variance and practical no-arbitrage constraints during fitting.

### Backtest Logic

- Enter short-put opportunities from IV-RV dislocation and DTE filters
- Apply daily delta hedging with the underlying
- Enforce simple stop-loss/take-profit exits
- Account for options and hedge transaction costs in reported PnL

## Testing

```bash
python -m src.greeks
python -m src.surface_builder
python -m src.strategy
pytest tests/test_strategy.py -v
```

## Notes

Built for quantitative analytics, volatility modeling, and systematic strategy evaluation.

## License

MIT
