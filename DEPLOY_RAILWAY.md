# Railway平台部署指南

## 1. 准备工作

### 1.1 注册Railway账户
1. 访问 [railway.app](https://railway.app)
2. 使用GitHub账户登录
3. 验证邮箱地址

### 1.2 安装Railway CLI（可选）
```bash
npm install -g @railway/cli
```

## 2. 部署步骤

### 2.1 上传项目到GitHub
1. 在GitHub创建新仓库
2. 上传项目代码：
```bash
git add .
git commit -m "准备Railway部署"
git push origin main
```

### 2.2 在Railway创建项目
1. 登录Railway控制台
2. 点击"New Project"
3. 选择"Deploy from GitHub repo"
4. 选择您的项目仓库
5. Railway会自动检测到Python项目并开始构建

### 2.3 配置数据库
1. 在Railway项目中点击"Add Service"
2. 选择"Database" → "MySQL"
3. 等待MySQL实例创建完成
4. 复制MySQL连接URL

### 2.4 配置环境变量
在Railway项目设置中添加以下环境变量：
```
DATABASE_URL=<从MySQL服务复制的连接URL>
HF_API_HOST=your_api_host
HF_PROJECT_ID=your_project_id
HF_KEY_ID=your_credential_id
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
```

### 2.5 上传API密钥文件
如果使用ed25519私钥文件：
1. 将私钥内容作为环境变量：
```
HF_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----
...私钥内容...
-----END PRIVATE KEY-----
```

## 3. 部署配置说明

### 3.1 自动部署文件
项目包含以下部署配置文件：
- `railway.json`: Railway平台配置
- `Procfile`: 应用启动命令
- `runtime.txt`: Python版本指定
- `app_deploy.py`: 生产环境启动文件

### 3.2 数据库自动初始化
应用启动时会自动：
1. 检测数据库连接
2. 创建必要的数据表
3. 在连接失败时使用轻量级模式

## 4. 访问应用

部署成功后：
1. Railway会提供一个随机域名（如：`your-app.railway.app`）
2. 访问该域名即可使用应用
3. 可在Railway控制台查看部署日志

## 5. 故障排除

### 5.1 构建失败
- 检查`requirements.txt`是否完整
- 查看构建日志中的错误信息
- 确认Python版本兼容性

### 5.2 数据库连接问题
- 验证`DATABASE_URL`格式正确
- 确认MySQL服务状态正常
- 检查网络连接权限

### 5.3 API访问问题
- 验证和风天气API密钥配置
- 检查API请求限制和余额
- 确认密钥文件格式正确

## 6. 成本控制

Railway免费计划限制：
- 每月500小时运行时间
- 1GB内存限制
- 1GB存储空间

建议：
- 配置应用休眠（无访问时自动停止）
- 监控资源使用情况
- 必要时升级到付费计划

## 7. 备用部署平台

如Railway部署遇到问题，可考虑：
- **Render**: render.com
- **Heroku**: heroku.com
- **PythonAnywhere**: pythonanywhere.com

每个平台的配置方法类似，主要区别在于环境变量设置和数据库配置方式。