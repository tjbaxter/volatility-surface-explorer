# 🚀 Quick Start Guide

Get the Volatility Surface Explorer up and running in 5 minutes!

## Prerequisites

- Python 3.10 or higher
- pip package manager
- Internet connection (for fetching market data)

## Installation Steps

### 1. Navigate to Project Directory

```bash
cd /Users/tombaxter/vega-engine/volatility-surface-explorer
```

### 2. (Optional) Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- streamlit (web interface)
- pandas, numpy (data processing)
- scipy (optimization)
- plotly (visualizations)
- yfinance (market data)
- scikit-learn (utilities)

### 4. Run the Application

```bash
streamlit run app.py
```

The app will automatically open in your browser at `http://localhost:8501`

## First Time Usage

### Tab 1: Volatility Surface 🌐

1. **Automatic Data Loading**: The app will fetch current SPY options data from Yahoo Finance
   - If yfinance fails, it will generate synthetic data
   - Data is cached for 1 hour

2. **3D Surface Visualization**:
   - Rotate: Click and drag
   - Zoom: Scroll or pinch
   - Red line shows ATM (At-The-Money) options

3. **Volatility Smile**:
   - Select an expiry from dropdown
   - View IV vs Strike for that expiry
   - Green = Calls, Red = Puts

### Tab 2: Greeks Dashboard 📊

1. **Select Expiry**: Choose expiry date from dropdown

2. **View Greeks Charts**:
   - **Delta**: Sensitivity to underlying price movement
   - **Gamma**: Rate of change of delta
   - **Vega**: Sensitivity to volatility changes
   - **Theta**: Time decay (per day)

3. **Top Gamma Options**: See options with highest gamma (good for gamma scalping)

### Tab 3: Strategy Backtest 💰

1. **Set Parameters**:
   - Start Date: Beginning of backtest period
   - End Date: End of backtest period
   - Initial Capital: Starting portfolio value

2. **Advanced Parameters** (optional):
   - IV-RV Threshold: How much IV must exceed RV
   - DTE Range: Days to expiration filter
   - Max Positions: Maximum concurrent trades

3. **Run Backtest**: Click "🚀 Run Backtest"

4. **View Results**:
   - Performance metrics (Sharpe, Max DD, Win Rate)
   - Cumulative P&L chart
   - Trade distribution histogram
   - Monthly returns heatmap
   - Complete trade log (downloadable)

## Testing Individual Modules

Each module can be tested independently:

```bash
# Test data loading
python -m src.data_loader

# Test Greeks calculations
python -m src.greeks

# Test surface building
python -m src.surface_builder

# Test strategy backtest
python -m src.strategy

# Test visualizations
python -m src.visualizations
```

## Troubleshooting

### Issue: "Module not found" errors

**Solution**: Make sure you've installed all dependencies:
```bash
pip install -r requirements.txt
```

### Issue: yfinance fails to fetch data

**Solution**: The app will automatically fall back to synthetic data. If you want to force synthetic data:
- The data loader will detect failures and generate synthetic data
- For backtesting, synthetic data is used by default

### Issue: App is slow

**Solution**: 
- First load may take longer (fetching data)
- Data is cached for subsequent loads
- Building SVI surface requires optimization (may take 10-30 seconds)
- Backtest on long periods may take 1-2 minutes

### Issue: Port 8501 already in use

**Solution**: Either:
1. Kill the existing Streamlit process
2. Or specify a different port:
```bash
streamlit run app.py --server.port 8502
```

## Understanding the Output

### Performance Metrics

- **Total Return**: % gain/loss from start to end
- **Sharpe Ratio**: Risk-adjusted returns (>1 is good, >2 is excellent)
- **Max Drawdown**: Largest peak-to-trough decline
- **Win Rate**: % of profitable trades
- **Avg P&L per Trade**: Average profit/loss per trade
- **Avg Hold Time**: Average days each position is held

### Strategy Logic

The backtest implements a **delta-hedged skew selling** strategy:

1. **Entry**: Sell 30-delta OTM puts when IV > RV
2. **Hedging**: Buy stock to neutralize delta exposure
3. **Rebalancing**: Adjust hedge daily as delta changes
4. **Exit**: Close on expiry, stop-loss, or take-profit

### Transaction Costs

Built-in realistic costs:
- Options: 12 bps (10 bps spread + 2 bps slippage)
- Stock: 0.1 bps per trade

## Next Steps

1. **Experiment with Parameters**: Try different IV-RV thresholds
2. **Analyze Greeks**: Understand how delta/gamma change with strike/expiry
3. **Study Trade Log**: See which trades were profitable and why
4. **Compare Periods**: Run backtests on different time periods
5. **Modify Strategy**: Edit `src/strategy.py` to test your own ideas

## Tips for Best Results

✅ **DO**:
- Use realistic transaction costs
- Test on multiple time periods
- Understand the Greeks before trading
- Start with small position sizes

❌ **DON'T**:
- Over-optimize on one backtest period
- Ignore transaction costs
- Trade without understanding the risks
- Assume past results predict future performance

## Getting Help

If you encounter issues:

1. Check the terminal for error messages
2. Review the module documentation in source files
3. Test individual modules (see "Testing" section above)
4. Check that all data is loading correctly

## Performance Expectations

On typical hardware:
- **Data Loading**: 5-15 seconds (first time)
- **Surface Building**: 10-30 seconds
- **Backtest (6 months)**: 30-90 seconds
- **Visualization Rendering**: 1-3 seconds

---

**Enjoy exploring the volatility surface!** 📈

*Remember: This is for educational purposes only. Not financial advice.*

