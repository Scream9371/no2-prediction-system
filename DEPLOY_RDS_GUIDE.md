# 阿里云ECS + RDS云数据库部署指南

## 🎯 部署架构

**ECS + RDS架构**：
```
Internet → 阿里云安全组 → Nginx → Gunicorn → Flask应用 ──网络──→ RDS MySQL
```

**服务器配置**：
- **ECS实例**: iZbp1cyahargerh8ifamn1Z
- **ECS IP**: 8.136.12.26
- **RDS地址**: rm-bp15v1h0r46qac7rvso.mysql.rds.aliyuncs.com
- **RDS端口**: 3306

## 🚀 部署优势

### 使用RDS的好处
- ✅ **免去MySQL安装配置复杂性**
- ✅ **专业数据库运维支持**
- ✅ **自动备份和恢复**
- ✅ **高可用性和容灾能力**  
- ✅ **按需扩容和性能优化**
- ✅ **安全防护和访问控制**

### 与本地MySQL对比
| 特性 | 本地MySQL | 阿里云RDS |
|------|-----------|-----------|
| 安装配置 | 复杂，易出错 | 开箱即用 |
| 运维管理 | 需手动维护 | 托管服务 |
| 数据备份 | 需自己实现 | 自动备份 |
| 高可用性 | 单点故障 | 主从复制 |
| 性能监控 | 需额外工具 | 内置监控 |
| 安全性 | 需手动配置 | 企业级安全 |

## 📋 部署步骤

### 前期准备

#### 1. RDS实例准备
1. **登录阿里云RDS控制台**
2. **确认RDS实例状态为"运行中"**
3. **记录RDS连接信息**：
   - 外网地址：`rm-bp15v1h0r46qac7rvso.mysql.rds.aliyuncs.com`
   - 端口：`3306`
   - 主账户用户名（通常是root）
   - 主账户密码

#### 2. 网络安全配置
1. **RDS安全组配置**：
   - 允许ECS IP `8.136.12.26` 访问3306端口
   - 或允许ECS所在的安全组访问

2. **ECS安全组配置**：
   - 确保出站规则允许访问RDS（3306端口）

### 快速部署

#### 第一阶段：基础环境部署
```bash
# 1. SSH连接ECS服务器
ssh ubuntu@8.136.12.26

# 2. 克隆项目代码
git clone https://github.com/Scream9371/no2-prediction-system.git
cd no2-prediction-system

# 3. 执行基础环境部署（不安装MySQL）
sudo chmod +x deploy_aliyun_ecs_rds.sh
sudo ./deploy_aliyun_ecs_rds.sh
```

#### 第二阶段：RDS数据库配置
```bash
# 1. 配置RDS连接信息
nano setup_rds_database.py

# 在RDS_CONFIG中填入您的RDS主账户密码：
# RDS_CONFIG = {
#     'host': 'rm-bp15v1h0r46qac7rvso.mysql.rds.aliyuncs.com',
#     'port': 3306,
#     'user': 'root',  # 您的RDS主账户用户名
#     'password': 'YOUR_RDS_PASSWORD',  # 填入实际密码
#     ...
# }

# 2. 执行RDS数据库初始化
python setup_rds_database.py
```

#### 第三阶段：应用服务配置
```bash
# 配置Web服务和启动应用
sudo chmod +x setup_services_rds.sh
sudo ./setup_services_rds.sh
```

### 配置验证

#### 测试RDS连接
```bash
# 1. 直接测试RDS连接
mysql -h rm-bp15v1h0r46qac7rvso.mysql.rds.aliyuncs.com -P 3306 -u no2user -p no2_prediction

# 2. 通过API测试连接
curl http://localhost/api/debug/database

# 3. 查看RDS配置信息  
curl http://localhost/api/debug/rds-info

# 4. 查看数据库表结构
curl http://localhost/api/debug/tables
```

#### 服务状态检查
```bash
# 检查所有服务状态
sudo systemctl status no2-prediction nginx

# 查看应用日志
sudo tail -f /var/log/gunicorn/error.log

# 检查端口监听
sudo netstat -tlnp | grep -E ':80|:5000'
```

## 🔧 配置详情

### RDS连接配置
```bash
# 数据库连接字符串
DATABASE_URL=mysql+pymysql://no2user:NO2User2025!@rm-bp15v1h0r46qac7rvso.mysql.rds.aliyuncs.com:3306/no2_prediction

# RDS配置信息
RDS_HOST=rm-bp15v1h0r46qac7rvso.mysql.rds.aliyuncs.com
RDS_PORT=3306
RDS_DATABASE=no2_prediction
RDS_USER=no2user
```

### 应用数据库用户
```sql
-- 自动创建的应用数据库用户
用户名: no2user
密码: NO2User2025!
权限: no2_prediction数据库的完全访问权限
主机: %（允许从任何IP连接）
```

### Nginx配置差异
```nginx
# RDS版本特殊配置
location /rds-status {
    proxy_pass http://127.0.0.1:5000/api/debug/database;
}

# 更长的超时时间（考虑网络延迟）
proxy_connect_timeout 60s;
proxy_send_timeout 60s;
proxy_read_timeout 60s;
```

## 🐛 故障排除

### 常见问题及解决方案

#### 1. RDS连接超时
**症状**：`Connection timed out` 或 `Can't connect to MySQL server`

**解决方案**：
```bash
# 检查网络连通性
ping rm-bp15v1h0r46qac7rvso.mysql.rds.aliyuncs.com

# 检查端口连通性
telnet rm-bp15v1h0r46qac7rvso.mysql.rds.aliyuncs.com 3306

# 检查安全组规则
# 1. RDS安全组是否允许ECS IP访问
# 2. ECS安全组出站规则是否允许访问3306端口
```

#### 2. RDS认证失败
**症状**：`Access denied for user` 或 `Authentication failed`

**解决方案**：
```bash
# 1. 检查用户名密码是否正确
# 2. 确认RDS实例状态正常
# 3. 检查用户是否已创建：
mysql -h rm-bp15v1h0r46qac7rvso.mysql.rds.aliyuncs.com -P 3306 -u root -p
> SELECT User, Host FROM mysql.user WHERE User='no2user';

# 4. 重新创建用户（如果需要）
python setup_rds_database.py
```

#### 3. 应用启动失败
**症状**：`systemctl status no2-prediction` 显示failed

**解决方案**：
```bash
# 查看详细错误日志
sudo journalctl -u no2-prediction -f

# 检查环境变量配置
cat /var/www/no2-prediction-system/.env

# 手动测试应用启动
cd /var/www/no2-prediction-system
sudo -u ubuntu ./venv/bin/python app_deploy.py
```

#### 4. 数据库表不存在
**症状**：`Table 'no2_prediction.xxx' doesn't exist`

**解决方案**：
```bash
# 手动初始化数据库表
cd /var/www/no2-prediction-system
python -c "
import sys
sys.path.insert(0, '.')
from database.session import init_database
init_database()
"

# 或重新运行数据库设置
python setup_rds_database.py
```

### 调试工具

#### RDS连接测试脚本
```bash
# 创建快速测试脚本
cat > test_rds.py << 'EOF'
import mysql.connector
try:
    conn = mysql.connector.connect(
        host='rm-bp15v1h0r46qac7rvso.mysql.rds.aliyuncs.com',
        port=3306,
        user='no2user',
        password='NO2User2025!',
        database='no2_prediction'
    )
    print("✅ RDS连接成功!")
    cursor = conn.cursor()
    cursor.execute("SELECT VERSION()")
    print(f"MySQL版本: {cursor.fetchone()[0]}")
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print(f"数据表数量: {len(tables)}")
    conn.close()
except Exception as e:
    print(f"❌ RDS连接失败: {e}")
EOF

python test_rds.py
```

## 📊 性能监控

### RDS性能指标
- **连接数**: 监控当前活跃连接数
- **CPU使用率**: RDS实例CPU使用情况
- **内存使用率**: 内存占用情况
- **IOPS**: 磁盘读写性能
- **网络流量**: 入站出站流量

### 应用性能指标
- **响应时间**: 包含网络延迟的总响应时间
- **数据库查询时间**: 单独的SQL执行时间
- **连接池状态**: SQLAlchemy连接池使用情况

### 监控命令
```bash
# 应用性能监控
sudo ./monitor_services.sh

# 查看RDS连接状态
curl -s http://localhost/api/debug/database | jq .

# 查看应用实时日志
sudo tail -f /var/log/gunicorn/error.log | grep -i rds
```

## 🔒 安全最佳实践

### RDS安全配置
1. **网络隔离**: 使用专有网络VPC隔离
2. **访问控制**: 精确配置IP白名单
3. **SSL加密**: 启用SSL连接加密
4. **审计日志**: 开启SQL审计功能

### 应用安全配置
1. **连接加密**: 使用SSL连接RDS
2. **密码安全**: 定期更换数据库密码
3. **权限最小化**: 应用用户仅授予必要权限
4. **连接池限制**: 控制并发连接数

## 🚀 扩展和优化

### 性能优化建议
1. **读写分离**: 使用RDS只读实例
2. **连接池优化**: 调整SQLAlchemy连接池参数
3. **查询优化**: 添加适当的数据库索引
4. **缓存策略**: 使用Redis缓存热点数据

### 高可用部署
1. **多可用区部署**: RDS跨可用区部署
2. **ECS集群**: 多台ECS负载均衡
3. **备份策略**: 定期备份和异地容灾
4. **监控告警**: 完善的监控和自动告警

---

## 📞 技术支持

### 访问地址
- **生产地址**: http://8.136.12.26
- **RDS状态检查**: http://8.136.12.26/api/debug/database
- **配置信息查看**: http://8.136.12.26/api/debug/rds-info

### 关键日志位置
- **应用日志**: `/var/log/gunicorn/error.log`
- **Nginx日志**: `/var/log/nginx/no2-prediction.error.log`
- **系统日志**: `sudo journalctl -u no2-prediction`

### 重要配置文件
- **环境变量**: `/var/www/no2-prediction-system/.env`
- **Gunicorn配置**: `/var/www/no2-prediction-system/gunicorn.conf.py`
- **Nginx配置**: `/etc/nginx/sites-available/no2-prediction`

**部署完成后，您的NO2预测系统将稳定运行在ECS+RDS架构上，具备企业级的可靠性和可扩展性！**