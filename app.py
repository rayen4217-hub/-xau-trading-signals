import streamlit as st
import requests
import json

st.title("🟡 XAU/USD API Test")

url = "https://xaus.com/api/v1/intraday"

params = {
    "symbol": "xau",
    "hours": 48
}

try:
    response = requests.get(
        url,
        params=params,
        timeout=20
    )

    st.write("HTTP Status:", response.status_code)

    data = response.json()

    st.success("✅ API ردت")

    st.write("نوع البيانات:")
    st.write(type(data).__name__)

    st.write("البيانات الخام:")

    st.json(data)

except Exception as e:

    st.error("❌ خطأ")

    st.code(str(e))
