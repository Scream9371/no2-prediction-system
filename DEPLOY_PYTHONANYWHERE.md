# PythonAnywhere部署指南

## 前期准备

### 1. 注册账户
1. 访问 https://www.pythonanywhere.com
2. 选择"Create a Beginner account"（免费）
3. 记住您的用户名，后续配置需要用到

### 2. 免费账户限制
- CPU时间：100秒/天
- 存储空间：512MB
- Web应用：1个
- MySQL数据库：1个（20MB）

## 部署步骤

### 步骤1：上传项目文件

#### 方法A：直接上传（推荐新手）
1. 登录PythonAnywhere控制台
2. 点击"Files"标签页
3. 创建目录：`no2-prediction-system`
4. 上传以下核心文件：
   ```
   app_deploy.py
   pythonanywhere_wsgi.py
   requirements_pythonanywhere.txt
   web/
   database/
   config/
   ml/
   ```

#### 方法B：Git克隆（推荐有经验用户）
1. 点击"Consoles"标签页
2. 启动"Bash console"
3. 运行命令：
   ```bash
   git clone https://github.com/Scream9371/no2-prediction-system.git
   cd no2-prediction-system
   ```

### 步骤2：修改配置文件

1. **修改pythonanywhere_wsgi.py**：
   - 将`yourusername`替换为您的实际用户名
   - 更新数据库密码

2. **创建.env文件**（可选）：
   ```bash
   # 在Files界面创建.env文件
   DATABASE_URL=mysql://用户名:密码@用户名.mysql.pythonanywhere-services.com/用户名$no2prediction
   SECRET_KEY=your-secret-key
   ```

### 步骤3：配置MySQL数据库

1. **创建数据库**：
   - 点击"Databases"标签页
   - 设置MySQL密码
   - 创建数据库：`用户名$no2prediction`

2. **初始化数据表**：
   在Console中运行：
   ```bash
   cd no2-prediction-system
   python3.8 -c "from database.session import init_database; init_database()"
   ```

### 步骤4：安装Python依赖

在Bash console中运行：
```bash
cd no2-prediction-system
pip3.8 install --user -r requirements_pythonanywhere.txt
```

**注意**：如果某些包安装失败（如torch），可以忽略，系统会自动降级到轻量模式。

### 步骤5：配置Web应用

1. **创建Web应用**：
   - 点击"Web"标签页
   - 点击"Add a new web app"
   - 选择"Manual configuration"
   - 选择"Python 3.8"

2. **配置WSGI文件**：
   - 在"Code"部分找到"WSGI configuration file"
   - 将路径设置为：`/home/用户名/no2-prediction-system/pythonanywhere_wsgi.py`

3. **设置静态文件**（可选）：
   - URL: `/static/`
   - Directory: `/home/用户名/no2-prediction-system/web/static/`

### 步骤6：重载并测试

1. **重载Web应用**：
   - 在Web标签页点击绿色"Reload"按钮

2. **访问应用**：
   - 您的应用将在：`https://用户名.pythonanywhere.com`

## 故障排除

### 常见问题

1. **Import错误**：
   - 检查WSGI文件中的路径是否正确
   - 确认用户名替换正确

2. **数据库连接失败**：
   - 验证数据库密码
   - 确认数据库名格式：`用户名$no2prediction`

3. **依赖包缺失**：
   - 在Console中重新安装：`pip3.8 install --user 包名`
   - 检查requirements_pythonanywhere.txt

4. **CPU时间超限**：
   - 优化代码减少计算量
   - 考虑升级到付费账户

### 调试方法

1. **查看错误日志**：
   - Web标签页的"Error log"
   - Server log中的详细信息

2. **测试WSGI文件**：
   ```bash
   cd no2-prediction-system
   python3.8 pythonanywhere_wsgi.py
   ```

## 优化建议

### 性能优化
1. **启用轻量模式**：
   - 如果ML模型加载失败，系统会自动使用示例数据
   - 适合演示和测试

2. **数据库优化**：
   - 限制历史数据量
   - 使用数据库索引

### 升级选项
- **Hacker计划**（$5/月）：更多CPU时间和存储
- **Web Developer计划**（$12/月）：无限制使用

## 部署检查清单

- [ ] 账户注册完成
- [ ] 项目文件上传
- [ ] 用户名替换正确
- [ ] MySQL数据库创建
- [ ] 依赖包安装
- [ ] WSGI文件配置
- [ ] Web应用重载
- [ ] 访问测试成功

部署成功后，您的NO2预测系统将在 `https://用户名.pythonanywhere.com` 上运行！