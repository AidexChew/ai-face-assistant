# ai_face_assistant_app.py
import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="AI 看脸色助手", layout="wide")

st.title("📈 AI 看脸色助手")
st.write("输入股票代码，我帮你看看行情的“脸色” 😊")

# 输入股票代码
symbol = st.text_input("请输入股票代码 (例：000001.SZ 或 AAPL)：", "000001.SZ")

# 数据拉取
@st.cache_data(ttl=3600)  # 缓存1小时，减少重复请求
def get_data(symbol):
    df = yf.download(symbol, period="6mo", interval="1d")
    if df.empty:
        return None
    df["MA20"] = df["Close"].rolling(window=20).mean()
    df["MA50"] = df["Close"].rolling(window=50).mean()
    return df

df = get_data(symbol)

# 判断数据是否成功拉取
if df is None:
    st.error("无法获取该股票数据，请检查股票代码。")
else:
    st.subheader(f"{symbol} 最近收盘价 & 均线")
    st.line_chart(df[["Close", "MA20", "MA50"]])

    # AI 看脸色分析
def analyze_face(df):
    """
    根据收盘价和均线计算“脸色”，返回文字描述
    df: DataFrame，需要包含 ['Close','MA20','MA50']
    """
    # 检查数据
    if df.empty or len(df) < 50:
        return "数据不足，无法分析"

    # 确保 MA20 和 MA50 是数值，而不是 Series
    close = float(df["Close"].iloc[-1])
    ma20 = float(df["MA20"].iloc[-1])
    ma50 = float(df["MA50"].iloc[-1])
    prev_close = float(df["Close"].iloc[-2])

    # 根据收盘价与均线关系判断脸色
    if close > ma20 > ma50:
        face = "😊 开心：行情看起来不错"
    elif close < ma20 < ma50:
        face = "😟 忧心：行情偏弱，注意风险"
    else:
        face = "😐 平常：行情震荡，谨慎操作"

    # 最新涨跌幅
    pct_change = (close - prev_close) / prev_close * 100
    face += f"（最新涨跌幅：{pct_change:.2f}%）"

    return face




    result = analyze_face(df)
    st.subheader("📊 AI 看脸色结果")
    st.write(result)
