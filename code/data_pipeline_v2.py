#!/usr/bin/env python3
"""
A股真实数据获取与数据工程流水线 V2
- 简化版本，只处理主板股票
- 更好的错误处理

作者: 研究员
日期: 2026-02-28
"""

import akshare as ak
import pandas as pd
import numpy as np
import pickle
import time
import os
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/data_pipeline_v2.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 工作目录
WORK_DIR = '/Users/variya/.openclaw/workspace/projects/a-stock-advisor'
os.chdir(WORK_DIR)

# 数据配置
START_DATE = '20190101'
END_DATE = '20241231'
MIN_AMOUNT = 1000000  # 最小成交额

def get_main_board_stocks():
    """获取主板股票列表"""
    # 硬编码主板热门股票（避免网络问题）
    stocks = [
        ('000001', '平安银行'), ('000002', '万科A'), ('000063', '中兴通讯'),
        ('000333', '美的集团'), ('000651', '格力电器'), ('000858', '五粮液'),
        ('002142', '宁波银行'), ('002415', '海康威视'), ('002594', '比亚迪'),
        ('600000', '浦发银行'), ('600036', '招商银行'), ('600519', '贵州茅台'),
        ('600900', '长江电力'), ('601318', '中国平安'), ('601888', '中国中免'),
        ('601939', '建设银行'), ('603259', '药明康德'), ('600276', '恒瑞医药'),
        ('601166', '兴业银行'), ('601818', '光大银行'), ('600030', '中信证券'),
        ('601211', '国泰君安'), ('601398', '工商银行'), ('601288', '农业银行'),
        ('600016', '民生银行'), ('600009', '上海机场'), ('601012', '隆基绿能'),
        ('002714', '牧原股份'), ('300750', '宁德时代'), ('002352', '顺丰控股'),
        ('600887', '伊利股份'), ('000568', '泸州老窖'), ('002304', '洋河股份'),
        ('000596', '古井贡酒'), ('600809', '山西汾酒'), ('002475', '立讯精密'),
        ('002460', '赣锋锂业'), ('002129', '中环股份'), ('600438', '通威股份'),
        ('601899', '紫金矿业'), ('600111', '包钢股份'), ('601225', '陕西煤业'),
        ('601088', '中国神华'), ('600028', '中国石化'), ('601857', '中国石油'),
    ]
    return pd.DataFrame(stocks, columns=['代码', '名称'])

def fetch_single_stock_data(stock_code, stock_name):
    """获取单只股票数据"""
    try:
        hist_data = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=START_DATE,
            end_date=END_DATE,
            adjust="qfq"
        )
        
        if hist_data is None or len(hist_data) == 0:
            return None
            
        # 重命名列
        hist_data = hist_data.rename(columns={
            '日期': 'date', '开盘': 'open', '收盘': 'close',
            '最高': 'high', '最低': 'low', '成交量': 'volume',
            '成交额': 'amount', '振幅': 'amplitude',
            '涨跌幅': 'change_pct', '涨跌额': 'change_amount',
            '换手率': 'turnover'
        })
        
        # 添加股票信息
        hist_data['stock_code'] = stock_code
        hist_data['stock_name'] = stock_name
        hist_data['date'] = pd.to_datetime(hist_data['date'])
        hist_data['date_str'] = hist_data['date'].dt.strftime('%Y-%m-%d')
        
        logger.info(f"  ✓ [{stock_code}] {stock_name}: {len(hist_data)} 条")
        return hist_data
        
    except Exception as e:
        logger.warning(f"  ✗ [{stock_code}] {stock_name}: {str(e)[:80]}")
        return None

def calculate_factors(df):
    """计算因子"""
    df = df.sort_values('date').reset_index(drop=True)
    
    # 动量因子
    df['momentum_20'] = df['close'].pct_change(20)
    df['momentum_60'] = df['close'].pct_change(60)
    
    # 波动率
    df['volatility_20'] = df['close'].pct_change().rolling(20).std()
    
    # 均线
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    
    # 相对位置
    df['price_to_ma20'] = df['close'] / df['ma20'] - 1
    df['price_to_ma60'] = df['close'] / df['ma60'] - 1
    
    # 布林带
    df['bb_middle'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 0.001)
    
    # 换手率均值
    df['turnover_mean_20'] = df['turnover'].rolling(20).mean()
    
    # 下移因子（消除未来函数）
    factor_cols = ['momentum_20', 'momentum_60', 'volatility_20', 'ma5', 'ma20', 'ma60',
                   'price_to_ma20', 'price_to_ma60', 'bb_position', 'turnover_mean_20']
    for col in factor_cols:
        if col in df.columns:
            df[col] = df[col].shift(1)
    
    return df

def create_factor_score(df):
    """创建因子得分"""
    factor_cols = ['momentum_20', 'price_to_ma20', 'bb_position', 'volatility_20']
    
    # 检查因子是否存在
    available = [f for f in factor_cols if f in df.columns]
    
    if len(available) < 2:
        df['factor_score'] = 0
        return df
    
    # 标准化
    for factor in available:
        mean = df[factor].mean()
        std = df[factor].std()
        if std > 0:
            df[f'{factor}_norm'] = (df[factor] - mean) / std
        else:
            df[f'{factor}_norm'] = 0
    
    # 综合得分
    norm_cols = [f'{f}_norm' for f in available]
    df['factor_score'] = df[norm_cols].mean(axis=1)
    
    return df

def main():
    logger.info("=" * 70)
    logger.info("A股量化系统 - 真实数据获取 V2")
    logger.info("=" * 70)
    
    # 获取股票列表
    logger.info("📋 使用硬编码主板股票列表...")
    stock_list = get_main_board_stocks()
    logger.info(f"  共 {len(stock_list)} 只股票")
    
    # 获取数据
    all_data = []
    success = 0
    failed = 0
    
    for idx, row in stock_list.iterrows():
        code = row['代码']
        name = row['名称']
        
        logger.info(f"  处理 [{idx+1}/{len(stock_list)}]: {code} {name}")
        
        data = fetch_single_stock_data(code, name)
        
        if data is not None:
            # 计算因子
            data = calculate_factors(data)
            data = create_factor_score(data)
            all_data.append(data)
            success += 1
        else:
            failed += 1
        
        time.sleep(0.3)  # 控制频率
    
    logger.info(f"\n获取完成: 成功={success}, 失败={failed}")
    
    if len(all_data) == 0:
        logger.error("❌ 没有获取到任何数据！")
        return
    
    # 合并数据
    logger.info("🔗 合并数据...")
    combined = pd.concat(all_data, ignore_index=True)
    
    # 添加月份列
    combined['month'] = combined['date'].dt.strftime('%Y-%m')
    
    # 流动性过滤
    initial = len(combined)
    combined = combined[combined['amount'] >= MIN_AMOUNT]
    logger.info(f"  流动性过滤: {initial} -> {len(combined)}")
    
    # 保存数据
    output_file = 'data/real_stock_data.pkl'
    logger.info(f"💾 保存数据到 {output_file}...")
    
    os.makedirs('data', exist_ok=True)
    with open(output_file, 'wb') as f:
        pickle.dump(combined, f)
    
    # 数据摘要
    logger.info("\n" + "=" * 70)
    logger.info("✓ 数据工程完成！")
    logger.info("=" * 70)
    logger.info(f"📊 数据摘要:")
    logger.info(f"  - 总记录数: {len(combined):,}")
    logger.info(f"  - 股票数量: {combined['stock_code'].nunique()}")
    logger.info(f"  - 时间范围: {combined['date_str'].min()} 至 {combined['date_str'].max()}")
    logger.info(f"  - 月份数量: {combined['month'].nunique()}")
    logger.info(f"  - 数据文件: {output_file}")
    
    # 保存元数据
    metadata = {
        'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'success_count': success,
        'failed_count': failed,
        'total_records': len(combined),
        'stock_count': combined['stock_code'].nunique(),
        'date_range': f"{combined['date_str'].min()} to {combined['date_str'].max()}",
        'month_count': combined['month'].nunique(),
    }
    
    import json
    with open('data/real_stock_data_metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    logger.info("=" * 70)

if __name__ == '__main__':
    main()
