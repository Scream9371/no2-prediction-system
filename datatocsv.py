import os
import csv
import sys
from datetime import datetime
import pandas as pd

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.crud import CITY_MODEL_MAP
from database.db import get_db


def export_city_data_to_csv(city_name, model_class):
    """
    从数据库导出指定城市的数据到CSV文件
    
    Args:
        city_name (str): 城市名称
        model_class: 对应的数据库模型类
        
    Returns:
        bool: 导出是否成功
    """
    db = next(get_db())
    
    try:
        # 从数据库获取所有记录，按时间升序排列
        records = db.query(model_class).order_by(model_class.observation_time.asc()).all()
        
        if not records:
            print(f"警告: {city_name} 没有可导出的数据")
            return False
        
        # 确保data目录存在
        os.makedirs("data", exist_ok=True)
        
        # 定义CSV文件名和字段
        csv_file = f"data/{city_name}_data.csv"
        fieldnames = [
            "observation_time",
            "no2_concentration", 
            "temperature",
            "humidity",
            "wind_speed",
            "wind_direction",
            "pressure"
        ]
        
        # 写入CSV文件
        with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for record in records:
                # 格式化时间为MySQL标准格式
                formatted_time = record.observation_time.strftime("%Y-%m-%d %H:%M:%S")
                
                row = {
                    "observation_time": formatted_time,
                    "no2_concentration": record.no2_concentration,
                    "temperature": record.temperature,
                    "humidity": record.humidity,
                    "wind_speed": record.wind_speed,
                    "wind_direction": record.wind_direction,
                    "pressure": record.pressure
                }
                writer.writerow(row)
        
        print(f"成功导出 {city_name} 数据到 {csv_file}，共 {len(records)} 条记录")
        return True
        
    except Exception as e:
        print(f"导出 {city_name} 数据时出错: {str(e)}")
        return False
    finally:
        db.close()


def export_all_cities_to_csv():
    """
    导出所有城市的数据到CSV文件
    
    Returns:
        dict: 导出结果统计
    """
    results = {
        "successful": [],
        "failed": [],
        "total_records": 0
    }
    
    print("=== 开始导出所有城市数据到CSV ===")
    print()
    
    for city_name, model_class in CITY_MODEL_MAP.items():
        print(f"正在导出 {city_name} 的数据...")
        
        success = export_city_data_to_csv(city_name, model_class)
        
        if success:
            results["successful"].append(city_name)
            # 计算记录数
            db = next(get_db())
            try:
                count = db.query(model_class).count()
                results["total_records"] += count
            finally:
                db.close()
        else:
            results["failed"].append(city_name)
        
        print()
    
    # 输出总结
    print("=== 导出完成 ===")
    print(f"成功导出城市: {len(results['successful'])}/{len(CITY_MODEL_MAP)}")
    print(f"成功的城市: {', '.join(results['successful'])}")
    if results["failed"]:
        print(f"失败的城市: {', '.join(results['failed'])}")
    print(f"总计导出记录数: {results['total_records']}")
    
    return results


def main():
    """
    主函数：从数据库导出所有城市数据到CSV文件
    """
    try:
        results = export_all_cities_to_csv()
        
        if results["successful"]:
            print(f"\n成功完成CSV导出!")
            print(f"所有CSV文件已保存到 'data/' 目录")
        else:
            print(f"\nCSV导出失败!")
            
    except Exception as e:
        print(f"程序执行时发生错误: {str(e)}")


if __name__ == "__main__":
    main()
