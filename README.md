# Volatility Surface Explorer

**Live demo:** https://tjbaxter.github.io/volatility-surface-explorer/

Implied volatility modeling and options strategy research for SPY, with SVI calibration, Greeks analytics, and a delta-hedged backtest.

## Features

- SVI calibration for each expiry slice, with implied volatility interpolated across strike and expiry
- Black-Scholes pricing and Greeks (`delta`, `gamma`, `vega`, `theta`, `rho`)
- Delta-hedged short-put backtest on a synthetic SPY history, with configurable IV-RV threshold, DTE window and position limit
- Streamlit app with interactive Plotly charts for the surface, smile, Greeks by strike, and backtest PnL
- SPY option chain from yfinance (delayed quotes, first 8 expiries), filtered for missing or zero quotes, illiquid strikes and spreads wider than 50% of mid, with a synthetic chain as fallback when the fetch fails

## Run Locally (Full App)

```bash
git clone https://github.com/tjbaxter/volatility-surface-explorer.git
cd volatility-surface-explorer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The first run fetches the chain and caches it to `data/cached_spy_options.csv`. Later runs reuse that file; delete it to fetch a fresh chain.

## Interactive Demo Deployment

A GitHub Actions workflow runs on every push to `main` and:

1. Fetches the SPY chain and fits the SVI surface
2. Exports standalone Plotly HTML views (surface, smile, ATM term structure) into `docs/`
3. Deploys those pages to GitHub Pages

If the yfinance fetch fails or the filters leave no rows, the export uses the synthetic chain instead, so a Spot of `$450.00` on the demo page means it is showing synthetic data.

Main files:

- [`scripts/export_static_demo.py`](scripts/export_static_demo.py)
- [`.github/workflows/deploy-demo-pages.yml`](.github/workflows/deploy-demo-pages.yml)

To regenerate the demo pages locally:

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
├── docs/
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

where `k` is log-moneyness against the forward. Call and put IVs are averaged per strike, and each slice is fitted by seeded differential evolution on squared error in total variance, rejecting any parameter set that breaks `a + b * sigma * sqrt(1 - rho^2) >= 0`, `b >= 0`, `|rho| <= 1`, `sigma > 0` or `b * (1 + |rho|) <= 4.5`. Slices with fewer than five strikes or a failed fit are dropped. These constraints apply per slice; the surface is not checked for calendar arbitrage across expiries.

### Backtest Logic

The backtest runs on synthetic data: a seeded random-walk SPY path with a parametric put skew, quoted every fifth business day. No historical option quotes are loaded.

- Sell 30-delta puts with 7 to 14 days to expiry when IV exceeds realized vol by more than a set number (default 2) of standard deviations of that day's IV-RV spread
- Delta-hedge with the underlying, rebalancing on each quote date when the hedge changes by 5 or more shares
- Exit at expiry, on a stop-loss (loss beyond 2% of the premium received) or on a take-profit (gain beyond 40% of the premium received)
- Hold at most 5 positions, opening at most one per day
- Charge 12 bps of option premium per side and 0.1 bps of notional on each hedge trade, deducted from reported PnL

## Testing

```bash
python -m src.greeks
python -m pytest tests/test_strategy.py -v
```

## License

MIT. See [LICENSE](LICENSE).
