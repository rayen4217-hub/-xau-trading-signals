import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="XAU/USD Signals", page_icon="🟡")

st.title("🟡 XAU/USD Trading Signals")
st.caption("15 Minute • EMA 20/50 • RSI • MACD")

@st.cache_data(ttl=60)
def get_data():
    data = yf.download(
        "GC=F",
        period="5d",
        interval="15m",
        auto_adjust=False,
        progress=False
    )

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    return data.dropna()

data = get_data()

if data.empty:
    st.error("لم يتم الحصول على بيانات الذهب.")
    st.stop()

close = data["Close"]

# EMA
data["EMA20"] = close.ewm(span=20, adjust=False).mean()
data["EMA50"] = close.ewm(span=50, adjust=False).mean()

# RSI
delta = close.diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)

avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()

rs = avg_gain / avg_loss
data["RSI"] = 100 - (100 / (1 + rs))

# MACD
ema12 = close.ewm(span=12, adjust=False).mean()
ema26 = close.ewm(span=26, adjust=False).mean()

data["MACD"] = ema12 - ema26
data["Signal"] = data["MACD"].ewm(span=9, adjust=False).mean()

last = data.iloc[-1]

price = float(last["Close"])
ema20 = float(last["EMA20"])
ema50 = float(last["EMA50"])
rsi = float(last["RSI"])
macd = float(last["MACD"])
signal = float(last["Signal"])

buy_conditions = (
    ema20 > ema50 and
    rsi > 50 and
    macd > signal
)

sell_conditions = (
    ema20 < ema50 and
    rsi < 50 and
    macd < signal
)

if buy_conditions:
    result = "🟢 BUY"
elif sell_conditions:
    result = "🔴 SELL"
else:
    result = "⚪ WAIT"

st.subheader(result)

col1, col2 = st.columns(2)

with col1:
    st.metric("Gold Price", f"{price:.2f}")
    st.metric("EMA 20", f"{ema20:.2f}")
    st.metric("EMA 50", f"{ema50:.2f}")

with col2:
    st.metric("RSI", f"{rsi:.2f}")
    st.metric("MACD", f"{macd:.2f}")
    st.metric("MACD Signal", f"{signal:.2f}")

st.divider()

st.write("### آخر البيانات")
st.dataframe(
    data[["Close", "EMA20", "EMA50", "RSI", "MACD", "Signal"]].tail(20),
    use_container_width=True
)

st.caption(
    "هذه إشارة تحليلية وليست ضماناً للربح. لا يتم تنفيذ أي صفقة تلقائياً."
)

if st.button("🔄 تحديث البيانات"):
    st.cache_data.clear()
    st.rerun()
