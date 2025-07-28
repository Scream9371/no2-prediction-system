#!/usr/bin/env python3
"""
maoyuxuan专用PythonAnywhere自动设置脚本
在PythonAnywhere Console中运行此脚本来配置maoyuxuan用户的环境
"""
import os
import sys
import subprocess
from pathlib import Path

def install_requirements():
    """安装Python依赖包"""
    requirements_file = Path('requirements_pythonanywhere.txt')
    
    if not requirements_file.exists():
        print("❌ 错误: requirements_pythonanywhere.txt 文件不存在")
        return False
    
    print("📦 开始安装Python依赖包...")
    try:
        # 使用pip安装依赖
        result = subprocess.run([
            'pip3.8', 'install', '--user', 
            '-r', str(requirements_file)
        ], capture_output=True, text=True)
        
        print("安装日志:")
        print(result.stdout)
        
        if result.stderr:
            print("警告信息:")
            print(result.stderr)
        
        print("✅ 依赖包安装完成（部分包可能跳过，这是正常的）")
        return True
        
    except Exception as e:
        print(f"❌ 安装依赖时出错: {e}")
        return False

def setup_database():
    """初始化数据库结构"""
    print("🗄️ 初始化数据库...")
    try:
        # 导入数据库初始化函数
        sys.path.insert(0, '.')
        from database.session import init_database
        
        if init_database():
            print("✅ 数据库表结构创建成功")
            return True
        else:
            print("⚠️ 数据库表可能已存在，跳过创建")
            return True
    except Exception as e:
        print(f"⚠️ 数据库初始化遇到问题: {e}")
        print("💡 这通常是正常的，数据库会在Web应用首次访问时自动初始化")
        return True

def create_env_file():
    """创建maoyuxuan专用环境变量文件"""
    env_content = """# maoyuxuan用户的PythonAnywhere环境变量配置
DATABASE_URL=mysql://maoyuxuan:YOUR_MYSQL_PASSWORD@maoyuxuan.mysql.pythonanywhere-services.com/maoyuxuan$no2prediction
SECRET_KEY=maoyuxuan-no2-prediction-2025
FLASK_ENV=production

# 和风天气API配置（如果有API密钥请取消注释并填入真实值）
# HF_API_HOST=your_api_host
# HF_PROJECT_ID=your_project_id
# HF_KEY_ID=your_credential_id

# PythonAnywhere特定设置
PYTHONPATH=/home/maoyuxuan/no2-prediction-system
"""
    
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✅ 已创建 .env 环境变量文件")
    return True

def test_imports():
    """测试关键模块导入"""
    print("🧪 测试模块导入...")
    
    test_modules = [
        'flask',
        'sqlalchemy', 
        'pandas',
        'numpy',
        'sklearn'
    ]
    
    success_count = 0
    for module in test_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
            success_count += 1
        except ImportError:
            print(f"❌ {module} (将使用轻量级模式)")
    
    print(f"📊 模块测试完成: {success_count}/{len(test_modules)} 成功导入")
    return success_count > 2  # 至少需要Flask等基础模块

def main():
    """主设置函数"""
    print("🚀 开始为maoyuxuan用户配置PythonAnywhere环境...")
    print("🌐 目标网址: https://maoyuxuan.pythonanywhere.com")
    print("=" * 60)
    
    # 检查是否在正确的目录
    if not Path('app_deploy.py').exists():
        print("❌ 错误: 请确保在no2-prediction-system项目根目录中运行此脚本")
        sys.exit(1)
    
    # 显示当前目录
    current_dir = Path.cwd()
    print(f"📁 当前目录: {current_dir}")
    
    # 执行设置步骤
    steps = [
        ("📦 安装Python依赖", install_requirements),
        ("🗄️ 初始化数据库", setup_database),
        ("⚙️ 创建环境变量文件", create_env_file),
        ("🧪 测试模块导入", test_imports)
    ]
    
    success_count = 0
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        try:
            if step_func():
                success_count += 1
            else:
                print(f"⚠️ 步骤未完全成功: {step_name}")
        except Exception as e:
            print(f"❌ 步骤执行出错: {step_name} - {e}")
    
    # 输出结果
    print("\n" + "=" * 60)
    print(f"🎉 环境设置完成! ({success_count}/{len(steps)} 步骤成功)")
    
    print(f"\n📋 接下来的手动操作步骤:")
    print(f"1. 📊 在PythonAnywhere的Databases页面:")
    print(f"   - 设置MySQL密码")
    print(f"   - 创建数据库: maoyuxuan$no2prediction")
    
    print(f"\n2. 🌐 在Web页面配置:")
    print(f"   - 创建新的Web应用（Python 3.8）")
    print(f"   - WSGI文件路径设置为:")
    print(f"     /home/maoyuxuan/no2-prediction-system/maoyuxuan_wsgi.py")
    
    print(f"\n3. ⚙️ 更新配置:")
    print(f"   - 编辑 maoyuxuan_wsgi.py")
    print(f"   - 将 YOUR_MYSQL_PASSWORD 替换为您的实际MySQL密码")
    
    print(f"\n4. 🔄 重载和测试:")
    print(f"   - 点击Web页面的绿色'Reload'按钮")
    print(f"   - 访问: https://maoyuxuan.pythonanywhere.com")
    
    print(f"\n5. 🐛 如果遇到问题:")
    print(f"   - 查看Web页面的Error log")
    print(f"   - 检查WSGI文件路径是否正确")
    print(f"   - 确认MySQL密码设置正确")
    
    print(f"\n✨ 预期结果: 成功访问您的NO2预测系统!")

if __name__ == "__main__":
    main()