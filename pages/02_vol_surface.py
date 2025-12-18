import numpy as np
import pandas as pd
import streamlit as st

from core.data import fetch_option_chain, add_mid_and_moneyness
from core.greeks import add_iv_and_greeks


st.set_page_config(page_title="Vol Surface", layout="wide")
TICKER = "RKLB"

@st.cache_data(ttl=60 * 10)
def load_chain(ticker: str, expiry: str | None):
    return fetch_option_chain(ticker, expiry)

st.title("Vol Surface / Skew")
st.caption("Implied volatility by strike (skew/smile) and by expiry (term structure).")

base = load_chain(TICKER, None)

# Choose parameters for plots
c1, c2, c3 = st.columns([2, 1, 1])
expiry = c1.selectbox("Expiry (for skew plot)", base.expiries, index=0)
side = c2.radio("Side", ["Calls", "Puts"], horizontal=True)
x_axis = c3.selectbox("X-axis", ["Strike", "Moneyness (K/S)"], index=1)

# Get spot price
chain = load_chain(TICKER, expiry)
spot = chain.spot
st.metric(f"Spot ({TICKER})", f"{spot:.2f}")

# Choose which column to treat as "option price" when solving implied volatility
price_source = st.selectbox("Price source for IV solve", ["mid", "bid", "ask", "lastPrice"], index=0)

# Adding mid and moneyness columns
df = chain.calls if side == "Calls" else chain.puts
df = add_mid_and_moneyness(df, spot)

# Filters
with st.expander("Filters", expanded=True):
    f1, f2, f3, f4 = st.columns(4)
    min_oi = f1.number_input("Min OI", min_value=0, value=50, step=10)
    min_vol = f2.number_input("Min Volume", min_value=0, value=10, step=10)
    m_low = f3.number_input("Moneyness min", value=0.7)
    m_high = f4.number_input("Moneyness max", value=1.3)

# Applying filters and cleaning
df["openInterest"] = df["openInterest"].fillna(0)
df["volume"] = df["volume"].fillna(0)
df = df[(df["openInterest"] >= min_oi) & (df["volume"] >= min_vol)]
df = df[(df["moneyness"] >= m_low) & (df["moneyness"] <= m_high)]
df = df[(df["bid"].fillna(0) > 0) & (df["ask"].fillna(0) > 0)]
df = df[(df[price_source].fillna(0) > 0)]
df = df.sort_values("strike")

# Compute IV and greeks for each row
# Greeks not necessary
opt_type = "call" if side == "Calls" else "put"
df = add_iv_and_greeks(df, spot=spot, expiry=expiry, option_type=opt_type, price_col=price_source)

# Fallback toggle if solving fails — use provider IV
use_fallback = st.checkbox("Fallback to provider impliedVolatility when IV solve fails", value=True)

iv_series = df["iv"]
if use_fallback and "impliedVolatility" in df.columns:
    iv_series = iv_series.fillna(df["impliedVolatility"])

# Prepare plotting dataframe for skew
plot_df = pd.DataFrame(
    {
        "strike": df["strike"].astype(float),
        "moneyness": df["moneyness"].astype(float),
        "iv": iv_series.astype(float),
    }
).dropna()

# Skew plot
st.subheader("Skew (Smile): IV vs Strike/Moneyness")
if plot_df.empty:
    st.warning("No data points after filtering. Loosen filters or change expiry.")
else:
    x = "moneyness" if x_axis.startswith("Moneyness") else "strike"
    plot_df = plot_df.sort_values(x)
    st.line_chart(plot_df.set_index(x)["iv"])

# Choose how many expiries to loop through
st.subheader("Term Structure: ATM IV vs Expiry")
max_expiries = st.slider("Number of expiries to scan", 3, min(20, len(base.expiries)), 10)

# Term structure loop
rows = []
for exp in base.expiries[:max_expiries]:
    ch = load_chain(TICKER, exp)
    S = ch.spot
    d = ch.calls if side == "Calls" else ch.puts
    d = add_mid_and_moneyness(d, S)

    # Filter bad quotes
    d = d[(d["bid"].fillna(0) > 0) & (d["ask"].fillna(0) > 0)]
    if d.empty:
        continue

    # Choose option with strike closest to spot (ATM)
    d["dist"] = (d["strike"].astype(float) - S).abs()
    atm_row = d.sort_values("dist").head(1).copy()

    # Compute IV for that row & fallback if needed
    atm_row = add_iv_and_greeks(atm_row, spot=S, expiry=exp, option_type=opt_type, price_col=price_source)
    atm_iv = float(atm_row["iv"].iloc[0]) if "iv" in atm_row.columns else np.nan

    if (not np.isfinite(atm_iv)) and ("impliedVolatility" in atm_row.columns) and use_fallback:
        atm_iv = float(atm_row["impliedVolatility"].iloc[0])
    
    rows.append({"expiry": exp, "atm_iv": atm_iv})

# Plot term structure
term = pd.DataFrame(rows).dropna()
if term.empty:
    st.warning("Couldn't compute term structure with current settings.")
else:
    st.line_chart(term.set_index("expiry")["atm_iv"])