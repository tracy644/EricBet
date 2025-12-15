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

# --- Helper: Fetch Data with Caching ---
# We keep the caching to minimize how often we ask Yahoo for data.
# We REMOVED the manual session. We are relying on 'curl-cffi' (in requirements.txt)
# to handle the browser impersonation automatically behind the scenes.
@st.cache_data(ttl=43200) 
def fetch_stock_data(ticker):
    stock = yf.Ticker(ticker)
    # Fetch 2 years of history
    hist = stock.history(period="2y")
    return hist

def get_projection(hist, target_date_str):
    """
    Calculates a simple linear regression projection based on historical data.
    """
    if hist.empty:
        return 0.0

    # Prepare data for linear regression
    hist = hist.copy() # Avoid SettingWithCopy warning
    hist['Date_Ordinal'] = hist.index.map(pd.Timestamp.toordinal)
    
    X = hist['Date_Ordinal'].values.reshape(-1, 1)
    y = hist['Close'].values

    # Calculate slope (m) and intercept (b) -> y = mx + b
    slope, intercept = np.polyfit(X.flatten(), y, 1)

    # Predict for target date
    target_date = pd.to_datetime(target_date_str)
    target_ordinal = target_date.toordinal()
    
    projected_price = (slope * target_ordinal) + intercept
    return projected_price

# --- Streamlit App Layout ---
st.set_page_config(page_title="Stock Tracker & Projection", page_icon="📈")

st.title("📈 AVGO vs VTSAX Tracker")
st.write(f"Projection Target Date: **{TARGET_DATE}**")
st.write("---")

cols = st.columns(len(STOCKS))

for index, stock_info in enumerate(STOCKS):
    ticker = stock_info["ticker"]
    start_price = stock_info["start_price"]
    
    with cols[index]:
        st.subheader(f"{ticker}")
        st.caption(stock_info["name"])
        
        try:
            # use our cached fetch function
            hist_data = fetch_stock_data(ticker)
            
            if not hist_data.empty:
                current_price = hist_data['Close'].iloc[-1]
                
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
                projected_val = get_projection(hist_data, TARGET_DATE)
                proj_gain_pct = ((projected_val - start_price) / start_price) * 100
                
                st.info(f"🔮 **July 4, 2026 Projection**")
                st.write(f"Estimated Value: **${projected_val:.2f}**")
                st.write(f"Implied Gain: **{proj_gain_pct:.1f}%**")
            else:
                st.error("No data found.")
                
        except Exception as e:
            st.error(f"Error loading data: {e}")
            st.caption("Try refreshing in a few minutes.")

st.write("---")
st.caption("Disclaimer: Projections are based on a linear regression of the last 2 years. Not financial advice.")

if st.button("Force Refresh Data"):
    st.cache_data.clear()
    st.rerun()
