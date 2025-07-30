#!/bin/bash
# 阿里云ECS + RDS服务配置脚本
# 配置Nginx、Gunicorn、systemd服务（使用RDS数据库）

set -e

# 导入用户配置
if [ -f "/tmp/no2_user_config.sh" ]; then
    source /tmp/no2_user_config.sh
else
    # 自动检测用户
    if [ -n "$SUDO_USER" ]; then
        APP_USER="$SUDO_USER"
    else
        APP_USER=$(awk -F: '$3 >= 1000 && $3 != 65534 && $1 != "nobody" {print $1; exit}' /etc/passwd)
        if [ -z "$APP_USER" ]; then
            APP_USER="root"
        fi
    fi
    RDS_HOST="rm-bp15v1h0r46qac7rvso.mysql.rds.aliyuncs.com"
    RDS_PORT="3306"
fi

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置变量
SERVER_IP="8.136.12.26"
PROJECT_NAME="no2-prediction-system"
APP_DIR="/var/www/$PROJECT_NAME"
NGINX_AVAILABLE="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}    配置Web服务和应用服务 (RDS版)${NC}"
echo -e "${BLUE}    应用用户: $APP_USER${NC}"
echo -e "${BLUE}    RDS地址: $RDS_HOST${NC}"
echo -e "${BLUE}===========================================${NC}"

# 检查root权限
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用root权限运行: sudo $0${NC}"
    exit 1
fi

# 验证用户存在
if ! id "$APP_USER" &>/dev/null; then
    echo -e "${RED}用户 $APP_USER 不存在，使用root用户${NC}"
    APP_USER="root"
fi

# 检查.env文件是否存在
if [ ! -f "$APP_DIR/.env" ]; then
    echo -e "${YELLOW}未找到.env配置文件，请先运行 python setup_rds_database.py${NC}"
    if [ -f "$APP_DIR/.env.template" ]; then
        echo -e "${YELLOW}发现.env.template模板文件，是否继续？(y/N)${NC}"
        read -r continue_choice
        if [ "$continue_choice" != "y" ] && [ "$continue_choice" != "Y" ]; then
            echo -e "${RED}请先配置RDS数据库连接${NC}"
            exit 1
        fi
        # 使用模板文件作为临时配置
        cp "$APP_DIR/.env.template" "$APP_DIR/.env"
        echo -e "${YELLOW}使用模板配置继续，请稍后更新数据库连接信息${NC}"
    fi
fi

# 1. 测试RDS连接
echo -e "${YELLOW}[1/6] 测试RDS数据库连接...${NC}"
cd $APP_DIR

# 测试数据库连接
echo -e "${BLUE}测试应用数据库连接...${NC}"
if [ "$APP_USER" = "root" ]; then
    $APP_DIR/venv/bin/python -c "
import sys
sys.path.insert(0, '.')
try:
    from database.session import test_database_connection
    if test_database_connection():
        print('✅ RDS数据库连接成功')
    else:
        print('⚠️ RDS数据库连接失败，请检查配置')
except Exception as e:
    print(f'⚠️ 数据库连接测试出错: {e}')
    print('💡 应用将在首次访问时尝试连接数据库')
"
else
    sudo -u $APP_USER $APP_DIR/venv/bin/python -c "
import sys
sys.path.insert(0, '.')
try:
    from database.session import test_database_connection
    if test_database_connection():
        print('✅ RDS数据库连接成功')
    else:
        print('⚠️ RDS数据库连接失败，请检查配置')
except Exception as e:
    print(f'⚠️ 数据库连接测试出错: {e}')
    print('💡 应用将在首次访问时尝试连接数据库')
"
fi

# 2. 准备Gunicorn运行环境
echo -e "${YELLOW}[2/6] 准备Gunicorn运行环境...${NC}"

# 创建日志目录
mkdir -p /var/log/gunicorn
chown $APP_USER:$APP_USER /var/log/gunicorn

# 3. 创建systemd服务文件
echo -e "${YELLOW}[3/6] 配置systemd服务...${NC}"
cat > /etc/systemd/system/no2-prediction.service << EOF
[Unit]
Description=NO2 Prediction System with RDS Database
After=network.target
Wants=network-online.target

[Service]
Type=notify
User=$APP_USER
Group=$APP_USER
RuntimeDirectory=no2-prediction
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
Environment=DATABASE_CONNECT_TIMEOUT=30
Environment=DATABASE_READ_TIMEOUT=30
Environment=DATABASE_WRITE_TIMEOUT=30
ExecStart=$APP_DIR/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 2 --timeout 120 --max-requests 1000 --max-requests-jitter 50 --preload --access-logfile /var/log/gunicorn/access.log --error-logfile /var/log/gunicorn/error.log --log-level info --name no2-prediction-gunicorn-rds web.app:app
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
TimeoutStartSec=60
PrivateTmp=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 4. 配置Nginx
echo -e "${YELLOW}[4/6] 配置Nginx...${NC}"
cat > $NGINX_AVAILABLE/no2-prediction << EOF
# NO2预测系统 Nginx配置 - RDS版本
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
        
        # 超时设置（RDS可能需要更长时间）
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
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
        return 200 "healthy\\n";
        add_header Content-Type text/plain;
    }
    
    # RDS状态检查
    location /rds-status {
        access_log off;
        proxy_pass http://127.0.0.1:5000/api/debug/database;
        proxy_set_header Host \$host;
    }

    # 日志配置
    access_log /var/log/nginx/no2-prediction.access.log;
    error_log /var/log/nginx/no2-prediction.error.log;
    
    # 文件上传大小限制
    client_max_body_size 10M;
    
    # 连接保持
    keepalive_timeout 65;
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
sleep 5
if systemctl is-active --quiet no2-prediction; then
    echo -e "${GREEN}✅ NO2预测系统服务启动成功${NC}"
else
    echo -e "${RED}❌ NO2预测系统服务启动失败${NC}"
    echo -e "${YELLOW}查看服务状态:${NC}"
    systemctl status no2-prediction --no-pager -l
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
sleep 3
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ || echo "000")
echo "HTTP状态码: $HTTP_CODE"

# 测试RDS连接状态
echo -e "${BLUE}测试RDS连接状态:${NC}"
RDS_TEST=$(curl -s http://localhost/api/debug/database 2>/dev/null || echo "无法连接到应用")
echo "RDS状态: $RDS_TEST"

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}    🎉 RDS版部署完成！${NC}"
echo -e "${GREEN}    应用用户: $APP_USER${NC}"
echo -e "${GREEN}    RDS地址: $RDS_HOST${NC}"
echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}访问地址: http://$SERVER_IP${NC}"
echo -e "${YELLOW}服务状态检查:${NC}"
echo -e "  systemctl status no2-prediction"
echo -e "  systemctl status nginx"
echo -e ""
echo -e "${YELLOW}日志查看:${NC}"
echo -e "  tail -f /var/log/gunicorn/error.log"
echo -e "  tail -f /var/log/nginx/no2-prediction.error.log"
echo -e ""
echo -e "${YELLOW}RDS相关命令:${NC}"
echo -e "  # 测试RDS连接"
echo -e "  mysql -h $RDS_HOST -P $RDS_PORT -u no2user -p no2_prediction"
echo -e "  # 查看RDS状态"
echo -e "  curl http://localhost/rds-status"

# 保存配置信息
echo -e "${BLUE}配置信息已保存到 /tmp/no2_rds_deploy_info.txt${NC}"
cat > /tmp/no2_rds_deploy_info.txt << EOF
NO2预测系统RDS部署信息
========================
部署时间: $(date)
ECS服务器: $SERVER_IP
RDS地址: $RDS_HOST:$RDS_PORT
应用用户: $APP_USER
应用目录: $APP_DIR
数据库: no2_prediction
访问地址: http://$SERVER_IP
========================
RDS连接字符串:
mysql+pymysql://no2user:NO2User2025!@$RDS_HOST:$RDS_PORT/no2_prediction
========================
EOF