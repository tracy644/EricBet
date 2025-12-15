import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime as dt

# --- Configuration ---
TARGET_DATE = "2026-07-04"
STOCKS = [
    {"ticker": "AVGO", "start_price": 294.30, "name": "Broadcom Inc."},
    {"ticker": "VTSAX", "start_price": 152.64, "name": "Vanguard Total Stock Market"},
]

# --- Helper: Fetch Data with Caching ---
@st.cache_data(ttl=43200) 
def fetch_stock_data(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="2y")
    return hist

def get_projection(hist, target_date_str):
    if hist.empty:
        return 0.0
    hist = hist.copy()
    hist['Date_Ordinal'] = hist.index.map(pd.Timestamp.toordinal)
    X = hist['Date_Ordinal'].values.reshape(-1, 1)
    y = hist['Close'].values
    slope, intercept = np.polyfit(X.flatten(), y, 1)
    target_date = pd.to_datetime(target_date_str)
    target_ordinal = target_date.toordinal()
    projected_price = (slope * target_ordinal) + intercept
    return projected_price

# --- Streamlit App Layout ---
st.set_page_config(page_title="Stock Tracker & Projection", page_icon="📈")

st.title("📈 AVGO vs VTSAX Tracker")
st.write(f"Projection Target Date: **{TARGET_DATE}**")
st.write("---")

# 1. Fetch all data first so we can compare them
stock_data_store = []

for stock_info in STOCKS:
    try:
        hist = fetch_stock_data(stock_info["ticker"])
        if not hist.empty:
            current_price = hist['Close'].iloc[-1]
            gain_pct = ((current_price - stock_info["start_price"]) / stock_info["start_price"]) * 100
            
            stock_data_store.append({
                "ticker": stock_info["ticker"],
                "name": stock_info["name"],
                "start_price": stock_info["start_price"],
                "current_price": current_price,
                "gain_pct": gain_pct,
                "history": hist
            })
    except Exception as e:
        st.error(f"Error fetching {stock_info['ticker']}: {e}")

# 2. Display the data in columns
if len(stock_data_store) == 2:
    cols = st.columns(2)
    
    # Get the gain percentages to compare
    stock_a = stock_data_store[0] # AVGO
    stock_b = stock_data_store[1] # VTSAX
    
    # Calculate "Price to Match" for Stock A (AVGO)
    # Target Price = Start Price * (1 + Other_Stock_Gain_Decimal)
    target_price_for_a = stock_a["start_price"] * (1 + (stock_b["gain_pct"] / 100))
    
    # Calculate "Price to Match" for Stock B (VTSAX)
    target_price_for_b = stock_b["start_price"] * (1 + (stock_a["gain_pct"] / 100))
    
    # Store these targets back into the objects for easy access in the loop
    stock_a["match_price"] = target_price_for_a
    stock_a["other_ticker"] = stock_b["ticker"]
    
    stock_b["match_price"] = target_price_for_b
    stock_b["other_ticker"] = stock_a["ticker"]

    # Render the columns
    for index, data in enumerate(stock_data_store):
        with cols[index]:
            st.subheader(f"{data['ticker']}")
            st.caption(data['name'])
            
            # Metric
            st.metric(
                label="Current Price",
                value=f"${data['current_price']:.2f}",
                delta=f"{data['gain_pct']:.2f}% (Since ${data['start_price']:.2f})"
            )
            
            # --- New Feature: Price to Match ---
            st.markdown(f"**🎯 Price to Match {data['other_ticker']}:**")
            
            diff = data['match_price'] - data['current_price']
            if diff > 0:
                # We are behind, need to grow
                st.write(f"Need to hit: **${data['match_price']:.2f}** (Up ${diff:.2f})")
            else:
                # We are ahead
                st.write(f"Already beating {data['other_ticker']}! (Equivalent: ${data['match_price']:.2f})")
            
            st.write("---")

            # Projection
            projected_val = get_projection(data['history'], TARGET_DATE)
            proj_gain_pct = ((projected_val - data['start_price']) / data['start_price']) * 100
            
            st.info(f"🔮 **July 4, 2026 Projection**")
            st.write(f"Estimated Value: **${projected_val:.2f}**")
            st.write(f"Implied Gain: **{proj_gain_pct:.1f}%**")

else:
    st.warning("Could not load data for both stocks to perform comparison.")

st.write("---")
st.caption("Disclaimer: Projections are based on a linear regression of the last 2 years. Not financial advice.")

if st.button("Force Refresh Data"):
    st.cache_data.clear()
    st.rerun()
