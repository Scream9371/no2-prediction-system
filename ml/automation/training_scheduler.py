#!/usr/bin/env python3
"""
自动化训练调度器

专为生产环境设计的简化版本，特点：
- 不需要版本控制，只保留每日最新模型
- 完全自动化，无需人工干预
- 基于现有训练管道，直接调用scripts/run_pipeline.py
- 智能训练决策和监控
"""

import os
import sys
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from scripts.run_pipeline import train_all_cities, show_model_status, cleanup_old_models
from ml.src.control import get_supported_cities
from ml.src.data_loader import load_data_from_mysql


@dataclass
class SimpleTrainingResult:
    """训练结果"""
    timestamp: str
    total_cities: int
    successful_cities: int
    failed_cities: int
    skipped_cities: int
    execution_time: float
    successful_city_list: List[str]
    failed_city_list: List[str]
    skipped_city_list: List[str]


class SimpleAutoTrainingScheduler:
    """自动化训练调度器"""
    
    def __init__(self, log_dir: str = None):
        """
        初始化训练调度器
        
        Args:
            log_dir (str): 日志目录，默认为 logs/auto_training
        """
        self.log_dir = log_dir or os.path.join(os.getcwd(), 'logs', 'auto_training')
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('SimpleAutoTrainingScheduler')
        logger.setLevel(logging.INFO)
        
        # 避免重复添加handler
        if logger.handlers:
            return logger
        
        # 创建日志目录
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 文件handler - 按日期命名
        today = datetime.now().strftime('%Y%m%d')
        log_file = os.path.join(self.log_dir, f'auto_training_{today}.log')
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 控制台handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def check_data_freshness(self, days_threshold: int = 3) -> Tuple[List[str], List[str]]:
        """
        检查数据可用性和训练需求，确定哪些城市需要训练
        
        Args:
            days_threshold (int): 数据可用性阈值（天数），默认3天内有数据即可
            
        Returns:
            Tuple[List[str], List[str]]: (需要训练的城市, 跳过的城市)
        """
        cities = get_supported_cities()
        cities_to_train = []
        cities_to_skip = []
        
        # 数据可用性阈值：最近N天内有数据即可
        data_cutoff_time = datetime.now() - timedelta(days=days_threshold)
        today_str = datetime.now().strftime("%Y%m%d")
        
        for city in cities:
            try:
                # 1. 检查今天是否已经训练过模型
                from scripts.run_pipeline import is_model_trained_today
                if is_model_trained_today(city):
                    cities_to_skip.append(city)
                    self.logger.info(f"{city}: 今日模型已存在，跳过训练")
                    continue
                
                # 2. 检查数据可用性
                df = load_data_from_mysql(city)
                if df.empty:
                    cities_to_skip.append(city)
                    self.logger.warning(f"{city}: 无可用数据")
                    continue
                
                # 3. 检查数据量是否足够
                if len(df) < 100:
                    cities_to_skip.append(city)
                    self.logger.warning(f"{city}: 数据量不足 ({len(df)}条)")
                    continue
                
                # 4. 检查数据是否太陈旧（超过阈值天数）
                latest_time = df['observation_time'].max()
                if latest_time < data_cutoff_time:
                    cities_to_skip.append(city)
                    self.logger.warning(f"{city}: 数据过于陈旧 (最新: {latest_time}, 阈值: {days_threshold}天)")
                    continue
                
                # 5. 所有检查通过，可以训练
                cities_to_train.append(city)
                days_old = (datetime.now() - latest_time).days
                self.logger.info(f"{city}: 数据检查通过 (最新: {latest_time}, {days_old}天前, 共{len(df)}条)")
                
            except Exception as e:
                cities_to_skip.append(city)
                self.logger.error(f"{city}: 数据检查失败 - {str(e)}")
        
        self.logger.info(f"数据检查完成: 需训练{len(cities_to_train)}个城市, 跳过{len(cities_to_skip)}个城市")
        return cities_to_train, cities_to_skip
    
    def run_daily_training(self) -> SimpleTrainingResult:
        """
        执行每日自动训练
        
        Returns:
            SimpleTrainingResult: 训练结果
        """
        start_time = datetime.now()
        self.logger.info("=" * 60)
        self.logger.info(f"开始每日自动模型训练 - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 60)
        
        try:
            # 1. 显示当前模型状态
            self.logger.info("📊 当前模型状态:")
            show_model_status()
            
            # 2. 检查数据新鲜度
            self.logger.info("\n🔍 检查数据新鲜度...")
            cities_to_train, cities_to_skip = self.check_data_freshness()
            
            if not cities_to_train:
                self.logger.info("所有城市都已跳过，无需训练")
                end_time = datetime.now()
                return SimpleTrainingResult(
                    timestamp=start_time.isoformat(),
                    total_cities=len(get_supported_cities()),
                    successful_cities=0,
                    failed_cities=0,
                    skipped_cities=len(cities_to_skip),
                    execution_time=(end_time - start_time).total_seconds(),
                    successful_city_list=[],
                    failed_city_list=[],
                    skipped_city_list=cities_to_skip
                )
            
            # 3. 执行训练（使用现有的train_all_cities函数）
            self.logger.info(f"\n🚀 开始训练 {len(cities_to_train)} 个城市...")
            training_results = train_all_cities()
            
            # 4. 解析训练结果
            successful_cities = training_results.get('successful', [])
            failed_cities = training_results.get('failed', [])
            
            # 5. 清理旧模型
            self.logger.info("\n🧹 清理旧模型文件...")
            cleaned_count = cleanup_old_models(days_to_keep=7)
            self.logger.info(f"已清理 {cleaned_count} 个旧模型文件")
            
            # 6. 显示最终状态
            self.logger.info("\n📊 训练后模型状态:")
            show_model_status()
            
            # 7. 生成结果
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            result = SimpleTrainingResult(
                timestamp=start_time.isoformat(),
                total_cities=len(get_supported_cities()),
                successful_cities=len(successful_cities),
                failed_cities=len(failed_cities),
                skipped_cities=len(cities_to_skip),
                execution_time=execution_time,
                successful_city_list=successful_cities,
                failed_city_list=failed_cities,
                skipped_city_list=cities_to_skip
            )
            
            # 8. 记录训练报告
            self._save_training_report(result)
            
            # 9. 输出总结
            self.logger.info("=" * 60)
            self.logger.info("📋 每日训练完成总结:")
            self.logger.info(f"   执行时间: {execution_time:.1f}秒")
            self.logger.info(f"   总城市数: {result.total_cities}")
            self.logger.info(f"   训练成功: {result.successful_cities}")
            self.logger.info(f"   训练失败: {result.failed_cities}")
            self.logger.info(f"   跳过训练: {result.skipped_cities}")
            
            if result.successful_cities > 0:
                self.logger.info(f"   成功城市: {', '.join(result.successful_city_list)}")
            if result.failed_cities > 0:
                self.logger.info(f"   失败城市: {', '.join(result.failed_city_list)}")
            
            self.logger.info("=" * 60)
            
            return result
            
        except Exception as e:
            end_time = datetime.now()
            self.logger.error(f"每日训练执行失败: {str(e)}")
            
            # 返回失败结果
            return SimpleTrainingResult(
                timestamp=start_time.isoformat(),
                total_cities=len(get_supported_cities()),
                successful_cities=0,
                failed_cities=len(get_supported_cities()),
                skipped_cities=0,
                execution_time=(end_time - start_time).total_seconds(),
                successful_city_list=[],
                failed_city_list=get_supported_cities(),
                skipped_city_list=[]
            )
    
    def _save_training_report(self, result: SimpleTrainingResult):
        """保存训练报告到JSON文件"""
        try:
            report_file = os.path.join(
                self.log_dir, 
                f"training_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            report_data = {
                'timestamp': result.timestamp,
                'summary': {
                    'total_cities': result.total_cities,
                    'successful_cities': result.successful_cities,
                    'failed_cities': result.failed_cities,
                    'skipped_cities': result.skipped_cities,
                    'execution_time_seconds': result.execution_time
                },
                'details': {
                    'successful_city_list': result.successful_city_list,
                    'failed_city_list': result.failed_city_list,
                    'skipped_city_list': result.skipped_city_list
                }
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"训练报告已保存: {report_file}")
            
        except Exception as e:
            self.logger.error(f"保存训练报告失败: {str(e)}")
    
    def health_check(self) -> Dict[str, bool]:
        """
        系统健康检查
        
        Returns:
            Dict[str, bool]: 各项检查结果
        """
        checks = {}
        
        try:
            # 检查数据库连接
            cities = get_supported_cities()
            checks['database_connection'] = len(cities) > 0
            
            # 检查模型目录
            from config.paths import DAILY_MODELS_DIR, LATEST_MODELS_DIR
            checks['model_directories'] = (
                os.path.exists(DAILY_MODELS_DIR) and 
                os.path.exists(LATEST_MODELS_DIR)
            )
            
            # 检查日志目录
            checks['log_directory'] = os.path.exists(self.log_dir)
            
            # 检查数据可用性
            data_available = 0
            for city in cities[:3]:  # 只检查前3个城市
                try:
                    df = load_data_from_mysql(city)
                    if not df.empty:
                        data_available += 1
                except:
                    pass
            checks['data_availability'] = data_available > 0
            
        except Exception as e:
            self.logger.error(f"健康检查失败: {str(e)}")
            checks['system_error'] = False
        
        return checks


def main():
    """命令行入口"""
    import sys
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        scheduler = SimpleAutoTrainingScheduler()
        
        if command == 'health':
            # 健康检查
            checks = scheduler.health_check()
            print("🏥 系统健康检查:")
            for check_name, status in checks.items():
                status_icon = "✅" if status else "❌"
                print(f"  {status_icon} {check_name}: {'通过' if status else '失败'}")
            
            # 如果有检查失败，退出码为1
            if not all(checks.values()):
                sys.exit(1)
                
        elif command == 'run':
            # 执行训练
            result = scheduler.run_daily_training()
            
            # 如果有失败的城市，退出码为1
            if result.failed_cities > 0:
                sys.exit(1)
        
        else:
            print(f"未知命令: {command}")
            print("可用命令: health, run")
            sys.exit(1)
    
    else:
        # 默认执行训练
        scheduler = SimpleAutoTrainingScheduler()
        result = scheduler.run_daily_training()
        
        # 如果有失败的城市，退出码为1
        if result.failed_cities > 0:
            sys.exit(1)


if __name__ == '__main__':
    main()