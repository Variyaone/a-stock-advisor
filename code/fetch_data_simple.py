#!/usr/bin/env python3
"""
简化版A股数据获取脚本
- 直接使用硬编码的沪深300+主要A股列表
- 多次重试机制
- 自动保存进度

作者: 研究员
日期: 2026-03-02
"""

import os
import sys
import time

# 工作目录
WORK_DIR = '/Users/variya/.openclaw/workspace/projects/a-stock-advisor'
os.chdir(WORK_DIR)

import pandas as pd
import numpy as np
import pickle
import json
import logging
from datetime import datetime
from typing import Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/fetch_simple.log', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 数据配置
START_DATE = '2019-01-01'
END_DATE = '2024-12-31'
MIN_AMOUNT = 1000000

# A股主要股票列表（沪深300成分股 + 重要股票，约150只）
STOCK_LIST = [
    # 沪深300主要成分股
    ('600519', '贵州茅台'), ('600036', '招商银行'), ('601318', '中国平安'),
    ('000858', '五粮液'), ('000333', '美的集团'), ('000651', '格力电器'),
    ('601166', '兴业银行'), ('600000', '浦发银行'), ('601398', '工商银行'),
    ('601288', '农业银行'), ('601939', '建设银行'), ('601988', '中国银行'),
    ('600030', '中信证券'), ('600276', '恒瑞医药'), ('000002', '万科A'),
    ('002594', '比亚迪'), ('601888', '中国中免'), ('002415', '海康威视'),
    ('600900', '长江电力'), ('601012', '隆基绿能'), ('603259', '药明康德'),
    ('600031', '三一重工'), ('601818', '光大银行'), ('601328', '交通银行'),
    ('000001', '平安银行'), ('600009', '上海机场'), ('601857', '中国石油'),
    ('601088', '中国神华'), ('600019', '宝钢股份'), ('600585', '海螺水泥'),
    ('600016', '民生银行'), ('601601', '中国太保'), ('601628', '中国人寿'),
    ('601668', '中国建筑'), ('601766', '中国中车'), ('601800', '中国交建'),
    ('600048', '保利发展'), ('600111', '北方稀土'), ('600150', '中国船舶'),
    ('600309', '万华化学'), ('600346', '恒力石化'), ('600438', '通威股份'),
    ('600690', '海尔智家'), ('600809', '山西汾酒'), ('601138', '工业富联'),
    ('601236', '红塔证券'), ('601555', '东吴证券'), ('601688', '华泰证券'),
    ('601788', '光大证券'), ('601881', '中国银河'), ('601901', '方正证券'),
    ('601985', '中国核电'), ('601919', '中远海控'), ('601998', '中信银行'),
    ('603288', '海天味业'), ('603501', '韦尔股份'), ('603986', '兆易创新'),
    ('000063', '中兴通讯'), ('000157', '中联重科'), ('000338', '潍柴动力'),
    ('000425', '徐工机械'), ('000568', '泸州老窖'), ('000625', '长安汽车'),
    ('000703', '世纪华通'), ('000725', '京东方A'), ('000768', '中航西飞'),
    ('000776', '广发证券'), ('000876', '新希望'), ('000895', '双汇发展'),
    ('001979', '招商蛇口'), ('002007', '华兰生物'), ('002027', '分众传媒'),
    ('002049', '紫光国微'), ('002129', 'TCL中环'), ('002142', '宁波银行'),
    ('002230', '科大讯飞'), ('002236', '大华股份'), ('002304', '洋河股份'),
    ('002352', '顺丰控股'), ('002410', '广联达'), ('002475', '立讯精密'),
    ('002493', '荣盛石化'), ('002555', '三七互娱'), ('002600', '领益智造'),
    ('002624', '完美世界'), ('002714', '牧原股份'), ('002739', '万达电影'),
    ('002812', '恩捷股份'), ('002841', '视源股份'), ('003816', '中国广核'),
    # 科创板龙头
    ('688981', '中芯国际'), ('688111', '金山办公'), ('688012', '中微公司'),
    ('688008', '澜起科技'), ('688126', '沪硅产业'), ('688561', '奇安信'),
    # 创业板龙头
    ('300750', '宁德时代'), ('300059', '东方财富'), ('300015', '爱尔眼科'),
    ('300033', '同花顺'), ('300124', '汇川技术'), ('300144', '宋城演艺'),
    ('300223', '北京君正'), ('300274', '阳光电源'), ('300308', '中际旭创'),
    ('31300', '迈瑞医疗'), ('300433', '蓝思科技'), ('300454', '深信服'),
    ('300496', '中科创达'), ('300595', '欧普康视'), ('300628', '亿联网络'),
    ('300661', '圣邦股份'), ('300750', '宁德时代'), ('300760', '迈瑞医疗'),
    ('300896', '爱美客'), ('300999', '金龙鱼'),
]


def fetch_single_stock(stock_code: str, stock_name: str, max_retries: int = 5) -> Optional[pd.DataFrame]:
    """获取单只股票数据（多次重试）"""
    import akshare as ak
    
    for attempt in range(max_retries):
        try:
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date="20190101",
                end_date="20241231",
                adjust="qfq"
            )
            
            if df is None or len(df) == 0:
                time.sleep(2)
                continue
            
            # 添加股票信息
            df['stock_code'] = stock_code
            df['stock_name'] = stock_name
            
            # 标准化列名
            column_mapping = {
                '日期': 'date', '开盘': 'open', '收盘': 'close',
                '最高': 'high', '最低': 'low', '成交量': 'volume',
                '成交额': 'amount', '振幅': 'amplitude',
                '涨跌幅': 'change_pct', '涨跌额': 'change_amount',
                '换手率': 'turnover'
            }
            df = df.rename(columns=column_mapping)
            
            # 日期格式
            if '日期' in df.columns:
                df['date'] = pd.to_datetime(df['日期']).dt.strftime('%Y-%m-%d')
            elif 'date' not in df.columns:
                # 查找可能的日期列
                for col in df.columns:
                    if '日期' in str(col) or 'date' in str(col).lower():
                        df['date'] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d')
                        break
            
            # 确保数值列正确
            numeric_cols = ['open', 'close', 'high', 'low', 'volume', 'amount', 'change_pct', 'turnover']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
            
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                logger.debug(f"  {stock_code} 第{attempt+1}次失败，等待{wait_time}秒...")
                time.sleep(wait_time)
            else:
                logger.warning(f"  ✗ {stock_code} {stock_name}: 获取失败 - {e}")
                return None
    
    return None


def calculate_factors(df: pd.DataFrame) -> pd.DataFrame:
    """计算技术因子"""
    df = df.sort_values('date').copy()
    
    # 基础因子
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    
    df['momentum_5'] = df['close'].pct_change(5)
    df['momentum_10'] = df['close'].pct_change(10)
    df['momentum_20'] = df['close'].pct_change(20)
    
    df['volatility_10'] = df['close'].pct_change().rolling(10).std()
    df['volatility_20'] = df['close'].pct_change().rolling(20).std()
    
    if 'turnover' in df.columns and df['turnover'].notna().any():
        df['turnover_ma5'] = df['turnover'].rolling(5).mean()
        df['turnover_ma20'] = df['turnover'].rolling(20).mean()
    
    df['amount_ma5'] = df['amount'].rolling(5).mean()
    df['amount_ma20'] = df['amount'].rolling(20).mean()
    
    df['price_to_ma20'] = df['close'] / df['ma20'] - 1
    
    # 消除未来函数（因子下移）
    factor_cols = ['ma5', 'ma10', 'ma20', 'ma60', 'momentum_5', 'momentum_10', 
                   'momentum_20', 'volatility_10', 'volatility_20', 
                   'turnover_ma5', 'turnover_ma20', 'amount_ma5', 'amount_ma20', 'price_to_ma20']
    for col in factor_cols:
        if col in df.columns:
            df[col] = df[col].shift(1)
    
    return df


def main():
    """主函数"""
    logger.info("=" * 70)
    logger.info("简化版A股数据获取工具")
    logger.info("=" * 70)
    
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    all_data = []
    success_count = 0
    fail_count = 0
    
    total = len(STOCK_LIST)
    
    for idx, (code, name) in enumerate(STOCK_LIST):
        logger.info(f"[{idx+1}/{total}] {code} {name}...")
        
        df = fetch_single_stock(code, name)
        
        if df is not None and len(df) >= 50:
            # 计算因子
            df = calculate_factors(df)
            
            # 日期过滤
            start = '2019-01-01'
            end = '2024-12-31'
            df = df[(df['date'] >= start) & (df['date'] <= end)]
            
            # 流动性过滤
            if 'amount' in df.columns:
                df = df[df['amount'] >= MIN_AMOUNT]
            
            if len(df) >= 50:
                all_data.append(df)
                success_count += 1
                logger.info(f"  ✓ 成功: {len(df)} 条记录")
            else:
                fail_count += 1
                logger.warning(f"  ⚠ 数据不足")
        else:
            fail_count += 1
        
        # 控制频率
        time.sleep(0.5)
    
    if not all_data:
        logger.error("✗ 没有获取到任何数据")
        return 1
    
    # 合并数据
    combined = pd.concat(all_data, ignore_index=True)
    
    # 添加月份
    combined['date_dt'] = pd.to_datetime(combined['date'])
    combined['month'] = combined['date_dt'].dt.strftime('%Y-%m')
    
    # 保存
    output_file = 'data/real_stock_data.pkl'
    
    metadata = {
        'source': 'akshare_real',
        'start_date': START_DATE,
        'end_date': END_DATE,
        'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'success_count': success_count,
        'fail_count': fail_count,
        'total_records': len(combined),
        'unique_stocks': int(combined['stock_code'].nunique()),
        'date_range': f"{combined['date'].min()} to {combined['date'].max()}"
    }
    
    # 保存数据
    with open(output_file, 'wb') as f:
        pickle.dump(combined, f)
    
    # 保存元数据
    with open(output_file.replace('.pkl', '_metadata.json'), 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    logger.info("\n" + "=" * 70)
    logger.info(f"✓ 数据获取完成!")
    logger.info(f"  - 成功: {success_count} 只股票")
    logger.info(f"  - 失败: {fail_count} 只股票")
    logger.info(f"  - 总记录: {len(combined):,} 条")
    logger.info(f"  - 时间范围: {combined['date'].min()} ~ {combined['date'].max()}")
    logger.info(f"  - 已保存到: {output_file}")
    logger.info("=" * 70)
    
    return 0


if __name__ == '__main__':
    exit(main())
