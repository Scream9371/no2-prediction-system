"""
每日数据更新器

实现智能的增量数据采集机制，每日自动从和风天气API获取最新的NO2监测数据。

主要功能：
- 增量数据采集：只获取缺失的数据，避免重复
- 数据质量检查：确保数据准确性和完整性
- 错误处理和重试：提高系统可靠性
- 监控和日志：便于运维和故障排查
"""

import sys
import os
import logging
import time
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional, Tuple
import traceback

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.heweather.client import HeWeatherClient
from api.heweather.data_parser import parse_combined_data
from database.crud import create_no2_record, CITY_MODEL_MAP
from database.session import get_db
from utils.data_validator import data_validator, ValidationResult
from config.schedule_config import schedule_config

class DailyUpdater:
    """每日数据更新器"""
    
    def __init__(self):
        self.config = schedule_config
        self.client = HeWeatherClient()
        self.logger = self._setup_logger()
        self.execution_stats = {
            'start_time': None,
            'end_time': None,
            'total_cities': len(self.config.CITIES),
            'processed_cities': 0,
            'successful_cities': 0,
            'failed_cities': 0,
            'total_records': 0,
            'errors': []
        }
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志配置"""
        logger = logging.getLogger('daily_updater')
        logger.setLevel(getattr(logging, self.config.LOG_CONFIG['level']))
        
        # 避免重复添加处理器
        if logger.handlers:
            return logger
        
        # 文件处理器
        file_handler = logging.FileHandler(
            self.config.get_log_file_path(), 
            encoding='utf-8'
        )
        file_handler.setFormatter(
            logging.Formatter(self.config.LOG_CONFIG['format'])
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter(self.config.LOG_CONFIG['format'])
        )
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def get_latest_record_time(self, city_name: str) -> Optional[datetime]:
        """获取指定城市最新的记录时间"""
        try:
            db = next(get_db())
            model_class = CITY_MODEL_MAP[city_name]
            
            latest_record = db.query(model_class).order_by(
                model_class.observation_time.desc()
            ).first()
            
            db.close()
            return latest_record.observation_time if latest_record else None
            
        except Exception as e:
            self.logger.error(f"获取{city_name}最新记录时间失败: {str(e)}")
            return None
    
    def calculate_missing_dates(self, city_name: str) -> List[str]:
        """
        计算需要采集的缺失日期
        
        Args:
            city_name: 城市名称
            
        Returns:
            需要采集的日期列表 (YYYYMMDD格式)
        """
        try:
            latest_time = self.get_latest_record_time(city_name)
            yesterday = datetime.now() - timedelta(days=1)
            
            if not latest_time:
                # 如果没有历史数据，获取过去10天
                start_date = yesterday - timedelta(days=9)
                self.logger.info(f"{city_name}无历史数据，将采集过去10天的数据")
            else:
                # 从最新记录的下一天开始
                start_date = latest_time + timedelta(days=1)
                self.logger.info(f"{city_name}最新数据时间: {latest_time}, 从{start_date.date()}开始更新")
            
            missing_dates = []
            current_date = start_date.date()
            
            while current_date <= yesterday.date():
                missing_dates.append(current_date.strftime('%Y%m%d'))
                current_date += timedelta(days=1)
            
            return missing_dates
            
        except Exception as e:
            self.logger.error(f"计算{city_name}缺失日期失败: {str(e)}")
            return []
    
    def process_date_data(self, city_id: str, city_name: str, date_str: str) -> Tuple[int, List[str]]:
        """
        处理指定日期的数据
        
        Args:
            city_id: 城市ID
            city_name: 城市名称  
            date_str: 日期字符串 (YYYYMMDD)
            
        Returns:
            tuple: (成功保存的记录数, 错误信息列表)
        """
        errors = []
        records_saved = 0
        
        try:
            # 获取API数据
            self.logger.info(f"获取{city_name} {date_str}的API数据...")
            
            air_data = self.client.get_historical_air(city_id, date_str)
            if not air_data:
                errors.append(f"获取{date_str}空气质量数据失败")
                return 0, errors
            
            weather_data = self.client.get_historical_weather(city_id, date_str)
            if not weather_data:
                errors.append(f"获取{date_str}天气数据失败")
                return 0, errors
            
            # 解析数据
            parsed_data_list = parse_combined_data(
                air_data, weather_data, city_id, city_name, date_str
            )
            
            if not parsed_data_list:
                errors.append(f"解析{date_str}数据失败")
                return 0, errors
            
            # 数据质量检查
            validation_results, stats = data_validator.validate_batch_records(parsed_data_list)
            
            # 记录数据质量信息
            self.logger.info(
                f"{city_name} {date_str}数据质量: "
                f"总数{stats['total']}, 有效{stats['valid']}, "
                f"平均质量分数{stats['avg_quality']:.3f}"
            )
            
            # 保存有效数据
            db = next(get_db())
            try:
                for i, (record_data, validation_result) in enumerate(
                    zip(parsed_data_list, validation_results)
                ):
                    if validation_result.is_valid:
                        try:
                            create_no2_record(db, record_data, city_name)
                            records_saved += 1
                        except Exception as save_error:
                            errors.append(f"保存第{i+1}条记录失败: {str(save_error)}")
                    else:
                        errors.extend(validation_result.errors)
                        self.logger.warning(f"跳过无效记录: {'; '.join(validation_result.errors)}")
                
                db.commit()
                self.logger.info(f"成功保存{city_name} {date_str}的{records_saved}条记录")
                
            except Exception as db_error:
                db.rollback()
                errors.append(f"数据库操作失败: {str(db_error)}")
            finally:
                db.close()
            
            # API调用间隔
            time.sleep(self.config.API_REQUEST_DELAY)
            
        except Exception as e:
            errors.append(f"处理{date_str}数据时发生异常: {str(e)}")
            self.logger.error(f"处理{city_name} {date_str}数据异常: {str(e)}")
            self.logger.error(traceback.format_exc())
        
        return records_saved, errors
    
    def collect_incremental_data(self, city_name: str) -> Dict[str, Any]:
        """
        为指定城市执行增量数据采集
        
        Args:
            city_name: 城市名称
            
        Returns:
            采集结果字典
        """
        result = {
            'city': city_name,
            'success': False,
            'dates_processed': 0,
            'records_added': 0,
            'errors': [],
            'execution_time': 0
        }
        
        start_time = time.time()
        
        try:
            self.logger.info(f"开始处理{city_name}的增量数据更新...")
            
            # 获取城市ID
            city_id = self.client.get_city_id(city_name)
            if not city_id:
                result['errors'].append(f"无法获取城市{city_name}的ID")
                return result
            
            # 计算缺失日期
            missing_dates = self.calculate_missing_dates(city_name)
            
            if not missing_dates:
                result['message'] = '数据已是最新，无需更新'
                result['success'] = True
                self.logger.info(f"{city_name}数据已是最新，跳过更新")
                return result
            
            self.logger.info(f"{city_name}需要更新{len(missing_dates)}天的数据: {missing_dates}")
            
            # 逐日处理数据
            for date_str in missing_dates:
                records_count, date_errors = self.process_date_data(city_id, city_name, date_str)
                
                result['records_added'] += records_count
                result['dates_processed'] += 1
                result['errors'].extend(date_errors)
                
                if date_errors:
                    self.logger.warning(f"{city_name} {date_str}处理有错误: {'; '.join(date_errors)}")
            
            # 判断总体成功性
            if result['dates_processed'] > 0:
                success_rate = (result['dates_processed'] - len([e for e in result['errors'] if '失败' in e])) / result['dates_processed']
                result['success'] = success_rate >= 0.8  # 80%以上成功率认为成功
                result['message'] = f"处理{result['dates_processed']}天数据，新增{result['records_added']}条记录"
            
        except Exception as e:
            result['errors'].append(f"城市{city_name}处理异常: {str(e)}")
            self.logger.error(f"处理{city_name}时发生异常: {str(e)}")
            self.logger.error(traceback.format_exc())
        
        result['execution_time'] = time.time() - start_time
        return result
    
    def run_daily_update(self) -> Dict[str, Any]:
        """
        执行每日数据更新任务
        
        Returns:
            执行结果字典
        """
        self.execution_stats['start_time'] = datetime.now()
        self.logger.info("=" * 60)
        self.logger.info(f"开始执行每日数据更新任务 - {self.execution_stats['start_time']}")
        self.logger.info("=" * 60)
        
        city_results = []
        
        try:
            # 逐个处理城市
            for city_name in self.config.CITIES:
                self.execution_stats['processed_cities'] += 1
                
                try:
                    result = self.collect_incremental_data(city_name)
                    city_results.append(result)
                    
                    if result['success']:
                        self.execution_stats['successful_cities'] += 1
                        self.execution_stats['total_records'] += result['records_added']
                        self.logger.info(f"✅ {city_name}更新成功: {result.get('message', '')}")
                    else:
                        self.execution_stats['failed_cities'] += 1
                        self.logger.error(f"❌ {city_name}更新失败: {'; '.join(result['errors'])}")
                    
                except Exception as e:
                    self.execution_stats['failed_cities'] += 1
                    error_msg = f"处理{city_name}时发生异常: {str(e)}"
                    self.execution_stats['errors'].append(error_msg)
                    self.logger.error(error_msg)
                    self.logger.error(traceback.format_exc())
        
        except Exception as e:
            error_msg = f"执行每日更新任务时发生异常: {str(e)}"
            self.execution_stats['errors'].append(error_msg)
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
        
        # 生成执行报告
        self.execution_stats['end_time'] = datetime.now()
        execution_report = self._generate_execution_report(city_results)
        
        # 记录执行总结
        self._log_execution_summary(execution_report)
        
        return execution_report
    
    def _generate_execution_report(self, city_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成执行报告"""
        execution_time = (
            self.execution_stats['end_time'] - self.execution_stats['start_time']
        ).total_seconds()
        
        success_rate = (
            self.execution_stats['successful_cities'] / 
            self.execution_stats['total_cities']
        ) if self.execution_stats['total_cities'] > 0 else 0
        
        return {
            'timestamp': self.execution_stats['end_time'].isoformat(),
            'execution_time_seconds': round(execution_time, 2),
            'summary': {
                'total_cities': self.execution_stats['total_cities'],
                'successful_cities': self.execution_stats['successful_cities'],
                'failed_cities': self.execution_stats['failed_cities'],
                'success_rate': round(success_rate, 3),
                'total_records_added': self.execution_stats['total_records']
            },
            'city_details': city_results,
            'system_errors': self.execution_stats['errors'],
            'performance': {
                'avg_time_per_city': round(
                    execution_time / self.execution_stats['processed_cities'], 2
                ) if self.execution_stats['processed_cities'] > 0 else 0,
                'records_per_second': round(
                    self.execution_stats['total_records'] / execution_time, 2
                ) if execution_time > 0 else 0
            },
            'recommendations': self._generate_recommendations(success_rate, city_results)
        }
    
    def _generate_recommendations(self, success_rate: float, 
                                city_results: List[Dict[str, Any]]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if success_rate < 0.9:
            recommendations.append("整体成功率较低，建议检查API连接和配置")
        
        # 检查连续失败的城市
        failed_cities = [r['city'] for r in city_results if not r.get('success', False)]
        if len(failed_cities) >= 3:
            recommendations.append(f"多个城市更新失败: {', '.join(failed_cities)}，建议检查和风天气API状态")
        
        # 检查执行时间
        total_time = sum(r.get('execution_time', 0) for r in city_results)
        if total_time > self.config.MONITORING['max_execution_time_minutes'] * 60:
            recommendations.append("执行时间过长，建议优化API调用频率或检查网络状况")
        
        return recommendations
    
    def _log_execution_summary(self, report: Dict[str, Any]):
        """记录执行总结"""
        summary = report['summary']
        
        self.logger.info("=" * 60)
        self.logger.info("每日数据更新任务执行完成")
        self.logger.info(f"执行时间: {report['execution_time_seconds']}秒")
        self.logger.info(f"城市总数: {summary['total_cities']}")
        self.logger.info(f"成功城市: {summary['successful_cities']}")
        self.logger.info(f"失败城市: {summary['failed_cities']}")
        self.logger.info(f"成功率: {summary['success_rate']:.1%}")
        self.logger.info(f"新增记录: {summary['total_records_added']}条")
        
        if report['system_errors']:
            self.logger.error("系统错误:")
            for error in report['system_errors']:
                self.logger.error(f"  - {error}")
        
        if report['recommendations']:
            self.logger.info("改进建议:")
            for rec in report['recommendations']:
                self.logger.info(f"  - {rec}")
        
        self.logger.info("=" * 60)

def main():
    """主函数 - 执行每日数据更新"""
    try:
        updater = DailyUpdater()
        result = updater.run_daily_update()
        
        # 返回适当的退出码
        success_rate = result['summary']['success_rate']
        if success_rate >= 0.8:
            sys.exit(0)  # 成功
        else:
            sys.exit(1)  # 失败
            
    except Exception as e:
        print(f"每日数据更新器启动失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()