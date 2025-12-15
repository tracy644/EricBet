import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime as dt

# --- Configuration ---
TARGET_DATE = "2026-07-04"
STOCKS = [
    {"ticker": "AVGO", "start_price": 369.56, "name": "Broadcom Inc."},
    {"ticker": "VTSAX", "start_price": 152.64, "name": "Vanguard Total Stock Market"},
]

def get_projection(ticker, target_date_str):
    """
    Calculates a simple linear regression projection based on the last 2 years of data.
    """
    # 1. Get 2 years of historical data
    stock = yf.Ticker(ticker)
    hist = stock.history(period="2y")
    
    if hist.empty:
        return 0.0

    # 2. Prepare data for linear regression
    # We convert dates to 'ordinal' numbers so the math works
    hist['Date_Ordinal'] = hist.index.map(pd.Timestamp.toordinal)
    
    X = hist['Date_Ordinal'].values.reshape(-1, 1)
    y = hist['Close'].values

    # 3. Calculate slope (m) and intercept (b) -> y = mx + b
    # Using numpy polyfit for a degree 1 (linear) fit
    slope, intercept = np.polyfit(X.flatten(), y, 1)

    # 4. Predict for target date
    target_date = pd.to_datetime(target_date_str)
    target_ordinal = target_date.toordinal()
    
    projected_price = (slope * target_ordinal) + intercept
    return projected_price

# --- Streamlit App Layout ---
st.set_page_config(page_title="Stock Tracker & Projection", page_icon="📈")

st.title("📈 AVGO vs VTSAX Tracker")
st.write(f"Projection Target Date: **{TARGET_DATE}**")
st.write("---")

# Create columns for side-by-side comparison
cols = st.columns(len(STOCKS))

for index, stock_info in enumerate(STOCKS):
    ticker = stock_info["ticker"]
    start_price = stock_info["start_price"]
    
    with cols[index]:
        st.subheader(f"{ticker}")
        st.caption(stock_info["name"])
        
        # Fetch current data
        # Note: VTSAX is a mutual fund and updates once per day after close.
        # AVGO updates in real-time during market hours.
        data = yf.Ticker(ticker)
        todays_data = data.history(period="1d")
        
        if not todays_data.empty:
            current_price = todays_data['Close'].iloc[-1]
            
            # Calculate Gain/Loss
            gain_loss_amt = current_price - start_price
            gain_loss_pct = (gain_loss_amt / start_price) * 100
            
            # Display Metrics
            st.metric(
                label="Current Price",
                value=f"${current_price:.2f}",
                delta=f"{gain_loss_pct:.2f}% (Since ${start_price})"
            )
            
            # Calculate Projection
            projected_val = get_projection(ticker, TARGET_DATE)
            
            # Calculate Projected Gain vs Start
            proj_gain_pct = ((projected_val - start_price) / start_price) * 100
            
            st.info(f"🔮 **July 4, 2026 Projection**")
            st.write(f"Estimated Value: **${projected_val:.2f}**")
            st.write(f"Implied Gain: **{proj_gain_pct:.1f}%**")
            
        else:
            st.error("Could not fetch data.")

st.write("---")
st.caption("Disclaimer: Projections are based on a linear regression of the last 2 years of performance. This is not financial advice.")

if st.button("Refresh Data"):
    st.rerun()