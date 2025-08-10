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


class ResidualBlock(nn.Module):
    """残差块实现（修复属性问题）"""
    def __init__(self, in_features: int, out_features: int):
        super().__init__()
        # 显式保存输入输出特征维度（关键修复）
        self.in_features = in_features
        self.out_features = out_features
        
        self.layers = nn.Sequential(
            nn.Linear(in_features, out_features),
            nn.ReLU(),
            nn.BatchNorm1d(out_features),
            nn.Linear(out_features, out_features),
            nn.ReLU(),
            nn.BatchNorm1d(out_features)
        )
        
        # 残差连接（维度调整）
        if in_features != out_features:
            self.shortcut = nn.Linear(in_features, out_features)
        else:
            self.shortcut = nn.Identity()
    
    def forward(self, x):
        residual = self.shortcut(x)
        x = self.layers(x)
        x += residual
        return x


class QuantileNet(nn.Module):
    def __init__(self, input_dim: int, hidden_dims: list = [32, 32], use_residual: bool = False):
        super().__init__()
        """
        初始化NC-CQR网络
        
        Args:
            input_dim (int): 输入特征维度
            hidden_dims (list): 隐藏层维度列表
            use_residual (bool): 是否使用残差块
        """

        # 显式存储关键结构参数（修复核心问题）
        self.input_dim = input_dim
        self.hidden_dims = hidden_dims
        self.use_residual = use_residual
        
        layers = []
        prev_dim = input_dim
        for h_dim in hidden_dims:
            if use_residual:
                layers.append(ResidualBlock(prev_dim, h_dim))
            else:
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
    """分位数损失函数（Pinball Loss）"""
    error = target.unsqueeze(1) - output
    return torch.mean(torch.max((tau - 1) * error, tau * error))


def non_crossing_quantile_loss(lower_pred: torch.Tensor, upper_pred: torch.Tensor, 
                               target: torch.Tensor, tau_low: float = 0.025, 
                               tau_high: float = 0.975, lambda_penalty: float = 1.0) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """带非交叉约束的NC-CQR损失函数"""
    loss_lower = quantile_loss(lower_pred, target, tau_low)
    loss_upper = quantile_loss(upper_pred, target, tau_high)
    crossing_penalty = torch.mean(torch.relu(lower_pred - upper_pred))
    total_loss = loss_lower + loss_upper + lambda_penalty * crossing_penalty
    return total_loss, loss_lower, loss_upper, crossing_penalty


def train_nc_cqr_model(
    X_train: np.ndarray, 
    y_train: np.ndarray,
    X_calib: np.ndarray, 
    y_calib: np.ndarray,
    epochs: int = 150, 
    batch_size: int = 32,
    learning_rate: float = 4e-3,
    hidden_dims: list = [32, 32],
    use_residual: bool = False,
    city: str = None,
    deterministic: bool = True
) -> Tuple[nn.Module, float]:
    """训练NC-CQR模型（修复确定性数据加载器问题）"""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"使用设备: {device}")
    
    # 数据量检查（确保有足够数据）
    if len(X_train) < batch_size:
        print(f"警告：训练数据量({len(X_train)})少于批次大小({batch_size})，自动调整批次大小为{len(X_train)}")
        batch_size = min(batch_size, len(X_train))
    
    # 创建数据集
    train_dataset = TensorDataset(
        torch.FloatTensor(X_train),
        torch.FloatTensor(y_train)
    )
    
    # 修复：创建支持 drop_last 的确定性数据加载器
    if deterministic and city:
        city_seed = get_city_seed(city)
        
        # 创建自定义的确定性数据加载器
        generator = torch.Generator()
        generator.manual_seed(city_seed)
        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True,
            generator=generator,
            drop_last=True  # 添加 drop_last 支持
        )
        print(f"使用确定性数据加载器 - 城市种子: {city_seed} (带drop_last支持)")
    else:
        train_loader = DataLoader(
            train_dataset, 
            batch_size=batch_size, 
            shuffle=True,
            drop_last=True
        )
        print("使用标准数据加载器")
    
    # 初始化模型（支持残差块）
    model = QuantileNet(
        input_dim=X_train.shape[1], 
        hidden_dims=hidden_dims,
        use_residual=use_residual
    ).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    
    # 训练循环
    lambda_penalty = 1.0
    for epoch in range(epochs):
        model.train()
        epoch_total_loss = 0
        epoch_lower_loss = 0
        epoch_upper_loss = 0
        epoch_crossing_penalty = 0
        num_batches = 0
        
        for X_batch, y_batch in train_loader:
            # 跳过可能的小批次（双重保险）
            if X_batch.size(0) < 2:
                print(f"警告：跳过大小为{X_batch.size(0)}的小批次")
                continue
                
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            lower_pred, upper_pred = model(X_batch)
            
            total_loss, loss_lower, loss_upper, crossing_penalty = non_crossing_quantile_loss(
                lower_pred, upper_pred, y_batch, 
                tau_low=0.025, tau_high=0.975, lambda_penalty=lambda_penalty
            )
            
            optimizer.zero_grad()
            total_loss.backward()
            optimizer.step()
            
            epoch_total_loss += total_loss.item()
            epoch_lower_loss += loss_lower.item()
            epoch_upper_loss += loss_upper.item()
            epoch_crossing_penalty += crossing_penalty.item()
            num_batches += 1
        
        # 打印训练进度
        if (epoch + 1) % 50 == 0 or epoch == 0 or (epoch + 1) == epochs:
            if num_batches == 0:
                print(f"Epoch {epoch + 1}/{epochs} 没有有效批次可训练")
                continue
                
            avg_total = epoch_total_loss / num_batches
            avg_lower = epoch_lower_loss / num_batches
            avg_upper = epoch_upper_loss / num_batches
            avg_crossing = epoch_crossing_penalty / num_batches
            
            print(f"Epoch {epoch + 1}/{epochs}")
            print(f"  总损失: {avg_total:.6f}")
            print(f"  下分位数损失: {avg_lower:.6f}")
            print(f"  上分位数损失: {avg_upper:.6f}")
            print(f"  交叉惩罚: {avg_crossing:.6f} {'[警告]' if avg_crossing > 0.01 else '[正常]'}")
            
            # 动态调整交叉惩罚系数
            if avg_crossing > 0.2:
                lambda_penalty *= 1.5
                print(f"  [警告] 交叉惩罚过高，增加lambda_penalty到{lambda_penalty:.1f}")
            elif avg_crossing < 0.01:
                lambda_penalty = max(0.1, lambda_penalty * 0.9)
    
    # Conformal Prediction校准
    print("\n=== 开始Conformal预测校准 ===")
    alpha = 0.05  # 95%置信度
    
    with torch.no_grad():
        model.eval()
        X_calib_tensor = torch.FloatTensor(X_calib).to(device)
        y_calib_tensor = torch.FloatTensor(y_calib).to(device)
        
        lower_pred, upper_pred = model(X_calib_tensor)
        conformity_scores = torch.maximum(
            lower_pred.squeeze() - y_calib_tensor,
            y_calib_tensor - upper_pred.squeeze()
        )
        
        n_calib = len(X_calib)
        quantile_level = (1 - alpha) * (n_calib + 1) / n_calib
        quantile_level = min(1.0, quantile_level)
        Q_hat = torch.quantile(conformity_scores, quantile_level).cpu().item()
        
        num_violations = torch.sum(conformity_scores > Q_hat).item()
        violation_rate = num_violations / n_calib
        
        print(f"校准集大小: {n_calib}")
        print(f"目标置信度: {1-alpha:.1%}")
        print(f"计算分位数级别: {quantile_level:.4f}")
        print(f"校准量化值Q_hat: {Q_hat:.4f}")
        print(f"校准集违约率: {violation_rate:.1%}")
        
        if violation_rate <= alpha + 0.05:
            print("[成功] Conformal校准成功")
        else:
            print(f"[警告] Conformal校准可能有问题，目标违约率{alpha:.1%}，实际违约率{violation_rate:.1%}")
    
    return model, Q_hat

def evaluate_model(model: nn.Module, X_test: np.ndarray, y_test: np.ndarray, Q: float) -> Dict:
    """评估NC-CQR模型"""
    device = next(model.parameters()).device
    
    with torch.no_grad():
        model.eval()
        X_test_tensor = torch.FloatTensor(X_test).to(device)
        lower_pred, upper_pred = model(X_test_tensor)
        
        lower_bound = lower_pred.cpu().numpy().flatten() - Q
        upper_bound = upper_pred.cpu().numpy().flatten() + Q
        coverage = np.mean((y_test >= lower_bound) & (y_test <= upper_bound))
        avg_interval_width = np.mean(upper_bound - lower_bound)
        
        return {
            'coverage': coverage,
            'avg_interval_width': avg_interval_width,
            'test_samples': len(y_test),
            'lower_bound': lower_bound,
            'upper_bound': upper_bound
        }


def save_model(model: nn.Module, Q: float, scalers: Dict, model_path: str) -> str:
    """保存NC-CQR模型（修复核心问题）"""
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    
    # 使用模型显式存储的结构参数（关键修复）
    checkpoint = {
        'model_state_dict': model.state_dict(),
        'Q': Q,
        'scalers': scalers,
        'input_dim': model.input_dim,       # 直接使用存储的输入维度
        'hidden_dims': model.hidden_dims,   # 直接使用存储的隐藏层维度
        'use_residual': model.use_residual   # 直接使用残差块标志
    }
    
    torch.save(checkpoint, model_path)
    print(f"模型已保存到: {model_path}")
    return model_path


def load_model(model_path: str) -> Tuple[nn.Module, float, Dict]:
    """加载NC-CQR模型（修复核心问题）"""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"模型文件未找到: {model_path}")
    
    checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
    
    # 使用保存的结构参数重建模型（关键修复）
    model = QuantileNet(
        input_dim=checkpoint['input_dim'],
        hidden_dims=checkpoint['hidden_dims'],
        use_residual=checkpoint.get('use_residual', False)  # 支持残差块加载
    )
    model.load_state_dict(checkpoint['model_state_dict'])
    
    return model, checkpoint['Q'], checkpoint['scalers']


def train_full_pipeline(city: str = 'dongguan', 
                       train_ratio: float = 0.6,
                       calib_ratio: float = 0.3, 
                       test_ratio: float = 0.1,
                       **train_kwargs) -> Tuple[nn.Module, float, Dict, Dict]:
    """完整的NC-CQR训练流程"""
    print(f"=== 开始{city}市NC-CQR模型训练 ===")
    
    if abs(train_ratio + calib_ratio + test_ratio - 1.0) > 1e-6:
        raise ValueError(f"数据集比例之和必须为1.0，当前为{train_ratio + calib_ratio + test_ratio}")
    
    # 1. 加载数据
    df = load_data_from_mysql(city)
    
    # 2. 数据预处理
    X, y, scalers = prepare_nc_cqr_data(df)
    
    # 3. 数据集划分
    n_samples = len(X)
    n_train = int(n_samples * train_ratio)
    n_calib = int(n_samples * calib_ratio)
    n_test = n_samples - n_train - n_calib
    
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
    train_kwargs_with_city = {** train_kwargs, 'city': city}
    model, Q = train_nc_cqr_model(X_train, y_train, X_calib, y_calib, **train_kwargs_with_city)
    print(f"训练完成，Q值：{Q:.2f}")
    
    # 5. 模型评估
    print("\n=== 测试集评估 ===")
    eval_results = evaluate_model(model, X_test, y_test, Q)
    print(f"测试集覆盖率：{eval_results['coverage']:.1%}")
    print(f"平均预测区间宽度：{eval_results['avg_interval_width']:.2f}")
    
    # 6. 保存标准化器
    save_scalers_for_pipeline(scalers, city)
    
    return model, Q, scalers, eval_results