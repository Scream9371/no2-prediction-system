"""
部署前最终检查脚本
验证所有部署相关文件和配置
"""
import os
from pathlib import Path

def check_deploy_files():
    """检查部署相关文件"""
    required_files = [
        'railway.json',
        'Procfile', 
        'runtime.txt',
        'app_deploy.py',
        'requirements.txt',
        '.env.example',
        'DEPLOY_RAILWAY.md'
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
        else:
            print(f"[OK] {file}")
    
    if missing_files:
        print(f"[WARNING] 缺少文件: {', '.join(missing_files)}")
        return False
    return True

def check_requirements():
    """检查依赖包"""
    try:
        with open('requirements.txt', 'r') as f:
            content = f.read()
        
        required_packages = ['gunicorn', 'Flask', 'SQLAlchemy']
        missing_packages = []
        
        for pkg in required_packages:
            if pkg.lower() not in content.lower():
                missing_packages.append(pkg)
            else:
                print(f"[OK] {pkg} 已包含")
        
        if missing_packages:
            print(f"[WARNING] 缺少依赖: {', '.join(missing_packages)}")
            return False
        return True
    except FileNotFoundError:
        print("[ERROR] requirements.txt 文件不存在")
        return False

def check_app_structure():
    """检查应用结构"""
    required_dirs = ['web', 'database', 'config']
    missing_dirs = []
    
    for dir_name in required_dirs:
        if not Path(dir_name).exists():
            missing_dirs.append(dir_name)
        else:
            print(f"[OK] {dir_name}/ 目录存在")
    
    if missing_dirs:
        print(f"[WARNING] 缺少目录: {', '.join(missing_dirs)}")
        return False
    return True

def generate_deploy_summary():
    """生成部署摘要"""
    print("\n" + "="*60)
    print("Railway部署配置摘要")
    print("="*60)
    
    print("\n1. 部署文件:")
    print("   - railway.json: Railway平台配置")
    print("   - Procfile: 启动命令配置")
    print("   - runtime.txt: Python版本指定")
    print("   - app_deploy.py: 生产环境启动文件")
    
    print("\n2. 数据库配置:")
    print("   - 支持MySQL和SQLite")
    print("   - 自动数据库表创建")
    print("   - 连接失败时优雅降级")
    
    print("\n3. 环境变量需要设置:")
    print("   - DATABASE_URL (Railway MySQL)")
    print("   - HF_API_HOST (和风天气)")
    print("   - HF_PROJECT_ID")
    print("   - HF_KEY_ID")
    print("   - SECRET_KEY")
    
    print("\n4. 部署步骤:")
    print("   1. 将代码推送到GitHub")
    print("   2. 在Railway中连接GitHub仓库")
    print("   3. 添加MySQL数据库服务")
    print("   4. 配置环境变量")
    print("   5. 等待自动部署完成")
    
    print("\n5. 预估资源使用:")
    print("   - 内存: ~200-400MB")
    print("   - 启动时间: ~30-60秒")
    print("   - 月运行时间: 建议<500小时(免费额度)")

def main():
    """主检查函数"""
    print("开始部署前检查...")
    print("="*50)
    
    checks = [
        ("部署文件检查", check_deploy_files),
        ("依赖包检查", check_requirements), 
        ("应用结构检查", check_app_structure)
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        if not check_func():
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("[SUCCESS] 所有检查通过，可以开始部署！")
        generate_deploy_summary()
    else:
        print("[WARNING] 存在一些问题，建议修复后再部署")
    
    print(f"\n详细部署步骤请参考: DEPLOY_RAILWAY.md")

if __name__ == "__main__":
    main()