#!/usr/bin/env python3
"""
风险控制器
过滤和控制风险股票
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

class RiskController:
    """风险控制器"""
    
    def __init__(self):
        self.filters = {
            'ST股票': lambda row: not row.get('股票名称', '').startswith('ST'),
            '停牌股票': lambda row: row.get('is_suspended', 0) == 0,
            '退市股票': lambda row: not row.get('股票名称', '').startswith('*ST'),
        }
        self.control_summary = {}
    
    def apply_all_controls(self, selected_stocks: pd.DataFrame, stock_list: pd.DataFrame, 
                          factor_data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """
        应用所有风险控制
        
        Args:
            selected_stocks: 已选股票
            stock_list: 股票列表
            factor_data: 因子数据
            
        Returns:
            (控制后的股票, 控制摘要)
        """
        control_summary = {
            '过滤前': len(selected_stocks),
            '过滤详情': {}
        }
        
        # 合并股票信息
        if len(stock_list) > 0 and '股票代码' in stock_list.columns:
            stock_info = stock_list.set_index('股票代码')
        else:
            stock_info = pd.DataFrame(index=selected_stocks.index)
        
        result = selected_stocks.copy()
        
        # 应用各项过滤
        for filter_name, filter_func in self.filters.items():
            before_count = len(result)
            
            # 应用过滤
            try:
                if len(stock_info) > 0:
                    mask = result.index.map(lambda code: filter_func(stock_info.loc[code]) if code in stock_info.index else True)
                else:
                    mask = pd.Series(True, index=result.index)
                
                result = result[mask]
            except Exception as e:
                print(f"⚠️ 过滤{filter_name}失败: {e}")
            
            after_count = len(result)
            filtered_count = before_count - after_count
            
            control_summary['过滤详情'][filter_name] = filtered_count
        
        control_summary['过滤后'] = len(result)
        
        self.control_summary = control_summary
        
        return result, control_summary
    
    def format_control_summary(self, summary: Dict) -> str:
        """
        格式化控制摘要
        
        Args:
            summary: 控制摘要
            
        Returns:
            格式化的摘要文本
        """
        lines = []
        lines.append("风险控制摘要:")
        lines.append(f"  过滤前: {summary['过滤前']}只")
        
        for filter_name, count in summary['过滤详情'].items():
            if count > 0:
                lines.append(f"  - {filter_name}: 过滤{count}只")
        
        lines.append(f"  过滤后: {summary['过滤后']}只")
        
        return "\n".join(lines)
