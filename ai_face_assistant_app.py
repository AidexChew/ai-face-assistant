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

    # 使用文本输入框，移除按钮，直接通过输入触发
    ticker = st.text_input("请输入股票代码：", "AAPL", key="stock_input")
    
    # 添加自定义CSS样式来优化显示
    st.markdown("""
    <style>
    .analysis-card {
        padding: 12px;
        border-radius: 8px;
        margin: 8px 0;
        border-left: 4px solid;
    }
    .mood-card {
        border-left-color: #FF4B4B;
        background-color: #FFF5F5;
    }
    .price-card {
        border-left-color: #00D4AA;
        background-color: #F0FFFD;
    }
    .trend-card {
        border-left-color: #6F42C1;
        background-color: #F8F7FF;
    }
    .result-text {
        font-size: 14px;
        font-weight: bold;
        margin: 0;
    }
    </style>
    """, unsafe_allow_html=True)

    # 当有输入时自动触发分析（去掉按钮）
    if ticker:
        with st.spinner("正在获取数据并分析，请稍候..."):
            df, ticker_used = get_stock_data(ticker)

            if df is not None and not df.empty:
                st.subheader(f"📈 {ticker_used} 分析结果")
                
                # 分析股票数据
                mood, price_range, future_trend = analyze_stock(df)
                
                # 使用三列布局高亮显示分析结果
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # 当前行情情绪卡片
                    st.markdown(
                        f"""
                        <div class="analysis-card mood-card">
                            <p style="font-size: 12px; margin: 0 0 4px 0; color: #666;">当前行情情绪</p>
                            <p class="result-text">{mood}</p>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                
                with col2:
                    # 建议买入价区间卡片
                    st.markdown(
                        f"""
                        <div class="analysis-card price-card">
                            <p style="font-size: 12px; margin: 0 0 4px 0; color: #666;">建议买入价区间</p>
                            <p class="result-text">{price_range}</p>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                
                with col3:
                    # 未来趋势预测卡片
                    st.markdown(
                        f"""
                        <div class="analysis-card trend-card">
                            <p style="font-size: 12px; margin: 0 0 4px 0; color: #666;">未来趋势预测</p>
                            <p class="result-text">{future_trend}</p>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                
                st.divider()
                
                # 最近行情趋势图 - 移到分析结果下面，但在交易日数据之前
                st.subheader("📊 最近行情趋势")
                
                # 防止 KeyError：只画存在的列
                columns_to_show = [c for c in ["Close", "MA20", "MA50"] if c in df.columns]
                if columns_to_show:
                    st.line_chart(df[columns_to_show])
                else:
                    st.warning("图表列缺失，无法绘制走势图。")

                # 最近交易日数据
                st.subheader("📋 最近5个交易日数据")
                display_columns = []
                for col in ["Close", "MA5", "MA20", "MA50"]:
                    if col in df.columns:
                        display_columns.append(col)
                
                if display_columns:
                    recent_data = df.tail(5)[display_columns]
                    # 格式化数字显示
                    formatted_data = recent_data.round(2)
                    st.dataframe(formatted_data, use_container_width=True)
                else:
                    st.warning("暂无完整的指标数据")

            else:
                st.error("❌ 未能成功获取股票数据，请检查：")
                st.error("1. 股票代码格式是否正确（如：AAPL, 0700.HK, 600519.SS）")
                st.error("2. 网络连接是否正常")
                st.error("3. 该股票是否在交易时间")

    st.divider()
    st.caption("🚀 本应用由 AI 驱动，仅供学习参考，不构成投资建议。")


if __name__ == "__main__":
    main()