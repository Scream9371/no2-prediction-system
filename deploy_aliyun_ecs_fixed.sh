#!/bin/bash
# 阿里云ECS自动部署脚本 - 修复版
# 自动检测用户名，适用于Ubuntu 22.04系统
# 目标服务器: 8.136.12.26

set -e  # 遇到错误时停止执行

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 自动检测用户配置
detect_user() {
    # 检查当前登录用户（非root）
    if [ "$EUID" -eq 0 ]; then
        # 如果是root执行，尝试找到原始用户
        if [ -n "$SUDO_USER" ]; then
            APP_USER="$SUDO_USER"
        else
            # 查找第一个普通用户
            APP_USER=$(awk -F: '$3 >= 1000 && $3 != 65534 && $1 != "nobody" {print $1; exit}' /etc/passwd)
            
            # 如果没找到，创建ubuntu用户
            if [ -z "$APP_USER" ]; then
                echo -e "${YELLOW}未找到普通用户，创建ubuntu用户...${NC}"
                useradd -m -s /bin/bash ubuntu
                usermod -aG sudo ubuntu
                APP_USER="ubuntu"
            fi
        fi
    else
        APP_USER=$(whoami)
    fi
    
    echo -e "${GREEN}检测到应用用户: $APP_USER${NC}"
    
    # 确保用户存在
    if ! id "$APP_USER" &>/dev/null; then
        echo -e "${RED}用户 $APP_USER 不存在，正在创建...${NC}"
        useradd -m -s /bin/bash "$APP_USER"
        usermod -aG sudo "$APP_USER"
    fi
    
    # 获取用户的主目录
    APP_HOME=$(eval echo ~$APP_USER)
    echo -e "${BLUE}用户主目录: $APP_HOME${NC}"
}

# 服务器信息
SERVER_IP="8.136.12.26"
PROJECT_NAME="no2-prediction-system"
APP_DIR="/var/www/$PROJECT_NAME"
NGINX_AVAILABLE="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}    NO2预测系统 - 阿里云ECS部署脚本 (修复版)${NC}"
echo -e "${BLUE}    目标服务器: $SERVER_IP${NC}"
echo -e "${BLUE}===========================================${NC}"

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用root权限运行此脚本: sudo $0${NC}"
    exit 1
fi

# 自动检测用户
detect_user

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

# 5. 创建应用目录和设置权限
echo -e "${YELLOW}[5/8] 创建应用目录...${NC}"
mkdir -p $APP_DIR

# 安全地设置目录所有者
if id "$APP_USER" &>/dev/null; then
    chown -R $APP_USER:$APP_USER $APP_DIR
    echo -e "${GREEN}✅ 应用目录权限设置完成 (用户: $APP_USER)${NC}"
else
    echo -e "${RED}❌ 用户 $APP_USER 不存在，使用root权限${NC}"
    chown -R root:root $APP_DIR
    APP_USER="root"
fi

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

if [ "$APP_USER" = "root" ]; then
    python3.10 -m venv venv
    $APP_DIR/venv/bin/pip install --upgrade pip
    $APP_DIR/venv/bin/pip install -r requirements.txt
else
    sudo -u $APP_USER python3.10 -m venv venv
    sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip
    sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r requirements.txt
fi

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
APP_USER=$APP_USER
EOF

chown $APP_USER:$APP_USER $APP_DIR/.env

# 创建用户信息文件，供后续脚本使用
echo "APP_USER=$APP_USER" > /tmp/no2_user_config.sh
echo "APP_HOME=$APP_HOME" >> /tmp/no2_user_config.sh

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}    基础环境部署完成！${NC}"
echo -e "${GREEN}    检测到用户: $APP_USER${NC}"
echo -e "${GREEN}===========================================${NC}"
echo -e "下一步请运行服务配置脚本: sudo ./setup_services_fixed.sh"