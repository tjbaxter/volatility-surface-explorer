"""
Unit tests for strategy backtest module.

Run with: pytest tests/test_strategy.py
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.strategy import StrategyBacktest, Trade, apply_transaction_costs
from src.data_loader import generate_synthetic_historical_data, get_spot_prices_series, preprocess_options_data


class TestTransactionCosts:
    """Test transaction cost calculations."""
    
    def test_option_buy_cost(self):
        """Test option buying transaction cost."""
        price = 100.0
        cost = apply_transaction_costs(price, 'option', 'buy')
        expected = 100.0 * (1 + 12/10000)
        assert abs(cost - expected) < 0.01
    
    def test_option_sell_cost(self):
        """Test option selling transaction cost."""
        price = 100.0
        cost = apply_transaction_costs(price, 'option', 'sell')
        expected = 100.0 * (1 - 12/10000)
        assert abs(cost - expected) < 0.01
    
    def test_stock_cost(self):
        """Test stock transaction cost."""
        price = 10000.0
        cost = apply_transaction_costs(price, 'stock', 'buy')
        expected = 10000.0 * (1 + 0.1/10000)
        assert abs(cost - expected) < 0.01


class TestStrategyBacktest:
    """Test strategy backtest functionality."""
    
    @pytest.fixture
    def sample_data(self):
        """Generate sample historical data for testing."""
        hist_df = generate_synthetic_historical_data('2023-01-01', '2023-03-31')
        hist_df = preprocess_options_data(hist_df)
        spot_df = get_spot_prices_series(hist_df)
        return hist_df, spot_df
    
    def test_backtest_initialization(self, sample_data):
        """Test backtest object initialization."""
        hist_df, spot_df = sample_data
        
        backtest = StrategyBacktest(
            hist_df,
            spot_df,
            risk_free_rate=0.05,
            initial_capital=100000
        )
        
        assert backtest.initial_capital == 100000
        assert backtest.cash == 100000
        assert len(backtest.trades) == 0
        assert len(backtest.active_trades) == 0
    
    def test_realized_vol_calculation(self, sample_data):
        """Test realized volatility calculation."""
        hist_df, spot_df = sample_data
        
        backtest = StrategyBacktest(hist_df, spot_df)
        
        # Get realized vol for first date with data
        date = spot_df['date'].iloc[50]  # Skip first few days
        rv = backtest.calculate_realized_vol(date)
        
        assert rv > 0
        assert rv < 2.0  # Reasonable annual vol range
    
    def test_signal_identification(self, sample_data):
        """Test signal identification logic."""
        hist_df, spot_df = sample_data
        
        backtest = StrategyBacktest(hist_df, spot_df)
        
        # Find signals on a date with data
        date = hist_df['quote_date'].iloc[100]
        signals = backtest.identify_signals(date)
        
        # May or may not find signals, but should return a list
        assert isinstance(signals, list)
    
    def test_position_entry_exit(self, sample_data):
        """Test entering and exiting a position."""
        hist_df, spot_df = sample_data
        
        backtest = StrategyBacktest(hist_df, spot_df, initial_capital=100000)
        
        # Create a mock signal
        date = pd.to_datetime('2023-01-15')
        signal = {
            'strike': 400.0,
            'expiry': pd.to_datetime('2023-01-30'),
            'dte': 15,
            'implied_vol': 0.20,
            'bid': 2.0,
            'ask': 2.2,
            'mid_price': 2.1,
            'delta': -0.30,
            'time_to_expiry': 15/365
        }
        
        # Enter position
        initial_cash = backtest.cash
        trade = backtest.enter_position(signal, date)
        
        assert trade.trade_id == 1
        assert trade.strike == 400.0
        assert len(backtest.active_trades) == 1
        assert backtest.cash < initial_cash  # Cash decreased (bought stock for hedge)
        
        # Exit position
        exit_date = pd.to_datetime('2023-01-25')
        backtest.exit_position(trade.trade_id, exit_date, 'take_profit')
        
        assert len(backtest.active_trades) == 0
        assert len(backtest.trades) == 1
        assert backtest.trades[0].exit_reason == 'take_profit'
    
    def test_full_backtest_run(self, sample_data):
        """Test complete backtest execution."""
        hist_df, spot_df = sample_data
        
        backtest = StrategyBacktest(hist_df, spot_df, initial_capital=100000)
        
        results = backtest.run_backtest('2023-01-15', '2023-03-15')
        
        # Check that results contain expected keys
        assert 'total_return' in results
        assert 'sharpe' in results
        assert 'max_dd' in results
        assert 'win_rate' in results
        assert 'num_trades' in results
        
        # Check metrics are reasonable
        assert results['total_return'] >= -1.0  # Not losing more than 100%
        assert results['total_return'] <= 5.0   # Not gaining more than 500%
        assert results['max_dd'] <= 0           # Max drawdown is negative
        assert 0 <= results['win_rate'] <= 1    # Win rate between 0 and 1
    
    def test_position_limit(self, sample_data):
        """Test that max position limit is respected."""
        hist_df, spot_df = sample_data
        
        backtest = StrategyBacktest(hist_df, spot_df)
        backtest.max_positions = 3
        
        # Try to enter more than max positions
        date = pd.to_datetime('2023-01-15')
        signal = {
            'strike': 400.0,
            'expiry': pd.to_datetime('2023-01-30'),
            'dte': 15,
            'implied_vol': 0.20,
            'bid': 2.0,
            'ask': 2.2,
            'mid_price': 2.1,
            'delta': -0.30,
            'time_to_expiry': 15/365
        }
        
        # Enter max positions
        for i in range(3):
            if backtest.can_enter_position():
                backtest.enter_position(signal, date)
        
        # Should have 3 positions
        assert len(backtest.active_trades) == 3
        
        # Should not be able to enter another
        assert not backtest.can_enter_position()


class TestTrade:
    """Test Trade dataclass."""
    
    def test_trade_creation(self):
        """Test creating a trade object."""
        trade = Trade(
            trade_id=1,
            entry_date=datetime(2023, 1, 15),
            strike=400.0,
            expiry=datetime(2023, 1, 30),
            option_type='put',
            contracts=1
        )
        
        assert trade.trade_id == 1
        assert trade.strike == 400.0
        assert trade.option_type == 'put'
        assert trade.exit_date is None  # Not yet exited


def test_performance_metrics_calculation():
    """Test performance metrics calculation with known data."""
    # Create simple portfolio history
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
    
    # Simulate a portfolio that grows steadily
    portfolio_values = 100000 * (1 + np.linspace(0, 0.2, len(dates)))
    
    pv_df = pd.DataFrame({
        'date': dates,
        'portfolio_value': portfolio_values,
        'cash': 100000,
        'open_pnl': 0,
        'num_positions': 1,
        'spot_price': 450.0
    })
    
    # Calculate returns
    pv_df['returns'] = pv_df['portfolio_value'].pct_change()
    
    # Calculate Sharpe (simplified)
    excess_returns = pv_df['returns'].dropna() - (0.05 / 252)
    sharpe = np.sqrt(252) * excess_returns.mean() / excess_returns.std()
    
    # Should have positive Sharpe for upward trending portfolio
    assert sharpe > 0


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, '-v'])

