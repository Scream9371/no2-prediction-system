#!/usr/bin/env python3
"""
自动训练脚本

这是生产环境中用于定时执行模型训练的主入口脚本。

特点：
- 直接调用简化版训练调度器
- 适合crontab调度
- 提供健康检查功能
- 日志记录和错误处理
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ml.automation.training_scheduler import SimpleAutoTrainingScheduler


def setup_root_logger():
    """设置根日志记录器"""
    log_dir = project_root / 'logs' / 'auto_training'
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 配置根logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(
                log_dir / f'auto_training_{datetime.now().strftime("%Y%m%d")}.log',
                encoding='utf-8'
            ),
            logging.StreamHandler()
        ]
    )


def run_training(force_override=False):
    """执行自动训练"""
    logger = logging.getLogger('AutoTraining')
    
    try:
        logger.info("=" * 50)
        logger.info("启动自动训练脚本")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"工作目录: {os.getcwd()}")
        if force_override:
            logger.info("🔄 强制覆盖模式：将删除原有模型和预测缓存，重新训练所有城市")
        logger.info("=" * 50)
        
        # 创建调度器并执行训练
        scheduler = SimpleAutoTrainingScheduler()
        result = scheduler.run_daily_training(force_override=force_override)
        
        logger.info("🎯 自动训练执行完成")
        
        if result.failed_cities > 0:
            logger.warning(f"有 {result.failed_cities} 个城市训练失败")
            logger.warning(f"失败城市列表: {result.failed_city_list}")
            return False
        
        logger.info("✅ 自动训练脚本执行成功")
        return True
        
    except Exception as e:
        logger.error(f"❌ 自动训练脚本执行失败: {str(e)}")
        return False


def run_health_check():
    """执行健康检查"""
    logger = logging.getLogger('AutoTraining.HealthCheck')
    
    try:
        logger.info("🏥 开始系统健康检查...")
        
        scheduler = SimpleAutoTrainingScheduler()
        checks = scheduler.health_check()
        
        all_passed = True
        for check_name, status in checks.items():
            status_str = "✅ 通过" if status else "❌ 失败"
            logger.info(f"   {check_name}: {status_str}")
            if not status:
                all_passed = False
        
        if all_passed:
            logger.info("🎉 所有健康检查均通过")
            return True
        else:
            logger.warning("⚠️ 部分健康检查失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ 健康检查执行失败: {str(e)}")
        return False


def print_usage():
    """打印使用说明"""
    print("NO2预测系统 - 自动训练脚本")
    print()
    print("用法:")
    print("  python scripts/auto_training.py [命令] [选项]")
    print()
    print("命令:")
    print("  run      执行自动训练 (默认)")
    print("  health   执行健康检查")
    print("  help     显示此帮助信息")
    print()
    print("选项:")
    print("  --force  强制覆盖模式，删除原有模型和缓存重新训练")
    print()
    print("示例:")
    print("  python scripts/auto_training.py               # 执行训练（防重复保护）")
    print("  python scripts/auto_training.py run           # 执行训练（防重复保护）")
    print("  python scripts/auto_training.py run --force   # 强制重新训练并覆盖缓存")
    print("  python scripts/auto_training.py health        # 健康检查")
    print()
    print("定时任务设置 (crontab):")
    print("  # 每天凌晨3点执行训练（推荐不使用 --force）")
    print("  0 3 * * * cd /path/to/no2-prediction-system && python scripts/auto_training.py run")
    print()
    print("手动覆盖模式说明:")
    print("  --force 选项会：")
    print("    1. 删除今日已有的模型文件")
    print("    2. 清空预测数据缓存")
    print("    3. 强制重新训练所有城市")
    print("    4. 重新生成预测缓存")
    print("    5. 确保Web前端立即显示更新结果")
    print()


def main():
    """主入口函数"""
    # 设置日志
    setup_root_logger()
    
    # 解析命令行参数
    args = sys.argv[1:]  # 获取除脚本名外的所有参数
    
    # 提取命令
    command = 'run'  # 默认命令
    force_override = False
    
    for arg in args:
        arg = arg.lower()
        if arg in ['run', 'health', 'help', '-h', '--help']:
            command = arg
        elif arg == '--force':
            force_override = True
        else:
            print(f"❌ 未知参数: {arg}")
            print()
            print_usage()
            sys.exit(1)
    
    # 执行相应命令
    if command == 'run':
        success = run_training(force_override=force_override)
        sys.exit(0 if success else 1)
        
    elif command == 'health':
        if force_override:
            print("⚠️  健康检查不支持 --force 参数")
        success = run_health_check()
        sys.exit(0 if success else 1)
        
    elif command in ['help', '-h', '--help']:
        print_usage()
        sys.exit(0)
        
    else:
        print(f"❌ 未知命令: {command}")
        print()
        print_usage()
        sys.exit(1)


if __name__ == '__main__':
    main()