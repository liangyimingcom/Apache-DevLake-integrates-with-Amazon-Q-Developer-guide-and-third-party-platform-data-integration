#!/bin/bash

# DevLake健康检查脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_check() {
    echo -e "${BLUE}[CHECK]${NC} $1"
}

# 获取公网IP
get_public_ip() {
    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "localhost")
}

# 检查Docker服务
check_docker() {
    log_check "检查Docker服务状态..."
    
    if systemctl is-active --quiet docker; then
        log_info "✓ Docker服务运行正常"
    else
        log_error "✗ Docker服务未运行"
        return 1
    fi
}

# 检查Docker Compose
check_docker_compose() {
    log_check "检查Docker Compose..."
    
    if command -v docker-compose &> /dev/null; then
        COMPOSE_VERSION=$(docker-compose --version)
        log_info "✓ Docker Compose已安装: $COMPOSE_VERSION"
    else
        log_error "✗ Docker Compose未安装"
        return 1
    fi
}

# 检查DevLake容器状态
check_containers() {
    log_check "检查DevLake容器状态..."
    
    cd /opt/devlake 2>/dev/null || {
        log_error "✗ DevLake目录不存在: /opt/devlake"
        return 1
    }
    
    export PATH=/usr/local/bin:$PATH
    
    # 检查容器状态
    CONTAINERS=$(docker-compose ps --services)
    
    for container in $CONTAINERS; do
        STATUS=$(docker-compose ps $container | grep $container | awk '{print $4}')
        if [[ "$STATUS" == "Up" ]]; then
            log_info "✓ $container 容器运行正常"
        else
            log_error "✗ $container 容器状态异常: $STATUS"
        fi
    done
}

# 检查端口可用性
check_ports() {
    log_check "检查服务端口..."
    
    PORTS=(3000 4000 8080 3306)
    PORT_NAMES=("Grafana" "Config-UI" "DevLake-API" "MySQL")
    
    for i in "${!PORTS[@]}"; do
        PORT=${PORTS[$i]}
        NAME=${PORT_NAMES[$i]}
        
        if netstat -tlnp 2>/dev/null | grep -q ":$PORT "; then
            log_info "✓ $NAME 端口 $PORT 正在监听"
        else
            log_warn "✗ $NAME 端口 $PORT 未监听"
        fi
    done
}

# 检查服务HTTP响应
check_http_services() {
    log_check "检查HTTP服务响应..."
    
    get_public_ip
    
    # 检查Config UI
    if curl -s -f -m 10 http://localhost:4000 > /dev/null 2>&1; then
        log_info "✓ Config UI (4000) 响应正常"
    else
        log_error "✗ Config UI (4000) 无响应"
    fi
    
    # 检查DevLake API
    if curl -s -f -m 10 http://localhost:8080/version > /dev/null 2>&1; then
        log_info "✓ DevLake API (8080) 响应正常"
    else
        log_error "✗ DevLake API (8080) 无响应"
    fi
    
    # 检查Grafana
    if curl -s -f -m 10 http://localhost:3000 > /dev/null 2>&1; then
        log_info "✓ Grafana (3000) 响应正常"
    else
        log_error "✗ Grafana (3000) 无响应"
    fi
}

# 检查数据库连接
check_database() {
    log_check "检查数据库连接..."
    
    if docker exec devlake_mysql_1 mysql -u merico -pmerico -e "SELECT 1" > /dev/null 2>&1; then
        log_info "✓ MySQL数据库连接正常"
        
        # 检查DevLake表
        TABLE_COUNT=$(docker exec devlake_mysql_1 mysql -u merico -pmerico lake -e "SHOW TABLES" 2>/dev/null | wc -l)
        if [ "$TABLE_COUNT" -gt 10 ]; then
            log_info "✓ DevLake数据表已创建 ($((TABLE_COUNT-1)) 个表)"
        else
            log_warn "⚠ DevLake数据表较少，可能还在初始化"
        fi
    else
        log_error "✗ MySQL数据库连接失败"
    fi
}

# 检查磁盘空间
check_disk_space() {
    log_check "检查磁盘空间..."
    
    DISK_USAGE=$(df /opt/devlake | tail -1 | awk '{print $5}' | sed 's/%//')
    
    if [ "$DISK_USAGE" -lt 80 ]; then
        log_info "✓ 磁盘空间充足 (已使用 ${DISK_USAGE}%)"
    elif [ "$DISK_USAGE" -lt 90 ]; then
        log_warn "⚠ 磁盘空间紧张 (已使用 ${DISK_USAGE}%)"
    else
        log_error "✗ 磁盘空间不足 (已使用 ${DISK_USAGE}%)"
    fi
}

# 检查内存使用
check_memory() {
    log_check "检查内存使用..."
    
    MEMORY_INFO=$(free -m | grep "Mem:")
    TOTAL_MEM=$(echo $MEMORY_INFO | awk '{print $2}')
    USED_MEM=$(echo $MEMORY_INFO | awk '{print $3}')
    MEMORY_USAGE=$((USED_MEM * 100 / TOTAL_MEM))
    
    if [ "$MEMORY_USAGE" -lt 80 ]; then
        log_info "✓ 内存使用正常 (${MEMORY_USAGE}%, ${USED_MEM}MB/${TOTAL_MEM}MB)"
    elif [ "$MEMORY_USAGE" -lt 90 ]; then
        log_warn "⚠ 内存使用较高 (${MEMORY_USAGE}%, ${USED_MEM}MB/${TOTAL_MEM}MB)"
    else
        log_error "✗ 内存使用过高 (${MEMORY_USAGE}%, ${USED_MEM}MB/${TOTAL_MEM}MB)"
    fi
}

# 检查Q Dev连接
check_qdev_connection() {
    log_check "检查Q Dev数据连接..."
    
    CONNECTIONS=$(curl -s http://localhost:8080/plugins/q_dev/connections 2>/dev/null || echo "[]")
    
    if echo "$CONNECTIONS" | grep -q "q_dev_connection"; then
        log_info "✓ Q Dev数据连接已配置"
        
        # 检查数据表
        QDEV_TABLES=$(docker exec devlake_mysql_1 mysql -u merico -pmerico lake -e "SHOW TABLES LIKE '%q_dev%'" 2>/dev/null | wc -l)
        if [ "$QDEV_TABLES" -gt 1 ]; then
            log_info "✓ Q Dev数据表已创建 ($((QDEV_TABLES-1)) 个表)"
        else
            log_warn "⚠ Q Dev数据表未找到，可能需要运行数据收集"
        fi
    else
        log_warn "⚠ Q Dev数据连接未配置"
    fi
}

# 生成报告
generate_report() {
    echo ""
    echo "=== DevLake健康检查报告 ==="
    echo "检查时间: $(date)"
    echo "服务器IP: $PUBLIC_IP"
    echo ""
    echo "访问地址:"
    echo "  Config UI:    http://$PUBLIC_IP:4000"
    echo "  DevLake API:  http://$PUBLIC_IP:8080"
    echo "  Grafana:      http://$PUBLIC_IP:3000"
    echo ""
    
    # 显示容器状态
    echo "容器状态:"
    cd /opt/devlake 2>/dev/null && docker-compose ps || echo "无法获取容器状态"
    echo ""
    
    # 显示最近的日志
    echo "最近的错误日志:"
    cd /opt/devlake 2>/dev/null && docker-compose logs --tail=5 | grep -i error || echo "未发现错误日志"
    echo ""
}

# 主函数
main() {
    echo "=== DevLake健康检查开始 ==="
    echo ""
    
    check_docker
    check_docker_compose
    check_containers
    check_ports
    check_http_services
    check_database
    check_disk_space
    check_memory
    check_qdev_connection
    
    generate_report
    
    echo "=== 健康检查完成 ==="
}

# 执行主函数
main "$@"
