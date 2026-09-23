import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(
    page_title="XAU/USD Signal Engine",
    page_icon="🟡"
)

st.title("🟡 XAU/USD Signal Engine")
st.caption("15M • EMA • RSI • MACD • ATR")

@st.cache_data(ttl=60)
def get_data():
    df = yf.download(
        "GC=F",
        period="10d",
        interval="15m",
        auto_adjust=False,
        progress=False
    )

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    return df.dropna()


df = get_data()

if df.empty:
    st.error("No gold data available.")
    st.stop()

close = df["Close"]
high = df["High"]
low = df["Low"]

# =========================
# EMA
# =========================

df["EMA20"] = close.ewm(span=20, adjust=False).mean()
df["EMA50"] = close.ewm(span=50, adjust=False).mean()

# =========================
# RSI
# =========================

delta = close.diff()

gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)

avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()

rs = avg_gain / avg_loss

df["RSI"] = 100 - (100 / (1 + rs))

# =========================
# MACD
# =========================

ema12 = close.ewm(span=12, adjust=False).mean()
ema26 = close.ewm(span=26, adjust=False).mean()

df["MACD"] = ema12 - ema26
df["MACD_SIGNAL"] = df["MACD"].ewm(
    span=9,
    adjust=False
).mean()

# =========================
# ATR
# =========================

previous_close = close.shift(1)

tr1 = high - low
tr2 = (high - previous_close).abs()
tr3 = (low - previous_close).abs()

true_range = pd.concat(
    [tr1, tr2, tr3],
    axis=1
).max(axis=1)

df["ATR"] = true_range.rolling(14).mean()

# =========================
# LAST CANDLE
# =========================

last = df.iloc[-1]

price = float(last["Close"])
ema20 = float(last["EMA20"])
ema50 = float(last["EMA50"])
rsi = float(last["RSI"])
macd = float(last["MACD"])
macd_signal = float(last["MACD_SIGNAL"])
atr = float(last["ATR"])

# =========================
# SIGNAL ENGINE
# =========================

buy_score = 0
sell_score = 0

buy_reasons = []
sell_reasons = []

# EMA trend
if ema20 > ema50:
    buy_score += 1
    buy_reasons.append("EMA20 > EMA50")

elif ema20 < ema50:
    sell_score += 1
    sell_reasons.append("EMA20 < EMA50")

# MACD
if macd > macd_signal:
    buy_score += 1
    buy_reasons.append("MACD bullish")

elif macd < macd_signal:
    sell_score += 1
    sell_reasons.append("MACD bearish")

# RSI
if 50 <= rsi <= 70:
    buy_score += 1
    buy_reasons.append("RSI bullish zone")

elif 30 <= rsi < 50:
    sell_score += 1
    sell_reasons.append("RSI bearish zone")

# =========================
# EXTREME RSI FILTER
# =========================

if rsi < 20:
    sell_score = 0
    sell_reasons = []
    sell_blocked = True

elif rsi > 80:
    buy_score = 0
    buy_reasons = []
    buy_blocked = True

else:
    sell_blocked = False
    buy_blocked = False

# =========================
# FINAL SIGNAL
# =========================

if buy_score >= 2 and not buy_blocked:
    signal = "🟢 BUY"
    direction = "BUY"
    strength = (buy_score / 3) * 100
    reasons = buy_reasons

elif sell_score >= 2 and not sell_blocked:
    signal = "🔴 SELL"
    direction = "SELL"
    strength = (sell_score / 3) * 100
    reasons = sell_reasons

else:
    signal = "⚪ WAIT"
    direction = "WAIT"
    strength = 0
    reasons = ["No clean confirmation"]

# =========================
# ENTRY / SL / TP
# =========================

if direction == "BUY":

    entry = price
    sl = price - (atr * 1.5)

    tp1 = price + (atr * 1.5)
    tp2 = price + (atr * 2.5)
    tp3 = price + (atr * 3.5)

elif direction == "SELL":

    entry = price
    sl = price + (atr * 1.5)

    tp1 = price - (atr * 1.5)
    tp2 = price - (atr * 2.5)
    tp3 = price - (atr * 3.5)

else:

    entry = price
    sl = None
    tp1 = None
    tp2 = None
    tp3 = None

# =========================
# DISPLAY
# =========================

st.subheader(signal)

st.metric(
    "Signal Strength",
    f"{strength:.0f}%"
)

c1, c2 = st.columns(2)

with c1:
    st.metric("Gold", f"{price:.2f}")
    st.metric("EMA20", f"{ema20:.2f}")
    st.metric("EMA50", f"{ema50:.2f}")

with c2:
    st.metric("RSI", f"{rsi:.2f}")
    st.metric("MACD", f"{macd:.2f}")
    st.metric("ATR", f"{atr:.2f}")

# =========================
# TRADE PLAN
# =========================

if direction != "WAIT":

    st.divider()

    st.subheader("🎯 Trade Plan")

    c1, c2 = st.columns(2)

    with c1:
        st.metric("Entry", f"{entry:.2f}")
        st.metric("Stop Loss", f"{sl:.2f}")

    with c2:
        st.metric("TP1", f"{tp1:.2f}")
        st.metric("TP2", f"{tp2:.2f}")

    st.metric("TP3", f"{tp3:.2f}")

# =========================
# ANALYSIS
# =========================

st.divider()

st.subheader("🔎 Confirmation")

for reason in reasons:
    st.write("•", reason)

# =========================
# LAST DATA
# =========================

st.divider()

st.subheader("📊 Market Data")

st.dataframe(
    df[
        [
            "Close",
            "EMA20",
            "EMA50",
            "RSI",
            "MACD",
            "MACD_SIGNAL",
            "ATR"
        ]
    ].tail(20),
    use_container_width=True
)

if st.button("🔄 Refresh"):

    st.cache_data.clear()
    st.rerun()

st.caption(
    "⚠️ Educational technical-analysis tool. "
    "Signals do not guarantee profits and no trades are executed automatically."
)
