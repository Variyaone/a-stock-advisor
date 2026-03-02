#!/usr/bin/env python3
"""
A股量化系统 - 核心模块
"""

from .multi_factor_model import MultiFactorScoreModel
from .stock_selector import StockSelector
from .risk_controller import RiskController
from .generate_report import generate_daily_recommendation, save_factor_scores

__all__ = [
    'MultiFactorScoreModel',
    'StockSelector',
    'RiskController',
    'generate_daily_recommendation',
    'save_factor_scores',
]
