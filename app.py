import streamlit as st
import requests

st.title("🟡 XAU/USD - قراءة نقطة واحدة")

url = "https://xaus.com/api/v1/intraday"

params = {
    "symbol": "xau",
    "hours": 48
}

try:
    response = requests.get(url, params=params, timeout=20)
    data = response.json()

    st.write("Status:", response.status_code)
    st.write("عدد النقاط:", data.get("count"))

    points = data.get("points", [])

    st.write("نوع أول نقطة:")
    st.write(type(points[0]).__name__)

    st.write("أول نقطة:")
    st.json(points[0])

    st.write("آخر نقطة:")
    st.json(points[-1])

except Exception as e:
    st.error(str(e))
