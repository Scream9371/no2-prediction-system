"""
数据备份模块

此模块负责将数据库中的NO2预测数据备份到CSV文件，
为数据恢复和分析提供备份支持。

主要功能：
- 备份11个大湾区城市的完整历史数据
- 按城市分别保存CSV文件到data/backup目录
- 提供备份状态报告和数据统计

典型用法：
    python -m scripts.run_databackup
"""

import csv
import os
from datetime import datetime

from database.crud import BACKUP_CITY_LIST
from database.session import get_db
from dotenv import load_dotenv


def backup_city_data_to_csv(city_name, model_class):
    """
    从数据库备份指定城市的数据到CSV文件
    
    Args:
        city_name (str): 城市名称
        model_class: 对应的数据库模型类
        
    Returns:
        bool: 备份是否成功
    """
    db = next(get_db())

    try:
        # 从数据库获取所有记录，按时间升序排列
        records = db.query(model_class).order_by(model_class.observation_time.asc()).all()

        if not records:
            print(f"警告: {city_name} 没有可备份的数据")
            return False

        # 确保backup目录存在
        backup_dir = "data/backup"
        os.makedirs(backup_dir, exist_ok=True)

        # 定义CSV文件名和字段
        csv_file = f"{backup_dir}/{city_name}_backup.csv"
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

        print(f"成功备份 {city_name} 数据到 {csv_file}，共 {len(records)} 条记录")
        return True

    except Exception as e:
        print(f"备份 {city_name} 数据时出错: {str(e)}")
        return False
    finally:
        db.close()


def backup_all_cities_data():
    """
    备份所有城市的数据到CSV文件
    
    Returns:
        dict: 备份结果统计
    """
    results = {
        "successful": [],
        "failed": [],
        "total_records": 0
    }

    print("=== 开始备份所有城市数据 ===")
    print(f"备份时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    for city_name, model_class in BACKUP_CITY_LIST.items():
        print(f"正在备份 {city_name} 的数据...")

        success = backup_city_data_to_csv(city_name, model_class)

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
    print("=== 备份完成 ===")
    print(f"成功备份城市: {len(results['successful'])}/{len(BACKUP_CITY_LIST)}")
    print(f"成功的城市: {', '.join(results['successful'])}")
    if results["failed"]:
        print(f"失败的城市: {', '.join(results['failed'])}")
    print(f"总计备份记录数: {results['total_records']}")
    print(f"备份文件保存位置: data/backup/")

    return results


def main():
    """
    主函数：从数据库备份所有城市数据到CSV文件
    """
    try:
        # 加载环境变量
        load_dotenv()
        
        # 验证数据库连接
        from config.database import engine
        print(f"数据库连接: {engine.url}")
        print(f"数据库类型: {engine.dialect.name}")
        
        # 测试连接
        try:
            with engine.connect() as conn:
                print("数据库连接测试成功")
        except Exception as db_error:
            print(f"数据库连接失败: {db_error}")
            return
        
        results = backup_all_cities_data()

        if results["successful"]:
            print(f"\n数据备份成功完成!")
            print(f"所有备份文件已保存到 'data/backup/' 目录")
        else:
            print(f"\n数据备份失败!")

    except Exception as e:
        print(f"程序执行时发生错误: {str(e)}")


if __name__ == "__main__":
    main()