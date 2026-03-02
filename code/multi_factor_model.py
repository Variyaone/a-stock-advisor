#!/usr/bin/env python3
"""
多因子得分模型
基于IC值加权计算综合得分
"""

import pandas as pd
import numpy as np
from typing import Dict, List

class MultiFactorScoreModel:
    """多因子得分模型"""
    
    def __init__(self):
        self.factor_names = []
        self.factor_weights = {}
        self.factor_ic = {}
        self.normalized_factors = {}
    
    def load_factor_scores(self, score_file: str):
        """加载因子得分"""
        import json
        with open(score_file, 'r') as f:
            factor_scores = json.load(f)
        
        self.factor_ic = factor_scores
    
    def set_ic_weighted(self, factor_ic: Dict[str, float], available_factors: List[str] = None):
        """
        设置IC权重

        Args:
            factor_ic: 因子IC值字典 {factor_name: IC}
            available_factors: 可用的因子列名列表
        """
        self.factor_ic = factor_ic

        # 如果指定了可用因子，只使用这些因子
        if available_factors:
            factor_ic = {k: v for k, v in factor_ic.items() if k in available_factors}

        # 计算IC绝对值作为权重
        ic_abs = {k: abs(v) for k, v in factor_ic.items() if not pd.isna(v)}
        total_ic = sum(ic_abs.values())

        if total_ic > 0:
            self.factor_weights = {k: v/total_ic for k, v in ic_abs.items()}
        else:
            # 如果所有IC都是NaN，使用等权
            factor_names = list(factor_ic.keys())
            if factor_names:
                self.factor_weights = {k: 1.0/len(factor_names) for k in factor_names}
            else:
                self.factor_weights = {}

    def auto_detect_factors(self, factor_df: pd.DataFrame, exclude_columns: List[str] = None):
        """
        自动检测可用因子并创建默认权重

        Args:
            factor_df: 因子数据DataFrame
            exclude_columns: 要排除的列名列表
        """
        if exclude_columns is None:
            exclude_columns = ['date', 'stock_code', 'month', 'factor_score', '股票名称', '股票代码', 'is_suspended', 'index']

        # 找出所有数值型列，排除指定列
        numeric_columns = factor_df.select_dtypes(include=[np.number]).columns.tolist()
        factor_columns = [col for col in numeric_columns if col not in exclude_columns]

        # 为每个因子设置默认IC值
        default_ic = {col: 0.1 for col in factor_columns}

        # 设置权重
        self.set_ic_weighted(default_ic, factor_columns)

        return factor_columns
    
    def normalize_factor(self, factor_data: pd.Series) -> pd.Series:
        """
        标准化因子（Z-score标准化）
        
        Args:
            factor_data: 因子数据
            
        Returns:
            标准化后的因子数据
        """
        mean = factor_data.mean()
        std = factor_data.std()
        
        if std > 0:
            return (factor_data - mean) / std
        else:
            # 如果标准差为0，返回全0
            return pd.Series(0, index=factor_data.index)
    
    def calculate_score(self, factor_df: pd.DataFrame, stock_codes: List[str] = None) -> pd.Series:
        """
        计算综合得分
        
        Args:
            factor_df: 因子数据 DataFrame (index: stock_code, columns: factor_names)
            stock_codes: 股票代码列表
            
        Returns:
            综合得分 Series (index: stock_code)
        """
        if stock_codes is None:
            stock_codes = factor_df.index.tolist()
        
        # 过滤出有因子权重的列
        available_factors = [f for f in self.factor_weights.keys() if f in factor_df.columns]
        
        if not available_factors:
            raise ValueError("没有可用的因子数据")
        
        # 计算加权得分
        scores = pd.Series(0.0, index=factor_df.index)
        
        for factor in available_factors:
            weight = self.factor_weights[factor]
            factor_data = factor_df[factor]
            
            # 标准化因子
            normalized_factor = self.normalize_factor(factor_data)
            
            # 累加加权得分
            scores += weight * normalized_factor
        
        return scores
    
    def get_top_stocks(self, factor_df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
        """
        获取得分最高的股票
        
        Args:
            factor_df: 因子数据
            n: 选股数量
            
        Returns:
            选中的股票 DataFrame
        """
        scores = self.calculate_score(factor_df)
        
        # 按得分排序
        top_scores = scores.nlargest(n)
        
        # 返回包含得分的数据
        result = factor_df.loc[top_scores.index].copy()
        result['综合得分'] = top_scores
        
        return result.sort_values('综合得分', ascending=False)
