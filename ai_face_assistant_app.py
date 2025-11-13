# ai_face_assistant_app.py
import streamlit as st
import pandas as pd
import numpy as np
import akshare as ak
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

st.set_page_config(page_title="咧啊，股神", page_icon="📈", layout="centered")

# ---------------------
# 辅助：尝试获取中文名（容错）
# ---------------------
def safe_get_cn_name(stock_code):
    try:
        info = ak.stock_individual_info_em(symbol=stock_code)
        # info 是两列 (item, value)，我们查 "股票简称"
        if "item" in info.columns and "value" in info.columns:
            row = info.loc[info["item"] == "股票简称"]
            if not row.empty:
                return row["value"].values[0]
        # 兼容返回格式不同的情况
        if "股票简称" in info.values:
            # 最差情况，走默认
            return stock_code
        return stock_code
    except Exception:
        return stock_code

# ---------------------
# 更鲁棒的数据抓取函数
# ---------------------
def get_stock_data(stock_code):
    """
    从 akshare 获取 A 股历史数据，并标准化列名与计算指标。
    兼容 akshare 不同函数返回的列格式（中文/英文/索引不同）。
    """
    try:
        # 入参校验
        code = str(stock_code).strip()
        if not code or len(code) != 6:
            st.error("请输入6位A股代码，例如 600519 或 000001。")
            return None, None

        # 取最近 180 天数据
        end_date = datetime.today().strftime("%Y%m%d")
        start_date = (datetime.today() - timedelta(days=180)).strftime("%Y%m%d")

        # 首先尝试常用的接口（ak.stock_zh_a_hist），它通常返回含“日期”的中文列
        df = None
        try:
            df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
        except Exception:
            df = None

        # 如果没有数据，再尝试另一个接口 ak.stock_zh_a_daily（不同 akshare 版本可能存在）
        if df is None or df.empty:
            try:
                # ak.stock_zh_a_daily 有时返回以日期为索引，列名为小写 english
                df = ak.stock_zh_a_daily(symbol=code)
            except Exception:
                df = None

        if df is None or df.empty:
            st.warning(f"未获取到 {code} 的历史行情数据（akshare 可能未返回或网络异常）。")
            return None, safe_get_cn_name(code)

        # 现在我们已经有 df，但列名格式可能不同 —— 标准化它
        # 可能情况：
        # - 列为中文： '日期','开盘','收盘','最高','最低','成交量'
        # - 列为英文小写： 'date','open','close','high','low','volume'
        # - 列为英文大写： 'Date','Open','Close',...
        # 也可能是以日期为 index 而没有日期列
        df = df.copy()

        # 如果 DataFrame 的索引是 DatetimeIndex，但没有日期列，创建 Date 列
        if not any(c.lower() in ("日期", "date") for c in df.columns) and isinstance(df.index, pd.DatetimeIndex):
            df.reset_index(inplace=True)
            # 重命名 index 列名为 Date 或 date 视情况而定
            if "index" in df.columns:
                df.rename(columns={"index": "Date"}, inplace=True)

        # 标准化列名：map lower-case keys to known english/chinese names
        col_map = {}
        for col in df.columns:
            lc = str(col).lower()
            if lc in ("日期", "date"):
                col_map[col] = "Date"
            elif lc in ("开盘", "open"):
                col_map[col] = "Open"
            elif lc in ("收盘", "close"):
                col_map[col] = "Close"
            elif lc in ("最高", "high"):
                col_map[col] = "High"
            elif lc in ("最低", "low"):
                col_map[col] = "Low"
            elif lc in ("成交量", "volume"):
                col_map[col] = "Volume"
            elif lc in ("成交额", "amount"):
                col_map[col] = "Amount"
            # 其他列保留原名

        if col_map:
            df.rename(columns=col_map, inplace=True)

        # 有些接口把日期列叫 '日期' 且不是 datetime 类型，强转
        if "Date" in df.columns:
            try:
                df["Date"] = pd.to_datetime(df["Date"])
            except Exception:
                pass

        # 若依然没有 Date 列但 index 可转换为 datetime，则重置索引为 Date
        if "Date" not in df.columns and isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index().rename(columns={"index": "Date"})

        # 最后再检查必须存在的 Close 列
        if "Close" not in df.columns:
            # 输出列名以便调试
            st.error(f"获取A股数据失败: 返回的列中没有 Close 列（可用列：{list(df.columns)})")
            return None, safe_get_cn_name(code)

        # 确保按日期升序
        if "Date" in df.columns:
            df = df.sort_values("Date").reset_index(drop=True)
        else:
            df = df.sort_index(ascending=True)

        # 选择最近 120 天以内的数据（保证 MA 能算）
        if "Date" in df.columns:
            df = df.tail(120).copy()
        else:
            df = df.tail(120).copy()

        # Fill numeric conversion
        for col in ["Close", "Open", "High", "Low", "Volume", "Amount"]:
            if col in df.columns:
                # 转为数值
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # 计算 MA（容错，如果数据少也能计算 min_periods=1）
        df["MA5"] = df["Close"].rolling(window=5, min_periods=1).mean()
        df["MA20"] = df["Close"].rolling(window=20, min_periods=1).mean()
        df["MA50"] = df["Close"].rolling(window=50, min_periods=1).mean()

        # 计算 MACD（DIF/DEA/MACD柱）
        ema12 = df["Close"].ewm(span=12, adjust=False).mean()
        ema26 = df["Close"].ewm(span=26, adjust=False).mean()
        df["DIF"] = ema12 - ema26
        df["DEA"] = df["DIF"].ewm(span=9, adjust=False).mean()
        df["MACD"] = 2 * (df["DIF"] - df["DEA"])  # 以柱状表现

        # 获取中文名（尽量容错）
        cn_name = safe_get_cn_name(code)

        return df, cn_name

    except Exception as e:
        st.error(f"获取A股数据失败: {repr(e)}")
        # 在失败时返回 None，同时尽量返回中文名
        return None, safe_get_cn_name(stock_code)

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

        # 如果任一均线为 NaN，则提示数据不足
        if pd.isna(ma5) or pd.isna(ma20) or pd.isna(ma50):
            # check which exist
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
def plot_stock_charts(df, cn_name, code):
    st.subheader(f"📊 {cn_name} ({code}) - 趋势图 & 指标")

    # 保证 Date 在列中或索引是 DatetimeIndex
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

    # 成交量 使用双轴显示
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
    st.title("📈 咧啊，股神（A股版）")
    st.markdown("输入 6 位 A 股代码，例如 `600519`、`000001`，获取行情、均线、成交量与 MACD 指标。")

    col_desc, col_input = st.columns([2, 3])
    with col_desc:
        st.markdown("**股票代码（A股）**")
    with col_input:
        code = st.text_input("请输入 A 股代码：", "600519", label_visibility="collapsed")

    st.divider()

    if code:
        with st.spinner("正在获取数据并分析..."):
            df, cn_name = get_stock_data(code)

            if df is None:
                st.error("未能获取到数据，请稍后重试或检查代码是否正确。")
                return

            mood, price_range, future_trend = analyze_stock(df)

            # 三列展示（保持原风格）
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**当前行情情绪**\n\n{mood}")
            c2.markdown(f"**建议买入价区间**\n\n{price_range}")
            c3.markdown(f"**未来趋势预测**\n\n{future_trend}")

            st.divider()

            # 图表
            plot_stock_charts(df, cn_name, code)

            # 最近数据表
            st.subheader("📋 最近5个交易日数据")
            display_cols = [c for c in ["Date", "Close", "MA5", "MA20", "MA50", "Volume", "MACD"] if c in df.columns]
            if display_cols:
                df_display = df.tail(5)[display_cols]
                st.dataframe(df_display.style.format(na_rep="-", formatter={col: "{:.2f}" for col in df_display.columns if col not in ["Date"]}), use_container_width=True)
            else:
                st.info("无可显示的列。")

    st.caption("仅供学习参考，不构成投资建议。")

if __name__ == "__main__":
    main()
