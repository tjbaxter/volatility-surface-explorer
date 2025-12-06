"""
Volatility Surface Explorer & Options Strategy Backtest

A quantitative trading tool for analyzing SPY options markets and backtesting 
delta-hedged volatility strategies.

Main Streamlit application.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import custom modules
from src.data_loader import (
    fetch_spy_options_chain,
    preprocess_options_data,
    generate_synthetic_historical_data,
    get_spot_prices_series
)
from src.surface_builder import build_surface, interpolate_iv, get_vol_smile
from src.greeks import calculate_greeks
from src.strategy import StrategyBacktest
from src.visualizations import (
    plot_3d_volatility_surface,
    plot_volatility_smile,
    plot_pnl_curve,
    plot_greeks_heatmap,
    plot_trade_distribution,
    plot_monthly_returns
)

# Page configuration
st.set_page_config(
    page_title="Volatility Surface Explorer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.title("📈 About")
st.sidebar.markdown("""
**Volatility Surface Explorer & Strategy Backtest**

A quantitative trading tool for analyzing options markets and backtesting volatility strategies.

---

**Features:**
- Real-time SPY options data
- SVI volatility surface calibration
- Interactive 3D visualizations
- Greeks calculations
- Delta-hedged backtest

---

**Data:** SPY options via yfinance  
**Model:** SVI (Stochastic Volatility Inspired)  
**Strategy:** Delta-hedged skew selling

---

**Transaction Costs:**
- Options: 12 bps (10 bps spread + 2 bps slippage)
- Stock: 0.1 bps

---

**Contact:**  
Built for quantitative trading portfolio  
[GitHub](https://github.com) | [LinkedIn](https://linkedin.com)

---

*For educational purposes only. Past performance does not guarantee future results.*
""")

# Main title
st.title("📈 Volatility Surface Explorer")
st.markdown("*Advanced options analytics and strategy backtesting for SPY*")

# Data loading with caching
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_current_data():
    """Load and preprocess current options data."""
    try:
        df = fetch_spy_options_chain(use_cache=True)
        df = preprocess_options_data(df)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

@st.cache_data
def load_historical_data(start_date, end_date):
    """Load or generate historical options data for backtesting."""
    try:
        # For now, use synthetic data
        # In production, would load from database or API
        df = generate_synthetic_historical_data(start_date, end_date)
        df = preprocess_options_data(df)
        return df
    except Exception as e:
        st.error(f"Error loading historical data: {e}")
        return None

@st.cache_data
def build_vol_surface(options_df):
    """Build SVI volatility surface."""
    try:
        surface = build_surface(options_df)
        return surface
    except Exception as e:
        st.error(f"Error building surface: {e}")
        return None

# Load data
with st.spinner("Loading options data..."):
    options_df = load_current_data()

if options_df is None or len(options_df) == 0:
    st.error("Failed to load options data. Please try again later.")
    st.stop()

# Get key metrics
spot_price = options_df['underlying_price'].iloc[0]
quote_date = options_df['quote_date'].iloc[0]
num_options = len(options_df)
num_expiries = options_df['expiry'].nunique()

# Display key info
col1, col2, col3, col4 = st.columns(4)
col1.metric("Spot Price", f"${spot_price:.2f}")
col2.metric("Options in Chain", f"{num_options:,}")
col3.metric("Expiries", f"{num_expiries}")
col4.metric("Data Date", quote_date.strftime('%Y-%m-%d'))

st.markdown("---")

# Create tabs
tab1, tab2, tab3 = st.tabs(["🌐 Volatility Surface", "📊 Greeks Dashboard", "💰 Strategy Backtest"])

# ==================== TAB 1: VOLATILITY SURFACE ====================
with tab1:
    st.header("3D Volatility Surface")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Build surface
        with st.spinner("Building volatility surface..."):
            surface = build_vol_surface(options_df)
        
        if surface is not None:
            # Plot 3D surface
            fig_surface = plot_3d_volatility_surface(surface, spot_price)
            st.plotly_chart(fig_surface, use_container_width=True)
        else:
            st.error("Failed to build volatility surface")
    
    with col2:
        st.subheader("Surface Metrics")
        
        if surface is not None:
            st.metric("ATM Implied Vol", f"{surface['atm_iv']:.2%}")
            st.metric("Spot Price", f"${surface['spot_price']:.2f}")
            st.metric("Fitted Expiries", len(surface['expiries']))
            
            st.subheader("Expiry Details")
            for i, (expiry, T) in enumerate(zip(surface['expiries'][:5], surface['times_to_expiry'][:5])):
                dte = int(T * 365)
                st.text(f"{expiry.date()} ({dte}d)")
            
            if len(surface['expiries']) > 5:
                st.text(f"... and {len(surface['expiries']) - 5} more")
    
    # Volatility smile for selected expiry
    st.markdown("---")
    st.subheader("Volatility Smile")
    
    # Select expiry
    expiries_list = sorted(options_df['expiry'].unique())
    selected_expiry = st.selectbox(
        "Select Expiry",
        expiries_list,
        format_func=lambda x: f"{pd.to_datetime(x).strftime('%Y-%m-%d')} ({(pd.to_datetime(x) - quote_date).days}d)"
    )
    
    if selected_expiry is not None:
        fig_smile = plot_volatility_smile(options_df, pd.to_datetime(selected_expiry), spot_price)
        st.plotly_chart(fig_smile, use_container_width=True)

# ==================== TAB 2: GREEKS DASHBOARD ====================
with tab2:
    st.header("Greeks Dashboard")
    
    # Select expiry for Greeks
    expiry_for_greeks = st.selectbox(
        "Select Expiry for Greeks Analysis",
        expiries_list,
        format_func=lambda x: f"{pd.to_datetime(x).strftime('%Y-%m-%d')} ({(pd.to_datetime(x) - quote_date).days}d)",
        key='greeks_expiry'
    )
    
    if expiry_for_greeks is not None:
        df_slice = options_df[options_df['expiry'] == expiry_for_greeks].copy()
        
        # Calculate Greeks for the slice
        with st.spinner("Calculating Greeks..."):
            greeks_data = []
            for _, row in df_slice.iterrows():
                greeks = calculate_greeks(
                    row['option_type'],
                    row['underlying_price'],
                    row['strike'],
                    row['time_to_expiry'],
                    0.05,
                    row['implied_volatility']
                )
                greeks_data.append({
                    'strike': row['strike'],
                    'option_type': row['option_type'],
                    **greeks
                })
            
            greeks_df = pd.DataFrame(greeks_data)
        
        # Display Greeks heatmaps
        st.subheader("Greeks by Strike")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Delta**")
            # Create delta plot
            puts = greeks_df[greeks_df['option_type'] == 'put'].sort_values('strike')
            if len(puts) > 0:
                import plotly.graph_objects as go
                fig_delta = go.Figure()
                fig_delta.add_trace(go.Scatter(
                    x=puts['strike'],
                    y=puts['delta'],
                    mode='lines+markers',
                    name='Put Delta',
                    line=dict(color='red', width=2)
                ))
                fig_delta.add_hline(y=-0.30, line_dash="dash", annotation_text="30-delta")
                fig_delta.update_layout(
                    xaxis_title='Strike',
                    yaxis_title='Delta',
                    height=350
                )
                st.plotly_chart(fig_delta, use_container_width=True)
            
            st.markdown("**Vega**")
            if len(puts) > 0:
                fig_vega = go.Figure()
                fig_vega.add_trace(go.Scatter(
                    x=puts['strike'],
                    y=puts['vega'],
                    mode='lines+markers',
                    name='Put Vega',
                    line=dict(color='purple', width=2)
                ))
                fig_vega.update_layout(
                    xaxis_title='Strike',
                    yaxis_title='Vega',
                    height=350
                )
                st.plotly_chart(fig_vega, use_container_width=True)
        
        with col2:
            st.markdown("**Gamma**")
            if len(puts) > 0:
                fig_gamma = go.Figure()
                fig_gamma.add_trace(go.Scatter(
                    x=puts['strike'],
                    y=puts['gamma'],
                    mode='lines+markers',
                    name='Put Gamma',
                    line=dict(color='orange', width=2)
                ))
                fig_gamma.update_layout(
                    xaxis_title='Strike',
                    yaxis_title='Gamma',
                    height=350
                )
                st.plotly_chart(fig_gamma, use_container_width=True)
            
            st.markdown("**Theta**")
            if len(puts) > 0:
                fig_theta = go.Figure()
                fig_theta.add_trace(go.Scatter(
                    x=puts['strike'],
                    y=puts['theta'],
                    mode='lines+markers',
                    name='Put Theta',
                    line=dict(color='green', width=2)
                ))
                fig_theta.update_layout(
                    xaxis_title='Strike',
                    yaxis_title='Theta (per day)',
                    height=350
                )
                st.plotly_chart(fig_theta, use_container_width=True)
        
        # Top gamma options table
        st.markdown("---")
        st.subheader("Top 10 Gamma Options")
        st.markdown("*High gamma options are suitable for gamma scalping strategies*")
        
        top_gamma = greeks_df.nlargest(10, 'gamma')[
            ['strike', 'option_type', 'gamma', 'delta', 'vega', 'theta']
        ].reset_index(drop=True)
        
        st.dataframe(
            top_gamma.style.format({
                'strike': '${:.2f}',
                'gamma': '{:.6f}',
                'delta': '{:.4f}',
                'vega': '{:.4f}',
                'theta': '{:.4f}'
            }),
            use_container_width=True
        )

# ==================== TAB 3: STRATEGY BACKTEST ====================
with tab3:
    st.header("Delta-Hedged Skew Selling Strategy")
    
    st.markdown("""
    **Strategy Description:**
    - Sell 30-delta OTM puts when implied volatility exceeds realized volatility
    - Delta-hedge daily with SPY shares
    - Target 7-14 days to expiration
    - Stop-loss: -2% of position value
    - Take-profit: +50% of max gain
    - Max 5 concurrent positions
    """)
    
    st.markdown("---")
    
    # Backtest parameters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=pd.to_datetime("2023-01-01"),
            min_value=pd.to_datetime("2022-01-01"),
            max_value=pd.to_datetime("2024-12-01")
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=pd.to_datetime("2023-06-30"),
            min_value=pd.to_datetime("2022-01-01"),
            max_value=pd.to_datetime("2024-12-01")
        )
    
    with col3:
        initial_capital = st.number_input(
            "Initial Capital ($)",
            min_value=10000,
            max_value=10000000,
            value=100000,
            step=10000
        )
    
    # Advanced parameters (collapsible)
    with st.expander("Advanced Parameters"):
        col1, col2 = st.columns(2)
        
        with col1:
            iv_rv_threshold = st.slider(
                "IV-RV Threshold (σ)",
                min_value=0.5,
                max_value=3.0,
                value=2.0,
                step=0.25,
                help="Enter trade when IV exceeds RV by this many standard deviations"
            )
            
            min_dte = st.slider(
                "Min DTE",
                min_value=1,
                max_value=30,
                value=7,
                help="Minimum days to expiration"
            )
        
        with col2:
            max_dte = st.slider(
                "Max DTE",
                min_value=7,
                max_value=60,
                value=14,
                help="Maximum days to expiration"
            )
            
            max_positions = st.slider(
                "Max Positions",
                min_value=1,
                max_value=10,
                value=5,
                help="Maximum concurrent positions"
            )
    
    # Run backtest button
    if st.button("🚀 Run Backtest", type="primary"):
        
        # Load historical data
        with st.spinner("Loading historical data..."):
            hist_df = load_historical_data(
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
        
        if hist_df is None or len(hist_df) == 0:
            st.error("Failed to load historical data")
            st.stop()
        
        # Get spot price series
        spot_df = get_spot_prices_series(hist_df)
        
        st.success(f"Loaded {len(hist_df)} historical options across {len(spot_df)} trading days")
        
        # Run backtest
        with st.spinner("Running backtest... This may take a minute."):
            backtest = StrategyBacktest(
                hist_df,
                spot_df,
                risk_free_rate=0.05,
                initial_capital=initial_capital
            )
            
            # Update parameters
            backtest.iv_rv_threshold = iv_rv_threshold
            backtest.min_dte = min_dte
            backtest.max_dte = max_dte
            backtest.max_positions = max_positions
            
            results = backtest.run_backtest(
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
        
        # Display results
        st.success("✅ Backtest complete!")
        
        st.markdown("---")
        st.subheader("Performance Metrics")
        
        # Metrics cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Return",
                f"{results['total_return']:.2%}",
                delta=f"${results['final_value'] - initial_capital:,.0f}"
            )
        
        with col2:
            st.metric("Sharpe Ratio", f"{results['sharpe']:.2f}")
        
        with col3:
            st.metric("Max Drawdown", f"{results['max_dd']:.2%}")
        
        with col4:
            st.metric("Win Rate", f"{results['win_rate']:.1%}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Number of Trades", f"{results['num_trades']}")
        
        with col2:
            st.metric("Avg P&L per Trade", f"${results['avg_pnl']:.2f}")
        
        with col3:
            st.metric("Avg Hold Time", f"{results['avg_hold_days']:.1f} days")
        
        # P&L curve
        st.markdown("---")
        st.subheader("Cumulative P&L")
        fig_pnl = plot_pnl_curve(results)
        st.plotly_chart(fig_pnl, use_container_width=True)
        
        # Trade distribution
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Trade P&L Distribution")
            fig_dist = plot_trade_distribution(results)
            st.plotly_chart(fig_dist, use_container_width=True)
        
        with col2:
            st.subheader("Monthly Returns")
            fig_monthly = plot_monthly_returns(results)
            st.plotly_chart(fig_monthly, use_container_width=True)
        
        # Trade log
        st.markdown("---")
        st.subheader("Trade Log")
        
        if len(results['trades']) > 0:
            trades_data = []
            for trade in results['trades']:
                trades_data.append({
                    'ID': trade.trade_id,
                    'Entry': trade.entry_date.strftime('%Y-%m-%d'),
                    'Exit': trade.exit_date.strftime('%Y-%m-%d') if trade.exit_date else 'Open',
                    'Strike': trade.strike,
                    'Entry IV': trade.entry_iv,
                    'Option P&L': trade.option_pnl,
                    'Hedge P&L': trade.hedge_pnl,
                    'Total P&L': trade.total_pnl,
                    'Exit Reason': trade.exit_reason
                })
            
            trades_df = pd.DataFrame(trades_data)
            
            st.dataframe(
                trades_df.style.format({
                    'Strike': '${:.2f}',
                    'Entry IV': '{:.2%}',
                    'Option P&L': '${:.2f}',
                    'Hedge P&L': '${:.2f}',
                    'Total P&L': '${:.2f}'
                }).background_gradient(subset=['Total P&L'], cmap='RdYlGn', vmin=-500, vmax=500),
                use_container_width=True,
                height=400
            )
            
            # Download trades
            csv = trades_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Trade Log (CSV)",
                data=csv,
                file_name=f"backtest_trades_{start_date}_{end_date}.csv",
                mime="text/csv"
            )
        else:
            st.info("No trades were executed during the backtest period.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p><strong>Volatility Surface Explorer v1.0</strong></p>
    <p>Built with Streamlit, Python, and quantitative finance expertise</p>
    <p><em>Disclaimer: This tool is for educational and research purposes only. 
    Not financial advice. Options trading involves significant risk.</em></p>
</div>
""", unsafe_allow_html=True)

