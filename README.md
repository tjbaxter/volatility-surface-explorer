# Volatility Surface Explorer

Volatility and options analysis toolkit for SPY, with an interactive Streamlit UI and a delta-hedged strategy backtest.

## Features

- SVI calibration for implied volatility slices and surface interpolation
- Black-Scholes pricing and Greeks (delta, gamma, vega, theta, rho)
- Delta-hedged skew-selling backtest with transaction cost assumptions
- Interactive visualizations for surface, smiles, Greeks, and PnL
- Cached data loading with synthetic fallback when live data is unavailable

## Quick Start

```bash
git clone https://github.com/tjbaxter/volatility-surface-explorer.git
cd volatility-surface-explorer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
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
├── tests/
│   └── test_strategy.py
└── data/
```

## Technical Notes

### Vol Surface

The SVI parameterization is used per expiry:

`w(k) = a + b * (rho * (k - m) + sqrt((k - m)^2 + sigma^2))`

with basic no-arbitrage checks during calibration.

### Backtest

The strategy module models:

- entry selection from IV-RV spread and DTE filters
- single-contract option positions with daily delta hedge updates
- simple stop-loss / take-profit exits
- transaction costs for options and stock hedge legs

## Testing

```bash
python -m src.greeks
python -m src.surface_builder
python -m src.strategy
pytest tests/test_strategy.py -v
```

## Disclaimer

This repository is for research and software experimentation. It is not investment advice.

## License

MIT
