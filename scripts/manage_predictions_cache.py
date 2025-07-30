#!/usr/bin/env python3
"""
预测缓存管理脚本

提供缓存的查看、清理、手动生成等管理功能
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ml.automation.training_scheduler import SimpleAutoTrainingScheduler
from ml.src.control import get_supported_cities


def get_cache_dir() -> str:
    """获取缓存目录路径"""
    return os.path.join(os.getcwd(), 'data', 'predictions_cache')


def list_cache_files() -> List[Dict]:
    """
    列出所有缓存文件
    
    Returns:
        List[Dict]: 缓存文件信息列表
    """
    cache_dir = get_cache_dir()
    if not os.path.exists(cache_dir):
        return []
    
    cache_files = []
    for filename in os.listdir(cache_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(cache_dir, filename)
            file_stat = os.stat(file_path)
            
            # 尝试读取文件内容获取元数据
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                cache_files.append({
                    'filename': filename,
                    'path': file_path,
                    'size': file_stat.st_size,
                    'modified_time': datetime.fromtimestamp(file_stat.st_mtime),
                    'generated_at': cache_data.get('generated_at'),
                    'cities_count': cache_data.get('cities_count', 0),
                    'date': cache_data.get('date')
                })
            except:
                cache_files.append({
                    'filename': filename,
                    'path': file_path,
                    'size': file_stat.st_size,
                    'modified_time': datetime.fromtimestamp(file_stat.st_mtime),
                    'generated_at': None,
                    'cities_count': 0,
                    'date': None
                })
    
    return sorted(cache_files, key=lambda x: x['modified_time'], reverse=True)


def show_cache_status():
    """显示缓存状态"""
    print("📁 预测缓存状态报告")
    print("=" * 60)
    
    cache_files = list_cache_files()
    
    if not cache_files:
        print("❌ 未找到任何缓存文件")
        print(f"缓存目录: {get_cache_dir()}")
        return
    
    print(f"缓存目录: {get_cache_dir()}")
    print(f"缓存文件数: {len(cache_files)}")
    print()
    
    # 显示最新缓存信息
    latest_cache = None
    for cache_file in cache_files:
        if cache_file['filename'] == 'latest_predictions.json':
            latest_cache = cache_file
            break
    
    if latest_cache:
        print("🔮 最新缓存:")
        print(f"  文件: {latest_cache['filename']}")
        print(f"  生成时间: {latest_cache['generated_at'] or '未知'}")
        print(f"  城市数量: {latest_cache['cities_count']}")
        print(f"  文件大小: {latest_cache['size']:,} 字节")
        print()
    
    # 显示历史缓存文件
    daily_caches = [f for f in cache_files if f['filename'].startswith('daily_predictions_')]
    if daily_caches:
        print("📅 历史缓存文件:")
        for cache_file in daily_caches[:5]:  # 只显示最近5个
            age = datetime.now() - cache_file['modified_time']
            print(f"  {cache_file['filename']} ({cache_file['cities_count']}个城市, {age.days}天前)")
        
        if len(daily_caches) > 5:
            print(f"  ... 还有 {len(daily_caches) - 5} 个文件")
    
    print()


def view_cache_content(date_str: str = None):
    """
    查看缓存内容
    
    Args:
        date_str (str): 日期字符串 (YYYYMMDD)，默认查看最新缓存
    """
    scheduler = SimpleAutoTrainingScheduler()
    cache_data = scheduler.load_predictions_cache(date_str)
    
    if not cache_data:
        print(f"❌ 未找到缓存数据 (日期: {date_str or '最新'})")
        return
    
    print(f"🔮 缓存内容详情 (日期: {cache_data.get('date', '未知')})")
    print("=" * 60)
    print(f"生成时间: {cache_data.get('generated_at', '未知')}")
    print(f"城市数量: {cache_data.get('cities_count', 0)}")
    print()
    
    predictions = cache_data.get('predictions', {})
    if not predictions:
        print("❌ 缓存中无预测数据")
        return
    
    print("城市预测数据:")
    for city, data in predictions.items():
        current_value = data.get('currentValue', 0)
        avg_value = data.get('avgValue', 0)
        update_time = data.get('updateTime', '未知')
        cached = data.get('cached', False)
        
        print(f"  {city:12} | 当前: {current_value:6.1f} | 平均: {avg_value:6.1f} | 更新: {update_time} | 缓存: {'是' if cached else '否'}")


def cleanup_old_cache(days_to_keep: int = 7):
    """
    清理旧的缓存文件
    
    Args:
        days_to_keep (int): 保留的天数，默认7天
    """
    print(f"🧹 清理 {days_to_keep} 天前的缓存文件...")
    
    cache_files = list_cache_files()
    cutoff_time = datetime.now() - timedelta(days=days_to_keep)
    
    removed_count = 0
    for cache_file in cache_files:
        # 跳过latest_predictions.json
        if cache_file['filename'] == 'latest_predictions.json':
            continue
        
        if cache_file['modified_time'] < cutoff_time:
            try:
                os.remove(cache_file['path'])
                removed_count += 1
                print(f"  ✅ 删除: {cache_file['filename']}")
            except Exception as e:
                print(f"  ❌ 删除失败: {cache_file['filename']} - {e}")
    
    if removed_count > 0:
        print(f"🗑️  已清理 {removed_count} 个缓存文件")
    else:
        print("ℹ️  没有需要清理的缓存文件")


def generate_cache_manually(cities: List[str] = None):
    """
    手动生成预测缓存
    
    Args:
        cities (List[str]): 要生成缓存的城市列表，默认为所有城市
    """
    if cities is None:
        cities = get_supported_cities()
    
    print(f"🔮 手动生成预测缓存 ({len(cities)} 个城市)...")
    
    scheduler = SimpleAutoTrainingScheduler()
    result = scheduler._precompute_daily_predictions(cities)
    
    print(f"生成完成: 成功 {result['successful']} 个城市, 失败 {result['failed']} 个城市")
    
    if result['successful'] > 0:
        print("✅ 缓存生成成功，可通过 API 访问预测数据")
    
    if result['failed'] > 0:
        print("⚠️  部分城市生成失败，请检查模型文件是否存在")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='预测缓存管理工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # status 命令
    subparsers.add_parser('status', help='显示缓存状态')
    
    # view 命令
    view_parser = subparsers.add_parser('view', help='查看缓存内容')
    view_parser.add_argument('--date', help='日期 (YYYYMMDD)，默认查看最新缓存')
    
    # cleanup 命令
    cleanup_parser = subparsers.add_parser('cleanup', help='清理旧缓存文件')
    cleanup_parser.add_argument('--days', type=int, default=7, help='保留天数 (默认7天)')
    
    # generate 命令
    generate_parser = subparsers.add_parser('generate', help='手动生成缓存')
    generate_parser.add_argument('--cities', nargs='+', help='指定城市列表 (默认所有城市)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'status':
            show_cache_status()
        
        elif args.command == 'view':
            view_cache_content(args.date)
        
        elif args.command == 'cleanup':
            cleanup_old_cache(args.days)
        
        elif args.command == 'generate':
            generate_cache_manually(args.cities)
        
    except KeyboardInterrupt:
        print("\n操作已取消")
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()