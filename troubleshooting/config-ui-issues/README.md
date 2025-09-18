# Config UI访问问题故障排除指南

## 问题描述

Config UI无法访问的常见表现：
- 浏览器无法打开 `http://<IP>:4000`
- 连接超时或拒绝连接
- 页面加载失败

## 常见原因分析

### 1. 网络和安全组问题
- AWS安全组未开放4000端口
- 本地IP地址变化
- 防火墙阻止连接

### 2. 容器服务问题
- Config UI容器未启动
- 容器异常退出
- 端口绑定失败

### 3. SSH访问问题
- 无法SSH到EC2实例
- 密钥权限问题
- 安全组SSH规则限制

## 诊断步骤

### 步骤1: 检查网络连通性

```bash
# 1. 测试EC2实例连通性
ping <EC2-PUBLIC-IP>

# 2. 测试特定端口
telnet <EC2-PUBLIC-IP> 4000

# 3. 使用curl测试HTTP连接
curl -I --connect-timeout 10 http://<EC2-PUBLIC-IP>:4000
```

### 步骤2: 检查AWS安全组配置

```bash
# 使用AWS CLI检查安全组规则
aws ec2 describe-security-groups --group-ids <SECURITY-GROUP-ID>

# 检查是否包含4000端口规则
aws ec2 describe-security-groups --group-ids <SECURITY-GROUP-ID> \
  --query 'SecurityGroups[0].IpPermissions[?FromPort==`4000`]'
```

### 步骤3: 检查本地IP地址

```bash
# 获取当前公网IP
curl -s ifconfig.me

# 或使用其他服务
curl -s ipinfo.io/ip
```

## 解决方案

### 解决方案1: 修复安全组配置

#### 添加当前IP到安全组
```bash
# 获取当前IP
CURRENT_IP=$(curl -s ifconfig.me)

# 添加4000端口访问权限
aws ec2 authorize-security-group-ingress \
  --group-id <SECURITY-GROUP-ID> \
  --protocol tcp \
  --port 4000 \
  --cidr ${CURRENT_IP}/32
```

#### 添加SSH访问权限（如果需要）
```bash
# 添加SSH访问权限
aws ec2 authorize-security-group-ingress \
  --group-id <SECURITY-GROUP-ID> \
  --protocol tcp \
  --port 22 \
  --cidr ${CURRENT_IP}/32
```

### 解决方案2: 重启Config UI服务

如果能SSH到服务器：

```bash
# SSH连接到EC2实例
ssh -i <YOUR-KEY-PAIR>.pem ec2-user@<EC2-PUBLIC-IP>

# 进入DevLake目录
cd /opt/devlake
export PATH=/usr/local/bin:$PATH

# 检查Config UI容器状态
docker-compose ps config-ui

# 重启Config UI服务
docker-compose restart config-ui

# 等待服务启动
sleep 30

# 检查服务状态
docker-compose ps config-ui
```

### 解决方案3: 修复容器配置

如果容器异常退出：

```bash
# 查看容器日志
docker-compose logs config-ui

# 如果是nginx配置问题，修复配置
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

### 解决方案4: 重启EC2实例

如果SSH无法连接且其他服务正常：

```bash
# 使用AWS CLI重启实例
aws ec2 reboot-instances --instance-ids <INSTANCE-ID>

# 等待实例重启完成
aws ec2 describe-instances --instance-ids <INSTANCE-ID> \
  --query 'Reservations[0].Instances[0].State.Name'

# 等待显示 "running" 状态后再尝试连接
```

## 验证修复结果

### 1. 测试网络连接
```bash
# 测试端口连通性
telnet <EC2-PUBLIC-IP> 4000

# 测试HTTP响应
curl -I http://<EC2-PUBLIC-IP>:4000
```

### 2. 测试Config UI功能
```bash
# 测试主页访问
curl -s http://<EC2-PUBLIC-IP>:4000 | grep -i "html"

# 测试API接口
curl -s http://<EC2-PUBLIC-IP>:4000/api/store/onboard
```

### 3. 浏览器访问测试
在浏览器中访问：`http://<EC2-PUBLIC-IP>:4000`

应该能看到Config UI的主界面。

## 预防措施

### 1. 设置动态IP更新

创建脚本自动更新安全组规则：

```bash
#!/bin/bash
# update-security-group.sh

SECURITY_GROUP_ID="<SECURITY-GROUP-ID>"
CURRENT_IP=$(curl -s ifconfig.me)

# 删除旧规则（如果存在）
aws ec2 revoke-security-group-ingress \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 4000 \
  --cidr <OLD-IP>/32 2>/dev/null

# 添加新规则
aws ec2 authorize-security-group-ingress \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 4000 \
  --cidr ${CURRENT_IP}/32

echo "安全组已更新，当前IP: $CURRENT_IP"
```

### 2. 监控服务状态

设置定期健康检查：

```bash
# 添加到crontab
*/5 * * * * curl -s http://localhost:4000 > /dev/null || /opt/devlake/restart-config-ui.sh
```

### 3. 备用访问方法

配置其他访问方式：
- 使用Elastic IP避免IP变化
- 配置域名解析
- 设置VPN访问

## 常见错误信息

### 错误1: Connection refused
```
curl: (7) Failed to connect to <IP> port 4000: Connection refused
```
**原因**: 服务未启动或端口未开放
**解决**: 检查容器状态和安全组配置

### 错误2: Connection timed out
```
curl: (28) Failed to connect to <IP> port 4000: Connection timed out
```
**原因**: 网络不通或防火墙阻止
**解决**: 检查安全组规则和网络配置

### 错误3: SSH connection timed out
```
ssh: connect to host <IP> port 22: Operation timed out
```
**原因**: SSH端口未开放或IP限制
**解决**: 更新安全组SSH规则

## 应急处理

### 如果完全无法访问

1. **使用AWS控制台**：
   - 通过EC2控制台连接实例
   - 使用Session Manager（如果配置了）

2. **重新创建实例**：
   - 创建AMI快照
   - 启动新实例
   - 恢复数据

3. **联系AWS支持**：
   - 如果是AWS服务问题
   - 获取技术支持

## 相关文件

- [`fix-config-ui.sh`](fix-config-ui.sh) - Config UI修复脚本
- [`update-security-group.sh`](update-security-group.sh) - 安全组更新脚本
- [`restart-config-ui.sh`](restart-config-ui.sh) - 服务重启脚本

## 参考资源

- [AWS安全组文档](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_SecurityGroups.html)
- [Docker Compose网络配置](https://docs.docker.com/compose/networking/)
- [Nginx配置文档](https://nginx.org/en/docs/)
