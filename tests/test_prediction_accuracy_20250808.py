#!/usr/bin/env python3
"""
预测准确性测试脚本

测试改进后的NC-CQR算法（固定随机种子）对预测结果一致性和准确性的影响。
模拟预测流程：
1. 使用固定的历史数据训练模型
2. 基于训练好的模型预测全天24小时的NO2浓度
3. 与真实观测数据进行对比分析
4. 计算预测区间覆盖率，评估模型准确性
"""
import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.session import get_db_session
from database.crud import CITY_MODEL_MAP, get_no2_records
from ml.src.data_loader import load_data_from_mysql
from ml.src.data_processing import prepare_nc_cqr_data
from ml.src.train import train_full_pipeline, QuantileNet
from ml.src.predict import predict_future_nc_cqr
from ml.src.reproducibility import set_deterministic_seeds


class PredictionAccuracyTest:
    """预测准确性测试类"""
    
    def __init__(self):
        """初始化测试环境"""
        self.test_date = datetime(2025, 8, 9)  # 预测当天
        self.cutoff_date = datetime(2025, 8, 8, 23, 59, 59)  # 数据截止时间
        self.test_results = {}
        self.city_names_cn = {
            'guangzhou': '广州', 'shenzhen': '深圳', 'zhuhai': '珠海',
            'foshan': '佛山', 'huizhou': '惠州', 'dongguan': '东莞',
            'zhongshan': '中山', 'jiangmen': '江门', 'zhaoqing': '肇庆',
            'hongkong': '香港', 'macao': '澳门'
        }
        
        print(f"=" * 60)
        print(f"预测准确性测试")
        print(f"测试目标：验证修复随机种子后的预测一致性和准确性")
        print(f"数据截止时间：{self.cutoff_date}")
        print(f"预测目标日期：{self.test_date.strftime('%Y-%m-%d')}")
        print(f"=" * 60)

    def load_historical_data_until_date(self, city: str, cutoff_date: datetime) -> pd.DataFrame:
        """
        加载截止到指定日期的历史数据
        
        Args:
            city (str): 城市英文名
            cutoff_date (datetime): 截止日期
            
        Returns:
            pd.DataFrame: 截止日期前的历史数据
        """
        print(f"  加载{city}截止至{cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}的历史数据...")
        
        # 加载数据库中的所有历史数据
        all_data = load_data_from_mysql(city)
        
        # 过滤截止日期之前的数据
        all_data['observation_time'] = pd.to_datetime(all_data['observation_time'])
        historical_data = all_data[all_data['observation_time'] <= cutoff_date].copy()
        
        print(f"  - 总数据量: {len(all_data)} 条")
        print(f"  - 截止日期前数据量: {len(historical_data)} 条")
        
        if len(historical_data) < 100:  # 确保有足够的训练数据
            raise ValueError(f"城市 {city} 的历史数据不足（少于100条），无法进行模型训练")
            
        return historical_data

    def load_ground_truth_data(self, city: str, target_date: datetime) -> pd.DataFrame:
        """
        加载指定日期的真实观测数据
        
        Args:
            city (str): 城市英文名
            target_date (datetime): 目标日期
            
        Returns:
            pd.DataFrame: 目标日期的真实观测数据
        """
        print(f"  加载{city}在{target_date.strftime('%Y-%m-%d')}的真实观测数据...")
        
        city_cn = self.city_names_cn[city]
        
        # 查询目标日期的观测数据
        start_time = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
        
        ground_truth_data = []
        
        with get_db_session() as db:
            if db is None:
                raise RuntimeError("数据库连接失败")
                
            model_class = CITY_MODEL_MAP[city_cn]
            
            # 查询目标日期的所有数据
            ground_truth = db.query(model_class).filter(
                model_class.observation_time >= start_time,
                model_class.observation_time < end_time
            ).order_by(model_class.observation_time).all()
            
            # 在会话内完成数据转换，避免会话关闭后访问ORM对象
            for record in ground_truth:
                ground_truth_data.append({
                    'observation_time': record.observation_time,
                    'no2_concentration': record.no2_concentration,
                    'temperature': record.temperature,
                    'humidity': record.humidity,
                    'wind_speed': record.wind_speed,
                    'wind_direction': record.wind_direction,
                    'pressure': record.pressure
                })
        
        if not ground_truth_data:
            raise ValueError(f"未找到城市 {city} 在 {target_date.strftime('%Y-%m-%d')} 的观测数据")
        
        df = pd.DataFrame(ground_truth_data)
        print(f"  - 找到 {len(df)} 条真实观测记录")
        
        return df

    def train_model_with_historical_data(self, city: str, historical_data: pd.DataFrame) -> Tuple:
        """
        使用历史数据训练NC-CQR模型
        
        Args:
            city (str): 城市英文名
            historical_data (pd.DataFrame): 历史训练数据
            
        Returns:
            Tuple: (model, Q, scalers, training_summary)
        """
        print(f"  使用历史数据训练{city}的NC-CQR模型...")
        
        # 使用城市特定的确定性种子（关键修复）
        from ml.src.reproducibility import get_city_seed
        city_seed = get_city_seed(city)
        set_deterministic_seeds(city_seed, ensure_deterministic=True)
        print(f"  - 使用城市{city}专用种子: {city_seed}")
        
        try:
            # 创建临时的数据加载器函数，只返回历史数据
            def temp_load_data_from_mysql(city_name):
                return historical_data.copy()
            
            # 临时替换数据加载器
            import ml.src.train
            original_load_func = ml.src.train.load_data_from_mysql
            ml.src.train.load_data_from_mysql = temp_load_data_from_mysql
            
            try:
                # 使用完整训练管道
                model, Q, scalers, eval_results = train_full_pipeline(
                    city=city,
                    train_ratio=0.6,   # 训练集比例
                    calib_ratio=0.3,   # 校准集比例  
                    test_ratio=0.1,    # 测试集比例
                    epochs=150         # 减少训练轮数加快测试
                )
                
                train_loss = eval_results.get('train_loss', 'N/A')
                val_loss = eval_results.get('val_loss', 'N/A')
                coverage_rate = eval_results.get('coverage_rate', 'N/A')
                
            finally:
                # 恢复原始数据加载器
                ml.src.train.load_data_from_mysql = original_load_func
            
            training_summary = {
                'city': city,
                'data_size': len(historical_data),
                'feature_count': 'N/A',  # 特征数量由训练管道内部计算
                'train_loss': train_loss,
                'val_loss': val_loss,
                'coverage_rate': coverage_rate,
                'Q_value': Q
            }
            
            print(f"  - 模型训练完成")
            print(f"    * 训练损失: {train_loss}")
            print(f"    * 验证损失: {val_loss}")
            print(f"    * Q值: {Q:.4f}")
            print(f"    * 验证覆盖率: {coverage_rate}")
            
            return model, Q, scalers, training_summary
            
        except Exception as e:
            print(f"  - 训练失败: {str(e)}")
            raise

    def predict_with_fixed_seed(self, model, historical_data: pd.DataFrame, scalers: Dict, Q: float, city: str) -> pd.DataFrame:
        """
        使用固定随机种子进行预测
        
        Args:
            model: 训练好的模型
            historical_data (pd.DataFrame): 历史数据
            scalers (Dict): 标准化器
            Q (float): 校准值
            city (str): 城市名
            
        Returns:
            pd.DataFrame: 预测结果
        """
        print(f"  使用固定随机种子预测{city}的24小时NO2浓度...")
        
        # 使用基于城市名称和日期的固定种子（确定性修复）
        from ml.src.reproducibility import get_city_seed
        seed_base = get_city_seed(city) + int(self.test_date.strftime('%Y%m%d')) % 1000
        
        try:
            predictions = predict_future_nc_cqr(
                model=model,
                last_data=historical_data,
                scalers=scalers,
                Q=Q,
                steps=24,
                random_seed=seed_base  # 使用固定种子确保可重现性
            )
            
            print(f"  - 预测完成，生成24个时间点的预测值")
            print(f"  - 使用随机种子: {seed_base}")
            
            return predictions
            
        except Exception as e:
            print(f"  - 预测失败: {str(e)}")
            raise

    def calculate_prediction_metrics(self, predictions: pd.DataFrame, ground_truth: pd.DataFrame, city: str) -> Dict:
        """
        计算预测准确性指标
        
        Args:
            predictions (pd.DataFrame): 预测结果
            ground_truth (pd.DataFrame): 真实观测数据
            city (str): 城市名
            
        Returns:
            Dict: 包含各种准确性指标的字典
        """
        print(f"  计算{city}预测准确性指标...")
        
        # 确保时间列是datetime类型
        predictions['observation_time'] = pd.to_datetime(predictions['observation_time'])
        ground_truth['observation_time'] = pd.to_datetime(ground_truth['observation_time'])
        
        # 按时间合并数据（内连接，只保留两边都有的时间点）
        merged = pd.merge(
            predictions, ground_truth, 
            on='observation_time', 
            how='inner',
            suffixes=('_pred', '_actual')
        )
        
        if len(merged) == 0:
            print(f"  - 警告：预测数据与真实数据时间不匹配，无法计算指标")
            return {
                'city': city,
                'matched_hours': 0,
                'error': '时间不匹配'
            }
        
        print(f"  - 匹配到 {len(merged)} 个时间点的数据")
        
        # 计算各种指标
        pred_values = merged['prediction']
        actual_values = merged['no2_concentration']
        lower_bounds = merged['lower_bound']
        upper_bounds = merged['upper_bound']
        
        # 1. 基本误差指标
        mae = np.mean(np.abs(pred_values - actual_values))
        mse = np.mean((pred_values - actual_values) ** 2)
        rmse = np.sqrt(mse)
        mape = np.mean(np.abs((actual_values - pred_values) / actual_values)) * 100
        
        # 2. 预测区间覆盖率（最重要的指标）
        coverage_count = np.sum((actual_values >= lower_bounds) & (actual_values <= upper_bounds))
        coverage_rate = coverage_count / len(merged)
        
        # 3. 区间宽度分析
        interval_widths = upper_bounds - lower_bounds
        avg_interval_width = np.mean(interval_widths)
        std_interval_width = np.std(interval_widths)
        
        # 4. 相关性
        correlation = np.corrcoef(pred_values, actual_values)[0, 1]
        
        # 5. 统计信息
        pred_mean = np.mean(pred_values)
        actual_mean = np.mean(actual_values)
        pred_std = np.std(pred_values)
        actual_std = np.std(actual_values)
        
        metrics = {
            'city': city,
            'matched_hours': len(merged),
            'mae': round(mae, 3),
            'mse': round(mse, 3),
            'rmse': round(rmse, 3),
            'mape': round(mape, 2),
            'coverage_rate': round(coverage_rate, 4),
            'coverage_count': int(coverage_count),
            'avg_interval_width': round(avg_interval_width, 3),
            'std_interval_width': round(std_interval_width, 3),
            'correlation': round(correlation, 4),
            'pred_mean': round(pred_mean, 3),
            'actual_mean': round(actual_mean, 3),
            'pred_std': round(pred_std, 3),
            'actual_std': round(actual_std, 3),
            'prediction_data': merged[['observation_time', 'prediction', 'lower_bound', 'upper_bound']].to_dict('records'),
            'actual_data': merged[['observation_time', 'no2_concentration']].to_dict('records')
        }
        
        print(f"  - 平均绝对误差 (MAE): {mae:.3f}")
        print(f"  - 均方根误差 (RMSE): {rmse:.3f}")
        print(f"  - 平均绝对百分比误差 (MAPE): {mape:.2f}%")
        print(f"  - 预测区间覆盖率: {coverage_rate:.1%} ({coverage_count}/{len(merged)})")
        print(f"  - 平均区间宽度: {avg_interval_width:.3f}")
        print(f"  - 相关性: {correlation:.4f}")
        
        return metrics

    def test_single_city(self, city: str) -> Dict:
        """
        测试单个城市的预测准确性
        
        Args:
            city (str): 城市英文名
            
        Returns:
            Dict: 测试结果
        """
        print(f"\n{'='*20} 测试城市: {city.upper()} ({'='*20}")
        
        try:
            # 1. 加载历史数据
            historical_data = self.load_historical_data_until_date(city, self.cutoff_date)
            
            # 2. 训练模型
            model, Q, scalers, training_summary = self.train_model_with_historical_data(city, historical_data)
            
            # 3. 使用固定种子进行预测
            predictions = self.predict_with_fixed_seed(model, historical_data, scalers, Q, city)
            
            # 4. 加载真实观测数据
            ground_truth = self.load_ground_truth_data(city, self.test_date)
            
            # 5. 计算预测准确性指标
            metrics = self.calculate_prediction_metrics(predictions, ground_truth, city)
            
            # 6. 整合测试结果
            result = {
                'city': city,
                'success': True,
                'training_summary': training_summary,
                'prediction_metrics': metrics,
                'error': None
            }
            
            print(f"[成功] {city} 测试完成")
            return result
            
        except Exception as e:
            error_msg = f"测试失败: {str(e)}"
            print(f"[失败] {city} {error_msg}")
            
            result = {
                'city': city,
                'success': False,
                'training_summary': None,
                'prediction_metrics': None,
                'error': error_msg
            }
            
            return result

    def run_all_cities_test(self) -> Dict:
        """
        运行所有城市的测试
        
        Returns:
            Dict: 所有城市的测试结果汇总
        """
        print(f"开始运行所有城市的预测准确性测试...")
        print(f"[一致性检查] 使用固定时间戳种子确保可重现性")
        
        all_results = {
            'test_info': {
                'test_date': self.test_date.isoformat(),
                'cutoff_date': self.cutoff_date.isoformat(),
                'test_time': datetime.now().isoformat(),
                'algorithm_version': 'NC-CQR with fixed random seed'
            },
            'city_results': {},
            'summary': {
                'total_cities': len(self.city_names_cn),
                'successful_cities': 0,
                'failed_cities': 0,
                'avg_coverage_rate': 0,
                'cities_above_75_coverage': 0
            }
        }
        
        successful_results = []
        
        # 逐个测试城市
        for city in self.city_names_cn.keys():
            try:
                result = self.test_single_city(city)
                all_results['city_results'][city] = result
                
                if result['success']:
                    all_results['summary']['successful_cities'] += 1
                    successful_results.append(result)
                else:
                    all_results['summary']['failed_cities'] += 1
                    
            except KeyboardInterrupt:
                print(f"\\n测试被用户中断")
                break
            except Exception as e:
                print(f"\\n测试城市 {city} 时发生未预期错误: {e}")
                all_results['city_results'][city] = {
                    'city': city,
                    'success': False,
                    'error': f"未预期错误: {str(e)}"
                }
                all_results['summary']['failed_cities'] += 1
        
        # 计算整体统计
        if successful_results:
            coverage_rates = []
            cities_above_75 = 0
            
            for result in successful_results:
                coverage_rate = result['prediction_metrics']['coverage_rate']
                coverage_rates.append(coverage_rate)
                
                if coverage_rate >= 0.75:
                    cities_above_75 += 1
            
            all_results['summary']['avg_coverage_rate'] = round(np.mean(coverage_rates), 4)
            all_results['summary']['cities_above_75_coverage'] = cities_above_75
        
        # 打印汇总报告
        self.print_summary_report(all_results)
        
        return all_results

    def print_summary_report(self, all_results: Dict):
        """
        打印测试汇总报告
        
        Args:
            all_results (Dict): 所有测试结果
        """
        print(f"\\n{'='*60}")
        print(f"测试汇总报告")
        print(f"{'='*60}")
        
        summary = all_results['summary']
        print(f"总测试城市数: {summary['total_cities']}")
        print(f"成功测试城市数: {summary['successful_cities']}")
        print(f"失败测试城市数: {summary['failed_cities']}")
        
        if summary['successful_cities'] > 0:
            print(f"平均预测区间覆盖率: {summary['avg_coverage_rate']:.1%}")
            print(f"达到75%+覆盖率的城市数: {summary['cities_above_75_coverage']}")
            
            print(f"\\n各城市详细结果:")
            print(f"{'城市':<10} {'覆盖率':<8} {'MAE':<8} {'RMSE':<8} {'相关性':<8}")
            print(f"{'-'*50}")
            
            for city, result in all_results['city_results'].items():
                if result['success']:
                    metrics = result['prediction_metrics']
                    print(f"{city:<10} {metrics['coverage_rate']:.1%}    {metrics['mae']:<7.3f} {metrics['rmse']:<7.3f} {metrics['correlation']:<7.4f}")
                else:
                    print(f"{city:<10} 失败     -       -       -")
        
        print(f"\\n测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def save_results(self, all_results: Dict, output_file: str = None):
        """
        保存测试结果到JSON文件
        
        Args:
            all_results (Dict): 测试结果
            output_file (str): 输出文件路径
        """
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"prediction_accuracy_test_{timestamp}.json"
        
        output_path = os.path.join(os.path.dirname(__file__), output_file)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
                
            print(f"\\n测试结果已保存到: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"\\n保存测试结果失败: {e}")
            return None


def main():
    """主函数"""
    try:
        # 创建测试实例
        test_runner = PredictionAccuracyTest()
        
        # 运行测试
        results = test_runner.run_all_cities_test()
        
        # 保存结果
        test_runner.save_results(results)
        
        print(f"\\n[完成] 预测准确性测试全部完成！")
        
        # 返回结果用于进一步分析
        return results
        
    except KeyboardInterrupt:
        print(f"\\n[中断] 测试被用户中断")
        return None
    except Exception as e:
        print(f"\\n[错误] 测试过程中发生错误: {e}")
        return None


if __name__ == "__main__":
    main()