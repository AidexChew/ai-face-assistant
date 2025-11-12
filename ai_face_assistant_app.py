import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt


# ========== 获取股票数据 ==========
def get_stock_data(ticker):
    try:
        df = yf.download(ticker, period="60d", interval="1d")
        if df.empty:
            return None, None

        df = df.sort_index(ascending=True)
        df["MA5"] = df["Close"].rolling(window=5, min_periods=1).mean()
        df["MA20"] = df["Close"].rolling(window=20, min_periods=1).mean()
        df["MA50"] = df["Close"].rolling(window=50, min_periods=1).mean()

        return df, ticker
    except Exception as e:
        st.error(f"获取数据时出错: {str(e)}")
        return None, None


# ========== 分析逻辑 ==========
def analyze_stock(df):
    try:
        latest = df.iloc[-1]

        ma5 = latest["MA5"] if "MA5" in latest else None
        ma20 = latest["MA20"] if "MA20" in latest else None
        ma50 = latest["MA50"] if "MA50" in latest else None

        mood, price_range, future_trend = "未知", "暂无买入区间", "无法预测"

        if pd.notna(ma5) and pd.notna(ma20) and pd.notna(ma50):
            # 简单均线趋势判断
            if ma5 > ma20 > ma50:
                mood = "强势上涨"
                price_range = f"{latest['Close'] * 0.95:.2f} - {latest['Close'] * 1.05:.2f}"
                future_trend = "短期看涨"
            elif ma5 < ma20 < ma50:
                mood = "弱势下跌"
                price_range = f"{latest['Close'] * 0.85:.2f} - {latest['Close'] * 0.95:.2f}"
                future_trend = "短期看跌"
            else:
                mood = "震荡整理"
                price_range = f"{latest['Close'] * 0.9:.2f} - {latest['Close'] * 1.1:.2f}"
                future_trend = "横盘或微幅波动"
        else:
            mood = "数据不足，无法分析"

        return mood, price_range, future_trend

    except Exception as e:
        st.error(f"分析出错: {str(e)}")
        return "错误", "暂无", "无法预测"


# ========== 主程序入口 ==========
def main():
    st.set_page_config(page_title="咧啊，股神", page_icon="📈", layout="centered")

    st.title("📊 咧啊，股神")
    st.markdown("输入股票代码（示例：`AAPL`, `TSLA`, `0700.HK`, `600519.SS`）")
    st.divider()

    ticker = st.text_input("请输入股票代码：", "AAPL")

    if st.button("开始分析"):
        with st.spinner("正在获取数据并分析，请稍候..."):
            df, ticker = get_stock_data(ticker)

            if df is not None and not df.empty:
                st.subheader(f"📈 {ticker} 最近行情趋势")

                # ✅ 防止 KeyError：只画存在的列
                columns_to_show = [c for c in ["Close", "MA20", "MA50"] if c in df.columns]
                if columns_to_show:
                    st.line_chart(df[columns_to_show])
                else:
                    st.warning("图表列缺失，无法绘制走势图。")

                # 输出分析结果
                mood, price_range, future_trend = analyze_stock(df)

                st.markdown("### 💡 分析结果")
                st.write(f"**当前行情情绪：** {mood}")
                st.write(f"**建议买入价区间：** {price_range}")
                st.write(f"**未来趋势预测：** {future_trend}")

            else:
                st.error("未能成功获取股票数据，请检查股票代码是否正确。")

    st.divider()
    st.caption("🚀 本应用由 AI 驱动，仅供学习参考，不构成投资建议。")


if __name__ == "__main__":
    main()
