import streamlit as st
import yfinance as yf

st.set_page_config(page_title="XAU/USD Test")

st.title("🟡 XAU/USD Data Test")

st.write("جاري اختبار مصدر البيانات...")

try:
    ticker = yf.Ticker("XAUUSD=X")

    df = ticker.history(
        period="5d",
        interval="15m",
        auto_adjust=False
    )

    if df.empty:
        st.error("❌ البيانات رجعت فارغة.")
        st.write("Symbol tested: XAUUSD=X")
        st.write("Rows:", len(df))

    else:
        st.success("✅ البيانات وصلت بنجاح!")

        st.write("عدد الشموع:", len(df))

        st.write("آخر سعر:")
        st.metric(
            "XAU/USD",
            f"${float(df['Close'].iloc[-1]):.2f}"
        )

        st.write("آخر البيانات:")
        st.dataframe(df.tail(10))

except Exception as e:
    st.error("❌ صار خطأ أثناء جلب البيانات")
    st.code(str(e))
