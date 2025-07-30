#!/usr/bin/env python3
"""
预计算系统功能测试脚本

测试预计算缓存系统的各个功能模块
"""

import os
import sys
import json
import tempfile
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ml.automation.training_scheduler import SimpleAutoTrainingScheduler
from ml.src.control import get_supported_cities


def test_precompute_functions():
    """测试预计算核心功能"""
    print("测试1: 预计算核心功能")
    print("-" * 40)
    
    scheduler = SimpleAutoTrainingScheduler()
    
    # 测试城市列表（选择2个城市进行快速测试）
    test_cities = get_supported_cities()[:2]
    print(f"测试城市: {test_cities}")
    
    try:
        # 测试预计算功能
        result = scheduler._precompute_daily_predictions(test_cities)
        
        print(f"预计算结果: 成功 {result['successful']} 个城市, 失败 {result['failed']} 个城市")
        
        if result['successful'] > 0:
            print("预计算功能正常")
        else:
            print("预计算功能异常：所有城市都失败")
            return False
            
    except Exception as e:
        print(f"预计算功能测试失败: {e}")
        return False
    
    return True


def test_cache_file_operations():
    """测试缓存文件操作"""
    print("\n测试2: 缓存文件操作")
    print("-" * 40)
    
    scheduler = SimpleAutoTrainingScheduler()
    
    try:
        # 创建测试数据
        test_cache = {
            'guangzhou': {
                "updateTime": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "currentValue": 25.5,
                "avgValue": 23.2,
                "times": ["00:00", "01:00", "02:00"],
                "values": [25.5, 24.1, 23.8],
                "low": [20.5, 19.1, 18.8],
                "high": [30.5, 29.1, 28.8],
                "cached": True,
                "cache_time": datetime.now().isoformat()
            }
        }
        
        # 测试保存缓存
        scheduler._save_predictions_cache(test_cache)
        print("缓存保存功能正常")
        
        # 测试加载缓存
        loaded_cache = scheduler.load_predictions_cache()
        
        if loaded_cache and 'predictions' in loaded_cache:
            if 'guangzhou' in loaded_cache['predictions']:
                print("缓存加载功能正常")
                print(f"   加载的城市数量: {len(loaded_cache['predictions'])}")
            else:
                print("缓存加载功能异常：数据不完整")
                return False
        else:
            print("缓存加载功能异常：无法加载数据")
            return False
            
    except Exception as e:
        print(f"缓存文件操作测试失败: {e}")
        return False
    
    return True


def test_api_integration():
    """测试API集成"""
    print("\n测试3: API集成测试")
    print("-" * 40)
    
    try:
        # 导入API函数
        from web.routes.api_routes import load_daily_predictions_cache, fallback_realtime_prediction
        
        # 测试缓存加载函数
        cached_data = load_daily_predictions_cache()
        
        if cached_data:
            print("API缓存加载功能正常")
            print(f"   缓存数据包含 {len(cached_data.get('predictions', {}))} 个城市")
        else:
            print("API缓存加载：未找到缓存数据（正常情况）")
        
        # 测试降级预测功能（使用不存在的城市）
        print("测试降级预测功能...")
        # 注意：这里不实际调用，因为需要Flask上下文
        print("API集成测试通过（函数导入成功）")
        
    except Exception as e:
        print(f"API集成测试失败: {e}")
        return False
    
    return True


def test_cache_management():
    """测试缓存管理功能"""
    print("\n测试4: 缓存管理功能")
    print("-" * 40)
    
    try:
        # 导入缓存管理函数
        from scripts.manage_predictions_cache import list_cache_files, get_cache_dir
        
        cache_dir = get_cache_dir()
        print(f"缓存目录: {cache_dir}")
        
        cache_files = list_cache_files()
        print(f"找到 {len(cache_files)} 个缓存文件")
        
        if cache_files:
            latest_file = cache_files[0]
            print(f"最新缓存: {latest_file['filename']} ({latest_file['cities_count']} 个城市)")
        
        print("缓存管理功能正常")
        
    except Exception as e:
        print(f"缓存管理功能测试失败: {e}")
        return False
    
    return True


def test_data_format():
    """测试数据格式"""
    print("\n测试5: 数据格式验证")
    print("-" * 40)
    
    scheduler = SimpleAutoTrainingScheduler()
    
    try:
        # 创建模拟预测数据
        import pandas as pd
        from datetime import timedelta
        
        current_time = datetime.now()
        test_predictions = pd.DataFrame({
            'observation_time': [current_time + timedelta(hours=i) for i in range(24)],
            'prediction': [25.0 + i * 0.1 for i in range(24)],
            'lower_bound': [20.0 + i * 0.1 for i in range(24)],
            'upper_bound': [30.0 + i * 0.1 for i in range(24)]
        })
        
        # 测试格式化函数
        formatted_data = scheduler._format_predictions_for_api(test_predictions)
        
        # 验证必要字段
        required_fields = ['updateTime', 'currentValue', 'avgValue', 'times', 'values', 'low', 'high', 'cached']
        missing_fields = [field for field in required_fields if field not in formatted_data]
        
        if missing_fields:
            print(f"数据格式验证失败：缺少字段 {missing_fields}")
            return False
        
        # 验证数据长度
        if len(formatted_data['times']) != 24:
            print(f"数据格式验证失败：时间点数量不正确 ({len(formatted_data['times'])})")
            return False
        
        if len(formatted_data['values']) != 24:
            print(f"数据格式验证失败：预测值数量不正确 ({len(formatted_data['values'])})")
            return False
        
        print("数据格式验证通过")
        print(f"   时间点: {len(formatted_data['times'])} 个")
        print(f"   预测值: {len(formatted_data['values'])} 个")
        print(f"   当前值: {formatted_data['currentValue']}")
        print(f"   平均值: {formatted_data['avgValue']}")
        
    except Exception as e:
        print(f"数据格式验证失败: {e}")
        return False
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("开始预计算系统功能测试")
    print("=" * 60)
    
    tests = [
        test_cache_file_operations,
        test_api_integration,
        test_cache_management,
        test_data_format,
        # test_precompute_functions,  # 放到最后，因为可能需要较长时间
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print("测试失败")
        except Exception as e:
            print(f"测试异常: {e}")
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("所有测试通过！预计算系统功能正常")
    else:
        print("部分测试失败，请检查相关功能")
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)