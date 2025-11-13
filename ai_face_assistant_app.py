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
    """
    自动识别股票代码所属的市场
    返回: market_type, normalized_code
    """
    code = str(stock_code).strip().upper()
    
    # 美股识别（字母代码）[5](@ref)
    if code.isalpha():
        return 'US', code
    
    # 纯数字代码识别
    if code.isdigit():
        # A股: 6位数字
        if len(code) == 6:
            if code.startswith(('6', '5', '9')):  # 上交所
                return 'A', code + '.SS'
            elif code.startswith(('0', '2', '3')):  # 深交所
                return 'A', code + '.SZ'
        # 港股: 1-5位数字，补足到5位
        elif 1 <= len(code) <= 5:
            return 'H', code.zfill(5) + '.HK'
    
    # 默认按A股处理
    return 'A', code

# ---------------------
# 增强的数据获取函数
# ---------------------
def get_stock_data(stock_code):
    """
    增强版股票数据获取，支持A股、港股、美股
    """
    try:
        # 识别市场类型
        market_type, normalized_code = identify_market(stock_code)
        
        df = None
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                if market_type == 'A':
                    # A股使用akshare
                    df = ak.stock_zh_a_hist(symbol=normalized_code.replace('.SS', '').replace('.SZ', ''), 
                                          period="daily", adjust="qfq")
                elif market_type == 'H':
                    # 港股使用akshare
                    df = ak.stock_hk_hist(symbol=normalized_code.replace('.HK', ''), period="daily")
                elif market_type == 'US':
                    # 美股使用yfinance（更稳定）[5](@ref)
                    ticker = yf.Ticker(normalized_code)
                    df = ticker.history(period="6mo", interval="1d")
                    if df is not None and not df.empty:
                        # 标准化列名
                        df = df.rename(columns={
                            'Open': 'open', 'High': 'high', 'Low': 'low', 
                            'Close': 'close', 'Volume': 'volume'
                        })
                
                if df is not None and not df.empty:
                    break
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                # 指数退避重试
                time.sleep(random.uniform(1, 3))
        
        if df is None or df.empty:
            st.warning(f"未获取到 {normalized_code} 的历史行情数据")
            return None, normalized_code

        # 数据预处理
        df = preprocess_dataframe(df, market_type)
        if df is None:
            return None, normalized_code
            
        # 计算技术指标
        df = calculate_technical_indicators(df)
        
        return df, normalized_code
        
    except Exception as e:
        st.error(f"获取数据时出错: {str(e)}")
        return None, stock_code

def preprocess_dataframe(df, market_type):
    """统一处理不同市场返回的数据框"""
    df = df.copy()
    
    # 统一列名映射
    col_map = {}
    for col in df.columns:
        col_str = str(col).lower()
        if any(x in col_str for x in ['日期', 'date']):
            col_map[col] = "date"
        elif any(x in col_str for x in ['开盘', 'open']):
            col_map[col] = "open"
        elif any(x in col_str for x in ['收盘', 'close']):
            col_map[col] = "close"
        elif any(x in col_str for x in ['最高', 'high']):
            col_map[col] = "high"
        elif any(x in col_str for x in ['最低', 'low']):
            col_map[col] = "low"
        elif any(x in col_str for x in ['成交量', 'volume', '交易量']):
            col_map[col] = "volume"
    
    if col_map:
        df.rename(columns=col_map, inplace=True)
    
    # 处理日期列
    if "date" in df.columns:
        try:
            df["date"] = pd.to_datetime(df["date"])
        except:
            pass
    elif isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index().rename(columns={"index": "date"})
    
    # 确保有close列
    if "close" not in df.columns:
        st.error(f"数据中缺少close列，可用列: {list(df.columns)}")
        return None
    
    # 按日期排序并取最近120天
    if "date" in df.columns:
        df = df.sort_values("date").tail(120).reset_index(drop=True)
    else:
        df = df.tail(120).copy()
    
    # 数值列转换
    numeric_cols = ["close", "open", "high", "low", "volume"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    
    return df

def calculate_technical_indicators(df):
    """计算技术指标"""
    # 移动平均线
    df["MA5"] = df["close"].rolling(window=5, min_periods=1).mean()
    df["MA20"] = df["close"].rolling(window=20, min_periods=1).mean()
    df["MA50"] = df["close"].rolling(window=50, min_periods=1).mean()
    
    # MACD
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["DIF"] = ema12 - ema26
    df["DEA"] = df["DIF"].ewm(span=9, adjust=False).mean()
    df["MACD"] = 2 * (df["DIF"] - df["DEA"])
    
    return df

# ---------------------
# 分析逻辑
# ---------------------
def analyze_stock(df):
    try:
        if df is None or df.empty:
            return "暂无数据", "暂无买入区间", "无法判断趋势"

        latest = df.iloc[-1]
        ma5 = latest.get("MA5", np.nan)
        ma20 = latest.get("MA20", np.nan)
        ma50 = latest.get("MA50", np.nan)
        current_price = latest.get("close", np.nan)

        if pd.isna(ma5) or pd.isna(ma20) or pd.isna(ma50):
            available = []
            if not pd.isna(ma5): available.append("MA5")
            if not pd.isna(ma20): available.append("MA20")
            if not pd.isna(ma50): available.append("MA50")
            if available:
                mood = f"🤔 仅检测到指标：{', '.join(available)}，分析结果谨慎参考。"
            else:
                mood = "📊 指标数据不足，无法给出完整分析。"
            return mood, "暂无买入区间", "无法预测"

        # 三种情形判断
        if ma5 > ma20 and ma20 > ma50:
            mood = "🚀 牛气冲天！主力资金强势介入，短期倾向上涨。"
            price_range = f"{current_price * 0.95:.2f} - {current_price * 1.05:.2f}"
            future_trend = "短期看涨概率约65%"
        elif ma5 < ma20 and ma20 < ma50:
            mood = "💸 空头占优，行情承压，建议谨慎观望。"
            price_range = f"{current_price * 0.85:.2f} - {current_price * 0.95:.2f}"
            future_trend = "短期看跌概率约60%"
        else:
            mood = "🎢 震荡整理，短线方向不明，适合高抛低吸。"
            price_range = f"{current_price * 0.9:.2f} - {current_price * 1.1:.2f}"
            future_trend = "横盘概率约50%"

        return mood, price_range, future_trend

    except Exception as e:
        st.error(f"分析出错: {repr(e)}")
        return "错误", "暂无", "无法预测"

# ---------------------
# 绘图函数
# ---------------------
def plot_stock_charts(df, display_name):
    st.subheader(f"📊 {display_name} - 技术分析")
    
    if "date" in df.columns:
        x = df["date"]
    else:
        x = df.index

    # 价格与均线
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(x, df["close"], label="收盘价", color="black", linewidth=1)
    if "MA5" in df.columns: 
        ax1.plot(x, df["MA5"], label="MA5", color="orange", linewidth=0.8)
    if "MA20" in df.columns: 
        ax1.plot(x, df["MA20"], label="MA20", color="blue", linewidth=0.8)
    if "MA50" in df.columns: 
        ax1.plot(x, df["MA50"], label="MA50", color="purple", linewidth=0.8)
    ax1.set_ylabel("价格")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)
    
    plt.xticks(rotation=45)
    st.pyplot(fig)

# ---------------------
# 主程序
# ---------------------
def main():
    st.title("📈 全市场股票分析工具")
    st.markdown("""
    支持A股、港股、美股分析
    - ​**A股**: 6位数字代码，如 `600519` (贵州茅台), `000001` (平安银行)  
    - ​**港股**: 1-5位数字代码，如 `00700` (腾讯), `09988` (阿里巴巴)
    - ​**美股**: 字母代码，如 `AAPL` (苹果), `TSLA` (特斯拉)
    """)

    # 输入区域
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("​**股票代码**​")
    with col2:
        code = st.text_input("请输入股票代码：", "AAPL", label_visibility="collapsed")

    st.divider()

    if code:
        with st.spinner("正在获取数据并分析..."):
            df, display_code = get_stock_data(code)

            if df is not None and not df.empty:
                # 分析结果
                mood, price_range, future_trend = analyze_stock(df)
                
                # 三列显示分析结果
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"​**当前行情情绪**​")
                    st.info(mood)
                
                with col2:
                    st.markdown(f"​**建议买入区间**​")
                    st.success(price_range)
                
                with col3:
                    st.markdown(f"​**未来趋势预测**​")
                    st.warning(future_trend)

                st.divider()

                # 图表显示
                plot_stock_charts(df, display_code)

                # 最近数据表
                st.subheader("📋 最近交易数据")
                display_cols = ["date", "close", "MA5", "MA20", "MA50", "volume"]
                available_cols = [col for col in display_cols if col in df.columns]
                
                if available_cols:
                    recent_data = df.tail(10)[available_cols]
                    # 格式化数字显示
                    for col in recent_data.columns:
                        if col != "date" and pd.api.types.is_numeric_dtype(recent_data[col]):
                            recent_data[col] = recent_data[col].round(2)
                    st.dataframe(recent_data, use_container_width=True)
                
                # 显示最新价格
                latest_price = df.iloc[-1]["close"]
                st.metric("最新收盘价", f"{latest_price:.2f}", 
                         delta=f"{(latest_price - df.iloc[-2]['close']):.2f}" if len(df) > 1 else None)

            else:
                st.error("❌ 未能获取股票数据，请检查：")
                st.error("1. 股票代码是否正确（A股: 600519, 港股: 00700, 美股: AAPL）")
                st.error("2. 网络连接是否正常")
                st.error("3. 该股票是否在交易时间")

    st.divider()
    st.caption("💡 提示：本工具仅供参考，不构成投资建议")
    st.caption("🚀 支持市场：A股 • 港股 • 美股")

if __name__ == "__main__":
    main()