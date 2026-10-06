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
        df = yf.Ticker(ticker).history(period=period)
        return df.dropna(subset=["Close"])  # drop empty rows that cause "nan"
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


@st.cache_data(ttl=86400)
def get_fundamentals():
    """Load historical fundamentals from CSV (cached for 24 hours)."""
    try:
        return pd.read_csv("https://raw.githubusercontent.com/darshdhingra40-hash/lufthansa-dashboard/main/lufthansa_fundamentals.csv")
    except Exception:
        return pd.DataFrame()


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
pe = info.get("trailingPE")
if pe is None and market_cap:
    # Fallback when Yahoo blocks us: market cap / latest net income from CSV
    _f = get_fundamentals()
    if not _f.empty and _f["net_income_eur_m"].iloc[-1] > 0:
        pe = market_cap / (_f["net_income_eur_m"].iloc[-1] * 1e6)
col3.metric("P/E Ratio", fmt(pe, "{:.1f}x"))
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

# ---------- Historical Fundamentals (from CSV) ----------
st.subheader("5-Year Financial Fundamentals")
fundamentals = get_fundamentals()

if not fundamentals.empty:
    # Revenue & EBIT trend
    fig_fin = go.Figure()
    fig_fin.add_trace(go.Scatter(
        x=fundamentals["year"], y=fundamentals["revenue_eur_m"], mode="lines+markers",
        name="Revenue", line=dict(color="#1f77b4", width=2),
    ))
    fig_fin.add_trace(go.Scatter(
        x=fundamentals["year"], y=fundamentals["adj_ebit_eur_m"], mode="lines+markers",
        name="Adjusted EBIT", line=dict(color="#ff7f0e", width=2),
    ))
    fig_fin.update_layout(hovermode="x unified", height=350, yaxis_title="EUR millions",
                          xaxis_title="Year", template="plotly_white")
    fig_fin.update_xaxes(type="category")  # show 2021, 2022... not 2021.5
    st.plotly_chart(fig_fin, use_container_width=True)

    # Key fundamentals table
    st.write("**Financial Metrics Summary (2021–2025)**")
    display_cols = ["year", "revenue_eur_m", "adj_ebitda_eur_m", "adj_ebit_eur_m",
                    "net_income_eur_m", "passengers_m", "passenger_load_factor_pct"]
    display_df = fundamentals[display_cols].copy()
    display_df.columns = ["Year", "Revenue (€M)", "Adj EBITDA (€M)", "Adj EBIT (€M)",
                          "Net Income (€M)", "Passengers (M)", "Load Factor (%)"]

    # Format numbers
    for col in display_df.columns[1:]:
        if "Load Factor" in col:
            display_df[col] = display_df[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
        elif "Passengers" in col:
            display_df[col] = display_df[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
        else:
            display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "N/A")

    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.warning("Could not load historical fundamentals from CSV.")

# ---------- Ratios ----------
st.subheader("Key Financial Ratios")
r1, r2, r3 = st.columns(3)
_f = get_fundamentals()
if not _f.empty:
    last = _f.iloc[-1]
    r1.metric("Net Debt / Adj EBITDA (2025)", fmt(last["net_debt_eur_m"] / last["adj_ebitda_eur_m"], "{:.1f}x"))
    r2.metric("Adj EBIT Margin (2025)", fmt(last["adj_ebit_eur_m"] / last["revenue_eur_m"] * 100, "{:.1f}%"))
    r3.metric("Net Income Margin (2025)", fmt(last["net_income_eur_m"] / last["revenue_eur_m"] * 100, "{:.1f}%"))
else:
    st.warning("Ratios unavailable.")

st.write("---")
st.caption(f"Data source: Yahoo Finance | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
