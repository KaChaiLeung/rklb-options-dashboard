import streamlit as st

from core.data import fetch_option_chain, add_mid_and_moneyness
from core.greeks import add_iv_and_greeks


st.set_page_config(page_title="Chain Explorer", layout="wide")

TICKER = "RKLB"


@st.cache_data(ttl=60 * 10)
def load_chain(ticker: str, expiry: str | None):
    return fetch_option_chain(ticker, expiry)


st.title("Chain Explorer")
st.caption(f"Browse {TICKER} option chains. Mid price and moneyness are computed locally.")

# Load to get expiries
base = load_chain(TICKER, None)

expiry = st.selectbox("Expiry", options=base.expiries, index=0)
side = st.radio("Side", ["Calls", "Puts"], horizontal=True)

chain = load_chain(TICKER, expiry)
spot = chain.spot
st.metric(f"Spot ({TICKER})", f"{spot:.2f}")

df = chain.calls if side == "Calls" else chain.puts
df = add_mid_and_moneyness(df, spot)

with st.expander("Filters", expanded=True):
    c1, c2, c3, c4 = st.columns(4)
    min_oi = c1.number_input("Min Open Interest", min_value=0, value=0, step=10)
    min_vol = c2.number_input("Min Volume", min_value=0, value=0, step=10)
    m_low = c3.number_input("Moneyness min (K/S)", value=0.5)
    m_high = c4.number_input("Moneyness max (K/S)", value=1.5)

f = df.copy()
f["openInterest"] = f["openInterest"].fillna(0)
f["volume"] = f["volume"].fillna(0)

f = f[(f["openInterest"] >= min_oi) & (f["volume"] >= min_vol)]
f = f[(f["moneyness"] >= m_low) & (f["moneyness"] <= m_high)]
f = f.sort_values("strike")


compute = st.checkbox("Compute IV + Greeks (slower)", value=False)
if compute:
    opt_type = "call" if side == "Calls" else "put"
    f = add_iv_and_greeks(
        f,
        spot=spot,
        expiry=expiry,
        option_type=opt_type,
        r=0.045,
        q=0.0,
        price_col="mid"
    )

preferred_cols = [
    "contractSymbol", "expiry", "type", "strike", "bid", "ask", "mid", "lastPrice", "impliedVolatility", "moneyness",
]

if compute:
    preferred_cols += ["iv", "delta", "gamma", "vega", "theta"]

cols = [c for c in preferred_cols if c in f.columns]

st.dataframe(f[cols], use_container_width=True, height=560)