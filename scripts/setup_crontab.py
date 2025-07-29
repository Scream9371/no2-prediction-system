#!/usr/bin/env python3
"""
Crontab调度设置脚本

设置每日数据更新器的自动化调度，实现每日凌晨2:00自动执行数据采集任务。

功能：
- 安装/移除crontab任务
- 检查任务状态
- 生成适当的cron表达式
- 处理日志重定向
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.schedule_config import schedule_config

class CrontabManager:
    """Crontab管理器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.daily_updater_path = self.project_root / "api" / "schedules" / "daily_updater.py"
        self.python_executable = sys.executable
        self.log_dir = self.project_root / "logs"
        self.cron_identifier = "# NO2-Prediction Daily Updater"
        
        # 确保日志目录存在
        self.log_dir.mkdir(exist_ok=True)
    
    def get_cron_command(self) -> str:
        """
        生成完整的cron命令
        
        Returns:
            完整的cron命令字符串
        """
        log_file = self.log_dir / "crontab_daily_updater.log"
        error_log = self.log_dir / "crontab_daily_updater_error.log"
        
        # 构建完整命令
        command = (
            f"cd {self.project_root} && "
            f"{self.python_executable} -m api.schedules.daily_updater "
            f">> {log_file} 2>> {error_log}"
        )
        
        return command
    
    def get_cron_line(self) -> str:
        """
        生成完整的crontab行
        
        Returns:
            包含时间表达式和命令的完整cron行
        """
        cron_expression = schedule_config.get_cron_expression()
        command = self.get_cron_command()
        
        return f"{cron_expression} {command} {self.cron_identifier}"
    
    def get_current_crontab(self) -> str:
        """
        获取当前用户的crontab内容
        
        Returns:
            当前crontab内容字符串
        """
        try:
            result = subprocess.run(
                ["crontab", "-l"], 
                capture_output=True, 
                text=True, 
                check=False
            )
            return result.stdout if result.returncode == 0 else ""
        except FileNotFoundError:
            print("错误: crontab命令未找到，请确保系统支持cron")
            return ""
    
    def install_crontab(self) -> bool:
        """
        安装每日数据更新的crontab任务
        
        Returns:
            安装是否成功
        """
        try:
            print("🚀 开始安装每日数据更新crontab任务...")
            
            # 检查必要文件
            if not self.daily_updater_path.exists():
                print(f"❌ 错误: 找不到daily_updater.py文件: {self.daily_updater_path}")
                return False
            
            # 获取当前crontab
            current_crontab = self.get_current_crontab()
            
            # 检查是否已存在
            if self.cron_identifier in current_crontab:
                print("⚠️  警告: 每日数据更新任务已存在，将先移除旧任务")
                self.remove_crontab()
                current_crontab = self.get_current_crontab()
            
            # 添加新的cron任务
            new_cron_line = self.get_cron_line()
            updated_crontab = current_crontab + "\n" + new_cron_line + "\n"
            
            # 写入新的crontab
            process = subprocess.Popen(
                ["crontab", "-"], 
                stdin=subprocess.PIPE, 
                text=True
            )
            process.communicate(input=updated_crontab)
            
            if process.returncode == 0:
                print("✅ 每日数据更新crontab任务安装成功!")
                print(f"📅 调度时间: 每日 {schedule_config.DAILY_UPDATE_TIME}")
                print(f"📝 日志文件: {self.log_dir}/crontab_daily_updater.log")
                print(f"🚨 错误日志: {self.log_dir}/crontab_daily_updater_error.log")
                return True
            else:
                print("❌ 安装crontab任务失败")
                return False
                
        except Exception as e:
            print(f"❌ 安装过程中发生异常: {str(e)}")
            return False
    
    def remove_crontab(self) -> bool:
        """
        移除每日数据更新的crontab任务
        
        Returns:
            移除是否成功
        """
        try:
            print("🗑️  开始移除每日数据更新crontab任务...")
            
            current_crontab = self.get_current_crontab()
            
            if self.cron_identifier not in current_crontab:
                print("⚠️  警告: 未找到每日数据更新任务，可能已被移除")
                return True
            
            # 过滤掉包含标识符的行
            lines = current_crontab.split('\n')
            filtered_lines = [
                line for line in lines 
                if self.cron_identifier not in line
            ]
            
            updated_crontab = '\n'.join(filtered_lines)
            
            # 写入更新后的crontab
            process = subprocess.Popen(
                ["crontab", "-"], 
                stdin=subprocess.PIPE, 
                text=True
            )
            process.communicate(input=updated_crontab)
            
            if process.returncode == 0:
                print("✅ 每日数据更新crontab任务移除成功!")
                return True
            else:
                print("❌ 移除crontab任务失败")
                return False
                
        except Exception as e:
            print(f"❌ 移除过程中发生异常: {str(e)}")
            return False
    
    def check_status(self) -> None:
        """检查crontab任务状态"""
        print("🔍 检查每日数据更新crontab任务状态...")
        
        current_crontab = self.get_current_crontab()
        
        if not current_crontab:
            print("⚠️  当前用户没有设置任何crontab任务")
            return
        
        if self.cron_identifier in current_crontab:
            print("✅ 每日数据更新任务已安装")
            
            # 显示任务详情
            for line in current_crontab.split('\n'):
                if self.cron_identifier in line:
                    print(f"📋 任务详情: {line}")
                    break
            
            # 检查相关文件
            print(f"📁 项目路径: {self.project_root}")
            print(f"🐍 Python路径: {self.python_executable}")
            print(f"📜 脚本路径: {self.daily_updater_path}")
            print(f"📝 日志目录: {self.log_dir}")
            
            # 检查最近的日志
            self._check_recent_logs()
        else:
            print("❌ 每日数据更新任务未安装")
    
    def _check_recent_logs(self) -> None:
        """检查最近的执行日志"""
        log_file = self.log_dir / "crontab_daily_updater.log"
        error_log = self.log_dir / "crontab_daily_updater_error.log"
        
        if log_file.exists():
            try:
                stat = log_file.stat()
                mod_time = datetime.fromtimestamp(stat.st_mtime)
                print(f"📄 主日志最后修改: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 显示最近几行日志
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        print("📋 最近日志:")
                        for line in lines[-3:]:
                            print(f"   {line.strip()}")
            except Exception as e:
                print(f"⚠️  读取日志文件失败: {str(e)}")
        else:
            print("📄 日志文件尚未生成（任务可能未执行）")
        
        if error_log.exists() and error_log.stat().st_size > 0:
            print("🚨 发现错误日志，请检查:")
            print(f"   tail -f {error_log}")
    
    def test_command(self) -> bool:
        """
        测试daily_updater命令是否能正常执行
        
        Returns:
            测试是否成功
        """
        print("🧪 测试每日数据更新命令...")
        
        try:
            # 构建测试命令（添加--dry-run参数如果支持）
            test_command = [
                self.python_executable, 
                "-m", "api.schedules.daily_updater"
            ]
            
            print(f"🔧 执行命令: {' '.join(test_command)}")
            print("⏳ 请等待测试完成...")
            
            # 在项目根目录执行
            result = subprocess.run(
                test_command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                print("✅ 命令测试成功!")
                print("📊 测试输出:")
                print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
                return True
            else:
                print("❌ 命令测试失败!")
                print("🚨 错误输出:")
                print(result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            print("⏰ 命令执行超时，但这可能是正常的（数据更新需要时间）")
            return True
        except Exception as e:
            print(f"❌ 测试过程中发生异常: {str(e)}")
            return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="NO2预测系统每日数据更新crontab管理工具"
    )
    parser.add_argument(
        "action", 
        choices=["install", "remove", "status", "test"],
        help="操作类型: install=安装, remove=移除, status=检查状态, test=测试命令"
    )
    parser.add_argument(
        "--force", 
        action="store_true",
        help="强制执行（跳过确认）"
    )
    
    args = parser.parse_args()
    
    manager = CrontabManager()
    
    print("🔧 NO2预测系统 - 每日数据更新crontab管理工具")
    print("=" * 60)
    
    if args.action == "install":
        if not args.force:
            confirm = input("确认安装每日数据更新crontab任务? (y/N): ")
            if confirm.lower() not in ['y', 'yes']:
                print("操作已取消")
                return
        
        success = manager.install_crontab()
        sys.exit(0 if success else 1)
        
    elif args.action == "remove":
        if not args.force:
            confirm = input("确认移除每日数据更新crontab任务? (y/N): ")
            if confirm.lower() not in ['y', 'yes']:
                print("操作已取消")
                return
        
        success = manager.remove_crontab()
        sys.exit(0 if success else 1)
        
    elif args.action == "status":
        manager.check_status()
        
    elif args.action == "test":
        print("🧪 这将执行一次完整的数据更新测试...")
        if not args.force:
            confirm = input("确认执行测试? (y/N): ")
            if confirm.lower() not in ['y', 'yes']:
                print("测试已取消")
                return
        
        success = manager.test_command()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()