#!/bin/bash
# 阿里云ECS自动部署脚本
# 适用于Ubuntu 22.04系统
# 目标服务器: 8.136.12.26

set -e  # 遇到错误时停止执行

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 服务器信息
SERVER_IP="8.136.12.26"
PROJECT_NAME="no2-prediction-system"
APP_USER="ubuntu"
APP_DIR="/var/www/$PROJECT_NAME"
NGINX_AVAILABLE="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}    NO2预测系统 - 阿里云ECS部署脚本${NC}"
echo -e "${BLUE}    目标服务器: $SERVER_IP${NC}"
echo -e "${BLUE}===========================================${NC}"

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用root权限运行此脚本: sudo $0${NC}"
    exit 1
fi

# 1. 系统更新
echo -e "${YELLOW}[1/8] 更新系统包...${NC}"
apt update && apt upgrade -y

# 2. 安装基础软件
echo -e "${YELLOW}[2/8] 安装基础软件包...${NC}"
apt install -y python3.10 python3.10-venv python3-pip \
    mysql-server nginx git curl wget \
    ufw fail2ban supervisor \
    build-essential python3.10-dev libmysqlclient-dev

# 3. 配置防火墙
echo -e "${YELLOW}[3/8] 配置防火墙...${NC}"
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 'Nginx Full'
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# 4. 配置MySQL
echo -e "${YELLOW}[4/8] 配置MySQL数据库...${NC}"
systemctl start mysql
systemctl enable mysql

# 设置MySQL root密码和创建应用数据库
mysql -u root <<EOF
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'NO2Prediction2025!';
CREATE DATABASE IF NOT EXISTS no2_prediction CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'no2user'@'localhost' IDENTIFIED BY 'NO2User2025!';
GRANT ALL PRIVILEGES ON no2_prediction.* TO 'no2user'@'localhost';
FLUSH PRIVILEGES;
EOF

echo -e "${GREEN}MySQL配置完成:${NC}"
echo -e "  数据库: no2_prediction"
echo -e "  用户: no2user"
echo -e "  密码: NO2User2025!"

# 5. 创建应用目录和用户
echo -e "${YELLOW}[5/8] 创建应用目录...${NC}"
mkdir -p $APP_DIR
chown -R $APP_USER:$APP_USER $APP_DIR

# 6. 克隆项目代码
echo -e "${YELLOW}[6/8] 下载项目代码...${NC}"
cd /tmp
if [ -d "$PROJECT_NAME" ]; then
    rm -rf $PROJECT_NAME
fi

git clone https://github.com/Scream9371/no2-prediction-system.git
cp -r $PROJECT_NAME/* $APP_DIR/
chown -R $APP_USER:$APP_USER $APP_DIR

# 7. 设置Python虚拟环境
echo -e "${YELLOW}[7/8] 配置Python环境...${NC}"
cd $APP_DIR
sudo -u $APP_USER python3.10 -m venv venv
sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip

# 安装Python依赖
echo -e "${BLUE}安装Python依赖包...${NC}"
sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r requirements.txt

# 8. 创建环境配置文件
echo -e "${YELLOW}[8/8] 创建配置文件...${NC}"
cat > $APP_DIR/.env << EOF
# 生产环境配置
FLASK_ENV=production
SECRET_KEY=aliyun-ecs-no2-prediction-2025
DATABASE_URL=mysql+pymysql://no2user:NO2User2025!@localhost:3306/no2_prediction

# 和风天气API配置（可选）
# HF_API_HOST=your_api_host
# HF_PROJECT_ID=your_project_id
# HF_KEY_ID=your_credential_id

# 服务器配置
SERVER_IP=8.136.12.26
PORT=5000
EOF

chown $APP_USER:$APP_USER $APP_DIR/.env

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}    基础环境部署完成！${NC}"
echo -e "${GREEN}===========================================${NC}"
echo -e "下一步请运行应用配置脚本: ./setup_services.sh"