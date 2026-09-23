import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(
    page_title="XAU/USD Trading Signals",
    page_icon="🟡",
    layout="centered"
)

st.title("🟡 XAU/USD Trading Signals")
st.caption("XAU/USD Spot • 15 Minute • EMA • RSI • MACD • ATR")
st.caption("🔄 Auto refresh: every 60 seconds")


# =========================
# XAUS DATA
# =========================

@st.cache_data(ttl=60)
def get_gold_data():

    url = "https://xaus.com/api/v1/intraday"

    params = {
        "symbol": "xau",
        "hours": 48
    }

    response = requests.get(
        url,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    points = data.get("points", [])

    if not points:
        return pd.DataFrame()

    df = pd.DataFrame(points)

    # Convert timestamp
    df["t"] = pd.to_datetime(
        df["t"],
        utc=True
    )

    df["p"] = pd.to_numeric(
        df["p"],
        errors="coerce"
    )

    df = df.dropna()

    df = df.set_index("t")

    # Convert 2-minute prices into 15-minute candles
    candles = df["p"].resample("15min").ohlc()

    candles = candles.dropna()

    candles.columns = [
        "Open",
        "High",
        "Low",
        "Close"
    ]

    return candles


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

    df["RSI"] = 100 - (
        100 / (1 + rs)
    )

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
    high_low = (
        df["High"] - df["Low"]
    )

    high_close = (
        df["High"] -
        df["Close"].shift()
    ).abs()

    low_close = (
        df["Low"] -
        df["Close"].shift()
    ).abs()

    tr = pd.concat(
        [
            high_low,
            high_close,
            low_close
        ],
        axis=1
    ).max(axis=1)

    df["ATR"] = tr.rolling(14).mean()

    return df


# =========================
# SIGNAL
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

    buy = 0
    sell = 0

    # EMA
    if ema20 > ema50:
        buy += 1
    elif ema20 < ema50:
        sell += 1

    # MACD
    if macd > macd_signal:
        buy += 1
    elif macd < macd_signal:
        sell += 1

    # RSI
    if 50 < rsi < 80:
        buy += 1
    elif 20 < rsi < 50:
        sell += 1

    # Price / EMA
    if price > ema20:
        buy += 1
    elif price < ema20:
        sell += 1

    # Extreme RSI protection
    if rsi < 20 or rsi > 80:

        signal = "WAIT"
        strength = 0

    elif buy >= 3 and buy > sell:

        signal = "BUY"
        strength = int(
            (buy / 4) * 100
        )

    elif sell >= 3 and sell > buy:

        signal = "SELL"
        strength = int(
            (sell / 4) * 100
        )

    else:

        signal = "WAIT"
        strength = int(
            max(buy, sell) / 4 * 100
        )

    if pd.isna(atr) or atr <= 0:
        atr = price * 0.001

    entry = price

    if signal == "BUY":

        sl = entry - atr * 1.5
        tp1 = entry + atr
        tp2 = entry + atr * 2
        tp3 = entry + atr * 3

    elif signal == "SELL":

        sl = entry + atr * 1.5
        tp1 = entry - atr
        tp2 = entry - atr * 2
        tp3 = entry - atr * 3

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
# DASHBOARD
# =========================

@st.fragment(run_every="60s")
def dashboard():

    try:

        df = get_gold_data()

    except Exception as e:

        st.error(
            "❌ خطأ في جلب بيانات XAU/USD"
        )

        st.code(str(e))

        return

    if df.empty:

        st.error(
            "❌ ما وصلتناش بيانات XAU/USD."
        )

        return

    df = calculate_indicators(df)

    df = df.dropna()

    if len(df) < 60:

        st.warning(
            f"⏳ البيانات الحالية غير كافية للمؤشرات. "
            f"عدد الشموع: {len(df)}"
        )

        return

    result = generate_signal(df)

    signal = result["signal"]

    # Signal
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

    # Price
    st.metric(
        "XAU/USD Spot",
        f"${result['price']:.2f}"
    )

    # Levels
    st.subheader("📍 Trade Levels")

    c1, c2 = st.columns(2)

    with c1:

        st.metric(
            "Entry",
            f"{result['entry']:.2f}"
        )

        if result["sl"] is not None:

            st.metric(
                "Stop Loss",
                f"{result['sl']:.2f}"
            )

    with c2:

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

    # Indicators
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
            f"**MACD Signal:** "
            f"{result['macd_signal']:.4f}"
        )

        st.write(
            f"**ATR:** {result['atr']:.2f}"
        )

    # Chart
    st.subheader("📈 XAU/USD — 15m")

    chart = df[
        ["Close", "EMA20", "EMA50"]
    ].tail(100)

    st.line_chart(chart)

    st.caption(
        "🔄 آخر تحديث: "
        + datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    st.caption(
        "⚠️ الإشارات تقنية وليست ضمانًا للربح."
    )


dashboard()
