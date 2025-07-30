"""
ML自动化模块

提供模型训练的自动化功能，包括：
- 训练调度器
- 模型版本管理
- 训练监控
- 性能追踪
"""

from .training_scheduler import SimpleAutoTrainingScheduler

__all__ = [
    'SimpleAutoTrainingScheduler'
]