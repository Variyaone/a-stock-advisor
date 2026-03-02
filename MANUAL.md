# A股量化系统完整手册

## 目录

1. [系统概述](#1-系统概述)
2. [数据工程](#2-数据工程)
3. [因子体系](#3-因子体系)
4. [策略体系](#4-策略体系)
5. [回测系统](#5-回测系统)
6. [实盘工程](#6-实盘工程)
7. [运维指南](#7-运维指南)
8. [待办事项与改进路线图](#8-待办事项与改进路线图)

---

## 1. 系统概述

### 1.1 系统目标

本A股量化系统旨在构建一个完整的多因子量化选股和策略执行框架，实现从数据获取、因子挖掘、策略研发到实盘交易的全流程自动化。系统的核心理念是**从"寻找圣杯"到"管理不确定性"**，通过系统的工程化方法管理量化投资中的各种不确定性。

### 1.2 核心理念

系统设计遵循以下核心理念：

**五阶段框架**：
1. **数据工程** - 确保数据质量，建立数据管道
2. **模型研发** - 因子挖掘与策略开发
3. **回测验证** - 严格验证策略有效性
4. **实盘工程** - 模拟盘与风控体系
5. **监控迭代** - 持续监控与优化

**管理不确定性**：
- 不追求完美的预测模型，而是构建鲁棒的系统
- 通过分散化、风险控制、持续监控来管理风险
- 接受策略的周期性波动，但确保长期正期望

### 1.3 当前状态与已知问题

#### ✅ 已完成的成果

1. **因子库（80+因子）** - 覆盖基本面、技术面、情绪、另类数据
2. **策略库（5大类策略）** - 趋势跟踪、均值回归、因子轮动、行业轮动、事件驱动
3. **RDagent分析方法** - 自动化因子挖掘方法论
4. **过拟合检测** - 发现中度过拟合风险
5. **监控系统** - 基础监控框架已搭建

#### ⚠️ 已知问题

**P0级问题（必须解决）**：

1. **数据质量问题** 🔴
   - 当前的 `data/mock_data.pkl` 是标准化合成数据，非真实A股数据
   - 单日最大涨幅852%（A股限制±10%）
   - 股价出现负值
   - 回测结果（年化收益率317%）不可信

2. **过拟合风险** 🔴
   - IC衰减检测显示：debt_ratio_20d的IC衰减率达18.20%
   - 参数敏感性测试：6/6因子对参数变化高度敏感
   - 样本外夏普比率仅0.25，远低于样本内0.99

3. **交易成本未考虑** 🔴
   - 回测未计算印花税、佣金、滑点
   - 预期年化成本影响：0.5-1.5%

**P1级问题（应尽快解决）**：

1. **策略容量未知** - 未评估最大资金容量和冲击成本
2. **行业过度集中** - 选股结果集中在特定行业
3. **流动性风险** - 未对小盘股流动性压力进行充分测试
4. **样本外验证不足** - 数据时间跨度和样本量有限

#### 📊 当前评估

| 维度 | 状态 | 说明 |
|-----|------|------|
| **数据质量** | 🔴 不可用 | 需替换为真实行情数据 |
| **因子体系** | 🟢 完整 | 80+因子覆盖全面 |
| **策略体系** | 🟢 完整 | 5大类策略库建立 |
| **回测系统** | 🟡 部分可用 | 框架完整但数据错误 |
| **实盘工程** | 🔴 未实施 | 尚未搭建模拟盘 |
| **监控系统** | 🟡 框架搭建 | 基础监控已实现 |

---

## 2. 数据工程

### 2.1 数据源说明

#### 2.1.1 基础行情数据

**必选数据源**（推荐按优先级排序）：

1. **Tushare Pro** ⭐⭐⭐⭐⭐
   - 官网：https://tushare.pro
   - 数据质量：高
   - 免费/付费：积分制（免费额度充足）
   - 更新频率：日度/实时
   - 推荐原因：数据最完整，接口文档清晰

2. **AKShare** ⭐⭐⭐⭐
   - 官网：https://akshare.akfamily.xyz
   - 数据质量：高
   - 免费/付费：完全免费
   - 更新频率：日度
   - 推荐原因：开源免费，覆盖面广

3. **Baostock** ⭐⭐⭐
   - 官网：http://baostock.com
   - 数据质量：中
   - 免费/付费：完全免费
   - 更新频率：日度
   - 推荐原因：适合学习，数据量相对较少

#### 2.1.2 财务数据

必选字段：
- `ts_code` - 股票代码
- `trade_date` - 交易日期
- `close` - 收盘价（前复权）
- `open` - 开盘价
- `high` - 最高价
- `low` - 最低价
- `volume` - 成交量
- `amount` - 成交额
- `turnover_rate` - 换手率

#### 2.1.3 财务数据

季度/年度数据：
- 利润表：营业总收入、净利润、营业利润
- 资产负债表：总资产、总负债、净资产
- 现金流量表：经营现金流净额

#### 2.1.4 另类数据

可选数据：
- 分析师研报与评级
- 北向资金流向
- 融资融券余额
- 机构持仓数据
- 舆情数据（新闻、社交媒体）

### 2.2 数据获取方式

#### 2.2.1 Tushare获取示例

```python
import tushare as ts

# 初始化
ts.set_token('your_token_here')
pro = ts.pro_api()

# 获取日线行情
df = pro.daily(
    ts_code='000001.SZ',
    start_date='20190101',
    end_date='20240101',
    fields='ts_code,trade_date,open,high,low,close,vol,amount'
)

# 获取财务指标
df_fin = pro.fina_indicator(
    ts_code='000001.SZ',
    start_date='20190101',
    end_date='20240101',
    fields='ts_code,end_date,roe,roa,eps,debt_to_assets,turnover_ratio'
)

# 获取股票列表
stock_list = pro.stock_basic(
    exchange='',
    list_status='L',
    fields='ts_code,symbol,name,area,industry,list_date'
)
```

#### 2.2.2 AKShare获取示例

```python
import akshare as ak

# 获取个股历史行情
df = ak.stock_zh_a_hist(
    symbol='000001',
    period='daily',
    start_date='20190101',
    end_date='20240101',
    adjust='qfq'  # 前复权
)

# 获取财务指标
df_fin = ak.stock_financial_analysis_indicator(
    symbol='000001',
    indicator='ROE'
)

# 获取全市场列表
stock_list = ak.stock_info_a_code_name()
```

### 2.3 数据质量要求

#### 2.3.1 必检指标

实现以下数据质量检查：

```python
def validate_data(df):
    """数据质量验证函数"""

    checks = []

    # 1. 单日涨跌幅检查（A股±10%）
    df['pct_change'] = df['close'].pct_change()
    max_single_day_change = df['pct_change'].abs().max()
    if max_single_day_change > 0.11:  # 允许0.01误差
        checks.append(f"❌ 单日涨跌幅异常: {max_single_day_change:.2%}")
    else:
        checks.append(f"✅ 单日涨跌幅正常: {max_single_day_change:.2%}")

    # 2. 价格非负检查
    if (df['close'] <= 0).any():
        negative_count = (df['close'] <= 0).sum()
        checks.append(f"❌ 发现负值价格: {negative_count}条")
    else:
        checks.append("✅ 价格均为正值")

    # 3. 成交量非负检查
    if (df['volume'] < 0).any():
        checks.append("❌ 发现负成交量")
    else:
        checks.append("✅ 成交量均为非负")

    # 4. 价格波动合理性检查
    price_std = df['close'].std()
    price_mean = df['close'].mean()
    volatility_ratio = price_std / price_mean
    if volatility_ratio > 1.0:
        checks.append(f"❌ 波动率异常: {volatility_ratio:.2f}")
    else:
        checks.append(f"✅ 波动率正常: {volatility_ratio:.2f}")

    # 5. 数据完整性检查
    missing_ratio = df.isnull().sum().sum() / (df.shape[0] * df.shape[1])
    if missing_ratio > 0.01:
        checks.append(f"⚠️ 缺失值比例: {missing_ratio:.2%}")
    else:
        checks.append(f"✅ 数据完整度高: {missing_ratio:.2%}")

    return checks
```

#### 2.3.2 数据质量标准

| 指标 | 要求 | 说明 |
|-----|------|------|
| 单日涨跌幅 | ≤ ±10% | A股涨跌停限制，ST股±5% |
| 价格 | > 0 | 股价必须为正数 |
| 成交量 | ≥ 0 | 成交量不能为负 |
| 波动率/均价 | ≤ 1.0 | 防止极端标准化数据 |
| 缺失值比例 | < 1% | 数据完整性要求 |
| 时间连续性 | 工作日连续 | 需处理停牌日 |
| 复权一致性 | 前复权 | 确保价格可比 |

### 2.4 数据处理流程

#### 2.4.1 标准处理流程

```
原始数据 → 数据清洗 → 数据验证 → 数据存储
   ↓           ↓           ↓           ↓
获取行情   去除异常   质量检查   按日期存储
获取财务   填充缺失   异常报警   建立索引
```

#### 2.4.2 关键处理步骤

**1. 数据清洗**

```python
# 处理停牌日（价格无变化但成交量为0）
df.loc[df['volume'] == 0, 'close'] = df['close'].ffill()

# 处理除权除息
# 使用前复权数据避免人工复权

# 去除异常值（如单日超过±11%）
df = df[df['pct_change'].abs() <= 0.11]

# 填充缺失值
df = df.fillna(method='ffill').fillna(method='bfill')
```

**2. 数据标准化**

```python
from scipy import stats

# Z-score标准化（用于因子计算）
def standardize(series):
    """Z-score标准化"""
    return (series - series.mean()) / series.std()

# Rank标准化（用于排序）
def rank_normalize(series):
    """Rank标准化"""
    return series.rank(pct=True)

# 行业中性化
def industry_neutralize(factor, industry_group):
    """行业中性化"""
    factor_mean = factor.groupby(industry_group).transform('mean')
    factor_std = factor.groupby(industry_group).transform('std')
    return (factor - factor_mean) / factor_std
```

**3. 幸存者偏差处理**

问题：只留存当前上市股票会排除已退市股票，导致回测结果过拟合。

解决方案：
```python
# 1. 获取历史上市清单（包含已退市股票）
stock_list_historical = get_historical_stock_list(start_date, end_date)

# 2. 只保留在回测期间上市的股票
valid_stocks = [
    stock for stock in stock_list_historical
    if list_date <= backtest_start_date
]

# 3. 在每个时间点，只使用当时上市的股票
for date in date_range:
    available_stocks = get_stocks_listed_before(date)
    df = df[df['ts_code'].isin(available_stocks)]
```

**4. 未来函数处理**

问题：使用未来数据会导致回测结果虚假。

检测方法：
```python
def detect_look_ahead(factor_series, forward_returns):
    """
    检测是否存在未来函数
    因子不应与未来收益率有过于显著的相关性
    """
    correlation = factor_series.corr(forward_returns)

    # 如果相关系数异常高（>0.5），可能存在未来函数
    if abs(correlation) > 0.5:
        print(f"⚠️ 警告：可能存在未来函数，相关系数={correlation:.2f}")
        return False
    else:
        return True
```

常见未来函数：
- ❌ 使用当日收盘价作为因子
- ❌ 财务数据使用报告期而非公告期
- ❌ 技术指标使用未来数据点

正确做法：
- ✅ 使用因子时lag一个周期：`factor.shift(1)`
- ✅ 财务数据按公告日（而非报告期）对齐
- ✅ 技术指标基于历史数据

**5. 流动性过滤**

目的：排除流动性过差导致无法交易的股票。

```python
def filter_liquidity(df, min_daily_turnover=5000000):
    """流动性过滤

    Args:
        df: 数据框
        min_daily_turnover: 最小日均成交额（元）

    Returns:
        过滤后的数据框
    """
    # 计算日均成交额
    avg_turnover = df.groupby('ts_code')['amount'].apply(
        lambda x: x * df.loc[x.index, 'volume'].mean()
    )

    # 过滤
    liquid_stocks = avg_turnover[avg_turnover >= min_daily_turnover].index
    return df[df['ts_code'].isin(liquid_stocks)]

# 应用过滤
df = filter_liquidity(df, min_daily_turnover=10000000)  # 日均1000万以上
```

### 2.5 数据存储

#### 2.5.1 存储格式

推荐使用以下存储格式：

**1. CSV/Parquet (小规模)**
```python
# CSV（兼容性好）
df.to_csv('data/stock_prices.csv', index=False)

# Parquet（压缩率高，查询快）
df.to_parquet('data/stock_prices.parquet', engine='pyarrow')
```

**2. HDF5 (中等规模)**
```python
import pandas as pd

with pd.HDFStore('data/market_data.h5', mode='w') as store:
    store.put('prices', df, format='table')
    store.put('fundamentals', df_fin, format='table')
```

**3. 数据库（大规模）**
```python
# SQLite（本地）
import sqlite3
conn = sqlite3.connect('data/market.db')
df.to_sql('prices', conn, if_exists='replace', index=False)

# PostgreSQL/Mysql（生产环境）
from sqlalchemy import create_engine
engine = create_engine('postgresql://user:password@localhost/dbname')
df.to_sql('prices', engine, if_exists='replace', index=False)
```

#### 2.5.2 数据更新策略

```python
def update_data(df_new, df_existing, primary_key='ts_code', date_key='trade_date'):
    """增量更新数据

    Args:
        df_new: 新获取的数据
        df_existing: 已有数据
        primary_key: 主键
        date_key: 日期键
    """
    # 合并数据
    df_all = pd.concat([df_existing, df_new])

    # 去重（保留最新数据）
    df_all = df_all.drop_duplicates(
        subset=[primary_key, date_key],
        keep='last'
    )

    # 排序
    df_all = df_all.sort_values([primary_key, date_key])

    return df_all
```

---

## 3. 因子体系

### 3.1 因子分类说明

系统当前包含 **80+个因子**，按数据来源分为四大类：

| 大类 | 子类 | 因子数量 | 说明 |
|-----|------|---------|------|
| **基本面因子** | 估值因子 | 10 | PE、PB、PS、PCF、PEG等 |
| | 盈利能力因子 | 7 | ROE、ROA、ROIC、毛利率、净利率等 |
| | 成长性因子 | 5 | 营收增长、净利润增长、ROE增长等 |
| | 偿债能力因子 | 5 | 资产负债率、流动比率、速动比率等 |
| | 营运能力因子 | 5 | 存货周转、应收账款周转等 |
| **技术面因子** | 动量因子 | 10 | 20/60/120日动量、相对强度等 |
| | 反转因子 | 6 | RSI反转、MACD反转、偏离度等 |
| | 波动率因子 | 7 | 历史波动率、ATR、上行/下行波动率等 |
| | 流动性因子 | 7 | 换手率、Amihud非流动性、价差等 |
| **情绪因子** | 市场情绪 | 5 | 融资买入、融资余额、融资融券比等 |
| | 舆情情绪 | 5 | 新闻数量、情绪评分、搜索指数等 |
| **另类数据因子** | 分析师指标 | 5 | 覆盖度、目标价涨幅、评级变化等 |
| | 机构指标 | 3 | 机构持股、机构流向、北向资金 |

### 3.2 因子计算方法

#### 3.2.1 基本面因子计算

**估值因子**：

```python
def calculate_valuation_factors(df_fin, df_price):
    """计算估值因子"""
    factors = {}

    # PE (市盈率)
    factors['pe_ttm'] = df_price['close'] / df_fin['eps_ttm']

    # PB (市净率)
    factors['pb'] = df_price['close'] / df_fin['net_assets_per_share']

    # PS (市销率)
    factors['ps_ttm'] = df_price['close'] / df_fin['revenue_per_share_ttm']

    # PCF (市现率)
    factors['pcf_ttm'] = df_price['close'] / df_fin['operating_cf_per_share_ttm']

    # PEG (市盈增长率)
    revenue_growth = df_fin['revenue_yoy']
    factors['peg'] = factors['pe_ttm'] / (revenue_growth * 100)  # 转为百分比

    # 股息率
    factors['dividend_yield'] = df_fin['dividend_per_share'] / df_price['close']

    return pd.DataFrame(factors)
```

**盈利能力因子**：

```python
def calculate_profitability_factors(df_fin):
    """计算盈利能力因子"""
    factors = {}

    # ROE (净资产收益率)
    factors['roe'] = df_fin['roe']

    # ROA (总资产收益率)
    factors['roa'] = df_fin['roa']

    # ROIC (投入资本收益率)
    nopat = df_fin['operating_profit'] * (1 - df_fin['tax_rate'])
    invested_capital = df_fin['total_equity'] + df_fin['total_debt']
    factors['roic'] = nopat / invested_capital

    # 毛利率
    factors['gross_margin'] = (df_fin['revenue'] - df_fin['cost_of_goods_sold']) / df_fin['revenue']

    # 净利率
    factors['net_margin'] = df_fin['net_profit'] / df_fin['revenue']

    # 资产周转率
    factors['asset_turnover'] = df_fin['revenue'] / df_fin['total_assets']

    return pd.DataFrame(factors)
```

**成长性因子**：

```python
def calculate_growth_factors(df_fin):
    """计算成长性因子"""
    factors = {}

    # 营收增长率
    factors['revenue_growth'] = df_fin['revenue_yoy']  # 同比增长率

    # 净利润增长率
    factors['profit_growth'] = df_fin['net_profit_yoy']

    # ROE增长率
    factors['roe_growth'] = df_fin['roe'].pct_change(periods=4)  # 同比

    # 毛利率变化率
    factors['gross_margin_change'] = df_fin['gross_margin'].diff()

    # 总资产增长率
    factors['asset_growth'] = df_fin['total_assets'].pct_change(periods=4)

    return pd.DataFrame(factors)
```

#### 3.2.2 技术面因子计算

**动量因子**：

```python
def calculate_momentum_factors(df_price, windows=[5, 20, 60, 120]):
    """计算动量因子"""
    factors = {}

    for window in windows:
        # 价格动量
        factors[f'mom_{window}d'] = (
            df_price['close'] - df_price['close'].shift(window)
        ) / df_price['close'].shift(window)

    # 相对强度（个股 vs 市场）
    market_return = df_price['close'].mean(axis=1).pct_change()
    for window in windows:
        factors[f'rel_strength_{window}d'] = (
            df_price['close'].pct_change(window) / market_return.rolling(window).sum()
        )

    return pd.DataFrame(factors)
```

**反转因子**：

```python
def calculate_reversal_factors(df_price):
    """计算反转因子"""
    factors = {}

    # 5日反转
    factors['rev_5d'] = -df_price['close'].pct_change(5)

    # 20日反转
    factors['rev_20d'] = -df_price['close'].pct_change(20)

    # 偏离度
    ma20 = df_price['close'].rolling(20).mean()
    factors['deviation_ma20'] = (df_price['close'] - ma20) / ma20

    # 威廉指标
    high_max = df_price['high'].rolling(14).max()
    low_min = df_price['low'].rolling(14).min()
    factors['williams_r'] = -100 * (high_max - df_price['close']) / (high_max - low_min)

    return pd.DataFrame(factors)
```

**波动率因子**：

```python
def calculate_volatility_factors(df_price, windows=[20, 60]):
    """计算波动率因子"""
    factors = {}

    for window in windows:
        # 历史波动率（收益率标准差）
        returns = df_price['close'].pct_change()
        factors[f'vol_{window}d'] = returns.rolling(window).std()

        # 上行波动率
        up_returns = returns[returns > 0]
        factors[f'up_vol_{window}d'] = up_returns.rolling(window).std()

        # 下行波动率
        down_returns = returns[returns < 0]
        factors[f'down_vol_{window}d'] = down_returns.abs().rolling(window).std()

    # ATR (平均真实波幅)
    high_low = df_price['high'] - df_price['low']
    high_close = abs(df_price['high'] - df_price['close'].shift(1))
    low_close = abs(df_price['low'] - df_price['close'].shift(1))
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    factors['atr_14d'] = tr.rolling(14).mean()

    return pd.DataFrame(factors)
```

**流动性因子**：

```python
def calculate_liquidity_factors(df_price):
    """计算流动性因子"""
    factors = {}

    # 换手率
    factors['turnover_rate'] = df_price['volume'] / df_price['total_shares']

    # Amihud非流动性指标
    returns = df_price['close'].pct_change()
    factors['amihud'] = abs(returns) / df_price['amount']

    # 流通市值
    factors['float_market_cap'] = df_price['close'] * df_price['float_shares']

    # 买卖价差（proxy）
    factors['bid_ask_spread'] = (df_price['high'] - df_price['low']) / df_price['close']

    # 成交额占市值比
    factors['turnover_to_cap'] = df_price['amount'] / factors['float_market_cap']

    return pd.DataFrame(factors)
```

#### 3.2.3 情绪因子计算

```python
def calculate_sentiment_factors(df_sentiment):
    """计算情绪因子"""
    factors = {}

    # 融资买入额
    factors['margin_buy'] = df_sentiment['margin_buy_amount']

    # 融资余额
    factors['margin_balance'] = df_sentiment['margin_balance']

    # 融券余额
    factors['short_balance'] = df_sentiment['short_balance']

    # 融资融券比
    factors['margin_short_ratio'] = (
        df_sentiment['margin_balance'] / (df_sentiment['short_balance'] + 1e-6)
    )

    # 新闻数量
    factors['news_count'] = df_sentiment['news_count']

    # 新闻情绪评分（normalized）
    factors['news_sentiment'] = df_sentiment['news_sentiment_score']

    # 搜索指数
    factors['search_index'] = df_sentiment['search_index']

    return pd.DataFrame(factors)
```

#### 3.2.4 另类数据因子计算

```python
def calculate_alternative_factors(df_alt):
    """计算另类数据因子"""
    factors = {}

    # 分析师覆盖度
    factors['analyst_coverage'] = df_alt['analyst_count']

    # 目标价涨幅
    factors['target_price_rise'] = (
        df_alt['target_price'] - df_alt['current_price']
    ) / df_alt['current_price']

    # 评级变化（量化）
    rating_map = {'买入': 2, '增持': 1, '中性': 0, '减持': -1, '卖出': -2}
    factors['rating_change'] = df_alt['rating'].map(rating_map).diff()

    # 机构持仓比例
    factors['institution_holdings'] = df_alt['institution_holdings_ratio']

    # 机构资金流向
    factors['institution_flow'] = df_alt['institution_net_buy']

    # 北向资金持股
    factors['north_bound_holdings'] = df_alt['north_bound_holdings_ratio']

    return pd.DataFrame(factors)
```

### 3.3 因子评估标准

#### 3.3.1 IC（Information Coefficient）

IC衡量因子与未来收益率的相关性，范围[-1, 1]。

```python
def calculate_ic(factor, forward_return, method='spearman'):
    """计算IC值

    Args:
        factor: 因子值序列
        forward_return: 未来收益率序列
        method: 'pearson' 或 'spearman'

    Returns:
        IC值
    """
    if method == 'spearman':
        ic = factor.corr(forward_return, method='spearman')
    else:
        ic = factor.corr(forward_return, method='pearson')

    return ic

# 计算每日IC
daily_ic = calculate_ic(factor_series, returns_series)

# 计算IC统计指标
ic_mean = daily_ic.mean()
ic_std = daily_ic.std()
ic_ir = ic_mean / ic_std  # Information Ratio
ic_win_rate = (daily_ic > 0).sum() / len(daily_ic)
```

**IC评价标准**：
- IC > 0.05：优秀
- IC > 0.03：良好
- IC > 0.02：可用
- IC < 0.02：不可用

#### 3.3.2 IR（Information Ratio）

IR = IC均值 / IC标准差，衡量因子稳定性。

```python
def calculate_ir(ic_series):
    """计算IR值

    Args:
        ic_series: IC值序列

    Returns:
        IR值
    """
    return ic_series.mean() / ic_series.std()
```

**IR评价标准**：
- IR > 0.7：优秀
- IR > 0.5：良好
- IR > 0.3：可用
- IR < 0.3：不稳定

#### 3.3.3 因子衰减分析

检测因子在样本外的表现衰减。

```python
def analyze_factor_decay(ic_in_sample, ic_out_sample):
    """分析因子衰减

    Args:
        ic_in_sample: 样本内IC值
        ic_out_sample: 样本外IC值

    Returns:
        衰减报告
    """
    ic_abs_in = abs(ic_in_sample)
    ic_abs_out = abs(ic_out_sample)

    decay_rate = (ic_abs_in - ic_abs_out) / ic_abs_in

    report = {
        'ic_in_sample': ic_in_sample,
        'ic_out_sample': ic_out_sample,
        'decay_rate': decay_rate,
        'status': '✅ 正常' if decay_rate < 0.2 else '⚠️ 衰减严重'
    }

    return report
```

#### 3.3.4 因子组合评估

多因子模型的整体评估。

```python
def evaluate_factor_model(factor_scores, returns, top_pct=0.1):
    """评估因子模型

    Args:
        factor_scores: 多因子组合得分
        returns: 实际收益率
        top_pct: 选取前x%的股票

    Returns:
        评估指标
    """
    # 分组：Top组 vs Bottom组
    top_quantile = factor_scores.quantile(1 - top_pct)
    bottom_quantile = factor_scores.quantile(top_pct)

    top_group = returns[factor_scores >= top_quantile].mean()
    bottom_group = returns[factor_scores <= bottom_quantile].mean()

    # 分组收益差异
    group_diff = top_group - bottom_group

    # Rank IC
    rank_ic = factor_scores.corr(returns, method='spearman')

    # 分组胜率
    long_short_win_rate = (top_group > bottom_group).sum() / len(returns)

    return {
        'top_group_return': top_group,
        'bottom_group_return': bottom_group,
        'long_short_diff': group_diff,
        'rank_ic': rank_ic,
        'win_rate': long_short_win_rate
    }
```

### 3.4 因子挖掘方法

系统支持两种因子挖掘方法：**人工挖掘**和**自动挖掘**。

#### 3.4.1 人工挖掘

基于金融理论和行业经验，手动构建因子。

```python
# 示例：构建杜邦分析因子
def build_duPont_factors(df_fin):
    """构建杜邦分析因子"""
    factors = {}

    # ROE = 净利率 × 资产周转率 × 权益乘数
    factors['net_margin'] = df_fin['net_profit'] / df_fin['revenue']
    factors['asset_turnover'] = df_fin['revenue'] / df_fin['total_assets']
    factors['equity_multiplier'] = df_fin['total_assets'] / df_fin['total_equity']

    # 组合因子：ROE分解质量
    factors['roe_quality'] = (
        factors['net_margin'] *
        factors['asset_turnover'] *
        factors['equity_multiplier']
    )

    return pd.DataFrame(factors)
```

#### 3.4.2 自动挖掘

使用RD-Agent、遗传规划、GFlowNet等方法自动发现因子。

**使用遗传规划（gplearn）**：

```python
from gplearn.genetic import SymbolicRegressor

# 定义训练数据
X = base_factors  # 基础因子
y = forward_returns  # 未来收益率

# 训练遗传规划模型
est_gp = SymbolicRegressor(
    population_size=5000,
    generations=20,
    function_set=['add', 'sub', 'mul', 'div', 'log', 'abs',
                 'sqrt', 'sin', 'cos'],
    metric='pearson',  # 优化IC
    parsimony_coefficient=0.01,
    verbose=1,
    random_state=42
)

est_gp.fit(X, y)

# 获取生成的因子表达式
factor_formula = est_gp._program
print(f"生成的因子：{factor_formula}")

# 计算因子值
new_factor = est_gp.predict(X)
```

**使用GFlowNet（alpha-gfn）**：

```python
from alpha_gfn import GFNFactorGenerator

# 初始化生成器
generator = GFNFactorGenerator(
    base_features=base_columns,
    operators=['+', '-', '*', '/', 'log', 'lag', 'ma', 'ema'],
    max_depth=5
)

# 训练生成器（以IC为目标）
generator.train(
    target_ic=0.05,
    num_iterations=1000,
    validation_split=0.2
)

# 生成候选因子
candidates = generator.generate(num_factors=100)

# 评估和筛选
valid_factors = []
for factor in candidates:
    ic, ir = evaluate_factor(factor, returns)
    if ic > 0.03 and ir > 0.5:
        valid_factors.append(factor)
```

**使用RD-Agent（Qlib集成）**：

```python
from qlib.workflow import R
from rdagent.scenarios.qlib.experiment import QlibQuantScenario

# 定义场景
scenario = QlibQuantScenario(
    data_dir="qlib_data",
    feature_dir="features",
    model_dir="models"
)

# 配置参数
config = {
    "budget": 1000,  # 计算预算（GPU小时数）
    "max_factors": 100,
    "objective": "sharpe_ratio",
}

# 运行RD-Agent
results = scenario.run(
    config=config,
    knowledge_base="factor_knowledge.txt"
)

# 获取最佳因子
best_factors = results["factors"]
```

### 3.5 因子使用建议

#### 3.5.1 因子选择策略

1. **相关性控制**
   - 选择相关性低于0.6的因子组合
   - 使用聚类方法避免因子冗余

2. **IC稳定性**
   - 选择IC均值>3%，IR>0.5的因子
   - 避免IC波动过大的因子

3. **容量考虑**
   - 高IC但低容量因子需谨慎使用
   - 结合资金规模选择因子

4. **换手率控制**
   - 平衡换手率与交易成本
   - 换手率>50%/月的因子需考虑成本

5. **风格中性**
   - 对规模、价值等风格因子进行中性化
   - 避免过度暴露单一风格

#### 3.5.2 因子组合示例

**保守组合**：
```
估值因子（30%）：PE低、PB低
质量因子（30%）：ROE高、ROA高
波动率因子（20%）：低波动
规模因子（20%）：中小盘
```

**成长组合**：
```
成长因子（40%）：营收增长、盈利增长
动量因子（30%）：中期动量
分析师预期（20%）：目标价涨幅高
市值因子（10%）：中等市值
```

**多因子组合**：
```
基本面因子（40%）：估值+质量+成长
技术面因子（30%）：动量+反转+低波
情绪因子（15%）：分析师情绪+舆情
另类因子（15%）：机构持仓+北向资金
```

---

## 4. 策略体系

### 4.1 5大类策略说明

#### 4.1.1 趋势跟踪策略

**核心逻辑**：追随市场趋势，"追涨杀跌"，上涨时买入，下跌时卖出。

**适用场景**：
- 单边上涨/下跌行情
- 趋势明显的市场
- 高波动市场

**优势**：
- 能够捕捉大级别行情
- 收益潜力大
- 实现简单

**劣势**：
- 震荡市表现差
- 容易错过局部高低点
- 可能产生假信号

**典型策略**：

1. **双均线策略**
```python
def dual_ma_strategy(df_price, short_window=20, long_window=60):
    """双均线策略

    Args:
        df_price: 价格数据
        short_window: 短期均线周期
        long_window: 长期均线周期

    Returns:
        交易信号（1=买入，-1=卖出，0=持有）
    """
    # 计算均线
    short_ma = df_price['close'].rolling(short_window).mean()
    long_ma = df_price['close'].rolling(long_window).mean()

    # 生成信号
    signal = pd.Series(0, index=df_price.index)

    # 金叉（短期均线上穿长期均线）
    signal[(short_ma > long_ma) & (short_ma.shift(1) <= long_ma.shift(1))] = 1

    # 死叉（短期均线下穿长期均线）
    signal[(short_ma < long_ma) & (short_ma.shift(1) >= long_ma.shift(1))] = -1

    return signal
```

2. **布林带突破策略**
```python
def bollinger_band_strategy(df_price, window=20, num_std=2):
    """布林带策略"""
    middle = df_price['close'].rolling(window).mean()
    std = df_price['close'].rolling(window).std()

    upper = middle + num_std * std
    lower = middle - num_std * std

    signal = pd.Series(0, index=df_price.index)

    # 突破上轨
    signal[(df_price['close'] > upper) &
           (df_price['close'].shift(1) <= upper.shift(1))] = 1

    # 跌破下轨
    signal[(df_price['close'] < lower) &
           (df_price['close'].shift(1) >= lower.shift(1))] = -1

    return signal
```

3. **海龟交易法**
```python
def turtle_trading(df_price, entry_window=55, exit_window=20):
    """海龟交易法"""
    # 唐奇安通道
    donchian_high = df_price['high'].rolling(entry_window).max()
    donchian_low = df_price['low'].rolling(entry_window).min()

    signal = pd.Series(0, index=df_price.index)

    # 突破通道上轨
    signal[(df_price['high'] > donchian_high) &
           (df_price['high'].shift(1) <= donchian_high.shift(1))] = 1

    # 跌破通道下轨（止损或退出）
    signal[(df_price['low'] < donchian_low) &
           (df_price['low'].shift(1) >= donchian_low.shift(1))] = -1

    return signal
```

#### 4.1.2 均值回归策略

**核心逻辑**：价格长期围绕均值波动，偏离均值过度会回归。"低买高卖"。

**适用场景**：
- 震荡市
- 价格高波动
- 回归明显的市场

**优势**：
- 震荡市表现好
- 捕捉超卖超买机会
- 风险相对可控

**劣势**：
- 趋势市容易亏损
- 反弹时机难把握
- 可能被套在下跌趋势中

**典型策略**：

1. **RSI均值回归**
```python
def rsi_strategy(df_price, window=14, oversold=30, overbought=70):
    """RSI均值回归策略"""
    # 计算RSI
    delta = df_price['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    signal = pd.Series(0, index=df_price.index)

    # 超卖买入
    signal[(rsi < oversold) & (rsi.shift(1) >= oversold)] = 1

    # 超买卖出
    signal[(rsi > overbought) & (rsi.shift(1) <= overbought)] = -1

    return signal
```

2. **MACD反转**
```python
def macd_strategy(df_price, fast=12, slow=26, signal=9):
    """MACD反转策略"""
    # 计算MACD
    ema_fast = df_price['close'].ewm(span=fast).mean()
    ema_slow = df_price['close'].ewm(span=slow).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal).mean()
    histogram = macd - macd_signal

    signal = pd.Series(0, index=df_price.index)

    # MACD金叉+柱状图翻正
    signal[(macd > macd_signal) & (macd.shift(1) <= macd_signal.shift(1))] = 1

    # MACD死叉+柱状图翻负
    signal[(macd < macd_signal) & (macd.shift(1) >= macd_signal.shift(1))] = -1

    return signal
```

3. **统计套利（配对交易）**
```python
def pairs_trading(df_price_a, df_price_b, window=20, entry_z=2, exit_z=0.5):
    """配对交易策略

    Args:
        df_price_a: 股票A的价格
        df_price_b: 股票B的价格
        window: 滚动窗口
        entry_z: 入场Z-score阈值
        exit_z: 出场Z-score阈值
    """
    # 计算价差比率
    spread_ratio = df_price_a / df_price_b

    # 计算价差的Z-score
    spread_mean = spread_ratio.rolling(window).mean()
    spread_std = spread_ratio.rolling(window).std()
    spread_z = (spread_ratio - spread_mean) / spread_std

    signal = pd.Series(0, index=df_price_a.index)

    # 价差偏高，做空价差（卖A买B）
    signal[spread_z > entry_z] = -1

    # 价差偏低，做多价差（买A卖B）
    signal[spread_z < -entry_z] = 1

    # 价差回归，平仓
    signal[(spread_z > -exit_z) & (spread_z < exit_z)] = 0

    return signal
```

#### 4.1.3 因子轮动策略

**核心逻辑**：不同因子在不同市场环境下表现不同，根据因子表现动态调整因子权重。

**适用场景**：
- 市场风格切换频繁
- 因子收益率不稳定
- 需要动态配置的场景

**优势**：
- 适应市场变化
- 降低因子风险
- 提高整体收益

**劣势**：
- 因子切换成本高
- 可能误判风格
- 实施复杂度高

**典型策略**：

1. **基于因子IC的轮动**
```python
def factor_ic_rotation(factor_returns, rolling_window=12, top_n=5):
    """基于因子表现的轮动策略

    Args:
        factor_returns: 各因子的月度收益（DataFrame，列为因子）
        rolling_window: 滚动窗口（月数）
        top_n: 选取top_n个因子

    Returns:
        因子权重
    """
    factor_weights = pd.DataFrame(0, index=factor_returns.index,
                                   columns=factor_returns.columns)

    for i in range(rolling_window, len(factor_returns)):
        # 计算滚动IC均值
        rolling_ic = factor_returns.iloc[i-rolling_window:i].mean()

        # 选取IC最高的top_n个因子
        top_factors = rolling_ic.nlargest(top_n).index

        # 简单等权
        factor_weights.iloc[i][top_factors] = 1 / top_n

    return factor_weights
```

2. **基于市场风格的轮动**
```python
def style_factor_rotation(market_conditions, factor_compositions):
    """基于市场风格的因子轮动

    Args:
        market_conditions: 市场风格判断（成长/价值/大小盘）
        factor_compositions: 各风格对应的因子组合权重

    Returns:
        当前因子权重
    """
    # 判断市场风格
    current_style = detect_market_style(market_conditions)

    # 匹配对应的因子组合
    factor_weights = factor_compositions[current_style]

    return factor_weights

def detect_market_style(market_data):
    """检测市场风格

    Returns:
        style: 'growth', 'value', 'large_cap', 'small_cap'
    """
    pe_ratio = market_data['market_pe']
    market_cap = market_data['market_cap']
    momentum = market_data['market_momentum']

    # 判断成长vs价值
    if pe_ratio < 15 and momentum > 0:
        style = 'growth'
    else:
        style = 'value'

    # 结合大小盘
    if market_cap > 1000000000000:  # 万亿以上
        style += '_large'
    else:
        style += '_small'

    return style
```

#### 4.1.4 行业轮动策略

**核心逻辑**：不同行业在不同经济周期阶段表现不同，根据宏观经济形势动态调整行业配置。

**适用场景**：
- 宏观经济周期明显
- 行业分化严重
- 政策驱动市场

**优势**：
- 捕捉宏观机会
- 提高组合弹性
- 分散行业风险

**劣势**：
- 宏观判断难度大
- 政策影响不可预测
- 行业切换成本高

**典型策略**：

1. **基于行业动量的轮动**
```python
def industry_momentum_rotation(industry_returns, lookback_window=3, top_n=3):
    """基于行业动量的轮动

    Args:
        industry_returns: 行业指数收益率
        lookback_window: 观察期（月）
        top_n: 选取top_n个行业

    Returns:
        行业权重
    """
    industry_weights = pd.DataFrame(0, index=industry_returns.index,
                                     columns=industry_returns.columns)

    for i in range(lookback_window, len(industry_returns)):
        # 计算动量（累计收益率）
        momentum = (1 + industry_returns.iloc[i-lookback_window:i]).prod() - 1

        # 选取动量最高的行业
        top_industries = momentum.nlargest(top_n).index

        # 等权配置
        industry_weights.iloc[i][top_industries] = 1 / top_n

    return industry_weights
```

2. **基于美林时钟的轮动**
```python
def merlin_industry_rotation(gdp_growth, inflation, industry_mapping):
    """基于美林时钟的行业轮动

    Args:
        gdp_growth: GDP增长率
        inflation: 通胀率
        industry_mapping: 各经济阶段对应的行业

    Returns:
        推荐行业
    """
    # 判断经济阶段
    if gdp_growth > 0 and inflation < 0:
        phase = 'recovery'  # 复苏期
    elif gdp_growth > 0 and inflation > 0:
        phase = 'overheat'  # 过热期
    elif gdp_growth < 0 and inflation > 0:
        phase = 'stagflation'  # 滞胀期
    else:
        phase = 'recession'  # 衰退期

    # 匹配行业
    recommended_industries = industry_mapping[phase]

    return recommended_industries

# 行业映射
industry_mapping = {
    'recovery': ['有色金属', '化工', '银行', '可选消费'],
    'overheat': ['能源', '煤炭', '有色金属'],
    'stagflation': ['必需消费', '公用事业', '黄金'],
    'recession': ['医药', '国防军工', '成长股']
}
```

#### 4.1.5 事件驱动策略

**核心逻辑**：跟踪特定事件（财报发布、分红派息、并购重组等），利用市场对事件反应不足或过度反应获取超额收益。

**适用场景**：
- 事件发布
- 政策变化
- 宏观事件

**优势**：
- 收益确定性强
- 事件可预先知晓
- 风险相对可控

**劣势**：
- 机会有限
- 信息不对称
- 流动性风险

**典型策略**：

1. **财报超预期策略**
```python
def earnings_surprise_strategy(earnings_data, surprise_threshold=0.05):
    """财报超预期策略

    Args:
        earnings_data: 财报数据
        surprise_threshold: 超预期阈值（5%）

    Returns:
        交易股票列表
    """
    # 计算超预期幅度
    earnings_data['surprise'] = (
        earnings_data['actual_eps'] - earnings_data['expected_eps']
    ) / earnings_data['expected_eps']

    # 筛选超预期股票
    surprise_stocks = earnings_data[
        earnings_data['surprise'] > surprise_threshold
    ]['ts_code']

    return surprise_stocks
```

2. **分红派息策略**
```python
def dividend_strategy(dividend_data):
    """高股息策略"""
    # 计算股息率
    dividend_data['dividend_yield'] = (
        dividend_data['dividend_per_share'] / dividend_data['price']
    )

    # 筛选高股息股票（股息率>4%）
    high_dividend_stocks = dividend_data[
        dividend_data['dividend_yield'] > 0.04
    ].sort_values('dividend_yield', ascending=False)

    # 只保留ROE>10%的股票（盈利质量）
    high_dividend_stocks = high_dividend_stocks[
        high_dividend_stocks['roe'] > 0.10
    ]

    return high_dividend_stocks
```

3. **政策事件驱动**
```python
def policy_event_strategy(policy_news, industry_keywords):
    """政策事件驱动策略

    Args:
        policy_news: 政策新闻
        industry_keywords: 行业关键词映射

    Returns:
        受益行业
    """
   受益行业 = []

    for news in policy_news:
        # 提取关键词
        keywords = extract_keywords(news['content'])

        # 匹配行业
        for keyword in keywords:
            if keyword in industry_keywords:
                受益行业.append(industry_keywords[keyword])

    return list(set(受益行业))

# 行业关键词映射
industry_keywords = {
    '新能源': '电力设备',
    '半导体': '电子',
    '碳中和': '环保',
    '基建': '建筑装饰',
    '降准降息': '银行'
}
```

### 4.2 策略组合方法

#### 4.2.1 多策略组合

将不同类型的策略组合，分散风险，提高收益。

```python
def multi_strategy_combination(strategy_returns, weights=None):
    """多策略组合

    Args:
        strategy_returns: 各策略的收益率（DataFrame，列为策略）
        weights: 策略权重（None则等权）

    Returns:
        组合收益率
    """
    if weights is None:
        weights = np.ones(len(strategy_returns.columns)) / len(strategy_returns.columns)

    # 计算组合收益
    portfolio_return = (strategy_returns * weights).sum(axis=1)

    return portfolio_return

# 示例：构建多策略组合
strategy_returns = pd.DataFrame({
    'trend': trend_strategy_returns,
    'mean_reversion': mean_reversion_returns,
    'factor_rotation': factor_rotation_returns,
    'industry_rotation': industry_rotation_returns,
    'event_driven': event_driven_returns
})

# 定义策略权重
weights = {
    'trend': 0.20,
    'mean_reversion': 0.20,
    'factor_rotation': 0.25,
    'industry_rotation': 0.15,
    'event_driven': 0.20
}

# 计算组合收益
portfolio_return = multi_strategy_combination(strategy_returns, list(weights.values()))
```

#### 4.2.2 风险平价组合

追求各策略风险贡献相等。

```python
def risk_parity_portfolio(strategy_returns):
    """风险平价组合"""
    # 计算协方差矩阵
    cov_matrix = strategy_returns.cov()

    # 优化求解，使各资产风险贡献相等
    n = len(strategy_returns.columns)
    w = cp.Variable(n)

    constraints = [
        w >= 0,
        cp.sum(w) == 1
    ]

    # 目标：最小化风险贡献差异
    risk_contributions = cp.diag(cov_matrix @ w) * w
    avg_risk_contribution = cp.sum(risk_contributions) / n
    risk_diff = cp.sum_squares(risk_contributions - avg_risk_contribution)

    problem = cp.Problem(cp.Minimize(risk_diff), constraints)
    problem.solve()

    return pd.Series(w.value, index=strategy_returns.columns)
```

#### 4.2.3 动态权重调整

根据市场环境动态调整策略权重。

```python
def dynamic_strategy_allocation(market_regime, strategy_mapping):
    """动态策略配置

    Args:
        market_regime: 市场环境判断（牛市、熊市、震荡市）
        strategy_mapping: 各环境对应的策略权重

    Returns:
        当前策略权重
    """
    # 判断市场环境
    current_regime = detect_market_regime(market_regime)

    # 匹配策略权重
    strategy_weights = strategy_mapping[current_regime]

    return strategy_weights

def detect_market_regime(market_data):
    """检测市场环境"""
    # 计算市场趋势（均线系统）
    ma20 = market_data['close'].rolling(20).mean()
    ma60 = market_data['close'].rolling(60).mean()
    ma120 = market_data['close'].rolling(120).mean()

    # 计算市场波动率
    volatility = market_data['close'].pct_change().rolling(20).std()

    # 判断环境
    if ma20 > ma60 > ma120:
        if volatility < 0.02:
            regime = 'bull_market_low_vol'
        else:
            regime = 'bull_market'
    elif ma20 < ma60 < ma120:
        regime = 'bear_market'
    else:
        regime = 'sideways_market'

    return regime

# 策略权重映射
strategy_mapping = {
    'bull_market': {'trend': 0.40, 'momentum': 0.30, 'value': 0.30},
    'bear_market': {'defensive': 0.40, 'low_volatility': 0.30, 'cash': 0.30},
    'sideways_market': {'mean_reversion': 0.40, 'low_freq': 0.30, 'event': 0.30}
}
```

### 4.3 风险管理框架

#### 4.3.1 仓位控制

```python
def position_control(portfolio_value, max_single_position=0.05,
                    max_sector_position=0.30, max_strategy_position=0.30):
    """仓位控制

    Args:
        portfolio_value: 组合总值
        max_single_position: 单股票最大仓位
        max_sector_position: 单行业最大仓位
        max_strategy_position: 单策略最大仓位

    Returns:
        调整后的仓位
    """
    # 单股票仓位控制
    single_position_limit = portfolio_value * max_single_position

    # 单行业仓位控制
    sector_position_limit = portfolio_value * max_sector_position

    # 单策略仓位控制
    strategy_position_limit = portfolio_value * max_strategy_position

    return {
        'single_position_limit': single_position_limit,
        'sector_position_limit': sector_position_limit,
        'strategy_position_limit': strategy_position_limit
    }
```

#### 4.3.2 止损机制

```python
def stop_loss_mechanism(current_price, entry_price, stop_loss_pct=0.15):
    """止损机制

    Args:
        current_price: 当前价格
        entry_price: 入场价格
        stop_loss_pct: 止损百分比

    Returns:
        是否止损
    """
    return_pct = (current_price - entry_price) / entry_price

    if return_pct < -stop_loss_pct:
        return True
    else:
        return False
```

#### 4.3.3 动态监控

```python
def dynamic_monitoring(portfolio, risk_limits):
    """动态监控组合风险

    Args:
        portfolio: 当前组合
        risk_limits: 风险限制

    Returns:
        监控报告和警报
    """
    report = {}
    alerts = []

    # 1. 监控净值
    nav = portfolio['total_value'] / portfolio['initial_value']
    if nav < risk_limits['nav_warning']:
        alerts.append(f"⚠️ 净值警告: {nav:.2f}")

    # 2. 监控最大回撤
    max_drawdown = portfolio['max_drawdown']
    if max_drawdown < risk_limits['max_drawdown_warning']:
        alerts.append(f"⚠️ 最大回撤警告: {max_drawdown:.2%}")

    # 3. 监控风险暴露
    for factor, exposure in portfolio['factor_exposures'].items():
        if abs(exposure) > risk_limits['factor_exposure_limit']:
            alerts.append(f"⚠️ {factor}因子暴露过大: {exposure:.2f}")

    # 4. 监控行业集中度
    sector_concentration = portfolio['sector_concentration']
    if sector_concentration['max'] > risk_limits['sector_concentration_limit']:
        alerts.append(f"⚠️ 行业集中度过高: {sector_concentration['max']:.2%}")

    report['alerts'] = alerts
    report['status'] = 'PASS' if len(alerts) == 0 else 'WARNING'

    return report
```

#### 4.3.4 压力测试

```python
def stress_test(portfolio, scenarios):
    """压力测试

    Args:
        portfolio: 当前组合
        scenarios: 压力测试情景

    Returns:
        测试结果
    """
    results = {}

    for scenario_name, scenario_return in scenarios.items():
        # 计算组合在情景下的收益
        portfolio_return = (portfolio['positions'] * scenario_return).sum()
        portfolio_value_change = portfolio['total_value'] * portfolio_return

        results[scenario_name] = {
            'portfolio_return': portfolio_return,
            'value_change': portfolio_value_change,
            'shock_severity': 'SEVERE' if portfolio_return < -0.3 else
                              'MODERATE' if portfolio_return < -0.2 else 'MILD'
        }

    return results

# 压力测试情景
scenarios = {
    '2008_crash': -0.50,  # 2008年式大跌
    '2015_crash': -0.40,  # 2015年式股灾
    '2020_pandemic': -0.30,  # 2020年式疫情
    '2024_sideways': -0.05,  # 2024年式震荡
    'tech_bubble': -0.60  # 科技泡沫破裂
}
```

---

## 5. 回测系统

### 5.1 回测引擎架构

回测系统包含以下核心模块：

```
┌─────────────────────────────────────────────────────────────┐
│                        回测引擎                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  数据加载    │──│  因子计算    │──│  信号生成    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                 │                 │              │
│         v                 v                 v              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  组合构建    │──│  交易执行    │──│  绩效计算    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              成本模型（佣金、印花税、滑点）             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  风险控制模块                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 成本模型

#### 5.2.1 A股交易成本

A股交易成本包括以下部分：

| 成本类型 | 方向 | 费率 | 说明 |
|---------|------|------|------|
| 印花税 | 只卖 | 0.1% | 政府征收 |
| 佣金 | 双向 | 0.03% | 券商佣金（可协商） |
| 过户费 | 双向 | 0.001% | 交易所收取 |
| 滑点 | 双向 | 0.1% | 估计值（实际因成交量而异） |
| **合计** | 买入 | ~0.13% | 0.03%+0.001%+0.1% |
| **合计** | 卖出 | ~0.23% | 0.1%+0.03%+0.001%+0.1% |

#### 5.2.2 成本计算实现

```python
def calculate_transaction_cost(order, price, volume, commission_rate=0.0003,
                               stamp_tax_rate=0.001, transfer_fee_rate=0.00001,
                               slippage_rate=0.001):
    """计算交易成本

    Args:
        order: 订单（buy/sell）
        price: 价格
        volume: 成交量
        commission_rate: 佣金费率
        stamp_tax_rate: 印花税率
        transfer_fee_rate: 过户费率
        slippage_rate: 滑点率

    Returns:
        交易成本字典
    """
    cost = {}

    # 计算交易金额
    trade_amount = price * volume

    # 佣金
    commission = trade_amount * commission_rate
    commission = max(5, commission)  # 最低5元

    # 印花税（仅卖出）
    stamp_tax = 0
    if order == 'sell':
        stamp_tax = trade_amount * stamp_tax_rate

    # 过户费
    transfer_fee = trade_amount * transfer_fee_rate

    # 滑点（买卖方向相反）
    if order == 'buy':
        slippage = trade_amount * slippage_rate
        actual_price = price * (1 + slippage_rate)
    else:
        slippage = trade_amount * slippage_rate
        actual_price = price * (1 - slippage_rate)

    # 总成本
    total_cost = commission + stamp_tax + transfer_fee + slippage

    cost['commission'] = commission
    cost['stamp_tax'] = stamp_tax
    cost['transfer_fee'] = transfer_fee
    cost['slippage'] = slippage
    cost['total_cost'] = total_cost
    cost['actual_price'] = actual_price

    return cost
```

#### 5.2.3 冲击成本评估

对于大资金账户，需要考虑交易对价格的冲击。

```python
def calculate_impact_cost(order_size, average_daily_volume, impact_coefficient=0.1):
    """计算冲击成本

    Args:
        order_size: 订单规模（成交量）
        average_daily_volume: 平均日成交量
        impact_coefficient: 冲击系数

    Returns:
        冲击成本（价格影响百分比）
    """
    # 冲击成本 = 冲击系数 × （订单规模 / 日成交量）^0.5
    impact_cost = impact_coefficient * (order_size / average_daily_volume) ** 0.5

    return impact_cost
```

### 5.3 评估指标体系

#### 5.3.1 基础收益指标

```python
def calculate_return_metrics(portfolio_values, risk_free_rate=0.03):
    """计算收益指标

    Args:
        portfolio_values: 组合净值序列
        risk_free_rate: 无风险利率（年化）

    Returns:
        收益指标字典
    """
    metrics = {}

    # 日收益率
    daily_returns = portfolio_values.pct_change().dropna()

    # 年化收益率
    annual_return = (1 + daily_returns.mean()) ** 252 - 1

    # 累计收益率
    total_return = (portfolio_values.iloc[-1] / portfolio_values.iloc[0]) - 1

    # 波动率（年化）
    annual_volatility = daily_returns.std() * np.sqrt(252)

    # 下行波动率
    downside_returns = daily_returns[daily_returns < 0]
    downside_volatility = downside_returns.std() * np.sqrt(252)

    metrics['annual_return'] = annual_return
    metrics['total_return'] = total_return
    metrics['annual_volatility'] = annual_volatility
    metrics['downside_volatility'] = downside_volatility

    return metrics
```

#### 5.3.2 风险调整收益指标

```python
def calculate_risk_adjusted_metrics(portfolio_values, risk_free_rate=0.03):
    """计算风险调整收益指标"""
    # 获取日收益率
    daily_returns = portfolio_values.pct_change().dropna()
    annual_return = (1 + daily_returns.mean()) ** 252 - 1
    annual_volatility = daily_returns.std() * np.sqrt(252)
    daily_rf = (1 + risk_free_rate) ** (1/252) - 1

    metrics = {}

    # 夏普比率
    excess_return = daily_returns - daily_rf
    sharpe_ratio = excess_return.mean() / excess_return.std() * np.sqrt(252)

    # 索提诺比率（仅考虑下行风险）
    downside_std = daily_returns[daily_returns < 0].std()
    sortino_ratio = (annual_return - risk_free_rate) / (downside_std * np.sqrt(252))

    # 卡玛比率（收益/最大回撤）
    max_drawdown = calculate_max_drawdown(portfolio_values)
    calmar_ratio = annual_return / abs(max_drawdown)

    # 信息比率（相对基准的超额收益/跟踪误差）
    # 假设benchmark为市场指数收益率
    benchmark_returns = get_benchmark_returns()  # 需要实现
    excess_returns = daily_returns - benchmark_returns
    tracking_error = excess_returns.std() * np.sqrt(252)
    information_ratio = excess_returns.mean() * 252 / tracking_error

    metrics['sharpe_ratio'] = sharpe_ratio
    metrics['sortino_ratio'] = sortino_ratio
    metrics['calmar_ratio'] = calmar_ratio
    metrics['information_ratio'] = information_ratio

    return metrics

def calculate_max_drawdown(portfolio_values):
    """计算最大回撤"""
    peak = portfolio_values.expanding().max()
    drawdown = (portfolio_values - peak) / peak
    max_drawdown = drawdown.min()

    return max_drawdown
```

#### 5.3.3 交易指标

```python
def calculate_trading_metrics(trades):
    """计算交易指标

    Args:
        trades: 交易记录DataFrame

    Returns:
        交易指标字典
    """
    metrics = {}

    # 持仓天数
    metrics['avg_holding_days'] = trades['holding_days'].mean()

    # 胜率
    metrics['win_rate'] = (trades['profit'] > 0).sum() / len(trades)

    # 盈亏比
    avg_profit = trades[trades['profit'] > 0]['profit'].mean()
    avg_loss = abs(trades[trades['profit'] < 0]['profit'].mean())
    metrics['profit_loss_ratio'] = avg_profit / avg_loss if avg_loss > 0 else np.inf

    # 换手率（年化）
    total_trades = len(trades)
    trading_days = len(trades['date'].unique())
    metrics['annual_turnover'] = total_trades / trading_days * 252

    return metrics
```

#### 5.3.4 完整评估报告

```python
def generate_full_backtest_report(portfolio_values, trades, benchmark_values=None):
    """生成完整回测报告

    Args:
        portfolio_values: 组合净值序列
        trades: 交易记录
        benchmark_values: 基准净值序列（可选）

    Returns:
        完整报告字典
    """
    report = {}

    # 1. 基础收益指标
    report['returns'] = calculate_return_metrics(portfolio_values)

    # 2. 风险调整收益指标
    report['risk_adjusted'] = calculate_risk_adjusted_metrics(portfolio_values)

    # 3. 交易指标
    report['trading'] = calculate_trading_metrics(trades)

    # 4. 最大回撤
    report['max_drawdown'] = calculate_max_drawdown(portfolio_values)

    # 5. 相对基准表现
    if benchmark_values is not None:
        report['benchmark_comparison'] = compare_with_benchmark(
            portfolio_values, benchmark_values
        )

    # 6. 月度/年度表现
    report['periodic_returns'] = calculate_periodic_returns(portfolio_values)

    # 7. 因子暴露分析
    report['factor_exposures'] = analyze_factor_exposures(portfolio_values)

    return report

def compare_with_benchmark(portfolio_values, benchmark_values):
    """对比基准表现"""
    # 计算相对收益
    portfolio_returns = portfolio_values.pct_change().dropna()
    benchmark_returns = benchmark_values.pct_change().dropna()

    excess_returns = portfolio_returns - benchmark_returns

    return {
        'excess_annual_return': excess_returns.mean() * 252,
        'tracking_error': excess_returns.std() * np.sqrt(252),
        'excess_sharpe': excess_returns.mean() / excess_returns.std() * np.sqrt(252)
    }

def calculate_periodic_returns(portfolio_values):
    """计算周期性收益"""
    returns = portfolio_values.pct_change()

    # 月度收益
    monthly_returns = returns.resample('M').apply(lambda x: (1 + x).prod() - 1)

    # 年度收益
    yearly_returns = returns.resample('Y').apply(lambda x: (1 + x).prod() - 1)

    return {
        'monthly_returns': monthly_returns,
        'yearly_returns': yearly_returns,
        'avg_monthly_return': monthly_returns.mean(),
        'avg_yearly_return': yearly_returns.mean()
    }
```

---

## 6. 实盘工程

### 6.1 模拟盘设计

#### 6.1.1 模拟盘架构

模拟盘系统是实盘前的关键验证环节，需要完全模拟实盘交易环境，包括下单、成交、成本计算等全流程。

**模拟盘架构图**：
```
┌─────────────────────────────────────────────────────────────┐
│                      模拟盘交易系统                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  信号生成    │──│  订单生成    │──│  模拟成交    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                 │                 │              │
│         v                 v                 v              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  持仓管理    │──│  成本计算    │──│  绩效统计    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                   风控检查（事前）                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  风控检查（事后）                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 6.1.2 模拟订单执行

```python
class SimulatedOrderExecutor:
    """模拟订单执行器"""
    
    def __init__(self, initial_capital=1000000):
        """
        Args:
            initial_capital: 初始资金
        """
        self.cash = initial_capital
        self.positions = {}  # 持仓 {stock_code: {'quantity': int, 'avg_price': float}}
        self.orders = []  # 历史订单
        self.fills = []  # 成交记录
        self.nav = initial_capital  # 净值
        
    def place_order(self, stock_code, order_type, quantity, price=None):
        """下单
        
        Args:
            stock_code: 股票代码
            order_type: 'buy' 或 'sell'
            quantity: 数量（股）
            price: 价格（None则用市价）
        """
        # 事前风控检查
        if not self.pre_trade_risk_check(stock_code, order_type, quantity):
            print(f"❌ 订单被风控拒绝：{stock_code} {order_type} {quantity}")
            return False
        
        # 计算订单金额
        if price is None:
            price = self.get_market_price(stock_code)
        
        order_amount = price * quantity
        
        # 买入检查资金
        if order_type == 'buy':
            cost = self.calculate_transaction_cost('buy', price, quantity)
            total_cost = order_amount + cost['total_cost']
            
            if total_cost > self.cash:
                print(f"❌ 资金不足：需要 {total_cost:.2f}，可用 {self.cash:.2f}")
                return False
        
        # 卖出检查持仓
        if order_type == 'sell':
            if stock_code not in self.positions or \
               self.positions[stock_code]['quantity'] < quantity:
                print(f"❌ 持仓不足：{stock_code} 持有 {self.positions.get(stock_code, {}).get('quantity', 0)}")
                return False
        
        # 记录订单
        order = {
            'timestamp': datetime.now(),
            'stock_code': stock_code,
            'order_type': order_type,
            'quantity': quantity,
            'price': price,
            'amount': order_amount,
            'status': 'SUBMITTED'
        }
        
        self.orders.append(order)
        
        # 模拟成交
        fill = self.simulate_fill(order)
        self.fills.append(fill)
        
        # 更新持仓和资金
        self.update_position(order, fill)
        
        # 事后风控检查
        self.post_trade_risk_check()
        
        # 更新净值
        self.update_nav()
        
        return True
    
    def get_market_price(self, stock_code):
        """获取市场价格（模拟）"""
        # 在实际系统中，这里会调用行情API
        # 这里简化为随机生成
        return np.random.uniform(10, 30)
    
    def calculate_transaction_cost(self, order_type, price, quantity):
        """计算交易成本"""
        return calculate_transaction_cost(
            order_type=order_type,
            price=price,
            quantity=quantity
        )
    
    def simulate_fill(self, order):
        """模拟成交"""
        # 模拟成交时间（当日T+1成交）
        fill_timestamp = datetime.now() + timedelta(days=1)
        
        # 模拟成交价格（可能有滑点）
        slippage_rate = 0.001
        if order['order_type'] == 'buy':
            fill_price = order['price'] * (1 + slippage_rate)
        else:
            fill_price = order['price'] * (1 - slippage_rate)
        
        # 计算实际成交金额
        fill_amount = fill_price * order['quantity']
        
        # 计算成本
        cost = self.calculate_transaction_cost(
            order['order_type'], fill_price, order['quantity']
        )
        
        fill = {
            'timestamp': fill_timestamp,
            'order_id': len(self.orders),
            'stock_code': order['stock_code'],
            'order_type': order['order_type'],
            'quantity': order['quantity'],
            'price': fill_price,
            'amount': fill_amount,
            'commission': cost['commission'],
            'stamp_tax': cost['stamp_tax'],
            'transfer_fee': cost['transfer_fee'],
            'slippage': cost['slippage'],
            'total_cost': cost['total_cost']
        }
        
        return fill
    
    def update_position(self, order, fill):
        """更新持仓"""
        stock_code = fill['stock_code']
        quantity = fill['quantity']
        price = fill['price']
        total_cost = fill['total_cost']
        
        if fill['order_type'] == 'buy':
            # 买入
            total_amount = price * quantity + total_cost
            
            if stock_code in self.positions:
                # 加仓
                old_quantity = self.positions[stock_code]['quantity']
                old_avg_price = self.positions[stock_code]['avg_price']
                old_total_cost = old_quantity * old_avg_price
                
                new_quantity = old_quantity + quantity
                new_total_cost = old_total_cost + total_amount
                new_avg_price = new_total_cost / new_quantity
                
                self.positions[stock_code] = {
                    'quantity': new_quantity,
                    'avg_price': new_avg_price
                }
            else:
                # 新建仓
                self.positions[stock_code] = {
                    'quantity': quantity,
                    'avg_price': total_amount / quantity
                }
            
            self.cash -= total_amount
            
        else:
            # 卖出
            old_quantity = self.positions[stock_code]['quantity']
            old_avg_price = self.positions[stock_code]['avg_price']
            
            # 计算盈亏
            total_revenue = price * quantity - total_cost
            self.cash += total_revenue
            
            # 更新持仓
            new_quantity = old_quantity - quantity
            if new_quantity == 0:
                del self.positions[stock_code]
            else:
                self.positions[stock_code]['quantity'] = new_quantity
    
    def update_nav(self):
        """更新净值"""
        # 计算持仓市值
        total_market_value = self.cash
        for stock_code, position in self.positions.items():
            current_price = self.get_market_price(stock_code)
            market_value = position['quantity'] * current_price
            total_market_value += market_value
        
        self.nav = total_market_value
    
    def pre_trade_risk_check(self, stock_code, order_type, quantity):
        """事前风控检查"""
        # 1. 单股票仓位限制
        price = self.get_market_price(stock_code)
        position_value = price * quantity
        max_single_position = self.nav * 0.05  # 单股票最大5%
        
        if position_value > max_single_position:
            print(f"⚠️ 单股票仓位超限：{position_value:.2f} > {max_single_position:.2f}")
            return False
        
        # 2. 行业集中度限制
        # 省略...需要获取股票行业信息
        
        # 3. 单日交易限制
        # 省略...需要统计当日已下单金额
        
        return True
    
    def post_trade_risk_check(self):
        """事后风控检查"""
        # 1. 最大回撤检查
        # 省略...需要跟踪历史净值
        
        # 2. 整体仓位检查
        total_position_value = sum([
            pos['quantity'] * self.get_market_price(sc)
            for sc, pos in self.positions.items()
        ])
        position_ratio = total_position_value / self.nav
        
        if position_ratio > 0.95:
            print(f"⚠️ 整体仓位过高：{position_ratio:.2%}")
        
        # 3. 风险暴露检查
        # 省略...需要实现因子暴露计算
    
    def get_portfolio_summary(self):
        """获取组合摘要"""
        total_market_value = self.cash
        positions_summary = []
        
        for stock_code, position in self.positions.items():
            current_price = self.get_market_price(stock_code)
            market_value = position['quantity'] * current_price
            profit = market_value - position['quantity'] * position['avg_price']
            profit_ratio = profit / (position['quantity'] * position['avg_price'])
            
            positions_summary.append({
                'stock_code': stock_code,
                'quantity': position['quantity'],
                'avg_price': position['avg_price'],
                'current_price': current_price,
                'market_value': market_value,
                'profit': profit,
                'profit_ratio': profit_ratio
            })
            
            total_market_value += market_value
        
        return {
            'cash': self.cash,
            'total_market_value': total_market_value,
            'nav': total_market_value,
            'position_ratio': (total_market_value - self.cash) / total_market_value,
            'positions': positions_summary
        }
```

#### 6.1.3 模拟盘与实盘差异

模拟盘与实盘存在以下差异，需要在实盘前充分了解：

| 差异项 | 模拟盘 | 实盘 | 潜在影响 |
|-------|-------|------|---------|
| 滑点 | 估计值0.1% | 实际可能更高/更低 | 交易成本可能误判 |
| 成交概率 | 假设都能成交 | 可能部分成交或未成交 | 规模扩大后更明显 |
| 冲击成本 | 简单模型 | 受深度影响 | 大资金影响大 |
| 延迟 | 几乎无延迟 | 网络延迟+排队延迟 | 可能错过最佳价位 |
| 系统稳定性 | 相对稳定 | 可能有故障 | 执行失败风险 |
| 数据问题 | 假设完美 | 可能有异常 | 需要异常处理 |

**建议**：
- 模拟盘运行至少3-6个月
- 逐步增加资金规模（如10万 → 100万 → 1000万）
- 记录模拟盘与实盘的差异，不断调整模型
- 建立异常处理机制

### 6.2 风控模块

#### 6.2.1 多级风控体系

```python
class MultiLevelRiskManager:
    """多级风控管理器"""
    
    def __init__(self, portfolio):
        """
        Args:
            portfolio: 投资组合
        """
        self.portfolio = portfolio
        self.risk_limits = {
            'portfolio': {
                'max_drawdown': -0.20,
                'max_daily_loss': -0.05,
                'max_position_ratio': 0.95,
                'min_cash_ratio': 0.05
            },
            'position': {
                'max_single_stock_ratio': 0.05,
                'max_sector_ratio': 0.30,
                'max_style_beta': 0.3
            },
            'trading': {
                'max_daily_trades': 100,
                'max_single_trade_ratio': 0.02
            }
        }
        self.alerts = []
        self.block_orders = False
    
    def check_portfolio_risk(self):
        """检查组合级风险"""
        nav = self.portfolio['nav']
        current_drawdown = self.portfolio['current_drawdown']
        
        alerts = []
        
        # 最大回撤检查
        if current_drawdown < self.risk_limits['portfolio']['max_drawdown']:
            alerts.append({
                'level': 'CRITICAL',
                'type': 'MAX_DRAWDOWN',
                'message': f"最大回撤超限：{current_drawdown:.2%}",
                'action': 'REDUCE_POSITIONS'
            })
        
        # 整体仓位检查
        position_ratio = (nav - self.portfolio['cash']) / nav
        if position_ratio > self.risk_limits['portfolio']['max_position_ratio']:
            alerts.append({
                'level': 'WARNING',
                'type': 'POSITION_RATIO',
                'message': f"整体仓位过高：{position_ratio:.2%}",
                'action': 'STOP_NEW_ORDERS'
            })
        
        # 现金比例检查
        cash_ratio = self.portfolio['cash'] / nav
        if cash_ratio < self.risk_limits['portfolio']['min_cash_ratio']:
            alerts.append({
                'level': 'WARNING',
                'type': 'CASH_RATIO',
                'message': f"现金比例过低：{cash_ratio:.2%}",
                'action': 'INCREASE_CASH'
            })
        
        self.alerts.extend(alerts)
        return alerts
    
    def check_position_risk(self, new_position):
        """检查持仓级风险"""
        alerts = []
        
        # 单股票仓位检查
        nav = self.portfolio['nav']
        position_value = new_position['quantity'] * new_position['price']
        single_stock_ratio = position_value / nav
        
        if single_stock_ratio > self.risk_limits['position']['max_single_stock_ratio']:
            alerts.append({
                'level': 'WARNING',
                'type': 'SINGLE_STOCK_RATIO',
                'message': f"单股票仓位超限：{single_stock_ratio:.2%}",
                'action': 'REDUCE_QUANTITY'
            })
        
        # 行业集中度检查
        sector = get_stock_sector(new_position['stock_code'])
        sector_exposure = calculate_sector_exposure(self.portfolio, sector)
        new_sector_exposure = sector_exposure + single_stock_ratio
        
        if new_sector_exposure > self.risk_limits['position']['max_sector_ratio']:
            alerts.append({
                'level': 'WARNING',
                'type': 'SECTOR_CONCENTRATION',
                'message': f"行业集中度过高：{new_sector_exposure:.2%}",
                'action': 'REJECT_ORDER'
            })
        
        self.alerts.extend(alerts)
        return alerts
    
    def check_trading_risk(self, order):
        """检查交易级风险"""
        alerts = []
        
        # 单日交易数量检查
        today_orders = len([
            o for o in self.portfolio['orders']
            if o['date'] == datetime.now().date()
        ])
        
        if today_orders >= self.risk_limits['trading']['max_daily_trades']:
            alerts.append({
                'level': 'WARNING',
                'type': 'DAILY_TRADE_LIMIT',
                'message': f"单日交易数量超限：{today_orders}",
                'action': 'BLOCK_ADDITIONAL_ORDERS'
            })
            self.block_orders = True
        
        # 单笔交易规模检查
        nav = self.portfolio['nav']
        trade_ratio = (order['quantity'] * order['price']) / nav
        
        if trade_ratio > self.risk_limits['trading']['max_single_trade_ratio']:
            alerts.append({
                'level': 'WARNING',
                'type': 'SINGLE_TRADE_SIZE',
                'message': f"单笔交易规模过大：{trade_ratio:.2%}",
                'action': 'REDUCE_QUANTITY'
            })
        
        self.alerts.extend(alerts)
        return alerts
    
    def execute_risk_control_action(self, alert):
        """执行风控操作"""
        if alert['level'] == 'CRITICAL':
            # 紧急减仓
            if alert['action'] == 'REDUCE_POSITIONS':
                self.portfolio['executor'].reduce_all_positions(0.5)  # 减仓50%
        
        elif alert['level'] == 'WARNING':
            # 阻止新订单
            if alert['action'] == 'STOP_NEW_ORDERS':
                self.block_orders = True
            elif alert['action'] == 'REJECT_ORDER':
                return False  # 拒绝订单
        
        return True  # 允许订单
    
    def reset_daily_limits(self):
        """重置每日限制"""
        self.block_orders = False
```

#### 6.2.2 动态止损

```python
def dynamic_stop_loss(position, current_price, initial_stop_loss=0.15,
                     trailing_stop_loss=0.10, volatility_window=20):
    """动态止损
    
    Args:
        position: 持仓信息
        current_price: 当前价格
        initial_stop_loss: 初始止损（15%）
        trailing_stop_loss: 移动止损（10%）
        volatility_window: 波动率计算窗口
    
    Returns:
        是否止损
    """
    entry_price = position['avg_price']
    quantity = position['quantity']
    
    # 计算当前收益
    current_return = (current_price - entry_price) / entry_price
    
    # 1. 初始止损
    if current_return < -initial_stop_loss:
        return True
    
    # 2. 移动止损（如果盈利超过5%）
    if current_return > 0.05:
        # 计算移动止损价格
        stop_loss_price = max(entry_price, position.get('high_watermark', entry_price)) * (1 - trailing_stop_loss)
        
        # 更新最高水位线
        position['high_watermark'] = max(position.get('high_watermark', entry_price), current_price)
    else:
        # 根据波动率调整止损
        volatility = calculate_volatility(current_price, volatility_window)
        dynamic_stop_loss = initial_stop_loss + volatility
        
        if current_return < -dynamic_stop_loss:
            return True
    
    return False

def calculate_volatility(price, window):
    """计算波动率"""
    # 这里需要历史价格数据
    # 简化：假设有价格序列
    returns = price.pct_change()
    volatility = returns.rolling(window).std().iloc[-1]
    
    return volatility
```

### 6.3 监控系统

#### 6.3.1 实时监控指标

```python
class RealTimeMonitor:
    """实时监控系统"""
    
    def __init__(self, portfolio):
        self.portfolio = portfolio
        self.metrics = {}
        self.alerts = []
    
    def update_metrics(self):
        """更新监控指标"""
        # 组合净值
        self.metrics['nav'] = self.portfolio['nav']
        
        # 组合收益率
        self.metrics['daily_return'] = (
            self.portfolio['nav'] / self.portfolio['prev_nav'] - 1
        )
        
        # 最大回撤
        self.metrics['max_drawdown'] = self.portfolio['current_drawdown']
        
        # 仓位比例
        self.metrics['position_ratio'] = (
            (self.portfolio['nav'] - self.portfolio['cash']) /
            self.portfolio['nav']
        )
        
        # 夏普比率（滚动）
        self.metrics['rolling_sharpe'] = self.calculate_rolling_sharpe()
        
        # 因子暴露
        self.metrics['factor_exposures'] = self.calculate_factor_exposures()
        
        # 行业暴露
        self.metrics['sector_exposures'] = self.calculate_sector_exposures()
    
    def check_alerts(self):
        """检查警报"""
        alerts = []
        
        # 净值警报
        if self.metrics['nav'] < self.portfolio['nav_warning']:
            alerts.append({
                'type': 'NAV_WARNING',
                'severity': 'WARNING',
                'message': f"净值警告：{self.metrics['nav']:.2f}"
            })
        
        # 回撤警报
        if self.metrics['max_drawdown'] < self.portfolio['max_drawdown_warning']:
            alerts.append({
                'type': 'MAX_DRAWDOWN_WARNING',
                'severity': 'CRITICAL',
                'message': f"最大回撤警告：{self.metrics['max_drawdown']:.2%}"
            })
        
        # 夏普比率警报
        if self.metrics['rolling_sharpe'] < self.portfolio['sharpe_warning']:
            alerts.append({
                'type': 'SHARPE_WARNING',
                'severity': 'WARNING',
                'message': f"夏普比率警告：{self.metrics['rolling_sharpe']:.2f}"
            })
        
        # 因子暴露警报
        for factor, exposure in self.metrics['factor_exposures'].items():
            if abs(exposure) > self.portfolio['factor_exposure_limit']:
                alerts.append({
                    'type': 'FACTOR_EXPOSURE_WARNING',
                    'severity': 'WARNING',
                    'message': f"{factor}因子暴露过大：{exposure:.2f}"
                })
        
        self.alerts = alerts
        return alerts
    
    def generate_report(self):
        """生成监控报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'metrics': self.metrics,
            'alerts': self.alerts,
            'portfolio_summary': self.portfolio.get_summary()
        }
        
        return report
    
    def send_alert(self, alert):
        """发送警报"""
        if alert['severity'] == 'CRITICAL':
            # 发送紧急通知（短信、电话）
            send_emergency_notification(alert['message'])
        elif alert['severity'] == 'WARNING':
            # 发送普通通知（邮件、消息）
            send_warning_notification(alert['message'])
```

#### 6.3.2 监控面板配置

```json
{
  "dashboard_config": {
    "panels": [
      {
        "name": "净值曲线",
        "type": "line_chart",
        "metrics": ["nav_history"],
        "y_axis": "净值"
      },
      {
        "name": "收益率分布",
        "type": "histogram",
        "metrics": ["daily_returns"],
        "bins": 50
      },
      {
        "name": "回撤分析",
        "type": "area_chart",
        "metrics": ["drawdown_series"],
        "y_axis": "回撤"
      },
      {
        "name": "持仓分布",
        "type": "pie_chart",
        "metrics": ["positions"],
        "group_by": "sector"
      },
      {
        "name": "因子暴露",
        "type": "bar_chart",
        "metrics": ["factor_exposures"],
        "y_axis": "暴露度"
      },
      {
        "name": "风险指标",
        "type": "table",
        "metrics": ["sharpe_ratio", "sortino_ratio", "max_drawdown", "volatility"]
      },
      {
        "name": "告警列表",
        "type": "list",
        "metrics": ["alerts"],
        "sort_by": "severity"
      }
    ]
  }
}
```

---

## 7. 运维指南

### 7.1 日常运维流程

#### 7.1.1 每日例行任务

**开盘前（9:00-9:25）**：

1. **数据检查**
```bash
# 1. 检查数据更新
python scripts/check_data_update.py --date $(date +%Y%m%d)

# 2. 检查数据质量
python scripts/validate_data.py --date $(date +%Y%m%d)

# 3. 检查数据异常
python scripts/check_data_anomalies.py --date $(date +%Y%m%d)
```

2. **系统检查**
```bash
# 1. 检查系统状态
python scripts/check_system_status.py

# 2. 检查依赖服务
python scripts/check_dependencies.py

# 3. 检查磁盘空间
df -h
```

3. **因子计算**
```bash
# 计算当日因子
python scripts/calculate_factors.py --date $(date +%Y%m%d)

# 验证因子质量
python scripts/validate_factors.py --date $(date +%Y%m%d)
```

4. **信号生成**
```bash
# 生成交易信号
python scripts/generate_signals.py --date $(date +%Y%m%d)

# 检查信号合理性
python scripts/validate_signals.py --date $(date +%Y%m%d)
```

**盘中（9:30-15:00）**：

1. **实时监控**
```bash
# 启动监控面板
python scripts/monitor_dashboard.py

# 检查实时风险
python scripts/check_realtime_risk.py
```

2. **订单执行**
```bash
# 自动执行订单
python scripts/execute_orders.py --mode=auto
# 或手动审批
python scripts/execute_orders.py --mode=manual
```

**盘后（15:00-18:00）**：

1. **数据更新**
```bash
# 更新行情数据
python scripts/update_market_data.py --date $(date +%Y%m%d)

# 更新财务数据
python scripts/update_financial_data.py --date $(date +%Y%m%d)
```

2. **组合回顾**
```bash
# 计算当日收益
python scripts/calculate_daily_return.py --date $(date +%Y%m%d)

# 生成组合报告
python scripts/generate_portfolio_report.py --date $(date +%Y%m%d)

# 更新风险指标
python scripts/update_risk_metrics.py --date $(date +%Y%m%d)
```

3. **系统备份**
```bash
# 备份数据
python scripts/backup_data.py --date $(date +%Y%m%d)

# 备份日志
python scripts/backup_logs.py --date $(date +%Y%m%d)
```

#### 7.1.2 周例行任务

**每周一**：
- 检查因子IC变化趋势
- 评估策略表现
- 调整因子权重（如需要）

**每周五**：
- 生成周度报告
- 压力测试
- 风险评估

#### 7.1.3 月例行任务

**每月1日**：
- 生成月度报告
- 进行月度回顾
- 调整模型参数（如需要）

**每月最后一个交易日**：
- 进行月度归因分析
- 评估因子有效性
- 制定下月策略

### 7.2 异常处理手册

#### 7.2.1 数据异常处理

**问题1：数据缺失**

症状：检查发现某日期数据缺失

处理流程：
```python
def handle_missing_data(date, data_type):
    """处理缺失数据"""
    # 1. 记录异常
    log_error(f"数据缺失：{date} {data_type}")
    
    # 2. 尝试重新获取
    try:
        data = fetch_data_source(date, data_type)
        if data is not None:
            store_data(data)
            return True
    except Exception as e:
        log_error(f"重新获取失败：{e}")
    
    # 3. 使用历史数据填充
    try:
        data = fetch_last_n_days(date, data_type, 1)
        forward_fill_data(data, date)
        return True
    except Exception as e:
        log_error(f"历史填充失败：{e}")
    
    # 4. 使用插值
    try:
        data = fetch_surrounding_days(date, data_type, 5)
        interpolate_data(data, date)
        return True
    except Exception as e:
        log_error(f"插值失败：{e}")
    
    # 5. 暂停交易，通知运维
    suspend_trading("数据缺失")
    notify运维团队(f"{date} {data_type} 数据缺失")
    
    return False
```

**问题2：数据异常值**

症状：数据出现明显异常值（如股价>1000，成交量<0）

处理流程：
```python
def handle_outliers(data, thresholds):
    """处理异常值"""
    outliers = []
    
    # 1. 检测异常值
    for column, threshold in thresholds.items():
        if (abs(data[column]) > threshold).any():
            outliers.append(column)
    
    # 2. 记录异常
    log_warning(f"发现异常值：{outliers}")
    
    # 3. 处理异常值
    for column in outliers:
        # 使用滚动中位数替换
        rolling_median = data[column].rolling(20).median()
        data[column] = data[column].where(
            abs(data[column]) <= thresholds[column],
            rolling_median
        )
    
    # 4. 验证处理结果
    if validate_data(data):
        return data
    else:
        # 处理失败，暂停交易
        suspend_trading("数据异常值处理失败")
        return None
```

#### 7.2.2 系统异常处理

**问题1：交易系统故障**

症状：无法下单或订单执行失败

处理流程：
```python
def handle_trading_system_fault():
    """处理交易系统故障"""
    # 1. 立即停止自动交易
    stop_auto_trading()
    
    # 2. 记录故障信息
    log_error("交易系统故障")
    
    # 3. 通知人工介入
    send_alert("交易系统故障，需人工介入")
    
    # 4. 切换到备用系统（如果有）
    if backup_system_available():
        switch_to_backup()
    else:
        # 只能操作止损单
        allow_only_stop_loss_orders()
    
    # 5. 故障排查
    # - 网络连接
    # - API接口
    # - 认证信息
    # - 服务器状态
    
    # 6. 恢复后测试
    # - 小额测试单
    # - 验证执行逻辑
    # - 检查订单状态
    
    # 7. 渐渐恢复正常
    restart_auto_trading()
```

**问题2：风控触发**

症状：警报被触发，需要紧急处理

处理流程：
```python
def handle_risk_alert(alert):
    """处理风控警报"""
    severity = alert['severity']
    
    if severity == 'CRITICAL':
        # 紧急处理
        if alert['type'] == 'MAX_DRAWDOWN_WARNING':
            # 减仓50%
            reduce_positions(ratio=0.5)
        elif alert['type'] == 'NAV_WARNING':
            # 停止新开仓，只允许平仓
            stop_new_orders()
            allow_only_close_orders()
        
        # 通知决策层
        send_emergency_alert(alert)
        
    elif severity == 'WARNING':
        # 普通处理
        if alert['type'] == 'FACTOR_EXPOSURE_WARNING':
            # 调整持仓以降低因子暴露
            adjust_factor_exposures()
        
        # 记录到日志
        log_warning(alert['message'])
```

#### 7.2.3 市场异常处理

**问题1：市场剧烈波动**

症状：市场出现极端行情（如千股跌停）

处理流程：
```python
def handle_extreme_market_volatility():
    """处理极端市场波动"""
    # 1. 检测市场状态
    market_state = detect_market_state()
    
    if market_state == 'CRASH':
        # 市场崩盘
        # 立即减仓
        reduce_positions(ratio=0.3)
        # 只保留现金和国债
        keep_only_safe_assets()
        
    elif market_state == 'EXTREME_VOLATILITY':
        # 极端波动
        # 降低仓位
        reduce_positions(ratio=0.5)
        # 暂停高频交易
        suspend_high_frequency_trading()
        
    elif market_state == 'RESTRICTED':
        # 市场受限（如熔断）
        # 无法交易，只能观察
        suspend_all_trading()
        monitor_market_situation()
```

**问题2：流动性危机**

症状：股票无法买卖，或成交价偏离

处理流程：
```python
def handle_liquidity_crisis(stock_code):
    """处理流动性危机"""
    # 1. 检测流动性
    liquidity = check_liquidity(stock_code)
    
    if liquidity['status'] == 'SEVERE':
        # 流动性严重不足
        # 暂停该股票交易
        suspend_stock_trading(stock_code)
        
        # 分批平仓（小量多次）
        liquidate_positions_gradually(stock_code)
        
    elif liquidity['status'] == 'MODERATE':
        # 流动性稍差
        # 降低该股票仓位
        reduce_stock_position(stock_code, ratio=0.5)
        
        # 增加滑点容忍度
        adjust_slippage_tolerance(increase=True)
```

### 7.3 定期任务清单

#### 7.3.1 每日清单

| 任务 | 时间 | 执行人 | 检查项 |
|-----|------|-------|-------|
| 数据检查 | 开盘前30分钟 | 系统 | 数据完整性、准确性 |
| 因子计算 | 开盘前20分钟 | 系统 | 因子值合理性 |
| 信号生成 | 开盘前10分钟 | 系统 | 信号逻辑正确性 |
| 风险检查 | 开盘前5分钟 | 系统 | 风控参数 |
| 实盘监控 | 盘中 | 系统/人工 | 异常交易 |
| 盘后报告 | 盘后1小时内 | 系统 | 收益、风险指标 |
| 系统备份 | 每日20:00 | 系统 | 数据备份 |

#### 7.3.2 每周清单

| 任务 | 时间 | 执行人 | 说明 |
|-----|------|-------|------|
| 因子IC评估 | 周一 | 研究员 | 检查因子有效性 |
| 策略回顾 | 周五 | 研究员 | 策略表现分析 |
| 压力测试 | 周五 | 风控经理 | 极端情景测试 |
| 系统健康检查 | 周日 | 运维 | 磁盘、网络、依赖 |
| 报告生成 | 周日 | 系统 | 周度汇总报告 |

#### 7.3.3 每月清单

| 任务 | 时间 | 执行人 | 说明 |
|-----|------|-------|------|
| 月度报告 | 月初1-3日 | 系统 | 详细绩效报告 |
| 因子失效监控 | 月初 | 研究员 | 检查IC衰减 |
| 模型优化 | 每月中 | 研究员 | 参数调优 |
| 风险评估 | 每月末 | 风控经理 | 风险评估报告 |
| 归因分析 | 每月末 | 分析师 | 收益归因 |
| 系统维护 | 每月末 | 运维 | 更新、优化 |

#### 7.3.4 每季度清单

| 任务 | 时间 | 执行人 | 说明 |
|-----|------|-------|------|
| 季度报告 | 季度末 | 系统 | 季度总结 |
| 复盘会议 | 季度首周 | 团队 | 策略复盘 |
| 因子库更新 | 每季度中 | 研究员 | 新增/淘汰因子 |
| 风险限额调整 | 每季度末 | 决策层 | 根据市场调整 |
| 压力测试更新 | 每季度末 | 风控经理 | 更新测试情景 |

---

## 8. 待办事项与改进路线图

### 8.1 当前待解决问题（P0级）

#### 8.1.1 数据质量修复

**问题**：当前使用的是模拟数据，需要替换为真实A股数据。

**行动计划**：
1. **立即可行（1周内）**
   - [ ] 注册Tushare Pro账号
   - [ ] 申请API Token
   - [ ] 编写数据获取脚本
   - [ ] 下载真实历史数据（2019-2024，沪深300或中证500成分股）
   - [ ] 进行数据质量验证

2. **短期目标（2周内）**
   - [ ] 完成数据清洗流程
   - [ ] 处理停牌、除权除息
   - [ ] 建立数据更新机制
   - [ ] 进行幸存者偏差处理

3. **预期成果**
   - 真实、完整、准确的A股历史数据
   - 自动化数据更新管道
   - 数据质量监控系统

**工作量估算**：2-3人天
**责任人**：架构师 + 研究员

#### 8.1.2 过拟合风险缓解

**问题**：IC衰减分析显示存在中度过拟合风险。

**行动计划**：

1. **样本外验证（立即）**
   - [ ] 重新划分训练集/测试集（70%/30%）
   - [ ] 在测试集上评估策略表现
   - [ ] 记录样本内外表现差异

2. **参数敏感性分析（1周内）**
   - [ ] 对关键参数进行敏感性测试
   - [ ] 识别高敏感性参数
   - [ ] 对高敏感性参数进行正则化

3. **滚动窗口回测（2周内）**
   - [ ] 实现滚动窗口回测框架
   - [ ] 使用多个时间段验证策略稳定性
   - [ ] 统计策略在不同时期的表现分布

4. **因子有效性验证**
   - [ ] 对80+因子逐一进行有效性检验
   - [ ] 剔除IC<3%或IR<0.5的因子
   - [ ] 保留有效因子，淘汰失效因子

**预期成果**：
- 样本外验证报告
- 参数敏感性分析报告
- 滚动窗口回测报告
- 因子有效性评估报告

**工作量估算**：3-5人天
**责任人**：研究员

#### 8.1.3 交易成本模型完善

**问题**：回测未考虑交易成本，导致收益虚高。

**行动计划**：

1. **成本模型实现（立即）**
   - [ ] 实现交易成本计算模块
   - [ ] 包括：印花税、佣金、过户费、滑点
   - [ ] 集成到回测系统

2. **成本敏感性测试（1周内）**
   - [ ] 测试不同成本假设下的策略表现
   - [ ] 分析策略对成本的敏感性
   - [ ] 优化交易频率以降低成本

3. **冲击成本评估（2周内）**
   - [ ] 实现冲击成本模型
   - [ ] 测试不同资金规模下的策略表现
   - [ ] 评估策略最大容量

**预期成果**：
- 完整的交易成本模块
- 成本敏感性分析报告
- 策略容量评估报告

**工作量估算**：2-3人天
**责任人**：架构师

### 8.2 短期改进计划（1-3个月）

#### 8.2.1 基础设施完善

**目标**：搭建稳定的系统基础设施。

**任务清单**：

1. **数据管道（第1个月）**
   - [ ] 建立自动化数据获取流程
   - [ ] 实现数据质量监控
   - [ ] 搭建数据存储系统
   - [ ] 建立数据备份机制

2. **回测系统优化（第1个月）**
   - [ ] 优化回测性能
   - [ ] 增加更多评估指标
   - [ ] 实现多策略并行回测
   - [ ] 建立回测结果数据库

3. **监控系统搭建（第2个月）**
   - [ ] 实现实时监控面板
   - [ ] 建立多级警报系统
   - [ ] 实现异常检测算法
   - [ ] 建立历史数据查询系统

4. **风控系统强化（第2-3个月）**
   - [ ] 实现多级风控体系
   - [ ] 建立压力测试框架
   - [ ] 实现动态风险限额
   - [ ] 建立风险报告系统

**里程碑**：
- 第1个月末：数据管道和回测系统上线
- 第2个月末：监控系统上线
- 第3个月末：风控系统上线

**工作量估算**：15-20人天
**责任人**：架构师 + 运维

#### 8.2.2 因子体系优化

**目标**：建立高质量的因子库。

**任务清单**：

1. **因子有效性评估（第1个月）**
   - [ ] 对80+因子进行系统评估
   - [ ] 计算IC、IR、换手率等指标
   - [ ] 进行因子相关性分析
   - [ ] 识别并淘汰无效因子

2. **因子挖掘增强（第1-2个月）**
   - [ ] 实现遗传规划因子挖掘
   - [ ] 尝试OpenFE自动特征工程
   - [ ] 测试因子组合方法
   - [ ] 建立因子评估流程

3. **因子动态权重（第2-3个月）**
   - [ ] 实现基于IC的因子轮动
   - [ ] 测试风险平价因子配置
   - [ ] 建立因子权重优化模型
   - [ ] 实现自适应权重调整

**里程碑**：
- 第1个月末：完成因子有效性评估报告
- 第2个月末：新增10+有效因子
- 第3个月末：实现动态因子权重系统

**工作量估算**：10-15人天
**责任人**：研究员

#### 8.2.3 策略体系完善

**目标**：丰富策略库，提高策略鲁棒性。

**任务清单**：

1. **策略实现（第1-2个月）**
   - [ ] 实现趋势跟踪策略
   - [ ] 实现均值回归策略
   - [ ] 实现因子轮动策略
   - [ ] 实现行业轮动策略
   - [ ] 实现事件驱动策略

2. **策略组合（第2-3个月）**
   - [ ] 实现多策略组合框架
   - [ ] 测试不同组合方法
   - [ ] 优化组合权重
   - [ ] 建立策略评估体系

3. **实盘准备（第3个月）**
   - [ ] 搭建模拟盘环境
   - [ ] 进行小资金测试
   - [ ] 记录模拟盘与回测差异
   - [ ] 优化策略参数

**里程碑**：
- 第2个月末：完成5大类策略实现
- 第3个月末：模拟盘稳定运行

**工作量估算**：15-20人天
**责任人**：研究员 + 交易员

### 8.3 中期改进计划（3-6个月）

#### 8.3.1 自动化因子挖掘

**目标**：建立自动化因子挖掘系统。

**任务清单**：

1. **RD-Agent集成（第3-4个月）**
   - [ ] 安装Qlib平台
   - [ ] 配置RD-Agent环境
   - [ ] 测试自动化因子生成
   - [ ] 建立因子评估流程

2. **遗传规划优化（第4-5个月）**
   - [ ] 优化遗传规划参数
   - [ ] 扩展算子库
   - [ ] 实现并行计算
   - [ ] 建立因子库管理

3. **机器学习增强（第5-6个月）**
   - [ ] 测试随机森林/XGBoost
   - [ ] 尝试深度学习因子
   - [ ] 实现特征重要性分析
   - [ ] 建立模型选择流程

**里程碑**：
- 第4个月末：RD-Agent系统上线
- 第5个月末：遗传规划系统优化完成
- 第6个月末：机器学习增强系统上线

**工作量估算**：20-25人天
**责任人**：研究员 + 数据科学家

#### 8.3.2 智能监控系统

**目标**：建立智能化的监控和警报系统。

**任务清单**：

1. **异常检测（第3-4个月）**
   - [ ] 实现统计异常检测
   - [ ] 测试机器学习异常检测
   - [ ] 建立多维度监控
   - [ ] 优化警报阈值

2. **预测性维护（第4-5个月）**
   - [ ] 实现系统健康预测
   - [ ] 建立故障预警机制
   - [ ] 实现自动故障恢复
   - [ ] 建立维护计划

3. **智能报告（第5-6个月）**
   - [ ] 实现自动化报告生成
   - [ ] 建立归因分析系统
   - [ ] 实现智能诊断
   - [ ] 建立决策建议系统

**里程碑**：
- 第4个月末：异常检测系统上线
- 第5个月末：预测性维护系统上线
- 第6个月末：智能报告系统上线

**工作量估算**：15-20人天
**责任人**：运维 + 数据科学家

#### 8.3.3 实盘工程优化

**目标**：从模拟盘过渡到小资金实盘。

**任务清单**：

1. **模拟盘优化（第3-4个月）**
   - [ ] 优化模拟盘执行逻辑
   - [ ] 完善成本模型
   - [ ] 测试极端情况处理
   - [ ] 记录模拟盘表现

2. **实盘准备（第4-5个月）**
   - [ ] 选择券商和交易接口
   - [ ] 开发实盘交易模块
   - [ ] 建立实盘风控系统
   - [ ] 进行合规检查

3. **小资金实盘（第5-6个月）**
   - [ ] 启动10万级资金实盘
   - [ ] 监控实盘与模拟盘差异
   - [ ] 优化执行算法
   - [ ] 建立应急预案

**里程碑**：
- 第4个月末：模拟盘稳定运行3个月
- 第5个月末：实盘系统开发完成
- 第6个月末：小资金实盘启动

**工作量估算**：20-25人天
**责任人**：架构师 + 交易员

### 8.4 长期改进计划（6-12个月）

#### 8.4.1 系统性能优化

**目标**：提升系统处理能力和响应速度。

**任务清单**：

1. **并行计算（第6-8个月）**
   - [ ] 实现因子计算并行化
   - [ ] 优化回测引擎性能
   - [ ] 建立分布式计算框架
   - [ ] 测试GPU加速

2. **数据存储优化（第8-10个月）**
   - [ ] 优化数据库查询
   - [ ] 实现数据缓存
   - [ ] 建立数据分区
   - [ ] 测试不同存储方案

3. **系统架构优化（第10-12个月）**
   - [ ] 微服务化改造
   - [ ] 实现容器化部署
   - [ ] 建立CI/CD流程
   - [ ] 优化系统可扩展性

**预期成果**：
- 因子计算速度提升10倍
- 回测时间缩短50%
- 系统可处理1000+股票

**工作量估算**：30-40人天
**责任人**：架构师 + 运维

#### 8.4.2 策略扩展

**目标**：拓展策略覆盖范围。

**任务清单**：

1. **新策略开发（第6-9个月）**
   - [ ] 开发日内交易策略
   - [ ] 开发期权策略
   - [ ] 开发商品期货策略
   - [ ] 开发跨境套利策略

2. **多市场覆盖（第9-12个月）**
   - [ ] 港股市场策略
   - [ ] 美股市场策略
   - [ ] 债券市场策略
   - [ ] 跨市场对冲策略

**预期成果**：
- 策略库扩展到10+大类
- 覆盖A股、港股、美股市场
- 实现多资产配置

**工作量估算**：40-50人天
**责任人**：研究员团队

#### 8.4.3 量化研究平台

**目标**：建立完整的量化研究平台。

**任务清单**：

1. **研究工具（第6-8个月）**
   - [ ] 建立Jupyter研究环境
   - [ ] 实现可视化分析工具
   - [ ] 建立研究笔记本系统
   - [ ] 实现协作平台

2. **知识库（第8-10个月）**
   - [ ] 建立因子知识库
   - [ ] 建立策略知识库
   - [ ] 建立市场研究库
   - [ ] 建立风险管理库

3. **研究流程（第10-12个月）**
   - [ ] 建立研究工作流
   - [ ] 实现研究项目管理
   - [ ] 建立研究成果分享机制
   - [ ] 建立研究质量评估

**预期成果**：
- 完整的量化研究平台
- 丰富的知识库资源
- 高效的研究协作流程

**工作量估算**：25-30人天
**责任人**：架构师 + 研究员

### 8.5 改进路线图总览

```
时间轴：
├── 第1-2周：数据质量修复（P0）
├── 第3-4周：过拟合风险缓解（P0）
├── 第5-6周：交易成本模型完善（P0）
├── 第1个月：
│   ├── 数据管道搭建
│   ├── 回测系统优化
│   └── 因子有效性评估
├── 第2个月：
│   ├── 监控系统搭建
│   ├── 因子挖掘增强
│   └── 策略实现
├── 第3个月：
│   ├── 风控系统强化
│   ├── 因子动态权重
│   └── 策略组合与模拟盘
├── 第4-6个月：
│   ├── 自动化因子挖掘
│   ├── 智能监控系统
│   └── 实盘工程优化
└── 第7-12个月：
    ├── 系统性能优化
    ├── 策略扩展
    └── 量化研究平台
```

### 8.6 资源需求

#### 8.6.1 人力资源

| 角色 | 人数 | 工作内容 | 时间投入 |
|-----|------|---------|---------|
| 架构师 | 1 | 系统架构、基础设施 | 50% |
| 研究员 | 1-2 | 因子挖掘、策略开发 | 80% |
| 交易员 | 1 | 实盘执行、风险监控 | 30% |
| 运维 | 1 | 系统运维、监控 | 40% |
| 数据科学家 | 1 | 机器学习、数据分析 | 50% |

#### 8.6.2 技术资源

| 资源 | 规格 | 用途 | 成本估算 |
|-----|------|------|---------|
| 服务器 | 8核32G | 计算和存储 | ¥500/月 |
| 数据API | Tushare Pro | 行情数据 | 免费或¥200/月 |
| 云服务 | 按需 | 备份和监控 | ¥300/月 |
| 交易接口 | 券商提供 | 实盘交易 | 免费 |

#### 8.6.3 资金需求

| 项目 | 金额 | 说明 |
|-----|------|------|
| 数据成本 | ¥2,400/年 | 数据API费用 |
| 服务器成本 | ¥6,000/年 | 云服务器费用 |
| 研究工具 | ¥5,000/年 | 软件许可等 |
| 实盘资金 | ¥100,000+ | 小资金实盘测试 |
| **合计** | ¥113,400+ | 第一年预算 |

### 8.7 风险与应对

#### 8.7.1 技术风险

| 风险 | 概率 | 影响 | 应对措施 |
|-----|------|------|---------|
| 数据质量问题 | 中 | 高 | 多源数据备份，质量监控 |
| 系统故障 | 低 | 高 | 冗余设计，快速恢复 |
| 模型过拟合 | 高 | 中 | 严格验证，持续监控 |
| 策略失效 | 中 | 中 | 定期回顾，动态调整 |

#### 8.7.2 市场风险

| 风险 | 概率 | 影响 | 应对措施 |
|-----|------|------|---------|
| 极端行情 | 低 | 高 | 压力测试，止损机制 |
| 市场结构变化 | 中 | 中 | 持续监控，适应性调整 |
| 流动性危机 | 低 | 高 | 流动性监控，分批平仓 |
| 政策变化 | 中 | 中 | 政策监控，预案准备 |

#### 8.7.3 运营风险

| 风险 | 概率 | 影响 | 应对措施 |
|-----|------|------|---------|
| 人员变动 | 中 | 中 | 文档完善，知识共享 |
| 流程错误 | 低 | 中 | 流程检查，双人复核 |
| 合规问题 | 低 | 高 | 合规培训，法律咨询 |
| 资金不足 | 低 | 高 | 资金规划，备用资金 |

---

## 结语

本手册整合了A股量化系统的所有研究成果，从数据工程、因子体系、策略体系、回测系统、实盘工程到运维指南，形成了一套完整的系统文档。

### 核心要点回顾

1. **系统理念**：从"寻找圣杯"到"管理不确定性"
2. **五阶段框架**：数据工程 → 模型研发 → 回测验证 → 实盘工程 → 监控迭代
3. **因子体系**：80+因子，覆盖基本面、技术面、情绪、另类数据
4. **策略体系**：5大类策略，多样化组合
5. **风险管理**：多级风控，动态监控
6. **持续改进**：明确的改进路线图

### 下一步行动

**立即行动（本周）**：
1. 注册Tushare Pro，获取真实数据
2. 进行数据质量验证
3. 重新运行回测，验证过拟合风险

**短期行动（1个月内）**：
1. 完成数据管道搭建
2. 完善交易成本模型
3. 建立基础监控系统

**中期行动（3-6个月）**：
1. 启动模拟盘运行
2. 建立自动化因子挖掘系统
3. 完善风控体系

**长期目标（6-12个月）**：
1. 启动小资金实盘
2. 扩展策略体系
3. 建立完整的研究平台

### 最后的忠告

量化投资是一场马拉松，而非短跑。请牢记：

1. **数据是基础** - 没有好数据，一切模型都是空谈
2. **风控是核心** - 活下来比赚钱更重要
3. **持续迭代** - 市场在变，策略需要适应
4. **保持谦逊** - 市场永远是对的，模型可能会错
5. **管理预期** - 不追求暴利，追求长期稳定

祝您的量化之旅顺利！

---

**文档信息**：
- 编写日期：2026-02-28
- 版本：v1.0
- 编写人：创作者 ✍️
- 审核人：指挥官小龙虾🦞
- 更新记录：初始版本

---

## 附录

### 附录A：参考资料

1. **学术文献**
   - Fama, E. F., & French, K. R. (1993). Common risk factors in the returns on stocks and bonds.
   - Barra Risk Model Handbook
   - RD-Agent(Q)论文：https://arxiv.org/abs/2505.15155

2. **技术文档**
   - Qlib量化平台：https://github.com/microsoft/qlib
   - OpenFE特征工程：https://github.com/IIIS-Li-Group/OpenFE
   - gplearn遗传规划：https://github.com/trevorstephens/gplearn

3. **行业报告**
   - 华泰金工系列报告
   - 海通证券量化研究
   - BigQuant量化平台因子库

### 附录B：术语表

| 术语 | 英文 | 解释 |
|-----|------|------|
| 因子 | Factor | 能够预测股票未来收益的特征 |
| IC | Information Coefficient | 因子与未来收益率的相关系数 |
| IR | Information Ratio | IC均值/IC标准差，衡量因子稳定性 |
| 夏普比率 | Sharpe Ratio | (收益率-无风险利率)/波动率 |
| 最大回撤 | Maximum Drawdown | 组合净值从高点到低点的最大跌幅 |
| 换手率 | Turnover Rate | 一定时期内的交易量/持仓量 |
| 过拟合 | Overfitting | 模型在训练数据上表现好，但在新数据上表现差 |
| 幸存者偏差 | Survivorship Bias | 只考虑现存的股票，忽略已退市的股票 |
| 未来函数 | Look-ahead Bias | 使用未来数据导致的偏差 |
| 流动性 | Liquidity | 资产能够快速买卖而不影响价格的能力 |
| 冲击成本 | Market Impact | 大额交易对价格的影响 |
| 风险平价 | Risk Parity | 各资产风险贡献相等的配置方法 |

### 附录C：常用Python库

```python
# 数据获取
import tushare as ts
import akshare as ak
import baostock as bs

# 数据处理
import pandas as pd
import numpy as np
from scipy import stats

# 因子计算
from scipy.stats import spearmanr
import statsmodels.api as sm

# 机器学习
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
import xgboost as xgb

# 遗传规划
from gplearn.genetic import SymbolicRegressor

# 可视化
import matplotlib.pyplot as plt
import seaborn as sns

# 回测
import backtrader as bt
# 或使用Qlib
from qlib.workflow import R

# 优化
import cvxpy as cp
from scipy.optimize import minimize
```

### 附录D：检查清单模板

**每日检查清单**：
- [ ] 数据更新成功
- [ ] 因子计算完成
- [ ] 信号生成合理
- [ ] 风控参数正常
- [ ] 订单执行正常
- [ ] 持仓检查完成
- [ ] 绩效计算完成
- [ ] 报告生成完成

**每周检查清单**：
- [ ] 因子IC评估
- [ ] 策略表现回顾
- [ ] 风险指标检查
- [ ] 系统健康检查
- [ ] 备份完成

**每月检查清单**：
- [ ] 月度报告生成
- [ ] 因子有效性评估
- [ ] 风险评估
- [ ] 归因分析
- [ ] 参数优化建议

---

## 9. 系统改进计划（2026-03-02更新）

### 9.1 推送连续性改造

#### 问题诊断
- 当前推送是"单次推送"，没有跟踪持仓状态
- 用户看不到"昨日建议→今日执行→明日调整"的闭环
- 缺乏换仓决策逻辑

#### 解决方案

**1. 持仓跟踪系统**
- 创建 `portfolio_tracker.py`
- 记录每日持仓状态（股票代码、成本价、当前价、收益率、持仓天数）
- 记录建仓/加仓/减仓/清仓决策
- 生成持仓日报

**2. 推送内容改造**
推送增加内容：
- **昨日回顾**：昨日建议 vs 实际执行情况
- **今日持仓**：当前持仓列表、收益率、持仓天数
- **今日决策**：建仓/加仓/减仓/清仓建议
- **换仓逻辑**：收益>20%或亏损>10%，建议换仓
- **明日计划**：明天操作计划

**3. 数据持久化**
- 创建 `portfolio_state.json`
- 记录每日收盘后持仓状态
- 支持复盘和绩效归因

### 9.2 选股质量提升

#### 问题诊断
- Top 5都是大盘蓝筹（宁德时代、茅台、五粮液）
- 这些股票α收益有限，主要是β收益
- 缺乏"低估+高α"的股票筛选机制

#### 解决方案

**1. α因子筛选模块**
- 创建 `alpha_stock_selector.py`
- 因子有效性验证：IC>5%、IR>1.0
- 行业中性化处理
- 避免因子冗余（相关性<0.7）

**2. 低估+高α筛选**
筛选逻辑：
- 低估条件：PB<行业均值、PE<行业均值、PEG<1
- 高α条件：α因子得分>80分
- 流动性条件：日均成交额>5000万
- 市值限制：剔除市值>5000亿的大盘蓝筹

**3. 组合构建优化**
- 核心持仓（60%）：5只高α+低估股票
- 卫星持仓（20%）：2只行业轮动股票
- 现金（20%）：应对加仓和风险

### 9.3 换仓策略开发

#### 换仓触发条件
- 止盈触发：收益>20%，分批止盈
- 止损触发：亏损>10%，立即止损
- 时间触发：持仓>60天，评估是否换仓
- 因子触发：α因子得分下降>20%，考虑换仓

#### 换仓决策逻辑
- 换仓时机：收盘前30分钟决策
- 换仓目标：从备选股票池选择替代股票
- 换仓执行：分批执行，避免冲击成本

### 9.4 实盘跟踪与绩效归因

#### 每日记录
- 创建 `daily_performance.json`
- 记录每日收益率、沪深300基准收益率
- 记录每日持仓变化、交易决策
- 记录每日因子表现

#### 月度归因
- 创建 `monthly_attribution.py`
- Brinson归因分析
- 因子收益归因
- 行业/风格归因

### 9.5 验证要求

#### 回测验证
- 使用真实数据（akshare_real_data_fixed.pkl）
- 回测2019-2024年完整数据
- 计算年化收益、夏普比率、最大回撤

#### 样本外验证
- 2023-2024年数据验证
- 验证换仓策略有效性

#### 实盘准备
- 模拟盘运行7天
- 每日记录决策和绩效
- 月底绩效归因分析

---

## 10. 数据工程优化

### 10.1 数据质量提升
- **多源数据验证**：Tushare、AKShare、Baostock交叉验证
- **数据质量监控**：自动化数据质量检查脚本
- **实时监控数据异常**

### 10.2 数据处理流程优化
- **完善幸存者偏差处理**：确保回测数据包含已退市股票
- **优化未来函数检测**：建立严格的未来数据使用检查机制
- **增强流动性过滤**：根据不同资金规模动态调整流动性阈值

---

## 11. 因子体系改进

### 11.1 因子有效性评估
- **系统性因子筛选**：对80+因子进行全面评估，淘汰IC<3%或IR<0.5的因子
- **因子相关性分析**：识别高度相关的因子，避免因子冗余
- **行业中性化**：对因子进行行业中性化处理，减少行业暴露

### 11.2 因子挖掘增强
- **引入深度学习因子**：使用LSTM、Transformer等模型挖掘非线性因子
- **开发高阶因子**：基于基础因子构建复合因子
- **实现动态因子权重**：根据市场环境自动调整因子权重

---

## 12. 策略体系优化

### 12.1 策略多样性
- **开发日内交易策略**：利用日内数据捕捉短期机会
- **增加对冲策略**：开发市场中性策略，降低系统性风险
- **拓展跨市场策略**：考虑港股、美股等市场的联动机会

### 12.2 策略组合优化
- **实现风险平价组合**：确保各策略风险贡献相等
- **动态策略配置**：根据市场环境自动调整策略权重
- **策略绩效归因**：建立详细的策略归因分析系统

---

## 13. 回测系统完善

### 13.1 成本模型优化
- **精确计算交易成本**：包括印花税、佣金、过户费、滑点
- **冲击成本模型**：根据资金规模和股票流动性计算冲击成本
- **成本敏感性分析**：评估不同成本假设下的策略表现

### 13.2 回测框架改进
- **实现并行回测**：利用多核计算加速回测过程
- **滚动窗口回测**：使用多个时间段验证策略稳定性
- **情景分析**：测试策略在不同市场环境下的表现

---

## 14. 实盘工程准备

### 14.1 模拟盘优化
- **模拟真实交易环境**：包括交易延迟、部分成交等情况
- **记录模拟盘与回测差异**：分析并调整模型参数
- **压力测试**：测试极端市场情况下的系统表现

### 14.2 风控系统强化
- **多级风控体系**：事前、事中、事后风控检查
- **动态止损机制**：根据市场波动率调整止损阈值
- **风险限额管理**：建立基于VaR的风险限额体系

---

## 15. 系统架构改进

### 15.1 系统性能优化
- **并行计算**：实现因子计算和回测的并行处理
- **数据存储优化**：使用列式数据库提高查询效率
- **缓存机制**：对频繁访问的数据建立缓存

### 15.2 监控与告警
- **实时监控面板**：可视化展示组合绩效和风险指标
- **智能告警系统**：基于机器学习的异常检测
- **自动故障恢复**：建立系统故障自动恢复机制

---

## 16. 研究平台建设

### 16.1 研究工具
- **Jupyter研究环境**：搭建统一的研究环境
- **可视化分析工具**：开发因子和策略分析的可视化工具
- **研究协作平台**：支持团队协作和知识共享

### 16.2 知识库建设
- **因子知识库**：记录因子的历史表现和使用方法
- **策略知识库**：存储策略代码和绩效分析
- **市场研究库**：收集市场分析和行业研究

---

## 17. 实施路线图

### 近期（1-2周）
1. ✅ 替换为真实A股数据（已完成）
2. ✅ 完善交易成本模型（已完成）
3. 🔄 建立基础监控系统（进行中）
4. 🔄 启动模拟盘运行（进行中）

### 中期（1-2个月）
1. 实现自动化因子挖掘
2. 完善风控体系
3. 启动小资金实盘
4. 开发智能监控系统

### 长期（3-6个月）
1. 系统性能优化
2. 拓展策略体系
3. 建立完整的量化研究平台
4. 实现多市场覆盖

---

## 18. 风险控制

### 技术风险
- **数据质量问题**：多源数据备份，质量监控
- **系统故障**：冗余设计，快速恢复
- **模型过拟合**：严格验证，持续监控
- **策略失效**：定期回顾，动态调整

### 市场风险
- **极端行情**：压力测试，止损机制
- **市场结构变化**：持续监控，适应性调整
- **流动性危机**：流动性监控，分批平仓
- **政策变化**：政策监控，预案准备

---

**文档结束**

© 2026 A股量化系统团队

最后更新：2026-03-02 02:30
