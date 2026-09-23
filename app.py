import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

st.set_page_config(
    page_title="XAU/USD Trading Signals",
    page_icon="🟡",
    layout="centered"
)

st.title("🟡 XAU/USD Trading Signals")
st.caption("15 Minute • EMA 20/50 • RSI • MACD • ATR")
st.caption("🔄 Auto refresh: every 60 seconds")


# =========================
# GET XAU/USD SPOT DATA
# =========================
@st.cache_data(ttl=60)
def get_data():

    ticker = yf.Ticker("XAUUSD=X")

    df = ticker.history(
        period="10d",
        interval="15m",
        auto_adjust=False
    )

    if df.empty:
        return pd.DataFrame()

    df = df.dropna()

    return df


# =========================
# INDICATORS
# =========================
def calculate_indicators(df):

    df = df.copy()

    # EMA
    df["EMA20"] = df["Close"].ewm(
        span=20,
        adjust=False
    ).mean()

    df["EMA50"] = df["Close"].ewm(
        span=50,
        adjust=False
    ).mean()

    # RSI
    delta = df["Close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss.replace(0, pd.NA)

    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["Close"].ewm(
        span=12,
        adjust=False
    ).mean()

    ema26 = df["Close"].ewm(
        span=26,
        adjust=False
    ).mean()

    df["MACD"] = ema12 - ema26

    df["MACD_SIGNAL"] = df["MACD"].ewm(
        span=9,
        adjust=False
    ).mean()

    # ATR
    high_low = df["High"] - df["Low"]

    high_close = (
        df["High"] - df["Close"].shift()
    ).abs()

    low_close = (
        df["Low"] - df["Close"].shift()
    ).abs()

    true_range = pd.concat(
        [
            high_low,
            high_close,
            low_close
        ],
        axis=1
    ).max(axis=1)

    df["ATR"] = true_range.rolling(14).mean()

    return df


# =========================
# SIGNAL ENGINE
# =========================
def generate_signal(df):

    last = df.iloc[-1]

    price = float(last["Close"])
    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])
    rsi = float(last["RSI"])
    macd = float(last["MACD"])
    macd_signal = float(last["MACD_SIGNAL"])
    atr = float(last["ATR"])

    buy_score = 0
    sell_score = 0

    # EMA
    if ema20 > ema50:
        buy_score += 1
    elif ema20 < ema50:
        sell_score += 1

    # MACD
    if macd > macd_signal:
        buy_score += 1
    elif macd < macd_signal:
        sell_score += 1

    # RSI
    if 50 < rsi < 80:
        buy_score += 1
    elif 20 < rsi < 50:
        sell_score += 1

    # Price vs EMA20
    if price > ema20:
        buy_score += 1
    elif price < ema20:
        sell_score += 1

    # Extreme RSI protection
    if rsi < 20:
        signal = "WAIT"
        strength = 0

    elif rsi > 80:
        signal = "WAIT"
        strength = 0

    elif buy_score >= 3 and buy_score > sell_score:
        signal = "BUY"
        strength = int((buy_score / 4) * 100)

    elif sell_score >= 3 and sell_score > buy_score:
        signal = "SELL"
        strength = int((sell_score / 4) * 100)

    else:
        signal = "WAIT"
        strength = int(
            max(buy_score, sell_score) / 4 * 100
        )

    # =========================
    # ENTRY / SL / TP
    # =========================

    entry = price

    if pd.isna(atr) or atr <= 0:
        atr = price * 0.001

    if signal == "BUY":

        sl = entry - (atr * 1.5)

        tp1 = entry + (atr * 1.0)
        tp2 = entry + (atr * 2.0)
        tp3 = entry + (atr * 3.0)

    elif signal == "SELL":

        sl = entry + (atr * 1.5)

        tp1 = entry - (atr * 1.0)
        tp2 = entry - (atr * 2.0)
        tp3 = entry - (atr * 3.0)

    else:

        sl = None
        tp1 = None
        tp2 = None
        tp3 = None

    return {
        "signal": signal,
        "strength": strength,
        "price": price,
        "ema20": ema20,
        "ema50": ema50,
        "rsi": rsi,
        "macd": macd,
        "macd_signal": macd_signal,
        "atr": atr,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3
    }


# =========================
# LIVE DASHBOARD
# =========================
@st.fragment(run_every="60s")
def live_dashboard():

    df = get_data()

    if df.empty:

        st.error(
            "❌ ما قدرناش نجيبو بيانات XAU/USD حاليا."
        )

        return

    df = calculate_indicators(df)

    df = df.dropna()

    if len(df) < 60:

        st.warning(
            "⏳ مازال نحتاجو بيانات أكثر لحساب المؤشرات."
        )

        return

    result = generate_signal(df)

    signal = result["signal"]

    # =========================
    # SIGNAL
    # =========================

    if signal == "BUY":
        st.success(
            f"🟢 BUY — Strength {result['strength']}%"
        )

    elif signal == "SELL":
        st.error(
            f"🔴 SELL — Strength {result['strength']}%"
        )

    else:
        st.warning(
            f"⚪ WAIT — Strength {result['strength']}%"
        )

    # =========================
    # PRICE
    # =========================

    st.metric(
        "XAU/USD Spot",
        f"${result['price']:.2f}"
    )

    # =========================
    # TRADE LEVELS
    # =========================

    st.subheader("📍 Trade Levels")

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Entry",
            f"{result['entry']:.2f}"
        )

        if result["sl"] is not None:

            st.metric(
                "Stop Loss",
                f"{result['sl']:.2f}"
            )

    with col2:

        if result["tp1"] is not None:

            st.metric(
                "TP1",
                f"{result['tp1']:.2f}"
            )

            st.metric(
                "TP2",
                f"{result['tp2']:.2f}"
            )

            st.metric(
                "TP3",
                f"{result['tp3']:.2f}"
            )

    # =========================
    # INDICATORS
    # =========================

    st.subheader("📊 Indicators")

    c1, c2 = st.columns(2)

    with c1:

        st.write(
            f"**EMA 20:** {result['ema20']:.2f}"
        )

        st.write(
            f"**EMA 50:** {result['ema50']:.2f}"
        )

        st.write(
            f"**RSI:** {result['rsi']:.2f}"
        )

    with c2:

        st.write(
            f"**MACD:** {result['macd']:.4f}"
        )

        st.write(
            f"**MACD Signal:** {result['macd_signal']:.4f}"
        )

        st.write(
            f"**ATR:** {result['atr']:.2f}"
        )

    # =========================
    # CHART
    # =========================

    st.subheader("📈 XAU/USD — 15m")

    chart_data = df[[
        "Close",
        "EMA20",
        "EMA50"
    ]].tail(100)

    st.line_chart(chart_data)

    # =========================
    # UPDATE TIME
    # =========================

    st.caption(
        "Last update: "
        + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    st.caption(
        "⚠️ الإشارة تقنية فقط وليست ضمانًا للربح."
    )


live_dashboard()
