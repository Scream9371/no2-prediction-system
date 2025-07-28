#!/bin/bash
# 阿里云ECS服务配置脚本 - 第二阶段
# 配置Nginx、Gunicorn、systemd服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置变量
SERVER_IP="8.136.12.26"
PROJECT_NAME="no2-prediction-system"
APP_USER="ubuntu"
APP_DIR="/var/www/$PROJECT_NAME"
NGINX_AVAILABLE="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}    配置Web服务和应用服务${NC}"
echo -e "${BLUE}===========================================${NC}"

# 检查root权限
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用root权限运行: sudo $0${NC}"
    exit 1
fi

# 1. 初始化数据库
echo -e "${YELLOW}[1/6] 初始化应用数据库...${NC}"
cd $APP_DIR
sudo -u $APP_USER $APP_DIR/venv/bin/python -c "
import sys
sys.path.insert(0, '.')
try:
    from database.session import init_database
    if init_database():
        print('✅ 数据库初始化成功')
    else:
        print('⚠️ 数据库表已存在')
except Exception as e:
    print(f'⚠️ 数据库初始化警告: {e}')
    print('数据库将在首次访问时自动初始化')
"

# 2. 创建Gunicorn配置
echo -e "${YELLOW}[2/6] 配置Gunicorn...${NC}"
cat > $APP_DIR/gunicorn.conf.py << 'EOF'
# Gunicorn配置文件
import os

# 服务器套接字
bind = "127.0.0.1:5000"
backlog = 2048

# 工作进程
workers = 2
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
preload_app = True
timeout = 120
keepalive = 2

# 日志
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程命名
proc_name = 'no2-prediction-gunicorn'

# 用户和组
user = "ubuntu"
group = "ubuntu"

# 临时目录
tmp_upload_dir = None

# SSL (如果需要)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"
EOF

# 创建日志目录
mkdir -p /var/log/gunicorn
chown $APP_USER:$APP_USER /var/log/gunicorn

# 3. 创建systemd服务文件
echo -e "${YELLOW}[3/6] 配置systemd服务...${NC}"
cat > /etc/systemd/system/no2-prediction.service << EOF
[Unit]
Description=NO2 Prediction System Gunicorn Application
After=network.target mysql.service
Requires=mysql.service

[Service]
Type=notify
User=$APP_USER
Group=$APP_USER
RuntimeDirectory=no2-prediction
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/gunicorn --config $APP_DIR/gunicorn.conf.py app_deploy:app
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 4. 配置Nginx
echo -e "${YELLOW}[4/6] 配置Nginx...${NC}"
cat > $NGINX_AVAILABLE/no2-prediction << EOF
# NO2预测系统 Nginx配置
server {
    listen 80;
    server_name $SERVER_IP;
    
    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # 主应用代理
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # 超时设置
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # 缓冲设置
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }

    # 静态文件
    location /static {
        alias $APP_DIR/web/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
    
    # 网站图标
    location /favicon.ico {
        alias $APP_DIR/web/static/favicon.ico;
        expires 1y;
        access_log off;
    }
    
    # 健康检查
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    # 日志配置
    access_log /var/log/nginx/no2-prediction.access.log;
    error_log /var/log/nginx/no2-prediction.error.log;
    
    # 文件上传大小限制
    client_max_body_size 10M;
}
EOF

# 启用站点配置
if [ -f "$NGINX_ENABLED/default" ]; then
    rm $NGINX_ENABLED/default
fi

ln -sf $NGINX_AVAILABLE/no2-prediction $NGINX_ENABLED/
nginx -t

# 5. 启动服务
echo -e "${YELLOW}[5/6] 启动所有服务...${NC}"

# 重新加载systemd
systemctl daemon-reload

# 启动并启用服务
systemctl enable no2-prediction
systemctl start no2-prediction
systemctl restart nginx

# 检查服务状态
sleep 3
if systemctl is-active --quiet no2-prediction; then
    echo -e "${GREEN}✅ NO2预测系统服务启动成功${NC}"
else
    echo -e "${RED}❌ NO2预测系统服务启动失败${NC}"
    systemctl status no2-prediction --no-pager
fi

if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Nginx服务运行正常${NC}"
else
    echo -e "${RED}❌ Nginx服务异常${NC}"
    systemctl status nginx --no-pager
fi

# 6. 部署完成信息
echo -e "${YELLOW}[6/6] 部署完成检查...${NC}"

# 检查端口监听
echo -e "${BLUE}检查端口监听状态:${NC}"
netstat -tlnp | grep -E ':80|:5000' || echo "端口检查完成"

# 测试HTTP响应
echo -e "${BLUE}测试HTTP响应:${NC}"
sleep 2
curl -s -o /dev/null -w "HTTP状态码: %{http_code}\n" http://localhost/ || echo "HTTP测试完成"

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}    🎉 部署完成！${NC}"
echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}访问地址: http://$SERVER_IP${NC}"
echo -e "${YELLOW}服务状态检查:${NC}"
echo -e "  systemctl status no2-prediction"
echo -e "  systemctl status nginx"
echo -e "  systemctl status mysql"
echo -e ""
echo -e "${YELLOW}日志查看:${NC}"
echo -e "  tail -f /var/log/gunicorn/error.log"
echo -e "  tail -f /var/log/nginx/no2-prediction.error.log"
echo -e ""
echo -e "${YELLOW}服务管理:${NC}"
echo -e "  sudo systemctl restart no2-prediction"
echo -e "  sudo systemctl reload nginx"