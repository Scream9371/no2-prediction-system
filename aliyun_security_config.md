# 阿里云ECS安全组配置指南

## 🔒 安全组规则配置

### 目标ECS实例
- **实例ID**: iZbp1cyahargerh8ifamn1Z
- **公网IP**: 8.136.12.26
- **操作系统**: Ubuntu 22.04 64位

### 必需的安全组规则

#### 1. SSH访问（管理用）
```
协议类型: SSH(22)
端口范围: 22/22
授权对象: 0.0.0.0/0 (或您的IP地址)
描述: SSH远程管理
```

#### 2. HTTP访问（Web服务）
```
协议类型: HTTP(80)
端口范围: 80/80
授权对象: 0.0.0.0/0
描述: NO2预测系统Web访问
```

#### 3. HTTPS访问（SSL加密）
```
协议类型: HTTPS(443)
端口范围: 443/443
授权对象: 0.0.0.0/0
描述: NO2预测系统SSL访问
```

## 📋 配置步骤

### 步骤1: 登录阿里云控制台
1. 访问 https://ecs.console.aliyun.com
2. 选择对应地域
3. 找到实例 `iZbp1cyahargerh8ifamn1Z`

### 步骤2: 配置安全组
1. 点击实例ID进入详情页
2. 点击"安全组"标签页
3. 点击安全组ID进入安全组管理
4. 点击"配置规则"

### 步骤3: 添加入方向规则
```bash
# 规则1: SSH
方向: 入方向
优先级: 1
协议类型: SSH(22)
端口范围: 22/22
授权对象: 0.0.0.0/0
描述: SSH管理访问

# 规则2: HTTP
方向: 入方向
优先级: 1
协议类型: HTTP(80)
端口范围: 80/80
授权对象: 0.0.0.0/0
描述: Web服务访问

# 规则3: HTTPS
方向: 入方向
优先级: 1
协议类型: HTTPS(443)
端口范围: 443/443
授权对象: 0.0.0.0/0
描述: SSL Web访问
```

## 🔐 SSH连接配置

### 连接命令
```bash
# 使用密钥连接（推荐）
ssh -i /path/to/your-key.pem ubuntu@8.136.12.26

# 使用密码连接
ssh ubuntu@8.136.12.26
```

### 首次连接后的安全加固
```bash
# 1. 更新系统
sudo apt update && sudo apt upgrade -y

# 2. 配置防火墙
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 3. 安装fail2ban防暴力破解
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## 📊 安全最佳实践

### 1. SSH密钥认证
```bash
# 生成SSH密钥对（在本地执行）
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# 复制公钥到服务器
ssh-copy-id ubuntu@8.136.12.26
```

### 2. 更改默认SSH端口（可选）
```bash
# 编辑SSH配置
sudo nano /etc/ssh/sshd_config

# 修改端口（例如改为2222）
Port 2222

# 重启SSH服务
sudo systemctl restart ssh

# 记得在安全组中添加新端口规则
```

### 3. 配置自动安全更新
```bash
# 安装unattended-upgrades
sudo apt install unattended-upgrades -y

# 启用自动安全更新
sudo dpkg-reconfigure -plow unattended-upgrades
```

## 🌐 域名配置（可选）

### 如果您有域名
1. **DNS解析配置**:
   ```
   A记录: your-domain.com → 8.136.12.26
   CNAME: www.your-domain.com → your-domain.com
   ```

2. **Nginx配置更新**:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com www.your-domain.com;
       # ... 其他配置
   }
   ```

3. **SSL证书配置**:
   ```bash
   # 安装certbot
   sudo apt install certbot python3-certbot-nginx -y
   
   # 获取SSL证书
   sudo certbot --nginx -d your-domain.com -d www.your-domain.com
   ```

## ⚠️ 重要提醒

1. **备份数据**: 定期备份MySQL数据库和应用代码
2. **监控资源**: 关注CPU、内存、磁盘使用情况
3. **日志管理**: 定期清理和轮转日志文件
4. **版本更新**: 保持系统和应用依赖包更新

## 🚨 应急联系

如果遇到访问问题：
1. 检查安全组规则是否正确配置
2. 确认ECS实例状态正常运行
3. 验证服务进程是否启动
4. 查看相关日志文件

---

**配置完成后，您的NO2预测系统将通过以下地址访问:**
- HTTP: http://8.136.12.26
- HTTPS: https://8.136.12.26 (配置SSL后)