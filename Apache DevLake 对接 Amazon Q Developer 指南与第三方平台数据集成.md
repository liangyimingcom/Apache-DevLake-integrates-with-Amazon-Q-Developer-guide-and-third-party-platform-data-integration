# Apache DevLake 对接 Amazon Q Developer 指南与第三方平台数据集成

[[更新版本github](https://github.com/liangyimingcom/Apache-DevLake-integrates-with-Amazon-Q-Developer-guide-and-third-party-platform-data-integration)]

## 📋 文档概述

本指南提供了在AWS平台上部署Apache DevLake并对接Amazon Q Developer的完整操作步骤，包括常见问题的解决方案和第三方平台数据集成方案。通过本指南，您可以一次性完成整个配置部署过程。

### 🎯 目标
- 在AWS EC2上部署Apache DevLake
- 配置Amazon Q Developer数据源连接
- 实现Q Dev用户指标数据的收集和可视化
- 提供第三方平台数据集成解决方案
- 解决部署过程中的常见问题

### 📁 文档结构
```
├── Apache DevLake 对接 Amazon Q Developer 指南与第三方平台数据集成.md  # 主文档
├── code-examples/                    # 代码示例
│   ├── database-access/             # 数据库直接访问
│   ├── api-integration/             # API集成
│   └── data-export/                 # 数据导出
├── configs/                         # 配置文件
│   ├── docker/                      # Docker配置
│   ├── aws/                         # AWS配置
│   └── grafana/                     # Grafana配置
├── scripts/                         # 自动化脚本
├── troubleshooting/                 # 故障排除
│   ├── devlake-500-error/          # DevLake 500错误
│   ├── config-ui-issues/           # Config UI问题
│   └── database-connection/        # 数据库连接问题
└── docs/                           # 补充文档
```

## 🚀 快速开始

### 准备工作

确保已启用Amazon Q Developer per-user activity report，具体步骤可以参考此文：https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/q-admin-user-telemetry.html

[放入截屏: 已启用Amazon Q Developer per-user activity report的配置页面]
![image-20250918125533679](./assets/image-20250918125533679.png)

![image-20250918131559349](./assets/image-20250918131559349.png)

##### Amazon Q Developer S3 权限错误解决方案

- Amazon Q Developer 需要专门的 IAM 服务角色来访问 S3 资源
- 系统中没有预配置的 Q Developer 服务角色
详细解决方案: [`troubleshooting/amazon-q-developer-s3-permission-fix.md`](troubleshooting/database-connection/README.md)




---

## 第一部分：AWS环境准备

### 前置条件

- AWS账户和适当的权限
- 基本的Linux命令行操作能力
- 了解Docker和Docker Compose基础概念

### 1.1 创建EC2实例

#### 步骤1: 启动EC2实例
1. 登录AWS控制台，进入EC2服务
2. 点击"Launch Instance"
3. 配置实例参数：
   - **Name**: `DevLake-Server-Dockerallinone`
   - **AMI**: Amazon Linux 2023 AMI
   - **Instance Type**: `t3.large` (推荐最小配置)
   - **Key Pair**: 创建新密钥对 `<YOUR-KEY-PAIR>`

[放入截屏: EC2实例配置页面]

![image-20250918130059010](./assets/image-20250918130059010.png)

#### 步骤2: 配置安全组
创建安全组 `devlake-sg`，配置以下入站规则：

| 类型 | 协议 | 端口范围 | 源 | 描述 |
|------|------|----------|-----|------|
| SSH | TCP | 22 | 0.0.0.0/0 | SSH访问 |
| HTTP | TCP | 80 | 0.0.0.0/0 | HTTP访问 |
| HTTPS | TCP | 443 | 0.0.0.0/0 | HTTPS访问 |
| **Custom TCP** | **TCP** | **3000** | **0.0.0.0/0** | **Grafana** |
| **Custom TCP** | **TCP** | **4000** | **0.0.0.0/0** | **Config UI** |
| Custom TCP | TCP | 8080 | 0.0.0.0/0 | DevLake API |
| **Custom TCP** | **TCP** | **3306** | **0.0.0.0/0** | **MySQL** |

[放入截屏: 安全组配置页面]

![image-20250918130210222](./assets/image-20250918130210222.png)

⚠️ **重要提示**: 
- 将"您的IP"替换为您的实际公网IP地址
- MySQL端口3306仅在需要直接数据库访问时开放
- 生产环境建议进一步限制访问范围

#### 步骤3: 启动实例
1. 检查配置无误后点击"Launch Instance"
2. 等待实例状态变为"Running"
3. 记录实例的公网IP地址

[放入截屏: EC2实例运行状态]

### 1.2 连接到EC2实例

#### 使用SSH连接
```bash
# 设置密钥文件权限
chmod 400 <YOUR-KEY-PAIR>.pem

# 连接到EC2实例
ssh -i <YOUR-KEY-PAIR>.pem ec2-user@<EC2-PUBLIC-IP>
```

#### 验证连接
```bash
# 检查系统信息
uname -a
whoami
pwd
```

---



## 第二部分：DevLake环境部署

### 前置条件： <u>【建议用QCLI来部署，PROMPT如下即可：】</u>

确保部署最新版本的DevLake，您可以参考DevLake的官方文档进行部署。

如：使用docker-compose的部署步骤参考 https://devlake.apache.org/docs/GettingStarted/DockerComposeSetup/

**注意：请确保使用的devlake, grafana和config-ui的镜像版本为****`main_250723_0848_e474b4e`****。以下是镜像URI：**

- DevLake: `apache/devlake:main_250723_0848_e474b4e`
- Grafana: `apache/devlake-dashboard:main_250723_0848_e474b4e`
- Config-UI: `apache/devlake-config-ui:main_250723_0848_e474b4e`

部署完毕后，访问localhost:4000以确保可以成功访问页面。



### 2.1 安装Docker和Docker Compose

#### 步骤1: 更新系统
```bash
sudo yum update -y
```

#### 步骤2: 安装Docker
```bash
# 安装Docker
sudo yum install -y docker

# 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户添加到docker组
sudo usermod -a -G docker ec2-user

# 重新登录以使组权限生效
exit
# 重新SSH连接

# 验证Docker安装
docker --version
```

#### 步骤3: 安装Docker Compose
```bash
# 下载Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# 设置执行权限
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
/usr/local/bin/docker-compose --version
```



### 2.2 部署DevLake

#### 步骤1: 创建部署目录
```bash
# 创建DevLake部署目录
sudo mkdir -p /opt/devlake
sudo chown ec2-user:ec2-user /opt/devlake
cd /opt/devlake
```

#### 步骤2: 创建Docker Compose配置
创建 `docker-compose.yml` 文件：

```yaml
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
```

#### 步骤3: 启动DevLake服务
```bash
# 启动所有服务
export PATH=/usr/local/bin:$PATH
/usr/local/bin/docker-compose up -d

# 检查服务状态
/usr/local/bin/docker-compose ps
```

#### 步骤4: 验证服务访问
```bash
# 等待服务完全启动
sleep 60

# 检查各服务状态
curl -I http://localhost:4000  # Config UI
curl -I http://localhost:8080  # DevLake API  
curl -I http://localhost:3000  # Grafana
```

⚠️ **常见问题**: 如果服务无法启动，请参考 [故障排除章节](#故障排除)



---

## 第三部分：Amazon Q Developer数据源配置

### 3.1 准备AWS凭证和资源

创建一个IAM用户，为其添加以下权限，并创建AK/SK。

```JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DevLakeRequiredPermissions",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "identitystore:DescribeUser",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::<your-bucket-name>",
        "arn:aws:s3:::<your-bucket-name>/<your-prefix>/*",
        "arn:aws:identitystore:::user/*",
        "arn:aws:identitystore::<your-account-id>:identitystore/<your-identity-store-id>"
      ]
    }
  ]
}
```

修改上述JSON中的字段：

- `<your-bucket-name>`：Amazon Q Developer per-user activity report所在的S3桶名
- `<your-prefix>`：Amazon Q Developer per-user activity report所在的路径
- `<your-account-id>`：12位AWS账号ID，可以在网页控制台右上角看到
- `<your-identity-store-id>`：IAM Identity Center的名字，格式为`d-xxxxxxxx`



### 3.2 创建数据连接

您可以使用如下命令创建连接:

```Bash
curl 'http://localhost:8080/plugins/q_dev/connections' \
--header 'Content-Type: application/json' \
--data-raw '{
    "name": "q_dev_connection",
    "accessKeyId": "<YOUR_ACCESS_KEY_ID>",
    "secretAccessKey": "<YOUR_SECRET_ACCESS_KEY>",
    "region": "<AWS_REGION>",
    "bucket": "<YOUR_S3_BUCKET_NAME>",
    "identityStoreId": "<YOUR_IDENTITY_STORE_ID>",
    "identityStoreRegion": "<YOUR_IDENTITY_CENTER_REGION>",
    "rateLimitPerHour": 20000
}'
```

您需要替换上述命令中的

- `<YOUR_ACCESS_KEY_ID>`：刚才创建的IAM用户的AK
- `<YOUR_SECRET_ACCESS_KEY>`：刚才创建的IAM用户的SK
- `<AWS_REGION>`：S3桶所在的区域，如 `us-east-1`
- `<YOUR_S3_BUCKET_NAME>`：S3桶名
- `<YOUR_IDENTITY_STORE_ID>`：IAM Identity Center的ID，如 `d-xxxxxxxxx`
- `<YOUR_IDENTITY_CENTER_REGION>`：IAM Identity Center所在的区域，如 `us-east-1`

请求成功后，返回的JSON中会包含connection ID，示例：

```JSON
{
  "name":"q_dev_connection_1",
  "id":1, // <=======================================================注意这个id
  "createdAt":"2025-06-06T07:08:22.333Z",
  "updatedAt":"2025-06-06T07:08:22.333Z",
  "accessKeyId":"AK123131312312312312",
  "secretAccessKey":"yj************************************wy",
  "region":"us-east-1",
  "bucket":"wxxxxxx",
  "rateLimitPerHour":20000
}
```



### 3.3 创建Blueprints

访问 localhost:4000 的config-ui，在Advanced中创建新的Blueprints

![img](./assets/(null)-20250918131133435.(null))

**确保选择 Advanced Mode**

![img](./assets/(null)-20250918131133911.(null))

编辑Blueprint，填入JSON配置

![img](./assets/(null)-20250918131133479.(null))

内容如下：

```JSON
[
  [
    {
      "plugin": "q_dev",
      "subtasks": null,
      "options": {
        "connectionId": 1, // <================== 确保这个ID和上文的connection ID一致
        "s3Prefix": "" // <===================== 填写正确的S3路径
      }
    }
  ]
]
```

> 假设文件保存在 `s3://some-bucket/some-prefix/AWSLogs/123123123/QDeveloperLogs/by_user_analytic/` ，那么S3路径应该填写 `some-prefix/AWSLogs/123123123/QDeveloperLogs/by_user_analytic/`

编辑完毕后点击保存。

- **务必注意，这里很容易填错：S3路径应该填写 `some-prefix/AWSLogs/123123123/QDeveloperLogs/by_user_analytic/`**



### 3.4 执行Blueprints

在Blueprints页面，查看Status，点击Run Now即可执行数据获取。

![img](./assets/(null))

如果执行成功，可以看到如下界面。

![img](./assets/(null)-20250918131133491.(null))



### 3.5 进入Grafana

点击右上角Dashboards跳转到Grafana

![img](./assets/(null)-20250918131133371.(null))

默认用户名和密码是 admin/admin。首次登录需要设置密码。



### 3.6 查询数据

在Dashboards中搜索 q dev 即可看到相关看板

![img](./assets/(null)-20250918131133463.(null))







---

## 第四部分：数据收集与可视化 - 效果演示

### 4.1 配置数据收集
```bash
curl 'http://<EC2-PUBLIC-IP>:4000/advanced/blueprints/1'
curl 'http://<EC2-PUBLIC-IP>:4000/pipelines'
```

#### 步骤1: 启动数据同步

通过Config UI或API配置数据收集任务：

#### 步骤2: 监控数据收集进度

[放入截屏: DevLake数据收集进度页面]

![image-20250918131855757](./assets/image-20250918131855757.png)



### 4.2 访问Grafana仪表板

#### 步骤1: 登录Grafana
访问：`http://<EC2-PUBLIC-IP>:3000`
- 用户名: `admin`
- 密码: `admin`

[放入截屏: Grafana登录页面]

![image-20250918132217774](./assets/image-20250918132217774.png)

#### 📁 最终效果演示

![image-20250918113814097](./assets/image-20250918113814097.png)



![image-20250918113903214](./assets/image-20250918113903214.png)

- **主要数据表**:
  - `_tool_q_dev_user_metrics` - 用户聚合指标
  - `_tool_q_dev_user_data` - 用户日常数据

### 核心指标字段

```sql
-- 用户聚合指标表 (_tool_q_dev_user_metrics)
- user_id, display_name                    -- 用户标识
- first_date, last_date, total_days        -- 时间范围
- total_inline_suggestions_count           -- 总建议数
- total_inline_acceptance_count            -- 总接受数
- acceptance_rate                          -- 接受率
- total_inline_ai_code_lines              -- AI生成代码行数
- total_code_review_findings_count         -- 代码审查发现数
- avg_* 字段                              -- 各种平均值

-- 用户日常数据表 (_tool_q_dev_user_data)
- user_id, display_name, date             -- 用户和日期
- inline_suggestions_count                -- 日建议数
- inline_acceptance_count                 -- 日接受数
- chat_messages_sent                      -- 聊天消息数
- code_fix_generation_event_count         -- 代码修复生成事件
- test_generation_event_count             -- 测试生成事件
```

## 

#### 步骤2: 查看Q Dev仪表板

导航到Q Dev用户指标仪表板：
`http://<EC2-PUBLIC-IP>:3000/d/qdev_user_metrics/q-dev-user-metrics-dashboard`

[放入截屏: Q Dev用户指标仪表板]

![image-20250918132319866](./assets/image-20250918132319866.png)

---



## 第五部分：故障排除

### 5.1 DevLake 500错误修复

#### 问题描述
访问Config UI时出现HTTP 500错误，通常由以下原因引起：
1. DevLake服务启动顺序问题
2. MySQL连接失败
3. Nginx代理配置错误

#### 解决方案1: 修复启动顺序问题
```bash
# 检查MySQL状态
cd /opt/devlake
export PATH=/usr/local/bin:$PATH
/usr/local/bin/docker-compose ps mysql

# 确保MySQL运行后重启DevLake
/usr/local/bin/docker-compose stop devlake
/usr/local/bin/docker-compose start devlake

# 等待服务启动
sleep 30
/usr/local/bin/docker-compose ps
```

#### 解决方案2: 修复Config UI Nginx配置
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

#### 验证修复结果
```bash
# 测试Config UI API
curl -s http://<EC2-PUBLIC-IP>:4000/api/store/onboard
# 应该返回: {"done":false,"step":1,"records":[]}
```

[放入截屏: 修复后的Config UI正常响应]

### 5.2 Config UI访问问题

#### 问题描述
无法访问Config UI (端口4000)，可能原因：
1. 安全组配置问题
2. 容器异常退出
3. 端口冲突

#### 解决步骤
```bash
# 1. 检查容器状态
/usr/local/bin/docker-compose ps config-ui

# 2. 如果容器退出，重启服务
/usr/local/bin/docker-compose restart config-ui

# 3. 检查端口占用
sudo netstat -tlnp | grep :4000

# 4. 查看容器日志
/usr/local/bin/docker-compose logs config-ui
```

#### 安全组配置检查
确保安全组包含以下规则：
```bash
# 使用AWS CLI检查安全组
aws ec2 describe-security-groups --group-ids <SECURITY-GROUP-ID>
```

### 5.3 数据库连接问题

#### 问题描述
第三方系统无法连接MySQL数据库

#### 解决方案
```bash
# 1. 检查MySQL容器状态
/usr/local/bin/docker-compose ps mysql

# 2. 测试数据库连接
docker exec devlake_mysql_1 mysql -u merico -pmerico -e "SELECT 1"

# 3. 检查端口绑定
docker port devlake_mysql_1

# 4. 如果需要外部访问，确保端口正确暴露
# 修改docker-compose.yml中MySQL端口配置为:
# ports:
#   - "3306:3306"  # 而不是 "127.0.0.1:3306:3306"
```

---

## 第六部分：第三方平台数据集成

### 6.1 数据集成方案概述

DevLake收集的Q Dev用户指标数据可以通过多种方式集成到第三方报表系统：

| 方案 | 复杂度 | 实时性 | 适用场景 |
|------|--------|--------|----------|
| **直接数据库访问** | **⭐** | **⭐⭐⭐⭐⭐** | **内部系统，实时需求** |
| DevLake API | ⭐⭐ | ⭐⭐⭐⭐ | 【需要鉴权开发】标准集成，推荐 |
| Grafana API | ⭐⭐⭐ | ⭐⭐⭐ | 【需要鉴权开发】复用现有配置 |
| 文件导出 | ⭐⭐ | ⭐ | 批处理，离线分析 |
| 实时数据流 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 【需要鉴权开发】大规模实时系统 |

### 6.2 方案1: 直接数据库访问 (推荐)

#### 数据表结构
DevLake将Q Dev数据存储在以下表中：

**用户聚合指标表** (`_tool_q_dev_user_metrics`):
```sql
-- 主要字段
user_id                              -- 用户唯一标识
display_name                         -- 用户显示名称  
total_inline_suggestions_count       -- 总代码建议数
total_inline_acceptance_count        -- 总接受数
acceptance_rate                      -- 接受率
total_inline_ai_code_lines          -- AI生成代码总行数
avg_inline_suggestions_count         -- 日均建议数
```

**用户日常数据表** (`_tool_q_dev_user_data`):
```sql
-- 主要字段
user_id                              -- 用户唯一标识
date                                 -- 数据日期
inline_suggestions_count             -- 当日建议数
inline_acceptance_count              -- 当日接受数
chat_messages_sent                   -- 聊天消息数
code_fix_generation_event_count      -- 代码修复生成事件数
```

#### 实现示例
参考完整代码: [`code-examples/database-access/qdev_database_demo.py`](code-examples/database-access/qdev_database_demo.py)

```python
import mysql.connector
import pandas as pd

class QDevMetricsDB:
    def __init__(self, host='<EC2-PUBLIC-IP>', port=3306, 
                 user='merico', password='merico', database='lake'):
        self.config = {
            'host': host, 'port': port, 'user': user,
            'password': password, 'database': database
        }
    
    def get_user_metrics_summary(self):
        """获取用户指标汇总"""
        query = """
        SELECT user_id, display_name, total_inline_suggestions_count,
               total_inline_acceptance_count, acceptance_rate,
               total_inline_ai_code_lines
        FROM _tool_q_dev_user_metrics 
        WHERE connection_id = 1
        """
        conn = mysql.connector.connect(**self.config)
        df = pd.read_sql(query, conn)
        conn.close()
        return df

# 使用示例
db = QDevMetricsDB()
metrics = db.get_user_metrics_summary()
print(metrics)
```

#### 环境配置
```bash
# 安装Python依赖
pip install mysql-connector-python pandas

# 确保MySQL端口开放
# 在安全组中添加3306端口访问权限
```

#### 验证数据访问
```python
# 测试连接
try:
    conn = mysql.connector.connect(
        host='<EC2-PUBLIC-IP>', port=3306,
        user='merico', password='merico', database='lake'
    )
    print("数据库连接成功!")
    conn.close()
except Exception as e:
    print(f"连接失败: {e}")
```

[放入截屏: 数据库连接测试结果]

---

## 附录

### A. 配置文件模板

#### A.1 Docker Compose完整配置
文件位置: [`configs/docker/docker-compose.yml`](configs/docker/docker-compose.yml)

#### A.2 AWS安全组配置
文件位置: [`configs/aws/security-group-rules.json`](configs/aws/security-group-rules.json)

#### A.3 Grafana数据源配置  
文件位置: [`configs/grafana/datasource.yml`](configs/grafana/datasource.yml)

### B. 自动化脚本

#### B.1 一键部署脚本
文件位置: [`scripts/deploy-devlake.sh`](scripts/deploy-devlake.sh)

#### B.2 健康检查脚本
文件位置: [`scripts/health-check.sh`](scripts/health-check.sh)

#### B.3 数据备份脚本
文件位置: [`scripts/backup-data.sh`](scripts/backup-data.sh)

### C. 代码示例

#### C.1 数据库访问示例
- [`code-examples/database-access/qdev_database_demo.py`](code-examples/database-access/qdev_database_demo.py)
- [`code-examples/database-access/requirements.txt`](code-examples/database-access/requirements.txt)

#### C.2 API集成示例  
- [`code-examples/api-integration/devlake_api_client.py`](code-examples/api-integration/devlake_api_client.py)
- [`code-examples/api-integration/grafana_exporter.py`](code-examples/api-integration/grafana_exporter.py)

#### C.3 数据导出示例
- [`code-examples/data-export/csv_exporter.py`](code-examples/data-export/csv_exporter.py)
- [`code-examples/data-export/json_exporter.py`](code-examples/data-export/json_exporter.py)

### D. 故障排除指南

#### D.1 DevLake 500错误
详细解决方案: [`troubleshooting/devlake-500-error/README.md`](troubleshooting/devlake-500-error/README.md)

#### D.2 Config UI问题
详细解决方案: [`troubleshooting/config-ui-issues/README.md`](troubleshooting/config-ui-issues/README.md)

#### D.3 数据库连接问题
详细解决方案: [`troubleshooting/database-connection/README.md`](troubleshooting/database-connection/README.md)

#### D.4 Amazon Q Developer S3 权限错误解决方案
- Amazon Q Developer 需要专门的 IAM 服务角色来访问 S3 资源
- 系统中没有预配置的 Q Developer 服务角色
详细解决方案: [`troubleshooting/amazon-q-developer-s3-permission-fix.md`](troubleshooting/database-connection/README.md)

---

## 🎯 总结

通过本指南，您应该能够：

1. ✅ 在AWS EC2上成功部署Apache DevLake
2. ✅ 配置Amazon Q Developer数据源连接
3. ✅ 实现Q Dev用户指标的数据收集和可视化
4. ✅ 解决部署过程中的常见问题
5. ✅ 实现第三方平台数据集成

### 🔗 相关资源

- [Apache DevLake官方文档](https://devlake.apache.org/)
- [Amazon Q Developer文档](https://docs.aws.amazon.com/amazonq/)
- [Docker Compose文档](https://docs.docker.com/compose/)
- [Grafana文档](https://grafana.com/docs/)

### 📞 技术支持

如果在部署过程中遇到问题，请：
1. 首先查看[故障排除章节](#故障排除)
2. 检查相关日志文件
3. 参考代码示例和配置模板
4. 联系技术支持团队



## 使用说明

基于安全考虑，本文档中的AWS凭证信息等敏感信息已进行屏蔽处理，使用时请替换为您的实际值：

- `<EC2-PUBLIC-IP>`: 您的EC2实例公网IP地址
- `<YOUR-ACCESS-KEY-ID>`: 您的AWS Access Key ID
- `<YOUR-SECRET-ACCESS-KEY>`: 您的AWS Secret Access Key
- `<YOUR-S3-BUCKET-NAME>`: 您的S3存储桶名称
- `<YOUR-IDENTITY-STORE-ID>`: 您的IAM Identity Center ID
- `<SECURITY-GROUP-ID>`: 您的AWS安全组ID
- `<YOUR-KEY-PAIR>.pem`: 您的SSH密钥文件名
- `<AWS-REGION>`: 您使用的AWS区域（如us-east-1）



## 原始文章参考

Apache DevLake 对接 Amazon Q Developer 指南 https://amzn-chn.feishu.cn/docx/VkD7dXLq2oXEM5xz48qcUBmPnlh





---

*最后更新: 2025-09-17*
*文档版本: v2.0*
