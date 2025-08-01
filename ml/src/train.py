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
        self.lower_out = nn.Linear(prev_dim, 1)  # τ1=0.05 (下分位数)
        self.upper_out = nn.Linear(prev_dim, 1)  # τ2=0.95 (上分位数)
    
    def forward(self, x):
        """前向传播"""
        shared = self.shared_layers(x)
        return self.lower_out(shared), self.upper_out(shared)


def quantile_loss(output: torch.Tensor, target: torch.Tensor, tau: float) -> torch.Tensor:
    """
    分位数损失函数
    
    Args:
        output (torch.Tensor): 模型输出
        target (torch.Tensor): 真实目标
        tau (float): 分位数水平
        
    Returns:
        torch.Tensor: 分位数损失
    """
    error = target.unsqueeze(1) - output
    return torch.mean(torch.max((tau - 1) * error, tau * error))


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
    
    # 训练循环
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            
            # 前向传播
            lower_pred, upper_pred = model(X_batch)
            
            # 计算分位数损失 - 修改为95%区间对应的分位数
            loss_lower = quantile_loss(lower_pred, y_batch, tau=0.05)
            loss_upper = quantile_loss(upper_pred, y_batch, tau=0.95)
            
            # 非交叉约束惩罚项
            penalty = torch.mean(torch.relu(lower_pred - upper_pred))
            
            # 总损失
            total_loss = loss_lower + loss_upper + 0.1 * penalty
            
            # 反向传播
            optimizer.zero_grad()
            total_loss.backward()
            optimizer.step()
        
        # 打印训练进度
        if (epoch + 1) % 50 == 0:
            print(f"Epoch {epoch + 1}/{epochs}, Loss: {total_loss.item():.4f}")
    
    # 保形校准
    with torch.no_grad():
        model.eval()
        X_calib_tensor = torch.FloatTensor(X_calib).to(device)
        y_calib_tensor = torch.FloatTensor(y_calib).to(device)
        
        lower_pred, upper_pred = model(X_calib_tensor)
        
        # 计算校准分数
        scores = torch.maximum(
            y_calib_tensor - upper_pred.squeeze(),
            lower_pred.squeeze() - y_calib_tensor
        )
        Q = torch.quantile(scores, 0.9).cpu().item()
    
    return model, Q


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
                       train_ratio: float = 0.4,
                       calib_ratio: float = 0.4, 
                       test_ratio: float = 0.2,
                       **train_kwargs) -> Tuple[nn.Module, float, Dict, Dict]:
    """
    完整的NC-CQR训练流程 - 使用标准40%-40%-20%数据集划分
    
    Args:
        city (str): 城市名称
        train_ratio (float): 训练集比例 (默认: 0.4)
        calib_ratio (float): 校准集比例 (默认: 0.4)
        test_ratio (float): 测试集比例 (默认: 0.2)
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
    
    # 3. NC-CQR标准数据集划分：40%训练，40%校准，20%测试
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