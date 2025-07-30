#!/usr/bin/env python3
"""
自动训练定时任务配置脚本

用于在Linux/ECS服务器上配置crontab定时任务，实现自动模型训练。

功能：
- 安装/卸载crontab定时任务
- 检查定时任务状态
- 测试定时任务执行
"""

import os
import sys
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class AutoTrainingCronManager:
    """自动训练定时任务管理器"""
    
    def __init__(self, project_root: Optional[str] = None):
        """
        初始化定时任务管理器
        
        Args:
            project_root (str): 项目根目录，默认自动检测
        """
        if project_root is None:
            self.project_root = Path(__file__).parent.parent.absolute()
        else:
            self.project_root = Path(project_root).absolute()
        
        self.python_path = sys.executable
        self.script_path = self.project_root / 'scripts' / 'auto_training.py'
        
        # 验证脚本存在
        if not self.script_path.exists():
            raise FileNotFoundError(f"自动训练脚本不存在: {self.script_path}")
    
    def get_current_crontab(self) -> List[str]:
        """
        获取当前用户的crontab内容
        
        Returns:
            List[str]: crontab行列表
        """
        try:
            result = subprocess.run(['crontab', '-l'], 
                                  capture_output=True, text=True, check=False)
            if result.returncode == 0:
                return result.stdout.strip().split('\n') if result.stdout.strip() else []
            else:
                return []  # 没有crontab或其他错误
        except FileNotFoundError:
            print("❌ 错误: 系统中未找到crontab命令")
            return []
    
    def has_auto_training_cron(self) -> bool:
        """
        检查是否已经设置了自动训练定时任务
        
        Returns:
            bool: 是否已设置
        """
        crontab_lines = self.get_current_crontab()
        script_name = 'auto_training.py'
        
        for line in crontab_lines:
            if script_name in line and not line.strip().startswith('#'):
                return True
        return False
    
    def install_cron_job(self, hour: int = 3, minute: int = 0) -> bool:
        """
        安装自动训练定时任务
        
        Args:
            hour (int): 执行小时 (0-23)
            minute (int): 执行分钟 (0-59)
            
        Returns:
            bool: 是否安装成功
        """
        try:
            # 检查是否已存在
            if self.has_auto_training_cron():
                print("⚠️  自动训练定时任务已存在")
                return True
            
            # 获取现有crontab
            current_crontab = self.get_current_crontab()
            
            # 创建新的cron任务
            cron_command = f"cd {self.project_root} && {self.python_path} {self.script_path} run"
            cron_line = f"{minute} {hour} * * * {cron_command}"
            
            # 添加注释说明
            comment_line = f"# NO2 Model Auto Training - Added on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # 构建新的crontab内容
            new_crontab = current_crontab + [comment_line, cron_line]
            
            # 写入临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cron', delete=False) as f:
                for line in new_crontab:
                    if line.strip():  # 跳过空行
                        f.write(line + '\n')
                temp_file = f.name
            
            try:
                # 安装新的crontab
                result = subprocess.run(['crontab', temp_file], 
                                      capture_output=True, text=True, check=True)
                
                print("✅ 自动训练定时任务安装成功")
                print(f"   执行时间: 每天 {hour:02d}:{minute:02d}")
                print(f"   执行命令: {cron_command}")
                return True
                
            except subprocess.CalledProcessError as e:
                print(f"❌ 安装定时任务失败: {e.stderr}")
                return False
            finally:
                # 清理临时文件
                os.unlink(temp_file)
                
        except Exception as e:
            print(f"❌ 安装定时任务时发生错误: {str(e)}")
            return False
    
    def remove_cron_job(self) -> bool:
        """
        移除自动训练定时任务
        
        Returns:
            bool: 是否移除成功
        """
        try:
            if not self.has_auto_training_cron():
                print("ℹ️  未找到自动训练定时任务")
                return True
            
            # 获取现有crontab
            current_crontab = self.get_current_crontab()
            
            # 过滤掉相关的任务行
            script_name = 'auto_training.py'
            filtered_crontab = []
            
            skip_next = False
            for line in current_crontab:
                if skip_next and script_name in line:
                    skip_next = False
                    continue
                elif line.strip().startswith('# NO2 Model Auto Training'):
                    skip_next = True
                    continue
                elif script_name in line:
                    continue
                else:
                    filtered_crontab.append(line)
            
            # 写入临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cron', delete=False) as f:
                for line in filtered_crontab:
                    if line.strip():
                        f.write(line + '\n')
                temp_file = f.name
            
            try:
                # 安装过滤后的crontab
                result = subprocess.run(['crontab', temp_file], 
                                      capture_output=True, text=True, check=True)
                
                print("✅ 自动训练定时任务移除成功")
                return True
                
            except subprocess.CalledProcessError as e:
                print(f"❌ 移除定时任务失败: {e.stderr}")
                return False
            finally:
                # 清理临时文件
                os.unlink(temp_file)
                
        except Exception as e:
            print(f"❌ 移除定时任务时发生错误: {str(e)}")
            return False
    
    def show_cron_status(self):
        """显示定时任务状态"""
        print("📋 自动训练定时任务状态:")
        print("-" * 50)
        
        # 检查crontab命令
        try:
            subprocess.run(['crontab', '--help'], capture_output=True, check=False)
            print("✅ crontab命令可用")
        except FileNotFoundError:
            print("❌ crontab命令不可用")
            return
        
        # 检查定时任务
        if self.has_auto_training_cron():
            print("✅ 自动训练定时任务已配置")
            
            # 显示相关的cron行
            crontab_lines = self.get_current_crontab()
            script_name = 'auto_training.py'
            
            print("\n📄 相关定时任务:")
            for line in crontab_lines:
                if script_name in line or line.strip().startswith('# NO2 Model'):
                    print(f"   {line}")
        else:
            print("❌ 自动训练定时任务未配置")
        
        # 检查脚本
        print(f"\n📁 项目信息:")
        print(f"   项目根目录: {self.project_root}")
        print(f"   Python路径: {self.python_path}")
        print(f"   训练脚本: {self.script_path}")
        print(f"   脚本存在: {'✅' if self.script_path.exists() else '❌'}")
        
        # 检查服务状态
        print(f"\n🏥 系统检查:")
        try:
            # 测试脚本健康检查
            result = subprocess.run([
                self.python_path, str(self.script_path), 'health'
            ], capture_output=True, text=True, cwd=str(self.project_root), 
            timeout=30, check=False)
            
            if result.returncode == 0:
                print("✅ 脚本健康检查通过")
            else:
                print("❌ 脚本健康检查失败")
                if result.stderr:
                    print(f"   错误信息: {result.stderr.strip()}")
                    
        except Exception as e:
            print(f"❌ 无法执行健康检查: {str(e)}")
    
    def test_cron_job(self) -> bool:
        """
        测试定时任务执行
        
        Returns:
            bool: 测试是否成功
        """
        print("🧪 测试自动训练脚本执行...")
        
        try:
            # 执行健康检查
            result = subprocess.run([
                self.python_path, str(self.script_path), 'health'
            ], capture_output=True, text=True, cwd=str(self.project_root), 
            timeout=60, check=False)
            
            print("📄 执行输出:")
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("错误输出:")
                print(result.stderr)
            
            if result.returncode == 0:
                print("✅ 测试成功")
                return True
            else:
                print(f"❌ 测试失败 (退出码: {result.returncode})")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ 测试超时")
            return False
        except Exception as e:
            print(f"❌ 测试时发生错误: {str(e)}")
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='自动训练定时任务配置')
    parser.add_argument('action', choices=['install', 'remove', 'status', 'test'],
                       help='操作类型: install=安装, remove=移除, status=查看状态, test=测试')
    parser.add_argument('--hour', type=int, default=3, 
                       help='执行小时 (0-23，默认3)')
    parser.add_argument('--minute', type=int, default=0,
                       help='执行分钟 (0-59，默认0)')
    parser.add_argument('--project-root', type=str,
                       help='项目根目录路径 (默认自动检测)')
    
    args = parser.parse_args()
    
    # 验证时间参数
    if not (0 <= args.hour <= 23):
        print("❌ 错误: 小时必须在0-23之间")
        sys.exit(1)
    
    if not (0 <= args.minute <= 59):
        print("❌ 错误: 分钟必须在0-59之间")
        sys.exit(1)
    
    try:
        manager = AutoTrainingCronManager(args.project_root)
        
        if args.action == 'install':
            success = manager.install_cron_job(args.hour, args.minute)
            sys.exit(0 if success else 1)
            
        elif args.action == 'remove':
            success = manager.remove_cron_job()
            sys.exit(0 if success else 1)
            
        elif args.action == 'status':
            manager.show_cron_status()
            
        elif args.action == 'test':
            success = manager.test_cron_job()
            sys.exit(0 if success else 1)
            
    except Exception as e:
        print(f"❌ 执行失败: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()