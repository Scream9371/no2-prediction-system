#!/usr/bin/env python3
"""
NC-CQR主控制脚本 - 非交叉分位数回归NO2浓度预测系统
"""
import sys
import os
import argparse
from datetime import datetime

from .data_loader import load_data_from_mysql, get_supported_cities
from .data_processing import prepare_nc_cqr_data, save_scalers_for_control
from .train import train_full_pipeline, load_model, save_model
from .predict import predict_with_saved_model, visualize_predictions, export_predictions_to_csv
from .reproducibility import ensure_reproducibility_context


def train_mode(city: str = 'dongguan', deterministic: bool = True, **kwargs):
    """训练模式"""
    print(f"=== NC-CQR训练模式 - {city} ===")
    
    try:
        # 使用可重现性上下文管理器进行训练
        with ensure_reproducibility_context(city, base_seed=42, ensure_deterministic=deterministic):
            model, Q, scalers, eval_results = train_full_pipeline(city, **kwargs)
        
        # 保存控制脚本专用的标准化器
        save_scalers_for_control(scalers, city)
        
        # 保存模型到outputs/models/
        from config.paths import get_control_model_path
        model_path = get_control_model_path(city)
        save_model(model, Q, scalers, model_path)
        
        print(f"\n=== 训练完成 ===")
        print(f"城市: {city}")
        print(f"Q值: {Q:.2f}")
        print(f"测试集覆盖率: {eval_results['coverage']:.1%}")
        print(f"平均区间宽度: {eval_results['avg_interval_width']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"训练失败: {str(e)}")
        return False


def predict_mode(city: str = 'dongguan', steps: int = 24, save_chart: bool = False):
    """预测模式"""
    print(f"=== NC-CQR预测模式 - {city} ===")
    
    try:
        # 进行预测（控制脚本专用，仅使用控制脚本模型）
        predictions = predict_with_saved_model(city, steps=steps, model_source='control')
        
        # 获取历史数据用于可视化（使用数据库中所有240小时数据）
        history = load_data_from_mysql(city)
        
        # 生成统一的时间戳，用于图像和CSV文件
        from config.paths import get_control_prediction_image_path, get_control_prediction_csv_path, ensure_directories
        ensure_directories()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 可视化结果
        save_path = None
        if save_chart:
            save_path = get_control_prediction_image_path(city, timestamp)
        
        visualize_predictions(history, predictions, save_path=save_path)
        
        # 导出预测结果
        csv_path = get_control_prediction_csv_path(city, timestamp)
        export_predictions_to_csv(predictions, csv_path, city)
        
        print(f"\n=== 预测完成 ===")
        print(f"城市: {city}")
        print(f"预测步数: {steps}小时")
        print(f"预测结果:")
        print(predictions.head())
        
        return predictions
        
    except Exception as e:
        print(f"预测失败: {str(e)}")
        return False


def evaluate_mode(city: str = 'dongguan'):
    """评估模式"""
    print(f"=== NC-CQR评估模式 - {city} ===")
    
    try:
        # 加载数据和模型
        df = load_data_from_mysql(city)
        X, y, scalers = prepare_nc_cqr_data(df)
        
        from config.paths import get_control_model_path
        model_path = get_control_model_path(city)
        model, Q, _ = load_model(model_path)
        
        # 使用最后30%数据进行评估
        test_size = int(len(X) * 0.3)
        X_test = X[-test_size:]
        y_test = y[-test_size:]
        
        from .train import evaluate_model
        eval_results = evaluate_model(model, X_test, y_test, Q)
        
        print(f"\n=== 评估结果 ===")
        print(f"测试集样本数: {eval_results['test_samples']}")
        print(f"覆盖率: {eval_results['coverage']:.1%}")
        print(f"平均区间宽度: {eval_results['avg_interval_width']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"评估失败: {str(e)}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='NC-CQR NO2浓度预测系统')
    parser.add_argument('mode', choices=['train', 'predict', 'evaluate'], 
                       help='运行模式: train(训练), predict(预测), evaluate(评估)')
    parser.add_argument('--city', type=str, default='dongguan',
                       help='城市名称 (默认: dongguan)')
    parser.add_argument('--steps', type=int, default=24,
                       help='预测步数(小时) (默认: 24)')
    parser.add_argument('--epochs', type=int, default=150,
                       help='训练轮数 (默认: 150)')
    parser.add_argument('--batch-size', type=int, default=32,
                       help='批次大小 (默认: 32)')
    parser.add_argument('--learning-rate', type=float, default=1e-3,
                       help='学习率 (默认: 1e-3)')
    parser.add_argument('--save-chart', action='store_true',
                       help='保存预测图表')
    parser.add_argument('--list-cities', action='store_true',
                       help='列出支持的城市')
    
    args = parser.parse_args()
    
    # 列出支持的城市
    if args.list_cities:
        cities = get_supported_cities()
        print("支持的城市:")
        for city in cities:
            print(f"  - {city}")
        return
    
    # 验证城市
    if args.city not in get_supported_cities():
        print(f"不支持的城市: {args.city}")
        print(f"支持的城市: {get_supported_cities()}")
        return
    
    # 根据模式执行相应功能
    if args.mode == 'train':
        success = train_mode(
            city=args.city,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate
        )
    elif args.mode == 'predict':
        result = predict_mode(
            city=args.city,
            steps=args.steps,
            save_chart=args.save_chart
        )
        success = result is not False
    elif args.mode == 'evaluate':
        success = evaluate_mode(city=args.city)
    
    if success:
        print(f"\n{args.mode}模式执行成功")
    else:
        print(f"\n{args.mode}模式执行失败")
        sys.exit(1)


def run_demo():
    """演示模式 - 自动运行训练和预测"""
    print("=== NC-CQR演示模式 ===")
    
    city = 'dongguan'
    
    # 1. 训练模型
    print("1. 开始训练模型...")
    if not train_mode(city, epochs=150):
        print("训练失败，退出演示")
        return
    
    # 2. 进行预测
    print("\n2. 开始预测...")
    if not predict_mode(city, steps=24, save_chart=True):
        print("预测失败，退出演示")
        return
    
    # 3. 评估模型
    print("\n3. 开始评估...")
    if not evaluate_mode(city):
        print("评估失败，退出演示")
        return
    
    print("\n演示完成！")


if __name__ == "__main__":
    # 如果没有命令行参数，运行演示模式
    if len(sys.argv) == 1:
        run_demo()
    else:
        main()