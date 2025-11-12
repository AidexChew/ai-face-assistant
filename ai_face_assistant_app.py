import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

# ==============================
# 股票数据获取与处理
# ==============================
def get_stock_data(ticker):
    try:
        df = yf.download(ticker, period="35d", interval="1d")
        if df.empty:
            st.error(f"未获取到 {ticker} 的数据，请检查股票代码或时间范围。")
            return None, None

        # 统一列名格式
        df.rename(columns=lambda x: x.capitalize(), inplace=True)
        if "Close" not in df.columns:
            st.error("数据中没有 'Close' 列，可能是下载失败。")
            return None, None

        df = df.sort_index(ascending=True)
        df["MA5"] = df["Close"].rolling(window=5, min_periods=1).mean()
        df["MA20"] = df["Close"].rolling(window=20, min_periods=1).mean()
        df["MA50"] = df["Close"].rolling(window=50, min_periods=1).mean()

        return df, ticker
    except Exception as e:
        st.error(f"获取数据时出错: {str(e)}")
        return None, None


# ==============================
# 数据分析逻辑
# ==============================
def analyze_stock(df):
    if df is None or df.empty:
        return "数据不足，无法分析", "暂无买入区间", "无法预测"

    latest = df.iloc[-1]

    ma5 = latest["Ma5"] if "Ma5" in latest else None
    ma20 = latest["Ma20"] if "Ma20" in latest else None
    ma50 = latest["Ma50"] if "Ma50" in latest else None
    close = latest["Close"]

    # 防止NaN错误
    if any(pd.isna(x) for x in [ma5, ma20, ma50, close]):
        return "数据不足", "暂无买入区间", "无法预测"

    # 情绪判断
    if close > ma5 > ma20:
        mood = "市场情绪偏强（多头趋势）"
    elif close < ma5 < ma20:
        mood = "市场情绪偏弱（空头趋势）"
    else:
        mood = "震荡整理（情绪中性）"

    # 买入区间（简单示例）
    buy_zone = f"{round(ma20 * 0.98, 2)} - {round(ma20 * 1.02, 2)}"

    # 趋势预测
    if ma5 > ma20 > ma50:
        trend = "短期看涨，趋势良好"
    elif ma5 < ma20 < ma50:
        trend = "短期下行，需谨慎"
    else:
        trend = "趋势不明朗，建议观望"

    return mood, buy_zone, trend


# ==============================
# 主程序
# ==============================
def main():
    st.set_page_config(page_title="AI股票分析助手", page_icon="📈", layout="centered")

    st.title("📊 AI 股票分析助手")
    st.write("输入股票代码（例如：AAPL、TSLA、MSFT、0700.HK、600519.SS）")

    ticker = st.text_input("请输入股票代码：", "AAPL")

    if st.button("开始分析"):
        df, ticker = get_stock_data(ticker)

        if df is not None and not df.empty:
            st.subheader(f"📈 {ticker} 最近走势")
            st.line_chart(df[["Close", "MA20", "MA50"]])

            mood, price_range, future_trend = analyze_stock(df)

            st.markdown("### 💡 分析结果")
            st.write(f"**当前行情情绪：** {mood}")
            st.write(f"**建议买入价区间：** {price_range}")
            st.write(f"**未来趋势预测：** {future_trend}")
        else:
            st.warning("未能成功获取数据，请检查输入的股票代码。")


if __name__ == "__main__":
    main()
