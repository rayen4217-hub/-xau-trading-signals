import streamlit as st
import pandas as pd
import requests
import numpy as np
from datetime import datetime, timezone

st.set_page_config(
    page_title="XAU/USD Signals",
    page_icon="🟡",
    layout="wide"
)


@st.cache_data(ttl=60)
def get_data():
    url = "https://xaus.com/api/v1/intraday"

    params = {
        "symbol": "xau",
        "hours": 48
    }

    response = requests.get(
        url,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    points = data.get("points", [])

    if not points:
        return pd.DataFrame()

    df = pd.DataFrame(points)

    df["time"] = pd.to_datetime(
        df["t"],
        unit="s",
        utc=True
    )

    df["price"] = pd.to_numeric(
        df["p"],
        errors="coerce"
    )

    df = df[["time", "price"]]
    df = df.dropna()
    df = df.set_index("time")
    df = df.sort_index()

    # تحويل بيانات كل دقيقتين إلى شموع 15 دقيقة
    candles = df["price"].resample("15min").ohlc()

    candles = candles.dropna()

    return candles


def calculate_indicators(df):

    df = df.copy()

    # EMA
    df["EMA20"] = df["close"].ewm(
        span=20,
        adjust=False
    ).mean()

    df["EMA50"] = df["close"].ewm(
        span=50,
        adjust=False
    ).mean()

    # RSI 14
    delta = df["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss

    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["close"].ewm(
        span=12,
        adjust=False
    ).mean()

    ema26 = df["close"].ewm(
        span=26,
        adjust=False
    ).mean()

    df["MACD"] = ema12 - ema26

    df["Signal"] = df["MACD"].ewm(
        span=9,
        adjust=False
    ).mean()

    # ATR 14
    high_low = df["high"] - df["low"]

    high_close = (
        df["high"] - df["close"].shift()
    ).abs()

    low_close = (
        df["low"] - df["close"].shift()
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


def generate_signal(df):

    last = df.iloc[-1]

    price = last["close"]
    ema20 = last["EMA20"]
    ema50 = last["EMA50"]
    rsi = last["RSI"]
    macd = last["MACD"]
    macd_signal = last["Signal"]
    atr = last["ATR"]

    buy_score = 0
    sell_score = 0

    # EMA trend
    if ema20 > ema50:
        buy_score += 1
    elif ema20 < ema50:
        sell_score += 1

    # Price vs EMA20
    if price > ema20:
        buy_score += 1
    elif price < ema20:
        sell_score += 1

    # MACD
    if macd > macd_signal:
        buy_score += 1
    elif macd < macd_signal:
        sell_score += 1

    # RSI
    if 50 < rsi < 70:
        buy_score += 1
    elif 30 < rsi < 50:
        sell_score += 1

    # منع الإشارات في التشبع
    if rsi >= 80:
        signal = "WAIT"
    elif rsi <= 20:
        signal = "WAIT"
    elif buy_score >= 3 and buy_score > sell_score:
        signal = "BUY"
    elif sell_score >= 3 and sell_score > buy_score:
        signal = "SELL"
    else:
        signal = "WAIT"

    # قوة الإشارة = اتفاق المؤشرات
    strength = max(
        buy_score,
        sell_score
    ) / 4 * 100

    # Entry / SL / TP
    entry = price

    if signal == "BUY":

        sl = entry - (1.5 * atr)

        tp1 = entry + (1.0 * atr)
        tp2 = entry + (2.0 * atr)
        tp3 = entry + (3.0 * atr)

    elif signal == "SELL":

        sl = entry + (1.5 * atr)

        tp1 = entry - (1.0 * atr)
        tp2 = entry - (2.0 * atr)
        tp3 = entry - (3.0 * atr)

    else:

        sl = None
        tp1 = None
        tp2 = None
        tp3 = None

    return {
        "signal": signal,
        "strength": strength,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "rsi": rsi,
        "ema20": ema20,
        "ema50": ema50,
        "macd": macd,
        "macd_signal": macd_signal,
        "atr": atr
    }


@st.fragment(run_every="60s")
def dashboard():

    st.title("🟡 XAU/USD Trading Signals")

    try:

        df = get_data()

        if df.empty:
            st.error("❌ لا توجد بيانات.")
            return

        if len(df) < 60:
            st.warning(
                f"البيانات الحالية غير كافية للمؤشرات. "
                f"عدد الشموع: {len(df)}"
            )
            return

        df = calculate_indicators(df)

        df = df.dropna()

        result = generate_signal(df)

        last_time = df.index[-1]

        st.subheader(
            f"السعر الحالي: {result['entry']:.2f}"
        )

        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                "Signal",
                result["signal"]
            )

        with col2:

            st.metric(
                "Strength",
                f"{result['strength']:.0f}%"
            )

        st.divider()

        st.subheader("🎯 Trading Levels")

        if result["signal"] != "WAIT":

            c1, c2, c3, c4 = st.columns(4)

            c1.metric(
                "Entry",
                f"{result['entry']:.2f}"
            )

            c2.metric(
                "Stop Loss",
                f"{result['sl']:.2f}"
            )

            c3.metric(
                "TP1",
                f"{result['tp1']:.2f}"
            )

            c4.metric(
                "TP2",
                f"{result['tp2']:.2f}"
            )

            st.metric(
                "TP3",
                f"{result['tp3']:.2f}"
            )

        else:

            st.info(
                "WAIT — المؤشرات ما عطاوش توافق كافي للدخول."
            )

        st.divider()

        st.subheader("📊 Indicators")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "RSI",
            f"{result['rsi']:.2f}"
        )

        c2.metric(
            "EMA20",
            f"{result['ema20']:.2f}"
        )

        c3.metric(
            "EMA50",
            f"{result['ema50']:.2f}"
        )

        c4.metric(
            "ATR",
            f"{result['atr']:.2f}"
        )

        st.subheader("📈 XAU/USD 15M")

        chart_data = df[
            ["open", "high", "low", "close"]
        ].tail(100)

        st.line_chart(
            chart_data["close"]
        )

        st.caption(
            f"آخر شمعة: {last_time.strftime('%Y-%m-%d %H:%M UTC')}"
        )

        st.caption(
            "Strength = نسبة توافق المؤشرات، "
            "وليست احتمال ربح."
        )

    except Exception as e:

        st.error("❌ حدث خطأ")

        st.code(str(e))


dashboard()
