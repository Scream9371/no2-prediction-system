# maoyuxuan用户专用部署指南

## 🎯 目标网址
https://maoyuxuan.pythonanywhere.com

## 📋 部署清单

### ✅ 第1步：上传项目文件
在PythonAnywhere的Console中运行：
```bash
# 克隆项目
git clone https://github.com/Scream9371/no2-prediction-system.git
cd no2-prediction-system

# 检查文件是否完整
ls -la
```

### ✅ 第2步：自动环境配置
运行专用设置脚本：
```bash
python3.8 maoyuxuan_setup.py
```

### ✅ 第3步：配置MySQL数据库
1. **进入Databases页面**
2. **设置MySQL密码**（记住这个密码）
3. **创建数据库**：`maoyuxuan$no2prediction`

### ✅ 第4步：更新数据库密码
编辑配置文件，将密码替换为真实值：
```bash
# 编辑WSGI文件
nano maoyuxuan_wsgi.py

# 找到这一行并替换YOUR_MYSQL_PASSWORD
# os.environ['DATABASE_URL'] = 'mysql://maoyuxuan:YOUR_MYSQL_PASSWORD@...'
```

### ✅ 第5步：创建Web应用
1. **进入Web页面**
2. **点击"Add a new web app"**
3. **选择"Manual configuration"**
4. **选择"Python 3.8"**

### ✅ 第6步：配置WSGI文件
在Web应用配置页面：
1. **找到"WSGI configuration file"**
2. **设置路径为**：
   ```
   /home/maoyuxuan/no2-prediction-system/maoyuxuan_wsgi.py
   ```

### ✅ 第7步：设置静态文件（可选）
- **URL**: `/static/`
- **Directory**: `/home/maoyuxuan/no2-prediction-system/web/static/`

### ✅ 第8步：重载应用
点击绿色的**"Reload maoyuxuan.pythonanywhere.com"**按钮

## 🧪 测试访问

访问：https://maoyuxuan.pythonanywhere.com

**预期结果**：
- ✅ 正常情况：显示NO2预测系统主页
- ⚠️ 初始化中：显示"系统正在初始化"页面
- ❌ 错误：查看下方故障排除

## 🐛 故障排除

### 问题1：Import Error
**症状**：页面显示"Flask应用加载失败"
**解决**：
```bash
cd no2-prediction-system
pip3.8 install --user flask sqlalchemy
```

### 问题2：数据库连接失败
**症状**：500错误或数据库相关错误
**解决**：
1. 检查MySQL密码是否正确
2. 确认数据库名称：`maoyuxuan$no2prediction`
3. 重新运行设置脚本

### 问题3：文件路径错误
**症状**：WSGI文件找不到
**解决**：
确认WSGI文件路径完全正确：
```
/home/maoyuxuan/no2-prediction-system/maoyuxuan_wsgi.py
```

### 问题4：依赖包缺失
**症状**：ModuleNotFoundError
**解决**：
```bash
cd no2-prediction-system
pip3.8 install --user -r requirements_pythonanywhere.txt
```

## 📊 系统状态检查

运行诊断脚本：
```bash
cd no2-prediction-system
python3.8 -c "
import sys
print('Python版本:', sys.version)
print('当前目录:', __import__('os').getcwd())
try:
    from app_deploy import app
    print('✅ Flask应用加载成功')
except Exception as e:
    print('❌ Flask应用加载失败:', e)
"
```

## 🎉 成功标志

当您访问 https://maoyuxuan.pythonanywhere.com 时看到：
- 🏠 NO2预测系统主页
- 🌍 城市选择界面
- 📊 预测图表功能

恭喜！您的NO2预测系统已成功部署！

## 📞 需要帮助？

如果遇到问题，请：
1. 检查Web页面的Error log
2. 查看Server log中的详细信息
3. 确认所有配置步骤都已完成
4. 尝试重新运行 `maoyuxuan_setup.py`

---

**部署目标**：https://maoyuxuan.pythonanywhere.com  
**预计部署时间**：10-15分钟  
**技术支持**：查看Error log和Server log进行调试