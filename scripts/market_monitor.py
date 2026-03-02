#!/usr/bin/env python3
"""
市场状态监控脚本
功能：监控跌停股票数量、流动性、市场情绪，检测极端情况，生成市场状态报告
"""

import sys
import os
import json
import pickle as pkl
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class MarketMonitor:
    """市场状态监控器"""

    def __init__(self):
        """初始化"""
        self.data_file = 'data/akshare_real_data_fixed.pkl'
        self.market_report_file = 'reports/daily_market_report.json'

        # 阈值配置（基于设计文档）
        self.thresholds = {
            'limit_down_count': 1000,  # 千股跌停阈值
            'liquidity_ratio': 0.3,    # 流动性枯竭阈值（低于5日均量的30%）
            'sentiment_ratio': 5,       # 恐慌阈值（涨跌停比例 > 5:1）
        }

    def load_stock_data(self) -> pd.DataFrame:
        """加载股票数据"""
        try:
            with open(self.data_file, 'rb') as f:
                df = pkl.load(f)
            return df
        except Exception as e:
            print(f"加载数据失败: {e}")
            return pd.DataFrame()

    def count_limit_down_stocks(self, stock_data: pd.DataFrame) -> Dict:
        """
        统计跌停股票数量

        Args:
            stock_data: 股票数据

        Returns:
            跌停统计信息
        """
        if len(stock_data) == 0:
            return {'count': 0, 'ratio': 0, 'status': '无数据', 'level': 'info'}

        # 获取最新日期数据
        if 'date_dt' in stock_data.columns:
            latest_date = stock_data['date_dt'].max()
            latest_df = stock_data[stock_data['date_dt'] == latest_date].copy()
        else:
            latest_df = stock_data.copy()

        # 统计跌停股票（跌幅 >= 9.9% 且 涨跌幅 < -9%）
        if 'change_pct' in latest_df.columns:
            limit_down = latest_df[latest_df['change_pct'] < -9.9]
        elif 'pct_chg' in latest_df.columns:
            limit_down = latest_df[latest_df['pct_chg'] < -9.9]
        else:
            return {'count': 0, 'ratio': 0, 'status': '无涨跌幅数据', 'level': 'warning'}

        count = len(limit_down)
        total = len(latest_df)
        ratio = count / total * 100 if total > 0 else 0

        # 判断状态
        if count > self.thresholds['limit_down_count']:
            status = '极端'
            level = 'danger'
        elif count > 500:
            status = '危险'
            level = 'danger'
        elif count > 100:
            status = '警告'
            level = 'warning'
        else:
            status = '正常'
            level = 'info'

        return {
            'count': count,
            'ratio': round(ratio, 2),
            'status': status,
            'level': level,
            'threshold': self.thresholds['limit_down_count']
        }

    def count_limit_up_stocks(self, stock_data: pd.DataFrame) -> Dict:
        """
        统计涨停股票数量

        Args:
            stock_data: 股票数据

        Returns:
            涨停统计信息
        """
        if len(stock_data) == 0:
            return {'count': 0, 'ratio': 0, 'status': '无数据', 'level': 'info'}

        # 获取最新日期数据
        if 'date_dt' in stock_data.columns:
            latest_date = stock_data['date_dt'].max()
            latest_df = stock_data[stock_data['date_dt'] == latest_date].copy()
        else:
            latest_df = stock_data.copy()

        # 统计涨停股票（涨幅 >= 9.9%）
        if 'change_pct' in latest_df.columns:
            limit_up = latest_df[latest_df['change_pct'] > 9.9]
        elif 'pct_chg' in latest_df.columns:
            limit_up = latest_df[latest_df['pct_chg'] > 9.9]
        else:
            return {'count': 0, 'ratio': 0, 'status': '无涨跌幅数据', 'level': 'warning'}

        count = len(limit_up)
        total = len(latest_df)
        ratio = count / total * 100 if total > 0 else 0

        return {
            'count': count,
            'ratio': round(ratio, 2)
        }

    def check_liquidity(self, stock_data: pd.DataFrame) -> Dict:
        """
        检查流动性（成交量）

        Args:
            stock_data: 股票数据

        Returns:
            流动性信息
        """
        if len(stock_data) == 0:
            return {'status': '无数据', 'level': 'info', 'liquidity_ratio': 100}

        # 获取最新日期数据和5日平均
        if 'date_dt' in stock_data.columns and 'amount' in stock_data.columns:
            latest_date = stock_data['date_dt'].max()
            latest_df = stock_data[stock_data['date_dt'] == latest_date].copy()

            # 获取最近5个交易日
            recent_dates = stock_data['date_dt'].unique()
            recent_dates = sorted(recent_dates)[-6:]  # 最新日期+5个历史日期

            # 计算5日平均成交量
            avg_amount = stock_data[stock_data['date_dt'].isin(recent_dates[:-1])]['amount'].mean()

            if avg_amount == 0:
                return {'status': '无历史数据', 'level': 'warning', 'liquidity_ratio': 0}

            current_amount = latest_df['amount'].sum()
            liquidity_ratio = current_amount / avg_amount

            # 判断状态
            if liquidity_ratio < self.thresholds['liquidity_ratio']:
                status = '枯竭'
                level = 'danger'
            elif liquidity_ratio < 0.5:
                status = '紧张'
                level = 'warning'
            else:
                status = '正常'
                level = 'info'

            return {
                'status': status,
                'level': level,
                'current_amount': float(current_amount),
                'avg_amount': float(avg_amount),
                'liquidity_ratio': round(liquidity_ratio, 2)
            }
        else:
            return {'status': '无成交量数据', 'level': 'warning', 'liquidity_ratio': 100}

    def check_market_sentiment(self, stock_data: pd.DataFrame) -> Dict:
        """
        检查市场情绪（涨跌停比例）

        Args:
            stock_data: 股票数据

        Returns:
            市场情绪信息
        """
        limit_down = self.count_limit_down_stocks(stock_data)
        limit_up = self.count_limit_up_stocks(stock_data)

        down_count = limit_down['count']
        up_count = limit_up['count']

        # 计算涨跌停比例（跌停/涨停）
        if up_count > 0:
            ratio = down_count / up_count
        else:
            ratio = float('inf') if down_count > 0 else 0

        # 判断情绪
        if ratio > self.thresholds['sentiment_ratio']:
            sentiment = '恐慌'
            level = 'danger'
        elif ratio > 2:
            sentiment = '悲观'
            level = 'warning'
        elif ratio < 0.2:
            sentiment = '亢奋'
            level = 'warning'
        else:
            sentiment = '中性'
            level = 'info'

        return {
            'sentiment': sentiment,
            'level': level,
            'limit_up': up_count,
            'limit_down': down_count,
            'ratio': round(ratio, 2),
            'threshold': self.thresholds['sentiment_ratio']
        }

    def detect_extreme_conditions(self, stock_data: pd.DataFrame) -> Dict:
        """
        检测极端市场情况

        Args:
            stock_data: 股票数据

        Returns:
            极端情况列表
        """
        conditions = []

        # 检测千股跌停
        limit_down = self.count_limit_down_stocks(stock_data)
        if limit_down['level'] == 'danger':
            conditions.append({
                'type': '千股跌停',
                'severity': 'extreme',
                'description': f"跌停股票数量({limit_down['count']})超过阈值({limit_down['threshold']})",
                'action': '立即暂停所有交易'
            })

        # 检测流动性枯竭
        liquidity = self.check_liquidity(stock_data)
        if liquidity['level'] == 'danger':
            conditions.append({
                'type': '流动性枯竭',
                'severity': 'extreme',
                'description': f"当前成交量仅为5日均量的{liquidity['liquidity_ratio']*100:.0f}%",
                'action': '暂停交易，等待流动性恢复'
            })

        # 检测恐慌情绪
        sentiment = self.check_market_sentiment(stock_data)
        if sentiment['level'] == 'danger':
            conditions.append({
                'type': '市场恐慌',
                'severity': 'high',
                'description': f"跌停/涨停比例({sentiment['ratio']})超过阈值({sentiment['threshold']})",
                'action': '降低仓位至60%，增加现金至40%'
            })

        return {
            'has_extreme': len(conditions) > 0,
            'conditions': conditions,
            'count': len(conditions)
        }

    def generate_market_report(self) -> Dict:
        """生成市场状态报告"""
        print("=" * 60)
        print("🌐 市场状态监控")
        print("=" * 60)

        # 加载数据
        stock_data = self.load_stock_data()
        print(f"数据量: {len(stock_data)}条记录")
        print()

        # 计算各项指标
        limit_down = self.count_limit_down_stocks(stock_data)
        print(f"✓ 跌停股票: {limit_down['count']}只 ({limit_down['ratio']}%) ({limit_down['status']})")

        limit_up = self.count_limit_up_stocks(stock_data)
        print(f"✓ 涨停股票: {limit_up['count']}只 ({limit_up['ratio']}%)")

        liquidity = self.check_liquidity(stock_data)
        print(f"✓ 流动性: {liquidity['status']} (比率: {liquidity.get('liquidity_ratio', 100):.2%})")

        sentiment = self.check_market_sentiment(stock_data)
        print(f"✓ 市场情绪: {sentiment['sentiment']} (涨跌停比: {sentiment['ratio']:.1f})")

        extreme = self.detect_extreme_conditions(stock_data)
        print(f"✓ 极端情况: {extreme['count']}个")
        if extreme['has_extreme']:
            for cond in extreme['conditions']:
                print(f"  ⚠️ {cond['type']}: {cond['description']}")

        print()

        # 汇总报告
        report = {
            'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'limit_down': limit_down,
            'limit_up': limit_up,
            'liquidity': liquidity,
            'sentiment': sentiment,
            'extreme_conditions': extreme,
            'overall_status': self._calculate_overall_status([
                limit_down['level'],
                liquidity['level'],
                sentiment['level'],
                'danger' if extreme['has_extreme'] else 'info'
            ])
        }

        # 保存报告
        os.makedirs(os.path.dirname(self.market_report_file), exist_ok=True)
        with open(self.market_report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"✓ 市场报告已保存: {self.market_report_file}")
        print("=" * 60)
        print()

        return report

    def _calculate_overall_status(self, levels: List[str]) -> str:
        """计算整体状态"""
        if 'danger' in levels:
            return 'danger'
        elif 'warning' in levels:
            return 'warning'
        else:
            return 'normal'

    def format_report(self, report: Dict) -> str:
        """格式化报告为文本"""
        lines = []
        lines.append('四、市场状态')
        lines.append('')

        limit_down = report['limit_down']
        lines.append(f"• 跌停股票：{limit_down['count']}只（{limit_down['status']}）")

        liquidity = report['liquidity']
        lines.append(f"• 流动性：{liquidity['status']}")

        sentiment = report['sentiment']
        lines.append(f"• 市场情绪：{sentiment['sentiment']}")

        # 极端情况提醒
        extreme = report['extreme_conditions']
        if extreme['has_extreme']:
            lines.append('')
            lines.append('⚠️ 极端情况提醒：')
            for cond in extreme['conditions']:
                lines.append(f"• {cond['type']}：{cond['action']}")
        lines.append('')

        return '\n'.join(lines)

def main():
    """主函数"""
    monitor = MarketMonitor()
    report = monitor.generate_market_report()

    # 打印格式化报告
    print(monitor.format_report(report))

    return report

if __name__ == "__main__":
    main()
