"""
Visualization functions for volatility surface and backtest results.

Uses Plotly for interactive 3D plots and charts.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Optional


def plot_3d_volatility_surface(surface_dict: Dict, spot_price: float, option_type: str = 'put') -> go.Figure:
    """
    3D surface plot: Strike (x) vs Expiry (y) vs Implied Vol (z).
    
    Parameters:
        surface_dict: Output from build_surface()
        spot_price: Current spot price of underlying
        option_type: 'call' or 'put' (for labeling)
    
    Returns:
        plotly.graph_objects.Figure
    """
    # Extract grid data
    strikes = surface_dict['surface_grid']['strikes']
    times = surface_dict['surface_grid']['times']
    iv_surface = surface_dict['surface_grid']['iv']
    
    # Convert times to days for better readability
    times_days = times * 365
    
    # Create meshgrid
    X, Y = np.meshgrid(strikes, times_days)
    Z = iv_surface * 100  # Convert to percentage
    
    # Create 3D surface
    fig = go.Figure(data=[
        go.Surface(
            x=X,
            y=Y,
            z=Z,
            colorscale='Viridis',
            colorbar=dict(
                title='Implied Vol (%)',
                titleside='right'
            ),
            hovertemplate='<b>Strike:</b> $%{x:.2f}<br>' +
                          '<b>DTE:</b> %{y:.0f} days<br>' +
                          '<b>IV:</b> %{z:.1f}%<extra></extra>'
        )
    ])
    
    # Add ATM strike line
    atm_line_y = times_days
    atm_line_x = [spot_price] * len(times_days)
    atm_line_z = [Z[i, np.argmin(np.abs(strikes - spot_price))] for i in range(len(times_days))]
    
    fig.add_trace(go.Scatter3d(
        x=atm_line_x,
        y=atm_line_y,
        z=atm_line_z,
        mode='lines',
        line=dict(color='red', width=5),
        name='ATM',
        hovertemplate='<b>ATM Strike</b><br>$%{x:.2f}<extra></extra>'
    ))
    
    # Layout
    fig.update_layout(
        title=f'Implied Volatility Surface - {option_type.upper()}s',
        scene=dict(
            xaxis=dict(title='Strike Price ($)', backgroundcolor='white'),
            yaxis=dict(title='Days to Expiry', backgroundcolor='white'),
            zaxis=dict(title='Implied Volatility (%)', backgroundcolor='white'),
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.3)
            )
        ),
        width=900,
        height=700,
        margin=dict(l=0, r=0, b=0, t=40)
    )
    
    return fig


def plot_volatility_smile(options_df: pd.DataFrame, expiry_date: pd.Timestamp, spot_price: float) -> go.Figure:
    """
    2D plot: Strike (x) vs Implied Vol (y) for single expiry.
    Overlay ATM strike, current spot price.
    
    Parameters:
        options_df: Options data
        expiry_date: Specific expiry to plot
        spot_price: Current spot price
    
    Returns:
        plotly.graph_objects.Figure
    """
    # Filter for specific expiry
    df = options_df[options_df['expiry'] == expiry_date].copy()
    
    if len(df) == 0:
        # Return empty figure
        fig = go.Figure()
        fig.add_annotation(
            text="No data available for selected expiry",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Separate calls and puts
    calls = df[df['option_type'] == 'call'].sort_values('strike')
    puts = df[df['option_type'] == 'put'].sort_values('strike')
    
    fig = go.Figure()
    
    # Plot calls
    if len(calls) > 0:
        fig.add_trace(go.Scatter(
            x=calls['strike'],
            y=calls['implied_volatility'] * 100,
            mode='markers+lines',
            name='Calls',
            line=dict(color='green', width=2),
            marker=dict(size=6),
            hovertemplate='<b>Call</b><br>Strike: $%{x:.2f}<br>IV: %{y:.1f}%<extra></extra>'
        ))
    
    # Plot puts
    if len(puts) > 0:
        fig.add_trace(go.Scatter(
            x=puts['strike'],
            y=puts['implied_volatility'] * 100,
            mode='markers+lines',
            name='Puts',
            line=dict(color='red', width=2),
            marker=dict(size=6),
            hovertemplate='<b>Put</b><br>Strike: $%{x:.2f}<br>IV: %{y:.1f}%<extra></extra>'
        ))
    
    # Add vertical line at spot price
    fig.add_vline(
        x=spot_price,
        line=dict(color='blue', width=2, dash='dash'),
        annotation_text=f'Spot: ${spot_price:.2f}',
        annotation_position='top'
    )
    
    # Layout
    dte = (expiry_date - df['quote_date'].iloc[0]).days
    fig.update_layout(
        title=f'Volatility Smile - {expiry_date.date()} ({dte} DTE)',
        xaxis_title='Strike Price ($)',
        yaxis_title='Implied Volatility (%)',
        hovermode='x unified',
        width=800,
        height=500,
        legend=dict(x=0.02, y=0.98)
    )
    
    return fig


def plot_pnl_curve(backtest_results: Dict) -> go.Figure:
    """
    Line chart: Date (x) vs Cumulative P&L (y).
    Overlay individual trade entry/exit points.
    
    Parameters:
        backtest_results: Output from StrategyBacktest.calculate_metrics()
    
    Returns:
        plotly.graph_objects.Figure
    """
    pv_df = backtest_results['portfolio_history']
    trades = backtest_results['trades']
    
    # Calculate cumulative P&L from initial capital
    initial_capital = pv_df['portfolio_value'].iloc[0]
    pv_df['cumulative_pnl'] = pv_df['portfolio_value'] - initial_capital
    
    fig = go.Figure()
    
    # Plot cumulative P&L
    fig.add_trace(go.Scatter(
        x=pv_df['date'],
        y=pv_df['cumulative_pnl'],
        mode='lines',
        name='Cumulative P&L',
        line=dict(color='blue', width=2),
        fill='tozeroy',
        fillcolor='rgba(0, 100, 255, 0.1)',
        hovertemplate='Date: %{x}<br>P&L: $%{y:,.0f}<extra></extra>'
    ))
    
    # Add zero line
    fig.add_hline(
        y=0,
        line=dict(color='gray', width=1, dash='dash'),
        annotation_text='Breakeven'
    )
    
    # Plot trade entry/exit points
    if len(trades) > 0:
        entry_dates = [t.entry_date for t in trades]
        exit_dates = [t.exit_date for t in trades if t.exit_date]
        
        # Get P&L at entry dates
        entry_pnls = []
        for date in entry_dates:
            idx = (pv_df['date'] - date).abs().argmin()
            entry_pnls.append(pv_df.iloc[idx]['cumulative_pnl'])
        
        fig.add_trace(go.Scatter(
            x=entry_dates,
            y=entry_pnls,
            mode='markers',
            name='Trade Entry',
            marker=dict(color='green', size=8, symbol='triangle-up'),
            hovertemplate='Entry: %{x}<extra></extra>'
        ))
        
        # Get P&L at exit dates
        exit_pnls = []
        for date in exit_dates:
            idx = (pv_df['date'] - date).abs().argmin()
            exit_pnls.append(pv_df.iloc[idx]['cumulative_pnl'])
        
        fig.add_trace(go.Scatter(
            x=exit_dates,
            y=exit_pnls,
            mode='markers',
            name='Trade Exit',
            marker=dict(color='red', size=8, symbol='triangle-down'),
            hovertemplate='Exit: %{x}<extra></extra>'
        ))
    
    # Layout
    fig.update_layout(
        title='Cumulative P&L Over Time',
        xaxis_title='Date',
        yaxis_title='Cumulative P&L ($)',
        hovermode='x unified',
        width=900,
        height=500,
        legend=dict(x=0.02, y=0.98)
    )
    
    return fig


def plot_greeks_heatmap(options_df: pd.DataFrame, greek_name: str = 'delta') -> go.Figure:
    """
    Heatmap: Strike (y) vs Expiry (x) vs Greek value (color).
    
    Parameters:
        options_df: Options data with Greeks calculated
        greek_name: 'delta', 'gamma', 'vega', or 'theta'
    
    Returns:
        plotly.graph_objects.Figure
    """
    from src.greeks import calculate_greeks
    
    # Calculate Greeks if not present
    if greek_name not in options_df.columns:
        # Calculate Greeks for each option
        greeks_list = []
        for _, row in options_df.iterrows():
            greeks = calculate_greeks(
                row['option_type'],
                row['underlying_price'],
                row['strike'],
                row['time_to_expiry'],
                0.05,  # risk-free rate
                row['implied_volatility']
            )
            greeks_list.append(greeks[greek_name])
        
        options_df = options_df.copy()
        options_df[greek_name] = greeks_list
    
    # Create pivot table
    pivot = options_df.pivot_table(
        values=greek_name,
        index='strike',
        columns='expiry',
        aggfunc='mean'
    )
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        x=[pd.to_datetime(col).strftime('%Y-%m-%d') for col in pivot.columns],
        y=pivot.index,
        z=pivot.values,
        colorscale='RdBu_r' if greek_name == 'delta' else 'Viridis',
        colorbar=dict(title=greek_name.capitalize()),
        hovertemplate='Expiry: %{x}<br>Strike: $%{y:.2f}<br>' +
                      f'{greek_name.capitalize()}: %{{z:.4f}}<extra></extra>'
    ))
    
    # Layout
    fig.update_layout(
        title=f'{greek_name.capitalize()} Heatmap',
        xaxis_title='Expiry Date',
        yaxis_title='Strike Price ($)',
        width=700,
        height=500
    )
    
    return fig


def plot_trade_distribution(backtest_results: Dict) -> go.Figure:
    """
    Histogram: P&L per trade.
    Show win/loss distribution.
    
    Parameters:
        backtest_results: Output from StrategyBacktest.calculate_metrics()
    
    Returns:
        plotly.graph_objects.Figure
    """
    trades = backtest_results['trades']
    
    if len(trades) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No trades to display",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    pnls = [t.total_pnl for t in trades]
    
    # Create histogram
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=pnls,
        nbinsx=20,
        marker=dict(
            color=pnls,
            colorscale='RdYlGn',
            line=dict(color='black', width=1)
        ),
        hovertemplate='P&L Range: %{x}<br>Count: %{y}<extra></extra>'
    ))
    
    # Add vertical line at zero
    fig.add_vline(
        x=0,
        line=dict(color='black', width=2, dash='dash'),
        annotation_text='Breakeven'
    )
    
    # Add mean line
    mean_pnl = np.mean(pnls)
    fig.add_vline(
        x=mean_pnl,
        line=dict(color='blue', width=2),
        annotation_text=f'Mean: ${mean_pnl:.2f}',
        annotation_position='top'
    )
    
    # Layout
    wins = sum(1 for p in pnls if p > 0)
    win_rate = wins / len(pnls) * 100
    
    fig.update_layout(
        title=f'Trade P&L Distribution (Win Rate: {win_rate:.1f}%)',
        xaxis_title='P&L per Trade ($)',
        yaxis_title='Number of Trades',
        width=800,
        height=500,
        showlegend=False
    )
    
    return fig


def plot_monthly_returns(backtest_results: Dict) -> go.Figure:
    """
    Monthly returns heatmap.
    
    Parameters:
        backtest_results: Output from StrategyBacktest.calculate_metrics()
    
    Returns:
        plotly.graph_objects.Figure
    """
    pv_df = backtest_results['portfolio_history'].copy()
    
    # Calculate daily returns
    pv_df['returns'] = pv_df['portfolio_value'].pct_change()
    pv_df['year'] = pd.to_datetime(pv_df['date']).dt.year
    pv_df['month'] = pd.to_datetime(pv_df['date']).dt.month
    
    # Calculate monthly returns
    monthly = pv_df.groupby(['year', 'month'])['returns'].sum() * 100  # Convert to %
    
    if len(monthly) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="Insufficient data for monthly returns",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Reshape for heatmap
    monthly_df = monthly.reset_index()
    pivot = monthly_df.pivot(index='year', columns='month', values='returns')
    
    # Month names
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        x=[month_names[int(m)-1] for m in pivot.columns],
        y=pivot.index,
        z=pivot.values,
        colorscale='RdYlGn',
        zmid=0,
        colorbar=dict(title='Return (%)'),
        hovertemplate='%{y} %{x}<br>Return: %{z:.2f}%<extra></extra>'
    ))
    
    # Layout
    fig.update_layout(
        title='Monthly Returns Heatmap',
        xaxis_title='Month',
        yaxis_title='Year',
        width=800,
        height=400
    )
    
    return fig


def plot_metrics_cards(backtest_results: Dict) -> Dict[str, go.Figure]:
    """
    Create individual metric visualizations.
    
    Returns:
        dict: {metric_name: figure}
    """
    metrics = {}
    
    # Sharpe ratio gauge
    sharpe = backtest_results['sharpe']
    fig_sharpe = go.Figure(go.Indicator(
        mode='gauge+number',
        value=sharpe,
        title={'text': 'Sharpe Ratio'},
        gauge={
            'axis': {'range': [-1, 3]},
            'bar': {'color': 'darkblue'},
            'steps': [
                {'range': [-1, 0], 'color': 'lightcoral'},
                {'range': [0, 1], 'color': 'lightyellow'},
                {'range': [1, 2], 'color': 'lightgreen'},
                {'range': [2, 3], 'color': 'darkgreen'}
            ],
            'threshold': {
                'line': {'color': 'red', 'width': 4},
                'thickness': 0.75,
                'value': 1.0
            }
        }
    ))
    fig_sharpe.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
    metrics['sharpe'] = fig_sharpe
    
    return metrics


if __name__ == "__main__":
    print("Testing visualizations.py...")
    
    from data_loader import fetch_spy_options_chain, preprocess_options_data
    from surface_builder import build_surface
    
    # Load data
    print("\nLoading data...")
    options_df = fetch_spy_options_chain(use_cache=True)
    options_df = preprocess_options_data(options_df)
    
    spot_price = options_df['underlying_price'].iloc[0]
    
    # Build surface
    print("Building surface...")
    surface = build_surface(options_df)
    
    # Test 3D surface plot
    print("Creating 3D surface plot...")
    fig_surface = plot_3d_volatility_surface(surface, spot_price)
    fig_surface.write_html('/tmp/test_surface.html')
    print("Saved to /tmp/test_surface.html")
    
    # Test volatility smile
    print("\nCreating volatility smile plot...")
    first_expiry = options_df['expiry'].iloc[0]
    fig_smile = plot_volatility_smile(options_df, first_expiry, spot_price)
    fig_smile.write_html('/tmp/test_smile.html')
    print("Saved to /tmp/test_smile.html")
    
    # Test Greeks heatmap
    print("\nCreating Greeks heatmap...")
    fig_delta = plot_greeks_heatmap(options_df, 'delta')
    fig_delta.write_html('/tmp/test_greeks.html')
    print("Saved to /tmp/test_greeks.html")
    
    print("\nVisualization tests complete!")

