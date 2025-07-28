"""
模型训练管道脚本

此脚本负责批量训练所有大湾区城市的NO2预测模型，
支持每日版本控制，确保同一天多次执行不重复训练。

主要功能：
- 批量训练11个城市的NC-CQR模型
- 每日模型版本控制，按日期保存模型文件
- 防重复训练机制，同一天多次执行只训练缺失的模型
- 自动清理旧模型文件，节省存储空间

典型用法：
    python -m scripts.run_pipeline
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

from ml.src.control import get_supported_cities
from ml.src.train import train_full_pipeline, save_model


def get_daily_model_path(city: str, date_str: str = None) -> str:
    """
    获取每日模型文件路径
    
    Args:
        city (str): 城市名称
        date_str (str): 日期字符串，格式为YYYYMMDD，默认为今天
        
    Returns:
        str: 模型文件路径
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")
    
    from config.paths import get_daily_model_path as config_get_daily_model_path
    return config_get_daily_model_path(city, date_str)


def get_latest_model_path(city: str) -> str:
    """
    获取最新模型的符号链接路径（用于预测）
    
    Args:
        city (str): 城市名称
        
    Returns:
        str: 符号链接路径
    """
    from config.paths import get_latest_model_path as config_get_latest_model_path
    return config_get_latest_model_path(city)


def is_model_trained_today(city: str) -> bool:
    """
    检查今天是否已经训练过该城市的模型
    
    Args:
        city (str): 城市名称
        
    Returns:
        bool: 今天是否已训练
    """
    today_model_path = get_daily_model_path(city)
    return os.path.exists(today_model_path)


def create_model_symlink(city: str, date_str: str = None):
    """
    创建或更新模型的符号链接，指向最新的每日模型
    
    Args:
        city (str): 城市名称
        date_str (str): 日期字符串，默认为今天
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")
    
    daily_model_path = get_daily_model_path(city, date_str)
    latest_model_path = get_latest_model_path(city)
    
    # 如果每日模型存在
    if os.path.exists(daily_model_path):
        # 删除旧的符号链接（如果存在）
        if os.path.exists(latest_model_path) or os.path.islink(latest_model_path):
            os.remove(latest_model_path)
        
        # 创建新的符号链接（Windows上使用复制代替符号链接）
        try:
            if os.name == 'nt':  # Windows
                import shutil
                shutil.copy2(daily_model_path, latest_model_path)
            else:  # Unix/Linux/Mac
                os.symlink(os.path.abspath(daily_model_path), latest_model_path)
            print(f"已创建 {city} 模型链接: {latest_model_path} -> {daily_model_path}")
        except Exception as e:
            print(f"    创建 {city} 模型链接失败: {e}")


def train_city_with_version_control(city: str, **train_kwargs) -> bool:
    """
    带版本控制的城市模型训练
    
    Args:
        city (str): 城市名称
        **train_kwargs: 训练参数
        
    Returns:
        bool: 训练是否成功
    """
    # 检查今天是否已经训练过
    if is_model_trained_today(city):
        print(f"    {city} 今日模型已存在，跳过训练")
        # 确保符号链接存在
        create_model_symlink(city)
        return True
    
    # 临时修改train_mode以保存到带日期的路径
    today_str = datetime.now().strftime("%Y%m%d")
    daily_model_path = get_daily_model_path(city, today_str)
    
    try:
        # 直接调用训练流程，不预先保存模型
        model, Q, scalers, eval_results = train_full_pipeline(city=city, **train_kwargs)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(daily_model_path), exist_ok=True)
        
        # 保存到带日期的路径
        save_model(model, Q, scalers, daily_model_path)
        
        # 创建符号链接指向最新模型
        create_model_symlink(city, today_str)
        
        print(f"{city} 每日模型已保存: {daily_model_path}")
        print(f"   测试集覆盖率: {eval_results['coverage']:.1%}")
        print(f"   平均区间宽度: {eval_results['avg_interval_width']:.2f}")
        return True
            
    except Exception as e:
        print(f"{city} 训练过程出错: {str(e)}")
        return False


def train_all_cities():
    """
    批量训练所有城市的模型
    
    Returns:
        dict: 训练结果统计
    """
    print("=== 开始批量训练所有城市模型 ===")
    
    cities = get_supported_cities()
    results = {
        "total_cities": len(cities),
        "successful": [],
        "failed": [],
        "skipped": [],
        "start_time": datetime.now()
    }
    
    print(f"计划训练 {len(cities)} 个城市的模型")
    print()
    
    for i, city in enumerate(cities, 1):
        print(f"[{i}/{len(cities)}] 正在处理 {city}...")
        
        try:
            # 使用带版本控制的训练函数
            success = train_city_with_version_control(
                city=city,
                epochs=150,
                batch_size=32,
                learning_rate=1e-3
            )
            
            if success:
                if is_model_trained_today(city):
                    if city in results["successful"]:
                        results["successful"].append(city)
                    else:
                        results["skipped"].append(city)
                else:
                    results["successful"].append(city)
                print(f"{city} 模型处理成功")
            else:
                results["failed"].append(city)
                print(f"{city} 模型处理失败")
                
        except Exception as e:
            results["failed"].append(city)
            print(f"{city} 模型处理出错: {str(e)}")
        
        print()
    
    results["end_time"] = datetime.now()
    results["duration"] = results["end_time"] - results["start_time"]
    
    # 输出总结
    print("=== 批量训练完成 ===")
    print(f"总处理城市数: {results['total_cities']}")
    print(f"新训练成功: {len(results['successful'])}")
    print(f"跳过训练: {len(results['skipped'])}")
    print(f"训练失败: {len(results['failed'])}")
    print(f"执行耗时: {results['duration']}")
    
    if results["successful"]:
        print(f"新训练城市: {', '.join(results['successful'])}")
    if results["skipped"]:
        print(f"跳过城市: {', '.join(results['skipped'])}")
    if results["failed"]:
        print(f"失败城市: {', '.join(results['failed'])}")
    
    return results


def cleanup_old_models(days_to_keep: int = 7):
    """
    清理旧的模型文件，只保留最近N天的模型
    
    Args:
        days_to_keep (int): 保留的天数，默认7天
    """
    print(f"开始清理 {days_to_keep} 天前的旧模型...")
    
    from config.paths import DAILY_MODELS_DIR
    models_dir = DAILY_MODELS_DIR
    if not os.path.exists(models_dir):
        return
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    cutoff_str = cutoff_date.strftime("%Y%m%d")
    
    removed_count = 0
    for filename in os.listdir(models_dir):
        if filename.endswith(".pth") and "_nc_cqr_model_" in filename:
            # 提取日期字符串
            try:
                date_part = filename.split("_nc_cqr_model_")[1].replace(".pth", "")
                if len(date_part) == 8 and date_part.isdigit():  # YYYYMMDD格式
                    if date_part < cutoff_str:
                        old_model_path = os.path.join(models_dir, filename)
                        os.remove(old_model_path)
                        removed_count += 1
                        print(f"🗑️  已删除旧模型: {filename}")
            except:
                continue  # 跳过格式不正确的文件
    
    if removed_count > 0:
        print(f"已清理 {removed_count} 个旧模型文件")
    else:
        print("没有需要清理的旧模型")


def show_model_status():
    """
    显示所有城市的模型状态
    """
    print("模型状态报告:")
    print("-" * 60)
    
    cities = get_supported_cities()
    today_str = datetime.now().strftime("%Y%m%d")
    
    for city in cities:
        latest_path = get_latest_model_path(city)
        daily_path = get_daily_model_path(city, today_str)
        
        latest_exists = os.path.exists(latest_path)
        daily_exists = os.path.exists(daily_path)
        
        status = "[OK]" if daily_exists else ("[WARN]" if latest_exists else "[FAIL]")
        
        print(f"{status} {city:15} | 今日模型: {'存在' if daily_exists else '不存在':6} | 最新模型: {'存在' if latest_exists else '不存在'}")


def main():
    """
    主函数：执行模型训练管道
    """
    try:
        # 加载环境变量
        load_dotenv()
        
        print("NO2预测模型训练管道启动")
        print(f"执行日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 显示当前模型状态
        show_model_status()
        print()
        
        # 执行批量训练
        results = train_all_cities()
        print()
        
        # 清理旧模型（保留7天）
        cleanup_old_models(days_to_keep=7)
        print()
        
        # 显示最终状态
        show_model_status()
        
        # 判断整体成功状态
        if results["successful"] or results["skipped"]:
            print(f"\n训练管道执行完成！")
            print(f"成功处理 {len(results['successful']) + len(results['skipped'])} 个城市的模型")
            
            if results["failed"]:
                print(f"    {len(results['failed'])} 个城市处理失败，请检查日志")
        else:
            print(f"\\n训练管道执行失败！")
            print("所有城市模型处理都失败了")
            sys.exit(1)
            
    except Exception as e:
        print(f"训练管道执行时发生错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()