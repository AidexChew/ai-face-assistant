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
                mood = "📈 强势上涨"
                price_range = f"{latest['Close'] * 0.95:.2f} - {latest['Close'] * 1.05:.2f}"
                future_trend = "短期看涨"
            elif ma5 < ma20 < ma50:
                mood = "📉 弱势下跌"
                price_range = f"{latest['Close'] * 0.85:.2f} - {latest['Close'] * 0.95:.2f}"
                future_trend = "短期看跌"
            else:
                mood = "⚖️ 震荡整理"
                price_range = f"{latest['Close'] * 0.9:.2f} - {latest['Close'] * 1.1:.2f}"
                future_trend = "横盘或微幅波动"
        else:
            mood = "数据不足，无法分析"

        return mood, price_range, future_trend

    except Exception as e:
        return "错误", "暂无", "无法预测"

# ========== 主程序入口 ==========
def main():
    st.set_page_config(
        page_title="咧啊，股神", 
        page_icon="📈", 
        layout="centered",
        initial_sidebar_state="collapsed"
    )

    # 标题区域
    st.title("📊 咧啊，股神")
    st.markdown("输入股票代码（示例：`AAPL`, `TSLA`, `0700.HK`, `600519.SS`）")
    st.divider()

    # 输入区域 - 直接输入后回车查询
    ticker = st.text_input(
        "请输入股票代码：", 
        "AAPL",
        help="输入后按回车键开始分析"
    )

    # 自动触发分析（去掉按钮）
    if ticker:
        with st.spinner("正在获取数据并分析，请稍候..."):
            df, ticker_used = get_stock_data(ticker)

            if df is not None and not df.empty:
                st.subheader(f"📈 {ticker_used} 分析结果")
                
                # 分析股票
                mood, price_range, future_trend = analyze_stock(df)
                
                # 高亮显示分析结果 - 使用彩色卡片布局
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # 当前行情情绪卡片
                    if "上涨" in mood:
                        color_style = "background: linear-gradient(135deg, #d4edda, #c3e6cb); border-left: 4px solid #28a745;"
                    elif "下跌" in mood:
                        color_style = "background: linear-gradient(135deg, #f8d7da, #f5c6cb); border-left: 4px solid #dc3545;"
                    else:
                        color_style = "background: linear-gradient(135deg, #fff3cd, #ffeaa7); border-left: 4px solid #ffc107;"
                    
                    st.markdown(
                        f"""
                        <div style="{color_style} padding: 15px; border-radius: 8px; margin: 10px 0;">
                            <h4 style="margin: 0 0 8px 0; font-size: 14px; color: #555;">当前行情情绪</h4>
                            <p style="margin: 0; font-size: 16px; font-weight: bold;">{mood}</p>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                
                with col2:
                    st.markdown(
                        f"""
                        <div style="background: linear-gradient(135deg, #d1ecf1, #bee5eb); padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #17a2b8;">
                            <h4 style="margin: 0 0 8px 0; font-size: 14px; color: #555;">建议买入价区间</h4>
                            <p style="margin: 0; font-size: 16px; font-weight: bold;">{price_range}</p>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                
                with col3:
                    st.markdown(
                        f"""
                        <div style="background: linear-gradient(135deg, #e2e3e5, #d6d8db); padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #6c757d;">
                            <h4 style="margin: 0 0 8px 0; font-size: 14px; color: #555;">未来趋势预测</h4>
                            <p style="margin: 0; font-size: 16px; font-weight: bold;">{future_trend}</p>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                
                st.divider()
                
                # 最近行情趋势图 - 移到分析结果下面
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