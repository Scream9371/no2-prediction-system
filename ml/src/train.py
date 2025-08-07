"""
NC-CQR模型训练模块
"""
import os
from typing import Tuple, Dict

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from .data_loader import load_data_from_mysql
from .data_processing import prepare_nc_cqr_data, save_scalers_for_pipeline
from .reproducibility import create_deterministic_dataloader, get_city_seed


class QuantileNet(nn.Module):
    """非交叉分位数回归神经网络（NC-CQR）"""
    
    def __init__(self, input_dim: int, hidden_dims: list = [64, 64]):
        """
        初始化NC-CQR网络
        
        Args:
            input_dim (int): 输入特征维度
            hidden_dims (list): 隐藏层维度列表
        """
        super().__init__()
        layers = []
        prev_dim = input_dim
        for h_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, h_dim),
                nn.ReLU(),
                nn.BatchNorm1d(h_dim)
            ])
            prev_dim = h_dim
        
        self.shared_layers = nn.Sequential(*layers)
        self.lower_out = nn.Linear(prev_dim, 1)  # τ1=0.025 (下分位数)
        self.upper_out = nn.Linear(prev_dim, 1)  # τ2=0.975 (上分位数)
    
    def forward(self, x):
        """前向传播"""
        shared = self.shared_layers(x)
        return self.lower_out(shared), self.upper_out(shared)


def quantile_loss(output: torch.Tensor, target: torch.Tensor, tau: float) -> torch.Tensor:
    """
    分位数损失函数（Pinball Loss）
    
    Args:
        output (torch.Tensor): 模型输出
        target (torch.Tensor): 真实目标
        tau (float): 分位数水平
        
    Returns:
        torch.Tensor: 分位数损失
    """
    error = target.unsqueeze(1) - output
    return torch.mean(torch.max((tau - 1) * error, tau * error))


def non_crossing_quantile_loss(lower_pred: torch.Tensor, upper_pred: torch.Tensor, 
                               target: torch.Tensor, tau_low: float = 0.025, 
                               tau_high: float = 0.975, lambda_penalty: float = 1.0) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    带非交叉约束的NC-CQR损失函数
    
    基于论文《Nonparametric Quantile Regression: Non-Crossing Constraints and Conformal Prediction》
    对应论文中的公式(6)：R_n(f1, f2) = 分位数损失 + λ*非交叉惩罚项
    
    损失函数组成：
    1. 下分位数的Pinball Loss：ρ_τ_low(Y - f1(X))
    2. 上分位数的Pinball Loss：ρ_τ_high(Y - f2(X))  
    3. ReLU惩罚项：λ * max{f1(X) - f2(X), 0} 防止下分位数超过上分位数
    
    Args:
        lower_pred (torch.Tensor): 下分位数预测 f1(X)
        upper_pred (torch.Tensor): 上分位数预测 f2(X)
        target (torch.Tensor): 真实目标值 Y
        tau_low (float): 下分位数水平，默认0.025
        tau_high (float): 上分位数水平，默认0.975
        lambda_penalty (float): 非交叉惩罚权重，默认1.0
        
    Returns:
        Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]: 
            (总损失, 下分位数损失, 上分位数损失, 交叉惩罚项)
    """
    # 1. 计算两个分位数的Pinball Loss
    loss_lower = quantile_loss(lower_pred, target, tau_low)
    loss_upper = quantile_loss(upper_pred, target, tau_high)
    
    # 2. 计算非交叉惩罚项：V(f1, f2; x) = max{f1(x) - f2(x), 0}
    # 只有当lower_pred > upper_pred时才施加惩罚，确保 Q_low ≤ Q_high
    crossing_penalty = torch.mean(torch.relu(lower_pred - upper_pred))
    
    # 3. 组合成总损失：R_n(f1, f2) = L_low + L_high + λ * V
    total_loss = loss_lower + loss_upper + lambda_penalty * crossing_penalty
    
    return total_loss, loss_lower, loss_upper, crossing_penalty


def train_nc_cqr_model(
    X_train: np.ndarray, 
    y_train: np.ndarray,
    X_calib: np.ndarray, 
    y_calib: np.ndarray,
    epochs: int = 150, 
    batch_size: int = 32,
    learning_rate: float = 1e-3,
    hidden_dims: list = [64, 64],
    city: str = None,
    deterministic: bool = True
) -> Tuple[nn.Module, float]:
    """
    训练NC-CQR模型
    
    Args:
        X_train (np.ndarray): 训练特征
        y_train (np.ndarray): 训练目标
        X_calib (np.ndarray): 校准特征
        y_calib (np.ndarray): 校准目标
        epochs (int): 训练轮数
        batch_size (int): 批次大小
        learning_rate (float): 学习率
        hidden_dims (list): 隐藏层维度
        city (str): 城市名称，用于确定性训练
        deterministic (bool): 是否启用确定性训练模式
        
    Returns:
        Tuple[nn.Module, float]: 训练好的模型和校准量化值Q
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"使用设备: {device}")
    
    # 创建数据集
    train_dataset = TensorDataset(
        torch.FloatTensor(X_train),
        torch.FloatTensor(y_train)
    )
    
    # 根据是否需要确定性选择数据加载器
    if deterministic and city:
        # 使用城市特定的种子创建确定性数据加载器
        city_seed = get_city_seed(city)
        train_loader = create_deterministic_dataloader(train_dataset, batch_size, city_seed)
        print(f"使用确定性数据加载器 - 城市种子: {city_seed}")
    else:
        # 使用传统的随机数据加载器
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        print("使用标准数据加载器")
    
    # 初始化模型
    model = QuantileNet(input_dim=X_train.shape[1], hidden_dims=hidden_dims).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    
    # 训练循环 - 使用标准NC-CQR损失函数
    lambda_penalty = 1.0  # 非交叉惩罚权重，可调参数
    
    for epoch in range(epochs):
        model.train()
        epoch_total_loss = 0
        epoch_lower_loss = 0
        epoch_upper_loss = 0
        epoch_crossing_penalty = 0
        num_batches = 0
        
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            
            # 前向传播
            lower_pred, upper_pred = model(X_batch)
            
            # 使用改进的NC-CQR损失函数（更宽的预测区间）
            total_loss, loss_lower, loss_upper, crossing_penalty = non_crossing_quantile_loss(
                lower_pred, upper_pred, y_batch, 
                tau_low=0.025, tau_high=0.975, lambda_penalty=lambda_penalty
            )
            
            # 反向传播
            optimizer.zero_grad()
            total_loss.backward()
            optimizer.step()
            
            # 累积损失统计
            epoch_total_loss += total_loss.item()
            epoch_lower_loss += loss_lower.item()
            epoch_upper_loss += loss_upper.item()
            epoch_crossing_penalty += crossing_penalty.item()
            num_batches += 1
        
        # 打印训练进度（每50轮显示详细统计）
        if (epoch + 1) % 50 == 0:
            avg_total = epoch_total_loss / num_batches
            avg_lower = epoch_lower_loss / num_batches
            avg_upper = epoch_upper_loss / num_batches
            avg_crossing = epoch_crossing_penalty / num_batches
            
            print(f"Epoch {epoch + 1}/{epochs}")
            print(f"  总损失: {avg_total:.6f}")
            print(f"  下分位数损失: {avg_lower:.6f}")
            print(f"  上分位数损失: {avg_upper:.6f}")
            print(f"  交叉惩罚: {avg_crossing:.6f} {'[警告]' if avg_crossing > 0.01 else '[正常]'}")
            
            # 检查是否存在严重的交叉问题
            if avg_crossing > 0.1:
                print(f"  [警告] 交叉惩罚过高，考虑增加lambda_penalty参数")
    
    # 改进的Conformal Prediction校准（更高置信度）
    print("\n=== 开始Conformal预测校准 ===")
    alpha = 0.05  # 误覆盖率从0.1改为0.05，对应95%置信度
    
    with torch.no_grad():
        model.eval()
        X_calib_tensor = torch.FloatTensor(X_calib).to(device)
        y_calib_tensor = torch.FloatTensor(y_calib).to(device)
        
        lower_pred, upper_pred = model(X_calib_tensor)
        
        # 计算符合度分数：E_i = max{f1(X_i) - Y_i, Y_i - f2(X_i)}
        # 对应论文公式(13)
        conformity_scores = torch.maximum(
            lower_pred.squeeze() - y_calib_tensor,  # f1(X_i) - Y_i
            y_calib_tensor - upper_pred.squeeze()   # Y_i - f2(X_i)
        )
        
        # 分位数公式：(1-α)(n+1)/n
        n_calib = len(X_calib)
        quantile_level = (1 - alpha) * (n_calib + 1) / n_calib
        quantile_level = min(1.0, quantile_level)  # 确保不超过1.0
        
        Q_hat = torch.quantile(conformity_scores, quantile_level).cpu().item()
        
        # 统计信息
        num_violations = torch.sum(conformity_scores > Q_hat).item()
        violation_rate = num_violations / n_calib
        
        print(f"校准集大小: {n_calib}")
        print(f"目标置信度: {1-alpha:.1%}")
        print(f"计算分位数级别: {quantile_level:.4f}")
        print(f"校准量化值Q_hat: {Q_hat:.4f}")
        print(f"校准集违约率: {violation_rate:.1%}")
        
        # 验证校准效果
        if violation_rate <= alpha + 0.05:  # 允许5%的容差
            print("[成功] Conformal校准成功")
        else:
            print("[警告] Conformal校准可能存在问题")
    
    return model, Q_hat


def evaluate_model(model: nn.Module, X_test: np.ndarray, y_test: np.ndarray, Q: float) -> Dict:
    """
    评估NC-CQR模型
    
    Args:
        model (nn.Module): 训练好的模型
        X_test (np.ndarray): 测试特征
        y_test (np.ndarray): 测试目标
        Q (float): 校准量化值
        
    Returns:
        Dict: 评估结果
    """
    device = next(model.parameters()).device
    
    with torch.no_grad():
        model.eval()
        X_test_tensor = torch.FloatTensor(X_test).to(device)
        
        lower_pred, upper_pred = model(X_test_tensor)
        lower_bound = lower_pred.cpu().numpy().flatten() - Q
        upper_bound = upper_pred.cpu().numpy().flatten() + Q
        
        # 计算覆盖率
        coverage = np.mean((y_test >= lower_bound) & (y_test <= upper_bound))
        
        # 计算平均区间宽度
        avg_interval_width = np.mean(upper_bound - lower_bound)
        
        return {
            'coverage': coverage,
            'avg_interval_width': avg_interval_width,
            'test_samples': len(y_test),
            'lower_bound': lower_bound,
            'upper_bound': upper_bound
        }


def save_model(model: nn.Module, Q: float, scalers: Dict, 
               model_path: str) -> str:
    """
    保存NC-CQR模型
    
    Args:
        model (nn.Module): 训练好的模型
        Q (float): 校准量化值
        scalers (Dict): 标准化器
        model_path (str): 模型保存路径
        
    Returns:
        str: 保存路径
    """
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    
    # 保存模型状态和相关参数
    checkpoint = {
        'model_state_dict': model.state_dict(),
        'Q': Q,
        'scalers': scalers,
        'input_dim': model.shared_layers[0].in_features,
        'hidden_dims': [layer.out_features for layer in model.shared_layers if isinstance(layer, nn.Linear)]
    }
    
    torch.save(checkpoint, model_path)
    print(f"模型已保存到: {model_path}")
    
    return model_path


def load_model(model_path: str) -> Tuple[nn.Module, float, Dict]:
    """
    加载NC-CQR模型
    
    Args:
        model_path (str): 模型路径
        
    Returns:
        Tuple[nn.Module, float, Dict]: 模型, Q值, 标准化器
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"模型文件未找到: {model_path}")
    
    # 使用weights_only=False来处理包含sklearn对象的checkpoint
    checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
    
    # 重新创建模型
    model = QuantileNet(
        input_dim=checkpoint['input_dim'],
        hidden_dims=checkpoint['hidden_dims']
    )
    model.load_state_dict(checkpoint['model_state_dict'])
    
    return model, checkpoint['Q'], checkpoint['scalers']


def train_full_pipeline(city: str = 'dongguan', 
                       train_ratio: float = 0.6,
                       calib_ratio: float = 0.3, 
                       test_ratio: float = 0.1,
                       **train_kwargs) -> Tuple[nn.Module, float, Dict, Dict]:
    """
    完整的NC-CQR训练流程 - 使用改进的60%-30%-10%数据集划分（增加校准集）
    
    Args:
        city (str): 城市名称
        train_ratio (float): 训练集比例 (默认: 0.6)
        calib_ratio (float): 校准集比例 (默认: 0.3) 
        test_ratio (float): 测试集比例 (默认: 0.1)
        **train_kwargs: 训练参数
        
    Returns:
        Tuple[nn.Module, float, Dict, Dict]: 模型, Q值, 标准化器, 评估结果
    """
    print(f"=== 开始{city}市NC-CQR模型训练 ===")
    
    # 验证比例参数
    if abs(train_ratio + calib_ratio + test_ratio - 1.0) > 1e-6:
        raise ValueError(f"数据集比例之和必须为1.0，当前为{train_ratio + calib_ratio + test_ratio}")
    
    # 1. 加载数据
    df = load_data_from_mysql(city)
    
    # 2. 数据预处理
    X, y, scalers = prepare_nc_cqr_data(df)
    
    # 3. 数据集划分：60%训练，30%校准，10%测试
    n_samples = len(X)
    n_train = int(n_samples * train_ratio)
    n_calib = int(n_samples * calib_ratio)
    n_test = n_samples - n_train - n_calib  # 剩余部分作为测试集
    
    # 按时间顺序划分
    X_train = X[:n_train]
    y_train = y[:n_train]
    
    X_calib = X[n_train:n_train + n_calib]
    y_calib = y[n_train:n_train + n_calib]
    
    X_test = X[n_train + n_calib:]
    y_test = y[n_train + n_calib:]
    
    print(f"数据划分结果：")
    print(f"- 训练集：{len(X_train)}条 ({len(X_train)/len(X)*100:.1f}%)")
    print(f"- 校准集：{len(X_calib)}条 ({len(X_calib)/len(X)*100:.1f}%)")
    print(f"- 测试集：{len(X_test)}条 ({len(X_test)/len(X)*100:.1f}%)")
    
    # 4. 训练模型
    print("\n=== 开始模型训练 ===")
    # 确保城市参数传递给训练函数
    train_kwargs_with_city = {**train_kwargs, 'city': city}
    model, Q = train_nc_cqr_model(X_train, y_train, X_calib, y_calib, **train_kwargs_with_city)
    print(f"训练完成，Q值：{Q:.2f}")
    
    # 5. 模型评估
    print("\n=== 测试集评估 ===")
    eval_results = evaluate_model(model, X_test, y_test, Q)
    print(f"测试集覆盖率：{eval_results['coverage']:.1%}")
    print(f"平均预测区间宽度：{eval_results['avg_interval_width']:.2f}")
    
    # 6. 保存标准化器（按城市分离存储）
    save_scalers_for_pipeline(scalers, city)
    
    return model, Q, scalers, eval_results