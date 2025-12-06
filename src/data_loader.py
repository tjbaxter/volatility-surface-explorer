"""
Data loading and preprocessing module for SPY options data.

Fetches options chain data from yfinance and provides fallback synthetic data generation.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import yfinance as yf
from typing import Optional
import warnings

warnings.filterwarnings('ignore')


def fetch_spy_options_chain(use_cache: bool = True) -> pd.DataFrame:
    """
    Fetch current SPY options chain from yfinance.
    
    Parameters:
        use_cache: bool, whether to use cached data if available
    
    Returns:
        pd.DataFrame with columns:
        - quote_date: datetime
        - expiry: datetime  
        - strike: float
        - option_type: str ('call' or 'put')
        - bid: float
        - ask: float
        - last_price: float
        - volume: int
        - open_interest: int
        - implied_volatility: float
        - underlying_price: float
    """
    cache_file = Path(__file__).parent.parent / 'data' / 'cached_spy_options.csv'
    
    # Try to use cache if requested
    if use_cache and cache_file.exists():
        try:
            df = pd.read_csv(cache_file)
            df['quote_date'] = pd.to_datetime(df['quote_date'])
            df['expiry'] = pd.to_datetime(df['expiry'])
            print(f"Loaded {len(df)} options from cache")
            return df
        except Exception as e:
            print(f"Cache load failed: {e}, fetching fresh data...")
    
    try:
        # Fetch SPY ticker
        spy = yf.Ticker('SPY')
        spot_price = spy.history(period='1d')['Close'].iloc[-1]
        quote_date = datetime.now()
        
        # Get all available expiration dates
        expirations = spy.options
        
        if len(expirations) == 0:
            raise ValueError("No expiration dates available")
        
        all_options = []
        
        # Fetch options for each expiration (limit to first 8 for speed)
        for expiry_str in expirations[:8]:
            try:
                opt_chain = spy.option_chain(expiry_str)
                expiry_date = pd.to_datetime(expiry_str)
                
                # Process calls
                calls = opt_chain.calls.copy()
                calls['option_type'] = 'call'
                calls['expiry'] = expiry_date
                calls['quote_date'] = quote_date
                calls['underlying_price'] = spot_price
                
                # Process puts
                puts = opt_chain.puts.copy()
                puts['option_type'] = 'put'
                puts['expiry'] = expiry_date
                puts['quote_date'] = quote_date
                puts['underlying_price'] = spot_price
                
                all_options.extend([calls, puts])
                
            except Exception as e:
                print(f"Failed to fetch {expiry_str}: {e}")
                continue
        
        if len(all_options) == 0:
            raise ValueError("Failed to fetch any options data")
        
        # Combine all data
        df = pd.concat(all_options, ignore_index=True)
        
        # Standardize column names
        df = df.rename(columns={
            'lastPrice': 'last_price',
            'impliedVolatility': 'implied_volatility',
            'openInterest': 'open_interest',
            'contractSymbol': 'contract_symbol'
        })
        
        # Select relevant columns
        columns = [
            'quote_date', 'expiry', 'strike', 'option_type', 
            'bid', 'ask', 'last_price', 'volume', 'open_interest',
            'implied_volatility', 'underlying_price'
        ]
        
        df = df[columns]
        
        # Save to cache
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache_file, index=False)
        print(f"Fetched and cached {len(df)} options from yfinance")
        
        return df
        
    except Exception as e:
        print(f"yfinance fetch failed: {e}")
        print("Generating synthetic data as fallback...")
        return generate_synthetic_current_data()


def generate_synthetic_current_data(symbol: str = 'SPY') -> pd.DataFrame:
    """
    Generate synthetic current options data using parametric models.
    Used when real-time data is unavailable.
    
    Returns:
        pd.DataFrame with same columns as fetch_spy_options_chain()
    """
    # Synthetic parameters
    spot_price = 450.0  # Typical SPY price
    quote_date = datetime.now()
    risk_free_rate = 0.05
    
    # Generate expiries (weekly for first month, then monthly)
    expiries = []
    base_date = quote_date
    
    # Next 4 weekly expiries
    for i in range(1, 5):
        days = i * 7
        expiries.append(base_date + timedelta(days=days))
    
    # Next 6 monthly expiries
    for i in range(1, 7):
        days = 30 * i
        expiries.append(base_date + timedelta(days=days))
    
    # Generate strikes around spot
    strike_range = np.arange(0.80, 1.25, 0.01)  # 80% to 125% of spot
    strikes = spot_price * strike_range
    
    all_options = []
    
    for expiry in expiries:
        time_to_expiry = (expiry - quote_date).days / 365.0
        
        if time_to_expiry <= 0:
            continue
        
        for strike in strikes:
            moneyness = strike / spot_price
            
            # SVI-based synthetic vol surface
            # Higher vol for OTM options, vol smile/skew
            atm_vol = 0.15 + 0.05 * np.sqrt(time_to_expiry)
            
            # Add skew (puts have higher vol)
            skew = -0.1 * (moneyness - 1.0)
            
            # Add smile (far OTM options have higher vol)
            smile = 0.05 * (moneyness - 1.0) ** 2
            
            implied_vol = atm_vol + skew + smile
            implied_vol = max(0.05, min(0.60, implied_vol))  # Clamp to reasonable range
            
            # Generate both call and put
            for option_type in ['call', 'put']:
                # Simplified Black-Scholes price (actual implementation in greeks.py)
                if option_type == 'call':
                    intrinsic = max(0, spot_price - strike)
                else:
                    intrinsic = max(0, strike - spot_price)
                
                # Rough price estimate
                time_value = implied_vol * spot_price * np.sqrt(time_to_expiry) * 0.4
                mid_price = intrinsic + time_value
                
                # Generate bid/ask spread (wider for OTM)
                spread_pct = 0.02 + 0.03 * abs(moneyness - 1.0)
                bid = mid_price * (1 - spread_pct / 2)
                ask = mid_price * (1 + spread_pct / 2)
                
                # Synthetic volume and OI (higher for ATM)
                atm_factor = np.exp(-10 * (moneyness - 1.0) ** 2)
                volume = int(1000 * atm_factor * np.random.uniform(0.5, 1.5))
                open_interest = int(5000 * atm_factor * np.random.uniform(0.5, 1.5))
                
                all_options.append({
                    'quote_date': quote_date,
                    'expiry': expiry,
                    'strike': strike,
                    'option_type': option_type,
                    'bid': max(0.01, bid),
                    'ask': max(bid + 0.01, ask),
                    'last_price': mid_price,
                    'volume': volume,
                    'open_interest': open_interest,
                    'implied_volatility': implied_vol,
                    'underlying_price': spot_price
                })
    
    df = pd.DataFrame(all_options)
    print(f"Generated {len(df)} synthetic options")
    return df


def generate_synthetic_historical_data(
    start_date: str, 
    end_date: str, 
    symbol: str = 'SPY'
) -> pd.DataFrame:
    """
    Generate synthetic historical options data using parametric models.
    Used for backtesting when real historical data is unavailable.
    
    Parameters:
        start_date: str, format 'YYYY-MM-DD'
        end_date: str, format 'YYYY-MM-DD'
        symbol: str, ticker symbol
    
    Returns:
        pd.DataFrame with same columns as fetch_spy_options_chain()
    """
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    
    # Generate business days
    dates = pd.bdate_range(start, end)
    
    all_historical_options = []
    
    # Simulate SPY price path (random walk with drift)
    np.random.seed(42)
    initial_price = 400.0
    daily_return_mean = 0.0003  # ~7.5% annual
    daily_return_std = 0.01  # ~16% annual vol
    
    prices = [initial_price]
    for _ in range(len(dates) - 1):
        ret = np.random.normal(daily_return_mean, daily_return_std)
        prices.append(prices[-1] * (1 + ret))
    
    # Sample subset of dates for performance (every 5th day)
    sample_indices = range(0, len(dates), 5)
    
    for idx in sample_indices:
        quote_date = dates[idx]
        spot_price = prices[idx]
        
        # For each date, generate options with 7, 14, 30, 60 DTE
        dte_list = [7, 14, 30, 60]
        
        for dte in dte_list:
            expiry = quote_date + timedelta(days=dte)
            time_to_expiry = dte / 365.0
            
            # Generate strikes (focus on near-the-money for performance)
            strike_range = np.arange(0.90, 1.12, 0.01)
            strikes = spot_price * strike_range
            
            for strike in strikes:
                moneyness = strike / spot_price
                
                # Time-varying vol surface (add some vol clustering)
                base_vol = 0.15 + 0.05 * np.sin(idx / 50.0)  # Cycles in vol
                atm_vol = base_vol + 0.03 * np.sqrt(time_to_expiry)
                
                # Skew (puts more expensive)
                skew = -0.15 * (moneyness - 1.0)
                
                # Smile
                smile = 0.08 * (moneyness - 1.0) ** 2
                
                implied_vol = atm_vol + skew + smile
                implied_vol = max(0.05, min(0.60, implied_vol))
                
                # Only generate puts for the backtest strategy (focus on 30-delta puts)
                option_type = 'put'
                intrinsic = max(0, strike - spot_price)
                time_value = implied_vol * spot_price * np.sqrt(time_to_expiry) * 0.4
                mid_price = intrinsic + time_value
                
                spread_pct = 0.02
                bid = mid_price * (1 - spread_pct / 2)
                ask = mid_price * (1 + spread_pct / 2)
                
                atm_factor = np.exp(-10 * (moneyness - 1.0) ** 2)
                volume = int(500 * atm_factor)
                open_interest = int(2000 * atm_factor)
                
                all_historical_options.append({
                    'quote_date': quote_date,
                    'expiry': expiry,
                    'strike': strike,
                    'option_type': option_type,
                    'bid': max(0.01, bid),
                    'ask': max(bid + 0.01, ask),
                    'last_price': mid_price,
                    'volume': volume,
                    'open_interest': open_interest,
                    'implied_volatility': implied_vol,
                    'underlying_price': spot_price
                })
    
    df = pd.DataFrame(all_historical_options)
    print(f"Generated {len(df)} historical synthetic options across {len(sample_indices)} dates")
    return df


def preprocess_options_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and prepare options data:
    - Remove invalid rows (missing bid/ask, zero volume)
    - Calculate mid-price: (bid + ask) / 2
    - Calculate moneyness: strike / spot_price
    - Calculate time to expiry in years
    - Filter for liquid strikes (volume > threshold)
    
    Returns:
        pd.DataFrame (cleaned)
    """
    df = df.copy()
    
    # Remove rows with missing critical data
    df = df.dropna(subset=['bid', 'ask', 'strike', 'implied_volatility'])
    
    # Remove options with zero or negative prices
    df = df[(df['bid'] > 0) & (df['ask'] > 0) & (df['strike'] > 0)]
    
    # Remove options with invalid implied vol
    df = df[(df['implied_volatility'] > 0) & (df['implied_volatility'] < 2.0)]
    
    # Calculate mid price
    df['mid_price'] = (df['bid'] + df['ask']) / 2
    
    # Calculate moneyness
    df['moneyness'] = df['strike'] / df['underlying_price']
    
    # Calculate time to expiry in years
    df['time_to_expiry'] = (df['expiry'] - df['quote_date']).dt.days / 365.0
    
    # Remove expired options
    df = df[df['time_to_expiry'] > 0]
    
    # Filter for reasonable liquidity (at least some volume or OI)
    df = df[(df['volume'] > 0) | (df['open_interest'] > 10)]
    
    # Remove extremely wide bid-ask spreads (>50% of mid)
    df['spread_pct'] = (df['ask'] - df['bid']) / df['mid_price']
    df = df[df['spread_pct'] < 0.5]
    
    # Sort by expiry and strike
    df = df.sort_values(['expiry', 'strike']).reset_index(drop=True)
    
    print(f"Preprocessed data: {len(df)} options remaining")
    
    return df


def get_spot_prices_series(options_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract spot price time series from options data.
    
    Returns:
        pd.DataFrame with columns: date, spot_price
    """
    spot_prices = options_df.groupby('quote_date')['underlying_price'].first().reset_index()
    spot_prices.columns = ['date', 'spot_price']
    spot_prices = spot_prices.sort_values('date').reset_index(drop=True)
    
    return spot_prices


if __name__ == "__main__":
    # Test the module
    print("Testing data_loader.py...")
    
    # Test current data fetch
    df = fetch_spy_options_chain(use_cache=False)
    print(f"\nFetched {len(df)} options")
    print(f"Expiries: {df['expiry'].nunique()}")
    print(f"Date range: {df['quote_date'].min()} to {df['expiry'].max()}")
    
    # Test preprocessing
    df_clean = preprocess_options_data(df)
    print(f"\nAfter preprocessing: {len(df_clean)} options")
    print(f"\nSample data:")
    print(df_clean.head())
    
    # Test historical data generation
    hist_df = generate_synthetic_historical_data('2023-01-01', '2023-03-01')
    print(f"\nGenerated {len(hist_df)} historical options")

