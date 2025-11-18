# ai_face_assistant_app.py
import streamlit as st
import pandas as pd
import numpy as np
import akshare as ak
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time
import random

st.set_page_config(page_title="厉害了，股神", page_icon="📈", layout="centered")

# ---------------------
# 市场识别函数
# ---------------------
def identify_market(stock_code):
    code = str(stock_code).strip().upper()

    if code.isalpha():
        return 'US', code

    if code.isdigit():
        if len(code) == 6:
            if code.startswith(('6', '5', '9')):
                return 'A', code + '.SS'
            elif code.startswith(('0', '2', '3')):
                return 'A', code + '.SZ'
        elif 1 <= len(code) <= 5:
            return 'H', code.zfill(5) + '.HK'

    return 'A', code

# ---------------------
# 获取中文股票名（A股）
# ---------------------
def get_stock_cn_name(code):
    try:
        stock_list = ak.stock_info_a_code_name()
        row = stock_list[stock_list["code"] == code[:6]]
        if not row.empty:
            return row["name"].values[0]
    except:
        pass
    return code

# ---------------------
# 数据获取函数（A股/港股/美股）
# ---------------------
def get_stock_data(raw_code):
    try:
        market_type, normalized = identify_market(raw_code)
        df = None
        cn_name = raw_code

        for _ in range(3):
            try:
                if market_type == "A":
                    code6 = normalized.replace(".SS", "").replace(".SZ", "")
                    df = ak.stock_zh_a_hist(
                        symbol=code6, period="daily", adjust="qfq"
                    )
                    cn_name = get_stock_cn_name(code6)

                elif market_type == "H":
                    df = ak.stock_hk_hist(
                        symbol=normalized.replace(".HK",""), period="daily"
                    )

                elif market_type == "US":
                    ticker = yf.Ticker(normalized)
                    df = ticker.history(period="6mo", interval="1d")
                    if df is not None and not df.empty:
                        df = df.rename(columns={
                            "Open": "open","High": "high","Low": "low",
                            "Close": "close","Volume": "volume"
                        })
                break

            except:
                time.sleep(random.uniform(1, 2))
                continue

        if df is None or df.empty:
            st.error("获取 A 股数据失败")
            return None, normalized, cn_name

        # 清洗统一格式
        df = preprocess_dataframe(df, market_type)
        df = calculate_technical_indicators(df)

        return df, normalized, cn_name

    except Exception as e:
        st.error(f"获取数据失败: {str(e)}")
        return None, raw_code, raw_code

# ---------------------
# 预处理数据
# ---------------------
def preprocess_dataframe(df, market_type):
    df = df.copy()
    mapping = {}

    for col in df.columns:
        c = str(col).lower()
        if "date" in c or "日期" in c:
            mapping[col] = "date"
        elif "open" in c or "开盘" in c:
            mapping[col] = "open"
        elif "high" in c or "最高" in c:
            mapping[col] = "high"
        elif "low" in c or "最低" in c:
            mapping[col] = "low"
        elif "close" in c or "收盘" in c:
            mapping[col] = "close"
        elif "volume" in c or "成交量" in c:
            mapping[col] = "volume"

    df.rename(columns=mapping, inplace=True)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    else:
        df = df.reset_index().rename(columns={"index": "date"})

    df = df.sort_values("date").tail(180).reset_index(drop=True)

    for col in ["open","high","low","close","volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df

# ---------------------
# 技术指标
# ---------------------
def calculate_technical_indicators(df):
    df["MA5"] = df["close"].rolling(5).mean()
    df["MA20"] = df["close"].rolling(20).mean()
    df["MA50"] = df["close"].rolling(50).mean()

    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["DIF"] = ema12 - ema26
    df["DEA"] = df["DIF"].ewm(span=9, adjust=False).mean()
    df["MACD"] = 2 * (df["DIF"] - df["DEA"])

    return df

# ---------------------
# AI 投研总结（专业风格）
# ---------------------
def ai_research_summary(df):
    latest = df.iloc[-1]

    # 趋势
    if latest["MA5"] > latest["MA20"] > latest["MA50"]:
        trend_text = "当前处于【多头趋势】结构，资金偏强，整体走势健康。"
    elif latest["MA5"] < latest["MA20"] < latest["MA50"]:
        trend_text = "处于【空头趋势】，短期存在下行压力，需谨慎。"
    else:
        trend_text = "处于【震荡结构】，多空力量均衡。"

    # MACD
    if latest["MACD"] > 0 and latest["DIF"] > latest["DEA"]:
        macd_text = "MACD 红柱维持，多头动能增强。"
    elif latest["MACD"] < 0 and latest["DIF"] < latest["DEA"]:
        macd_text = "MACD 绿柱持续，空头动能增强。"
    else:
        macd_text = "MACD 动能中性，方向待确认。"

    # 成交量
    vol5 = df["volume"].tail(5).mean()
    vol1 = latest["volume"]
    if vol1 > vol5 * 1.2:
        vol_text = "成交量明显放大，资金活跃度提升。"
    elif vol1 < vol5 * 0.8:
        vol_text = "成交量萎缩，市场观望情绪偏重。"
    else:
        vol_text = "成交量正常波动。"

    summary = f"""
### 📘 AI 投研总结（专业版）

**1. 趋势结构：**  
{trend_text}

**2. MACD 动能：**  
{macd_text}

**3. 成交量情况：**  
{vol_text}

**4. 综合研判：**  
结合趋势、动能与成交量，短期参考意义：  
- 若 MA5 > MA20，可视为强势回踩后的观察窗口  
- 若 MA5 < MA20，短线有继续调整的风险  
"""
    return summary

# ---------------------
# 绘图
# ---------------------
def plot_stock_charts(df, name):
    st.subheader(f"📊 {name} - 技术分析")

    x = df["date"]

    # K线 + 均线
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(x, df["close"], label="收盘价", color="black")
    ax.plot(x, df["MA5"], label="MA5", color="orange")
    ax.plot(x, df["MA20"], label="MA20", color="blue")
    ax.plot(x, df["MA50"], label="MA50", color="purple")

    ax.legend()
    ax.grid(alpha=0.3)
    plt.xticks(rotation=45)
    st.pyplot(fig)

    # MACD
    fig2, ax2 = plt.subplots(figsize=(10, 3))
    ax2.bar(x, df["MACD"], color="red")
    ax2.plot(x, df["DIF"], label="DIF")
    ax2.plot(x, df["DEA"], label="DEA")
    ax2.legend()
    ax2.grid(alpha=0.3)
    plt.xticks(rotation=45)
    st.pyplot(fig2)

    # 成交量
    fig3, ax3 = plt.subplots(figsize=(10, 3))
    ax3.bar(x, df["volume"], alpha=0.5)
    ax3.set_title("成交量")
    plt.xticks(rotation=45)
    st.pyplot(fig3)

# ---------------------
# 主程序
# ---------------------
def main():
    st.title("📈 厉害了，股神")

    code = st.text_input("请输入股票代码：", "600519")

    if code:
        with st.spinner("正在获取数据并分析..."):
            df, display_code, cn_name = get_stock_data(code)

            if df is not None and not df.empty:
                plot_stock_charts(df, cn_name)

                st.subheader("📘 AI 投研风格总结")
                st.markdown(ai_research_summary(df))

                st.subheader("📋 最近交易数据")
                st.dataframe(df.tail(10))

main()
