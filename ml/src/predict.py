"""
NC-CQR预测模块 - 未来24小时NO2浓度预测
"""
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from datetime import timedelta
from typing import Tuple, Dict
import os
import matplotlib.pyplot as plt
from .train import QuantileNet, load_model
from .data_loader import get_latest_data
from .data_processing import load_scalers_for_pipeline, load_scalers_for_control


# 设置中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


def predict_future_nc_cqr(
    model: nn.Module,
    last_data: pd.DataFrame,
    scalers: Dict,
    Q: float,
    steps: int = 24
) -> pd.DataFrame:
    """
    使用NC-CQR模型预测未来步长的NO2浓度
    
    Args:
        model (nn.Module): 训练好的NC-CQR模型
        last_data (pd.DataFrame): 历史数据
        scalers (Dict): 标准化器字典
        Q (float): 校准量化值
        steps (int): 预测步数，默认24小时
        
    Returns:
        pd.DataFrame: 预测结果，包含时间、预测值、置信区间
    """
    device = next(model.parameters()).device
    predictions = []
    
    # 获取最近的历史数据用于特征构建
    history = last_data[['no2', 'temperature', 'humidity',
                         'wind_speed', 'pressure', 'wind_direction']].tail(2).copy()
    
    for i in range(steps):
        latest = history.iloc[-1]
        prev = history.iloc[-2]
        pred_time = last_data['observation_time'].iloc[-1] + timedelta(hours=i + 1)
        
        # 构建特征
        features = {
            'temperature': scalers['temperature'].transform([[latest['temperature']]])[0][0],
            'humidity': scalers['humidity'].transform([[latest['humidity']]])[0][0],
            'wind_speed': scalers['wind_speed'].transform([[latest['wind_speed']]])[0][0],
            'pressure': scalers['pressure'].transform([[latest['pressure']]])[0][0],
            'wind_sin': np.sin(np.radians(latest['wind_direction'])),
            'wind_cos': np.cos(np.radians(latest['wind_direction'])),
            'no2_lag1': latest['no2'],
            'no2_lag2': prev['no2'],
            'hour': pred_time.hour,
            'day_of_week': pred_time.dayofweek,
            'is_weekend': int(pred_time.dayofweek in [5, 6])
        }
        
        # 按训练时的特征顺序排列
        feature_order = [
            'temperature', 'humidity', 'wind_speed', 'pressure',
            'wind_sin', 'wind_cos',
            'no2_lag1', 'no2_lag2',
            'hour', 'day_of_week', 'is_weekend'
        ]
        X = np.array([features[col] for col in feature_order]).reshape(1, -1)
        
        # 模型预测
        with torch.no_grad():
            model.eval()
            X_tensor = torch.FloatTensor(X).to(device)
            lower_pred, upper_pred = model(X_tensor)
        
        # 应用保形预测校准
        lower_bound = lower_pred.item() - Q
        upper_bound = upper_pred.item() + Q
        mid_point = (lower_bound + upper_bound) / 2
        
        predictions.append({
            'observation_time': pred_time,
            'prediction': mid_point,
            'lower_bound': lower_bound,
            'upper_bound': upper_bound
        })
        
        # 更新历史数据，用于下一步预测
        new_row = {
            'no2': mid_point,
            'temperature': latest['temperature'],
            'humidity': latest['humidity'],
            'wind_speed': latest['wind_speed'],
            'pressure': latest['pressure'],
            'wind_direction': latest['wind_direction']
        }
        history = pd.concat([history.iloc[1:], pd.DataFrame([new_row])], ignore_index=True)
    
    return pd.DataFrame(predictions)


def predict_with_saved_model(
    city: str = 'dongguan',
    model_path: str = None,
    steps: int = 24
) -> pd.DataFrame:
    """
    使用已保存的模型进行预测
    
    Args:
        city (str): 城市名称
        model_path (str): 模型路径，如果为None则使用默认路径
        steps (int): 预测步数
        
    Returns:
        pd.DataFrame: 预测结果
    """
    # 确定模型路径（优先使用训练管道模型）
    if model_path is None:
        from config.paths import get_latest_model_path, get_control_model_path
        # 先尝试训练管道的最新模型
        pipeline_model_path = get_latest_model_path(city)
        if os.path.exists(pipeline_model_path):
            model_path = pipeline_model_path
            print(f"使用训练管道模型: {model_path}")
        else:
            # 如果训练管道模型不存在，检查控制脚本模型
            control_model_path = get_control_model_path(city)
            if os.path.exists(control_model_path):
                model_path = control_model_path
                print(f"使用控制脚本模型: {model_path}")
            else:
                # 两个模型都不存在
                raise FileNotFoundError(
                    f"城市 {city} 的模型文件不存在:\n"
                    f"  训练管道模型: {pipeline_model_path}\n"
                    f"  控制脚本模型: {control_model_path}\n"
                    f"请先运行训练管道 'python -m scripts.run_pipeline' 或控制脚本训练模式"
                )
    
    # 加载模型
    model, Q, scalers = load_model(model_path)
    
    # 获取数据库中所有数据（240小时）
    from .data_loader import load_data_from_mysql
    last_data = load_data_from_mysql(city)
    
    # 进行预测
    predictions = predict_future_nc_cqr(model, last_data, scalers, Q, steps)
    
    return predictions


def visualize_predictions(
    history: pd.DataFrame, 
    predictions: pd.DataFrame,
    eval_results: Dict = None,
    save_path: str = None
) -> None:
    """
    可视化预测结果
    
    Args:
        history (pd.DataFrame): 历史数据
        predictions (pd.DataFrame): 预测结果
        eval_results (Dict): 评估结果，可选
        save_path (str): 保存路径，可选
    """
    plt.figure(figsize=(14, 6))
    
    # 绘制历史观测值
    plt.plot(history['observation_time'], history['no2'], 
             'b-', label='历史观测值', alpha=0.7)
    
    # 标记预测起始点
    pred_start = predictions['observation_time'].iloc[0]
    plt.axvline(x=pred_start, color='gray', linestyle='--', label='预测起始点')
    
    # 绘制预测值和置信区间
    plt.plot(predictions['observation_time'], predictions['prediction'], 
             'r-', label='预测中值')
    plt.fill_between(
        predictions['observation_time'],
        predictions['lower_bound'],
        predictions['upper_bound'],
        color='r', alpha=0.2, label='95%预测区间'
    )
    
    # 设置标题（包含评估结果）
    title = '二氧化氮浓度预测结果（未来24小时）'
    if eval_results:
        title += f"\n测试集覆盖率：{eval_results['coverage']:.1%}，平均区间宽度：{eval_results['avg_interval_width']:.2f}"
    plt.title(title, fontsize=14)
    
    plt.xlabel('时间', fontsize=12)
    plt.ylabel('NO₂浓度 (μg/m³)', fontsize=12)
    plt.legend(fontsize=10)
    plt.grid(alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"图表已保存到: {save_path}")
    
    plt.show()


def export_predictions_to_csv(
    predictions: pd.DataFrame,
    output_path: str,
    city: str = None
) -> str:
    """
    导出预测结果到CSV文件
    
    Args:
        predictions (pd.DataFrame): 预测结果
        output_path (str): 输出路径
        city (str): 城市名称，可选
        
    Returns:
        str: 保存的文件路径
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 添加城市信息
    if city:
        predictions = predictions.copy()
        predictions['city'] = city
    
    predictions.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"预测结果已导出到: {output_path}")
    
    return output_path


def calculate_prediction_metrics(
    predictions: pd.DataFrame,
    actual: pd.DataFrame = None
) -> Dict:
    """
    计算预测指标
    
    Args:
        predictions (pd.DataFrame): 预测结果
        actual (pd.DataFrame): 实际观测值，可选
        
    Returns:
        Dict: 预测指标
    """
    metrics = {
        'prediction_steps': len(predictions),
        'avg_prediction': predictions['prediction'].mean(),
        'prediction_std': predictions['prediction'].std(),
        'avg_interval_width': (predictions['upper_bound'] - predictions['lower_bound']).mean(),
        'prediction_range': {
            'min': predictions['prediction'].min(),
            'max': predictions['prediction'].max()
        }
    }
    
    # 如果有实际值，计算准确性指标
    if actual is not None and len(actual) == len(predictions):
        errors = predictions['prediction'] - actual['no2']
        metrics.update({
            'mae': np.mean(np.abs(errors)),
            'rmse': np.sqrt(np.mean(errors**2)),
            'mape': np.mean(np.abs(errors / actual['no2'])) * 100,
            'coverage': np.mean(
                (actual['no2'] >= predictions['lower_bound']) & 
                (actual['no2'] <= predictions['upper_bound'])
            )
        })
    
    return metrics


def predict_next_24h(city: str = 'dongguan', **kwargs) -> Tuple[pd.DataFrame, Dict]:
    """
    预测未来24小时NO2浓度的便捷函数
    
    Args:
        city (str): 城市名称
        **kwargs: 其他参数
        
    Returns:
        Tuple[pd.DataFrame, Dict]: 预测结果和指标
    """
    predictions = predict_with_saved_model(city, steps=24, **kwargs)
    metrics = calculate_prediction_metrics(predictions)
    
    return predictions, metrics