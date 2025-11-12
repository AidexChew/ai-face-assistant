import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

# ========== 获取股票数据 ==========
def get_stock_data(ticker):
    try:
        # 使用Ticker对象而不是download，更稳定
        stock = yf.Ticker(ticker)
        df = stock.history(period="60d", interval="1d")
        
        if df.empty:
            st.warning(f"未找到股票 {ticker} 的数据，请检查代码是否正确")
            return None, None

        # 修复列名：如果是MultiIndex，转换为单级索引
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)  # 只取第一级列名
        
        df = df.sort_index(ascending=True)
        
        # 确保有足够数据计算移动平均
        if len(df) >= 5:
            df["MA5"] = df["Close"].rolling(window=5, min_periods=1).mean()
        if len(df) >= 20:
            df["MA20"] = df["Close"].rolling(window=20, min_periods=1).mean()
        if len(df) >= 50:
            df["MA50"] = df["Close"].rolling(window=50, min_periods=1).mean()

        return df, ticker
        
    except Exception as e:
        st.error(f"获取数据时出错: {str(e)}")
        return None, None

# ========== 安全的列检查函数 ==========
def get_available_columns(df, desired_columns):
    """返回DataFrame中实际存在的列名"""
    if df is None:
        return []
    return [col for col in desired_columns if col in df.columns]

# ========== 分析逻辑 ==========
def analyze_stock(df):
    try:
        if df is None or df.empty:
            return "数据不足", "暂无买入区间", "无法预测"
            
        latest = df.iloc[-1]

        # 安全地获取移动平均值，处理可能的NaN
        ma5 = latest["MA5"] if "MA5" in df.columns and pd.notna(latest["MA5"]) else None
        ma20 = latest["MA20"] if "MA20" in df.columns and pd.notna(latest["MA20"]) else None
        ma50 = latest["MA50"] if "MA50" in df.columns and pd.notna(latest["MA50"]) else None

        mood, price_range, future_trend = "未知", "暂无买入区间", "无法预测"

        # 检查是否有足够的有效数据进行分析
        if pd.notna(ma5) and pd.notna(ma20) and pd.notna(ma50):
            if ma5 > ma20 and ma20 > ma50:
                mood = "📈 强势上涨"
                price_range = f"{latest['Close'] * 0.95:.2f} - {latest['Close'] * 1.05:.2f}"
                future_trend = "短期看涨"
            elif ma5 < ma20 and ma20 < ma50:
                mood = "📉 弱势下跌"
                price_range = f"{latest['Close'] * 0.85:.2f} - {latest['Close'] * 0.95:.2f}"
                future_trend = "短期看跌"
            else:
                mood = "⚖️ 震荡整理"
                price_range = f"{latest['Close'] * 0.9:.2f} - {latest['Close'] * 1.1:.2f}"
                future_trend = "横盘或微幅波动"
        else:
            available_data = []
            if ma5 is not None: available_data.append("MA5")
            if ma20 is not None: available_data.append("MA20") 
            if ma50 is not None: available_data.append("MA50")
            
            if available_data:
                mood = f"数据部分缺失（已有{', '.join(available_data)}）"
            else:
                mood = "数据不足，无法计算移动平均线"

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

    # 添加自定义CSS样式来优化分析结果的显示
    st.markdown("""
    <style>
    .analysis-card {
        padding: 12px;
        border-radius: 8px;
        margin: 8px 0;
        border-left: 4px solid;
        background-color: #f8f9fa;
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
    .metric-label {
        font-size: 12px;
        color: #666;
        margin-bottom: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

    # 移除了按钮，改为直接通过文本输入触发查询
    ticker = st.text_input("请输入股票代码：", "AAPL", key="stock_input")
    
    # 当有输入时自动触发分析（去掉按钮）
    if ticker:
        with st.spinner("正在获取数据并分析，请稍候..."):
            df, ticker_used = get_stock_data(ticker)

            if df is not None and not df.empty:
                # 移除了过强的成功提示
                st.subheader(f"📈 {ticker_used} 分析结果")
                
                # 分析股票数据
                mood, price_range, future_trend = analyze_stock(df)
                
                # 使用三列布局高亮显示分析结果
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # 当前行情情绪卡片 - 使用更紧凑的布局
                    st.markdown(
                        f"""
                        <div class="analysis-card mood-card">
                            <div class="metric-label">当前行情情绪</div>
                            <div class="result-text">{mood}</div>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                
                with col2:
                    # 建议买入价区间卡片
                    st.markdown(
                        f"""
                        <div class="analysis-card price-card">
                            <div class="metric-label">建议买入价区间</div>
                            <div class="result-text">{price_range}</div>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                
                with col3:
                    # 未来趋势预测卡片
                    st.markdown(
                        f"""
                        <div class="analysis-card trend-card">
                            <div class="metric-label">未来趋势预测</div>
                            <div class="result-text">{future_trend}</div>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                
                st.divider()
                
                # 最近行情趋势图 - 移到分析结果下面，但在交易日数据之前
                st.subheader("📊 最近行情趋势")
                
                # 安全的图表绘制：只绘制存在的列
                desired_chart_columns = ["Close", "MA5", "MA20", "MA50"]
                columns_to_show = get_available_columns(df, desired_chart_columns)
                
                if columns_to_show:
                    st.line_chart(df[columns_to_show])
                else:
                    st.warning("⚠️ 没有可用的数据列来绘制图表")

                # 显示最近几天数据
                st.subheader("📋 最近5个交易日数据")
                display_columns = ["Close", "MA5", "MA20", "MA50"]
                available_display_cols = get_available_columns(df, display_columns)
                if available_display_cols:
                    recent_data = df.tail(5)[available_display_cols]
                    st.dataframe(recent_data.style.format("{:.2f}"), use_container_width=True)

            else:
                st.error("❌ 未能成功获取股票数据，请检查：")
                st.error("1. 股票代码格式是否正确（如：AAPL, 0700.HK, 600519.SS）")
                st.error("2. 网络连接是否正常")
                st.error("3. 该股票是否在交易时间")

    st.divider()
    st.caption("🚀 本应用由 AI 驱动，仅供学习参考，不构成投资建议。")

if __name__ == "__main__":
    main()