"""
Black-Scholes option pricing and Greeks calculations.

Implements analytical formulas for European options pricing and Greeks.
"""

import numpy as np
from scipy.stats import norm
from typing import Dict, Tuple


def black_scholes_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Calculate Black-Scholes call option price.
    
    Parameters:
        S: Spot price of underlying
        K: Strike price
        T: Time to expiry (years)
        r: Risk-free rate (annual)
        sigma: Implied volatility (annual)
    
    Returns:
        float: Call option price
    """
    if T <= 0:
        return max(0, S - K)
    
    if sigma <= 0:
        return max(0, S - K * np.exp(-r * T))
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    call_price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    
    return call_price


def black_scholes_put(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Calculate Black-Scholes put option price.
    
    Parameters:
        S: Spot price of underlying
        K: Strike price
        T: Time to expiry (years)
        r: Risk-free rate (annual)
        sigma: Implied volatility (annual)
    
    Returns:
        float: Put option price
    """
    if T <= 0:
        return max(0, K - S)
    
    if sigma <= 0:
        return max(0, K * np.exp(-r * T) - S)
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    put_price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    return put_price


def calculate_delta(option_type: str, S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Calculate option delta (∂V/∂S).
    
    Delta measures the rate of change of option price with respect to underlying price.
    
    Returns:
        float: Delta (calls: 0 to 1, puts: -1 to 0)
    """
    if T <= 0:
        if option_type.lower() == 'call':
            return 1.0 if S > K else 0.0
        else:
            return -1.0 if S < K else 0.0
    
    if sigma <= 0:
        sigma = 0.001  # Small value to avoid division by zero
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    
    if option_type.lower() == 'call':
        delta = norm.cdf(d1)
    else:  # put
        delta = norm.cdf(d1) - 1
    
    return delta


def calculate_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Calculate option gamma (∂²V/∂S²).
    
    Gamma measures the rate of change of delta with respect to underlying price.
    Gamma is the same for calls and puts.
    
    Returns:
        float: Gamma (always positive)
    """
    if T <= 0 or sigma <= 0:
        return 0.0
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    
    return gamma


def calculate_vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Calculate option vega (∂V/∂σ).
    
    Vega measures the rate of change of option price with respect to volatility.
    Vega is the same for calls and puts.
    
    Returns:
        float: Vega (per 1% change in volatility)
    """
    if T <= 0:
        return 0.0
    
    if sigma <= 0:
        sigma = 0.001
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    
    # Vega per 1% (0.01) change in volatility
    vega = S * norm.pdf(d1) * np.sqrt(T) / 100
    
    return vega


def calculate_theta(option_type: str, S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Calculate option theta (∂V/∂T).
    
    Theta measures the rate of change of option price with respect to time.
    Usually negative (options lose value as time passes).
    
    Returns:
        float: Theta (per day, not per year)
    """
    if T <= 0:
        return 0.0
    
    if sigma <= 0:
        sigma = 0.001
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type.lower() == 'call':
        theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) 
                 - r * K * np.exp(-r * T) * norm.cdf(d2))
    else:  # put
        theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) 
                 + r * K * np.exp(-r * T) * norm.cdf(-d2))
    
    # Convert to per-day theta
    theta = theta / 365
    
    return theta


def calculate_rho(option_type: str, S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Calculate option rho (∂V/∂r).
    
    Rho measures the rate of change of option price with respect to interest rate.
    
    Returns:
        float: Rho (per 1% change in interest rate)
    """
    if T <= 0:
        return 0.0
    
    if sigma <= 0:
        sigma = 0.001
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type.lower() == 'call':
        rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100
    else:  # put
        rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
    
    return rho


def calculate_greeks(
    option_type: str, 
    S: float, 
    K: float, 
    T: float, 
    r: float, 
    sigma: float
) -> Dict[str, float]:
    """
    Calculate all Greeks for an option.
    
    Parameters:
        option_type: 'call' or 'put'
        S: Spot price of underlying
        K: Strike price
        T: Time to expiry (years)
        r: Risk-free rate (annual)
        sigma: Implied volatility (annual)
    
    Returns:
        dict: {
            'price': float,
            'delta': float,
            'gamma': float,
            'vega': float,
            'theta': float,
            'rho': float
        }
    """
    # Calculate price
    if option_type.lower() == 'call':
        price = black_scholes_call(S, K, T, r, sigma)
    else:
        price = black_scholes_put(S, K, T, r, sigma)
    
    # Calculate all Greeks
    greeks = {
        'price': price,
        'delta': calculate_delta(option_type, S, K, T, r, sigma),
        'gamma': calculate_gamma(S, K, T, r, sigma),
        'vega': calculate_vega(S, K, T, r, sigma),
        'theta': calculate_theta(option_type, S, K, T, r, sigma),
        'rho': calculate_rho(option_type, S, K, T, r, sigma)
    }
    
    return greeks


def implied_volatility_newton(
    option_price: float,
    option_type: str,
    S: float,
    K: float,
    T: float,
    r: float,
    initial_guess: float = 0.2,
    max_iterations: int = 100,
    tolerance: float = 1e-6
) -> float:
    """
    Calculate implied volatility using Newton-Raphson method.
    
    Parameters:
        option_price: Market price of option
        option_type: 'call' or 'put'
        S: Spot price
        K: Strike price
        T: Time to expiry (years)
        r: Risk-free rate
        initial_guess: Starting point for iteration
        max_iterations: Maximum number of iterations
        tolerance: Convergence tolerance
    
    Returns:
        float: Implied volatility
    """
    if T <= 0:
        return 0.0
    
    sigma = initial_guess
    
    for i in range(max_iterations):
        # Calculate price and vega at current sigma
        if option_type.lower() == 'call':
            calculated_price = black_scholes_call(S, K, T, r, sigma)
        else:
            calculated_price = black_scholes_put(S, K, T, r, sigma)
        
        vega = calculate_vega(S, K, T, r, sigma) * 100  # Vega per 100% vol change
        
        # Price difference
        price_diff = calculated_price - option_price
        
        # Check convergence
        if abs(price_diff) < tolerance:
            return sigma
        
        # Avoid division by zero
        if abs(vega) < 1e-10:
            return sigma
        
        # Newton-Raphson update
        sigma = sigma - price_diff / vega
        
        # Keep sigma in reasonable bounds
        sigma = max(0.001, min(5.0, sigma))
    
    # If didn't converge, return best guess
    return sigma


def delta_from_strike(
    strike: float,
    option_type: str,
    S: float,
    T: float,
    r: float,
    sigma: float
) -> float:
    """
    Calculate delta for a given strike.
    Useful for finding strikes that match target deltas (e.g., 30-delta puts).
    
    Returns:
        float: Delta value
    """
    return calculate_delta(option_type, S, strike, T, r, sigma)


def find_strike_for_delta(
    target_delta: float,
    option_type: str,
    S: float,
    T: float,
    r: float,
    sigma: float,
    max_iterations: int = 50
) -> float:
    """
    Find strike price that produces a target delta using binary search.
    
    Parameters:
        target_delta: Desired delta (e.g., -0.30 for 30-delta put)
        option_type: 'call' or 'put'
        S: Spot price
        T: Time to expiry
        r: Risk-free rate
        sigma: Implied volatility
        max_iterations: Maximum iterations for search
    
    Returns:
        float: Strike price that produces target delta
    """
    if option_type.lower() == 'call':
        # For calls, delta ranges from 0 to 1
        # Higher strikes have lower deltas
        low_strike = S * 0.5
        high_strike = S * 1.5
    else:
        # For puts, delta ranges from -1 to 0
        # Higher strikes have more negative deltas
        low_strike = S * 0.5
        high_strike = S * 1.5
        target_delta = abs(target_delta)  # Work with absolute values
    
    for _ in range(max_iterations):
        mid_strike = (low_strike + high_strike) / 2
        delta = abs(calculate_delta(option_type, S, mid_strike, T, r, sigma))
        
        if abs(delta - target_delta) < 0.001:  # Within 0.1 delta
            return mid_strike
        
        if option_type.lower() == 'call':
            if delta > target_delta:
                low_strike = mid_strike
            else:
                high_strike = mid_strike
        else:  # put
            if delta > target_delta:
                high_strike = mid_strike
            else:
                low_strike = mid_strike
    
    return (low_strike + high_strike) / 2


if __name__ == "__main__":
    # Test the module
    print("Testing greeks.py...")
    
    # Example option parameters
    S = 450.0  # SPY spot
    K = 445.0  # Strike
    T = 30 / 365.0  # 30 days to expiry
    r = 0.05  # 5% risk-free rate
    sigma = 0.20  # 20% implied vol
    
    print(f"\nOption parameters:")
    print(f"Spot: ${S}, Strike: ${K}, DTE: {T*365:.0f} days, IV: {sigma:.1%}")
    
    # Test call Greeks
    print("\n=== CALL OPTION ===")
    call_greeks = calculate_greeks('call', S, K, T, r, sigma)
    for greek, value in call_greeks.items():
        print(f"{greek.capitalize():8s}: {value:10.4f}")
    
    # Test put Greeks
    print("\n=== PUT OPTION ===")
    put_greeks = calculate_greeks('put', S, K, T, r, sigma)
    for greek, value in put_greeks.items():
        print(f"{greek.capitalize():8s}: {value:10.4f}")
    
    # Test finding 30-delta put strike
    print("\n=== 30-DELTA PUT ===")
    target_delta = -0.30
    strike_30d = find_strike_for_delta(target_delta, 'put', S, T, r, sigma)
    actual_delta = calculate_delta('put', S, strike_30d, T, r, sigma)
    print(f"Target delta: {target_delta:.2f}")
    print(f"Strike found: ${strike_30d:.2f}")
    print(f"Actual delta: {actual_delta:.2f}")
    
    # Test implied vol calculation
    print("\n=== IMPLIED VOLATILITY ===")
    market_price = put_greeks['price']
    calc_iv = implied_volatility_newton(market_price, 'put', S, K, T, r)
    print(f"Input IV: {sigma:.4f}")
    print(f"Market price: ${market_price:.2f}")
    print(f"Calculated IV: {calc_iv:.4f}")
    print(f"Error: {abs(calc_iv - sigma):.6f}")

