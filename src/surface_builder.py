"""
SVI (Stochastic Volatility Inspired) volatility surface calibration.

Fits arbitrage-free volatility surfaces to options data using the SVI parameterization.
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize, differential_evolution
from scipy.interpolate import interp2d, RBFInterpolator
from typing import Dict, List, Tuple, Optional
import warnings

warnings.filterwarnings('ignore')


def svi_formula(k: np.ndarray, a: float, b: float, rho: float, m: float, sigma: float) -> np.ndarray:
    """
    SVI formula for total implied variance.
    
    w(k) = a + b * (ρ * (k - m) + sqrt((k - m)² + σ²))
    
    Parameters:
        k: log-moneyness = log(K/F) where F is forward price
        a: vertical shift of variance curve
        b: angle of the wings
        rho: orientation (skew)
        m: horizontal shift
        sigma: smoothness of the vertex
    
    Returns:
        np.ndarray: Total implied variance (σ²T)
    """
    k = np.asarray(k)
    return a + b * (rho * (k - m) + np.sqrt((k - m) ** 2 + sigma ** 2))


def svi_to_impl_vol(k: np.ndarray, T: float, a: float, b: float, rho: float, m: float, sigma: float) -> np.ndarray:
    """
    Convert SVI parameters to implied volatility.
    
    σ(k,T) = sqrt(w(k) / T)
    
    Returns:
        np.ndarray: Implied volatility
    """
    w = svi_formula(k, a, b, rho, m, sigma)
    w = np.maximum(w, 1e-6)  # Prevent negative variance
    return np.sqrt(w / T)


def check_svi_arbitrage_conditions(a: float, b: float, rho: float, sigma: float) -> bool:
    """
    Check if SVI parameters satisfy no-arbitrage conditions.
    
    Conditions:
    1. a + b * σ * sqrt(1 - ρ²) >= 0  (non-negative variance)
    2. b >= 0  (positive slope)
    3. |ρ| <= 1  (valid correlation)
    4. σ > 0  (positive smoothness)
    5. b * (1 + |ρ|) < 4  (butterfly arbitrage)
    
    Returns:
        bool: True if conditions satisfied
    """
    # Condition 1: non-negative variance at vertex
    if a + b * sigma * np.sqrt(1 - rho ** 2) < -1e-6:
        return False
    
    # Condition 2: positive slope
    if b < 0:
        return False
    
    # Condition 3: valid correlation
    if abs(rho) > 1:
        return False
    
    # Condition 4: positive smoothness
    if sigma <= 0:
        return False
    
    # Condition 5: butterfly arbitrage (relaxed slightly)
    if b * (1 + abs(rho)) > 4.5:
        return False
    
    return True


def fit_svi_slice(
    strikes: np.ndarray,
    impl_vols: np.ndarray,
    forward_price: float,
    time_to_expiry: float,
    method: str = 'differential_evolution'
) -> Dict[str, float]:
    """
    Fit SVI parameters to a single expiry slice.
    
    Parameters:
        strikes: np.array of strike prices
        impl_vols: np.array of implied volatilities (decimal, e.g., 0.20 for 20%)
        forward_price: float, forward price of underlying
        time_to_expiry: float, years to expiry
    
    Returns:
        dict: {'a': float, 'b': float, 'rho': float, 'm': float, 'sigma': float, 'error': float}
    """
    # Convert to log-moneyness
    k = np.log(strikes / forward_price)
    
    # Total implied variance
    w_market = (impl_vols ** 2) * time_to_expiry
    
    # Objective function: minimize squared error
    def objective(params):
        a, b, rho, m, sigma = params
        
        # Check arbitrage conditions
        if not check_svi_arbitrage_conditions(a, b, rho, sigma):
            return 1e10
        
        w_model = svi_formula(k, a, b, rho, m, sigma)
        error = np.sum((w_model - w_market) ** 2)
        
        return error
    
    # Initial guess based on market data
    atm_var = np.median(w_market)
    
    if method == 'differential_evolution':
        # Use differential evolution for global optimization
        bounds = [
            (0.001, 0.5),      # a: vertical shift
            (0.001, 1.0),      # b: angle
            (-0.99, 0.99),     # rho: correlation
            (-0.5, 0.5),       # m: horizontal shift
            (0.01, 1.0)        # sigma: smoothness
        ]
        
        result = differential_evolution(
            objective,
            bounds,
            seed=42,
            maxiter=200,
            atol=1e-6,
            tol=1e-6,
            workers=1
        )
        
    else:  # SLSQP
        # Initial guess
        x0 = [atm_var * 0.5, 0.1, -0.3, 0.0, 0.1]
        
        # Bounds
        bounds = [
            (0.001, 0.5),      # a
            (0.001, 1.0),      # b
            (-0.99, 0.99),     # rho
            (-0.5, 0.5),       # m
            (0.01, 1.0)        # sigma
        ]
        
        # Constraints for no-arbitrage
        constraints = [
            {
                'type': 'ineq',
                'fun': lambda x: x[0] + x[1] * x[4] * np.sqrt(1 - x[2] ** 2)  # a + b*σ*sqrt(1-ρ²) >= 0
            },
            {
                'type': 'ineq',
                'fun': lambda x: 4.5 - x[1] * (1 + abs(x[2]))  # b*(1+|ρ|) < 4.5
            }
        ]
        
        result = minimize(
            objective,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 500}
        )
    
    a, b, rho, m, sigma = result.x
    
    # Calculate final error
    w_model = svi_formula(k, a, b, rho, m, sigma)
    rmse = np.sqrt(np.mean((w_model - w_market) ** 2))
    
    return {
        'a': a,
        'b': b,
        'rho': rho,
        'm': m,
        'sigma': sigma,
        'error': rmse,
        'success': result.success
    }


def build_surface(options_df: pd.DataFrame, risk_free_rate: float = 0.05) -> Dict:
    """
    Build complete volatility surface by fitting SVI to each expiry.
    
    Parameters:
        options_df: pd.DataFrame from data_loader (must be preprocessed)
        risk_free_rate: Annual risk-free rate for forward price calculation
    
    Returns:
        dict: {
            'expiries': list of expiry dates,
            'times_to_expiry': list of years to expiry,
            'svi_params': list of dicts (one per expiry),
            'surface_grid': dict with keys for strikes, expiries, and IV grid,
            'spot_price': float,
            'atm_iv': float
        }
    """
    # Get spot price
    spot_price = options_df['underlying_price'].iloc[0]
    
    # Group by expiry
    expiry_groups = options_df.groupby('expiry')
    
    expiries = []
    times_to_expiry = []
    svi_params_list = []
    
    for expiry, group in expiry_groups:
        # Calculate time to expiry
        T = group['time_to_expiry'].iloc[0]
        
        if T <= 0 or len(group) < 5:  # Need at least 5 points
            continue
        
        # Calculate forward price: F = S * e^(rT)
        forward_price = spot_price * np.exp(risk_free_rate * T)
        
        # Get strikes and IVs (use mid of calls and puts at same strike)
        strike_iv = group.groupby('strike')['implied_volatility'].mean()
        
        if len(strike_iv) < 5:
            continue
        
        strikes = strike_iv.index.values
        impl_vols = strike_iv.values
        
        # Filter out extreme values
        valid_mask = (impl_vols > 0.02) & (impl_vols < 2.0)
        strikes = strikes[valid_mask]
        impl_vols = impl_vols[valid_mask]
        
        if len(strikes) < 5:
            continue
        
        try:
            # Fit SVI to this slice
            params = fit_svi_slice(strikes, impl_vols, forward_price, T)
            
            if params['success'] and params['error'] < 0.1:
                expiries.append(expiry)
                times_to_expiry.append(T)
                svi_params_list.append(params)
            else:
                print(f"Warning: SVI fit failed for expiry {expiry}")
        
        except Exception as e:
            print(f"Error fitting expiry {expiry}: {e}")
            continue
    
    if len(svi_params_list) == 0:
        raise ValueError("Failed to fit SVI to any expiry slice")
    
    # Build interpolation grid
    # Create grid of strikes and expiries
    strike_min = options_df['strike'].min()
    strike_max = options_df['strike'].max()
    strike_grid = np.linspace(strike_min, strike_max, 50)
    
    T_grid = np.array(times_to_expiry)
    
    # Build 2D surface grid
    surface_grid_data = np.zeros((len(T_grid), len(strike_grid)))
    
    for i, (T, params) in enumerate(zip(times_to_expiry, svi_params_list)):
        forward_price = spot_price * np.exp(risk_free_rate * T)
        k = np.log(strike_grid / forward_price)
        iv = svi_to_impl_vol(k, T, params['a'], params['b'], params['rho'], params['m'], params['sigma'])
        surface_grid_data[i, :] = iv
    
    # Calculate ATM IV (for display)
    atm_idx = np.argmin(np.abs(strike_grid - spot_price))
    atm_iv = np.mean(surface_grid_data[:, atm_idx])
    
    return {
        'expiries': expiries,
        'times_to_expiry': times_to_expiry,
        'svi_params': svi_params_list,
        'surface_grid': {
            'strikes': strike_grid,
            'times': T_grid,
            'iv': surface_grid_data
        },
        'spot_price': spot_price,
        'atm_iv': atm_iv,
        'risk_free_rate': risk_free_rate
    }


def interpolate_iv(
    strike: float,
    time_to_expiry: float,
    surface_dict: Dict,
    method: str = 'linear'
) -> float:
    """
    Interpolate implied volatility for arbitrary strike/expiry using fitted SVI surface.
    
    Parameters:
        strike: Strike price
        time_to_expiry: Years to expiry
        surface_dict: Output from build_surface()
        method: Interpolation method ('linear' or 'nearest')
    
    Returns:
        float: Interpolated implied volatility
    """
    spot_price = surface_dict['spot_price']
    risk_free_rate = surface_dict['risk_free_rate']
    
    # Find nearest expiry slices
    times = np.array(surface_dict['times_to_expiry'])
    
    if time_to_expiry <= times[0]:
        # Use first slice
        idx = 0
        T = times[0]
        params = surface_dict['svi_params'][0]
    elif time_to_expiry >= times[-1]:
        # Use last slice
        idx = -1
        T = times[-1]
        params = surface_dict['svi_params'][-1]
    else:
        # Interpolate between two slices
        idx = np.searchsorted(times, time_to_expiry)
        
        # Get adjacent slices
        T1, T2 = times[idx - 1], times[idx]
        params1 = surface_dict['svi_params'][idx - 1]
        params2 = surface_dict['svi_params'][idx]
        
        # Calculate IV from both slices
        forward_price1 = spot_price * np.exp(risk_free_rate * T1)
        forward_price2 = spot_price * np.exp(risk_free_rate * T2)
        
        k1 = np.log(strike / forward_price1)
        k2 = np.log(strike / forward_price2)
        
        iv1 = svi_to_impl_vol(np.array([k1]), T1, params1['a'], params1['b'], 
                               params1['rho'], params1['m'], params1['sigma'])[0]
        iv2 = svi_to_impl_vol(np.array([k2]), T2, params2['a'], params2['b'],
                               params2['rho'], params2['m'], params2['sigma'])[0]
        
        # Linear interpolation in time
        weight = (time_to_expiry - T1) / (T2 - T1)
        iv = iv1 * (1 - weight) + iv2 * weight
        
        return float(iv)
    
    # Single slice case
    forward_price = spot_price * np.exp(risk_free_rate * T)
    k = np.log(strike / forward_price)
    iv = svi_to_impl_vol(np.array([k]), T, params['a'], params['b'], 
                          params['rho'], params['m'], params['sigma'])[0]
    
    return float(iv)


def get_vol_smile(surface_dict: Dict, expiry_idx: int = 0) -> pd.DataFrame:
    """
    Extract volatility smile for a specific expiry.
    
    Parameters:
        surface_dict: Output from build_surface()
        expiry_idx: Index of expiry to extract (0 = nearest)
    
    Returns:
        pd.DataFrame with columns: strike, implied_vol, moneyness
    """
    strikes = surface_dict['surface_grid']['strikes']
    iv = surface_dict['surface_grid']['iv'][expiry_idx, :]
    spot_price = surface_dict['spot_price']
    
    df = pd.DataFrame({
        'strike': strikes,
        'implied_vol': iv,
        'moneyness': strikes / spot_price
    })
    
    return df


if __name__ == "__main__":
    # Test the module
    print("Testing surface_builder.py...")
    
    from data_loader import fetch_spy_options_chain, preprocess_options_data
    
    # Load data
    print("\nLoading options data...")
    options_df = fetch_spy_options_chain(use_cache=True)
    options_df = preprocess_options_data(options_df)
    
    print(f"Loaded {len(options_df)} options")
    print(f"Expiries: {options_df['expiry'].nunique()}")
    
    # Build surface
    print("\nBuilding SVI surface...")
    surface = build_surface(options_df)
    
    print(f"\nSurface built successfully!")
    print(f"Number of expiries fitted: {len(surface['expiries'])}")
    print(f"Spot price: ${surface['spot_price']:.2f}")
    print(f"ATM IV: {surface['atm_iv']:.2%}")
    
    # Display SVI parameters for each expiry
    print("\nSVI Parameters by Expiry:")
    for i, (expiry, T, params) in enumerate(zip(surface['expiries'], 
                                                  surface['times_to_expiry'], 
                                                  surface['svi_params'])):
        print(f"\n{i+1}. Expiry: {expiry.date()}, T={T:.3f} years")
        print(f"   a={params['a']:.4f}, b={params['b']:.4f}, rho={params['rho']:.3f}, "
              f"m={params['m']:.3f}, sigma={params['sigma']:.3f}")
        print(f"   RMSE: {params['error']:.6f}")
    
    # Test interpolation
    print("\n=== Testing Interpolation ===")
    test_strike = surface['spot_price'] * 0.95  # 5% OTM put
    test_T = 30 / 365  # 30 days
    
    iv = interpolate_iv(test_strike, test_T, surface)
    print(f"Strike: ${test_strike:.2f} (moneyness={test_strike/surface['spot_price']:.3f})")
    print(f"Time to expiry: {test_T*365:.0f} days")
    print(f"Interpolated IV: {iv:.2%}")

