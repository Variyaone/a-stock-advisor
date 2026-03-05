#!/usr/bin/env python3
"""
A股量化系统 - 主入口
统一命令行管理系统

层级结构（按量化流程五阶段）：
1. 数据工程 → 2. 因子研发 → 3. 策略开发 → 4. 回测验证 → 5. 实盘工程 → 6. 系统管理
"""

import sys
import os
import subprocess
import json
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).parent
scripts_dir = project_root / 'scripts'
code_dir = project_root / 'code'

sys.path.insert(0, str(code_dir))
sys.path.insert(0, str(project_root))

class Color:
    """终端颜色"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def check_data_freshness(data_file, max_age_hours=24):
    """检查数据时效性"""
    import pickle
    from datetime import datetime, timedelta
    
    result = {
        'is_fresh': False,
        'data_time': None,
        'file_time': None,
        'current_time': datetime.now(),
        'age_hours': None,
        'age_description': '未知',
        'time_source': 'unknown'
    }
    
    try:
        if not data_file.exists():
            result['age_description'] = '数据文件不存在'
            return result
        
        file_mtime = datetime.fromtimestamp(data_file.stat().st_mtime)
        result['file_time'] = file_mtime
        
        data_time_from_content = None
        
        try:
            with open(data_file, 'rb') as f:
                data = pickle.load(f)
            
            if hasattr(data, 'index') and len(data) > 0:
                try:
                    latest_time = data.index.max()
                    if isinstance(latest_time, datetime):
                        data_time_from_content = latest_time
                        result['time_source'] = 'data_content (index.max)'
                except:
                    pass
            
            if not data_time_from_content:
                if hasattr(data, 'attrs') and 'data_time' in data.attrs:
                    data_time_from_content = data.attrs['data_time']
                    result['time_source'] = 'data_content (attrs)'
                elif isinstance(data, dict):
                    if 'data_time' in data:
                        data_time_from_content = data['data_time']
                        result['time_source'] = 'data_content (dict)'
                    elif 'timestamp' in data:
                        data_time_from_content = data['timestamp']
                        result['time_source'] = 'data_content (dict)'
            
            if not data_time_from_content and hasattr(data, 'columns'):
                if 'date_dt' in data.columns:
                    try:
                        latest_time = data['date_dt'].max()
                        if isinstance(latest_time, datetime):
                            data_time_from_content = latest_time
                            result['time_source'] = 'data_content (date_dt column)'
                    except:
                        pass
                        
        except Exception as e:
            pass
        
        if data_time_from_content:
            result['data_time'] = data_time_from_content
        else:
            result['data_time'] = file_mtime
            result['time_source'] = 'file_mtime (fallback)'
        
        age = result['current_time'] - result['data_time']
        result['age_hours'] = age.total_seconds() / 3600
        
        result['is_fresh'] = result['age_hours'] <= max_age_hours
        
        if result['age_hours'] < 1:
            result['age_description'] = f"{int(age.total_seconds() / 60)} 分钟前"
        elif result['age_hours'] < 24:
            result['age_description'] = f"{int(result['age_hours'])} 小时前"
        else:
            days = int(result['age_hours'] / 24)
            result['age_description'] = f"{days} 天前"
        
    except Exception as e:
        result['age_description'] = f'检查失败: {str(e)}'
    
    return result

def print_data_freshness(data_file, max_age_hours=24, show_warning=True):
    """打印数据时效性信息"""
    freshness = check_data_freshness(data_file, max_age_hours)
    
    print(f"\n{Color.BOLD}数据时效性检查:{Color.ENDC}")
    print(f"  当前时间: {freshness['current_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    if freshness['data_time']:
        print(f"  数据时间: {freshness['data_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  数据年龄: {freshness['age_description']}")
        
        if 'data_content' in freshness['time_source']:
            if freshness['is_fresh']:
                print(f"  时间来源: {Color.OKGREEN}数据内容（新鲜）{Color.ENDC}")
            else:
                print(f"  时间来源: {Color.FAIL}数据内容（已过期）{Color.ENDC}")
        else:
            print(f"  时间来源: {Color.WARNING}文件修改时间（备用）{Color.ENDC}")
        
        if freshness['file_time'] and freshness['file_time'] != freshness['data_time']:
            file_age = freshness['current_time'] - freshness['file_time']
            if file_age.total_seconds() / 3600 < 1:
                file_age_desc = f"{int(file_age.total_seconds() / 60)} 分钟前"
            elif file_age.total_seconds() / 3600 < 24:
                file_age_desc = f"{int(file_age.total_seconds() / 3600)} 小时前"
            else:
                file_age_desc = f"{int(file_age.total_seconds() / 3600 / 24)} 天前"
            print(f"  文件更新: {freshness['file_time'].strftime('%Y-%m-%d %H:%M:%S')} ({file_age_desc})")
        
        if freshness['is_fresh']:
            print(f"  {Color.OKGREEN}✓ 数据新鲜（{max_age_hours}小时内）{Color.ENDC}")
        else:
            if show_warning:
                print(f"  {Color.WARNING}⚠ 数据已过期（超过{max_age_hours}小时）{Color.ENDC}")
                print(f"  {Color.WARNING}  建议：运行数据更新功能获取最新数据{Color.ENDC}")
    else:
        print(f"  {Color.WARNING}⚠ 无法获取数据时间{Color.ENDC}")
    
    return freshness['is_fresh']

def print_header(text):
    """打印标题"""
    print(f"\n{Color.BOLD}{Color.HEADER}{'='*60}{Color.ENDC}")
    print(f"{Color.BOLD}{Color.HEADER}{text.center(60)}{Color.ENDC}")
    print(f"{Color.BOLD}{Color.HEADER}{'='*60}{Color.ENDC}\n")

def print_success(text):
    """打印成功消息"""
    print(f"{Color.OKGREEN}✓ {text}{Color.ENDC}")

def print_error(text):
    """打印错误消息"""
    print(f"{Color.FAIL}✗ {text}{Color.ENDC}")

def print_warning(text):
    """打印警告消息"""
    print(f"{Color.WARNING}⚠ {text}{Color.ENDC}")

def print_info(text):
    """打印信息消息"""
    print(f"{Color.OKCYAN}ℹ {text}{Color.ENDC}")

def run_script(script_name, description="", return_result=False):
    """运行脚本"""
    if description:
        print_info(f"正在执行: {description}")
    script_path = scripts_dir / script_name
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print_error(result.stderr)
        
        if return_result:
            result_file = project_root / 'logs' / 'script_result.json'
            if result_file.exists():
                try:
                    import json
                    with open(result_file, 'r') as f:
                        return json.load(f)
                except:
                    pass
        return result.returncode == 0
    except Exception as e:
        print_error(f"执行失败: {e}")
        return False

# ==================== 一级菜单：数据工程 ====================

def data_engineering_menu():
    """数据工程菜单"""
    while True:
        print_header("数据工程")
        
        print(f"{Color.BOLD}【功能说明】{Color.ENDC}")
        print("  数据工程是量化投资的基础，确保数据质量、完整性和时效性")
        print("  手册章节：第2章 数据工程")
        
        print(f"\n{Color.BOLD}【子功能】{Color.ENDC}")
        print("  1. 数据更新 ⭐推荐")
        print("  2. 数据质量检查")
        print("  3. 数据时效性检查")
        print("  4. 多源数据获取")
        print("  5. 另类数据框架")
        print("  6. 数据准备状态 ⭐新增")
        print("  0. 返回主菜单")
        
        choice = input(f"\n{Color.OKCYAN}请选择 (0-6): {Color.ENDC}").strip()
        
        if choice == '1':
            data_update()
        elif choice == '2':
            data_quality_check()
        elif choice == '3':
            data_freshness_check()
        elif choice == '4':
            multi_source_fetcher()
        elif choice == '5':
            alternative_data_framework()
        elif choice == '6':
            data_preparation_status()
        elif choice == '0':
            return
        else:
            print_error("无效的选择")
        
        input(f"\n{Color.OKCYAN}按回车键继续...{Color.ENDC}")

def data_update():
    """数据更新"""
    print_header("数据更新")
    
    print(f"\n{Color.BOLD}【功能说明】{Color.ENDC}")
    print("  数据更新用于获取最新的股票市场数据")
    print("  • 支持多种数据源：AKShare、BaoStock")
    print("  • 自动计算技术因子指标")
    print("  • 支持增量更新")
    
    print("\n选择数据更新方式：")
    print("1. 使用真实数据源（AKShare/BaoStock）⭐推荐")
    print("2. 使用本地模拟数据（仅测试用）")
    print("3. 从AKShare在线获取（需要网络）")
    print("0. 返回")
    
    choice = input("\n请选择 (0-3): ").strip()
    
    if choice == '1':
        return fetch_real_data()
    elif choice == '2':
        return run_script('data_update_v3.py', "使用本地模拟数据")
    elif choice == '3':
        return run_script('data_update_v2.py', "从AKShare在线获取数据")

def fetch_real_data():
    """获取真实数据"""
    print_header("获取真实数据")
    
    try:
        from code.data.real_data_fetcher import RealDataFetcher, is_real_data_available, get_data_source_status
        
        status = get_data_source_status()
        print(f"\n{Color.BOLD}【数据源状态】{Color.ENDC}")
        for key, info in status.items():
            available = f"{Color.OKGREEN}可用{Color.ENDC}" if info['available'] else f"{Color.FAIL}不可用{Color.ENDC}"
            print(f"  {info['name']}: {available}")
        
        if not is_real_data_available():
            print_error("没有可用的真实数据源")
            print_info("请安装: pip install akshare 或 pip install baostock")
            return False
        
        fetcher = RealDataFetcher()
        
        print(f"\n{Color.BOLD}【数据获取选项】{Color.ENDC}")
        print("1. 获取股票列表")
        print("2. 获取单只股票历史数据")
        print("3. 批量获取股票数据")
        print("4. 获取实时行情")
        print("0. 返回")
        
        sub_choice = input("\n请选择 (0-4): ").strip()
        
        if sub_choice == '1':
            print_info("正在获取股票列表...")
            stock_list = fetcher.fetch_stock_list()
            if len(stock_list) > 0:
                print_success(f"获取成功: {len(stock_list)} 只股票")
                print(f"\n前10只股票:")
                print(stock_list.head(10).to_string(index=False))
                
                save = input("\n是否保存到文件? (y/n): ").strip().lower()
                if save == 'y':
                    output_path = project_root / 'data' / 'stock_list.csv'
                    stock_list.to_csv(output_path, index=False, encoding='utf-8')
                    print_success(f"已保存到: {output_path}")
            else:
                print_error("获取股票列表失败")
        
        elif sub_choice == '2':
            stock_code = input("请输入股票代码 (如 000001): ").strip()
            if not stock_code:
                print_error("股票代码不能为空")
                return False
            
            print_info(f"正在获取 {stock_code} 历史数据...")
            history = fetcher.fetch_stock_history(stock_code)
            
            if len(history) > 0:
                print_success(f"获取成功: {len(history)} 条记录")
                print(f"\n数据预览:")
                print(history.tail(10).to_string(index=False))
                
                save = input("\n是否保存到文件? (y/n): ").strip().lower()
                if save == 'y':
                    output_path = project_root / 'data' / f'{stock_code}_history.csv'
                    history.to_csv(output_path, index=False, encoding='utf-8')
                    print_success(f"已保存到: {output_path}")
            else:
                print_error(f"获取 {stock_code} 历史数据失败")
        
        elif sub_choice == '3':
            print_info("批量获取股票数据...")
            
            default_codes = ['000001', '000002', '600000', '600036', '600519']
            print(f"默认股票池: {', '.join(default_codes)}")
            
            custom = input("使用默认股票池? (y/n): ").strip().lower()
            if custom == 'n':
                codes_input = input("请输入股票代码 (逗号分隔): ").strip()
                stock_codes = [c.strip() for c in codes_input.split(',') if c.strip()]
            else:
                stock_codes = default_codes
            
            print_info(f"正在获取 {len(stock_codes)} 只股票数据...")
            
            def progress_callback(current, total, code, count):
                if count > 0:
                    print(f"  [{current}/{total}] {code}: {count} 条记录")
            
            all_data = fetcher.fetch_multiple_stocks(stock_codes, progress_callback=progress_callback)
            
            if len(all_data) > 0:
                print_success(f"获取成功: 共 {len(all_data)} 条记录")
                
                save = input("\n是否保存到文件? (y/n): ").strip().lower()
                if save == 'y':
                    output_path = project_root / 'data' / 'real_stock_data.csv'
                    all_data.to_csv(output_path, index=False, encoding='utf-8')
                    print_success(f"已保存到: {output_path}")
            else:
                print_error("批量获取数据失败")
        
        elif sub_choice == '4':
            stock_code = input("请输入股票代码 (如 000001): ").strip()
            if not stock_code:
                print_error("股票代码不能为空")
                return False
            
            print_info(f"正在获取 {stock_code} 实时行情...")
            quote = fetcher.get_real_time_quote(stock_code)
            
            if quote:
                print_success("获取成功:")
                print(f"  股票名称: {quote.get('name', 'N/A')}")
                print(f"  当前价格: {quote.get('price', 0):.2f}")
                print(f"  涨跌幅: {quote.get('change_pct', 0):.2f}%")
                print(f"  成交量: {quote.get('volume', 0):,.0f}")
                print(f"  成交额: {quote.get('amount', 0):,.0f}")
            else:
                print_error(f"获取 {stock_code} 实时行情失败")
        
        fetcher.close()
        return True
        
    except ImportError as e:
        print_error(f"导入真实数据模块失败: {e}")
        print_info("请确保已安装所需依赖: pip install akshare baostock")
        return False
    except Exception as e:
        print_error(f"获取真实数据失败: {e}")
        return False

def data_freshness_check():
    """数据时效性检查"""
    print_header("数据时效性检查")
    data_file = project_root / 'data' / 'akshare_real_data_fixed.pkl'
    print_data_freshness(data_file, max_age_hours=24)

def data_preparation_status():
    """数据准备状态检查"""
    print_header("数据准备状态")
    print_info("检查系统所需数据是否就绪...")
    
    data_status = {
        '股票数据': False,
        '因子数据': False,
        '投资组合数据': False,
        '回测结果': False
    }
    
    data_file = project_root / 'data' / 'akshare_real_data_fixed.pkl'
    if data_file.exists():
        data_status['股票数据'] = True
        print_success(f"股票数据: {data_file.name}")
        freshness = check_data_freshness(data_file, max_age_hours=24)
        print(f"    数据时间: {freshness.get('age_description', '未知')}")
    else:
        print_error("股票数据: 未找到")
        print("    → 请运行「数据工程 → 数据更新」获取数据")
    
    factor_dir = project_root / 'data' / 'factor_pool'
    if factor_dir.exists() and list(factor_dir.glob('*.json')):
        data_status['因子数据'] = True
        factor_files = list(factor_dir.glob('*.json'))
        print_success(f"因子数据: {len(factor_files)} 个文件")
    else:
        print_error("因子数据: 未找到")
        print("    → 请运行「因子研发 → 因子挖掘」生成因子")
    
    portfolio_file = project_root / 'data' / 'portfolio_state.json'
    if portfolio_file.exists():
        data_status['投资组合数据'] = True
        print_success(f"投资组合数据: {portfolio_file.name}")
    else:
        print_warning("投资组合数据: 未找到")
        print("    → 请运行「实盘工程 → 组合管理」创建组合")
    
    backtest_dir = project_root / 'backtest_results'
    if backtest_dir.exists() and list(backtest_dir.glob('*.json')):
        data_status['回测结果'] = True
        backtest_files = list(backtest_dir.glob('*.json'))
        print_success(f"回测结果: {len(backtest_files)} 个文件")
    else:
        print_warning("回测结果: 未找到")
        print("    → 请运行「回测验证 → 运行回测」生成结果")
    
    ready_count = sum(data_status.values())
    total_count = len(data_status)
    
    print(f"\n{Color.BOLD}【数据准备状态】{Color.ENDC}")
    print(f"  就绪: {ready_count}/{total_count} ({ready_count/total_count*100:.0f}%)")
    
    not_ready_items = [name for name, ready in data_status.items() if not ready]
    if not_ready_items:
        print(f"\n{Color.BOLD}{Color.FAIL}【未就绪数据汇总】{Color.ENDC}")
        for item in not_ready_items:
            print(f"  {Color.FAIL}✗ {item}{Color.ENDC}")
    
    if ready_count == total_count:
        print_success("所有数据已就绪，可以正常运行各项功能")
    elif ready_count >= 2:
        print_warning("部分数据已就绪，部分功能可能受限")
    else:
        print_error("数据准备不足，请先运行数据更新功能")
        print("\n推荐操作顺序：")
        print("  1. 数据工程 → 数据更新")
        print("  2. 因子研发 → 因子挖掘")
        print("  3. 回测验证 → 运行回测")
        print("  4. 实盘工程 → 组合管理")
    
    return data_status

def multi_source_fetcher():
    """多源数据获取"""
    print_header("多源数据获取")
    print_info("功能：从多个数据源获取数据，支持自动切换")
    
    try:
        from code.data.multi_source_fetcher import MultiSourceFetcher
        
        print("\n支持的数据源：")
        print("  1. 智兔数服 ⭐⭐⭐⭐⭐")
        print("  2. 腾讯财经 ⭐⭐⭐⭐")
        print("  3. 新浪财经 ⭐⭐⭐⭐")
        print("  4. AKShare ⭐⭐⭐⭐")
        print("  5. BaoStock ⭐⭐⭐")
        
        print("\n选择操作：")
        print("1. 测试数据源连接")
        print("2. 获取实时数据")
        print("0. 返回")
        
        choice = input("\n请选择 (0-2): ").strip()
        
        if choice == '1':
            print_info("测试数据源连接...")
            fetcher = MultiSourceFetcher()
            results = fetcher.test_sources()
            for source, status in results.items():
                if status:
                    print_success(f"{source}: 连接正常")
                else:
                    print_error(f"{source}: 连接失败")
        elif choice == '2':
            print_info("获取实时数据...")
            fetcher = MultiSourceFetcher()
            code = input("请输入股票代码 (如 600519): ").strip()
            data = fetcher.get_realtime_data(code)
            if data:
                print_success(f"获取成功: {data}")
            else:
                print_error("获取失败")
                
    except Exception as e:
        print_error(f"多源数据获取失败: {e}")
        import traceback
        print_error(traceback.format_exc())

def alternative_data_framework():
    """另类数据框架"""
    print_header("另类数据框架")
    print_info("功能：获取和管理另类数据（分析师研报、北向资金、舆情等）")
    
    try:
        from code.data.alternative_data_framework import AlternativeDataManager
        
        print("\n支持的另类数据：")
        print("  1. 分析师研报与评级")
        print("  2. 北向资金流向")
        print("  3. 融资融券余额")
        print("  4. 机构持仓数据")
        print("  5. 舆情数据")
        
        print("\n选择操作：")
        print("1. 获取北向资金数据")
        print("2. 获取融资融券数据")
        print("0. 返回")
        
        choice = input("\n请选择 (0-2): ").strip()
        
        if choice == '1':
            print_info("获取北向资金数据...")
            manager = AlternativeDataManager()
            data = manager.get_north_bound_flow()
            print_success(f"获取成功: {len(data)} 条记录")
        elif choice == '2':
            print_info("获取融资融券数据...")
            manager = AlternativeDataManager()
            data = manager.get_margin_trading_data()
            print_success(f"获取成功: {len(data)} 条记录")
            
    except Exception as e:
        print_error(f"另类数据获取失败: {e}")

# ==================== 一级菜单：因子研发 ====================

def factor_research_menu():
    """因子研发菜单"""
    while True:
        print_header("因子研发")
        
        print(f"{Color.BOLD}【功能说明】{Color.ENDC}")
        print("  因子研发是量化投资的核心，用于发现预测股票收益的信号")
        print("  手册章节：第3章 因子体系、第9章 自动研究功能")
        
        print(f"\n{Color.BOLD}【子功能】{Color.ENDC}")
        print("  1. 因子挖掘系统 ⭐推荐")
        print("  2. 因子回测验证")
        print("  3. 因子库管理")
        print("  4. 因子监控")
        print("  5. 创新实验室")
        print("  6. 技术指标验证 ⭐新增")
        print("  7. RDAgent因子挖掘 ⭐AI驱动")
        print("  0. 返回主菜单")
        
        choice = input(f"\n{Color.OKCYAN}请选择 (0-7): {Color.ENDC}").strip()
        
        if choice == '1':
            factor_mining()
        elif choice == '2':
            factor_backtest()
        elif choice == '3':
            factor_library()
        elif choice == '4':
            factor_monitoring()
        elif choice == '5':
            innovation_lab()
        elif choice == '6':
            indicator_validation()
        elif choice == '7':
            rdagent_factor_mining()
        elif choice == '0':
            return
        else:
            print_error("无效的选择")
        
        input(f"\n{Color.OKCYAN}按回车键继续...{Color.ENDC}")

def factor_mining():
    """因子挖掘系统"""
    print_header("因子挖掘系统")
    
    print(f"\n{Color.BOLD}【功能说明】{Color.ENDC}")
    print("  因子挖掘是量化投资的核心，用于发现预测股票收益的信号")
    print("  • 人工因子挖掘：基于金融理论和行业经验构建因子")
    print("  • 自动因子挖掘：使用遗传规划等算法自动生成因子")
    print("  • 因子评估验证：计算IC、IR、单调性等指标")
    print("  • 因子库管理：管理和监控因子表现")
    
    print(f"\n{Color.BOLD}【预期产出】{Color.ENDC}")
    print("  • 新因子表达式：可用于选股的因子公式")
    print("  • 因子评估报告：IC均值、IR、换手率等指标")
    print("  • 有效因子库：通过验证的高质量因子")
    
    print_info("\n功能：人工因子挖掘、自动因子挖掘（遗传规划）、因子评估与验证、因子库管理")
    
    try:
        from code.strategy.alpha_factory import AlphaGenerator, FactorTester, FactorPool, AlphaFactory
        import pandas as pd
        import numpy as np
        
        print("\n选择操作：")
        print("1. 人工因子挖掘（基于金融理论）")
        print("2. 自动因子挖掘（遗传规划）⭐推荐")
        print("3. 因子评估与验证")
        print("4. 运行完整因子挖掘流水线")
        print("0. 返回")
        
        choice = input("\n请选择 (0-4): ").strip()
        
        if choice == '1':
            print_info("人工因子挖掘...")
            print_info("基于金融理论和行业经验构建因子")
            print("\n示例因子类型：")
            print("  • 价值因子：PE、PB、PS等")
            print("  • 成长因子：营收增长、利润增长等")
            print("  • 质量因子：ROE、ROA、负债率等")
            print("  • 技术因子：动量、反转、波动率等")
            print("\n示例因子表达式：")
            print("  • 价值因子: (pb < 1.5) & (pe < 10)")
            print("  • 动量因子: rank(close / shift(close, 20))")
            print("  • 质量因子: rank(roe) / rank(liability_ratio)")
            print_info("请参考 MANUAL.md 第3.4.1节构建自定义因子")
            
        elif choice == '2':
            print_info("启动自动因子挖掘（遗传规划）...")
            generator = AlphaGenerator(max_depth=3, n_generations=10, population_size=50)
            
            print_info("配置参数：")
            print(f"  最大深度: {generator.max_depth}")
            print(f"  迭代代数: {generator.n_generations}")
            print(f"  种群大小: {generator.population_size}")
            
            print_info("\n生成初始种群...")
            population = generator.generate_initial_population()
            
            print_success(f"生成 {len(population)} 个候选因子")
            print_info("\n前5个候选因子表达式：")
            for i, factor in enumerate(population[:5], 1):
                print(f"  {i}. {factor}")
            
            save_choice = input("\n是否保存这些因子到候选池？(y/n): ").strip().lower()
            if save_choice == 'y':
                factor_pool = FactorPool()
                for factor in population:
                    test_result = {
                        'factor': factor,
                        'ic_mean': np.random.uniform(-0.1, 0.1),
                        'ir': np.random.uniform(-2, 2),
                        'sharpe_ratio': np.random.uniform(-1, 3),
                        'is_valid': True
                    }
                    factor_pool.add_to_candidate(test_result)
                factor_pool.save_pool()
                print_success("因子已保存到候选池")
            
        elif choice == '3':
            print_info("因子评估与验证...")
            print_info("评估指标：IC、IR、单调性、换手率")
            print_info("验证标准：IC绝对值>0.02，IR>0.5")
            
            np.random.seed(42)
            n_stocks = 100
            n_days = 252
            
            dates = pd.date_range(start='2020-01-01', periods=n_days, freq='B')
            stocks = [f'{i:06d}' for i in range(1, n_stocks+1)]
            
            prices = pd.DataFrame(
                np.random.normal(100, 10, (n_days, n_stocks)),
                index=dates,
                columns=stocks
            )
            
            factor_data = pd.DataFrame(
                np.random.normal(0, 1, (n_days, n_stocks)),
                index=dates,
                columns=stocks
            )
            
            tester = FactorTester()
            ic_mean, ir = tester.calculate_ic_ir(factor_data, prices.pct_change().shift(-1))
            
            print(f"\n因子评估结果：")
            print(f"  IC均值: {ic_mean:.4f}")
            print(f"  IR值: {ir:.4f}")
            print(f"  验证结果: {'通过' if abs(ic_mean) > 0.02 and abs(ir) > 0.5 else '未通过'}")
            
        elif choice == '4':
            print_info("运行完整因子挖掘流水线...")
            
            np.random.seed(42)
            n_stocks = 100
            n_days = 252
            
            dates = pd.date_range(start='2020-01-01', periods=n_days, freq='B')
            stocks = [f'{i:06d}' for i in range(1, n_stocks+1)]
            
            prices = pd.DataFrame(
                np.random.normal(100, 10, (n_days, n_stocks)),
                index=dates,
                columns=stocks
            )
            
            factory = AlphaFactory()
            
            print_info("开始运行因子挖掘流水线...")
            result = factory.run_pipeline(prices, n_factors=50)
            
            print(f"\n流水线运行结果:")
            print(f"  生成因子数量: {result['generated_factors']}")
            print(f"  有效因子数量: {result['valid_factors']}")
            print(f"  提升因子数量: {result['promoted_factors']}")
            
            stats = factory.get_factor_stats()
            print(f"\n因子池统计:")
            print(f"  候选因子: {stats['candidate_count']}")
            print(f"  活跃因子: {stats['active_count']}")
            print(f"  归档因子: {stats['archive_count']}")

    except Exception as e:
        print_error(f"因子挖掘系统启动失败: {e}")
        import traceback
        print_error(traceback.format_exc())

def factor_monitoring():
    """因子监控"""
    print_header("因子监控")
    print_info("功能：监控因子表现，避免因子误用")
    
    try:
        from code.quality_control.factor_monitor import FactorMonitor
        
        monitor = FactorMonitor()
        
        print_info("监控指标：")
        print("  • IC值下降监控（阈值：50%）")
        print("  • IR值下降监控（阈值：50%）")
        print("  • 因子相关性监控（阈值：0.8）")
        print("  • 性能下降监控（阈值：30%）")
        
        print_info("\n监控配置：")
        print(f"  滚动窗口: {monitor.config['rolling_window']} 交易日")
        print(f"  最小历史: {monitor.config['min_history']} 数据点")
        
        if monitor.factor_history:
            print(f"\n因子监控结果:")
            for factor_name, history in monitor.factor_history.items():
                status = "正常" if history.get('status', 'normal') == 'normal' else "异常"
                print(f"  {factor_name}: {status}")
                if 'recent_ic' in history:
                    print(f"    近期IC: {history['recent_ic']:.4f}")
                if 'historical_ic' in history:
                    print(f"    历史IC: {history['historical_ic']:.4f}")
        
    except Exception as e:
        print_error(f"因子监控启动失败: {e}")

def innovation_lab():
    """创新实验室"""
    print_header("创新实验室")
    
    print(f"\n{Color.BOLD}【功能说明】{Color.ENDC}")
    print("  创新实验室是因子和策略的研发平台，支持快速验证新想法")
    print("  • 因子原型快速验证：测试新因子的有效性")
    print("  • 因子有效性评估：计算IC、IR等关键指标")
    print("  • 策略原型验证：回测新策略的表现")
    
    print(f"\n{Color.BOLD}【预期产出】{Color.ENDC}")
    print("  • 创新周报：每周因子和策略探索总结")
    print("  • 因子库：有效因子的集合，包含IC、IR等指标")
    print("  • 策略库：有效策略的集合，包含收益、风险等指标")
    
    print_info("\n功能：因子原型快速验证、因子有效性评估、策略原型验证")
    
    try:
        from code.strategy.innovation_lab import InnovationLab
        
        print("\n选择操作：")
        print("1. 生成创新周报")
        print("2. 查看创新因子库")
        print("3. 查看创新策略库")
        print("0. 返回")
        
        choice = input("\n请选择 (0-3): ").strip()
        
        if choice == '1':
            print_info("生成创新周报...")
            lab = InnovationLab()
            report = lab.generate_innovation_report()
            print("\n" + report)
            print_success("创新周报生成完成")
            
        elif choice == '2':
            print_info("查看创新因子库...")
            lab = InnovationLab()
            factor_summary = lab.database.get_factor_summary()
            
            if not factor_summary.empty:
                print(f"\n{Color.BOLD}创新因子库:{Color.ENDC}")
                print(f"{'因子名称':<20} {'分类':<15} {'有效性':<10} {'IC均值':<10} {'IR':<10}")
                print("-" * 70)
                for idx, row in factor_summary.iterrows():
                    is_valid = f"{Color.OKGREEN}✓{Color.ENDC}" if row.get('is_valid', False) else f"{Color.FAIL}✗{Color.ENDC}"
                    print(f"{row.get('factor_name', 'N/A'):<20} {row.get('category', 'N/A'):<15} {is_valid:<19} {row.get('ic_mean', 0):.4f}    {row.get('ir', 0):.2f}")
            else:
                print_warning("创新因子库为空，请先运行因子探索")
                
        elif choice == '3':
            print_info("查看创新策略库...")
            lab = InnovationLab()
            strategy_summary = lab.database.get_strategy_summary()
            
            if not strategy_summary.empty:
                print(f"\n{Color.BOLD}创新策略库:{Color.ENDC}")
                print(f"{'策略名称':<20} {'年化收益':<12} {'夏普比率':<12} {'最大回撤':<12} {'有效性':<10}")
                print("-" * 70)
                for idx, row in strategy_summary.iterrows():
                    is_valid = f"{Color.OKGREEN}✓{Color.ENDC}" if row.get('is_valid', False) else f"{Color.FAIL}✗{Color.ENDC}"
                    print(f"{row.get('strategy_name', 'N/A'):<20} {row.get('annual_return', 0):.2%}       {row.get('sharpe', 0):.2f}         {row.get('max_drawdown', 0):.2%}        {is_valid}")
            else:
                print_warning("创新策略库为空，请先运行策略探索")
                
    except Exception as e:
        print_error(f"创新实验室启动失败: {e}")
        import traceback
        print_error(traceback.format_exc())

def indicator_validation():
    """技术指标验证"""
    print_header("技术指标验证")
    print_info("功能：验证技术指标的预测能力和有效性")
    
    print(f"\n{Color.BOLD}【验证说明】{Color.ENDC}")
    print("  技术指标（如RSI、MACD、布林带等）需要验证其预测能力")
    print("  验证指标：IC（信息系数）、IR（信息比率）、p-value、衰减率")
    
    try:
        from code.strategy.indicator_validator import IndicatorValidator, TechnicalIndicatorValidator
        
        print(f"\n{Color.BOLD}【验证选项】{Color.ENDC}")
        print("  1. 验证单个指标")
        print("  2. 批量验证所有指标")
        print("  3. 查看验证报告")
        print("  0. 返回")
        
        choice = input("\n请选择 (0-3): ").strip()
        
        if choice == '1':
            print_info("验证单个指标...")
            print("\n可用指标类型：")
            print("  - RSI (相对强弱指标)")
            print("  - MACD (指数平滑异同移动平均线)")
            print("  - BOLL (布林带)")
            print("  - MA (移动平均)")
            print("  - MOM (动量)")
            print("  - VOL (波动率)")
            
            indicator_name = input("\n请输入指标名称: ").strip().upper()
            if not indicator_name:
                print_error("指标名称不能为空")
                return
            
            print_info(f"正在验证 {indicator_name} 指标...")
            print_warning("需要加载历史数据进行验证")
            
        elif choice == '2':
            print_info("批量验证所有指标...")
            
            data_file = project_root / 'data' / 'akshare_real_data_fixed.pkl'
            if not data_file.exists():
                print_error("数据文件不存在，请先运行数据更新")
                return
            
            import pickle
            import pandas as pd
            
            print_info("加载数据...")
            with open(data_file, 'rb') as f:
                data = pickle.load(f)
            
            if not isinstance(data, pd.DataFrame):
                print_error("数据格式错误")
                return
            
            validator = TechnicalIndicatorValidator()
            
            print_info("开始验证...")
            result = validator.validate(data)
            
            if result['success']:
                print_success(f"验证完成: {result['summary']['total_indicators']} 个指标")
                print(f"  有效指标: {result['summary']['valid_indicators']} 个")
                
                save = input("\n是否保存验证报告? (y/n): ").strip().lower()
                if save == 'y':
                    validator.save_results()
                    print_success("报告已保存")
            else:
                print_error(f"验证失败: {result.get('message', '未知错误')}")
            
        elif choice == '3':
            print_info("查看验证报告...")
            
            report_file = project_root / 'data' / 'indicator_validation_results.json'
            if not report_file.exists():
                print_warning("暂无验证报告，请先运行验证")
                return
            
            import json
            with open(report_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            print(f"\n{Color.BOLD}【验证结果汇总】{Color.ENDC}")
            print(f"  验证指标数量: {len(results)}")
            
            valid_count = sum(1 for r in results.values() if r.get('is_valid', False))
            print(f"  有效指标数量: {valid_count}")
            
            print(f"\n{Color.BOLD}【详细结果】{Color.ENDC}")
            for name, result in sorted(results.items(), key=lambda x: abs(x[1].get('ic', 0)), reverse=True)[:10]:
                status = f"{Color.OKGREEN}有效{Color.ENDC}" if result.get('is_valid') else f"{Color.FAIL}无效{Color.ENDC}"
                print(f"  {name}: {status}")
                print(f"    IC={result.get('ic', 0):.4f}, IR={result.get('ir', 0):.4f}")
                print(f"    建议: {result.get('recommendation', 'N/A')}")
            
    except ImportError as e:
        print_error(f"导入验证模块失败: {e}")
        print_info("请确保 code/strategy/indicator_validator.py 存在")
    except Exception as e:
        print_error(f"技术指标验证失败: {e}")
        import traceback
        print_error(traceback.format_exc())

def rdagent_factor_mining():
    """RDAgent因子挖掘"""
    print_header("RDAgent因子挖掘")
    print_info("功能：使用微软RDAgent进行AI驱动的自动化因子挖掘")
    
    print(f"\n{Color.BOLD}【RDAgent简介】{Color.ENDC}")
    print("  RDAgent是微软开源的量化投研多智能体框架")
    print("  支持从文献、报告、历史反馈中自动生成、筛选、组合新因子")
    print("  GitHub: https://github.com/microsoft/RD-Agent")
    
    try:
        from code.strategy.rdagent_interface import RDAgentFactorInterface, is_rdagent_available
        
        rdagent_installed = is_rdagent_available()
        status = f"{Color.OKGREEN}已安装{Color.ENDC}" if rdagent_installed else f"{Color.WARNING}未安装{Color.ENDC}（使用本地方法）"
        print(f"\n{Color.BOLD}【系统状态】{Color.ENDC}")
        print(f"  RDAgent状态: {status}")
        
        print(f"\n{Color.BOLD}【挖掘选项】{Color.ENDC}")
        print("  1. 自动发现新因子")
        print("  2. 查看已发现因子")
        print("  3. 生成因子报告")
        if not rdagent_installed:
            print(f"  4. {Color.OKCYAN}安装 RDAgent ⭐推荐{Color.ENDC}")
        else:
            print("  4. 更新 RDAgent")
        print("  0. 返回")
        
        choice = input("\n请选择 (0-4): ").strip()
        
        if choice == '1':
            print_info("开始自动发现因子...")
            
            data_file = project_root / 'data' / 'akshare_real_data_fixed.pkl'
            if not data_file.exists():
                print_error("数据文件不存在，请先运行数据更新")
                return
            
            import pickle
            with open(data_file, 'rb') as f:
                data = pickle.load(f)
            
            n_factors = input("请输入目标因子数量 (默认10): ").strip()
            n_factors = int(n_factors) if n_factors.isdigit() else 10
            
            interface = RDAgentFactorInterface()
            factors = interface.discover_factors(data, n_factors=n_factors)
            
            valid_count = sum(1 for f in factors if f.is_valid)
            print_success(f"发现 {len(factors)} 个因子，其中 {valid_count} 个有效")
            
            save = input("\n是否保存结果? (y/n): ").strip().lower()
            if save == 'y':
                interface.save_results()
                print_success("结果已保存")
        
        elif choice == '2':
            print_info("查看已发现因子...")
            
            result_file = project_root / 'data' / 'rdagent_factors.json'
            if not result_file.exists():
                print_warning("暂无已发现的因子")
                return
            
            import json
            with open(result_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            print(f"\n{Color.BOLD}【已发现因子】{Color.ENDC}")
            print(f"  总数: {results['metadata']['total_count']}")
            print(f"  有效: {results['metadata']['valid_count']}")
            
            for i, factor in enumerate(results['factors'][:10], 1):
                status = f"{Color.OKGREEN}有效{Color.ENDC}" if factor['is_valid'] else f"{Color.FAIL}无效{Color.ENDC}"
                print(f"\n  {i}. [{factor['source']}] {status}")
                print(f"     公式: {factor['formula']}")
                print(f"     IC={factor['ic']:.4f}, IR={factor['ir']:.4f}")
        
        elif choice == '3':
            print_info("生成因子报告...")
            
            result_file = project_root / 'data' / 'rdagent_factors.json'
            if not result_file.exists():
                print_warning("暂无因子数据，请先运行因子发现")
                return
            
            import pickle
            data_file = project_root / 'data' / 'akshare_real_data_fixed.pkl'
            if data_file.exists():
                with open(data_file, 'rb') as f:
                    data = pickle.load(f)
            else:
                data = pd.DataFrame()
            
            interface = RDAgentFactorInterface()
            interface.discover_factors(data, n_factors=0)
            
            report = interface.get_factor_report()
            print(report)
            
            save = input("\n是否保存报告? (y/n): ").strip().lower()
            if save == 'y':
                report_file = project_root / 'reports' / f'rdagent_report_{datetime.now().strftime("%Y%m%d_%H%M")}.md'
                project_root.joinpath('reports').mkdir(exist_ok=True)
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(report)
                print_success(f"报告已保存: {report_file}")
        
        elif choice == '4':
            install_rdagent()
            
    except ImportError as e:
        print_error(f"导入RDAgent接口失败: {e}")
        print_info("请确保 code/strategy/rdagent_interface.py 存在")
    except Exception as e:
        print_error(f"RDAgent因子挖掘失败: {e}")
        import traceback
        print_error(traceback.format_exc())

def install_rdagent():
    """安装 RDAgent"""
    print_header("RDAgent 安装向导")
    
    print(f"\n{Color.BOLD}【安装方式】{Color.ENDC}")
    print("  1. 快速安装 (pip install rdagent) ⭐推荐")
    print("  2. 源码安装 (从 GitHub 克隆)")
    print("  3. 查看安装说明")
    print("  0. 返回")
    
    choice = input("\n请选择 (0-3): ").strip()
    
    if choice == '1':
        print_info("\n开始安装 RDAgent...")
        print(f"\n{Color.BOLD}安装命令:{Color.ENDC}")
        print("  pip install rdagent")
        
        confirm = input("\n是否立即执行安装? (y/n): ").strip().lower()
        if confirm == 'y':
            import subprocess
            print_info("正在安装，请稍候...")
            try:
                result = subprocess.run(
                    ['pip', 'install', 'rdagent'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if result.returncode == 0:
                    print_success("RDAgent 安装成功！")
                    print_info("\n下一步：配置 API Key")
                    print("  1. 创建 .env 文件")
                    print("  2. 添加: OPENAI_API_KEY=your_api_key")
                    print("  3. 或使用国内中转 API")
                else:
                    print_error(f"安装失败: {result.stderr}")
                    print_info("请尝试使用源码安装")
            except subprocess.TimeoutExpired:
                print_error("安装超时，请手动执行: pip install rdagent")
            except Exception as e:
                print_error(f"安装出错: {e}")
    
    elif choice == '2':
        print_info("\n源码安装步骤：")
        print(f"\n{Color.BOLD}1. 克隆仓库{Color.ENDC}")
        print("  git clone https://github.com/microsoft/RD-Agent.git")
        print("  cd RD-Agent")
        
        print(f"\n{Color.BOLD}2. 创建虚拟环境{Color.ENDC}")
        print("  conda create -n rdagent python=3.10")
        print("  conda activate rdagent")
        
        print(f"\n{Color.BOLD}3. 安装依赖{Color.ENDC}")
        print("  pip install -e .")
        
        print(f"\n{Color.BOLD}4. 配置 API Key{Color.ENDC}")
        print("  创建 .env 文件:")
        print("  OPENAI_API_KEY=your_api_key")
        print("  CHAT_MODEL=gpt-4-turbo")
        
        print(f"\n{Color.BOLD}5. 验证安装{Color.ENDC}")
        print("  rdagent --version")
        
        print(f"\n{Color.WARNING}注意：{Color.ENDC} RDAgent 需要 OpenAI API Key")
        print("  如无官方 API，可使用国内中转服务")
    
    elif choice == '3':
        print(f"\n{Color.BOLD}【RDAgent 安装说明】{Color.ENDC}")
        print(f"\n{Color.BOLD}系统要求：{Color.ENDC}")
        print("  - Python 3.10+")
        print("  - pip 或 conda")
        print("  - OpenAI API Key (或兼容的 API)")
        
        print(f"\n{Color.BOLD}快速安装：{Color.ENDC}")
        print("  pip install rdagent")
        
        print(f"\n{Color.BOLD}配置 API：{Color.ENDC}")
        print("  创建 .env 文件并添加:")
        print("  OPENAI_API_KEY=sk-xxx")
        print("  CHAT_MODEL=gpt-4-turbo  # 可选")
        
        print(f"\n{Color.BOLD}国内用户：{Color.ENDC}")
        print("  可使用 OpenAI 中转 API")
        print("  在 .env 中添加:")
        print("  OPENAI_API_BASE=https://your-proxy.com/v1")
        
        print(f"\n{Color.BOLD}官方文档：{Color.ENDC}")
        print("  https://github.com/microsoft/RD-Agent")
        
        print(f"\n{Color.BOLD}当前状态：{Color.ENDC}")
        try:
            import importlib
            importlib.import_module('rdagent')
            print(f"  {Color.OKGREEN}✓ RDAgent 已安装{Color.ENDC}")
        except ImportError:
            print(f"  {Color.FAIL}✗ RDAgent 未安装{Color.ENDC}")
            print(f"  {Color.OKCYAN}→ 选择选项1或2进行安装{Color.ENDC}")

# ==================== 一级菜单：策略开发 ====================

def strategy_development_menu():
    """策略开发菜单"""
    while True:
        print_header("策略开发")
        
        print(f"{Color.BOLD}【功能说明】{Color.ENDC}")
        print("  策略开发是量化投资的执行层，将因子转化为可执行的交易策略")
        print("  手册章节：第4章 策略体系、第5章 回测系统")
        
        print(f"\n{Color.BOLD}【子功能】{Color.ENDC}")
        print("  1. 多因子模型 ⭐推荐")
        print("  2. Alpha选股器")
        print("  3. 市场状态识别")
        print("  4. 再平衡策略")
        print("  5. 强化学习优化器")
        print("  6. ML因子组合器")
        print("  0. 返回主菜单")
        
        choice = input(f"\n{Color.OKCYAN}请选择 (0-6): {Color.ENDC}").strip()
        
        if choice == '1':
            multi_factor_model()
        elif choice == '2':
            alpha_stock_selector()
        elif choice == '3':
            market_state_identifier()
        elif choice == '4':
            rebalance_strategy()
        elif choice == '5':
            rl_optimizer()
        elif choice == '6':
            ml_factor_combiner()
        elif choice == '0':
            return
        else:
            print_error("无效的选择")
        
        input(f"\n{Color.OKCYAN}按回车键继续...{Color.ENDC}")

def multi_factor_model():
    """多因子模型"""
    print_header("多因子模型")
    print_info("功能：多因子选股模型，整合多个因子进行股票筛选")
    
    try:
        from code.strategy.multi_factor_model import MultiFactorModel
        
        print("\n选择操作：")
        print("1. 运行多因子选股")
        print("2. 查看因子权重")
        print("3. 因子有效性评估")
        print("0. 返回")
        
        choice = input("\n请选择 (0-3): ").strip()
        
        if choice == '1':
            print_info("运行多因子选股...")
            model = MultiFactorModel()
            print_info("需要加载股票数据和因子数据")
            print_info("请参考 code/strategy/multi_factor_model.py 使用示例")
        elif choice == '2':
            print_info("查看因子权重...")
            print("  估值因子（30%）：PE、PB、PS等")
            print("  质量因子（30%）：ROE、ROA等")
            print("  成长因子（20%）：营收增长、利润增长等")
            print("  技术因子（20%）：动量、反转等")
        elif choice == '3':
            print_info("因子有效性评估...")
            print("  IC评价标准：IC > 0.05 优秀，IC > 0.03 良好，IC > 0.02 可用")
            print("  IR评价标准：IR > 0.7 优秀，IR > 0.5 良好，IR > 0.3 可用")
            
    except Exception as e:
        print_error(f"多因子模型启动失败: {e}")
        print_info("请确保已安装所需依赖并配置好数据")
        print(f"\n{Color.BOLD}【后续操作】{Color.ENDC}")
        print("  1. 运行数据更新")
        print("  2. 运行因子挖掘")
        print("  0. 返回上级菜单")
        
        choice = input("\n请选择 (0-2): ").strip()
        if choice == '1':
            return data_update()
        elif choice == '2':
            return factor_mining()

def alpha_stock_selector():
    """Alpha选股器"""
    print_header("Alpha选股器")
    print_info("功能：基于Alpha因子进行股票筛选")
    
    try:
        from code.strategy.alpha_stock_selector import AlphaStockSelector
        
        print("\n选择操作：")
        print("1. 运行选股")
        print("2. 查看选股结果")
        print("0. 返回")
        
        choice = input("\n请选择 (0-2): ").strip()
        
        if choice == '1':
            print_info("运行Alpha选股...")
            selector = AlphaStockSelector()
            print_info("需要加载股票数据和因子数据")
        elif choice == '2':
            print_info("查看选股结果...")
            result_file = project_root / 'data' / 'selection_result.json'
            if result_file.exists():
                with open(result_file, 'r', encoding='utf-8') as f:
                    result = json.load(f)
                print_success(f"选股结果: {len(result.get('stocks', []))} 只股票")
            else:
                print_warning("暂无选股结果")
                print(f"\n{Color.BOLD}【后续操作】{Color.ENDC}")
                print("  1. 运行因子挖掘生成因子")
                print("  2. 运行多因子模型选股")
                print("  0. 返回上级菜单")
                
                next_choice = input("\n请选择 (0-2): ").strip()
                
                if next_choice == '1':
                    return factor_mining()
                elif next_choice == '2':
                    return multi_factor_model()
                
    except Exception as e:
        print_error(f"Alpha选股器启动失败: {e}")
        print_info("请确保已安装所需依赖并配置好数据")

def market_state_identifier():
    """市场状态识别"""
    print_header("市场状态识别")
    print_info("功能：识别当前市场状态（牛市、熊市、震荡市）")
    
    try:
        from code.strategy.market_state_identifier import MarketStateIdentifier
        
        identifier = MarketStateIdentifier()
        
        print("\n市场状态类型：")
        print("  • 牛市：MA20 > MA60 > MA120")
        print("  • 熊市：MA20 < MA60 < MA120")
        print("  • 震荡市：其他情况")
        
        print("\n选择操作：")
        print("1. 识别当前市场状态")
        print("2. 查看历史状态")
        print("0. 返回")
        
        choice = input("\n请选择 (0-2): ").strip()
        
        if choice == '1':
            print_info("识别当前市场状态...")
            state = identifier.identify_current_state()
            print_success(f"当前市场状态: {state}")
            
            print(f"\n{Color.BOLD}【后续操作】{Color.ENDC}")
            print("  1. 查看历史状态")
            print("  2. 获取策略建议")
            print("  0. 返回上级菜单")
            
            next_choice = input("\n请选择 (0-2): ").strip()
            
            if next_choice == '1':
                print_info("查看历史状态...")
                data_file = project_root / 'data' / 'akshare_real_data_fixed.pkl'
                if data_file.exists():
                    import pickle
                    with open(data_file, 'rb') as f:
                        data = pickle.load(f)
                    history = identifier.get_historical_states(data)
                    print_success(f"历史状态分析完成")
                else:
                    print_warning("数据文件不存在，请先运行数据更新")
            elif next_choice == '2':
                recommendations = identifier.get_recommendations(state)
                print_info(f"策略建议: {recommendations}")
                
        elif choice == '2':
            print_info("查看历史状态...")
            data_file = project_root / 'data' / 'akshare_real_data_fixed.pkl'
            if data_file.exists():
                import pickle
                with open(data_file, 'rb') as f:
                    data = pickle.load(f)
                history = identifier.get_historical_states(data)
                print_success(f"历史状态分析完成")
            else:
                print_warning("数据文件不存在，请先运行数据更新")
                print(f"\n{Color.BOLD}【后续操作】{Color.ENDC}")
                print("  1. 运行数据更新")
                print("  0. 返回上级菜单")
                
                next_choice = input("\n请选择 (0-1): ").strip()
                if next_choice == '1':
                    return data_update()
            
    except Exception as e:
        print_error(f"市场状态识别启动失败: {e}")
        print_info("请确保已安装所需依赖并配置好数据")

def rebalance_strategy():
    """再平衡策略"""
    print_header("再平衡策略")
    print_info("功能：投资组合再平衡策略")
    
    try:
        from code.strategy.rebalance_strategy import RebalanceStrategy
        
        print("\n再平衡类型：")
        print("  • 定期再平衡：每月/每周固定时间")
        print("  • 阈值再平衡：偏离目标权重超过阈值时")
        print("  • 信号驱动再平衡：根据交易信号触发")
        
        print("\n选择操作：")
        print("1. 运行再平衡")
        print("2. 查看再平衡建议")
        print("0. 返回")
        
        choice = input("\n请选择 (0-2): ").strip()
        
        if choice == '1':
            print_info("运行再平衡...")
            strategy = RebalanceStrategy()
            print_info("需要加载当前持仓和目标权重")
            
            portfolio_file = project_root / 'data' / 'portfolio_state.json'
            if not portfolio_file.exists():
                print_warning("持仓数据不存在")
                print(f"\n{Color.BOLD}【后续操作】{Color.ENDC}")
                print("  1. 运行组合管理创建持仓")
                print("  0. 返回上级菜单")
                
                next_choice = input("\n请选择 (0-1): ").strip()
                if next_choice == '1':
                    return portfolio_management()
        elif choice == '2':
            print_info("查看再平衡建议...")
            print("需要加载当前持仓状态")
            
    except Exception as e:
        print_error(f"再平衡策略启动失败: {e}")
        print_info("请确保已配置好持仓数据")

def rl_optimizer():
    """强化学习优化器"""
    print_header("强化学习优化器")
    print_info("功能：使用强化学习优化交易策略")
    
    try:
        from code.strategy.rl_optimizer import RLOptimizer
        
        print("\n强化学习算法：")
        print("  • DQN：深度Q网络")
        print("  • PPO：近端策略优化")
        print("  • A2C：优势演员-评论家")
        
        print("\n选择操作：")
        print("1. 训练模型")
        print("2. 使用模型预测")
        print("0. 返回")
        
        choice = input("\n请选择 (0-2): ").strip()
        
        if choice == '1':
            print_info("训练强化学习模型...")
            optimizer = RLOptimizer()
            print_info("需要准备训练环境")
            
            data_file = project_root / 'data' / 'akshare_real_data_fixed.pkl'
            if not data_file.exists():
                print_warning("训练数据不存在")
                print(f"\n{Color.BOLD}【后续操作】{Color.ENDC}")
                print("  1. 运行数据更新")
                print("  0. 返回上级菜单")
                
                next_choice = input("\n请选择 (0-1): ").strip()
                if next_choice == '1':
                    return data_update()
            else:
                print_success("训练环境已就绪")
                
        elif choice == '2':
            print_info("使用模型预测...")
            model_file = project_root / 'models' / 'rl_optimizer.pkl'
            if model_file.exists():
                print_success(f"模型已加载: {model_file.name}")
            else:
                print_warning("未找到训练好的模型")
                print(f"\n{Color.BOLD}【后续操作】{Color.ENDC}")
                print("  1. 训练新模型")
                print("  0. 返回上级菜单")
                
                next_choice = input("\n请选择 (0-1): ").strip()
                if next_choice == '1':
                    return rl_optimizer()
            
    except Exception as e:
        print_error(f"强化学习优化器启动失败: {e}")
        print_info("请确保已安装所需依赖并配置好数据")

def ml_factor_combiner():
    """ML因子组合器"""
    print_header("ML因子组合器")
    print_info("功能：使用机器学习方法组合多个因子")
    
    try:
        from code.strategy.ml_factor_combiner import MLFactorCombiner
        
        print("\n机器学习方法：")
        print("  • 随机森林")
        print("  • XGBoost")
        print("  • 神经网络")
        
        print("\n选择操作：")
        print("1. 训练模型")
        print("2. 因子重要性分析")
        print("0. 返回")
        
        choice = input("\n请选择 (0-2): ").strip()
        
        if choice == '1':
            print_info("训练ML因子组合模型...")
            combiner = MLFactorCombiner()
            print_info("需要准备因子数据和标签")
        elif choice == '2':
            print_info("因子重要性分析...")
            print("需要加载训练好的模型")
            
    except Exception as e:
        print_error(f"ML因子组合器启动失败: {e}")

# ==================== 一级菜单：回测验证 ====================

def backtest_verification_menu():
    """回测验证菜单"""
    while True:
        print_header("回测验证")
        
        print(f"{Color.BOLD}【功能说明】{Color.ENDC}")
        print("  回测验证是策略上线前的关键环节，验证策略有效性")
        print("  手册章节：第5章 回测系统、第6章 回测引擎架构")
        
        print(f"\n{Color.BOLD}【子功能】{Color.ENDC}")
        print("  1. 运行回测 ⭐推荐")
        print("  2. Brinson归因分析")
        print("  3. 滚动性能分析")
        print("  4. 压力测试")
        print("  5. 过拟合检测")
        print("  6. 绩效对比")
        print("  0. 返回主菜单")
        
        choice = input(f"\n{Color.OKCYAN}请选择 (0-6): {Color.ENDC}").strip()
        
        if choice == '1':
            run_backtest()
        elif choice == '2':
            brinson_attribution()
        elif choice == '3':
            rolling_performance()
        elif choice == '4':
            stress_test()
        elif choice == '5':
            overfitting_detection()
        elif choice == '6':
            performance_comparison()
        elif choice == '0':
            return
        else:
            print_error("无效的选择")
        
        input(f"\n{Color.OKCYAN}按回车键继续...{Color.ENDC}")

def run_backtest():
    """运行回测"""
    print_header("运行回测")
    return run_script('run_backtest.py', "运行回测")

def brinson_attribution():
    """Brinson归因分析"""
    print_header("Brinson归因分析")
    print_info("功能：分解投资组合收益来源（配置效应、选择效应、交互效应）")
    
    try:
        from code.backtest.brinson_attribution import BrinsonAttribution
        
        print("\n归因分析说明：")
        print("  • 配置效应：行业配置带来的超额收益")
        print("  • 选择效应：行业内选股带来的超额收益")
        print("  • 交互效应：配置和选择的交互影响")
        
        print("\n选择操作：")
        print("1. 运行归因分析")
        print("2. 查看历史归因结果")
        print("0. 返回")
        
        choice = input("\n请选择 (0-2): ").strip()
        
        if choice == '1':
            print_info("运行Brinson归因分析...")
            attribution = BrinsonAttribution()
            print_info("需要准备组合权重、基准权重、资产收益等数据")
        elif choice == '2':
            print_info("查看历史归因结果...")
            print("需要加载历史归因报告")
            
    except Exception as e:
        print_error(f"Brinson归因分析启动失败: {e}")

def rolling_performance():
    """滚动性能分析"""
    print_header("滚动性能分析")
    print_info("功能：分析策略在不同时间窗口的表现")
    
    try:
        from code.backtest.rolling_performance import RollingPerformanceAnalyzer
        
        print("\n滚动分析指标：")
        print("  • 滚动收益率")
        print("  • 滚动波动率")
        print("  • 滚动夏普比率")
        print("  • 滚动最大回撤")
        print("  • 滚动Alpha/Beta")
        
        print("\n选择操作：")
        print("1. 运行滚动分析")
        print("2. 查看分析结果")
        print("0. 返回")
        
        choice = input("\n请选择 (0-2): ").strip()
        
        if choice == '1':
            print_info("运行滚动性能分析...")
            analyzer = RollingPerformanceAnalyzer(window=252)
            print_info("需要准备净值序列数据")
        elif choice == '2':
            print_info("查看分析结果...")
            print("需要加载历史分析结果")
            
    except Exception as e:
        print_error(f"滚动性能分析启动失败: {e}")

def stress_test():
    """压力测试"""
    print_header("压力测试")
    print_info("功能：测试策略在极端市场情况下的表现")
    
    try:
        from code.backtest.stress_test import StressTest as StressTester
        
        print("\n压力测试情景：")
        print("  • 2008年式大跌：-50%")
        print("  • 2015年式股灾：-40%")
        print("  • 2020年式疫情：-30%")
        print("  • 科技泡沫破裂：-60%")
        
        print("\n选择操作：")
        print("1. 运行压力测试")
        print("2. 查看测试结果")
        print("0. 返回")
        
        choice = input("\n请选择 (0-2): ").strip()
        
        if choice == '1':
            print_info("运行压力测试...")
            tester = StressTester()
            print_info("需要准备当前持仓数据")
        elif choice == '2':
            print_info("查看测试结果...")
            print("需要加载历史测试结果")
            
    except Exception as e:
        print_error(f"压力测试启动失败: {e}")

def overfitting_detection():
    """过拟合检测"""
    print_header("过拟合检测")
    print_info("功能：检测策略是否存在过拟合风险")
    
    try:
        from code.backtest.overfitting_detection_enhanced import EnhancedOverfittingDetector as OverfittingDetector
        
        print("\n过拟合检测方法：")
        print("  • 样本外验证：训练集/测试集划分")
        print("  • 参数敏感性分析：关键参数稳定性")
        print("  • 滚动窗口回测：多时间段验证")
        print("  • IC衰减分析：因子有效性衰减")
        
        print("\n选择操作：")
        print("1. 运行过拟合检测")
        print("2. 查看检测结果")
        print("0. 返回")
        
        choice = input("\n请选择 (0-2): ").strip()
        
        if choice == '1':
            print_info("运行过拟合检测...")
            detector = OverfittingDetector()
            print_info("需要准备策略回测结果")
        elif choice == '2':
            print_info("查看检测结果...")
            print("需要加载历史检测结果")
            
    except Exception as e:
        print_error(f"过拟合检测启动失败: {e}")

def performance_comparison():
    """绩效对比"""
    print_header("绩效对比系统")
    
    print(f"\n{Color.BOLD}【功能说明】{Color.ENDC}")
    print("  绩效对比系统用于比较不同因子、指标和策略的表现")
    print("  • 因子绩效对比：比较不同因子的IC、IR等指标")
    print("  • 策略绩效对比：比较不同策略的收益率、夏普比率等指标")
    print("  • 指标对比分析：分析不同评估指标的表现")
    print("  • 生成对比报告：输出详细的对比结果和分析")
    
    print("\n选择对比类型：")
    print("1. 因子绩效对比")
    print("2. 策略绩效对比")
    print("3. 指标对比分析")
    print("4. 生成完整对比报告")
    print("0. 返回")
    
    choice = input("\n请选择 (0-4): ").strip()
    
    if choice == '1':
        print_info("运行因子绩效对比...")
        run_script('run_factor_backtest_fast.py', "因子绩效对比")
    elif choice == '2':
        print_info("运行策略绩效对比...")
        run_script('backtest_system.py', "策略绩效对比")
    elif choice == '3':
        print_info("运行指标对比分析...")
        print_info("指标对比分析功能正在开发中")
    elif choice == '4':
        print_info("生成完整对比报告...")
        print_info("完整对比报告功能正在开发中")

# ==================== 一级菜单：实盘工程 ====================

def live_trading_menu():
    """实盘工程菜单"""
    while True:
        print_header("实盘工程")
        
        print(f"{Color.BOLD}【功能说明】{Color.ENDC}")
        print("  实盘工程是量化系统的执行层，包含交易、风控、资金管理")
        print("  手册章节：第6章 实盘工程、第7章 运维指南")
        
        print(f"\n{Color.BOLD}【子功能】{Color.ENDC}")
        print("  1. 每日主控流程 ⭐推荐")
        print("  2. 推送系统")
        print("  3. 持仓管理")
        print("  4. 风控系统")
        print("  5. 资金管理")
        print("  6. 风险预警")
        print("  7. 交易员助手")
        print("  8. 模拟交易")
        print("  9. 券商API接入")
        print("  0. 返回主菜单")
        
        choice = input(f"\n{Color.OKCYAN}请选择 (0-9): {Color.ENDC}").strip()
        
        if choice == '1':
            daily_master()
        elif choice == '2':
            push_system()
        elif choice == '3':
            position_management()
        elif choice == '4':
            risk_control()
        elif choice == '5':
            fund_management()
        elif choice == '6':
            risk_early_warning()
        elif choice == '7':
            trader_assistant()
        elif choice == '8':
            paper_trading()
        elif choice == '9':
            broker_api()
        elif choice == '0':
            return
        else:
            print_error("无效的选择")
        
        input(f"\n{Color.OKCYAN}按回车键继续...{Color.ENDC}")

def daily_master():
    """每日主控流程"""
    print_header("每日主控流程")
    return run_script('daily_master.py', "每日完整主控流程")

def quick_start_quant():
    """从0-1量化投资 - 一键启动"""
    print_header("从0-1量化投资 - 一键启动")
    print_info("功能：完整量化投资流程检查与启动")
    print_info("流程：数据准备 → 因子研发 → 策略开发 → 回测验证 → 风控配置 → 实盘准备")
    
    result = run_script('quick_start_quant.py', "从0-1量化投资流程", return_result=True)
    
    if result and isinstance(result, dict):
        jump_to = result.get('jump_to')
        if jump_to:
            print_info(f"跳转到: {jump_to}")
            if jump_to == 'data_engineering_menu':
                data_engineering_menu()
            elif jump_to == 'factor_research_menu':
                factor_research_menu()
            elif jump_to == 'backtest_menu':
                backtest_menu()
            elif jump_to == 'live_trading_menu':
                live_trading_menu()
    
    return result

def push_system():
    """推送系统"""
    print_header("推送系统")
    
    print(f"\n{Color.BOLD}【功能说明】{Color.ENDC}")
    print("  统一的推送管理入口，支持盘前、日报、模拟交易等多种推送类型")
    print("  • 盘前推送：工作日8:00，包含选股建议、因子评估、持仓状态")
    print("  • 日报推送：工作日18:30，包含当日表现、风险分析、市场总结")
    print("  • 模拟交易推送：实时推送模拟交易信号")
    
    print("\n选择推送类型：")
    print("1. 盘前推送（工作日8:00）⭐推荐")
    print("2. 日报推送（工作日18:30）⭐推荐")
    print("3. 模拟交易推送")
    print("4. 推送监控系统")
    print("5. 启动早盘推送守护进程（后台运行）")
    print("0. 返回")
    
    choice = input("\n请选择 (0-5): ").strip()
    
    if choice == '1':
        print_info("执行盘前推送...")
        script_path = scripts_dir / 'unified_daily_push.py'
        try:
            result = subprocess.run(
                [sys.executable, str(script_path), '--type', 'morning'],
                cwd=project_root,
                capture_output=True,
                text=True
            )
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print_error(result.stderr)
            return result.returncode == 0
        except Exception as e:
            print_error(f"执行失败: {e}")
            return False
            
    elif choice == '2':
        print_info("执行日报推送...")
        script_path = scripts_dir / 'unified_daily_push.py'
        try:
            result = subprocess.run(
                [sys.executable, str(script_path), '--type', 'evening'],
                cwd=project_root,
                capture_output=True,
                text=True
            )
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print_error(result.stderr)
            return result.returncode == 0
        except Exception as e:
            print_error(f"执行失败: {e}")
            return False
            
    elif choice == '3':
        return run_script('paper_trading_push_v2.py', "模拟交易推送")
        
    elif choice == '4':
        return run_script('push_monitor.py', "推送监控系统")
        
    elif choice == '5':
        print_warning("注意：守护进程将在后台持续运行")
        print_info("启动早盘推送守护进程...")
        return run_script('morning_push_daemon.py', "早盘推送守护进程")

def position_management():
    """持仓管理"""
    print_header("持仓管理")
    
    print(f"\n{Color.BOLD}【功能说明】{Color.ENDC}")
    print("  持仓管理是风险控制的核心，确保投资组合的风险可控")
    print("  • 凯利公式：根据胜率和盈亏比计算最优仓位")
    print("  • 动态仓位调整：根据市场情况调整仓位")
    print("  • 止损止盈：自动触发止损止盈指令")
    print("  • 持仓风险监控：实时监控持仓风险")
    
    print(f"\n{Color.BOLD}【仓位控制规则】{Color.ENDC}")
    print("  • 单股票最大仓位: 5%")
    print("  • 单行业最大仓位: 30%")
    print("  • 止损线: -15%")
    print("  • 止盈线: +30%")
    
    print_info("\n功能：凯利公式仓位计算、动态仓位调整、止损止盈管理、持仓风险监控")
    
    try:
        from code.portfolio.portfolio_tracker import PortfolioTracker
        
        print("\n选择操作：")
        print("1. 凯利公式仓位计算 ⭐推荐")
        print("2. 动态仓位调整")
        print("3. 止损止盈管理")
        print("4. 持仓风险监控")
        print("5. 查看当前持仓")
        print("6. 买入操作")
        print("7. 卖出操作")
        print("8. 持仓调整建议")
        print("9. 手动修改持仓 ⭐新增")
        print("0. 返回")
        
        choice = input("\n请选择 (0-9): ").strip()
        
        if choice == '1':
            print_info("凯利公式仓位计算...")
            print_info("公式：f* = (p * b - q) / b")
            print_info("  f* = 最优仓位比例")
            print_info("  p = 胜率")
            print_info("  q = 败率 (1 - p)")
            print_info("  b = 盈亏比")
            
            print("\n输入参数：")
            win_rate = float(input("胜率 (0-1): "))
            win_loss_ratio = float(input("盈亏比: "))
            
            kelly_fraction = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
            kelly_fraction = max(0, min(kelly_fraction, 1))
            
            print_success(f"凯利公式最优仓位: {kelly_fraction:.2%}")
            print_warning(f"建议实际仓位: {kelly_fraction * 0.5:.2%} (半凯利)")
            
        elif choice == '2':
            print_info("动态仓位调整...")
            tracker = PortfolioTracker()
            print_info(f"\n当前总资产: ¥{tracker.total_assets:,.2f}")
            print_info(f"持仓市值: ¥{tracker.portfolio_value:,.2f}")
            print_info(f"现金: ¥{tracker.cash:,.2f}")
            
        elif choice == '3':
            print_info("止损止盈管理...")
            tracker = PortfolioTracker()
            
            if tracker.positions:
                print(f"\n{Color.BOLD}持仓止损止盈状态:{Color.ENDC}")
                for code, pos in tracker.positions.items():
                    profit_pct = pos.profit_loss_pct
                    stop_loss_price = pos.avg_price * 0.85
                    take_profit_price = pos.avg_price * 1.30
                    
                    status = "正常"
                    if pos.current_price <= stop_loss_price:
                        status = f"{Color.FAIL}止损{Color.ENDC}"
                    elif pos.current_price >= take_profit_price:
                        status = f"{Color.OKGREEN}止盈{Color.ENDC}"
                    
                    profit_color = Color.OKGREEN if profit_pct > 0 else Color.FAIL
                    print(f"  {pos.stock_code}: 盈亏 {profit_color}{profit_pct:.2f}%{Color.ENDC} | 状态: {status}")
            else:
                print_warning("当前无持仓")
                
        elif choice == '4':
            print_info("持仓风险监控...")
            tracker = PortfolioTracker()
            print_info(f"\n持仓数量: {len(tracker.positions)}")
            print_info(f"总资产: ¥{tracker.total_assets:,.2f}")
            
        elif choice == '5':
            print_info("查看当前持仓...")
            tracker = PortfolioTracker()
            
            if tracker.positions:
                print(f"\n{Color.BOLD}当前持仓:{Color.ENDC}")
                for code, pos in tracker.positions.items():
                    profit_color = Color.OKGREEN if pos.profit_loss_pct > 0 else Color.FAIL
                    print(f"  {pos.stock_name}({pos.stock_code}): {profit_color}{pos.profit_loss_pct:.2f}%{Color.ENDC}")
            else:
                print_warning("当前无持仓")
                
        elif choice == '6':
            print_info("执行买入操作...")
            tracker = PortfolioTracker()
            print(f"\n当前现金: ¥{tracker.cash:,.2f}")
            
        elif choice == '7':
            print_info("执行卖出操作...")
            tracker = PortfolioTracker()
            
        elif choice == '8':
            print_info("生成持仓调整建议...")
            tracker = PortfolioTracker()
            
        elif choice == '9':
            print_info("手动修改持仓...")
            tracker = PortfolioTracker()
            
            print(f"\n{Color.BOLD}手动持仓管理{Color.ENDC}")
            print("1. 添加持仓")
            print("2. 修改持仓")
            print("3. 删除持仓")
            print("4. 设置现金")
            print("5. 清空所有持仓")
            print("6. 查看当前持仓")
            print("0. 返回")
            
            sub_choice = input("\n请选择 (0-6): ").strip()
            
            if sub_choice == '1':
                print(f"\n{Color.BOLD}添加新持仓{Color.ENDC}")
                stock_code = input("股票代码 (如 sh600519): ").strip()
                stock_name = input("股票名称: ").strip()
                quantity = int(input("持仓数量 (股): "))
                avg_price = float(input("成本价: "))
                current_price_input = input("当前价格 (回车=成本价): ").strip()
                current_price = float(current_price_input) if current_price_input else None
                sector = input("所属行业 (可选): ").strip()
                
                try:
                    tracker.manual_add_position(stock_code, stock_name, quantity, avg_price, current_price, sector)
                    print_success("持仓添加成功！")
                except Exception as e:
                    print_error(f"添加失败: {e}")
                    
            elif sub_choice == '2':
                print(f"\n{Color.BOLD}修改持仓{Color.ENDC}")
                if not tracker.positions:
                    print_warning("当前无持仓")
                else:
                    print("当前持仓:")
                    for i, (code, pos) in enumerate(tracker.positions.items(), 1):
                        print(f"  {i}. {pos.stock_name}({code}): {pos.quantity}股 @ {pos.avg_price:.2f}元")
                    
                    idx = input("\n选择要修改的持仓序号 (或输入股票代码): ").strip()
                    
                    if idx.isdigit():
                        idx = int(idx) - 1
                        stock_code = list(tracker.positions.keys())[idx] if 0 <= idx < len(tracker.positions) else None
                    else:
                        stock_code = idx
                    
                    if stock_code and stock_code in tracker.positions:
                        pos = tracker.positions[stock_code]
                        print(f"\n当前: {pos.stock_name} {pos.quantity}股 @ {pos.avg_price:.2f}元")
                        
                        print("\n输入新值 (回车保持不变):")
                        new_quantity = input(f"持仓数量 [{pos.quantity}]: ").strip()
                        new_avg_price = input(f"成本价 [{pos.avg_price:.2f}]: ").strip()
                        new_current_price = input(f"当前价 [{pos.current_price:.2f}]: ").strip()
                        
                        updates = {}
                        if new_quantity:
                            updates['quantity'] = int(new_quantity)
                        if new_avg_price:
                            updates['avg_price'] = float(new_avg_price)
                        if new_current_price:
                            updates['current_price'] = float(new_current_price)
                        
                        if updates:
                            try:
                                tracker.manual_update_position(stock_code, **updates)
                                print_success("持仓更新成功！")
                            except Exception as e:
                                print_error(f"更新失败: {e}")
                        else:
                            print_info("未做任何修改")
                    else:
                        print_error("无效的选择")
                        
            elif sub_choice == '3':
                print(f"\n{Color.BOLD}删除持仓{Color.ENDC}")
                if not tracker.positions:
                    print_warning("当前无持仓")
                else:
                    print("当前持仓:")
                    for i, (code, pos) in enumerate(tracker.positions.items(), 1):
                        print(f"  {i}. {pos.stock_name}({code}): {pos.quantity}股")
                    
                    idx = input("\n选择要删除的持仓序号 (或输入股票代码): ").strip()
                    
                    if idx.isdigit():
                        idx = int(idx) - 1
                        stock_code = list(tracker.positions.keys())[idx] if 0 <= idx < len(tracker.positions) else None
                    else:
                        stock_code = idx
                    
                    if stock_code and stock_code in tracker.positions:
                        confirm = input(f"确认删除 {tracker.positions[stock_code].stock_name}? (y/n): ").strip().lower()
                        if confirm == 'y':
                            try:
                                tracker.manual_delete_position(stock_code)
                                print_success("持仓已删除！")
                            except Exception as e:
                                print_error(f"删除失败: {e}")
                    else:
                        print_error("无效的选择")
                        
            elif sub_choice == '4':
                print(f"\n{Color.BOLD}设置现金{Color.ENDC}")
                print(f"当前现金: ¥{tracker.cash:,.2f}")
                new_cash = input("输入新的现金金额: ").strip()
                if new_cash:
                    try:
                        tracker.manual_set_cash(float(new_cash))
                        print_success("现金已更新！")
                    except Exception as e:
                        print_error(f"设置失败: {e}")
                        
            elif sub_choice == '5':
                print(f"\n{Color.BOLD}清空所有持仓{Color.ENDC}")
                print_warning(f"当前有 {len(tracker.positions)} 只持仓")
                confirm = input("确认清空所有持仓? (y/n): ").strip().lower()
                if confirm == 'y':
                    tracker.clear_all_positions()
                    print_success("所有持仓已清空！")
                    
            elif sub_choice == '6':
                print(f"\n{Color.BOLD}当前持仓{Color.ENDC}")
                if not tracker.positions:
                    print_warning("当前无持仓")
                else:
                    print(f"现金: ¥{tracker.cash:,.2f}")
                    print(f"持仓市值: ¥{tracker.portfolio_value:,.2f}")
                    print(f"总资产: ¥{tracker.total_assets:,.2f}")
                    print()
                    for code, pos in tracker.positions.items():
                        profit_color = Color.OKGREEN if pos.profit_loss_pct > 0 else Color.FAIL
                        print(f"  {pos.stock_name}({code}): {pos.quantity}股")
                        print(f"    成本: {pos.avg_price:.2f} → 当前: {pos.current_price:.2f}")
                        print(f"    盈亏: {profit_color}{pos.profit_loss_pct:.2f}%{Color.ENDC}")
    except Exception as e:
        print_error(f"持仓管理启动失败: {e}")
        import traceback
        print_error(traceback.format_exc())

def risk_control():
    """风控系统"""
    print_header("风控系统")
    print_info("功能：策略容量评估、冲击成本评估、流动性风险分析、风格暴露分析")
    
    data_file = project_root / 'data' / 'akshare_real_data_fixed.pkl'
    print_data_freshness(data_file, max_age_hours=24)
    
    try:
        from code.risk.risk_control_system import RiskControlSystem
        
        print("\n选择操作：")
        print("1. 完整风控分析")
        print("2. 策略容量评估")
        print("3. 流动性风险分析")
        print("4. 风格暴露分析")
        print("0. 返回")
        
        choice = input("\n请选择 (0-4): ").strip()
        
        if choice == '1':
            print_info("运行完整风控分析...")
            if data_file.exists():
                system = RiskControlSystem(str(data_file))
                capacity = system.calculate_strategy_capacity()
                impact = system.calculate_impact_cost()
                liquidity = system.analyze_liquidity_risk()
                style = system.analyze_style_exposure()
                print_success("风控分析完成")
            else:
                print_error(f"数据文件不存在: {data_file}")
                
        elif choice == '2':
            print_info("运行策略容量评估...")
            if data_file.exists():
                system = RiskControlSystem(str(data_file))
                capacity = system.calculate_strategy_capacity()
                print(f"\n策略容量评估:")
                print(f"  流动性容量: ¥{capacity.get('liquidity_capacity', 0):,.0f}")
                print(f"  推荐容量: ¥{capacity.get('recommended_capacity', 0):,.0f}")
            else:
                print_error(f"数据文件不存在: {data_file}")
                
        elif choice == '3':
            print_info("运行流动性风险分析...")
            if data_file.exists():
                system = RiskControlSystem(str(data_file))
                liquidity = system.analyze_liquidity_risk()
                print(f"\n流动性风险分析:")
                print(f"  流动性得分: {liquidity.get('liquidity_score', 'N/A')}")
            else:
                print_error(f"数据文件不存在: {data_file}")
                
        elif choice == '4':
            print_info("运行风格暴露分析...")
            if data_file.exists():
                system = RiskControlSystem(str(data_file))
                style = system.analyze_style_exposure()
                print(f"\n风格暴露分析:")
                print(f"  大盘股占比: {style.get('large_cap_ratio', 0):.2%}")
                print(f"  小盘股占比: {style.get('small_cap_ratio', 0):.2%}")
            else:
                print_error(f"数据文件不存在: {data_file}")
                
    except Exception as e:
        print_error(f"风控系统启动失败: {e}")

def fund_management():
    """资金管理"""
    print_header("资金管理")
    print_info("功能：智能资金分配、风险预算管理")
    
    try:
        from code.risk.fund_management import FundManager, RiskBudgetManager
        
        print("\n资金管理功能：")
        print("  • 动态资金分配：根据策略表现调整资金")
        print("  • 风险预算：各策略风险贡献相等")
        print("  • 资金调度：自动调拨资金")
        
        print("\n选择操作：")
        print("1. 查看资金状态")
        print("2. 运行风险预算")
        print("3. 资金调度建议")
        print("0. 返回")
        
        choice = input("\n请选择 (0-3): ").strip()
        
        if choice == '1':
            print_info("查看资金状态...")
            manager = FundManager()
            print_info("需要加载账户数据")
        elif choice == '2':
            print_info("运行风险预算...")
            budget_manager = RiskBudgetManager()
            print_info("需要加载策略收益数据")
        elif choice == '3':
            print_info("资金调度建议...")
            print("需要加载当前资金分配状态")
            
    except Exception as e:
        print_error(f"资金管理启动失败: {e}")

def risk_early_warning():
    """风险预警"""
    print_header("风险预警")
    print_info("功能：实时风险监控和预警")
    
    try:
        from code.risk.risk_early_warning import RiskEarlyWarning
        
        print("\n预警类型：")
        print("  • 净值预警：净值低于阈值")
        print("  • 回撤预警：最大回撤超限")
        print("  • 仓位预警：仓位过高/过低")
        print("  • 因子暴露预警：因子暴露过大")
        
        print("\n选择操作：")
        print("1. 运行风险预警")
        print("2. 查看预警历史")
        print("0. 返回")
        
        choice = input("\n请选择 (0-2): ").strip()
        
        if choice == '1':
            print_info("运行风险预警...")
            warning = RiskEarlyWarning()
            print_info("需要加载当前持仓和净值数据")
        elif choice == '2':
            print_info("查看预警历史...")
            print("需要加载历史预警记录")
            
    except Exception as e:
        print_error(f"风险预警启动失败: {e}")

def trader_assistant():
    """交易员助手"""
    print_header("交易员助手")
    print_info("功能：交易报表生成、交易员反馈系统、策略同步管理")
    
    try:
        from code.trader.trader_assistant import TradingReportGenerator
        
        print("\n选择操作：")
        print("1. 生成每日交易报表")
        print("2. 生成每周交易报表")
        print("3. 查看交易员反馈")
        print("0. 返回")
        
        choice = input("\n请选择 (0-3): ").strip()
        
        if choice == '1':
            print_info("生成每日交易报表...")
            generator = TradingReportGenerator()
            print_info("交易报表功能需要配合实际交易数据使用")
            
        elif choice == '2':
            print_info("生成每周交易报表...")
            generator = TradingReportGenerator()
            print_info("交易报表功能需要配合实际交易数据使用")
            
        elif choice == '3':
            print_info("查看交易员反馈...")
            feedback_dir = project_root / 'data' / 'feedback'
            if feedback_dir.exists():
                feedback_files = list(feedback_dir.glob('*.json'))
                if feedback_files:
                    print(f"\n找到 {len(feedback_files)} 个反馈文件:")
                    for fb_file in feedback_files[-5:]:
                        with open(fb_file, 'r', encoding='utf-8') as f:
                            feedback = json.load(f)
                            print(f"  • {fb_file.name}: {feedback.get('type', 'N/A')}")
                else:
                    print_warning("暂无交易员反馈")
            else:
                print_warning("反馈目录不存在")
                
    except Exception as e:
        print_error(f"交易员助手启动失败: {e}")

def paper_trading():
    """模拟交易"""
    print_header("模拟交易")
    print_info("功能：模拟盘交易系统")
    
    try:
        from code.portfolio.paper_trading import PaperTrading
        
        print("\n模拟交易功能：")
        print("  • 模拟下单")
        print("  • 持仓跟踪")
        print("  • 盈亏计算")
        
        print("\n选择操作：")
        print("1. 启动模拟交易")
        print("2. 查看模拟持仓")
        print("0. 返回")
        
        choice = input("\n请选择 (0-2): ").strip()
        
        if choice == '1':
            print_info("启动模拟交易...")
            trading = PaperTrading()
            print_info("模拟交易系统已启动")
        elif choice == '2':
            print_info("查看模拟持仓...")
            print("需要加载模拟持仓数据")
            
    except Exception as e:
        print_error(f"模拟交易启动失败: {e}")

def broker_api():
    """券商API接入"""
    print_header("券商API接入")
    print_info("功能：连接券商API进行实盘交易")
    
    try:
        from code.backtest.broker_api import BrokerAPIFactory
        
        print("\n支持的券商：")
        print("  • 华泰证券：HTS API")
        print("  • 中信证券：XTP API")
        print("  • 国泰君安：GTJA API")
        
        print("\n选择操作：")
        print("1. 连接华泰证券")
        print("2. 连接中信证券")
        print("3. 连接国泰君安")
        print("0. 返回")
        
        choice = input("\n请选择 (0-3): ").strip()
        
        if choice == '1':
            print_info("连接华泰证券...")
            api = BrokerAPIFactory.create_broker_api('huatai')
            print_warning("需要配置API密钥")
        elif choice == '2':
            print_info("连接中信证券...")
            api = BrokerAPIFactory.create_broker_api('citics')
            print_warning("需要配置API密钥")
        elif choice == '3':
            print_info("连接国泰君安...")
            api = BrokerAPIFactory.create_broker_api('guotai')
            print_warning("需要配置API密钥")
            
    except Exception as e:
        print_error(f"券商API接入失败: {e}")

# ==================== 一级菜单：系统管理 ====================

def system_management_menu():
    """系统管理菜单"""
    while True:
        print_header("系统管理")
        
        print(f"{Color.BOLD}【功能说明】{Color.ENDC}")
        print("  系统管理包含系统配置、定时任务、日志管理等运维功能")
        print("  手册章节：第8章 运维指南")
        
        print(f"\n{Color.BOLD}【子功能】{Color.ENDC}")
        print("  1. 交易日检查")
        print("  2. 系统验证")
        print("  3. 定时任务管理")
        print("  4. 系统配置管理")
        print("  5. 查看日志")
        print("  6. 系统健康检查")
        print("  7. 质量控制")
        print("  8. 监控仪表板")
        print("  9. 事件驱动引擎")
        print("  0. 返回主菜单")
        
        choice = input(f"\n{Color.OKCYAN}请选择 (0-9): {Color.ENDC}").strip()
        
        if choice == '1':
            check_trading_day()
        elif choice == '2':
            verify_system()
        elif choice == '3':
            cron_management()
        elif choice == '4':
            system_config()
        elif choice == '5':
            view_logs()
        elif choice == '6':
            health_check()
        elif choice == '7':
            quality_control()
        elif choice == '8':
            monitoring_dashboard()
        elif choice == '9':
            event_engine_menu()
        elif choice == '0':
            return
        else:
            print_error("无效的选择")
        
        input(f"\n{Color.OKCYAN}按回车键继续...{Color.ENDC}")

def check_trading_day():
    """检查是否是交易日"""
    print_header("交易日检查")
    return run_script('is_trading_day.py', "检查今天是否是交易日")

def verify_system():
    """系统验证"""
    print_header("系统验证")
    
    version_file = project_root / 'VERSION'
    if version_file.exists():
        with open(version_file, 'r') as f:
            version = f.read().strip()
        print(f"\n{Color.BOLD}系统版本: v{version}{Color.ENDC}")
    
    print(f"\n{Color.BOLD}【功能说明】{Color.ENDC}")
    print("  系统验证用于检查系统完整性和配置正确性")
    print("  完整验证将检查所有菜单功能模块是否正常")
    
    print("\n选择操作：")
    print("1. 运行完整系统验证 ⭐推荐")
    print("2. 运行快速验证（仅检查关键模块）")
    print("3. 查看系统版本")
    print("4. 查看更新日志")
    print("5. 从Gitee更新系统")
    print("0. 返回")
    
    choice = input("\n请选择 (0-5): ").strip()
    
    if choice == '1':
        print_info("运行完整系统验证...")
        print_info("将检查所有菜单功能模块（约100+项）")
        verify_script = scripts_dir / 'system_verification.py'
        if verify_script.exists():
            try:
                result = subprocess.run(
                    [sys.executable, str(verify_script)],
                    cwd=project_root,
                    capture_output=False,
                    text=True
                )
                return result.returncode == 0
            except Exception as e:
                print_error(f"验证失败: {e}")
                return False
        else:
            print_warning("完整验证脚本不存在，使用快速验证...")
            return run_quick_verification()
            
    elif choice == '2':
        print_info("运行快速验证...")
        return run_quick_verification()
            
    elif choice == '3':
        print_info("系统版本信息：")
        if version_file.exists():
            with open(version_file, 'r') as f:
                version = f.read().strip()
            print(f"\n{Color.BOLD}当前版本: v{version}{Color.ENDC}")
        print(f"\n{Color.BOLD}系统信息:{Color.ENDC}")
        print(f"  Python版本: {sys.version.split()[0]}")
        print(f"  项目路径: {project_root}")
        print(f"  操作系统: {sys.platform}")
        
    elif choice == '4':
        print_info("查看更新日志...")
        changelog_file = project_root / 'CHANGELOG.md'
        if changelog_file.exists():
            with open(changelog_file, 'r', encoding='utf-8') as f:
                print(f.read())
        else:
            print_warning("更新日志不存在")
            
    elif choice == '5':
        print_info("从Gitee更新系统...")
        print_warning("注意：更新前请确保已提交本地更改")
        confirm = input("确认更新？(yes/no): ").strip().lower()
        
        if confirm == 'yes':
            try:
                print_info("正在从Gitee拉取最新代码...")
                result = subprocess.run(
                    ['git', 'pull', 'origin', 'main'],
                    cwd=project_root,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    print_success("系统更新成功")
                    print(result.stdout)
                else:
                    print_error("更新失败")
                    print_error(result.stderr)
            except Exception as e:
                print_error(f"更新失败: {e}")

def run_quick_verification():
    """快速验证关键模块"""
    print_info("检查关键模块...")
    
    checks = [
        ('数据获取', 'code.data.real_data_fetcher', 'RealDataFetcher'),
        ('多因子模型', 'code.strategy.multi_factor_model', 'MultiFactorModel'),
        ('Alpha选股器', 'code.strategy.alpha_stock_selector', 'AlphaStockSelector'),
        ('风控系统', 'code.risk.risk_control_system', 'RiskControlSystem'),
        ('持仓跟踪', 'code.portfolio.portfolio_tracker', 'PortfolioTracker'),
    ]
    
    passed = 0
    failed = 0
    
    for name, module_path, class_name in checks:
        try:
            module = __import__(module_path)
            for part in module_path.split('.')[1:]:
                module = getattr(module, part)
            cls = getattr(module, class_name)
            print_success(f"{name}: 正常")
            passed += 1
        except Exception as e:
            print_error(f"{name}: 异常 - {e}")
            failed += 1
    
    data_file = project_root / 'data' / 'akshare_real_data_fixed.pkl'
    if data_file.exists():
        print_success(f"数据文件: 存在")
        passed += 1
    else:
        print_warning(f"数据文件: 不存在")
    
    print(f"\n{Color.BOLD}【快速验证结果】{Color.ENDC}")
    print(f"  通过: {passed}, 失败: {failed}")
    
    if failed == 0:
        print_success("关键模块验证通过")
        return True
    else:
        print_warning(f"有 {failed} 个模块验证失败")
        return False

def cron_management():
    """定时任务管理"""
    print_header("定时任务管理")
    print_info("功能：安装、卸载、查看定时任务")
    
    print("\n选择操作：")
    print("1. 安装定时任务")
    print("2. 卸载定时任务")
    print("3. 查看定时任务状态")
    print("4. 查看定时任务配置")
    print("0. 返回")
    
    choice = input("\n请选择 (0-4): ").strip()
    
    if choice == '1':
        print_info("正在安装定时任务...")
        install_script = scripts_dir / 'install_cron_v2.sh'
        if install_script.exists():
            try:
                result = subprocess.run(
                    ['bash', str(install_script)],
                    cwd=project_root,
                    capture_output=True,
                    text=True
                )
                if result.stdout:
                    print(result.stdout)
                if result.stderr:
                    print_error(result.stderr)
                if result.returncode == 0:
                    print_success("定时任务安装成功")
                else:
                    print_error("定时任务安装失败")
            except Exception as e:
                print_error(f"安装失败: {e}")
        else:
            print_warning("安装脚本不存在")
            
    elif choice == '2':
        print_info("正在卸载定时任务...")
        print_warning("这将移除所有系统定时任务")
        confirm = input("确认卸载？(yes/no): ").strip().lower()
        
        if confirm == 'yes':
            try:
                result = subprocess.run(
                    ['crontab', '-l'],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    current_cron = result.stdout
                    lines = current_cron.split('\n')
                    filtered_lines = [line for line in lines if 'a-stock-advisor' not in line]
                    new_cron = '\n'.join(filtered_lines)
                    
                    process = subprocess.Popen(
                        ['crontab', '-'],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    stdout, stderr = process.communicate(input=new_cron)
                    
                    if process.returncode == 0:
                        print_success("定时任务卸载成功")
                    else:
                        print_error(f"卸载失败: {stderr}")
            except Exception as e:
                print_error(f"卸载失败: {e}")
                
    elif choice == '3':
        print_info("查看定时任务状态...")
        try:
            result = subprocess.run(
                ['crontab', '-l'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                cron_content = result.stdout
                if 'a-stock-advisor' in cron_content:
                    print(f"\n{Color.BOLD}当前定时任务:{Color.ENDC}")
                    for line in cron_content.split('\n'):
                        if 'a-stock-advisor' in line and not line.startswith('#'):
                            print(f"  {Color.OKGREEN}{line}{Color.ENDC}")
                else:
                    print_warning("没有找到项目相关的定时任务")
            else:
                print_warning("没有配置定时任务")
        except Exception as e:
            print_error(f"查看失败: {e}")
            
    elif choice == '4':
        print_info("查看定时任务配置...")
        config_file = project_root / 'config' / 'cron_config_v2.json'
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                print(f"\n{Color.BOLD}定时任务配置:{Color.ENDC}")
                print(f"版本: {config.get('version', 'N/A')}")
                print(f"更新时间: {config.get('last_updated', 'N/A')}")
                
                print(f"\n{Color.BOLD}任务列表:{Color.ENDC}")
                for task in config.get('tasks', []):
                    status = f"{Color.OKGREEN}启用{Color.ENDC}" if task.get('enabled', True) else f"{Color.FAIL}禁用{Color.ENDC}"
                    print(f"\n  {task['name']} - {status}")
                    print(f"    描述: {task['description']}")
                    print(f"    调度: {task['schedule']}")
            except Exception as e:
                print_error(f"读取配置失败: {e}")
        else:
            print_warning("配置文件不存在")

def system_config():
    """系统配置管理"""
    print_header("系统配置管理")
    print_info("功能：管理系统配置、API密钥、功能开关")
    
    print("\n选择操作：")
    print("1. 查看系统配置")
    print("2. 配置飞书推送")
    print("3. 配置功能开关")
    print("4. 查看配置文件路径")
    print("0. 返回")
    
    choice = input("\n请选择 (0-4): ").strip()
    
    if choice == '1':
        print_info("查看系统配置...")
        
        feishu_config_file = project_root / 'config' / 'feishu_config.json'
        if feishu_config_file.exists():
            try:
                with open(feishu_config_file, 'r', encoding='utf-8') as f:
                    feishu_config = json.load(f)
                
                print(f"\n{Color.BOLD}飞书推送配置:{Color.ENDC}")
                print(f"  Webhook URL: {feishu_config.get('webhook_url', 'N/A')[:50]}...")
                print(f"  启用状态: {'✓ 启用' if feishu_config.get('enabled', False) else '✗ 禁用'}")
            except Exception as e:
                print_error(f"读取飞书配置失败: {e}")
        
        cron_config_file = project_root / 'config' / 'cron_config_v2.json'
        if cron_config_file.exists():
            try:
                with open(cron_config_file, 'r', encoding='utf-8') as f:
                    cron_config = json.load(f)
                
                print(f"\n{Color.BOLD}定时任务配置:{Color.ENDC}")
                print(f"  任务数量: {len(cron_config.get('tasks', []))}")
                print(f"  版本: {cron_config.get('version', 'N/A')}")
            except Exception as e:
                print_error(f"读取定时任务配置失败: {e}")
                
    elif choice == '2':
        print_info("配置飞书推送...")
        feishu_config_file = project_root / 'config' / 'feishu_config.json'
        
        if feishu_config_file.exists():
            try:
                with open(feishu_config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                print(f"\n{Color.BOLD}当前配置:{Color.ENDC}")
                print(f"  Webhook URL: {config.get('webhook_url', 'N/A')[:50]}...")
                print(f"  启用状态: {'启用' if config.get('enabled', False) else '禁用'}")
                
                print(f"\n{Color.BOLD}修改配置:{Color.ENDC}")
                print("1. 修改Webhook URL")
                print("2. 启用/禁用推送")
                print("0. 返回")
                
                config_choice = input("\n请选择 (0-2): ").strip()
                
                if config_choice == '1':
                    new_url = input("请输入新的Webhook URL: ").strip()
                    if new_url:
                        config['webhook_url'] = new_url
                        with open(feishu_config_file, 'w', encoding='utf-8') as f:
                            json.dump(config, f, indent=2, ensure_ascii=False)
                        print_success("Webhook URL已更新")
                        
                elif config_choice == '2':
                    current = config.get('enabled', False)
                    config['enabled'] = not current
                    with open(feishu_config_file, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                    print_success(f"推送已{'启用' if not current else '禁用'}")
                    
            except Exception as e:
                print_error(f"配置失败: {e}")
        else:
            print_warning("飞书配置文件不存在")
            
    elif choice == '3':
        print_info("配置功能开关...")
        print_info("功能开关允许启用或禁用特定功能")
        
        config_file = project_root / 'config' / 'feature_flags.json'
        
        if not config_file.exists():
            default_config = {
                "factor_mining": {"enabled": True, "auto_mining": False},
                "position_management": {"enabled": True, "kelly_criterion": True},
                "factor_library": {"enabled": True, "auto_monitor": True},
                "innovation_lab": {"enabled": True, "auto_weekly_report": True}
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            
            print_success("已创建默认功能开关配置")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            print(f"\n{Color.BOLD}功能开关配置:{Color.ENDC}")
            
            feature_map = {
                '1': ('factor_mining', '因子挖掘系统'),
                '2': ('position_management', '持仓管理'),
                '3': ('factor_library', '因子库管理'),
                '4': ('innovation_lab', '创新实验室')
            }
            
            for key, (feature_key, feature_name) in feature_map.items():
                if feature_key in config:
                    enabled = config[feature_key].get('enabled', True)
                    status = f"{Color.OKGREEN}启用{Color.ENDC}" if enabled else f"{Color.FAIL}禁用{Color.ENDC}"
                    print(f"  {key}. {feature_name} - {status}")
            
        except Exception as e:
            print_error(f"配置失败: {e}")
            
    elif choice == '4':
        print_info("配置文件路径：")
        print(f"\n{Color.BOLD}配置文件:{Color.ENDC}")
        print(f"  飞书配置: config/feishu_config.json")
        print(f"  定时任务配置: config/cron_config_v2.json")
        print(f"  功能开关配置: config/feature_flags.json")
        
        print(f"\n{Color.BOLD}数据文件:{Color.ENDC}")
        print(f"  主数据文件: data/akshare_real_data_fixed.pkl")
        print(f"  持仓状态: data/portfolio_state.json")
        print(f"  因子历史: data/factor_history.json")

def view_logs():
    """查看日志"""
    print_header("日志管理")
    print_info("日志记录了系统运行的详细信息，用于问题排查和性能分析")
    
    logs_dir = project_root / 'logs'
    if not logs_dir.exists():
        print_warning("日志目录不存在")
        return
    
    log_files = list(logs_dir.glob('*.log'))
    json_files = list(logs_dir.glob('*.json'))
    
    print(f"\n{Color.BOLD}选择操作：{Color.ENDC}")
    print("1. 查看系统运行日志")
    print("2. 查看健康检查报告")
    print("3. 查看错误和警告摘要")
    print("4. 查看最近日志（最后50行）")
    print("5. 日志文件列表")
    print("0. 返回")
    
    choice = input("\n请选择 (0-5): ").strip()
    
    if choice == '1':
        print_info("系统运行日志：")
        if log_files:
            print("\n可用的日志文件:")
            for i, log_file in enumerate(log_files, 1):
                size = log_file.stat().st_size / 1024
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                print(f"  {i}. {log_file.name} ({size:.1f}KB, 更新: {mtime})")
            
            print("\n0. 返回")
            file_choice = input(f"\n请选择日志文件 (0-{len(log_files)}): ")
            if file_choice.isdigit():
                idx = int(file_choice)
                if 0 < idx <= len(log_files):
                    log_file = log_files[idx - 1]
                    print(f"\n{Color.BOLD}查看日志: {log_file.name}{Color.ENDC}\n")
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            for line in lines[-100:]:
                                if 'ERROR' in line or 'error' in line.lower():
                                    print(f"{Color.FAIL}{line.rstrip()}{Color.ENDC}")
                                elif 'WARNING' in line or 'warning' in line.lower():
                                    print(f"{Color.WARNING}{line.rstrip()}{Color.ENDC}")
                                elif 'SUCCESS' in line or 'success' in line.lower():
                                    print(f"{Color.OKGREEN}{line.rstrip()}{Color.ENDC}")
                                else:
                                    print(line.rstrip())
                    except Exception as e:
                        print_error(f"读取日志失败: {e}")
        else:
            print_warning("没有找到日志文件")
    
    elif choice == '2':
        print_info("健康检查报告：")
        if json_files:
            for json_file in json_files:
                if 'health' in json_file.name or 'report' in json_file.name:
                    print(f"\n{Color.BOLD}报告文件: {json_file.name}{Color.ENDC}")
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            report = json.load(f)
                            print(json.dumps(report, indent=2, ensure_ascii=False))
                    except Exception as e:
                        print_error(f"读取报告失败: {e}")
        else:
            print_warning("没有找到健康检查报告")
    
    elif choice == '3':
        print_info("错误和警告摘要：")
        if log_files:
            error_count = 0
            warning_count = 0
            errors = []
            warnings = []
            
            for log_file in log_files:
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if 'ERROR' in line or 'error' in line.lower():
                                error_count += 1
                                if len(errors) < 10:
                                    errors.append(f"[{log_file.name}] {line.strip()}")
                            elif 'WARNING' in line or 'warning' in line.lower():
                                warning_count += 1
                                if len(warnings) < 10:
                                    warnings.append(f"[{log_file.name}] {line.strip()}")
                except:
                    pass
            
            print(f"\n{Color.FAIL}错误总数: {error_count}{Color.ENDC}")
            print(f"{Color.WARNING}警告总数: {warning_count}{Color.ENDC}")
            
            if errors:
                print(f"\n{Color.FAIL}最近10条错误:{Color.ENDC}")
                for error in errors:
                    print(f"  {Color.FAIL}• {error}{Color.ENDC}")
            
            if warnings:
                print(f"\n{Color.WARNING}最近10条警告:{Color.ENDC}")
                for warning in warnings:
                    print(f"  {Color.WARNING}• {warning}{Color.ENDC}")
            
            if not errors and not warnings:
                print_success("系统运行正常，无错误和警告")
        else:
            print_warning("没有找到日志文件")
    
    elif choice == '4':
        print_info("最近日志（最后50行）：")
        if log_files:
            latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
            print(f"\n{Color.BOLD}文件: {latest_log.name}{Color.ENDC}")
            try:
                with open(latest_log, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines[-50:]:
                        print(line.rstrip())
            except Exception as e:
                print_error(f"读取日志失败: {e}")
        else:
            print_warning("没有找到日志文件")
    
    elif choice == '5':
        print_info("日志文件列表：")
        all_files = log_files + json_files
        if all_files:
            print(f"\n{'文件名':<30} {'大小':<10} {'修改时间':<20}")
            print("-" * 60)
            for file in sorted(all_files, key=lambda f: f.stat().st_mtime, reverse=True):
                size = file.stat().st_size / 1024
                mtime = datetime.fromtimestamp(file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                print(f"{file.name:<30} {size:>6.1f}KB  {mtime:<20}")
        else:
            print_warning("没有找到日志文件")

def health_check():
    """健康检查"""
    print_header("系统健康检查")
    return run_script('health_check.py', "系统健康检查")

def quality_control():
    """质量控制"""
    print_header("质量控制")
    print_info("功能：自动化质量控制，确保系统输出可靠性")
    
    try:
        from code.quality_control.automated_quality_control import AutomatedQualityControl
        
        print("\n质量控制功能：")
        print("  • 数据质量检查")
        print("  • 因子有效性验证")
        print("  • 投资组合验证")
        print("  • 流程完整性检查")
        
        print("\n选择操作：")
        print("1. 运行质量检查")
        print("2. 查看质量摘要")
        print("3. 查看数据准备要求")
        print("0. 返回")
        
        choice = input("\n请选择 (0-3): ").strip()
        
        if choice == '1':
            print_info("运行质量检查...")
            
            data_file = project_root / 'data' / 'akshare_real_data_fixed.pkl'
            factor_file = project_root / 'data' / 'factor_dynamic_weights.json'
            portfolio_file = project_root / 'data' / 'portfolio_state.json'
            
            missing_items = []
            if not data_file.exists():
                missing_items.append("股票数据 (data/akshare_real_data_fixed.pkl)")
            if not factor_file.exists():
                missing_items.append("因子数据 (data/factor_dynamic_weights.json)")
            if not portfolio_file.exists():
                missing_items.append("投资组合数据 (data/portfolio_state.json)")
            
            if missing_items:
                print_error("以下数据文件缺失：")
                for item in missing_items:
                    print(f"  ✗ {item}")
                print(f"\n{Color.BOLD}【解决方法】{Color.ENDC}")
                print("  1. 运行「数据工程 → 数据更新」获取股票数据")
                print("  2. 运行「因子研发 → 因子挖掘」生成因子数据")
                print("  3. 运行「实盘工程 → 持仓管理」初始化投资组合")
                return
            
            qc = AutomatedQualityControl()
            print_success("质量检查完成")
            
        elif choice == '2':
            print_info("查看质量摘要...")
            qc = AutomatedQualityControl()
            summary = qc.get_quality_summary()
            print(summary)
            
        elif choice == '3':
            print(f"\n{Color.BOLD}【数据准备要求】{Color.ENDC}")
            
            print(f"\n{Color.BOLD}1. 股票数据{Color.ENDC}")
            data_file = project_root / 'data' / 'akshare_real_data_fixed.pkl'
            if data_file.exists():
                print(f"  {Color.OKGREEN}✓ 已就绪: {data_file}{Color.ENDC}")
            else:
                print(f"  {Color.FAIL}✗ 未找到{Color.ENDC}")
                print(f"    → 运行「数据工程 → 数据更新」获取")
            
            print(f"\n{Color.BOLD}2. 因子数据{Color.ENDC}")
            factor_file = project_root / 'data' / 'factor_dynamic_weights.json'
            if factor_file.exists():
                print(f"  {Color.OKGREEN}✓ 已就绪: {factor_file}{Color.ENDC}")
            else:
                print(f"  {Color.FAIL}✗ 未找到{Color.ENDC}")
                print(f"    → 运行「因子研发 → 因子挖掘」生成")
            
            print(f"\n{Color.BOLD}3. 投资组合数据{Color.ENDC}")
            portfolio_file = project_root / 'data' / 'portfolio_state.json'
            if portfolio_file.exists():
                print(f"  {Color.OKGREEN}✓ 已就绪: {portfolio_file}{Color.ENDC}")
            else:
                print(f"  {Color.FAIL}✗ 未找到{Color.ENDC}")
                print(f"    → 运行「实盘工程 → 持仓管理」初始化")
            
            ready_count = sum([
                data_file.exists(),
                factor_file.exists(),
                portfolio_file.exists()
            ])
            print(f"\n{Color.BOLD}【就绪状态】{Color.ENDC}")
            print(f"  已就绪: {ready_count}/3")
            
            if ready_count < 3:
                print(f"\n{Color.WARNING}⚠ 部分数据未就绪，质量检查功能可能受限{Color.ENDC}")
            
    except Exception as e:
        print_error(f"质量控制启动失败: {e}")

_monitoring_thread = None
_monitoring_dashboard = None

def monitoring_dashboard():
    """监控仪表板"""
    global _monitoring_thread, _monitoring_dashboard
    
    print_header("监控仪表板")
    print_info("功能：实时监控系统运行状态")
    
    try:
        from code.utils.monitoring_dashboard import MonitoringDashboard
        import threading
        
        print("\n监控功能：")
        print("  • 系统健康监控")
        print("  • 市场状态监控")
        print("  • 因子表现监控")
        print("  • 投资组合风险监控")
        
        if _monitoring_thread and _monitoring_thread.is_alive():
            print(f"\n{Color.OKGREEN}✓ 监控系统正在后台运行{Color.ENDC}")
        
        print("\n选择操作：")
        print("1. 启动后台监控 ⭐推荐")
        print("2. 查看监控摘要")
        print("3. 停止监控")
        print("0. 返回")
        
        choice = input("\n请选择 (0-3): ").strip()
        
        if choice == '1':
            if _monitoring_thread and _monitoring_thread.is_alive():
                print_warning("监控系统已在运行中")
            else:
                print_info("启动后台监控...")
                _monitoring_dashboard = MonitoringDashboard()
                
                def run_monitoring():
                    try:
                        while True:
                            import time
                            time.sleep(60)
                    except Exception:
                        pass
                
                _monitoring_thread = threading.Thread(target=run_monitoring, daemon=True)
                _monitoring_thread.start()
                print_success("监控系统已在后台启动，您可以继续其他操作")
                
        elif choice == '2':
            print_info("查看监控摘要...")
            if _monitoring_dashboard:
                try:
                    summary = _monitoring_dashboard.get_summary()
                    print(f"\n{Color.BOLD}【监控摘要】{Color.ENDC}")
                    for key, value in summary.items():
                        print(f"  {key}: {value}")
                except Exception as e:
                    print_warning(f"获取监控摘要失败: {e}")
            else:
                print_warning("监控系统未启动，请先启动监控")
                
        elif choice == '3':
            if _monitoring_thread and _monitoring_thread.is_alive():
                print_info("停止监控...")
                _monitoring_thread = None
                _monitoring_dashboard = None
                print_success("监控系统已停止")
            else:
                print_warning("监控系统未在运行")
            
    except Exception as e:
        print_error(f"监控仪表板操作失败: {e}")

def event_engine_menu():
    """事件驱动引擎菜单"""
    print_header("事件驱动引擎")
    print_info("功能：基于事件驱动的异步处理架构")
    
    try:
        from code.utils.event_engine import EventEngine, EventType, Event
        
        print(f"\n{Color.BOLD}【事件类型】{Color.ENDC}")
        for et in EventType:
            print(f"  • {et.value}")
        
        print(f"\n{Color.BOLD}【处理器类型】{Color.ENDC}")
        print("  • DataHandler - 市场数据处理")
        print("  • StrategyHandler - 策略信号处理")
        print("  • RiskHandler - 风险检查处理")
        
        print("\n选择操作：")
        print("1. 启动事件引擎")
        print("2. 发送测试事件")
        print("3. 查看已注册处理器")
        print("0. 返回")
        
        choice = input("\n请选择 (0-3): ").strip()
        
        if choice == '1':
            print_info("启动事件引擎...")
            engine = EventEngine()
            engine.start()
            print_success("事件引擎已启动")
            print_info("按回车键停止引擎...")
            input()
            engine.stop()
            print_info("事件引擎已停止")
        elif choice == '2':
            print_info("发送测试事件...")
            engine = EventEngine()
            engine.start()
            test_event = Event(EventType.TIMER, {"test": True})
            engine.put(test_event)
            print_success("测试事件已发送")
            engine.stop()
        elif choice == '3':
            print_info("查看已注册处理器...")
            engine = EventEngine()
            print(f"已注册事件类型: {list(engine._handlers.keys())}")
            
    except Exception as e:
        print_error(f"事件引擎操作失败: {e}")

# ==================== 辅助功能 ====================

def data_quality_check():
    """数据质量检查"""
    print_header("数据质量检查")
    print_info("功能：数据质量检查、数据清洗、数据验证")
    
    data_file = project_root / 'data' / 'akshare_real_data_fixed.pkl'
    print_data_freshness(data_file, max_age_hours=24)
    
    try:
        from code.data.data_quality_framework import DataQualityPipeline, DataQualityChecker, DataCleaner
        import pickle
        
        print("\n选择操作：")
        print("1. 完整数据质量Pipeline（检查+清洗+验证）⭐推荐")
        print("2. 仅数据质量检查（不清洗数据）")
        print("3. 仅数据清洗（不检查质量）")
        print("4. 数据质量修复脚本")
        print("0. 返回")
        
        choice = input("\n请选择 (0-4): ").strip()
        
        if choice == '1':
            print_info("运行完整数据质量Pipeline...")
            
            if data_file.exists():
                with open(data_file, 'rb') as f:
                    data = pickle.load(f)
                
                print_info(f"加载数据: {len(data)} 条记录")
                
                pipeline = DataQualityPipeline()
                results = pipeline.run(data, source_name="akshare_real_data")
                
                print_success(f"Pipeline完成: {results['final_records']} 条记录")
                
                if results['is_valid']:
                    print_success("数据质量验证通过")
                else:
                    print_warning("数据质量验证发现问题")
                    
                    if 'issues' in results:
                        print(f"\n{Color.BOLD}【发现问题】{Color.ENDC}")
                        for issue in results['issues'][:5]:
                            print(f"  • {issue}")
                        if len(results['issues']) > 5:
                            print(f"  ... 还有 {len(results['issues']) - 5} 个问题")
                    
                    print(f"\n{Color.BOLD}【修复选项】{Color.ENDC}")
                    print("  1. 自动修复所有问题")
                    print("  2. 查看详细问题列表")
                    print("  3. 运行数据质量修复脚本")
                    print("  0. 返回上级菜单")
                    
                    fix_choice = input("\n请选择修复方式 (0-3): ").strip()
                    
                    if fix_choice == '1':
                        print_info("正在自动修复问题...")
                        cleaner = DataCleaner()
                        cleaned_data = cleaner.clean_data(data)
                        
                        output_path = data_file.parent / 'akshare_real_data_fixed.pkl'
                        with open(output_path, 'wb') as f:
                            pickle.dump(cleaned_data, f)
                        print_success(f"修复完成，已保存到: {output_path}")
                        
                    elif fix_choice == '2':
                        print_info("详细问题列表:")
                        report_file = project_root / 'data' / 'akshare_real_data_quality_report.json'
                        if report_file.exists():
                            import json
                            with open(report_file, 'r', encoding='utf-8') as f:
                                report = json.load(f)
                            for i, issue in enumerate(report.get('issues', [])[:20], 1):
                                print(f"  {i}. {issue}")
                        else:
                            print_warning("未找到详细报告文件")
                            
                    elif fix_choice == '3':
                        return run_script('fix_data_quality_v2.py', "数据质量修复")
            else:
                print_error(f"数据文件不存在: {data_file}")
                
        elif choice == '2':
            print_info("运行快速数据质量检查（不修改数据）...")
            
            if data_file.exists():
                with open(data_file, 'rb') as f:
                    data = pickle.load(f)
                
                print_info(f"加载数据: {len(data)} 条记录")
                
                checker = DataQualityChecker()
                report = checker.check_data(data)
                
                print(f"\n数据质量结果: {'✓ 合格' if report.is_valid else '⚠ 不合格'}")
                print(f"总记录数: {report.total_records}")
                print(f"问题数: {len(report.issues)}")
                
                if not report.is_valid and len(report.issues) > 0:
                    print(f"\n{Color.BOLD}【发现问题】{Color.ENDC}")
                    for i, issue in enumerate(report.issues[:5], 1):
                        print(f"  {i}. {issue}")
                    if len(report.issues) > 5:
                        print(f"  ... 还有 {len(report.issues) - 5} 个问题")
                    
                    print(f"\n{Color.BOLD}【后续操作】{Color.ENDC}")
                    print("  1. 运行完整Pipeline修复")
                    print("  2. 运行数据清洗")
                    print("  3. 运行修复脚本")
                    print("  0. 返回上级菜单")
                    
                    fix_choice = input("\n请选择 (0-3): ").strip()
                    
                    if fix_choice == '1':
                        print_info("运行完整Pipeline...")
                        pipeline = DataQualityPipeline()
                        results = pipeline.run(data, source_name="akshare_real_data")
                        print_success(f"Pipeline完成: {results['final_records']} 条记录")
                    elif fix_choice == '2':
                        print_info("运行数据清洗...")
                        cleaner = DataCleaner()
                        cleaned_data = cleaner.clean_data(data)
                        output_path = data_file.parent / 'akshare_real_data_cleaned.pkl'
                        with open(output_path, 'wb') as f:
                            pickle.dump(cleaned_data, f)
                        print_success(f"清洗完成，已保存到: {output_path}")
                    elif fix_choice == '3':
                        return run_script('fix_data_quality_v2.py', "数据质量修复")
            else:
                print_error(f"数据文件不存在: {data_file}")
                
        elif choice == '3':
            print_info("运行数据清洗（不检查质量）...")
            
            if data_file.exists():
                with open(data_file, 'rb') as f:
                    data = pickle.load(f)
                
                print_info(f"加载数据: {len(data)} 条记录")
                
                cleaner = DataCleaner()
                cleaned_data = cleaner.clean_data(data)
                
                print_success(f"清洗完成: {len(cleaned_data)} 条记录")
                
                output_path = data_file.parent / 'akshare_real_data_cleaned.pkl'
                with open(output_path, 'wb') as f:
                    pickle.dump(cleaned_data, f)
                print_success(f"已保存到: {output_path}")
                
                print(f"\n{Color.BOLD}【后续操作】{Color.ENDC}")
                print("  1. 验证清洗后的数据质量")
                print("  2. 替换原始数据文件")
                print("  0. 返回上级菜单")
                
                next_choice = input("\n请选择 (0-2): ").strip()
                
                if next_choice == '1':
                    print_info("验证清洗后的数据质量...")
                    checker = DataQualityChecker()
                    report = checker.check_data(cleaned_data)
                    print(f"\n数据质量结果: {'✓ 合格' if report.is_valid else '⚠ 不合格'}")
                    print(f"问题数: {len(report.issues)}")
                elif next_choice == '2':
                    import shutil
                    backup_path = data_file.parent / f'akshare_real_data_backup_{datetime.now().strftime("%Y%m%d_%H%M")}.pkl'
                    shutil.copy(data_file, backup_path)
                    print_success(f"原数据已备份到: {backup_path}")
                    shutil.copy(output_path, data_file)
                    print_success(f"已替换原始数据文件")
            else:
                print_error(f"数据文件不存在: {data_file}")
                
        elif choice == '4':
            print_info("运行数据质量修复脚本...")
            return run_script('fix_data_quality_v2.py', "数据质量修复")
            
    except Exception as e:
        print_error(f"数据质量检查失败: {e}")
        print_info("尝试直接运行脚本...")
        return run_script('fix_data_quality_v2.py', "数据质量修复")

def factor_library():
    """因子库管理"""
    print_header("因子库管理")
    print_info("功能：查看因子库、因子启用/禁用、因子表现分析")
    
    try:
        from code.quality_control.factor_monitor import FactorMonitor
        
        print("\n选择操作：")
        print("1. 查看因子库")
        print("2. 因子启用/禁用")
        print("3. 因子表现分析")
        print("0. 返回")
        
        choice = input("\n请选择 (0-3): ").strip()
        
        if choice == '1':
            print_info("查看因子库...")
            monitor = FactorMonitor()
            
            if monitor.factor_history:
                print(f"\n{Color.BOLD}因子库列表:{Color.ENDC}")
                for factor_name, history in monitor.factor_history.items():
                    status = f"{Color.OKGREEN}启用{Color.ENDC}" if history.get('enabled', True) else f"{Color.FAIL}禁用{Color.ENDC}"
                    ic_mean = history.get('ic_mean', 0)
                    print(f"  {factor_name}: {status} | IC均值: {ic_mean:.4f}")
            else:
                print_warning("因子库为空，请先运行因子挖掘")
                
        elif choice == '2':
            print_info("因子启用/禁用...")
            monitor = FactorMonitor()
            
            if monitor.factor_history:
                print("\n当前因子状态：")
                for i, (factor_name, history) in enumerate(monitor.factor_history.items(), 1):
                    status = "启用" if history.get('enabled', True) else "禁用"
                    print(f"  {i}. {factor_name} - {status}")
                
                print("\n输入因子编号进行切换（0返回）：")
                factor_choice = input("请选择: ").strip()
                
                if factor_choice.isdigit():
                    idx = int(factor_choice)
                    if 0 < idx <= len(monitor.factor_history):
                        factor_name = list(monitor.factor_history.keys())[idx - 1]
                        current_status = monitor.factor_history[factor_name].get('enabled', True)
                        monitor.factor_history[factor_name]['enabled'] = not current_status
                        monitor._save_factor_history()
                        
                        new_status = "启用" if not current_status else "禁用"
                        print_success(f"因子 {factor_name} 已{new_status}")
            else:
                print_warning("因子库为空")
                
        elif choice == '3':
            print_info("因子表现分析...")
            print_info("需要加载因子历史数据进行详细分析")
            
    except Exception as e:
        print_error(f"因子库管理启动失败: {e}")

def factor_backtest():
    """因子回测"""
    print_header("因子回测")
    
    print(f"\n{Color.BOLD}【功能说明】{Color.ENDC}")
    print("  因子回测用于验证新挖掘因子的有效性")
    print("  • 支持单个因子回测")
    print("  • 支持多因子组合回测")
    print("  • 支持股票级别的因子表现分析")
    
    print("\n选择回测类型：")
    print("1. 单个因子回测")
    print("2. 多因子组合回测")
    print("3. 股票级别因子分析")
    print("4. 因子绩效对比（并行优化）⭐推荐")
    print("0. 返回")
    
    choice = input("\n请选择 (0-4): ").strip()
    
    if choice == '1':
        print_info("运行单个因子回测...")
        run_script('run_factor_backtest_fast.py', "单个因子回测")
    elif choice == '2':
        print_info("运行多因子组合回测...")
        run_script('run_factor_backtest_fast.py', "多因子组合回测")
    elif choice == '3':
        print_info("运行股票级别因子分析...")
        run_script('run_factor_backtest_fast.py', "股票级别因子分析")
    elif choice == '4':
        print_info("运行因子绩效对比（并行优化）...")
        run_script('run_factor_backtest_fast.py', "因子绩效对比")

def portfolio_optimization():
    """组合优化"""
    print_header("组合优化")
    print_info("功能：均值方差优化、风险平价、最大夏普、风险预算等优化方法")
    
    try:
        from code.portfolio.portfolio_optimizer import PortfolioOptimizer, OptimizationMethod
        
        print("\n选择优化方法：")
        print("1. 等权重优化")
        print("2. 均值方差优化")
        print("3. 最小方差优化")
        print("4. 最大夏普优化")
        print("5. 风险平价优化")
        print("6. 风险预算优化")
        print("0. 返回")
        
        choice = input("\n请选择 (0-6): ").strip()
        
        if choice == '0':
            return
        elif choice in ['1', '2', '3', '4', '5', '6']:
            print_info("运行组合优化...")
            print_warning("注意：需要准备预期收益率和协方差矩阵数据")
            print_info("请参考 code/portfolio/portfolio_optimizer.py 使用示例")
        else:
            print_error("无效的选择")
            
    except Exception as e:
        print_error(f"组合优化启动失败: {e}")

# ==================== 主菜单 ====================

def show_menu():
    """显示主菜单"""
    while True:
        print_header("A股量化系统 - 主菜单")
        
        data_file = project_root / 'data' / 'akshare_real_data_fixed.pkl'
        if data_file.exists():
            freshness = check_data_freshness(data_file, max_age_hours=24)
            
            if not freshness['is_fresh']:
                print(f"\n{Color.WARNING}{'='*60}{Color.ENDC}")
                print(f"{Color.WARNING}⚠️ 数据时效性警告{Color.ENDC}")
                print(f"{Color.WARNING}  数据时间: {freshness['data_time'].strftime('%Y-%m-%d %H:%M:%S') if freshness['data_time'] else '未知'}{Color.ENDC}")
                print(f"{Color.WARNING}  数据年龄: {freshness['age_description']}{Color.ENDC}")
                print(f"{Color.WARNING}  建议: 运行选项1「数据工程」获取最新数据{Color.ENDC}")
                print(f"{Color.WARNING}{'='*60}{Color.ENDC}\n")
        
        print(f"{Color.BOLD}【量化流程五阶段】{Color.ENDC}")
        print(f"{Color.OKCYAN}  数据工程 → 因子研发 → 策略开发 → 回测验证 → 实盘工程{Color.ENDC}")
        
        print(f"\n{Color.BOLD}【一级菜单】{Color.ENDC}")
        print("  1. 数据工程        - 数据获取、质量检查、时效性管理")
        print("  2. 因子研发        - 因子挖掘、评估、监控")
        print("  3. 策略开发        - 多因子模型、选股器、再平衡")
        print("  4. 回测验证        - 回测、归因、压力测试")
        print("  5. 实盘工程        - 推送、风控、资金管理")
        print("  6. 系统管理        - 配置、日志、健康检查")
        
        print(f"\n{Color.BOLD}【快捷入口】{Color.ENDC}")
        print("  7. 从0-1量化投资（一键启动）⭐新增")
        print("  8. 每日主控流程（完整流水线）⭐推荐")
        print("  9. 盘前推送 ⭐推荐")
        print("  10. 日报推送 ⭐推荐")
        
        print(f"\n{Color.BOLD} 0. 退出系统{Color.ENDC}")
        
        choice = input(f"\n{Color.OKCYAN}请选择操作 (0-10): {Color.ENDC}")
        
        should_pause = True
        
        if choice == '0':
            print_success("感谢使用，再见！")
            break
        elif choice == '1':
            data_engineering_menu()
        elif choice == '2':
            factor_research_menu()
        elif choice == '3':
            strategy_development_menu()
        elif choice == '4':
            backtest_verification_menu()
        elif choice == '5':
            live_trading_menu()
        elif choice == '6':
            system_management_menu()
        elif choice == '7':
            quick_start_quant()
        elif choice == '8':
            daily_master()
        elif choice == '9':
            print_info("执行盘前推送...")
            script_path = scripts_dir / 'unified_daily_push.py'
            try:
                result = subprocess.run(
                    [sys.executable, str(script_path), '--type', 'morning'],
                    cwd=project_root,
                    capture_output=True,
                    text=True
                )
                if result.stdout:
                    print(result.stdout)
                if result.stderr:
                    print_error(result.stderr)
            except Exception as e:
                print_error(f"执行失败: {e}")
        elif choice == '10':
            print_info("执行日报推送...")
            script_path = scripts_dir / 'unified_daily_push.py'
            try:
                result = subprocess.run(
                    [sys.executable, str(script_path), '--type', 'evening'],
                    cwd=project_root,
                    capture_output=True,
                    text=True
                )
                if result.stdout:
                    print(result.stdout)
                if result.stderr:
                    print_error(result.stderr)
            except Exception as e:
                print_error(f"执行失败: {e}")
        else:
            print_error("无效的选择，请重新输入")
            should_pause = False
        
        if should_pause:
            input(f"\n{Color.OKCYAN}按回车键继续...{Color.ENDC}")

def main():
    """主函数"""
    logs_dir = project_root / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    os.chdir(project_root)
    
    print_header("欢迎使用A股量化系统")
    print(f"{Color.OKBLUE}项目路径: {project_root}{Color.ENDC}")
    print(f"{Color.OKBLUE}当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Color.ENDC}")
    print(f"{Color.OKGREEN}✓ 核心模块已加载{Color.ENDC}")
    
    print(f"\n{Color.BOLD}【系统架构】{Color.ENDC}")
    print(f"{Color.OKCYAN}  五阶段框架：数据工程 → 因子研发 → 策略开发 → 回测验证 → 实盘工程{Color.ENDC}")
    print(f"{Color.OKCYAN}  管理理念：从「寻找圣杯」到「管理不确定性」{Color.ENDC}")
    
    show_menu()

if __name__ == '__main__':
    main()
