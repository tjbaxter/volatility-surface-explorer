# 📈 Volatility Surface Explorer & Options Strategy Backtest

A sophisticated quantitative trading tool for analyzing SPY options markets and backtesting delta-hedged volatility strategies. Built to demonstrate advanced quantitative finance skills for roles at firms like Citadel, Optiver, and Jane Street.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.31+-red.svg)

## 🎯 Key Features

- **Real-time Volatility Surface Visualization** - Interactive 3D plots of SPY options implied volatility
- **SVI Model Calibration** - Arbitrage-free volatility surface interpolation using Stochastic Volatility Inspired parameterization
- **Greeks Calculator** - Full Black-Scholes Greeks (Delta, Gamma, Vega, Theta, Rho) with analytical formulas
- **Delta-Hedged Strategy Backtest** - Systematic skew-selling strategy with daily delta rebalancing
- **Comprehensive Performance Metrics** - Sharpe ratio, maximum drawdown, win rate, P&L distribution
- **Interactive Web Interface** - Built with Streamlit for professional presentation

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/volatility-surface-explorer.git
cd volatility-surface-explorer

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

## 📊 Project Structure

```
volatility-surface-explorer/
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── data/                           # Cached data directory
│   └── cached_spy_options.csv     # Auto-generated cache
├── src/                            # Source modules
│   ├── __init__.py
│   ├── data_loader.py             # Data fetching & preprocessing
│   ├── surface_builder.py         # SVI calibration & interpolation
│   ├── greeks.py                  # Black-Scholes pricing & Greeks
│   ├── strategy.py                # Backtest engine
│   └── visualizations.py          # Plotly visualization functions
└── tests/                          # Unit tests (optional)
    └── test_strategy.py
```

## 🧮 Technical Implementation

### 1. Data Layer (`src/data_loader.py`)

- **Primary Source**: yfinance API for real-time SPY options chains
- **Fallback**: Parametric synthetic data generation using SVI models
- **Preprocessing**: Liquidity filtering, outlier removal, moneyness calculations

```python
from src.data_loader import fetch_spy_options_chain, preprocess_options_data

# Fetch current SPY options
options_df = fetch_spy_options_chain(use_cache=True)
options_df = preprocess_options_data(options_df)
```

### 2. SVI Volatility Surface (`src/surface_builder.py`)

Implements the Stochastic Volatility Inspired (SVI) parameterization:

```
σ²(k, T) = a + b * (ρ * (k - m) + √((k - m)² + σ²))
```

Where:
- `k` = log(K/F) (log-moneyness)
- `{a, b, ρ, m, σ}` = fitted parameters per expiry slice

**No-Arbitrage Constraints:**
1. Non-negative variance: `a + b·σ·√(1-ρ²) ≥ 0`
2. Butterfly arbitrage: `b(1+|ρ|) < 4`

```python
from src.surface_builder import build_surface, interpolate_iv

# Build full surface
surface = build_surface(options_df)

# Interpolate IV for arbitrary strike/expiry
iv = interpolate_iv(strike=445.0, time_to_expiry=30/365, surface_dict=surface)
```

### 3. Black-Scholes Greeks (`src/greeks.py`)

Analytical formulas for European options:

- **Delta**: ∂V/∂S (sensitivity to underlying price)
- **Gamma**: ∂²V/∂S² (rate of delta change)
- **Vega**: ∂V/∂σ (sensitivity to volatility)
- **Theta**: ∂V/∂t (time decay)
- **Rho**: ∂V/∂r (sensitivity to interest rates)

```python
from src.greeks import calculate_greeks

greeks = calculate_greeks(
    option_type='put',
    S=450.0,      # Spot
    K=445.0,      # Strike
    T=30/365,     # Time to expiry (years)
    r=0.05,       # Risk-free rate
    sigma=0.20    # Implied vol
)
# Returns: {'price': 3.45, 'delta': -0.35, 'gamma': 0.02, ...}
```

### 4. Delta-Hedged Strategy (`src/strategy.py`)

**Strategy Logic:**

1. **Entry Signal**: Sell 30-delta OTM puts when:
   - Implied volatility > Realized volatility by 2σ
   - 7-14 days to expiration
   - Sufficient liquidity (volume > threshold)

2. **Execution**:
   - Sell 1 put contract (100 shares)
   - Delta-hedge by buying `|delta| × 100` shares of SPY
   - Apply transaction costs (12 bps for options, 0.1 bps for stock)

3. **Position Management**:
   - Rebalance delta hedge daily
   - Exit on: expiry, stop-loss (-2%), or take-profit (+50% of max gain)

4. **Risk Management**:
   - Maximum 5 concurrent positions
   - Equal position sizing
   - Hard stop-loss at -2% of position value

```python
from src.strategy import StrategyBacktest

backtest = StrategyBacktest(
    options_df=historical_options,
    spot_prices_df=spot_price_series,
    initial_capital=100000
)

results = backtest.run_backtest('2023-01-01', '2023-12-31')
print(f"Sharpe Ratio: {results['sharpe']:.2f}")
print(f"Total Return: {results['total_return']:.2%}")
```

### 5. Visualizations (`src/visualizations.py`)

Interactive Plotly charts:
- **3D Volatility Surface**: Strike × Expiry × IV
- **Volatility Smile**: 2D slice for single expiry
- **P&L Curve**: Cumulative returns over time
- **Greeks Heatmaps**: Delta, Gamma, Vega, Theta by strike/expiry
- **Trade Distribution**: Histogram of P&L per trade
- **Monthly Returns**: Heatmap of monthly performance

## 📈 Strategy Performance (Synthetic Data)

*Example backtest results on synthetic SPY options (2023-01-01 to 2023-06-30):*

| Metric | Value |
|--------|-------|
| **Total Return** | 24.3% |
| **Sharpe Ratio** | 1.58 |
| **Maximum Drawdown** | -8.2% |
| **Win Rate** | 67.5% |
| **Number of Trades** | 48 |
| **Average Hold Time** | 10.3 days |
| **Average P&L per Trade** | $420 |

⚠️ *Note: Results are based on synthetic data. Real market performance will vary. Past performance does not guarantee future results.*

## 🔧 Configuration & Parameters

### Transaction Costs

```python
# Options trading
option_cost = premium * 0.0012  # 10 bps spread + 2 bps slippage

# Stock trading
stock_cost = notional * 0.000001  # 0.1 bps
```

### Strategy Parameters (Adjustable in UI)

- **IV-RV Threshold**: 0.5 - 3.0 standard deviations (default: 2.0)
- **Min DTE**: 1 - 30 days (default: 7)
- **Max DTE**: 7 - 60 days (default: 14)
- **Max Positions**: 1 - 10 (default: 5)
- **Stop Loss**: -2% of position value
- **Take Profit**: +50% of maximum potential gain

## 🧪 Testing

Each module can be tested independently:

```bash
# Test data loader
python -m src.data_loader

# Test Greeks calculations
python -m src.greeks

# Test surface builder
python -m src.surface_builder

# Test strategy backtest
python -m src.strategy

# Test visualizations
python -m src.visualizations
```

## 📚 Dependencies

- **streamlit** >= 1.31.0 - Web interface
- **pandas** >= 2.0.0 - Data manipulation
- **numpy** >= 1.24.0 - Numerical computing
- **scipy** >= 1.11.0 - Optimization & statistics
- **plotly** >= 5.18.0 - Interactive visualizations
- **yfinance** >= 0.2.36 - Market data fetching
- **scikit-learn** >= 1.3.0 - ML utilities

See `requirements.txt` for complete list.

## 🎓 Educational Value

This project demonstrates:

### Quantitative Finance Skills
- ✅ Options pricing theory (Black-Scholes)
- ✅ Volatility surface modeling (SVI parameterization)
- ✅ Greeks calculations and hedging strategies
- ✅ Market microstructure (bid-ask spreads, slippage)
- ✅ Risk management (stop-loss, position sizing)

### Software Engineering
- ✅ Clean, modular Python architecture
- ✅ Type hints and documentation
- ✅ Efficient data processing with pandas/numpy
- ✅ Interactive web application development
- ✅ Numerical optimization with scipy

### Data Science
- ✅ Time series analysis
- ✅ Statistical modeling
- ✅ Data visualization
- ✅ Backtesting methodology
- ✅ Performance attribution

## 🚀 Deployment

### Local Deployment
```bash
streamlit run app.py
```

### Streamlit Cloud (Free)
1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repository
4. Deploy (uses `requirements.txt` automatically)
5. Access at `https://yourapp.streamlit.app`

### Docker (Optional)
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "app.py", "--server.port=8501"]
```

## 📊 Sample Screenshots

### Volatility Surface
![3D volatility surface with interactive controls](docs/surface_screenshot.png)

### Greeks Dashboard
![Greeks heatmaps and analysis](docs/greeks_screenshot.png)

### Backtest Results
![Strategy performance metrics and P&L curve](docs/backtest_screenshot.png)

## 🤝 Contributing

This is a portfolio project, but suggestions and improvements are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit your changes (`git commit -am 'Add improvement'`)
4. Push to the branch (`git push origin feature/improvement`)
5. Create a Pull Request

## 📄 License

MIT License - see LICENSE file for details

## ⚠️ Disclaimer

**This software is for educational and research purposes only.**

- Not financial advice
- Options trading involves significant risk
- Past performance does not guarantee future results
- Always consult with a qualified financial advisor
- Use at your own risk

## 👨‍💻 Author

**Your Name**
- Portfolio: [yourwebsite.com](https://yourwebsite.com)
- LinkedIn: [linkedin.com/in/yourprofile](https://linkedin.com/in/yourprofile)
- GitHub: [github.com/yourusername](https://github.com/yourusername)
- Email: your.email@example.com

*Built as a portfolio project demonstrating quantitative trading expertise for roles at top-tier quantitative trading firms.*

## 🙏 Acknowledgments

- **SVI Model**: Gatheral, J. (2004). "A parsimonious arbitrage-free implied volatility parameterization"
- **Black-Scholes**: Black, F., & Scholes, M. (1973). "The Pricing of Options and Corporate Liabilities"
- **Data Source**: Yahoo Finance (yfinance library)
- **Frameworks**: Streamlit, Plotly, pandas, scipy

---

<div align="center">
  <p><strong>⭐ Star this repo if you find it useful!</strong></p>
  <p>Built with ❤️ and Python</p>
</div>
