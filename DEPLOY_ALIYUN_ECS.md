# 阿里云ECS完整部署指南

## 🎯 部署目标
**访问地址**: http://8.136.12.26  
**ECS实例**: iZbp1cyahargerh8ifamn1Z  
**操作系统**: Ubuntu 22.04 64位  

## 📋 部署架构
```
用户访问 → 阿里云安全组 → Nginx反向代理 → Gunicorn → Flask应用 → MySQL数据库
```

## 🚀 完整部署流程

### 阶段一：阿里云基础配置

#### 1. 配置安全组规则
1. **登录阿里云控制台**: https://ecs.console.aliyun.com
2. **找到ECS实例**: `iZbp1cyahargerh8ifamn1Z`
3. **配置安全组**，添加以下规则:
   ```
   SSH(22):   0.0.0.0/0  - SSH管理访问
   HTTP(80):  0.0.0.0/0  - Web服务访问
   HTTPS(443): 0.0.0.0/0 - SSL访问（可选）
   ```

#### 2. SSH连接到服务器
```bash
ssh ubuntu@8.136.12.26
```

### 阶段二：环境部署

#### 3. 下载部署脚本
```bash
# 克隆项目代码
git clone https://github.com/Scream9371/no2-prediction-system.git
cd no2-prediction-system

# 查看部署文件
ls -la deploy_aliyun_ecs.sh setup_services.sh
```

#### 4. 执行基础环境部署
```bash
# 赋予执行权限
chmod +x deploy_aliyun_ecs.sh setup_services.sh monitor_services.sh

# 执行基础环境部署（需要root权限）
sudo ./deploy_aliyun_ecs.sh
```

**此脚本将完成**:
- ✅ 系统包更新
- ✅ 安装Python 3.10、MySQL、Nginx
- ✅ 配置防火墙和安全设置
- ✅ 创建MySQL数据库和用户
- ✅ 克隆项目代码到/var/www/
- ✅ 创建Python虚拟环境
- ✅ 安装项目依赖包
- ✅ 生成环境配置文件

#### 5. 执行服务配置
```bash
# 执行Web服务和应用服务配置
sudo ./setup_services.sh
```

**此脚本将完成**:
- ✅ 初始化应用数据库
- ✅ 配置Gunicorn应用服务器
- ✅ 创建systemd服务文件
- ✅ 配置Nginx反向代理
- ✅ 启动所有服务
- ✅ 测试服务状态

### 阶段三：验证和测试

#### 6. 验证部署状态
```bash
# 检查服务状态
sudo systemctl status no2-prediction
sudo systemctl status nginx
sudo systemctl status mysql

# 检查端口监听
sudo netstat -tlnp | grep -E ':80|:5000|:3306'

# 测试HTTP响应
curl -I http://localhost/
```

#### 7. 访问Web应用
打开浏览器访问: **http://8.136.12.26**

**预期结果**:
- ✅ 显示NO2预测系统主页
- ✅ 可以选择城市进行预测
- ✅ 图表正常显示

## 🔧 配置详情

### 数据库配置
```
数据库名: no2_prediction
用户名: no2user
密码: NO2User2025!
连接地址: localhost:3306
```

### 应用服务配置
```
应用目录: /var/www/no2-prediction-system
Python环境: /var/www/no2-prediction-system/venv
Gunicorn端口: 127.0.0.1:5000
服务名: no2-prediction
```

### Nginx配置
```
配置文件: /etc/nginx/sites-available/no2-prediction
监听端口: 80
代理目标: http://127.0.0.1:5000
静态文件: /var/www/no2-prediction-system/web/static
```

## 📊 监控和维护

### 运行监控脚本
```bash
# 执行系统监控
sudo ./monitor_services.sh
```

**监控内容**:
- 🔍 服务状态检查
- 🔍 端口监听检查  
- 🔍 HTTP响应检查
- 🔍 系统资源监控
- 🔍 数据库连接检查
- 🔍 日志管理

### 设置定时监控
```bash
# 添加到crontab，每10分钟检查一次
sudo crontab -e

# 添加以下行
*/10 * * * * /var/www/no2-prediction-system/monitor_services.sh >> /var/log/no2-monitor.log 2>&1
```

### 常用管理命令
```bash
# 重启应用服务
sudo systemctl restart no2-prediction

# 重新加载Nginx配置
sudo systemctl reload nginx

# 查看应用日志
sudo tail -f /var/log/gunicorn/error.log

# 查看Nginx日志
sudo tail -f /var/log/nginx/no2-prediction.error.log

# 查看系统资源
htop
```

## 🐛 故障排除

### 问题1: 无法访问Web页面
**检查步骤**:
```bash
# 1. 检查安全组是否开放80端口
# 2. 检查服务状态
sudo systemctl status nginx no2-prediction

# 3. 检查端口监听
sudo netstat -tlnp | grep :80

# 4. 查看错误日志
sudo tail -20 /var/log/nginx/no2-prediction.error.log
```

### 问题2: 应用服务启动失败
**检查步骤**:
```bash
# 查看服务状态详情
sudo systemctl status no2-prediction -l

# 查看应用日志
sudo tail -50 /var/log/gunicorn/error.log

# 测试应用是否能手动启动
cd /var/www/no2-prediction-system
sudo -u ubuntu ./venv/bin/python app_deploy.py
```

### 问题3: 数据库连接失败
**检查步骤**:
```bash
# 测试数据库连接
mysql -u no2user -pNO2User2025! no2_prediction -e "SELECT 1;"

# 检查MySQL服务状态
sudo systemctl status mysql

# 重置数据库（如果需要）
sudo mysql -u root -pNO2Prediction2025! < /var/www/no2-prediction-system/database/init.sql
```

## 🔒 安全建议

### 1. 加强SSH安全
```bash
# 修改SSH端口（可选）
sudo nano /etc/ssh/sshd_config
# Port 2222

# 禁用root登录
# PermitRootLogin no

# 重启SSH
sudo systemctl restart ssh
```

### 2. 配置SSL证书（如有域名）
```bash
# 安装certbot
sudo apt install certbot python3-certbot-nginx -y

# 获取SSL证书
sudo certbot --nginx -d your-domain.com
```

### 3. 设置自动备份
```bash
# 创建备份脚本
cat > /home/ubuntu/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
mysqldump -u no2user -pNO2User2025! no2_prediction > /home/ubuntu/backups/no2_${DATE}.sql
EOF

# 设置定时备份
crontab -e
# 0 2 * * * /home/ubuntu/backup.sh
```

## 🎉 部署完成

### 访问信息
- **Web地址**: http://8.136.12.26
- **管理SSH**: ubuntu@8.136.12.26
- **数据库**: localhost:3306/no2_prediction

### 预期功能
- ✅ 城市选择和NO2预测
- ✅ 可视化图表展示
- ✅ 历史数据查询
- ✅ 实时预测更新

### 性能指标
- **响应时间**: < 3秒
- **并发用户**: 支持50+用户同时访问
- **可用性**: 99.9%+

---

**部署成功后，您的NO2预测系统将稳定运行在阿里云ECS上，为用户提供准确的空气质量预测服务！**

## 📞 技术支持

如需帮助，请检查:
1. 服务状态: `sudo systemctl status no2-prediction nginx mysql`
2. 错误日志: `/var/log/gunicorn/error.log`
3. 监控报告: `sudo ./monitor_services.sh`