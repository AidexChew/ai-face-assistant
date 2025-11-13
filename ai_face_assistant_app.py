import streamlit as st
import pandas as pd
import numpy as np
import akshare as ak
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

st.set_page_config(page_title="厉害啊，股神", layout="wide")

# ========== 工具函数 ==========
def get_stock_data(stock_code: str, start_date: str, end_date: str):
    """
    从 A 股抓取行情数据，返回包含中文名、MA、MACD 的 DataFrame
    """
    try:
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
        df.rename(columns={"日期": "Date", "开盘": "Open", "收盘": "Close", "最高": "High", "最低": "Low", "成交量": "Volume"}, inplace=True)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date")

        # 移动平均线
        df["MA20"] = df["Close"].rolling(window=20).mean()
        df["MA50"] = df["Close"].rolling(window=50).mean()

        # MACD 计算
        short_ema = df["Close"].ewm(span=12, adjust=False).mean()
        long_ema = df["Close"].ewm(span=26, adjust=False).mean()
        df["DIF"] = short_ema - long_ema
        df["DEA"] = df["DIF"].ewm(span=9, adjust=False).mean()
        df["MACD"] = 2 * (df["DIF"] - df["DEA"])

        # 中文名
        stock_info = ak.stock_individual_info_em(symbol=stock_code)
        cn_name = stock_info.loc[stock_info["item"] == "股票简称", "value"].values[0]

        return df, cn_name
    except Exception as e:
        st.error(f"❌ 数据获取失败：{e}")
        return None, None

def ai_summary(df):
    """
    简易 AI 总结模块：基于均线与 MACD 分析当前趋势
    """
    last_row = df.iloc[-1]
    trend = ""
    macd_signal = ""

    if last_row["MA20"] > last_row["MA50"]:
        trend = "短期走势强于中期，市场情绪偏多"
    else:
        trend = "短期走势弱于中期，市场情绪偏空"

    if last_row["MACD"] > 0 and last_row["DIF"] > last_row["DEA"]:
        macd_signal = "MACD 指标呈多头排列，趋势有望延续上行"
    elif last_row["MACD"] < 0 and last_row["DIF"] < last_row["DEA"]:
        macd_signal = "MACD 指标呈空头排列，短期或有下行风险"
    else:
        macd_signal = "MACD 处于震荡区域，趋势不明朗"

    summary = f"📊 综合判断：{trend}。\n💡 技术信号：{macd_signal}。"
    return summary

# ========== 主程序 ==========
def main():
    st.title("📈 厉害啊，股神")
    st.markdown("通过A股数据自动生成趋势图与AI语言总结")

    # 用户输入
    stock_code = st.text_input("请输入股票代码（示例：000001 表示平安银行）", "000001")
    end_date = datetime.today()
    start_date = end_date - timedelta(days=180)

    if st.button("获取行情"):
        with st.spinner("正在获取数据中..."):
            df, cn_name = get_stock_data(stock_code, start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d"))

            if df is not None:
                st.subheader(f"📍 {cn_name}（{stock_code}）")
                
                # ---- 趋势图 ----
                fig, ax1 = plt.subplots(figsize=(12, 5))
                ax1.plot(df["Date"], df["Close"], label="收盘价", color="blue")
                ax1.plot(df["Date"], df["MA20"], label="MA20", color="orange")
                ax1.plot(df["Date"], df["MA50"], label="MA50", color="purple")
                ax1.set_title(f"{cn_name} 价格趋势")
                ax1.legend()
                st.pyplot(fig)

                # ---- 成交量图 ----
                fig, ax2 = plt.subplots(figsize=(12, 3))
                ax2.bar(df["Date"], df["Volume"], color="gray")
                ax2.set_title("成交量")
                st.pyplot(fig)

                # ---- MACD 图 ----
                fig, ax3 = plt.subplots(figsize=(12, 3))
                ax3.plot(df["Date"], df["DIF"], label="DIF", color="green")
                ax3.plot(df["Date"], df["DEA"], label="DEA", color="red")
                ax3.bar(df["Date"], df["MACD"], color=np.where(df["MACD"] >= 0, "r", "g"))
                ax3.set_title("MACD 指标")
                ax3.legend()
                st.pyplot(fig)

                # ---- AI语言总结 ----
                st.markdown("### 🤖 AI语言总结")
                ai_text = ai_summary(df)
                st.info(ai_text)
            else:
                st.warning("未获取到有效数据，请检查股票代码。")

if __name__ == "__main__":
    main()
