import streamlit as st
import pandas as pd
import akshare as ak
import matplotlib.pyplot as plt

# ========== 获取A股股票数据 ==========
def get_stock_data(ticker):
    """
    从A股源（akshare）获取最近60日行情
    """
    try:
        # 自动补全股票代码格式
        if ticker.startswith(("6", "9")):
            code = ticker + ".SH"
        elif ticker.startswith(("0", "3")):
            code = ticker + ".SZ"
        else:
            code = ticker
        
        # 获取日线数据
        df = ak.stock_zh_a_daily(symbol=code)
        df = df.sort_index(ascending=True).tail(120)  # 取最近120天，保证MA计算足够
        df.rename(columns={"close": "Close", "high": "High", "low": "Low", "open": "Open", "volume": "Volume"}, inplace=True)
        
        # 计算移动平均
        df["MA5"] = df["Close"].rolling(window=5).mean()
        df["MA20"] = df["Close"].rolling(window=20).mean()
        df["MA50"] = df["Close"].rolling(window=50).mean()

        # 计算MACD指标
        short_ema = df["Close"].ewm(span=12, adjust=False).mean()
        long_ema = df["Close"].ewm(span=26, adjust=False).mean()
        df["MACD"] = short_ema - long_ema
        df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
        df["Hist"] = df["MACD"] - df["Signal"]

        # 中文名
        stock_name = ak.stock_individual_info_em(symbol=code).loc[0, "value"]
        return df, stock_name

    except Exception as e:
        st.error(f"获取A股数据失败: {e}")
        return None, None


# ========== 趋势判断逻辑 ==========
def analyze_stock(df):
    if df is None or df.empty:
        return "数据不足", "暂无买入区间", "无法预测"

    latest = df.iloc[-1]
    current_price = latest["Close"]
    ma5, ma20, ma50 = latest["MA5"], latest["MA20"], latest["MA50"]

    if ma5 > ma20 > ma50:
        mood = "🚀 牛气冲天！强势上涨趋势明显！"
        price_range = f"{current_price * 0.95:.2f} - {current_price * 1.05:.2f}"
        future_trend = "短期看涨"
    elif ma5 < ma20 < ma50:
        mood = "💸 空头占优，趋势偏弱，谨慎操作"
        price_range = f"{current_price * 0.85:.2f} - {current_price * 0.95:.2f}"
        future_trend = "短期看跌"
    else:
        mood = "🎢 震荡整理阶段，短线博弈激烈"
        price_range = f"{current_price * 0.9:.2f} - {current_price * 1.1:.2f}"
        future_trend = "横盘或震荡"

    return mood, price_range, future_trend


# ========== 绘图模块 ==========
def plot_charts(df, stock_name):
    st.subheader(f"📊 {stock_name} 行情图表")

    # 价格与均线
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(df.index, df["Close"], label="收盘价", color="black", linewidth=1)
    ax1.plot(df.index, df["MA5"], label="MA5", color="red", linewidth=0.8)
    ax1.plot(df.index, df["MA20"], label="MA20", color="blue", linewidth=0.8)
    ax1.plot(df.index, df["MA50"], label="MA50", color="green", linewidth=0.8)
    ax1.set_title(f"{stock_name} - 价格与均线")
    ax1.legend()
    st.pyplot(fig)

    # 成交量
    fig, ax2 = plt.subplots(figsize=(10, 3))
    ax2.bar(df.index, df["Volume"], color="grey", alpha=0.6)
    ax2.set_title("成交量")
    st.pyplot(fig)

    # MACD图
    fig, ax3 = plt.subplots(figsize=(10, 3))
    ax3.plot(df.index, df["MACD"], label="MACD", color="blue", linewidth=1)
    ax3.plot(df.index, df["Signal"], label="Signal", color="orange", linewidth=1)
    ax3.bar(df.index, df["Hist"], color=df["Hist"].apply(lambda x: "red" if x > 0 else "green"), alpha=0.4)
    ax3.legend()
    ax3.set_title("MACD 指标")
    st.pyplot(fig)


# ========== 主程序入口 ==========
def main():
    st.set_page_config(page_title="厉害啊，股神 🇨🇳", page_icon="📈", layout="centered")
    st.title("🇨🇳 厉害啊，股神）")

    ticker = st.text_input("请输入A股股票代码（例如 600519, 000001）", "600519")

    if ticker:
        with st.spinner("正在获取A股行情数据..."):
            df, stock_name = get_stock_data(ticker)

            if df is not None and not df.empty:
                mood, price_range, future_trend = analyze_stock(df)

                st.markdown(f"### 🏷 股票名称：**{stock_name}** ({ticker})")
                st.markdown(f"**当前行情情绪：** {mood}")
                st.markdown(f"**建议买入区间：** {price_range}")
                st.markdown(f"**未来趋势预测：** {future_trend}")

                st.divider()
                plot_charts(df, stock_name)

                st.subheader("📋 最近5个交易日数据")
                st.dataframe(df.tail(5)[["Close", "MA5", "MA20", "MA50", "MACD", "Signal", "Volume"]].round(2))

            else:
                st.warning("⚠️ 未获取到有效数据，请检查股票代码是否正确。")

    st.caption("🚀 本应用仅供学习参考，不构成投资建议。")


if __name__ == "__main__":
    main()
