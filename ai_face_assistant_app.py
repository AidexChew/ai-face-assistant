# ai_face_assistant_app.py
import streamlit as st
import pandas as pd
import numpy as np
import akshare as ak
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

st.set_page_config(page_title="厉害了，股神", page_icon="📈", layout="centered")

# ---------------------
# 股票市场识别函数
# ---------------------
def identify_market(stock_code):
    """
    自动识别股票代码所属的市场
    返回: market_type, normalized_code
    market_type: 'A' (A股), 'H' (港股), 'US' (美股)
    """
    code = str(stock_code).strip().upper()
    
    # 美股识别（字母代码）
    if code.isalpha():
        return 'US', code
    
    # 纯数字代码识别
    if code.isdigit():
        # A股: 6位数字
        if len(code) == 6:
            return 'A', code
        # 港股: 1-5位数字，补足到5位
        elif 1 <= len(code) <= 5:
            return 'H', code.zfill(5)
    
    # 默认按A股处理
    return 'A', code

# ---------------------
# 辅助：尝试获取中文名（容错）- 扩展支持港股美股
# ---------------------
def safe_get_cn_name(stock_code, market_type):
    """
    根据市场类型获取股票名称
    """
    try:
        if market_type == 'A':
            # A股名称获取
            info = ak.stock_individual_info_em(symbol=stock_code)
            if "item" in info.columns and "value" in info.columns:
                row = info.loc[info["item"] == "股票简称"]
                if not row.empty:
                    return row["value"].values[0]
        elif market_type == 'H':
            # 港股名称获取
            try:
                hk_spot = ak.stock_hk_spot()
                if stock_code in hk_spot['代码'].values:
                    name_row = hk_spot[hk_spot['代码'] == stock_code]
                    if not name_row.empty:
                        return name_row['名称'].values[0]
            except:
                pass
        elif market_type == 'US':
            # 美股名称获取
            try:
                us_spot = ak.stock_us_spot()
                if stock_code in us_spot['代码'].values:
                    name_row = us_spot[us_spot['代码'] == stock_code]
                    if not name_row.empty:
                        return name_row['名称'].values[0]
            except:
                pass
        
        return stock_code
    except Exception:
        return stock_code

# ---------------------
# 统一的数据获取函数 - 支持A股、港股、美股
# ---------------------
def get_stock_data(stock_code):
    """
    从akshare获取股票历史数据，支持A股、港股、美股
    """
    try:
        # 识别市场类型
        market_type, normalized_code = identify_market(stock_code)
        
        # 取最近180天数据
        end_date = datetime.today().strftime("%Y%m%d")
        start_date = (datetime.today() - timedelta(days=180)).strftime("%Y%m%d")
        
        df = None
        
        # 根据不同市场调用不同的akshare接口
        if market_type == 'A':
            # A股数据获取
            try:
                df = ak.stock_zh_a_hist(symbol=normalized_code, period="daily", 
                                      start_date=start_date, end_date=end_date, adjust="qfq")
            except Exception as e:
                st.error(f"A股数据获取失败: {e}")
                return None, safe_get_cn_name(normalized_code, market_type)
                
        elif market_type == 'H':
            # 港股数据获取[7,8](@ref)
            try:
                df = ak.stock_hk_hist(symbol=normalized_code, period="daily",
                                    start_date=start_date, end_date=end_date, adjust="qfq")
            except Exception as e:
                st.error(f"港股数据获取失败: {e}")
                return None, safe_get_cn_name(normalized_code, market_type)
                
        elif market_type == 'US':
            # 美股数据获取[4](@ref)
            try:
                df = ak.stock_us_hist(symbol=normalized_code, period="daily", 
                                    start_date=start_date, end_date=end_date, adjust="qfq")
            except Exception as e:
                st.error(f"美股数据获取失败: {e}")
                return None, safe_get_cn_name(normalized_code, market_type)
        
        if df is None or df.empty:
            st.warning(f"未获取到 {normalized_code} 的历史行情数据。")
            return None, safe_get_cn_name(normalized_code, market_type)
        
        # 数据预处理和标准化
        df = preprocess_dataframe(df, market_type)
        
        if df is None:
            return None, safe_get_cn_name(normalized_code, market_type)
            
        # 计算技术指标
        df = calculate_technical_indicators(df)
        
        # 获取股票名称
        cn_name = safe_get_cn_name(normalized_code, market_type)
        
        # 添加市场标识
        market_symbol = {'A': '.SS/SZ', 'H': '.HK', 'US': ''}[market_type]
        display_code = f"{normalized_code}{market_symbol}"
        
        return df, f"{cn_name} ({display_code})"
        
    except Exception as e:
        st.error(f"获取股票数据失败: {repr(e)}")
        return None, stock_code

def preprocess_dataframe(df, market_type):
    """统一处理不同市场返回的数据框"""
    df = df.copy()
    
    # 统一列名映射
    col_map = {}
    for col in df.columns:
        col_str = str(col).lower()
        if any(x in col_str for x in ['日期', 'date']):
            col_map[col] = "Date"
        elif any(x in col_str for x in ['开盘', 'open']):
            col_map[col] = "Open"
        elif any(x in col_str for x in ['收盘', 'close']):
            col_map[col] = "Close"
        elif any(x in col_str for x in ['最高', 'high']):
            col_map[col] = "High"
        elif any(x in col_str for x in ['最低', 'low']):
            col_map[col] = "Low"
        elif any(x in col_str for x in ['成交量', 'volume', '交易量']):
            col_map[col] = "Volume"
        elif any(x in col_str for x in ['成交额', 'amount', '交易额']):
            col_map[col] = "Amount"
    
    if col_map:
        df.rename(columns=col_map, inplace=True)
    
    # 处理日期列
    if "Date" in df.columns:
        try:
            df["Date"] = pd.to_datetime(df["Date"])
        except:
            pass
    elif isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index().rename(columns={"index": "Date"})
    
    # 确保有Close列
    if "Close" not in df.columns:
        st.error(f"数据中缺少Close列，可用列: {list(df.columns)}")
        return None
    
    # 按日期排序并取最近120天
    if "Date" in df.columns:
        df = df.sort_values("Date").tail(120).reset_index(drop=True)
    else:
        df = df.tail(120).copy()
    
    # 数值列转换
    numeric_cols = ["Close", "Open", "High", "Low", "Volume", "Amount"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    
    return df

def calculate_technical_indicators(df):
    """计算技术指标"""
    # 移动平均线
    df["MA5"] = df["Close"].rolling(window=5, min_periods=1).mean()
    df["MA20"] = df["Close"].rolling(window=20, min_periods=1).mean()
    df["MA50"] = df["Close"].rolling(window=50, min_periods=1).mean()
    
    # MACD
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["DIF"] = ema12 - ema26
    df["DEA"] = df["DIF"].ewm(span=9, adjust=False).mean()
    df["MACD"] = 2 * (df["DIF"] - df["DEA"])
    
    return df

# ---------------------
# 趋势判断与分析（保持原风格）
# ---------------------
def analyze_stock(df):
    try:
        if df is None or df.empty:
            return "暂无数据", "暂无买入区间", "无法判断趋势"

        latest = df.iloc[-1]
        ma5 = latest.get("MA5", np.nan)
        ma20 = latest.get("MA20", np.nan)
        ma50 = latest.get("MA50", np.nan)
        current_price = latest.get("Close", np.nan)

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

        # 三种情形（保持你的表达风格）
        if ma5 > ma20 and ma20 > ma50:
            mood = "🚀 牛气冲天！主力资金强势介入，短期倾向上涨。"
            price_range = f"{current_price * 0.95:.2f} - {current_price * 1.05:.2f}"
            future_trend = "短期看涨概率较高"
        elif ma5 < ma20 and ma20 < ma50:
            mood = "💸 空头占优，行情承压，建议谨慎观望。"
            price_range = f"{current_price * 0.85:.2f} - {current_price * 0.95:.2f}"
            future_trend = "短期看跌概率较高"
        else:
            mood = "🎢 震荡整理，短线方向不明，适合高抛低吸。"
            price_range = f"{current_price * 0.9:.2f} - {current_price * 1.1:.2f}"
            future_trend = "短期震荡概率较高"

        return mood, price_range, future_trend

    except Exception as e:
        st.error(f"分析出错: {repr(e)}")
        return "错误", "暂无", "无法预测"

# ---------------------
# 绘图（价格/均线 + 成交量 + MACD）
# ---------------------
def plot_stock_charts(df, display_name):
    st.subheader(f"📊 {display_name} - 趋势图 & 指标")

    if "Date" in df.columns:
        x = df["Date"]
    else:
        x = df.index

    # 价格与均线
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(x, df["Close"], label="收盘价", color="black", linewidth=1)
    if "MA5" in df.columns: ax1.plot(x, df["MA5"], label="MA5", color="orange", linewidth=0.8)
    if "MA20" in df.columns: ax1.plot(x, df["MA20"], label="MA20", color="blue", linewidth=0.8)
    if "MA50" in df.columns: ax1.plot(x, df["MA50"], label="MA50", color="purple", linewidth=0.8)
    ax1.set_ylabel("价格")
    ax1.legend(loc="upper left")

    # 成交量
    ax2 = ax1.twinx()
    if "Volume" in df.columns:
        ax2.bar(x, df["Volume"], color="gray", alpha=0.3, label="成交量")
        ax2.set_ylabel("成交量")

    st.pyplot(fig)

    # MACD
    fig, ax = plt.subplots(figsize=(10, 3))
    if "DIF" in df.columns and "DEA" in df.columns and "MACD" in df.columns:
        ax.plot(x, df["DIF"], label="DIF", color="green")
        ax.plot(x, df["DEA"], label="DEA", color="red")
        colors = np.where(df["MACD"] >= 0, "r", "g")
        ax.bar(x, df["MACD"], color=colors, alpha=0.6)
        ax.set_title("MACD 指标")
        ax.legend()
        st.pyplot(fig)
    else:
        st.info("MACD 数据不足，无法绘制 MACD 图。")

# ---------------------
# 主界面
# ---------------------
def main():
    st.title("📈 厉害了，股神")
    st.markdown("""
    输入股票代码，支持：
    - ​**A股**: 6位数字代码，如 `600519` (贵州茅台), `000001` (平安银行)
    - ​**港股**: 1-5位数字代码，如 `00700` (腾讯), `09988` (阿里巴巴)
    - ​**美股**: 字母代码，如 `AAPL` (苹果), `TSLA` (特斯拉)
    """)

    col_desc, col_input = st.columns([2, 3])
    with col_desc:
        st.markdown("​**股票代码（支持A股/港股/美股）​**​")
    with col_input:
        code = st.text_input("请输入股票代码：", "600519", label_visibility="collapsed")

    st.divider()

    if code:
        with st.spinner("正在获取数据并分析..."):
            df, display_name = get_stock_data(code)

            if df is None:
                st.error("未能获取到数据，请检查：")
                st.error("1. 股票代码格式是否正确")
                st.error("2. 网络连接是否正常") 
                st.error("3. 该股票是否在交易时间")
                return

            mood, price_range, future_trend = analyze_stock(df)

            # 三列展示
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"​**当前行情情绪**​\n\n{mood}")
            c2.markdown(f"​**建议买入价区间**​\n\n{price_range}")
            c3.markdown(f"​**未来趋势预测**​\n\n{future_trend}")

            st.divider()

            # 图表
            plot_stock_charts(df, display_name)

            # 最近数据表
            st.subheader("📋 最近5个交易日数据")
            display_cols = [c for c in ["Date", "Close", "MA5", "MA20", "MA50", "Volume", "MACD"] if c in df.columns]
            if display_cols:
                df_display = df.tail(5)[display_cols]
                # 格式化数字显示
                formatted_df = df_display.copy()
                for col in formatted_df.columns:
                    if col != "Date" and pd.api.types.is_numeric_dtype(formatted_df[col]):
                        formatted_df[col] = formatted_df[col].round(2)
                st.dataframe(formatted_df, use_container_width=True)
            else:
                st.info("无可显示的列。")

    st.caption("仅供学习参考，不构成投资建议。")

if __name__ == "__main__":
    main()