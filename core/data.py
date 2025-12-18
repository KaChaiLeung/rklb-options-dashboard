from __future__ import annotations

from dataclasses import dataclass
import pandas as pd
import yfinance as yf


# class for a ticker
@dataclass(frozen=True) # Immutable
class OptionChain:
    ticker: str
    spot: float # Current price
    expiries: list[str] # List of contract expiry dates
    calls: pd.DataFrame # Table from yfinance
    puts: pd.DataFrame # Table from yfinance


def _get_spot(t: yf.Ticker) -> float:
    """
    Try to get the latest spot price. If fast_info isn't available, fall back to recent historical close.
    """
    try:
        spot = t.fast_info.get("last_price") # Get the most recent price — can fail or be missing
        if spot is not None:
            return float(spot)
    except Exception:
        pass

    # If failed, use t.history() to get most recent closing price
    hist = t.history(period="5d", interval="1d")
    if hist.empty:
        raise RuntimeError("Could not fetch spot price history.")
    return float(hist["Close"].iloc[-1])


def fetch_option_chain(ticker: str, expiry: str | None = None) -> OptionChain:
    """
    Fetch options chain + spot for a ticker.
    If expiry is None, uses the first available expiry.
    """
    t = yf.Ticker(ticker) # Object for stock
    
    expiries = list(t.options or []) # List of available expiration dates YYYY-MM-DD
    if not expiries:
        raise RuntimeError(f"No options expiries found for {ticker}")
    
    chosen_expiry = expiry or expiries[0]
    if chosen_expiry not in expiries:
        raise ValueError(
            f"Expiry {chosen_expiry} not in available expiries (showing first 5): {expiries[:5]}"
        )
    
    opt = t.option_chain(chosen_expiry) # Returns 2 dataframes: calls and puts
    spot = _get_spot(t) # Underlying spot price

    calls = opt.calls.copy()
    puts = opt.puts.copy()

    # Adding columns "expiry" and "type"
    calls["expiry"] = chosen_expiry
    puts["expiry"] = chosen_expiry
    calls["type"] = "call"
    puts["type"] = "put"

    return OptionChain(
        ticker=ticker.upper(),
        spot=spot,
        expiries=expiries,
        calls=calls,
        puts=puts,
    )


def add_mid_and_moneyness(df: pd.DataFrame, spot: float) -> pd.DataFrame:
    """
    Add:
    - mid: (bid + ask) / 2 with fallback to lastPrice if bid/ask is missing
    - moneyness: strike / spot
    """
    out = df.copy()

    out["mid"] = (out["bid"].fillna(0.0) + out["ask"].fillna(0.0)) / 2.0

    if "lastPrice" in out.columns:
        out["mid"] = out["mid"].where(out["mid"] > 0.0, out["lastPrice"].fillna(0.0))

    out["moneyness"] = out["strike"].astype(float) / float(spot)
    return out