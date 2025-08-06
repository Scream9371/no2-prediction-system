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

from scripts.run_pipeline import train_cities, show_model_status, cleanup_old_models
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
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        
        return logger
    
    def check_data_freshness(self, days_threshold: int = 3, force_override: bool = False) -> Tuple[List[str], List[str]]:
        """
        检查数据可用性和训练需求，确定哪些城市需要训练
        
        Args:
            days_threshold (int): 数据可用性阈值（天数），默认3天内有数据即可
            force_override (bool): 是否强制覆盖模式，跳过已训练检查
            
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
                # 1. 检查今天是否已经训练过模型（强制覆盖时跳过此检查）
                if not force_override:
                    from scripts.run_pipeline import is_model_trained_today
                    if is_model_trained_today(city):
                        cities_to_skip.append(city)
                        self.logger.info(f"{city}: 今日模型已存在，跳过训练")
                        continue
                else:
                    self.logger.info(f"{city}: 强制覆盖模式，忽略已训练检查")
                
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
    
    def run_daily_training(self, force_override: bool = False) -> SimpleTrainingResult:
        """
        执行每日自动训练
        
        Args:
            force_override (bool): 是否强制覆盖模式，删除现有模型和缓存重新训练
        
        Returns:
            SimpleTrainingResult: 训练结果
        """
        start_time = datetime.now()
        self.logger.info("=" * 60)
        if force_override:
            self.logger.info(f"开始强制覆盖训练 - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            self.logger.info(f"开始每日自动模型训练 - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 60)
        
        try:
            
            # 2. 检查数据新鲜度
            self.logger.info("\n🔍 检查数据新鲜度...")
            cities_to_train, cities_to_skip = self.check_data_freshness(force_override=force_override)
            
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
            
            # 3. 执行训练（只训练需要训练的城市）
            self.logger.info(f"\n🚀 开始训练 {len(cities_to_train)} 个城市...")
            training_results = train_cities(cities_to_train, force_override=force_override)
            
            # 4. 解析训练结果（合并预检查的跳过城市）
            successful_cities = training_results.get('successful', [])
            failed_cities = training_results.get('failed', [])
            skipped_cities_from_training = training_results.get('skipped', [])
            
            # 合并两种跳过的城市：预检查跳过 + 训练时跳过
            all_skipped_cities = cities_to_skip + skipped_cities_from_training
            
            # 5. 清理旧模型
            self.logger.info("\n🧹 清理旧模型文件...")
            cleanup_old_models(days_to_keep=7)
            
            # 6. 预计算今日预测数据
            if successful_cities:
                self.logger.info("\n🔮 开始预计算今日预测数据...")
                precompute_result = self._precompute_daily_predictions(successful_cities)
                self.logger.info(f"预计算完成: 成功{precompute_result['successful']}个城市, 失败{precompute_result['failed']}个城市")
            elif force_override:
                # 强制覆盖模式：即使没有新训练模型，也要重新预计算所有城市
                self.logger.info("\n🔮 强制覆盖模式：重新预计算所有城市...")
                all_cities = get_supported_cities()
                precompute_result = self._precompute_daily_predictions(all_cities)
                self.logger.info(f"强制预计算完成: 成功{precompute_result['successful']}个城市, 失败{precompute_result['failed']}个城市")
            else:
                self.logger.info("\n⏭️ 跳过预计算（无新训练模型）")
            
            # 7. 训练完成
            
            # 8. 生成结果
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            result = SimpleTrainingResult(
                timestamp=start_time.isoformat(),
                total_cities=len(get_supported_cities()),
                successful_cities=len(successful_cities),
                failed_cities=len(failed_cities),
                skipped_cities=len(all_skipped_cities),
                execution_time=execution_time,
                successful_city_list=successful_cities,
                failed_city_list=failed_cities,
                skipped_city_list=all_skipped_cities
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
    
    def _precompute_daily_predictions(self, cities: List[str]) -> Dict[str, int]:
        """
        预计算所有城市的24小时预测数据
        
        Args:
            cities (List[str]): 需要预计算的城市列表
            
        Returns:
            Dict[str, int]: 预计算结果统计 {'successful': int, 'failed': int}
        """
        from ml.src.predict import predict_for_web_api
        import pandas as pd
        
        predictions_cache = {}
        successful_count = 0
        failed_count = 0
        
        for city in cities:
            try:
                self.logger.info(f"  正在预计算 {city}...")
                
                # 执行预测
                predictions_df = predict_for_web_api(city, steps=24)
                
                # 格式化预测数据为API需要的格式
                formatted_data = self._format_predictions_for_api(predictions_df)
                predictions_cache[city] = formatted_data
                
                successful_count += 1
                self.logger.info(f"  ✅ {city} 预测数据已生成 (24小时)")
                
            except Exception as e:
                failed_count += 1
                self.logger.error(f"  ❌ {city} 预测失败: {str(e)}")
        
        # 保存预测缓存到文件
        if predictions_cache:
            self._save_predictions_cache(predictions_cache)
            self.logger.info(f"📁 预测缓存已保存 ({len(predictions_cache)} 个城市)")
        
        return {
            'successful': successful_count,
            'failed': failed_count
        }
    
    def _format_predictions_for_api(self, predictions_df) -> Dict:
        """
        将预测DataFrame格式化为API返回的JSON格式
        
        Args:
            predictions_df (pd.DataFrame): 预测结果DataFrame
            
        Returns:
            Dict: API格式的预测数据
        """
        import pandas as pd
        
        if predictions_df is None or predictions_df.empty:
            raise Exception("预测数据为空")
        
        # 提取24小时预测数据
        times = [pd.to_datetime(t).strftime("%H:%M") for t in predictions_df['observation_time'].tolist()[:24]]
        values = predictions_df['prediction'].tolist()[:24]
        low = predictions_df['lower_bound'].tolist()[:24]
        high = predictions_df['upper_bound'].tolist()[:24]
        
        current_value = values[0] if values else 0
        avg_value = sum(values) / len(values) if values else 0
        
        # 生成API格式数据
        formatted_data = {
            "updateTime": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "currentValue": round(current_value, 1),
            "avgValue": round(avg_value, 1),
            "times": times,
            "values": [round(v, 1) for v in values],
            "low": [round(l, 1) for l in low],
            "high": [round(h, 1) for h in high],
            "cached": True,  # 标记为缓存数据
            "cache_time": datetime.now().isoformat()
        }
        
        return formatted_data
    
    def _save_predictions_cache(self, predictions_cache: Dict):
        """
        保存预测缓存到文件
        
        Args:
            predictions_cache (Dict): 预测缓存数据
        """
        try:
            # 确保缓存目录存在
            cache_dir = os.path.join(os.getcwd(), 'data', 'predictions_cache')
            os.makedirs(cache_dir, exist_ok=True)
            
            # 生成文件名
            today_str = datetime.now().strftime('%Y%m%d')
            cache_file = os.path.join(cache_dir, f'daily_predictions_{today_str}.json')
            latest_cache_file = os.path.join(cache_dir, 'latest_predictions.json')
            
            # 添加元数据
            cache_data = {
                'generated_at': datetime.now().isoformat(),
                'date': today_str,
                'cities_count': len(predictions_cache),
                'predictions': predictions_cache
            }
            
            # 保存带日期的缓存文件
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            # 保存最新缓存文件（覆盖）
            with open(latest_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"缓存文件已保存:")
            self.logger.info(f"  - 日期版本: {cache_file}")
            self.logger.info(f"  - 最新版本: {latest_cache_file}")
            
        except Exception as e:
            self.logger.error(f"保存预测缓存失败: {str(e)}")
    
    def load_predictions_cache(self, date_str: str = None) -> Optional[Dict]:
        """
        加载预测缓存数据
        
        Args:
            date_str (str): 日期字符串 (YYYYMMDD)，默认为今天
            
        Returns:
            Optional[Dict]: 缓存数据，如果不存在返回None
        """
        try:
            cache_dir = os.path.join(os.getcwd(), 'data', 'predictions_cache')
            
            if date_str is None:
                # 加载最新缓存
                cache_file = os.path.join(cache_dir, 'latest_predictions.json')
            else:
                # 加载指定日期缓存
                cache_file = os.path.join(cache_dir, f'daily_predictions_{date_str}.json')
            
            if not os.path.exists(cache_file):
                self.logger.warning(f"缓存文件不存在: {cache_file}")
                return None
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            self.logger.info(f"已加载预测缓存: {cache_file}")
            return cache_data
            
        except Exception as e:
            self.logger.error(f"加载预测缓存失败: {str(e)}")
            return None


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