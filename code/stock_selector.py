#!/usr/bin/env python3
"""
股票选择器
基于多因子模型选择股票
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

class StockSelector:
    """股票选择器"""
    
    def __init__(self, score_model, n: int = 10):
        """
        Args:
            score_model: 多因子得分模型
            n: 选股数量
        """
        self.score_model = score_model
        self.n = n
        self.selected_stocks = None
        self.selection_date = None
    
    def select_top_stocks(self, factor_data: pd.DataFrame, date: str = None) -> pd.DataFrame:
        """
        选择得分最高的股票
        
        Args:
            factor_data: 因子数据，index为stock_code
            date: 选股日期
            
        Returns:
            选中的股票 DataFrame
        """
        self.selection_date = date
        
        # 检查数据
        if len(factor_data) == 0:
            raise ValueError("因子数据为空")
        
        # 确保有足够的股票
        if len(factor_data) < self.n:
            print(f"⚠️ 可选股票数量({len(factor_data)})少于选股数量({self.n})，调整选股数量")
            self.n = len(factor_data)
        
        # 计算综合得分
        scores = self.score_model.calculate_score(factor_data)
        
        # 选择Top N
        top_scores = scores.nlargest(self.n)
        
        # 构建结果
        result = factor_data.loc[top_scores.index].copy()
        result['综合得分'] = top_scores
        
        self.selected_stocks = result
        
        return result.sort_values('综合得分', ascending=False)
    
    def get_buy_reason(self, stock_code: str) -> str:
        """
        获取股票买入理由
        
        Args:
            stock_code: 股票代码
            
        Returns:
            买入理由文本
        """
        if self.selected_stocks is None:
            return "未执行选股"
        
        if stock_code not in self.selected_stocks.index:
            return "股票未被选中"
        
        stock_data = self.selected_stocks.loc[stock_code]
        score = stock_data['综合得分']
        
        # 分析各因子表现
        factor_performances = []
        for factor in self.score_model.factor_weights.keys():
            if factor in stock_data.index and not pd.isna(stock_data[factor]):
                weight = self.score_model.factor_weights[factor]
                value = stock_data[factor]
                factor_performances.append(f"{factor}={value:.2f}(权重{weight:.1%})")
        
        reasons = []
        reasons.append(f"综合得分{score:.2f}，位列选股池前{self.n}")
        
        if factor_performances:
            reasons.append("主要优势：")
            reasons.extend(f"  - {fp}" for fp in factor_performances[:3])
        
        return "\n".join(reasons)
