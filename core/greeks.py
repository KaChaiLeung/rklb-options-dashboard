from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import numpy as np
import pandas as pd

from py_vollib.black_scholes_merton.implied_volatility import implied_volatility
from py_vollib.black_scholes_merton.greeks.analytical import delta, gamma, vega, theta


def _time_to_expiry_years(expiry: str) -> float:
    """
    Convert an expiry into time-to-expiry in years.
    Uses UTC.
    """
    exp_dt = datetime.strptime(expiry, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    seconds = (exp_dt - now).total_seconds()
    return max(seconds, 0.0) / (365.0 * 24.0 * 3600.0)


def add_iv_and_greeks(df: pd.DataFrame, 
                      spot: float, 
                      expiry: str, 
                      option_type: Literal["call", "put"],
                      r: float = 0.045,
                      q: float = 0.0,
                      price_col: str = "mid",) -> pd.DataFrame:
    """
    Adds columns:
        iv, delta, gamma, vega, theta

    Assumptions:
        - Black-Scholes-Merton with constant r and q
        - Uses "price_col" as the option price
    """
    out = df.copy()

    T = _time_to_expiry_years(expiry)
    if T <= 0:
        # Expired so greeks/iv not meaningful
        out["iv"] = np.nan
        out["delta"] = np.nan
        out["gamma"] = np.nan
        out["vega"] = np.nan
        out["theta"] = np.nan
        return out
    
    flag = "c" if option_type == "call" else "p"

    # Ensure numeric arrays
    K = out["strike"].astype(float).to_numpy()
    price = out[price_col].astype(float).fillna(0.0).to_numpy()

    ivs = np.full(len(out), np.nan, dtype=float)
    deltas = np.full(len(out), np.nan, dtype=float)
    gammas = np.full(len(out), np.nan, dtype=float)
    vegas = np.full(len(out), np.nan, dtype=float)
    thetas = np.full(len(out), np.nan, dtype=float)

    for i in range(len(out)):
        if spot <= 0 or K[i] <= 0 or price[i] <= 0:
            continue

        try:
            sigma = implied_volatility(price[i], spot, K[i], T, r, q, flag)
            if not np.isfinite(sigma) or sigma <= 0:
                continue

            ivs[i] = sigma
            deltas[i] = delta(flag, spot, K[i], T, r, sigma, q)
            gammas[i] = gamma(flag, spot, K[i], T, r, sigma, q)
            vegas[i] = vega(flag, spot, K[i], T, r, sigma, q)
            thetas[i] = theta(flag, spot, K[i], T, r, sigma, q)
        except Exception:
            continue
    
    out["iv"] = ivs
    out["delta"] = deltas
    out["gamma"] = gammas
    out["vega"] = vegas
    out["theta"] = thetas
    return out