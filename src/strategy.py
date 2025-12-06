"""
Delta-hedged skew-selling options strategy backtest engine.

Implements a systematic strategy that sells OTM puts when implied vol exceeds realized vol.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from src.greeks import calculate_greeks, calculate_delta, black_scholes_put


@dataclass
class Trade:
    """Represents a single options trade with delta hedge."""
    trade_id: int
    entry_date: datetime
    exit_date: Optional[datetime] = None
    
    # Option details
    strike: float = 0.0
    expiry: datetime = None
    option_type: str = 'put'
    contracts: int = 1
    
    # Entry prices
    entry_option_price: float = 0.0
    entry_spot_price: float = 0.0
    entry_delta: float = 0.0
    entry_iv: float = 0.0
    
    # Hedge
    stock_quantity: float = 0.0  # Shares held for delta hedge
    
    # Exit prices
    exit_option_price: Optional[float] = None
    exit_spot_price: Optional[float] = None
    
    # P&L tracking
    option_pnl: float = 0.0
    hedge_pnl: float = 0.0
    transaction_costs: float = 0.0
    total_pnl: float = 0.0
    
    # Exit reason
    exit_reason: str = ''
    
    # Daily tracking
    daily_values: List[Dict] = field(default_factory=list)


def apply_transaction_costs(price: float, trade_type: str = 'option', side: str = 'buy') -> float:
    """
    Apply transaction costs to a trade.
    
    Parameters:
        price: Trade price (total notional)
        trade_type: 'option' or 'stock'
        side: 'buy' or 'sell'
    
    Returns:
        float: Actual cost after transaction costs
    """
    if trade_type == 'option':
        # 10 bps bid-ask + 2 bps slippage = 12 bps per side
        cost_bps = 12
    else:  # stock
        cost_bps = 0.1
    
    if side == 'buy':
        return price * (1 + cost_bps / 10000)
    else:
        return price * (1 - cost_bps / 10000)


class StrategyBacktest:
    """
    Delta-hedged skew-selling strategy backtest.
    
    Strategy:
    - Sell 30-delta OTM puts when IV > RV by threshold
    - Delta-hedge with underlying stock
    - Exit on expiry, stop-loss, or take-profit
    """
    
    def __init__(
        self,
        options_df: pd.DataFrame,
        spot_prices_df: pd.DataFrame,
        risk_free_rate: float = 0.05,
        initial_capital: float = 100000.0
    ):
        """
        Initialize backtest.
        
        Parameters:
            options_df: DataFrame with historical options data
            spot_prices_df: DataFrame with columns ['date', 'spot_price']
            risk_free_rate: Annual risk-free rate
            initial_capital: Starting capital
        """
        self.options_df = options_df.copy()
        self.spot_prices_df = spot_prices_df.copy()
        self.risk_free_rate = risk_free_rate
        self.initial_capital = initial_capital
        
        # Strategy parameters
        self.iv_rv_threshold = 2.0  # Standard deviations
        self.target_delta = -0.30  # 30-delta puts
        self.min_dte = 7
        self.max_dte = 14
        self.max_positions = 5
        self.stop_loss_pct = -0.02  # -2% of position value
        self.take_profit_pct = 0.50  # +50% of max potential gain
        self.min_rebalance_shares = 5  # Only rebalance if delta changes by 5+ shares
        
        # State
        self.trades: List[Trade] = []
        self.active_trades: Dict[int, Trade] = {}
        self.portfolio_value_history: List[Dict] = []
        self.cash = initial_capital
        self.next_trade_id = 1
        
        # Precompute realized volatility
        self._precompute_realized_vol()
    
    def _precompute_realized_vol(self, lookback_days: int = 30):
        """Calculate rolling realized volatility of underlying."""
        # Ensure date column is datetime
        self.spot_prices_df['date'] = pd.to_datetime(self.spot_prices_df['date'])
        self.spot_prices_df = self.spot_prices_df.sort_values('date').reset_index(drop=True)
        
        # Calculate returns
        self.spot_prices_df['returns'] = self.spot_prices_df['spot_price'].pct_change()
        
        # Calculate rolling realized vol (annualized)
        self.spot_prices_df['realized_vol'] = (
            self.spot_prices_df['returns']
            .rolling(window=lookback_days)
            .std() * np.sqrt(252)
        )
        
        # Fill NaN with median
        median_vol = self.spot_prices_df['realized_vol'].median()
        self.spot_prices_df['realized_vol'] = self.spot_prices_df['realized_vol'].fillna(median_vol)
    
    def calculate_realized_vol(self, date: datetime, lookback_days: int = 30) -> float:
        """Get realized volatility for a specific date."""
        date = pd.to_datetime(date)
        row = self.spot_prices_df[self.spot_prices_df['date'] == date]
        
        if len(row) == 0:
            # Find nearest date
            idx = (self.spot_prices_df['date'] - date).abs().argmin()
            return self.spot_prices_df.iloc[idx]['realized_vol']
        
        return row.iloc[0]['realized_vol']
    
    def get_spot_price(self, date: datetime) -> float:
        """Get spot price for a specific date."""
        date = pd.to_datetime(date)
        row = self.spot_prices_df[self.spot_prices_df['date'] == date]
        
        if len(row) == 0:
            # Find nearest date
            idx = (self.spot_prices_df['date'] - date).abs().argmin()
            return self.spot_prices_df.iloc[idx]['spot_price']
        
        return row.iloc[0]['spot_price']
    
    def identify_signals(self, date: datetime) -> List[Dict]:
        """
        Find trading opportunities on given date.
        
        Returns:
            List of dicts with option contract details
        """
        date = pd.to_datetime(date)
        
        # Get available options for this date
        available = self.options_df[
            (self.options_df['quote_date'] == date) &
            (self.options_df['option_type'] == 'put')
        ].copy()
        
        if len(available) == 0:
            return []
        
        # Filter by DTE
        available['dte'] = (available['expiry'] - date).dt.days
        available = available[
            (available['dte'] >= self.min_dte) &
            (available['dte'] <= self.max_dte)
        ]
        
        if len(available) == 0:
            return []
        
        # Get current spot and realized vol
        spot_price = available['underlying_price'].iloc[0]
        realized_vol = self.calculate_realized_vol(date)
        
        # Calculate IV-RV spread for each option
        available['iv_rv_spread'] = available['implied_volatility'] - realized_vol
        
        # Find options where IV > RV by threshold
        # Use standard deviation of IV-RV spread as threshold
        spread_std = available['iv_rv_spread'].std()
        if spread_std == 0:
            spread_std = 0.01
        
        threshold = realized_vol + self.iv_rv_threshold * spread_std
        
        candidates = available[available['implied_volatility'] > threshold].copy()
        
        if len(candidates) == 0:
            return []
        
        # Find options close to target delta (30-delta puts)
        # Calculate delta for each option
        deltas = []
        for _, row in candidates.iterrows():
            delta = calculate_delta(
                'put',
                spot_price,
                row['strike'],
                row['time_to_expiry'],
                self.risk_free_rate,
                row['implied_volatility']
            )
            deltas.append(abs(delta))
        
        candidates['abs_delta'] = deltas
        candidates['delta_diff'] = abs(candidates['abs_delta'] - abs(self.target_delta))
        
        # Sort by closeness to target delta
        candidates = candidates.sort_values('delta_diff')
        
        # Return top candidates
        signals = []
        for _, row in candidates.head(3).iterrows():
            signals.append({
                'strike': row['strike'],
                'expiry': row['expiry'],
                'dte': row['dte'],
                'implied_vol': row['implied_volatility'],
                'bid': row['bid'],
                'ask': row['ask'],
                'mid_price': row['mid_price'],
                'delta': -row['abs_delta'],
                'time_to_expiry': row['time_to_expiry']
            })
        
        return signals
    
    def can_enter_position(self) -> bool:
        """Check if we can enter a new position."""
        return len(self.active_trades) < self.max_positions
    
    def enter_position(self, signal: Dict, date: datetime) -> Trade:
        """
        Execute trade: sell put, delta-hedge with stock.
        
        Parameters:
            signal: Dict with option details from identify_signals()
            date: Entry date
        
        Returns:
            Trade object
        """
        spot_price = self.get_spot_price(date)
        
        # Create trade
        trade = Trade(
            trade_id=self.next_trade_id,
            entry_date=date,
            strike=signal['strike'],
            expiry=signal['expiry'],
            option_type='put',
            contracts=1,  # Sell 1 contract (100 shares)
            entry_option_price=signal['mid_price'],
            entry_spot_price=spot_price,
            entry_delta=signal['delta'],
            entry_iv=signal['implied_vol']
        )
        
        self.next_trade_id += 1
        
        # Calculate delta hedge (sell put = short delta, so buy stock to hedge)
        # Delta of position = contracts * 100 * delta_per_share
        position_delta = trade.contracts * 100 * trade.entry_delta
        
        # To hedge, we need to buy -position_delta shares (since delta is negative for puts)
        trade.stock_quantity = -position_delta
        
        # Calculate transaction costs
        # Sell option premium
        option_premium = trade.entry_option_price * trade.contracts * 100
        option_cost = option_premium * (12 / 10000)  # 12 bps
        
        # Buy stock for hedge
        stock_notional = trade.stock_quantity * spot_price
        stock_cost = stock_notional * (0.1 / 10000)  # 0.1 bps
        
        trade.transaction_costs = option_cost + stock_cost
        
        # Update cash (receive premium, pay for stock and costs)
        self.cash += option_premium - stock_notional - trade.transaction_costs
        
        # Add to active trades
        self.active_trades[trade.trade_id] = trade
        
        return trade
    
    def update_positions(self, date: datetime):
        """
        Daily update:
        - Rebalance delta hedge
        - Check stop-loss / take-profit
        - Mark-to-market all positions
        """
        if len(self.active_trades) == 0:
            return
        
        spot_price = self.get_spot_price(date)
        date = pd.to_datetime(date)
        
        trades_to_close = []
        
        for trade_id, trade in self.active_trades.items():
            # Check if expired
            if date >= trade.expiry:
                trades_to_close.append((trade_id, 'expiry'))
                continue
            
            # Get current option price and delta
            time_to_expiry = (trade.expiry - date).days / 365.0
            
            # Get current IV (try from market data, else use entry IV)
            current_options = self.options_df[
                (self.options_df['quote_date'] == date) &
                (self.options_df['strike'] == trade.strike) &
                (self.options_df['expiry'] == trade.expiry) &
                (self.options_df['option_type'] == 'put')
            ]
            
            if len(current_options) > 0:
                current_iv = current_options.iloc[0]['implied_volatility']
                current_option_price = current_options.iloc[0]['mid_price']
            else:
                # Use Black-Scholes with entry IV
                current_iv = trade.entry_iv
                current_option_price = black_scholes_put(
                    spot_price, trade.strike, time_to_expiry,
                    self.risk_free_rate, current_iv
                )
            
            # Calculate current delta
            current_delta = calculate_delta(
                'put', spot_price, trade.strike, time_to_expiry,
                self.risk_free_rate, current_iv
            )
            
            # Calculate current P&L
            # Option P&L: we sold at entry, so profit if price decreased
            option_pnl = (trade.entry_option_price - current_option_price) * trade.contracts * 100
            
            # Hedge P&L: stock position value change
            hedge_pnl = trade.stock_quantity * (spot_price - trade.entry_spot_price)
            
            total_pnl = option_pnl + hedge_pnl - trade.transaction_costs
            
            # Check stop-loss (based on initial premium received)
            initial_premium = trade.entry_option_price * trade.contracts * 100
            if total_pnl < initial_premium * self.stop_loss_pct:
                trades_to_close.append((trade_id, 'stop_loss'))
                continue
            
            # Check take-profit
            max_profit = initial_premium * 0.8  # Assume max profit is 80% of premium
            if total_pnl > max_profit * self.take_profit_pct:
                trades_to_close.append((trade_id, 'take_profit'))
                continue
            
            # Rebalance delta hedge
            target_stock_qty = -current_delta * trade.contracts * 100
            shares_to_trade = target_stock_qty - trade.stock_quantity
            
            if abs(shares_to_trade) >= self.min_rebalance_shares:
                # Execute rebalance
                trade_cost = abs(shares_to_trade) * spot_price * (0.1 / 10000)
                trade.transaction_costs += trade_cost
                
                if shares_to_trade > 0:
                    # Buy more shares
                    self.cash -= shares_to_trade * spot_price + trade_cost
                else:
                    # Sell shares
                    self.cash += -shares_to_trade * spot_price - trade_cost
                
                trade.stock_quantity = target_stock_qty
            
            # Record daily values
            trade.daily_values.append({
                'date': date,
                'spot_price': spot_price,
                'option_price': current_option_price,
                'delta': current_delta,
                'option_pnl': option_pnl,
                'hedge_pnl': hedge_pnl,
                'total_pnl': total_pnl
            })
        
        # Close trades that hit exit conditions
        for trade_id, reason in trades_to_close:
            self.exit_position(trade_id, date, reason)
    
    def exit_position(self, trade_id: int, date: datetime, reason: str):
        """
        Close out trade: buy back option, sell hedge stock.
        
        Parameters:
            trade_id: Trade ID to close
            date: Exit date
            reason: Exit reason ('expiry', 'stop_loss', 'take_profit')
        """
        if trade_id not in self.active_trades:
            return
        
        trade = self.active_trades[trade_id]
        spot_price = self.get_spot_price(date)
        date = pd.to_datetime(date)
        
        # Calculate final option price
        if date >= trade.expiry or reason == 'expiry':
            # At expiry, option worth intrinsic value
            exit_option_price = max(0, trade.strike - spot_price)
        else:
            time_to_expiry = (trade.expiry - date).days / 365.0
            
            # Try to get market price
            current_options = self.options_df[
                (self.options_df['quote_date'] == date) &
                (self.options_df['strike'] == trade.strike) &
                (self.options_df['expiry'] == trade.expiry) &
                (self.options_df['option_type'] == 'put')
            ]
            
            if len(current_options) > 0:
                exit_option_price = current_options.iloc[0]['mid_price']
            else:
                exit_option_price = black_scholes_put(
                    spot_price, trade.strike, time_to_expiry,
                    self.risk_free_rate, trade.entry_iv
                )
        
        # Calculate P&L
        # Option P&L: we sold at entry, buy back at exit
        option_pnl = (trade.entry_option_price - exit_option_price) * trade.contracts * 100
        
        # Hedge P&L: sell stock at current price
        hedge_pnl = trade.stock_quantity * (spot_price - trade.entry_spot_price)
        
        # Exit transaction costs
        exit_option_cost = exit_option_price * trade.contracts * 100 * (12 / 10000)
        exit_stock_cost = abs(trade.stock_quantity * spot_price) * (0.1 / 10000)
        exit_costs = exit_option_cost + exit_stock_cost
        
        total_pnl = option_pnl + hedge_pnl - trade.transaction_costs - exit_costs
        
        # Update trade
        trade.exit_date = date
        trade.exit_option_price = exit_option_price
        trade.exit_spot_price = spot_price
        trade.option_pnl = option_pnl
        trade.hedge_pnl = hedge_pnl
        trade.transaction_costs += exit_costs
        trade.total_pnl = total_pnl
        trade.exit_reason = reason
        
        # Update cash
        # Buy back option, sell stock
        option_buyback = exit_option_price * trade.contracts * 100
        stock_proceeds = trade.stock_quantity * spot_price
        
        self.cash -= option_buyback
        self.cash += stock_proceeds
        self.cash -= exit_costs
        
        # Move to closed trades
        self.trades.append(trade)
        del self.active_trades[trade_id]
    
    def run_backtest(self, start_date: str, end_date: str) -> Dict:
        """
        Main backtest loop.
        
        Parameters:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            dict: Performance metrics and results
        """
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        # Get trading dates from spot prices
        trading_dates = self.spot_prices_df[
            (self.spot_prices_df['date'] >= start) &
            (self.spot_prices_df['date'] <= end)
        ]['date'].values
        
        print(f"Running backtest from {start_date} to {end_date}")
        print(f"Trading days: {len(trading_dates)}")
        
        for date in trading_dates:
            date = pd.to_datetime(date)
            
            # Update existing positions
            self.update_positions(date)
            
            # Look for new signals
            if self.can_enter_position():
                signals = self.identify_signals(date)
                
                for signal in signals:
                    if self.can_enter_position():
                        trade = self.enter_position(signal, date)
                        # Only enter one position per day
                        break
            
            # Record portfolio value
            spot_price = self.get_spot_price(date)
            open_pnl = sum(
                trade.daily_values[-1]['total_pnl'] if trade.daily_values else 0
                for trade in self.active_trades.values()
            )
            
            portfolio_value = self.cash + open_pnl
            
            self.portfolio_value_history.append({
                'date': date,
                'portfolio_value': portfolio_value,
                'cash': self.cash,
                'open_pnl': open_pnl,
                'num_positions': len(self.active_trades),
                'spot_price': spot_price
            })
        
        # Close any remaining positions
        final_date = pd.to_datetime(end)
        for trade_id in list(self.active_trades.keys()):
            self.exit_position(trade_id, final_date, 'backtest_end')
        
        # Calculate metrics
        return self.calculate_metrics()
    
    def calculate_metrics(self) -> Dict:
        """
        Calculate performance metrics:
        - Total return
        - Sharpe ratio
        - Max drawdown
        - Win rate
        - Average hold time
        """
        if len(self.trades) == 0:
            return {
                'total_return': 0.0,
                'sharpe': 0.0,
                'max_dd': 0.0,
                'win_rate': 0.0,
                'num_trades': 0,
                'avg_pnl': 0.0,
                'avg_hold_days': 0.0
            }
        
        # Portfolio value time series
        pv_df = pd.DataFrame(self.portfolio_value_history)
        pv_df['returns'] = pv_df['portfolio_value'].pct_change()
        
        # Total return
        final_value = pv_df['portfolio_value'].iloc[-1]
        total_return = (final_value - self.initial_capital) / self.initial_capital
        
        # Sharpe ratio
        excess_returns = pv_df['returns'].dropna() - (self.risk_free_rate / 252)
        sharpe = np.sqrt(252) * excess_returns.mean() / excess_returns.std() if len(excess_returns) > 0 else 0.0
        
        # Max drawdown
        cummax = pv_df['portfolio_value'].cummax()
        drawdown = (pv_df['portfolio_value'] - cummax) / cummax
        max_dd = drawdown.min()
        
        # Win rate
        wins = sum(1 for t in self.trades if t.total_pnl > 0)
        win_rate = wins / len(self.trades) if self.trades else 0.0
        
        # Average P&L
        avg_pnl = np.mean([t.total_pnl for t in self.trades])
        
        # Average hold time
        hold_times = [(t.exit_date - t.entry_date).days for t in self.trades if t.exit_date]
        avg_hold_days = np.mean(hold_times) if hold_times else 0.0
        
        return {
            'total_return': total_return,
            'sharpe': sharpe,
            'max_dd': max_dd,
            'win_rate': win_rate,
            'num_trades': len(self.trades),
            'avg_pnl': avg_pnl,
            'avg_hold_days': avg_hold_days,
            'final_value': final_value,
            'trades': self.trades,
            'portfolio_history': pv_df
        }


if __name__ == "__main__":
    print("Testing strategy.py...")
    
    from data_loader import generate_synthetic_historical_data, get_spot_prices_series, preprocess_options_data
    
    # Generate synthetic historical data
    print("\nGenerating synthetic historical data...")
    hist_df = generate_synthetic_historical_data('2023-01-01', '2023-06-30')
    hist_df = preprocess_options_data(hist_df)
    
    spot_df = get_spot_prices_series(hist_df)
    
    print(f"Generated {len(hist_df)} options across {len(spot_df)} dates")
    
    # Run backtest
    print("\nRunning backtest...")
    backtest = StrategyBacktest(hist_df, spot_df)
    results = backtest.run_backtest('2023-01-15', '2023-06-15')
    
    print("\n=== BACKTEST RESULTS ===")
    print(f"Total Return: {results['total_return']:.2%}")
    print(f"Sharpe Ratio: {results['sharpe']:.2f}")
    print(f"Max Drawdown: {results['max_dd']:.2%}")
    print(f"Win Rate: {results['win_rate']:.1%}")
    print(f"Number of Trades: {results['num_trades']}")
    print(f"Average P&L per Trade: ${results['avg_pnl']:.2f}")
    print(f"Average Hold Time: {results['avg_hold_days']:.1f} days")

