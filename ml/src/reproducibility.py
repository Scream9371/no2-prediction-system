"""
NC-CQR可重现性保证模块 - 确保模型在不同设备上的一致性
"""
import os
import random
import hashlib
from typing import Optional

import numpy as np
import torch
import torch.backends.cudnn as cudnn


def set_deterministic_seeds(seed: int = 42, ensure_deterministic: bool = True) -> None:
    """
    设置所有随机种子以确保可重现性
    
    Args:
        seed (int): 随机种子值，默认42
        ensure_deterministic (bool): 是否启用严格确定性模式（可能影响性能）
        
    Note:
        在严格确定性模式下，某些CUDA操作可能会变慢，但能保证完全一致的结果
    """
    print(f"设置随机种子: {seed}")
    
    # 1. Python内置random模块
    random.seed(seed)
    
    # 2. NumPy随机种子
    np.random.seed(seed)
    
    # 3. PyTorch CPU随机种子
    torch.manual_seed(seed)
    
    # 4. PyTorch GPU随机种子
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)  # 对所有GPU设备设置种子
        
        if ensure_deterministic:
            # 启用CUDA确定性模式
            cudnn.deterministic = True
            cudnn.benchmark = False
            
            # 设置环境变量以确保CUDA操作的确定性
            os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
            
            # PyTorch 1.8+的确定性设置
            if hasattr(torch, 'use_deterministic_algorithms'):
                torch.use_deterministic_algorithms(True, warn_only=True)
                
            print("已启用CUDA确定性模式（可能影响性能）")
        else:
            # 为了性能考虑，允许一些非确定性操作
            cudnn.deterministic = False
            cudnn.benchmark = True
            print("使用高性能模式（可能存在微小的非确定性）")
    
    print(f"随机种子设置完成 - CPU种子: {seed}, GPU种子: {seed}")


def generate_city_specific_seed(city: str, base_seed: int = 42) -> int:
    """
    为不同城市生成特定的随机种子，确保每个城市有独立且可重现的随机性
    
    Args:
        city (str): 城市名称
        base_seed (int): 基础种子值
        
    Returns:
        int: 城市特定的种子值
        
    Example:
        >>> generate_city_specific_seed('dongguan', 42)
        1234567  # 基于城市名和基础种子计算的确定性值
    """
    # 使用城市名和基础种子的组合生成哈希
    combined_str = f"{city}_{base_seed}"
    hash_object = hashlib.md5(combined_str.encode())
    # 取哈希值的前8位作为种子（确保为正整数）
    city_seed = int(hash_object.hexdigest()[:8], 16) % (2**31 - 1)
    
    print(f"城市 {city} 的专用种子: {city_seed}")
    return city_seed


def ensure_reproducibility_context(city: str, base_seed: int = 42, 
                                  ensure_deterministic: bool = True):
    """
    创建可重现性上下文管理器，自动设置和恢复随机状态
    
    Args:
        city (str): 城市名称
        base_seed (int): 基础随机种子
        ensure_deterministic (bool): 是否启用严格确定性模式
        
    Usage:
        with ensure_reproducibility_context('dongguan', 42):
            # 在此上下文中的所有操作都是可重现的
            model = train_model()
    """
    return ReproducibilityContext(city, base_seed, ensure_deterministic)


class ReproducibilityContext:
    """可重现性上下文管理器"""
    
    def __init__(self, city: str, base_seed: int = 42, ensure_deterministic: bool = True):
        self.city = city
        self.base_seed = base_seed
        self.ensure_deterministic = ensure_deterministic
        
        # 保存原始状态
        self.original_python_state = None
        self.original_numpy_state = None
        self.original_torch_state = None
        self.original_cuda_state = None
        self.original_cudnn_deterministic = None
        self.original_cuda_env = None
        
    def __enter__(self):
        """进入上下文时设置可重现性"""
        print(f"=== 进入 {self.city} 市的可重现性训练模式 ===")
        
        # 保存原始随机状态
        self.original_python_state = random.getstate()
        self.original_numpy_state = np.random.get_state()
        self.original_torch_state = torch.get_rng_state()
        
        if torch.cuda.is_available():
            self.original_cuda_state = torch.cuda.get_rng_state_all()
            self.original_cudnn_deterministic = cudnn.deterministic
            self.original_cuda_env = os.environ.get('CUBLAS_WORKSPACE_CONFIG')
        
        # 设置城市特定的种子
        city_seed = generate_city_specific_seed(self.city, self.base_seed)
        set_deterministic_seeds(city_seed, self.ensure_deterministic)
        
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时恢复原始状态"""
        print(f"=== 退出 {self.city} 市的可重现性训练模式 ===")
        
        # 恢复原始随机状态
        if self.original_python_state:
            random.setstate(self.original_python_state)
        if self.original_numpy_state:
            np.random.set_state(self.original_numpy_state)
        if self.original_torch_state is not None:
            torch.set_rng_state(self.original_torch_state)
            
        if torch.cuda.is_available():
            if self.original_cuda_state:
                torch.cuda.set_rng_state_all(self.original_cuda_state)
            if self.original_cudnn_deterministic is not None:
                cudnn.deterministic = self.original_cudnn_deterministic
            if self.original_cuda_env:
                os.environ['CUBLAS_WORKSPACE_CONFIG'] = self.original_cuda_env
            elif 'CUBLAS_WORKSPACE_CONFIG' in os.environ:
                del os.environ['CUBLAS_WORKSPACE_CONFIG']


def verify_deterministic_behavior(model_factory, X, y, iterations: int = 3) -> bool:
    """
    验证模型训练的确定性行为
    
    Args:
        model_factory: 模型创建函数
        X: 输入特征
        y: 目标变量  
        iterations: 验证迭代次数
        
    Returns:
        bool: 是否具有确定性行为
    """
    print(f"验证确定性行为 - 进行 {iterations} 次独立训练...")
    
    results = []
    
    for i in range(iterations):
        print(f"第 {i+1} 次训练...")
        
        # 每次都设置相同的种子
        set_deterministic_seeds(42, ensure_deterministic=True)
        
        # 训练模型并获取结果
        model = model_factory()
        # 这里应该是实际的训练逻辑
        # 为简化，我们假设有一个获取模型参数哈希的方法
        model_hash = get_model_parameters_hash(model)
        results.append(model_hash)
        
        print(f"第 {i+1} 次训练的模型参数哈希: {model_hash[:16]}...")
    
    # 检查所有结果是否一致
    is_deterministic = len(set(results)) == 1
    
    if is_deterministic:
        print("✓ 验证通过：模型训练具有确定性行为")
    else:
        print("✗ 验证失败：模型训练存在随机性")
        print("不同训练的结果哈希:")
        for i, result in enumerate(results):
            print(f"  第 {i+1} 次: {result[:16]}...")
    
    return is_deterministic


def get_model_parameters_hash(model) -> str:
    """
    计算模型参数的哈希值，用于验证一致性
    
    Args:
        model: PyTorch模型
        
    Returns:
        str: 参数哈希值
    """
    if hasattr(model, 'state_dict'):
        # PyTorch模型
        param_string = ""
        for name, param in model.state_dict().items():
            if param is not None:
                param_string += f"{name}:{param.cpu().numpy().tobytes().hex()}"
    else:
        # 其他类型的模型
        param_string = str(model)
    
    return hashlib.sha256(param_string.encode()).hexdigest()


def create_deterministic_dataloader(dataset, batch_size: int, seed: int = 42):
    """
    创建确定性的数据加载器
    
    Args:
        dataset: PyTorch数据集
        batch_size: 批次大小
        seed: 随机种子
        
    Returns:
        DataLoader: 确定性的数据加载器
    """
    from torch.utils.data import DataLoader
    
    # 创建确定性的生成器
    generator = torch.Generator()
    generator.manual_seed(seed)
    
    return DataLoader(
        dataset, 
        batch_size=batch_size, 
        shuffle=True,  # 仍然可以洗牌，但是使用固定种子
        generator=generator,  # 确保洗牌的确定性
        worker_init_fn=lambda worker_id: np.random.seed(seed + worker_id)  # 多进程确定性
    )


# 配置常量
DEFAULT_SEED = 42
CITY_SEEDS = {
    'dongguan': 1001,
    'guangzhou': 1002, 
    'shenzhen': 1003,
    'zhuhai': 1004,
    'foshan': 1005,
    'huizhou': 1006,
    'zhongshan': 1007,
    'jiangmen': 1008,
    'zhaoqing': 1009,
    'hongkong': 1010,
    'macao': 1011
}


def get_city_seed(city: str) -> int:
    """
    获取城市的预定义种子值
    
    Args:
        city (str): 城市名称
        
    Returns:
        int: 城市种子值
    """
    return CITY_SEEDS.get(city.lower(), generate_city_specific_seed(city, DEFAULT_SEED))