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
    
    # 1. Get Historical Data (for the chart/projection)
    hist = stock.history(period="2y")
    
    # 2. Get the REAL latest price (more accurate for Mutual Funds like VTSAX)
    # fast_info is often more up-to-date than the last row of the dataframe
    try:
        latest_price = stock.fast_info['last_price']
    except:
        # Fallback if fast_info fails
        if not hist.empty:
            latest_price = hist['Close'].iloc[-1]
        else:
            latest_price = 0.0

    return hist, latest_price

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
st.set_page_config(page_title="Tracy vs Eric", page_icon="🍺")

st.header("Tracy VS Eric- One Beer to Rule Them All 🍺")
st.title("📈 AVGO vs VTSAX Tracker")
st.write(f"Projection Target Date: **{TARGET_DATE}**")
st.write("---")

# 1. Fetch all data first
stock_data_store = []

for stock_info in STOCKS:
    try:
        # Now fetching both the history AND the explicit latest price
        hist, current_price = fetch_stock_data(stock_info["ticker"])
        
        if not hist.empty and current_price > 0:
            # We use the explicit 'current_price' for calculations, 
            # but 'hist' for the projection and previous close.
            
            # Safe way to get previous close (2nd to last row)
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                
                # EDGE CASE: If VTSAX hasn't updated its history file yet, 
                # the "latest price" might be from today, but the history file only has yesterday.
                # We check if 'current_price' is basically the same as the last history row.
                last_hist_price = hist['Close'].iloc[-1]
                
                # If the fast_info price is different from the last history price, 
                # it means fast_info is NEWER. So use the last history price as "previous close".
                if abs(current_price - last_hist_price) > 0.01:
                    prev_close = last_hist_price
                else:
                    # If they are the same, go back one more day
                    prev_close = hist['Close'].iloc[-2]
            else:
                prev_close = current_price # Fallback

            # Overall Gain
            total_gain_pct = ((current_price - stock_info["start_price"]) / stock_info["start_price"]) * 100
            
            # Daily Gain
            daily_change_amt = current_price - prev_close
            daily_change_pct = ((current_price - prev_close) / prev_close) * 100
            
            stock_data_store.append({
                "ticker": stock_info["ticker"],
                "name": stock_info["name"],
                "start_price": stock_info["start_price"],
                "current_price": current_price,
                "prev_close": prev_close,
                "total_gain_pct": total_gain_pct,
                "daily_change_amt": daily_change_amt,
                "daily_change_pct": daily_change_pct,
                "history": hist
            })
    except Exception as e:
        st.error(f"Error fetching {stock_info['ticker']}: {e}")

# 2. Display and Compare
if len(stock_data_store) == 2:
    cols = st.columns(2)
    
    stock_a = stock_data_store[0] # AVGO
    stock_b = stock_data_store[1] # VTSAX
    
    # Calculate Targets to Match
    stock_a["match_price"] = stock_a["start_price"] * (1 + (stock_b["total_gain_pct"] / 100))
    stock_a["other_ticker"] = stock_b["ticker"]
    
    stock_b["match_price"] = stock_b["start_price"] * (1 + (stock_a["total_gain_pct"] / 100))
    stock_b["other_ticker"] = stock_a["ticker"]

    # Render Columns
    for index, data in enumerate(stock_data_store):
        with cols[index]:
            st.subheader(f"{data['ticker']}")
            st.caption(data['name'])
            
            # Main Metric
            st.metric(
                label="Current Price",
                value=f"${data['current_price']:.2f}",
                delta=f"{data['total_gain_pct']:.2f}% (Total Gain)"
            )
            
            # Daily Movement
            daily_color = "green" if data['daily_change_pct'] >= 0 else "red"
            st.markdown(
                f"**Today's Move:** <span style='color:{daily_color}'>"
                f"{data['daily_change_amt']:+.2f} ({data['daily_change_pct']:+.2f}%)</span>", 
                unsafe_allow_html=True
            )
            
            st.write("---")
            
            # Price to Match
            st.markdown(f"**🎯 Price to Match {data['other_ticker']}:**")
            diff = data['match_price'] - data['current_price']
            
            if abs(diff) < 0.01:
                 st.write(f"It's a dead heat! 🍺")
            elif diff > 0:
                st.write(f"Need to hit: **${data['match_price']:.2f}** (Up ${diff:.2f})")
            else:
                st.write(f"Already beating {data['other_ticker']}! (Equivalent: ${data['match_price']:.2f})")
            
            st.write("---")

            # Projection
            projected_val = get_projection(data['history'], TARGET_DATE)
            proj_gain_pct = ((projected_val - data['start_price']) / data['start_price']) * 100
            
            st.info(f"🔮 **2026 Projection**")
            st.write(f"Est. Value: **${projected_val:.2f}**")
            st.write(f"Est. Gain: **{proj_gain_pct:.1f}%**")

    # --- DAILY BATTLE SUMMARY ---
    st.write("---")
    st.subheader("⚔️ Today's Battle Report")
    
    daily_diff = stock_a['daily_change_pct'] - stock_b['daily_change_pct']
    
    if abs(daily_diff) < 0.01:
        st.write("It was a draw today! Both stocks moved roughly the same amount.")
    elif daily_diff > 0:
        st.success(f"**{stock_a['ticker']}** won today! It gained **{daily_diff:.2f}%** on {stock_b['ticker']}.")
    else:
        st.success(f"**{stock_b['ticker']}** won today! It gained **{abs(daily_diff):.2f}%** on {stock_a['ticker']}.")

else:
    st.warning("Could not load data for both stocks to perform comparison.")

st.write("---")
st.caption("Disclaimer: Projections are based on a linear regression of the last 2 years. Not financial advice.")

if st.button("Force Refresh Data"):
    st.cache_data.clear()
    st.rerun()
