#!/bin/bash

# DevLake一键部署脚本
# 适用于Amazon Linux 2023

set -e

echo "=== DevLake 一键部署脚本 ==="
echo "开始时间: $(date)"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# 检查是否为root用户
check_user() {
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要使用root用户运行此脚本"
        exit 1
    fi
}

# 更新系统
update_system() {
    log_info "更新系统包..."
    sudo yum update -y
}

# 安装Docker
install_docker() {
    log_info "安装Docker..."
    
    # 检查Docker是否已安装
    if command -v docker &> /dev/null; then
        log_warn "Docker已安装，跳过安装步骤"
        return
    fi
    
    sudo yum install -y docker
    sudo systemctl start docker
    sudo systemctl enable docker
    
    # 将当前用户添加到docker组
    sudo usermod -a -G docker $USER
    
    log_info "Docker安装完成"
}

# 安装Docker Compose
install_docker_compose() {
    log_info "安装Docker Compose..."
    
    # 检查Docker Compose是否已安装
    if command -v docker-compose &> /dev/null; then
        log_warn "Docker Compose已安装，跳过安装步骤"
        return
    fi
    
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    log_info "Docker Compose安装完成"
}

# 创建DevLake目录
create_devlake_directory() {
    log_info "创建DevLake部署目录..."
    
    DEVLAKE_DIR="/opt/devlake"
    
    if [ ! -d "$DEVLAKE_DIR" ]; then
        sudo mkdir -p $DEVLAKE_DIR
        sudo chown $USER:$USER $DEVLAKE_DIR
    fi
    
    cd $DEVLAKE_DIR
    log_info "工作目录: $(pwd)"
}

# 创建Docker Compose配置
create_docker_compose() {
    log_info "创建Docker Compose配置..."
    
    cat > docker-compose.yml << 'EOF'
version: "3"
services:
  mysql:
    image: mysql:8.0.26
    volumes:
      - ./mysql:/var/lib/mysql
    restart: always
    ports:
      - "3306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: admin
      MYSQL_DATABASE: lake
      MYSQL_USER: merico
      MYSQL_PASSWORD: merico
    command: --character-set-server=utf8mb4
      --collation-server=utf8mb4_bin

  grafana:
    image: apache/devlake-dashboard:latest
    ports:
      - "3000:3000"
    volumes:
      - ./grafana:/var/lib/grafana
    environment:
      GF_USERS_DEFAULT_THEME: "light"
      GF_SECURITY_ADMIN_PASSWORD: "admin"
      MYSQL_URL: mysql:3306
      MYSQL_DATABASE: lake
      MYSQL_USER: merico
      MYSQL_PASSWORD: merico
    restart: always
    depends_on:
      - mysql

  devlake:
    image: apache/devlake:latest
    ports:
      - "8080:8080"
    restart: always
    volumes:
      - ./logs:/app/logs
    environment:
      DB_URL: "mysql://merico:merico@mysql:3306/lake?charset=utf8mb4&parseTime=True&loc=Local"
      PORT: 8080
      ENCRYPTION_SECRET: "devlake-secret-key-2025"
    depends_on:
      - mysql

  config-ui:
    image: apache/devlake-config-ui:latest
    ports:
      - "4000:4000"
    environment:
      GRAFANA_ENDPOINT: http://grafana:3000
      DEVLAKE_ENDPOINT: http://devlake:8080
    depends_on:
      - devlake
EOF

    log_info "Docker Compose配置创建完成"
}

# 启动DevLake服务
start_devlake() {
    log_info "启动DevLake服务..."
    
    export PATH=/usr/local/bin:$PATH
    
    # 拉取镜像
    log_info "拉取Docker镜像..."
    /usr/local/bin/docker-compose pull
    
    # 启动服务
    log_info "启动所有服务..."
    /usr/local/bin/docker-compose up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 60
    
    # 检查服务状态
    log_info "检查服务状态..."
    /usr/local/bin/docker-compose ps
}

# 修复Config UI nginx配置
fix_config_ui() {
    log_info "修复Config UI nginx配置..."
    
    # 等待Config UI容器完全启动
    sleep 30
    
    # 修复nginx配置
    docker exec devlake_config-ui_1 sh -c 'cat > /etc/nginx/conf.d/default.conf << "EOF"
server {
    listen 4000;
    server_name localhost;
    
    root /usr/share/nginx/html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api/ {
        rewrite ^/api/(.*) /$1 break;
        proxy_pass http://devlake:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /grafana/ {
        proxy_pass http://grafana:3000/;
        proxy_set_header Host $host;
    }
}
EOF'

    # 重新加载nginx配置
    docker exec devlake_config-ui_1 nginx -s reload
    
    log_info "Config UI配置修复完成"
}

# 验证部署
verify_deployment() {
    log_info "验证部署结果..."
    
    # 获取公网IP
    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
    
    echo ""
    echo "=== 部署完成 ==="
    echo "DevLake服务访问地址:"
    echo "  Config UI:    http://$PUBLIC_IP:4000"
    echo "  DevLake API:  http://$PUBLIC_IP:8080"
    echo "  Grafana:      http://$PUBLIC_IP:3000 (admin/admin)"
    echo ""
    
    # 测试服务可用性
    log_info "测试服务可用性..."
    
    if curl -s -f http://localhost:4000 > /dev/null; then
        log_info "✓ Config UI 可访问"
    else
        log_warn "✗ Config UI 不可访问"
    fi
    
    if curl -s -f http://localhost:8080/version > /dev/null; then
        log_info "✓ DevLake API 可访问"
    else
        log_warn "✗ DevLake API 不可访问"
    fi
    
    if curl -s -f http://localhost:3000 > /dev/null; then
        log_info "✓ Grafana 可访问"
    else
        log_warn "✗ Grafana 不可访问"
    fi
    
    echo ""
    echo "注意事项:"
    echo "1. 确保AWS安全组已开放相应端口 (22, 80, 443, 3000, 4000, 8080)"
    echo "2. 如需直接数据库访问，请开放3306端口"
    echo "3. 首次访问可能需要等待几分钟让服务完全启动"
    echo ""
    echo "部署完成时间: $(date)"
}

# 主函数
main() {
    check_user
    update_system
    install_docker
    install_docker_compose
    create_devlake_directory
    create_docker_compose
    start_devlake
    fix_config_ui
    verify_deployment
}

# 执行主函数
main "$@"
