import yfinance as yf
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Lufthansa Financial Analysis", layout="wide")
st.title("Lufthansa Financial & Valuation Dashboard")
st.write("Real-time financial analysis of Deutsche Lufthansa AG (LHA.DE)")

# Fetch data
lh = yf.Ticker("LHA.DE")
history = lh.history(period="5y")
info = lh.info

# Key metrics
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Stock Price", f"€{history['Close'].iloc[-1]:.2f}")
with col2:
    st.metric("Market Cap", f"€{info.get('marketCap', 0)/1e9:.1f}B")
with col3:
    st.metric("P/E Ratio", f"{info.get('trailingPE', 'N/A'):.1f}x")
with col4:
    st.metric("Dividend Yield", f"{info.get('dividendYield', 0)*100:.2f}%")
with col5:
    st.metric("52W High", f"€{history['Close'].max():.2f}")

# Stock price trend
st.subheader("Stock Price Trend (5 Years)")
fig_price = go.Figure()
fig_price.add_trace(go.Scatter(
    x=history.index, 
    y=history['Close'], 
    mode='lines', 
    name='Price',
    line=dict(color='#1f77b4', width=2)
))
fig_price.update_layout(
    hovermode='x unified',
    height=400,
    yaxis_title='Price (EUR)',
    xaxis_title='Date',
    template='plotly_white'
)
st.plotly_chart(fig_price, use_container_width=True)

# Volume analysis
st.subheader("Trading Volume")
fig_vol = go.Figure()
fig_vol.add_trace(go.Bar(
    x=history.index[-252:],
    y=history['Volume'][-252:],
    name='Volume',
    marker_color='#ff7f0e'
))
fig_vol.update_layout(height=300, hovermode='x unified', template='plotly_white')
st.plotly_chart(fig_vol, use_container_width=True)

# Competitor comparison
st.subheader("vs Competitors (1 Year Performance)")
competitors = {"Lufthansa": "LHA.DE", "Ryanair": "RYA.IR", "Air France-KLM": "AFRAF"}
comp_data = {}
for name, ticker in competitors.items():
    try:
        price_data = yf.Ticker(ticker).history(period="1y")['Close']
        comp_data[name] = ((price_data.iloc[-1] / price_data.iloc[0]) - 1) * 100
    except:
        pass

if comp_data:
    fig_comp = go.Figure()
    fig_comp.add_trace(go.Bar(x=list(comp_data.keys()), y=list(comp_data.values()), marker_color='#2ca02c'))
    fig_comp.update_layout(
        title="1-Year Return Comparison",
        yaxis_title='Return (%)',
        height=350,
        template='plotly_white'
    )
    st.plotly_chart(fig_comp, use_container_width=True)

# Financial ratios
st.subheader("Key Financial Ratios")
col1, col2, col3 = st.columns(3)
with col1:
    st.write(f"**EPS:** €{info.get('trailingEps', 'N/A'):.2f}")
with col2:
    st.write(f"**ROE:** {info.get('returnOnEquity', 'N/A')}")
with col3:
    st.write(f"**Debt-to-Equity:** {info.get('debtToEquity', 'N/A'):.2f}")

st.write("---")
st.write("*Data source: Yahoo Finance | Last updated: {}*".format(datetime.now().strftime("%Y-%m-%d %H:%M")))
