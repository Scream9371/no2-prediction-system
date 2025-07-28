#!/bin/bash
# NO2预测系统监控和维护脚本
# 监控服务状态、资源使用、自动重启异常服务

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
LOG_FILE="/var/log/no2-monitor.log"
ALERT_EMAIL=""  # 可配置邮件告警
MAX_CPU_USAGE=80
MAX_MEMORY_USAGE=80
MAX_DISK_USAGE=85

# 日志函数
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a $LOG_FILE
}

# 检查服务状态
check_services() {
    echo -e "${BLUE}=== 服务状态检查 ===${NC}"
    
    services=("no2-prediction" "nginx" "mysql")
    all_healthy=true
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet $service; then
            echo -e "${GREEN}✅ $service: 运行正常${NC}"
            log_message "SERVICE_OK: $service is running"
        else
            echo -e "${RED}❌ $service: 服务异常${NC}"
            log_message "SERVICE_ERROR: $service is not running"
            all_healthy=false
            
            # 尝试重启服务
            echo -e "${YELLOW}正在尝试重启 $service...${NC}"
            systemctl restart $service
            sleep 5
            
            if systemctl is-active --quiet $service; then
                echo -e "${GREEN}✅ $service: 重启成功${NC}"
                log_message "SERVICE_RESTART_SUCCESS: $service restarted successfully"
            else
                echo -e "${RED}❌ $service: 重启失败${NC}"
                log_message "SERVICE_RESTART_FAILED: $service restart failed"
            fi
        fi
    done
    
    return $all_healthy
}

# 检查端口监听
check_ports() {
    echo -e "${BLUE}=== 端口监听检查 ===${NC}"
    
    ports=("80:nginx" "5000:gunicorn" "3306:mysql")
    
    for port_service in "${ports[@]}"; do
        port=${port_service%:*}
        service=${port_service#*:}
        
        if netstat -tlnp | grep -q ":$port "; then
            echo -e "${GREEN}✅ 端口 $port ($service): 正常监听${NC}"
        else
            echo -e "${RED}❌ 端口 $port ($service): 未监听${NC}"
            log_message "PORT_ERROR: Port $port ($service) not listening"
        fi
    done
}

# 检查HTTP响应
check_http_response() {
    echo -e "${BLUE}=== HTTP响应检查 ===${NC}"
    
    # 检查本地HTTP响应
    response_code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ || echo "000")
    
    if [ "$response_code" = "200" ]; then
        echo -e "${GREEN}✅ HTTP响应: 正常 ($response_code)${NC}"
        log_message "HTTP_OK: Response code $response_code"
    else
        echo -e "${RED}❌ HTTP响应: 异常 ($response_code)${NC}"
        log_message "HTTP_ERROR: Response code $response_code"
    fi
    
    # 检查响应时间
    response_time=$(curl -s -o /dev/null -w "%{time_total}" http://localhost/ || echo "999")
    response_time_ms=$(echo "$response_time * 1000" | bc)
    
    if (( $(echo "$response_time < 5.0" | bc -l) )); then
        echo -e "${GREEN}✅ 响应时间: ${response_time}秒 (${response_time_ms%.*}ms)${NC}"
    else
        echo -e "${YELLOW}⚠️ 响应时间: ${response_time}秒 (较慢)${NC}"
        log_message "HTTP_SLOW: Response time ${response_time}s"
    fi
}

# 系统资源监控
check_system_resources() {
    echo -e "${BLUE}=== 系统资源监控 ===${NC}"
    
    # CPU使用率
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')
    cpu_usage=${cpu_usage%.*}  # 去除小数部分
    
    if [ "$cpu_usage" -lt "$MAX_CPU_USAGE" ]; then
        echo -e "${GREEN}✅ CPU使用率: ${cpu_usage}%${NC}"
    else
        echo -e "${RED}⚠️ CPU使用率过高: ${cpu_usage}%${NC}"
        log_message "RESOURCE_WARNING: High CPU usage ${cpu_usage}%"
    fi
    
    # 内存使用率
    memory_info=$(free | grep Mem)
    total_mem=$(echo $memory_info | awk '{print $2}')
    used_mem=$(echo $memory_info | awk '{print $3}')
    memory_usage=$((used_mem * 100 / total_mem))
    
    if [ "$memory_usage" -lt "$MAX_MEMORY_USAGE" ]; then
        echo -e "${GREEN}✅ 内存使用率: ${memory_usage}%${NC}"
    else
        echo -e "${RED}⚠️ 内存使用率过高: ${memory_usage}%${NC}"
        log_message "RESOURCE_WARNING: High memory usage ${memory_usage}%"
    fi
    
    # 磁盘使用率
    disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    
    if [ "$disk_usage" -lt "$MAX_DISK_USAGE" ]; then
        echo -e "${GREEN}✅ 磁盘使用率: ${disk_usage}%${NC}"
    else
        echo -e "${RED}⚠️ 磁盘使用率过高: ${disk_usage}%${NC}"
        log_message "RESOURCE_WARNING: High disk usage ${disk_usage}%"
    fi
    
    # 负载平均值
    load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    echo -e "${BLUE}📊 系统负载: ${load_avg}${NC}"
}

# 检查数据库连接
check_database() {
    echo -e "${BLUE}=== 数据库连接检查 ===${NC}"
    
    # 测试MySQL连接
    if mysql -u no2user -pNO2User2025! -e "SELECT 1;" no2_prediction >/dev/null 2>&1; then
        echo -e "${GREEN}✅ MySQL数据库: 连接正常${NC}"
        
        # 检查数据表数量
        table_count=$(mysql -u no2user -pNO2User2025! -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='no2_prediction';" -s -N)
        echo -e "${BLUE}📊 数据表数量: ${table_count}${NC}"
        
    else
        echo -e "${RED}❌ MySQL数据库: 连接失败${NC}"
        log_message "DATABASE_ERROR: MySQL connection failed"
    fi
}

# 日志管理
manage_logs() {
    echo -e "${BLUE}=== 日志管理 ===${NC}"
    
    # 检查日志文件大小
    log_files=(
        "/var/log/gunicorn/error.log"
        "/var/log/gunicorn/access.log"
        "/var/log/nginx/no2-prediction.error.log"
        "/var/log/nginx/no2-prediction.access.log"
    )
    
    for log_file in "${log_files[@]}"; do
        if [ -f "$log_file" ]; then
            size=$(du -sh "$log_file" | cut -f1)
            echo -e "${BLUE}📄 $(basename $log_file): ${size}${NC}"
            
            # 如果日志文件超过100MB，进行轮转
            size_mb=$(du -sm "$log_file" | cut -f1)
            if [ "$size_mb" -gt 100 ]; then
                echo -e "${YELLOW}⚠️ 日志文件过大，执行轮转...${NC}"
                mv "$log_file" "${log_file}.old"
                touch "$log_file"
                chown ubuntu:ubuntu "$log_file"
                systemctl reload nginx
                systemctl reload no2-prediction
                log_message "LOG_ROTATION: Rotated $log_file"
            fi
        fi
    done
}

# 性能优化建议
performance_suggestions() {
    echo -e "${BLUE}=== 性能优化建议 ===${NC}"
    
    # 检查连接数
    current_connections=$(netstat -an | grep :80 | wc -l)
    echo -e "${BLUE}🔗 当前HTTP连接数: ${current_connections}${NC}"
    
    # 检查进程数
    gunicorn_processes=$(pgrep -f gunicorn | wc -l)
    echo -e "${BLUE}🔄 Gunicorn进程数: ${gunicorn_processes}${NC}"
    
    # 内存使用建议
    if [ "$memory_usage" -gt 70 ]; then
        echo -e "${YELLOW}💡 建议: 考虑增加服务器内存或优化应用内存使用${NC}"
    fi
    
    # CPU使用建议
    if [ "$cpu_usage" -gt 70 ]; then
        echo -e "${YELLOW}💡 建议: 考虑升级CPU或优化应用性能${NC}"
    fi
}

# 主函数
main() {
    echo -e "${GREEN}===============================================${NC}"
    echo -e "${GREEN}    NO2预测系统监控报告${NC}"
    echo -e "${GREEN}    $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo -e "${GREEN}===============================================${NC}"
    
    check_services
    echo ""
    check_ports
    echo ""
    check_http_response
    echo ""
    check_system_resources
    echo ""
    check_database
    echo ""
    manage_logs
    echo ""
    performance_suggestions
    
    echo -e "${GREEN}===============================================${NC}"
    echo -e "${GREEN}    监控检查完成${NC}"
    echo -e "${GREEN}===============================================${NC}"
    
    log_message "MONITOR_COMPLETE: System monitoring completed"
}

# 如果直接执行脚本
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    # 检查是否为root用户
    if [ "$EUID" -ne 0 ]; then 
        echo -e "${RED}请使用root权限运行: sudo $0${NC}"
        exit 1
    fi
    
    # 执行监控
    main
fi