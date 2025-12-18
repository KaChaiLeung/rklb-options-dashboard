import pandas as pd
import pytest

from core.data import add_mid_and_moneyness


def test_mid_uses_bid_ask_when_present():
    """
    Test that bid/ask exist and used to compute mid.
    """
    spot = 10.0
    df = pd.DataFrame({
        "strike": [8.0, 10.0],
        "bid": [1.0, 0.4],
        "ask": [1.2, 0.6],
        "lastPrice": [9.9, 9.9],
    })

    out = add_mid_and_moneyness(df, spot)

    assert out.loc[0, "mid"] == pytest.approx((1.0 + 1.2) / 2)
    assert out.loc[1, "mid"] == pytest.approx((0.4 + 0.6) / 2)


def test_mid_falls_back_to_lastPrice_when_bid_ask_missing_or_zero():
    """
    Test if bid/ask missing or zero then mid falls back to lastPrice.
    """
    spot = 10.0
    df = pd.DataFrame({
        "strike": [10.0, 11.0],
        "bid": [0.0, None],
        "ask": [0.0, None],
        "lastPrice": [0.55, 0.25],
    })

    out = add_mid_and_moneyness(df, spot)

    assert out.loc[0, "mid"] == pytest.approx(0.55)
    assert out.loc[1, "mid"] == pytest.approx(0.25)


def test_moneyness_is_strike_over_spot():
    """
    Test moneyness formula.
    """
    spot = 20.0
    df = pd.DataFrame({
        "strike": [10.0, 25.0],
        "bid": [1.0, 1.0],
        "ask": [1.0, 1.0]
    })

    out = add_mid_and_moneyness(df, spot)

    assert out.loc[0, "moneyness"] == pytest.approx(10.0 / 20.0)
    assert out.loc[1, "moneyness"] == pytest.approx(25.0 / 20.0)