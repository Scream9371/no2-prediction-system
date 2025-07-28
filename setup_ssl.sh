#!/bin/bash
# SSL证书配置脚本（可选）
# 如果您有域名，可以使用此脚本配置HTTPS访问

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}    SSL证书配置脚本${NC}"
echo -e "${BLUE}===========================================${NC}"

# 检查root权限
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用root权限运行: sudo $0${NC}"
    exit 1
fi

# 获取域名
echo -e "${YELLOW}请输入您的域名（例如: example.com）:${NC}"
read -p "域名: " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}域名不能为空${NC}"
    exit 1
fi

echo -e "${YELLOW}请输入您的邮箱（用于证书通知）:${NC}"
read -p "邮箱: " EMAIL

if [ -z "$EMAIL" ]; then
    echo -e "${RED}邮箱不能为空${NC}"
    exit 1
fi

# 1. 安装certbot
echo -e "${YELLOW}[1/4] 安装SSL证书工具...${NC}"
apt update
apt install -y certbot python3-certbot-nginx

# 2. 更新Nginx配置以支持域名
echo -e "${YELLOW}[2/4] 更新Nginx配置...${NC}"
NGINX_CONFIG="/etc/nginx/sites-available/no2-prediction"

# 备份原配置
cp $NGINX_CONFIG "${NGINX_CONFIG}.backup"

# 更新server_name
sed -i "s/server_name 8.136.12.26;/server_name $DOMAIN www.$DOMAIN 8.136.12.26;/" $NGINX_CONFIG

# 测试Nginx配置
nginx -t

if [ $? -ne 0 ]; then
    echo -e "${RED}Nginx配置测试失败，恢复备份${NC}"
    cp "${NGINX_CONFIG}.backup" $NGINX_CONFIG
    exit 1
fi

# 重新加载Nginx
systemctl reload nginx

# 3. 获取SSL证书
echo -e "${YELLOW}[3/4] 获取SSL证书...${NC}"
echo -e "${BLUE}注意: 请确保域名已正确解析到 8.136.12.26${NC}"

# 检查域名解析
echo -e "${BLUE}检查域名解析...${NC}"
RESOLVED_IP=$(dig +short $DOMAIN | tail -n1)

if [ "$RESOLVED_IP" != "8.136.12.26" ]; then
    echo -e "${YELLOW}警告: 域名 $DOMAIN 解析到 $RESOLVED_IP，不是服务器IP 8.136.12.26${NC}"
    echo -e "${YELLOW}请确保DNS解析正确配置后再继续${NC}"
    read -p "是否继续？(y/N): " CONTINUE
    
    if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
        echo -e "${YELLOW}SSL配置已取消${NC}"
        exit 0
    fi
fi

# 使用certbot获取证书
certbot --nginx -d $DOMAIN -d www.$DOMAIN --email $EMAIL --agree-tos --non-interactive

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ SSL证书获取成功！${NC}"
else
    echo -e "${RED}❌ SSL证书获取失败${NC}"
    exit 1
fi

# 4. 配置自动续期
echo -e "${YELLOW}[4/4] 配置证书自动续期...${NC}"

# 添加续期任务到crontab
(crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -

# 创建续期后的重载脚本
cat > /etc/letsencrypt/renewal-hooks/deploy/nginx-reload.sh << 'EOF'
#!/bin/bash
systemctl reload nginx
EOF

chmod +x /etc/letsencrypt/renewal-hooks/deploy/nginx-reload.sh

# 测试自动续期
echo -e "${BLUE}测试自动续期配置...${NC}"
certbot renew --dry-run

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 自动续期配置成功${NC}"
else
    echo -e "${YELLOW}⚠️ 自动续期测试失败，但SSL已配置成功${NC}"
fi

# 5. 验证HTTPS配置
echo -e "${YELLOW}验证HTTPS配置...${NC}"
sleep 3

# 测试HTTPS访问
if curl -s -I https://$DOMAIN | head -n1 | grep -q "200 OK"; then
    echo -e "${GREEN}✅ HTTPS访问正常${NC}"
else
    echo -e "${YELLOW}⚠️ HTTPS访问可能需要稍等片刻${NC}"
fi

# 6. 配置HTTP到HTTPS重定向（可选）
echo -e "${YELLOW}是否配置HTTP到HTTPS的自动重定向？(y/N):${NC}"
read -p "选择: " REDIRECT

if [ "$REDIRECT" = "y" ] || [ "$REDIRECT" = "Y" ]; then
    # 这通常已经由certbot自动配置了
    echo -e "${GREEN}✅ HTTP到HTTPS重定向已配置${NC}"
fi

# 7. 更新安全头配置
echo -e "${YELLOW}更新安全头配置...${NC}"
NGINX_SSL_CONFIG="/etc/nginx/sites-available/no2-prediction"

# 添加安全头到HTTPS server块
if ! grep -q "Strict-Transport-Security" $NGINX_SSL_CONFIG; then
    # 在HTTPS server块中添加安全头
    sed -i '/# SSL/a\    # SSL安全头\
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;\
    add_header X-Frame-Options "SAMEORIGIN" always;\
    add_header X-Content-Type-Options "nosniff" always;\
    add_header X-XSS-Protection "1; mode=block" always;' $NGINX_SSL_CONFIG
fi

# 重新加载Nginx配置
nginx -t && systemctl reload nginx

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}    🎉 SSL配置完成！${NC}"
echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}您的网站现在可以通过以下地址访问:${NC}"
echo -e "${GREEN}  HTTP:  http://$DOMAIN${NC}"
echo -e "${GREEN}  HTTPS: https://$DOMAIN${NC}"
echo -e "${GREEN}  备用:  http://8.136.12.26${NC}"
echo -e ""
echo -e "${YELLOW}重要提醒:${NC}"
echo -e "  1. 证书将在90天后到期，系统已配置自动续期"
echo -e "  2. DNS解析必须正确指向 8.136.12.26"
echo -e "  3. 确保阿里云安全组已开放443端口"
echo -e ""
echo -e "${BLUE}证书信息:${NC}"
certbot certificates

echo -e "${YELLOW}测试访问:${NC}"
echo -e "curl -I https://$DOMAIN"