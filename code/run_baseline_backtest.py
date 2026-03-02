#!/usr/bin/env python3
"""
运行基准模型回测并生成报告
"""

import pandas as pd
import numpy as np
import pickle
import os
from datetime import datetime

# 工作目录
WORK_DIR = '/Users/variya/.openclaw/workspace/projects/a-stock-advisor'
os.chdir(WORK_DIR)

# 导入模块
from backtest_engine_v2 import BacktestEngineV2, CostModel
from baseline_model import BaselineModel, construct_target_return, train_baseline_model
from paper_trading import (
    HistoricalDataModule,
    FactorScoreSignalModule,
    BasicRiskModule,
    PaperTradingSystem,
    Monitor
)

def load_data():
    """加载数据"""
    print("="*70)
    print("📂 加载数据")
    print("="*70)
    
    data_path = 'data/mock_data.pkl'
    
    with open(data_path, 'rb') as f:
        data = pickle.load(f)
    
    print(f"✓ 数据加载成功: {data.shape[0]:,} 行, {data.shape[1]} 列")
    print(f"  - 股票数量: {data['stock_code'].nunique()}")
    print(f"  - 时间范围: {data['date'].min()} 至 {data['date'].max()}")
    print(f"  - 月份数量: {data['month'].nunique()}")
    
    return data

def prepare_backtest_data(data):
    """准备回测数据"""
    print("\n" + "="*70)
    print("🔨 准备回测数据")
    print("="*70)
    
    # 按月获取最后一天的因子数据
    monthly_data = data.groupby(['month', 'stock_code']).last().reset_index()
    
    print(f"✓ 月度数据准备完成: {monthly_data.shape[0]:,} 行")
    print(f"  - 月份数: {monthly_data['month'].nunique()}")
    print(f"  - 平均每月股票数: {len(monthly_data) / monthly_data['month'].nunique():.0f}")
    
    return monthly_data

def train_model(data):
    """训练基准模型"""
    print("\n" + "="*70)
    print("🎓 训练基准模型")
    print("="*70)
    
    # 准备数据：使用monthly_data训练
    monthly_data = prepare_backtest_data(data)
    
    try:
        # 尝试使用LightGBM
        model, results = train_baseline_model(
            monthly_data,
            model_type='lightgbm',
            n_features=8,  # 控制在10个以内
            test_ratio=0.2
        )
    except Exception as e:
        print(f"⚠️  LightGBM训练失败: {e}")
        print("尝试使用LogisticRegression...")
        model, results = train_baseline_model(
            monthly_data,
            model_type='logistic',
            n_features=8,
            test_ratio=0.2
        )
    
    return model, results

def run_backtest_with_factor_score(data):
    """使用因子得分运行回测"""
    print("\n" + "="*70)
    print("📊 回测 - 基于因子得分")
    print("="*70)
    
    # 准备数据
    monthly_data = prepare_backtest_data(data)
    
    # 创建成本模型
    cost_model = CostModel(
        commission_rate=0.0003,  # 万三
        stamp_tax_rate=0.001,     # 千一
        impact_cost_base=0.0005,
        impact_cost_sqrt=0.001
    )
    
    # 创建回测引擎
    engine = BacktestEngineV2(
        initial_capital=1000000,
        cost_model=cost_model,
        max_single_position=0.10,   # 单票最大10%
        max_industry_exposure=0.30, # 单行业最大30%
        slippage_rate=0.001,        # 滑点0.1%
        fill_ratio=0.95             # 成交率95%
    )
    
    # 定义信号生成函数
    def signal_func(date, current_data):
        # 选择因子得分最高的10只股票，等权
        top_stocks = current_data.nlargest(10, 'factor_score')['stock_code'].values
        
        # 过滤问题股票
        if '股票名称' in current_data.columns:
            valid_stocks = current_data[
                (~current_data['股票名称'].str.startswith('ST', na=False)) &
                (~current_data['股票名称'].str.startswith('*ST', na=False)) &
                (current_data['is_suspended'] != 1)
            ]['stock_code'].values
            
            top_stocks = np.intersect1d(top_stocks, valid_stocks)
        
        # 返回等权信号
        position_size = 0.05  # 每票5%
        return {code: position_size for code in top_stocks}
    
    # 运行回测
    results = engine.run_backtest(monthly_data, signal_func, rebalance_freq='monthly')
    
    return results, engine

def run_backtest_with_paper_trading(data):
    """使用模拟盘系统运行回测"""
    print("\n" + "="*70)
    print("📊 回测 - 模拟盘系统")
    print("="*70)
    
    # 保存数据到临时文件
    monthly_data = prepare_backtest_data(data)
    
    import tempfile
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pkl', delete=False) as f:
        temp_path = f.name
        pickle.dump(monthly_data, f)
    
    try:
        # 创建数据模块
        data_module = HistoricalDataModule(temp_path)
        
        # 创建信号模块 - 基于因子得分
        signal_module = FactorScoreSignalModule(
            factor_col='factor_score',
            top_n=10,
            position_size=0.05
        )
        
        # 创建风控模块
        risk_module = BasicRiskModule(
            max_single_position=0.10,
            max_industry_exposure=0.30,
            max_position_count=20
        )
        
        # 创建成本模型
        cost_model = CostModel(
            commission_rate=0.0003,
            stamp_tax_rate=0.001,
            impact_cost_base=0.0005,
            impact_cost_sqrt=0.001
        )
        
        # 创建日志文件
        log_file = os.path.join('logs', f'backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        os.makedirs('logs', exist_ok=True)
        
        # 创建模拟盘系统
        system = PaperTradingSystem(
            data_module=data_module,
            signal_module=signal_module,
            risk_module=risk_module,
            initial_capital=1000000,
            cost_model=cost_model,
            log_file=log_file
        )
        
        # 运行回测
        date_list = sorted(monthly_data['month'].unique())
        results = system.run_backtest(date_list)
        
        # 添加监控信息
        results['monitor_summary'] = system.get_monitor_summary()
        results['portfolio_summary'] = system.get_portfolio_summary()
        
        return results, system, log_file
    
    finally:
        # 清理临时文件
        try:
            os.unlink(temp_path)
        except:
            pass

def generate_report(factor_results, paper_trading_results, model_results=None, log_file=None):
    """生成回测报告"""
    print("\n" + "="*70)
    print("📋 生成回测报告")
    print("="*70)
    
    report_lines = []
    
    # 标题
    report_lines.append("# A股量化系统 - 基准策略回测报告")
    report_lines.append("")
    report_lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    
    # 概览
    report_lines.append("## 📊 回测概览")
    report_lines.append("")
    report_lines.append("### 策略设置")
    report_lines.append("- **初始资金**: 1,000,000 元")
    report_lines.append("- **调仓频率**: 月度调仓")
    report_lines.append("- **选股数量**: 10 只")
    report_lines.append("- **单票仓位**: 5% (上限10%)")
    report_lines.append("- **总仓位**: ~50%")
    report_lines.append("")
    
    # 交易成本
    report_lines.append("### 交易成本模型")
    report_lines.append("- **佣金率**: 0.03% (万三)")
    report_lines.append("- **最低佣金**: 5 元")
    report_lines.append("- **印花税**: 0.1% (仅卖出)")
    report_lines.append("- **冲击成本**: 基础0.05% + 与订单额相关")
    report_lines.append("- **滑点率**: 0.1%")
    report_lines.append("- **成交率**: 95%")
    report_lines.append("")
    
    # 因子得分回测结果
    if factor_results and 'annual_return' in factor_results:
        report_lines.append("## 📈 回测结果 - 基于因子得分")
        report_lines.append("")
        
        # 主要指标
        report_lines.append("### 主要绩效指标")
        report_lines.append("")
        report_lines.append("| 指标 | 数值 | 评价 |")
        report_lines.append("|------|------|------|")
        
        total_return = factor_results['total_return']
        report_lines.append(f"| 总收益率 | {total_return:.2%} | {'优秀' if total_return > 0.2 else '良好' if total_return > 0 else '一般'} |")
        
        annual_return = factor_results['annual_return']
        report_lines.append(f"| 年化收益率 | {annual_return:.2%} | {'优秀' if annual_return > 0.15 else '良好' if annual_return > 0.1 else '一般'} |")
        
        annual_volatility = factor_results['annual_volatility']
        report_lines.append(f"| 年化波动率 | {annual_volatility:.2%} | {'低' if annual_volatility < 0.15 else '中' if annual_volatility < 0.25 else '高'} |")
        
        sharpe_ratio = factor_results['sharpe_ratio']
        report_lines.append(f"| 夏普比率 | {sharpe_ratio:.2f} | {'优秀' if sharpe_ratio > 2 else '良好' if sharpe_ratio > 1.5 else '一般'} |")
        
        max_drawdown = factor_results['max_drawdown']
        report_lines.append(f"| 最大回撤 | {max_drawdown:.2%} | {'稳健' if abs(max_drawdown) < 0.15 else '一般' if abs(max_drawdown) < 0.25 else '激进'} |")
        
        win_rate = factor_results['win_rate']
        report_lines.append(f"| 月度胜率 | {win_rate:.2%} | {'高' if win_rate > 0.6 else '中' if win_rate > 0.4 else '低'} |")
        
        report_lines.append("")
        
        # 交易统计
        if 'total_cost' in factor_results:
            total_cost = factor_results['total_cost']
            final_value = factor_results['final_value']
            cost_ratio = total_cost / final_value * 100 if final_value > 0 else 0
            
            report_lines.append("### 交易成本统计")
            report_lines.append("")
            report_lines.append(f"- **总交易成本**: {total_cost:.2f} 元")
            report_lines.append(f"- **成本占资产比**: {cost_ratio:.3f}%")
            report_lines.append(f"- **交易次数**: {factor_results.get('num_trades', 0)}")
            report_lines.append(f"- **成功成交**: {factor_results.get('num_filled', 0)}")
            if factor_results.get('num_trades', 0) > 0:
                fill_rate = factor_results.get('num_filled', 0) / factor_results.get('num_trades', 1)
                report_lines.append(f"- **成交率**: {fill_rate:.2%}")
            report_lines.append("")
    
    # 模拟盘回测结果
    if paper_trading_results and 'annual_return' in paper_trading_results:
        report_lines.append("## 📈 回测结果 - 模拟盘系统")
        report_lines.append("")
        
        # 主要指标
        report_lines.append("### 主要绩效指标")
        report_lines.append("")
        report_lines.append("| 指标 | 数值 | 评价 |")
        report_lines.append("|------|------|------|")
        
        total_return = paper_trading_results['total_return']
        report_lines.append(f"| 总收益率 | {total_return:.2%} | {'优秀' if total_return > 0.2 else '良好' if total_return > 0 else '一般'} |")
        
        annual_return = paper_trading_results['annual_return']
        report_lines.append(f"| 年化收益率 | {annual_return:.2%} | {'优秀' if annual_return > 0.15 else '良好' if annual_return > 0.1 else '一般'} |")
        
        annual_volatility = paper_trading_results['annual_volatility']
        report_lines.append(f"| 年化波动率 | {annual_volatility:.2%} | {'低' if annual_volatility < 0.15 else '中' if annual_volatility < 0.25 else '高'} |")
        
        sharpe_ratio = paper_trading_results['sharpe_ratio']
        report_lines.append(f"| 夏普比率 | {sharpe_ratio:.2f} | {'优秀' if sharpe_ratio > 2 else '良好' if sharpe_ratio > 1.5 else '一般'} |")
        
        max_drawdown = paper_trading_results['max_drawdown']
        report_lines.append(f"| 最大回撤 | {max_drawdown:.2%} | {'稳健' if abs(max_drawdown) < 0.15 else '一般' if abs(max_drawdown) < 0.25 else '激进'} |")
        
        win_rate = paper_trading_results['win_rate']
        report_lines.append(f"| 月度胜率 | {win_rate:.2%} | {'高' if win_rate > 0.6 else '中' if win_rate > 0.4 else '低'} |")
        
        report_lines.append("")
        
        # 监控摘要
        if 'monitor_summary' in paper_trading_results:
            monitor_summary = paper_trading_results['monitor_summary']
            report_lines.append("### 监控摘要")
            report_lines.append("")
            report_lines.append(f"- **总报警数**: {monitor_summary['total_alerts']}")
            for level, count in monitor_summary['by_level'].items():
                if count > 0:
                    report_lines.append(f"  - {level.upper()}: {count}")
            report_lines.append("")
        
        # 投资组合摘要
        if 'portfolio_summary' in paper_trading_results:
            portfolio_summary = paper_trading_results['portfolio_summary']
            report_lines.append("### 最终投资组合")
            report_lines.append("")
            report_lines.append(f"- **总资产**: {portfolio_summary['total_value']:,.2f} 元")
            report_lines.append(f"- **现金**: {portfolio_summary['cash']:,.2f} 元 ({portfolio_summary['cash']/portfolio_summary['total_value']:.2%})")
            report_lines.append(f"- **持仓市值**: {portfolio_summary['position_value']:,.2f} 元")
            report_lines.append(f"- **持仓数量**: {portfolio_summary['position_count']} 只")
            report_lines.append("")
            
            if portfolio_summary['position_count'] > 0:
                report_lines.append("| 股票代码 | 数量 | 均价 | 市值 | 权重 |")
                report_lines.append("|----------|------|------|------|------|")
                for code, pos in portfolio_summary['positions'].items():
                    report_lines.append(f"| {code} | {pos['quantity']} | {pos['avg_price']:.2f} | {pos['market_value']:,.2f} | {pos['weight']:.2%} |")
                report_lines.append("")
    
    # 基准模型结果
    if model_results:
        report_lines.append("## 🎓 基准模型评估")
        report_lines.append("")
        
        report_lines.append(f"- **模型类型**: {model_results['model_type']}")
        report_lines.append(f"- **特征数量**: {len(model_results['selected_features'])}")
        report_lines.append("- **选用的特征**: " + ", ".join(model_results['selected_features']))
        report_lines.append("")
        
        report_lines.append("### 交叉验证结果")
        cv_results = model_results['cv_results']
        report_lines.append(f"- **平均得分**: {cv_results['mean_score']:.4f}")
        report_lines.append(f"- **标准差**: {cv_results['std_score']:.4f}")
        report_lines.append("")
        
        report_lines.append("### 测试集性能")
        test_metrics = model_results['test_metrics']
        for metric, value in test_metrics.items():
            report_lines.append(f"- **{metric}**: {value:.4f}")
        report_lines.append("")
        
        # 特征重要性
        report_lines.append("### 特征重要性 Top 5")
        feature_importance = model_results['feature_importance']
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        for i, (feat, imp) in enumerate(sorted_features[:5], 1):
            report_lines.append(f"{i}. {feat}: {imp:.4f}")
        report_lines.append("")
    
    # 对比分析
    if factor_results and paper_trading_results:
        report_lines.append("## 🔍 对比分析")
        report_lines.append("")
        
        report_lines.append("### 因子得分 vs 模拟盘系统")
        report_lines.append("")
        report_lines.append("| 指标 | 因子得分回测 | 模拟盘系统 | 差异 |")
        report_lines.append("|------|-------------|------------|------|")
        
        metrics = [
            ('总收益率', 'total_return'),
            ('年化收益率', 'annual_return'),
            ('年化波动率', 'annual_volatility'),
            ('夏普比率', 'sharpe_ratio'),
            ('最大回撤', 'max_drawdown'),
            ('月度胜率', 'win_rate')
        ]
        
        for name, key in metrics:
            factor_val = factor_results.get(key, 0)
            paper_val = paper_trading_results.get(key, 0)
            diff = paper_val - factor_val
            
            if key in ['total_return', 'annual_return', 'sharpe_ratio', 'win_rate']:
                diff_str = f"+{diff:.4f}" if diff > 0 else f"{diff:.4f}"
            elif key in ['annual_volatility', 'max_drawdown']:
                diff_str = f"-{abs(diff):.4f}" if diff < 0 else f"+{abs(diff):.4f}"
            else:
                diff_str = f"{diff:.4f}"
            
            report_lines.append(f"| {name} | {factor_val:.4f} | {paper_val:.4f} | {diff_str} |")
        
        report_lines.append("")
    
    # 结论与建议
    report_lines.append("## 💡 结论与建议")
    report_lines.append("")
    
    if factor_results and 'sharpe_ratio' in factor_results:
        sharpe = factor_results['sharpe_ratio']
        if sharpe > 2:
            report_lines.append("### ✅ 优点")
            report_lines.append("- 策略夏普比率优秀，风险调整后收益良好")
            report_lines.append("- 回测结果稳健，可考虑进入实盘测试")
        elif sharpe > 1.5:
            report_lines.append("### ⚠️ 表现良好")
            report_lines.append("- 策略表现良好，但仍有优化空间")
            report_lines.append("- 建议增加更多因子，提升预测能力")
        else:
            report_lines.append("### ❌ 需要改进")
            report_lines.append("- 策略夏普比率偏低，需要进一步优化")
            report_lines.append("- 建议检查因子质量，调整组合构建方法")
        report_lines.append("")
    
    report_lines.append("### 下一步计划")
    report_lines.append("1. **因子优化**: 增加更多有效因子，剔除无效因子")
    report_lines.append("2. **组合优化**: 使用风险管理技术优化组合权重")
    report_lines.append("3. **回测优化**: 扩展回测时间范围，测试不同市场环境")
    report_lines.append("4. **实盘测试**: 在模拟盘运行一段时间后，考虑小规模实盘")
    report_lines.append("5. **监控系统**: 完善监控指标，增加异常检测")
    report_lines.append("")
    
    # 附录
    report_lines.append("## 📎 附录")
    report_lines.append("")
    
    if log_file:
        report_lines.append(f"- 完整日志文件: `{log_file}`")
        report_lines.append("")
    
    report_lines.append("### 系统说明")
    report_lines.append("- **回测引擎**: `code/backtest_engine_v2.py`")
    report_lines.append("- **基准模型**: `code/baseline_model.py`")
    report_lines.append("- **模拟盘系统**: `code/paper_trading.py`")
    report_lines.append("- **测试脚本**: `code/run_baseline_backtest.py`")
    report_lines.append("")
    
    report_lines.append("### 核心特性")
    report_lines.append("✅ **交易成本模型**: 包含佣金、印花税、冲击成本")
    report_lines.append("✅ **改进成交逻辑**: 支持限价单/市价单、部分成交")
    report_lines.append("✅ **仓位与风险限制**: 单票仓位上限、行业暴露限制")
    report_lines.append("✅ **模块化设计**: 数据、信号、风控、交易模块分离")
    report_lines.append("✅ **监控系统**: 日志、报警、异常检测")
    report_lines.append("✅ **无未来函数**: 严格时间序列逻辑，确保回测有效性")
    report_lines.append("")
    
    report_lines.append("---")
    report_lines.append(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    report_lines.append("*生成工具: OpenClaw 架构师 🏗️*")
    
    # 保存报告
    report_content = "\n".join(report_lines)
    report_file = os.path.join('reports', f'baseline_backtest_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md')
    os.makedirs('reports', exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"✓ 回测报告已保存: {report_file}")
    
    return report_file

def main():
    """主函数"""
    print("\n" + "="*70)
    print("🚀 A股量化系统 - 基准策略回测")
    print("="*70)
    print("")
    
    # 1. 加载数据
    data = load_data()
    
    # 2. 训练基准模型（可选）
    try:
        print("\n" + "="*70)
        print("🎓 训练基准模型（可选）")
        print("="*70)
        model, model_results = train_model(data)
    except Exception as e:
        print(f"⚠️  模型训练失败: {e}")
        model, model_results = None, None
    
    # 3. 运行回测 - 基于因子得分
    factor_results, engine = run_backtest_with_factor_score(data)
    
    # 4. 运行回测 - 模拟盘系统
    paper_trading_results, system, log_file = run_backtest_with_paper_trading(data)
    
    # 5. 生成报告
    report_file = generate_report(
        factor_results, 
        paper_trading_results, 
        model_results if model_results else None,
        log_file
    )
    
    print("\n" + "="*70)
    print("✅ 回测完成")
    print("="*70)
    print(f"📄 报告: {report_file}")
    if log_file:
        print(f"📝 日志: {log_file}")
    print("")

if __name__ == '__main__':
    main()
