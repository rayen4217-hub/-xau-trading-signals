import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(
    page_title="XAU/USD Trading Signals",
    page_icon="🟡",
    layout="centered"
)

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
    st.error("❌ لم يتم الحصول على بيانات الذهب.")
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
data["MACD_SIGNAL"] = data["MACD"].ewm(
    span=9,
    adjust=False
).mean()

# آخر شمعة
last = data.iloc[-1]

price = float(last["Close"])
ema20 = float(last["EMA20"])
ema50 = float(last["EMA50"])
rsi = float(last["RSI"])
macd = float(last["MACD"])
macd_signal = float(last["MACD_SIGNAL"])


# =========================
# SIGNAL ENGINE
# =========================

score = 0
reasons = []

# EMA
if ema20 > ema50:
    score += 1
    reasons.append("EMA Bullish")
elif ema20 < ema50:
    score -= 1
    reasons.append("EMA Bearish")

# RSI
if 50 < rsi < 70:
    score += 1
    reasons.append("RSI Bullish")
elif 30 < rsi < 50:
    score -= 1
    reasons.append("RSI Bearish")

# MACD
if macd > macd_signal:
    score += 1
    reasons.append("MACD Bullish")
elif macd < macd_signal:
    score -= 1
    reasons.append("MACD Bearish")


# =========================
# AVOID LATE ENTRIES
# =========================

# تشبع بيعي قوي
if rsi < 20:
    score = min(score, 0)
    reasons.append("RSI Oversold - Avoid Late SELL")

# تشبع شرائي قوي
if rsi > 80:
    score = max(score, 0)
    reasons.append("RSI Overbought - Avoid Late BUY")


# =========================
# SIGNAL
# =========================

if score >= 2:
    signal = "🟢 BUY"
    direction = "BUY"

elif score <= -2:
    signal = "🔴 SELL"
    direction = "SELL"

else:
    signal = "⚪ WAIT"
    direction = "WAIT"


# =========================
# STRENGTH
# =========================

strength = min(abs(score) / 3 * 100, 100)

# =========================
# RISK MANAGEMENT
# =========================

risk_distance = price * 0.0025

if direction == "BUY":

    entry = price
    stop_loss = price - risk_distance

    tp1 = price + risk_distance * 1.5
    tp2 = price + risk_distance * 2.5

elif direction == "SELL":

    entry = price
    stop_loss = price + risk_distance

    tp1 = price - risk_distance * 1.5
    tp2 = price - risk_distance * 2.5

else:

    entry = price
    stop_loss = None
    tp1 = None
    tp2 = None


# =========================
# DISPLAY
# =========================

st.subheader(signal)

st.metric(
    "Signal Strength",
    f"{strength:.0f}%"
)

col1, col2 = st.columns(2)

with col1:

    st.metric(
        "Gold Price",
        f"{price:.2f}"
    )

    st.metric(
        "EMA 20",
        f"{ema20:.2f}"
    )

    st.metric(
        "EMA 50",
        f"{ema50:.2f}"
    )

with col2:

    st.metric(
        "RSI",
        f"{rsi:.2f}"
    )

    st.metric(
        "MACD",
        f"{macd:.2f}"
    )

    st.metric(
        "MACD Signal",
        f"{macd_signal:.2f}"
    )


# =========================
# TRADE LEVELS
# =========================

if direction != "WAIT":

    st.divider()

    st.subheader("🎯 Trade Levels")

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Entry",
            f"{entry:.2f}"
        )

        st.metric(
            "Stop Loss",
            f"{stop_loss:.2f}"
        )

    with col2:

        st.metric(
            "TP1",
            f"{tp1:.2f}"
        )

        st.metric(
            "TP2",
            f"{tp2:.2f}"
        )


# =========================
# ANALYSIS
# =========================

st.divider()

st.subheader("🔎 Analysis")

for reason in reasons:
    st.write("•", reason)


# =========================
# DATA
# =========================

st.divider()

st.subheader("📊 Last 20 Candles")

st.dataframe(
    data[
        [
            "Close",
            "EMA20",
            "EMA50",
            "RSI",
            "MACD",
            "MACD_SIGNAL"
        ]
    ].tail(20),
    use_container_width=True
)


if st.button("🔄 Refresh"):

    st.cache_data.clear()
    st.rerun()


st.caption(
    "⚠️ أداة تحليلية تعليمية. الإشارات ليست ضماناً للربح ولا تنفذ الصفقات تلقائياً."
)
