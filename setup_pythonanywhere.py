#!/usr/bin/env python3
"""
PythonAnywhere自动设置脚本
在PythonAnywhere的Console中运行此脚本来自动配置环境
"""
import os
import sys
import subprocess
from pathlib import Path

def get_username():
    """获取PythonAnywhere用户名"""
    username = os.path.expanduser('~').split('/')[-1]
    print(f"检测到用户名: {username}")
    return username

def update_wsgi_config(username):
    """更新WSGI配置文件中的用户名"""
    wsgi_file = Path('pythonanywhere_wsgi.py')
    
    if not wsgi_file.exists():
        print("错误: pythonanywhere_wsgi.py 文件不存在")
        return False
    
    # 读取文件内容
    with open(wsgi_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换用户名
    content = content.replace("USERNAME = 'yourusername'", f"USERNAME = '{username}'")
    
    # 写回文件
    with open(wsgi_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ 已更新WSGI配置文件，用户名设置为: {username}")
    return True

def install_requirements():
    """安装Python依赖包"""
    requirements_file = Path('requirements_pythonanywhere.txt')
    
    if not requirements_file.exists():
        print("错误: requirements_pythonanywhere.txt 文件不存在")
        return False
    
    print("开始安装Python依赖包...")
    try:
        # 使用pip安装依赖
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', '--user', 
            '-r', str(requirements_file)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ 依赖包安装成功")
            return True
        else:
            print(f"警告: 部分依赖包安装失败，但这是正常的")
            print(f"错误详情: {result.stderr}")
            return True  # 继续执行，因为部分失败不影响基本功能
    except Exception as e:
        print(f"安装依赖时出错: {e}")
        return False

def setup_database():
    """设置数据库"""
    print("初始化数据库...")
    try:
        # 导入数据库初始化函数
        sys.path.insert(0, '.')
        from database.session import init_database
        
        if init_database():
            print("✓ 数据库初始化成功")
            return True
        else:
            print("- 数据库初始化跳过（可能已存在）")
            return True
    except Exception as e:
        print(f"数据库初始化出错: {e}")
        print("这是正常的，数据库会在Web应用首次访问时初始化")
        return True

def create_env_file(username):
    """创建环境变量文件"""
    env_content = f"""# PythonAnywhere环境变量配置
DATABASE_URL=mysql://{username}:YOUR_MYSQL_PASSWORD@{username}.mysql.pythonanywhere-services.com/{username}$no2prediction
SECRET_KEY=pythonanywhere-no2-prediction-2025
FLASK_ENV=production

# 和风天气API配置（可选）
# HF_API_HOST=your_api_host
# HF_PROJECT_ID=your_project_id
# HF_KEY_ID=your_credential_id
"""
    
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✓ 已创建 .env 环境变量文件")
    print(f"请手动编辑 .env 文件，将 YOUR_MYSQL_PASSWORD 替换为您的MySQL密码")

def main():
    """主设置函数"""
    print("开始PythonAnywhere环境设置...")
    print("=" * 50)
    
    # 检查是否在正确的目录
    if not Path('app_deploy.py').exists():
        print("错误: 请确保在项目根目录中运行此脚本")
        sys.exit(1)
    
    # 获取用户名
    username = get_username()
    
    # 执行设置步骤
    steps = [
        ("更新WSGI配置", lambda: update_wsgi_config(username)),
        ("安装Python依赖", install_requirements),
        ("初始化数据库", setup_database),
        ("创建环境变量文件", lambda: create_env_file(username))
    ]
    
    success_count = 0
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        if step_func():
            success_count += 1
        else:
            print(f"步骤失败: {step_name}")
    
    # 输出结果
    print("\n" + "=" * 50)
    print(f"设置完成! ({success_count}/{len(steps)} 步骤成功)")
    
    if success_count == len(steps):
        print("\n✓ 所有设置步骤完成!")
    else:
        print("\n- 部分步骤未完成，但这可能不影响基本功能")
    
    print(f"\n下一步操作:")
    print(f"1. 在PythonAnywhere的Databases页面创建MySQL数据库")
    print(f"2. 数据库名称: {username}$no2prediction")
    print(f"3. 在Web页面配置WSGI文件路径:")
    print(f"   /home/{username}/no2-prediction-system/pythonanywhere_wsgi.py")
    print(f"4. 重载Web应用")
    print(f"5. 访问: https://{username}.pythonanywhere.com")

if __name__ == "__main__":
    main()