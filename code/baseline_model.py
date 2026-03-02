#!/usr/bin/env python3
"""
基准模型 - 简单的预测模型
使用线性模型或梯度提升树，因子数量控制在10个以内
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import warnings
warnings.filterwarnings('ignore')

# 尝试导入LightGBM，如果未安装则使用sklearn
try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False
    print("⚠️  LightGBM未安装，将使用sklearn模型")

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False


class BaselineModel:
    """基准模型类"""
    
    def __init__(self,
                 model_type: str = 'linear',
                 n_features: int = 10,
                 random_state: int = 42):
        """
        初始化基准模型
        
        Args:
            model_type: 模型类型 ('linear', 'logistic', 'lightgbm', 'xgboost')
            n_features: 最大特征数量
            random_state: 随机种子
        """
        self.model_type = model_type
        self.n_features = n_features
        self.random_state = random_state
        self.model = None
        self.feature_names = []
        self.scaler = StandardScaler()
        self.is_fitted = False
        
        # 根据模型类型创建模型
        self._create_model()
    
    def _create_model(self):
        """创建模型"""
        if self.model_type == 'linear':
            self.model = LinearRegression()
        elif self.model_type == 'logistic':
            self.model = LogisticRegression(
                random_state=self.random_state,
                max_iter=1000,
                class_weight='balanced'
            )
        elif self.model_type == 'lightgbm':
            if HAS_LIGHTGBM:
                self.model = lgb.LGBMClassifier(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.05,
                    random_state=self.random_state,
                    verbose=-1
                )
            else:
                print("⚠️  LightGBM不可用，切换到LogisticRegression")
                self.model_type = 'logistic'
                self.model = LogisticRegression(
                    random_state=self.random_state,
                    max_iter=1000,
                    class_weight='balanced'
                )
        elif self.model_type == 'xgboost':
            if HAS_XGBOOST:
                self.model = xgb.XGBClassifier(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.05,
                    random_state=self.random_state,
                    eval_metric='logloss'
                )
            else:
                print("⚠️  XGBoost不可用，切换到LogisticRegression")
                self.model_type = 'logistic'
                self.model = LogisticRegression(
                    random_state=self.random_state,
                    max_iter=1000,
                    class_weight='balanced'
                )
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
    
    def prepare_data(self, data: pd.DataFrame,
                    target_col: str = 'target_return',
                    exclude_cols: List[str] = None) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        准备训练数据
        
        Args:
            data: 数据DataFrame
            target_col: 目标列名
            exclude_cols: 排除的列名列表
            
        Returns:
            (X, y, feature_names)
        """
        if exclude_cols is None:
            exclude_cols = [
                'date', 'stock_code', 'month', '股票名称', '股票代码', 'is_suspended',
                'open', 'high', 'low', 'close', 'volume', 'amount', 'target_return'
            ]
        
        # 只选择数值型列
        numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
        available_features = [col for col in numeric_cols if col not in exclude_cols]
        
        # 如果没有目标列，创建目标列（下一期收益率）
        if target_col not in data.columns:
            print("⚠️  目标列不存在，需要先构建目标变量")
            return None, None, []
        
        # 选择特征
        X = data[available_features].copy()
        y = data[target_col].copy()
        
        # 处理缺失值
        X = X.fillna(0)
        y = y.fillna(0)
        
        # 选择top N重要特征（如果有历史重要性，或者使用前N个）
        if len(available_features) > self.n_features:
            # 简化处理：选择方差最大的前N个特征
            variances = X.var()
            top_features = variances.nlargest(self.n_features).index.tolist()
            X = X[top_features]
            self.feature_names = top_features
        else:
            self.feature_names = available_features
        
        return X.values, y.values, self.feature_names
    
    def fit(self, X: np.ndarray, y: np.ndarray):
        """
        训练模型
        
        Args:
            X: 特征矩阵
            y: 目标变量
        """
        # 标准化特征（对树模型不需要，但保持一致性）
        if self.model_type in ['linear', 'logistic']:
            X_scaled = self.scaler.fit_transform(X)
        else:
            X_scaled = X
        
        # 转换为分类问题（正收益 vs 负收益）
        if self.model_type in ['logistic', 'lightgbm', 'xgboost']:
            y_binary = (y > 0).astype(int)
        else:
            y_binary = y
        
        self.model.fit(X_scaled, y_binary)
        self.is_fitted = True
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        预测
        
        Args:
            X: 特征矩阵
            
        Returns:
            预测结果
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        # 标准化特征
        if self.model_type in ['linear', 'logistic']:
            X_scaled = self.scaler.transform(X)
        else:
            X_scaled = X
        
        # 预测
        if self.model_type in ['logistic', 'lightgbm', 'xgboost']:
            # 返回概率值
            pred_proba = self.model.predict_proba(X_scaled)
            # 返回正类概率
            return pred_proba[:, 1]
        else:
            # 线性回归返回预测值
            return self.model.predict(X_scaled)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        获取特征重要性
        
        Returns:
            特征重要性字典
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before getting feature importance")
        
        if self.model_type == 'linear':
            importance = np.abs(self.model.coef_)
        elif self.model_type == 'logistic':
            importance = np.abs(self.model.coef_[0])
        elif self.model_type == 'lightgbm' and HAS_LIGHTGBM:
            importance = self.model.feature_importances_
        elif self.model_type == 'xgboost' and HAS_XGBOOST:
            importance = self.model.feature_importances_
        else:
            importance = np.ones(len(self.feature_names))
        
        return dict(zip(self.feature_names, importance))
    
    def time_series_cv(self, X: np.ndarray, y: np.ndarray,
                      n_splits: int = 5) -> Dict[str, float]:
        """
        时间序列交叉验证
        
        Args:
            X: 特征矩阵
            y: 目标变量
            n_splits: 折数
            
        Returns:
            交叉验证结果字典
        """
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        if self.model_type in ['logistic', 'lightgbm', 'xgboost']:
            y_binary = (y > 0).astype(int)
            scoring = 'roc_auc'
        else:
            y_binary = y
            scoring = 'neg_mean_squared_error'
        
        # 使用单进程避免多进程问题
        scores = cross_val_score(
            self.model, X, y_binary,
            cv=tscv, scoring=scoring, n_jobs=1
        )
        
        return {
            'mean_score': scores.mean(),
            'std_score': scores.std(),
            'scores': scores.tolist()
        }
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        """
        评估模型
        
        Args:
            X_test: 测试数据特征
            y_test: 测试数据目标
            
        Returns:
            评估指标字典
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before evaluation")
        
        # 预测
        y_pred = self.predict(X_test)
        
        if self.model_type in ['logistic', 'lightgbm', 'xgboost']:
            # 分类问题
            y_binary = (y_test > 0).astype(int)
            y_pred_binary = (y_pred > 0.5).astype(int)
            
            metrics = {
                'accuracy': accuracy_score(y_binary, y_pred_binary),
                'precision': precision_score(y_binary, y_pred_binary, zero_division=0),
                'recall': recall_score(y_binary, y_pred_binary, zero_division=0),
                'f1': f1_score(y_binary, y_pred_binary, zero_division=0),
                'roc_auc': roc_auc_score(y_binary, y_pred)
            }
        else:
            # 回归问题
            y_true_binary = (y_test > 0).astype(int)
            y_pred_binary = (y_pred > 0).astype(int)
            
            metrics = {
                'mse': np.mean((y_test - y_pred) ** 2),
                'mae': np.mean(np.abs(y_test - y_pred)),
                'rmse': np.sqrt(np.mean((y_test - y_pred) ** 2)),
                'direction_accuracy': accuracy_score(y_true_binary, y_pred_binary)
            }
        
        return metrics


def construct_target_return(data: pd.DataFrame, period: int = 1) -> pd.DataFrame:
    """
    构建目标收益率（未来收益率）
    
    Args:
        data: 数据DataFrame，必须包含 date, stock_code, close
        period: 期数（1=下期，2=下下期等）
        
    Returns:
        包含目标收益率的数据
    """
    data = data.sort_values(['stock_code', 'date']).copy()
    
    # 按股票分组，计算未来收益率
    data['future_close'] = data.groupby('stock_code')['close'].shift(-period)
    data['next_date'] = data.groupby('stock_code')['date'].shift(-period)
    
    # 计算收益率
    data['target_return'] = (data['future_close'] - data['close']) / data['close']
    
    # 删除没有未来价格的数据
    data = data[data['target_return'].notna()]
    
    return data


def select_top_features_by_ic(data: pd.DataFrame,
                             feature_cols: List[str],
                             target_col: str = 'target_return',
                             top_n: int = 10) -> List[str]:
    """
    基于IC值选择top N特征
    
    Args:
        data: 数据DataFrame
        feature_cols: 特征列名列表
        target_col: 目标列名
        top_n: 选择前N个特征
        
    Returns:
        选择的特征列表
    """
    ic_values = {}
    
    for col in feature_cols:
        # 计算IC（相关系数）
        valid_data = data[[col, target_col]].dropna()
        if len(valid_data) > 10:
            ic = valid_data[col].corr(valid_data[target_col])
            ic_values[col] = abs(ic) if ic is not None else 0
    
    # 按IC绝对值排序，选择top N
    sorted_features = sorted(ic_values.items(), key=lambda x: x[1], reverse=True)
    
    return [f[0] for f in sorted_features[:top_n]]


def train_baseline_model(data: pd.DataFrame,
                        model_type: str = 'lightgbm',
                        n_features: int = 10,
                        test_ratio: float = 0.2) -> Tuple[BaselineModel, Dict]:
    """
    训练基准模型
    
    Args:
        data: 数据DataFrame
        model_type: 模型类型
        n_features: 最大特征数量
        test_ratio: 测试集比例
        
    Returns:
        (模型, 训练结果字典)
    """
    print(f"🔧 训练基准模型 ({model_type})...")
    
    # 1. 构建目标收益率
    if 'target_return' not in data.columns:
        data = construct_target_return(data)
        print(f"  ✓ 构建目标收益率完成")
    
    # 2. 选择特征
    exclude_cols = [
        'date', 'stock_code', 'month', '股票名称', '股票代码', 'is_suspended',
        'future_close', 'next_date', 'target_return'
    ]
    
    available_features = [col for col in data.columns
                         if col not in exclude_cols and data[col].dtype in [np.float64, np.int64]]
    
    print(f"  可用特征数: {len(available_features)}")
    
    # 基于IC选择top特征
    if len(available_features) > n_features:
        selected_features = select_top_features_by_ic(
            data, available_features, 'target_return', top_n=n_features
        )
        print(f"  ✓ 选择特征数: {len(selected_features)}")
        print(f"    特征: {', '.join(selected_features[:5])}..." if len(selected_features) > 5 else f"    特征: {', '.join(selected_features)}")
    else:
        selected_features = available_features
    
    # 3. 准备训练和测试数据
    # 按时间划分（前80%训练，后20%测试）
    data_sorted = data.sort_values('date')
    split_idx = int(len(data_sorted) * (1 - test_ratio))
    
    train_data = data_sorted.iloc[:split_idx]
    test_data = data_sorted.iloc[split_idx:]
    
    print(f"  训练样本: {len(train_data)}")
    print(f"  测试样本: {len(test_data)}")
    
    # 4. 创建模型
    model = BaselineModel(model_type=model_type, n_features=n_features)
    
    # 5. 准备数据
    X_train, y_train, _ = model.prepare_data(train_data, exclude_cols=exclude_cols)
    X_test, y_test, _ = model.prepare_data(test_data, exclude_cols=exclude_cols)
    
    if X_train is None:
        raise ValueError("Failed to prepare data")
    
    # 6. 训练模型
    model.fit(X_train, y_train)
    print(f"  ✓ 模型训练完成")
    
    # 7. 评估模型
    train_metrics = model.evaluate(X_train, y_train)
    test_metrics = model.evaluate(X_test, y_test)
    
    # 8. 时间序列交叉验证
    cv_results = model.time_series_cv(X_train, y_train, n_splits=5)
    
    # 9. 特征重要性
    feature_importance = model.get_feature_importance()
    sorted_importance = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\n📊 模型评估:")
    print(f"  训练集性能: {train_metrics}")
    print(f"  测试集性能: {test_metrics}")
    print(f"  交叉验证: {cv_results['mean_score']:.4f} ± {cv_results['std_score']:.4f}")
    
    print(f"\n🎯 Top 5 特征重要性:")
    for feat, imp in sorted_importance[:5]:
        print(f"  {feat}: {imp:.4f}")
    
    results = {
        'model_type': model_type,
        'train_metrics': train_metrics,
        'test_metrics': test_metrics,
        'cv_results': cv_results,
        'feature_importance': dict(sorted_importance),
        'selected_features': selected_features,
        'feature_names': model.feature_names
    }
    
    return model, results


if __name__ == '__main__':
    # 测试基准模型
    print("=== 基准模型测试 ===\n")
    
    # 创建模拟数据
    np.random.seed(42)
    n_samples = 1000
    dates = pd.date_range('2024-01-01', periods=n_samples)
    
    data = pd.DataFrame({
        'date': dates,
        'stock_code': np.random.choice(['000001', '000002', '600000', '600036'], n_samples),
        'close': np.random.randn(n_samples).cumsum() + 100,
        'factor1': np.random.randn(n_samples),
        'factor2': np.random.randn(n_samples),
        'factor3': np.random.randn(n_samples),
        'factor4': np.random.randn(n_samples),
        'factor5': np.random.randn(n_samples),
        'volume': np.random.randint(1000000, 10000000, n_samples)
    })
    
    # 构建目标收益率
    data = construct_target_return(data)
    
    # 训练模型
    try:
        model, results = train_baseline_model(
            data,
            model_type='lightgbm',
            n_features=5,
            test_ratio=0.2
        )
        
        print(f"\n✓ 模型训练成功")
        print(f"模型类型: {model.model_type}")
        print(f"特征数量: {len(model.feature_names)}")
        
    except Exception as e:
        print(f"✗ 模型训练失败: {e}")
