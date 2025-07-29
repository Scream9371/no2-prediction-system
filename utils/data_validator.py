"""
数据质量检查器

负责验证从和风天气API获取的数据质量，确保数据准确性和完整性
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from config.schedule_config import schedule_config

# 配置日志
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """数据验证结果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    quality_score: float  # 0-1之间，1表示完美质量

class DataValidator:
    """数据质量检查器"""
    
    def __init__(self):
        self.thresholds = schedule_config.DATA_QUALITY_THRESHOLDS
    
    def validate_record(self, record_data: Dict[str, Any]) -> ValidationResult:
        """
        验证单条记录的数据质量
        
        Args:
            record_data: 包含NO2记录数据的字典
            
        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []
        
        # 1. 必需字段检查
        required_fields = [
            'observation_time', 'no2_concentration', 'temperature', 
            'humidity', 'wind_speed', 'wind_direction', 'pressure'
        ]
        
        for field in required_fields:
            if field not in record_data:
                errors.append(f"缺少必需字段: {field}")
            elif record_data[field] is None:
                errors.append(f"字段值为空: {field}")
        
        if errors:
            return ValidationResult(
                is_valid=False, 
                errors=errors, 
                warnings=warnings, 
                quality_score=0.0
            )
        
        # 2. 数据类型检查
        try:
            observation_time = record_data['observation_time']
            if not isinstance(observation_time, datetime):
                errors.append("observation_time必须是datetime类型")
            
            # 检查数值字段
            numeric_fields = ['no2_concentration', 'temperature', 'humidity', 
                            'wind_speed', 'wind_direction', 'pressure']
            
            for field in numeric_fields:
                try:
                    float(record_data[field])
                except (ValueError, TypeError):
                    errors.append(f"字段{field}不是有效的数值")
                    
        except Exception as e:
            errors.append(f"数据类型检查失败: {str(e)}")
        
        # 3. 数值范围检查
        quality_issues = 0
        total_checks = len(self.thresholds)
        
        for field, threshold in self.thresholds.items():
            if field in record_data:
                try:
                    value = float(record_data[field])
                    if not (threshold['min'] <= value <= threshold['max']):
                        errors.append(
                            f"{field}值{value}{threshold['unit']}超出合理范围"
                            f"[{threshold['min']}-{threshold['max']}]{threshold['unit']}"
                        )
                        quality_issues += 1
                except (ValueError, TypeError):
                    quality_issues += 1
        
        # 4. 时间合理性检查
        if 'observation_time' in record_data:
            obs_time = record_data['observation_time']
            now = datetime.now()
            
            # 处理时区问题：统一为naive datetime进行比较
            if hasattr(obs_time, 'tzinfo') and obs_time.tzinfo is not None:
                obs_time = obs_time.replace(tzinfo=None)
            
            # 检查时间是否在过去10天内
            if obs_time > now:
                errors.append("观测时间不能是未来时间")
            elif (now - obs_time).days > 10:
                warnings.append("观测时间超过10天前，可能是历史数据")
        
        # 5. 数据一致性检查
        self._check_data_consistency(record_data, warnings)
        
        # 计算质量分数
        quality_score = max(0.0, 1.0 - (quality_issues / total_checks))
        if warnings:
            quality_score *= 0.9  # 有警告时降低质量分数
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            quality_score=quality_score
        )
    
    def validate_batch_records(self, records: List[Dict[str, Any]]) -> Tuple[List[ValidationResult], Dict[str, Any]]:
        """
        批量验证记录数据质量
        
        Args:
            records: 记录数据列表
            
        Returns:
            tuple: (验证结果列表, 批量统计信息)
        """
        if not records:
            return [], {'total': 0, 'valid': 0, 'invalid': 0, 'avg_quality': 0.0}
        
        results = []
        valid_count = 0
        total_quality = 0.0
        
        for i, record in enumerate(records):
            try:
                result = self.validate_record(record)
                results.append(result)
                
                if result.is_valid:
                    valid_count += 1
                total_quality += result.quality_score
                
                # 记录严重错误
                if not result.is_valid:
                    logger.warning(f"记录{i+1}验证失败: {'; '.join(result.errors)}")
                    
            except Exception as e:
                error_result = ValidationResult(
                    is_valid=False,
                    errors=[f"验证过程异常: {str(e)}"],
                    warnings=[],
                    quality_score=0.0
                )
                results.append(error_result)
                logger.error(f"验证记录{i+1}时发生异常: {str(e)}")
        
        # 时间连续性检查
        continuity_issues = self._check_time_continuity(records)
        if continuity_issues:
            logger.warning(f"时间连续性问题: {'; '.join(continuity_issues)}")
        
        # 统计信息
        stats = {
            'total': len(records),
            'valid': valid_count,
            'invalid': len(records) - valid_count,
            'avg_quality': total_quality / len(records) if records else 0.0,
            'continuity_issues': continuity_issues
        }
        
        return results, stats
    
    def _check_data_consistency(self, record_data: Dict[str, Any], warnings: List[str]):
        """检查数据一致性"""
        try:
            # 温度和湿度的合理性检查
            temp = float(record_data.get('temperature', 0))
            humidity = float(record_data.get('humidity', 0))
            
            # 极端高温但高湿度的情况（不太合理）
            if temp > 35 and humidity > 80:
                warnings.append("高温高湿的组合可能不太合理")
            
            # 极端低温但低湿度的情况
            if temp < 0 and humidity < 10:
                warnings.append("低温低湿的组合可能不太合理")
            
            # 风速和风向的一致性
            wind_speed = float(record_data.get('wind_speed', 0))
            wind_direction = float(record_data.get('wind_direction', 0))
            
            # 无风但有风向的情况
            if wind_speed < 1 and wind_direction > 0:
                warnings.append("无风状态下不应有风向数据")
                
        except (ValueError, TypeError):
            # 如果数据类型转换失败，跳过一致性检查
            pass
    
    def _check_time_continuity(self, records: List[Dict[str, Any]]) -> List[str]:
        """检查时间序列的连续性"""
        issues = []
        
        if len(records) < 2:
            return issues
        
        try:
            # 按时间排序
            sorted_records = sorted(records, key=lambda x: x['observation_time'])
            
            for i in range(1, len(sorted_records)):
                prev_time = sorted_records[i-1]['observation_time']
                curr_time = sorted_records[i]['observation_time']
                
                # 检查时间间隔（期望是1小时）
                time_diff = curr_time - prev_time
                expected_interval = timedelta(hours=1)
                
                if time_diff != expected_interval:
                    if time_diff > expected_interval:
                        issues.append(f"时间间隔过大: {prev_time} 到 {curr_time}")
                    elif time_diff < expected_interval:
                        issues.append(f"时间间隔过小: {prev_time} 到 {curr_time}")
                        
        except Exception as e:
            issues.append(f"时间连续性检查异常: {str(e)}")
        
        return issues
    
    def generate_quality_report(self, validation_results: List[ValidationResult], 
                              stats: Dict[str, Any], city_name: str) -> Dict[str, Any]:
        """
        生成数据质量报告
        
        Args:
            validation_results: 验证结果列表
            stats: 批量统计信息
            city_name: 城市名称
            
        Returns:
            质量报告字典
        """
        return {
            'city_name': city_name,
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_records': stats['total'],
                'valid_records': stats['valid'],
                'invalid_records': stats['invalid'],
                'success_rate': stats['valid'] / stats['total'] if stats['total'] > 0 else 0,
                'average_quality_score': round(stats['avg_quality'], 3)
            },
            'quality_distribution': self._calculate_quality_distribution(validation_results),
            'common_errors': self._get_common_errors(validation_results),
            'continuity_issues': stats.get('continuity_issues', []),
            'recommendation': self._generate_recommendations(stats, validation_results)
        }
    
    def _calculate_quality_distribution(self, results: List[ValidationResult]) -> Dict[str, int]:
        """计算质量分布"""
        distribution = {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0}
        
        for result in results:
            score = result.quality_score
            if score >= 0.9:
                distribution['excellent'] += 1
            elif score >= 0.7:
                distribution['good'] += 1
            elif score >= 0.5:
                distribution['fair'] += 1
            else:
                distribution['poor'] += 1
        
        return distribution
    
    def _get_common_errors(self, results: List[ValidationResult]) -> List[str]:
        """获取常见错误"""
        error_counts = {}
        
        for result in results:
            for error in result.errors:
                error_counts[error] = error_counts.get(error, 0) + 1
        
        # 返回出现频率最高的前5个错误
        return sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    def _generate_recommendations(self, stats: Dict[str, Any], 
                                results: List[ValidationResult]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        success_rate = stats['valid'] / stats['total'] if stats['total'] > 0 else 0
        avg_quality = stats['avg_quality']
        
        if success_rate < 0.9:
            recommendations.append("数据验证成功率较低，建议检查数据源质量")
        
        if avg_quality < 0.7:
            recommendations.append("平均质量分数较低，建议加强数据预处理")
        
        if stats.get('continuity_issues'):
            recommendations.append("存在时间连续性问题，建议检查数据采集间隔")
        
        # 检查是否有特定类型的错误模式
        error_patterns = self._analyze_error_patterns(results)
        recommendations.extend(error_patterns)
        
        return recommendations
    
    def _analyze_error_patterns(self, results: List[ValidationResult]) -> List[str]:
        """分析错误模式"""
        patterns = []
        
        # 分析温度相关错误
        temp_errors = sum(1 for r in results for e in r.errors if 'temperature' in e)
        if temp_errors > len(results) * 0.1:
            patterns.append("温度数据异常频繁，建议检查温度传感器")
        
        # 分析NO2浓度相关错误  
        no2_errors = sum(1 for r in results for e in r.errors if 'no2_concentration' in e)
        if no2_errors > len(results) * 0.1:
            patterns.append("NO2浓度数据异常频繁，建议检查空气质量监测设备")
        
        return patterns

# 创建全局验证器实例
data_validator = DataValidator()