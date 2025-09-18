# DevLake 500错误故障排除指南

## 问题描述

访问DevLake Config UI时出现HTTP 500错误，通常表现为：
- 浏览器显示"500 Internal Server Error"
- Config UI页面无法正常加载
- API请求返回500状态码

## 常见原因

### 1. 服务启动顺序问题
DevLake服务依赖MySQL数据库，如果MySQL未完全启动就启动DevLake，会导致连接失败。

### 2. 数据库连接问题
- MySQL服务未运行
- 数据库连接配置错误
- 网络连接问题

### 3. Config UI Nginx配置问题
- Nginx代理配置错误
- 上游服务连接失败
- 配置文件语法错误

## 诊断步骤

### 步骤1: 检查服务状态
```bash
cd /opt/devlake
export PATH=/usr/local/bin:$PATH

# 检查所有容器状态
docker-compose ps

# 检查具体服务日志
docker-compose logs mysql | tail -20
docker-compose logs devlake | tail -20
docker-compose logs config-ui | tail -20
```

### 步骤2: 检查MySQL连接
```bash
# 测试MySQL连接
docker exec devlake_mysql_1 mysql -u merico -pmerico -e "SELECT 1"

# 检查数据库状态
docker exec devlake_mysql_1 mysql -u merico -pmerico lake -e "SHOW TABLES"
```

### 步骤3: 检查DevLake API
```bash
# 测试DevLake API
curl -I http://localhost:8080/version
curl -s http://localhost:8080/store/onboard
```

## 解决方案

### 解决方案1: 修复启动顺序问题

这是最常见的问题，通过重启DevLake服务解决：

```bash
cd /opt/devlake
export PATH=/usr/local/bin:$PATH

# 1. 确保MySQL正在运行
docker-compose ps mysql

# 2. 重启DevLake服务
docker-compose stop devlake
docker-compose start devlake

# 3. 等待服务启动
sleep 30

# 4. 检查服务状态
docker-compose ps
```

### 解决方案2: 修复Config UI Nginx配置

如果Config UI的nginx配置有问题，需要手动修复：

```bash
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
```

### 解决方案3: 完全重启所有服务

如果上述方法无效，尝试完全重启：

```bash
cd /opt/devlake
export PATH=/usr/local/bin:$PATH

# 停止所有服务
docker-compose down

# 等待完全停止
sleep 10

# 重新启动所有服务
docker-compose up -d

# 等待服务启动
sleep 60

# 应用nginx配置修复
docker exec devlake_config-ui_1 sh -c 'sed -i "s/return 400;//g" /etc/nginx/conf.d/default.conf'
docker exec devlake_config-ui_1 nginx -s reload
```

### 解决方案4: 检查和修复数据库问题

如果是数据库相关问题：

```bash
# 检查MySQL容器日志
docker-compose logs mysql

# 重启MySQL服务
docker-compose restart mysql

# 等待MySQL完全启动
sleep 30

# 重启依赖MySQL的服务
docker-compose restart devlake grafana
```

## 验证修复结果

### 1. 测试Config UI访问
```bash
# 测试Config UI主页
curl -I http://localhost:4000

# 测试Config UI API
curl -s http://localhost:4000/api/store/onboard
# 应该返回: {"done":false,"step":1,"records":[]}
```

### 2. 测试DevLake API
```bash
# 测试DevLake版本信息
curl -s http://localhost:8080/version

# 测试DevLake存储状态
curl -s http://localhost:8080/store/onboard
```

### 3. 检查服务状态
```bash
# 检查所有容器状态
docker-compose ps

# 所有服务应该显示为 "Up" 状态
```

## 预防措施

### 1. 正确的启动顺序
确保docker-compose.yml中正确配置了服务依赖：

```yaml
devlake:
  depends_on:
    - mysql

config-ui:
  depends_on:
    - devlake
```

### 2. 健康检查
定期运行健康检查脚本：

```bash
# 使用提供的健康检查脚本
./scripts/health-check.sh
```

### 3. 监控日志
定期检查服务日志：

```bash
# 检查错误日志
docker-compose logs | grep -i error

# 监控实时日志
docker-compose logs -f
```

## 常见错误信息

### 错误1: "invalid port in upstream"
```
nginx: [error] invalid port in upstream "http://devlake:8080/store/onboard"
```
**解决**: 修复nginx配置中的proxy_pass设置

### 错误2: "Can't connect to MySQL server"
```
ERROR 2003 (HY000): Can't connect to MySQL server on 'mysql:3306'
```
**解决**: 重启MySQL服务，确保网络连接正常

### 错误3: "Connection refused"
```
curl: (7) Failed to connect to localhost port 4000: Connection refused
```
**解决**: 检查Config UI容器状态，重启服务

## 获取帮助

如果问题仍然存在：

1. 收集诊断信息：
   ```bash
   # 生成诊断报告
   docker-compose ps > diagnosis.txt
   docker-compose logs >> diagnosis.txt
   ```

2. 检查系统资源：
   ```bash
   # 检查磁盘空间
   df -h
   
   # 检查内存使用
   free -m
   
   # 检查CPU使用
   top
   ```

3. 参考相关文档：
   - [Apache DevLake官方文档](https://devlake.apache.org/)
   - [Docker Compose故障排除](https://docs.docker.com/compose/troubleshooting/)

## 相关文件

- [`fix-500-error.sh`](fix-500-error.sh) - 自动修复脚本
- [`nginx-config-template.conf`](nginx-config-template.conf) - 正确的nginx配置模板
- [`docker-compose-fixed.yml`](docker-compose-fixed.yml) - 修复后的docker-compose配置
