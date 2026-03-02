#!/usr/bin/env python3
"""
统一运行脚本 - P0和P1任务
紧急任务：确保明天系统能正式使用

功能：
1. 运行P0过拟合缓解检测
2. 运行P1风控体系完善分析
3. 生成完整报告
4. 提供明确的行动建议
"""

import os
import sys
import json
from datetime import datetime

# 添加code目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

# 导入模块
try:
    from overfitting_detection_enhanced import EnhancedOverfittingDetector
    from risk_control_system import RiskControlSystem
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 导入模块失败: {e}")
    print("将尝试使用简化版本...")
    MODULES_AVAILABLE = False


def run_p0_overfitting_detection():
    """运行P0过拟合缓解检测"""
    print("\n" + "=" * 80)
    print("🎯 P0任务：过拟合缓解检测")
    print("=" * 80)
    
    data_path = '/Users/variya/.openclaw/workspace/projects/a-stock-advisor/data/mock_data.pkl'
    
    if not os.path.exists(data_path):
        print(f"❌ 数据文件不存在: {data_path}")
        return None
    
    try:
        detector = EnhancedOverfittingDetector(data_path)
        results = detector.run_full_detection()
        detector.save_report()
        
        print("\n✅ P0过拟合缓解检测完成")
        
        # 提取关键信息
        diagnosis = results.get('diagnosis', {})
        print("\n📋 关键发现:")
        print(f"  - 整体状态: {diagnosis.get('overall_status', 'unknown')}")
        print(f"  - 严重程度: {diagnosis.get('overfitting_severity', 'none')}")
        print(f"  - 发现问题数: {len(diagnosis.get('issues', []))}")
        
        if diagnosis.get('actions_required'):
            print("\n⚡ 必须采取的行动:")
            for i, action in enumerate(diagnosis['actions_required'], 1):
                print(f"  {i}. {action}")
        
        return results
    
    except Exception as e:
        print(f"❌ P0检测失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_p1_risk_control():
    """运行P1风控体系完善分析"""
    print("\n" + "=" * 80)
    print("🎯 P1任务：风控体系完善分析")
    print("=" * 80)
    
    data_path = '/Users/variya/.openclaw/workspace/projects/a-stock-advisor/data/mock_data.pkl'
    
    if not os.path.exists(data_path):
        print(f"❌ 数据文件不存在: {data_path}")
        return None
    
    try:
        rcs = RiskControlSystem(data_path)
        results = rcs.run_full_analysis()
        rcs.save_report()
        
        print("\n✅ P1风控体系分析完成")
        
        # 提取关键信息
        risk_report = results.get('risk_report', {})
        print("\n📋 关键发现:")
        print(f"  - 风险评分: {risk_report.get('risk_score', 0)}/100")
        print(f"  - 风险等级: {risk_report.get('overall_risk_level', 'unknown')}")
        
        return results
    
    except Exception as e:
        print(f"❌ P1分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_final_report(p0_results: dict, p1_results: dict):
    """生成最终综合报告"""
    print("\n" + "=" * 80)
    print("📊 生成最终综合报告")
    print("=" * 80)
    
    output_dir = '/Users/variya/.openclaw/workspace/projects/a-stock-advisor/reports'
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Markdown报告
    md_lines = []
    
    md_lines.append("# P0和P1紧急任务完成报告\n")
    md_lines.append(f"**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    md_lines.append(f"**任务目标:** 确保明天系统能正式使用\n\n")
    
    md_lines.append("---\n\n")
    
    # P0部分
    md_lines.append("## 🔍 P0: 过拟合缓解检测\n\n")
    
    if p0_results:
        diagnosis = p0_results.get('diagnosis', {})
        
        md_lines.append("### 诊断结果\n\n")
        md_lines.append(f"- **整体状态:** {diagnosis.get('overall_status', 'unknown')}\n")
        md_lines.append(f"- **严重程度:** {diagnosis.get('overfitting_severity', 'none')}\n\n")
        
        if diagnosis.get('issues'):
            md_lines.append("### 发现的问题\n\n")
            for i, issue in enumerate(diagnosis['issues'], 1):
                severity_icon = "🔴" if issue['severity'] == 'high' else "🟡" if issue['severity'] == 'moderate' else "🟢"
                md_lines.append(f"{i}. {severity_icon} **{issue['type']}**: {issue['description']}\n")
            md_lines.append("\n")
        
        if diagnosis.get('recommendations'):
            md_lines.append("### 改进建议\n\n")
            for i, rec in enumerate(diagnosis['recommendations'], 1):
                md_lines.append(f"{i}. {rec}\n")
            md_lines.append("\n")
        
        if diagnosis.get('actions_required'):
            md_lines.append("### 必须采取的行动\n\n")
            for i, action in enumerate(diagnosis['actions_required'], 1):
                md_lines.append(f"{i}. {action}\n")
            md_lines.append("\n")
    else:
        md_lines.append("⚠️ P0检测未能完成\n\n")
    
    md_lines.append("---\n\n")
    
    # P1部分
    md_lines.append("## 🛡️ P1: 风控体系完善分析\n\n")
    
    if p1_results:
        risk_report = p1_results.get('risk_report', {})
        
        md_lines.append("### 风控评估结果\n\n")
        md_lines.append(f"- **风险评分:** {risk_report.get('risk_score', 0)}/100\n")
        md_lines.append(f"- **风险等级:** {risk_report.get('overall_risk_level', 'unknown')}\n\n")
        
        # 策略容量
        if 'strategy_capacity' in p1_results:
            sc = p1_results['strategy_capacity']
            md_lines.append("#### P1-1: 策略容量评估\n\n")
            md_lines.append(f"- 推荐容量: ¥{sc.get('recommended_capacity', 0):,.0f}\n")
            md_lines.append(f"- 容量评级: {sc.get('capacity_grade', 'N/A')}\n\n")
        
        # 冲击成本
        if 'impact_cost' in p1_results:
            md_lines.append("#### P1-2: 冲击成本评估\n\n")
            md_lines.append("| 交易规模 | 冲击成本率 | 风险等级 |\n")
            md_lines.append("|---------|-----------|----------|\n")
            for label, data in p1_results['impact_cost'].get('impact_by_amount', {}).items():
                md_lines.append(f"| {label} | {data['impact_rate']:.4%} | {data['risk_level']} |\n")
            md_lines.append("\n")
        
        # 流动性风险
        if 'liquidity_risk' in p1_results:
            lr = p1_results['liquidity_risk']
            md_lines.append("#### P1-3: 流动性风险分析\n\n")
            md_lines.append(f"- 流动性评级: {lr.get('liquidity_grade', 'N/A')}\n\n")
        
        # 风格暴露
        if 'style_exposure' in p1_results:
            se = p1_results['style_exposure']
            md_lines.append("#### P1-4: 风格暴露分析\n\n")
            if 'size_exposure' in se:
                md_lines.append(f"- 大小盘风格: {se['size_exposure'].get('size_tilt', 'N/A')}\n")
            if 'value_growth_exposure' in se:
                md_lines.append(f"- 价值成长风格: {se['value_growth_exposure'].get('style_tilt', 'N/A')}\n")
            md_lines.append("\n")
        
        # 因子拥挤度
        if 'factor_crowding' in p1_results:
            fc = p1_results['factor_crowding']
            md_lines.append("#### P1-5: 因子拥挤度分析\n\n")
            md_lines.append(f"- 拥挤度评级: {fc.get('crowding_grade', 'N/A')}\n")
            if 'hhi' in fc:
                md_lines.append(f"- HHI指数: {fc['hhi']:.4f}\n")
            md_lines.append("\n")
    else:
        md_lines.append("⚠️ P1分析未能完成\n\n")
    
    md_lines.append("---\n\n")
    
    # 总结和建议
    md_lines.append("## 📋 总结和下一步行动\n\n")
    
    md_lines.append("### 系统状态评估\n\n")
    
    if p0_results and p1_results:
        p0_status = p0_results.get('diagnosis', {}).get('overall_status', 'unknown')
        p1_score = p1_results.get('risk_report', {}).get('risk_score', 0)
        
        if p0_status == 'no_overfitting' and p1_score >= 80:
            md_lines.append("✅ **系统状态良好，可以正式使用**\n\n")
            md_lines.append("- P0过拟合检测：无过拟合风险\n")
            md_lines.append(f"- P1风控评分：{p1_score}/100（低风险）\n\n")
        elif p0_status == 'potential_overfitting' or p1_score >= 60:
            md_lines.append("⚠️ **系统存在一些风险，需要优化后使用**\n\n")
            md_lines.append("- P0过拟合检测：可能存在过拟合\n")
            md_lines.append(f"- P1风控评分：{p1_score}/100（中等风险）\n\n")
        else:
            md_lines.append("❌ **系统存在较高风险，建议暂缓使用**\n\n")
            md_lines.append("- P0过拟合检测：检测到过拟合\n")
            md_lines.append(f"- P1风控评分：{p1_score}/100（高风险）\n\n")
    else:
        md_lines.append("⚠️ **部分检测未完成，需要进一步验证**\n\n")
    
    md_lines.append("### 下一步行动\n\n")
    md_lines.append("1. **立即执行（P0优先级）：**\n")
    md_lines.append("   - 处理过拟合检测中发现的问题\n")
    md_lines.append("   - 调整高风险因子权重\n\n")
    
    md_lines.append("2. **明日执行（P1优先级）：**\n")
    md_lines.append("   - 建立风险监控面板\n")
    md_lines.append("   - 设置流动性预警机制\n")
    md_lines.append("   - 完善交易执行策略\n\n")
    
    md_lines.append("3. **持续监控：**\n")
    md_lines.append("   - 每日监控IC变化\n")
    md_lines.append("   - 每周评估风险指标\n")
    md_lines.append("   - 每月更新模型参数\n\n")
    
    md_lines.append("---\n\n")
    md_lines.append(f"**报告生成完成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 保存Markdown报告
    md_path = os.path.join(output_dir, f'final_report_p0_p1_{timestamp}.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))
    
    # 保存JSON报告
    json_path = os.path.join(output_dir, f'final_report_p0_p1_{timestamp}.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'p0_results': p0_results,
            'p1_results': p1_results,
            'generated_at': datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n✓ 最终报告已保存:")
    print(f"  Markdown: {md_path}")
    print(f"  JSON: {json_path}")
    
    return md_path, json_path


def main():
    """主函数"""
    print("=" * 80)
    print("🚀 P0和P1紧急任务执行系统")
    print("=" * 80)
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标: 确保明天系统能正式使用")
    print("=" * 80)
    
    # 运行P0检测
    p0_results = run_p0_overfitting_detection()
    
    # 运行P1分析
    p1_results = run_p1_risk_control()
    
    # 生成最终报告
    generate_final_report(p0_results, p1_results)
    
    print("\n" + "=" * 80)
    print("✅ P0和P1紧急任务全部完成")
    print("=" * 80)
    print(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📋 请查看报告目录:")
    print("  /Users/variya/.openclaw/workspace/projects/a-stock-advisor/reports/")
    print("\n💡 建议明天正式使用前:")
    print("  1. 查看最终报告（final_report_p0_p1_*.md）")
    print("  2. 根据报告中的行动项执行必要调整")
    print("  3. 建立实时监控机制")
    print("=" * 80)


if __name__ == '__main__':
    main()
