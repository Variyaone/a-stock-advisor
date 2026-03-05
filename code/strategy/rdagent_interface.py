#!/usr/bin/env python3
"""
RDAgent因子挖掘接口模块
集成微软R&D-Agent-Quant自动化因子挖掘框架

GitHub: https://github.com/microsoft/RD-Agent

主要功能:
- 自动化因子挖掘：从文献、报告、历史反馈中生成、筛选、组合新因子
- 因子去重：与现有最优因子库计算相似性，避免重复
- 模型优化：动态调整优化方向（因子/模型）
- 多智能体协作：挣客、实现、验证、分析四个智能体协同工作
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging
import json
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

RDAgent_AVAILABLE = False

try:
    from rd_agent import RDAgent
    from rd_agent.quant import FactorAgent, ModelAgent
    RDAgent_AVAILABLE = True
    logger.info("RDAgent已安装，因子挖掘功能可用")
except ImportError:
    logger.info("RDAgent未安装，使用本地因子挖掘方法")
    RDAgent_AVAILABLE = False


@dataclass
class FactorCandidate:
    """因子候选"""
    formula: str
    description: str
    ic: float
    ir: float
    is_valid: bool
    source: str
    created_at: str


class RDAgentFactorInterface:
    """RDAgent因子挖掘接口"""
    
    def __init__(self, use_rdagent: bool = True):
        """
        初始化RDAgent接口
        
        Args:
            use_rdagent: 是否使用RDAgent（如果可用）
        """
        self.use_rdagent = use_rdagent and RDAgent_AVAILABLE
        self.factor_agent = None
        self.discovered_factors: List[FactorCandidate] = []
        
        if self.use_rdagent:
            try:
                self.factor_agent = FactorAgent()
                logger.info("✓ RDAgent因子智能体已初始化")
            except Exception as e:
                logger.warning(f"RDAgent初始化失败: {e}")
                self.use_rdagent = False
    
    def discover_factors(
        self,
        data: pd.DataFrame,
        n_factors: int = 10,
        literature_hints: List[str] = None,
        existing_factors: List[str] = None
    ) -> List[FactorCandidate]:
        """
        自动发现新因子
        
        Args:
            data: 市场数据
            n_factors: 目标因子数量
            literature_hints: 文献提示（如论文标题、摘要）
            existing_factors: 现有因子公式列表（用于去重）
            
        Returns:
            发现的因子候选列表
        """
        if self.use_rdagent and self.factor_agent is not None:
            return self._discover_with_rdagent(
                data, n_factors, literature_hints, existing_factors
            )
        else:
            return self._discover_with_local(
                data, n_factors, literature_hints, existing_factors
            )
    
    def _discover_with_rdagent(
        self,
        data: pd.DataFrame,
        n_factors: int,
        literature_hints: List[str],
        existing_factors: List[str]
    ) -> List[FactorCandidate]:
        """使用RDAgent发现因子"""
        try:
            new_factors = self.factor_agent.generate_factors(
                data=data,
                n_factors=n_factors,
                hints=literature_hints,
                existing=existing_factors
            )
            
            results = []
            for factor in new_factors:
                candidate = FactorCandidate(
                    formula=factor.formula,
                    description=factor.description,
                    ic=factor.ic,
                    ir=factor.ir,
                    is_valid=factor.is_valid,
                    source='RDAgent',
                    created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                results.append(candidate)
            
            self.discovered_factors.extend(results)
            return results
            
        except Exception as e:
            logger.error(f"RDAgent因子发现失败: {e}")
            return self._discover_with_local(data, n_factors, literature_hints, existing_factors)
    
    def _discover_with_local(
        self,
        data: pd.DataFrame,
        n_factors: int,
        literature_hints: List[str],
        existing_factors: List[str]
    ) -> List[FactorCandidate]:
        """使用本地方法发现因子（RDAgent不可用时的替代方案）"""
        logger.info("使用本地因子挖掘方法...")
        
        results = []
        base_formulas = [
            ("rank(close / ma(close, 20))", "价格相对20日均线的位置"),
            ("rank(volume / ma(volume, 20))", "成交量相对20日均量的位置"),
            ("rank((high - low) / close)", "日内波动率"),
            ("rank(roc(close, 20))", "20日价格动量"),
            ("rank((close - low) / (high - low))", "日内价格位置"),
            ("rank(correlation(close, volume, 20))", "价量相关性"),
            ("rank(std(close, 20) / mean(close, 20))", "变异系数"),
            ("rank((ma(close, 5) - ma(close, 20)) / ma(close, 20))", "均线偏离度"),
            ("rank(max(close, 20) / min(close, 20) - 1)", "20日价格区间"),
            ("rank(sum(max(0, close - delay(close, 1)), 20) / sum(max(0, delay(close, 1) - close), 20) + 0.001)", "RSI变体"),
        ]
        
        if existing_factors:
            base_formulas = [(f, d) for f, d in base_formulas if f not in existing_factors]
        
        for formula, description in base_formulas[:n_factors]:
            try:
                ic, ir = self._evaluate_factor_formula(data, formula)
                
                candidate = FactorCandidate(
                    formula=formula,
                    description=description,
                    ic=ic,
                    ir=ir,
                    is_valid=abs(ic) > 0.02 and abs(ir) > 0.3,
                    source='Local',
                    created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                results.append(candidate)
            except Exception as e:
                logger.debug(f"因子评估失败 {formula}: {e}")
        
        self.discovered_factors.extend(results)
        return results
    
    def _evaluate_factor_formula(
        self,
        data: pd.DataFrame,
        formula: str
    ) -> Tuple[float, float]:
        """评估因子公式"""
        try:
            import pandas as pd
            import numpy as np
            
            df = data.copy()
            
            if 'date' in df.columns:
                df = df.sort_values('date')
            
            factor_values = pd.Series(0.5, index=df.index)
            
            if 'rank(close / ma(close, 20))' in formula:
                if 'close' in df.columns:
                    ma20 = df['close'].rolling(20).mean()
                    factor_values = (df['close'] / ma20).rank(pct=True)
            
            elif 'rank(volume / ma(volume, 20))' in formula:
                if 'volume' in df.columns:
                    ma20 = df['volume'].rolling(20).mean()
                    factor_values = (df['volume'] / ma20).rank(pct=True)
            
            elif 'rank((high - low) / close)' in formula:
                if all(c in df.columns for c in ['high', 'low', 'close']):
                    factor_values = ((df['high'] - df['low']) / df['close']).rank(pct=True)
            
            elif 'rank(roc(close, 20))' in formula:
                if 'close' in df.columns:
                    roc = df['close'].pct_change(20)
                    factor_values = roc.rank(pct=True)
            
            factor_values = factor_values.fillna(0.5)
            
            if 'return_1d' in df.columns:
                future_returns = df['return_1d'].shift(-1)
            elif 'close' in df.columns:
                future_returns = df['close'].pct_change().shift(-1)
            else:
                return 0.0, 0.0
            
            valid_mask = ~(factor_values.isna() | future_returns.isna())
            if valid_mask.sum() < 30:
                return 0.0, 0.0
            
            from scipy.stats import spearmanr
            ic, pvalue = spearmanr(
                factor_values[valid_mask],
                future_returns[valid_mask]
            )
            
            ic_std = factor_values[valid_mask].std()
            ir = ic / ic_std if ic_std > 0 else 0
            
            return round(ic, 4), round(ir, 4)
            
        except Exception as e:
            logger.debug(f"因子评估失败: {e}")
            return 0.0, 0.0
    
    def deduplicate_factors(
        self,
        new_factors: List[FactorCandidate],
        existing_factors: List[Dict],
        similarity_threshold: float = 0.7
    ) -> List[FactorCandidate]:
        """
        因子去重
        
        Args:
            new_factors: 新发现的因子
            existing_factors: 现有因子列表
            similarity_threshold: 相似度阈值
            
        Returns:
            去重后的因子列表
        """
        if not existing_factors:
            return new_factors
        
        unique_factors = []
        existing_formulas = [f.get('formula', '') for f in existing_factors]
        
        for factor in new_factors:
            is_duplicate = False
            
            for existing_formula in existing_formulas:
                similarity = self._calculate_similarity(factor.formula, existing_formula)
                if similarity > similarity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_factors.append(factor)
        
        logger.info(f"因子去重: {len(new_factors)} -> {len(unique_factors)}")
        return unique_factors
    
    def _calculate_similarity(self, formula1: str, formula2: str) -> float:
        """计算公式相似度"""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, formula1, formula2).ratio()
    
    def get_factor_report(self) -> str:
        """生成因子发现报告"""
        lines = [
            "=" * 60,
            "RDAgent因子挖掘报告".center(60),
            "=" * 60,
            f"\n发现时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"RDAgent状态: {'可用' if self.use_rdagent else '不可用'}",
            f"发现因子总数: {len(self.discovered_factors)}",
            f"有效因子数量: {sum(1 for f in self.discovered_factors if f.is_valid)}",
            "\n" + "-" * 60,
            "因子列表:",
            "-" * 60
        ]
        
        for i, factor in enumerate(self.discovered_factors, 1):
            status = "✓ 有效" if factor.is_valid else "✗ 无效"
            lines.append(f"\n{i}. [{factor.source}] {status}")
            lines.append(f"   公式: {factor.formula}")
            lines.append(f"   描述: {factor.description}")
            lines.append(f"   IC={factor.ic:.4f}, IR={factor.ir:.4f}")
        
        return "\n".join(lines)
    
    def save_results(self, output_path: str = "data/rdagent_factors.json"):
        """保存发现的因子"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        results = {
            'factors': [
                {
                    'formula': f.formula,
                    'description': f.description,
                    'ic': float(f.ic),
                    'ir': float(f.ir),
                    'is_valid': bool(f.is_valid),
                    'source': f.source,
                    'created_at': f.created_at
                }
                for f in self.discovered_factors
            ],
            'metadata': {
                'rdagent_available': self.use_rdagent,
                'total_count': len(self.discovered_factors),
                'valid_count': sum(1 for f in self.discovered_factors if f.is_valid),
                'saved_at': datetime.now().isoformat()
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"因子结果已保存: {output_path}")


def is_rdagent_available() -> bool:
    """检查RDAgent是否可用"""
    return RDAgent_AVAILABLE


if __name__ == "__main__":
    print("RDAgent因子挖掘接口测试")
    print(f"RDAgent状态: {'可用' if RDAgent_AVAILABLE else '不可用'}")
    
    np.random.seed(42)
    n_days = 252
    dates = pd.date_range(start='2023-01-01', periods=n_days, freq='B')
    
    data = pd.DataFrame({
        'date': dates,
        'stock_code': '000001',
        'close': 10 + np.cumsum(np.random.normal(0, 0.02, n_days)),
        'high': 10.5 + np.cumsum(np.random.normal(0, 0.02, n_days)),
        'low': 9.5 + np.cumsum(np.random.normal(0, 0.02, n_days)),
        'volume': np.random.randint(1000000, 5000000, n_days),
        'return_1d': np.random.normal(0.001, 0.02, n_days)
    })
    
    interface = RDAgentFactorInterface()
    factors = interface.discover_factors(data, n_factors=5)
    
    print(interface.get_factor_report())
    interface.save_results()
