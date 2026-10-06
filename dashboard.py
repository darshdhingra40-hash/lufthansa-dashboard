import yfinance as yf
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Lufthansa Financial Analysis", layout="wide")


# ---------- Data loading (cached for 1 hour so we don't get rate-limited) ----------
@st.cache_data(ttl=3600)
def get_history(ticker, period):
    try:
        return yf.Ticker(ticker).history(period=period)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def get_info(ticker):
    try:
        return yf.Ticker(ticker).info or {}
    except Exception:
        return {}


@st.cache_data(ttl=3600)
def get_market_cap(ticker):
    try:
        return yf.Ticker(ticker).fast_info["market_cap"]
    except Exception:
        return None


def fmt(value, pattern, fallback="N/A"):
    """Format a number safely. Returns 'N/A' instead of crashing on missing data."""
    try:
        if value is None:
            return fallback
        return pattern.format(float(value))
    except (TypeError, ValueError):
        return fallback


# ---------- Header ----------
st.title("Lufthansa Financial & Valuation Dashboard")
st.write("Financial analysis of Deutsche Lufthansa AG (LHA.DE)")

history = get_history("LHA.DE", "5y")
info = get_info("LHA.DE")

if history.empty:
    st.error("Could not load price data from Yahoo Finance. Try again in a few minutes.")
    st.stop()

last_year = history.tail(252)  # ~252 trading days in a year

market_cap = info.get("marketCap") or get_market_cap("LHA.DE")

div_yield = info.get("dividendYield")
if div_yield is not None and div_yield < 1:  # some yfinance versions return 0.025 instead of 2.5
    div_yield = div_yield * 100

# ---------- Key metrics ----------
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Stock Price", fmt(history["Close"].iloc[-1], "€{:.2f}"))
col2.metric("Market Cap", fmt(market_cap / 1e9 if market_cap else None, "€{:.1f}B"))
col3.metric("P/E Ratio", fmt(info.get("trailingPE"), "{:.1f}x"))
col4.metric("Dividend Yield", fmt(div_yield, "{:.2f}%"))
col5.metric("52W High", fmt(last_year["Close"].max(), "€{:.2f}"))

if not info:
    st.caption("Some fundamentals are temporarily unavailable (Yahoo Finance rate limit). Price data is live.")

# ---------- Stock price trend ----------
st.subheader("Stock Price Trend (5 Years)")
fig_price = go.Figure()
fig_price.add_trace(go.Scatter(
    x=history.index, y=history["Close"], mode="lines", name="Price",
    line=dict(color="#1f77b4", width=2),
))
fig_price.update_layout(hovermode="x unified", height=400,
                        yaxis_title="Price (EUR)", xaxis_title="Date", template="plotly_white")
st.plotly_chart(fig_price, use_container_width=True)

# ---------- Volume ----------
st.subheader("Trading Volume (Last 12 Months)")
fig_vol = go.Figure()
fig_vol.add_trace(go.Bar(x=last_year.index, y=last_year["Volume"], marker_color="#ff7f0e"))
fig_vol.update_layout(height=300, hovermode="x unified", template="plotly_white")
st.plotly_chart(fig_vol, use_container_width=True)

# ---------- Competitors ----------
st.subheader("vs Competitors (1-Year Return)")
competitors = {"Lufthansa": "LHA.DE", "Ryanair": "RYA.IR", "Air France-KLM": "AF.PA"}
returns = {}
for name, ticker in competitors.items():
    prices = get_history(ticker, "1y")
    if not prices.empty:
        returns[name] = (prices["Close"].iloc[-1] / prices["Close"].iloc[0] - 1) * 100

if returns:
    fig_comp = go.Figure()
    fig_comp.add_trace(go.Bar(
        x=list(returns.keys()), y=list(returns.values()),
        marker_color=["#2ca02c" if r >= 0 else "#d62728" for r in returns.values()],
        text=[f"{r:.1f}%" for r in returns.values()], textposition="outside",
    ))
    fig_comp.update_layout(yaxis_title="Return (%)", height=350, template="plotly_white")
    st.plotly_chart(fig_comp, use_container_width=True)

# ---------- Ratios ----------
st.subheader("Key Financial Ratios")
r1, r2, r3 = st.columns(3)
r1.metric("EPS (TTM)", fmt(info.get("trailingEps"), "€{:.2f}"))
roe = info.get("returnOnEquity")
r2.metric("Return on Equity", fmt(roe * 100 if roe is not None else None, "{:.1f}%"))
r3.metric("Debt-to-Equity", fmt(info.get("debtToEquity"), "{:.1f}"))

st.write("---")
st.caption(f"Data source: Yahoo Finance | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
