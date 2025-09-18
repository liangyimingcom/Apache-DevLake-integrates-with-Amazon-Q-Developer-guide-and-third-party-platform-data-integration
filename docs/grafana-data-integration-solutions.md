# Grafana Q Dev用户指标数据集成方案

## 📊 数据源分析

### Grafana仪表板
- **URL**: http://<EC2-PUBLIC-IP>:3000/d/qdev_user_metrics/q-dev-user-metrics-dashboard
- **数据源**: DevLake MySQL数据库
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

## 🔄 数据集成方案

### 方案1: 直接数据库访问 (最简单)

#### 特点
- ✅ 实现简单，延迟最低
- ✅ 数据一致性最好
- ❌ 需要数据库访问权限
- ❌ 与DevLake系统耦合

#### 实现方式
```python
import mysql.connector
import pandas as pd

# 数据库连接
config = {
    'host': '<EC2-PUBLIC-IP>',
    'port': 3306,
    'user': 'merico',
    'password': 'merico',
    'database': 'lake'
}

def get_user_metrics(start_date, end_date):
    conn = mysql.connector.connect(**config)
    
    # 聚合指标查询
    query = """
    SELECT 
        user_id,
        display_name,
        total_inline_suggestions_count,
        total_inline_acceptance_count,
        acceptance_rate,
        total_inline_ai_code_lines,
        avg_inline_suggestions_count,
        first_date,
        last_date
    FROM _tool_q_dev_user_metrics
    WHERE connection_id = 1
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# 使用示例
metrics_data = get_user_metrics('2025-09-15', '2025-09-17')
```

#### 适用场景
- 内部报表系统
- 实时数据需求
- 技术团队有数据库访问能力

---

### 方案2: DevLake API接口 (推荐)

#### 特点
- ✅ 标准化API接口
- ✅ 权限控制完善
- ✅ 数据格式统一
- ❌ 需要API开发

#### 实现方式
```python
import requests
import json

class DevLakeAPI:
    def __init__(self, base_url="http://<EC2-PUBLIC-IP>:8080"):
        self.base_url = base_url
    
    def get_q_dev_metrics(self, connection_id=1):
        """获取Q Dev用户指标"""
        url = f"{self.base_url}/plugins/q_dev/connections/{connection_id}/metrics"
        response = requests.get(url)
        return response.json()
    
    def get_user_data(self, connection_id=1, start_date=None, end_date=None):
        """获取用户日常数据"""
        url = f"{self.base_url}/plugins/q_dev/connections/{connection_id}/user-data"
        params = {}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
            
        response = requests.get(url, params=params)
        return response.json()

# 使用示例
api = DevLakeAPI()
metrics = api.get_q_dev_metrics()
daily_data = api.get_user_data(start_date='2025-09-15', end_date='2025-09-17')
```

#### 适用场景
- 第三方系统集成
- 需要权限控制
- 标准化数据接口需求

---

### 方案3: Grafana API导出 (中等复杂度)

#### 特点
- ✅ 利用现有Grafana配置
- ✅ 支持多种数据格式
- ❌ 需要Grafana认证
- ❌ 数据格式可能需要转换

#### 实现方式
```python
import requests
import base64

class GrafanaExporter:
    def __init__(self, grafana_url="http://<EC2-PUBLIC-IP>:3000"):
        self.grafana_url = grafana_url
        self.session = requests.Session()
        
    def login(self, username="admin", password="admin"):
        """登录Grafana"""
        login_data = {
            "user": username,
            "password": password
        }
        response = self.session.post(f"{self.grafana_url}/login", data=login_data)
        return response.status_code == 200
    
    def export_dashboard_data(self, dashboard_uid="qdev_user_metrics", 
                            from_time="now-2d", to_time="now"):
        """导出仪表板数据"""
        # 获取仪表板配置
        dashboard_url = f"{self.grafana_url}/api/dashboards/uid/{dashboard_uid}"
        dashboard = self.session.get(dashboard_url).json()
        
        # 导出面板数据
        panels_data = []
        for panel in dashboard['dashboard']['panels']:
            if 'targets' in panel:
                for target in panel['targets']:
                    # 执行查询
                    query_url = f"{self.grafana_url}/api/ds/query"
                    query_data = {
                        "queries": [target],
                        "from": from_time,
                        "to": to_time
                    }
                    result = self.session.post(query_url, json=query_data)
                    panels_data.append({
                        'panel_title': panel.get('title', ''),
                        'data': result.json()
                    })
        
        return panels_data

# 使用示例
exporter = GrafanaExporter()
exporter.login()
data = exporter.export_dashboard_data()
```

#### 适用场景
- 需要保持与Grafana一致的数据视图
- 复用现有仪表板配置
- 定期数据导出需求

---

### 方案4: 数据文件导出 (批处理)

#### 特点
- ✅ 适合大批量数据处理
- ✅ 支持多种文件格式
- ✅ 可以离线处理
- ❌ 数据不是实时的
- ❌ 需要定期同步

#### 实现方式
```python
import pandas as pd
import json
from datetime import datetime, timedelta

class DataExporter:
    def __init__(self, db_config):
        self.db_config = db_config
    
    def export_to_csv(self, output_path="qdev_metrics.csv"):
        """导出为CSV文件"""
        conn = mysql.connector.connect(**self.db_config)
        
        query = """
        SELECT 
            m.user_id,
            m.display_name,
            m.total_inline_suggestions_count,
            m.total_inline_acceptance_count,
            m.acceptance_rate,
            m.total_inline_ai_code_lines,
            m.first_date,
            m.last_date,
            d.date,
            d.inline_suggestions_count as daily_suggestions,
            d.inline_acceptance_count as daily_acceptance,
            d.chat_messages_sent
        FROM _tool_q_dev_user_metrics m
        LEFT JOIN _tool_q_dev_user_data d ON m.user_id = d.user_id
        WHERE m.connection_id = 1
        ORDER BY m.user_id, d.date
        """
        
        df = pd.read_sql(query, conn)
        df.to_csv(output_path, index=False)
        conn.close()
        return output_path
    
    def export_to_json(self, output_path="qdev_metrics.json"):
        """导出为JSON文件"""
        conn = mysql.connector.connect(**self.db_config)
        
        # 用户聚合数据
        users_query = "SELECT * FROM _tool_q_dev_user_metrics WHERE connection_id = 1"
        users_df = pd.read_sql(users_query, conn)
        
        # 日常数据
        daily_query = "SELECT * FROM _tool_q_dev_user_data WHERE connection_id = 1"
        daily_df = pd.read_sql(daily_query, conn)
        
        # 组合数据
        export_data = {
            "export_time": datetime.now().isoformat(),
            "user_metrics": users_df.to_dict('records'),
            "daily_data": daily_df.to_dict('records')
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        conn.close()
        return output_path

# 定时任务示例 (使用cron或调度器)
def daily_export_job():
    exporter = DataExporter(db_config)
    csv_file = exporter.export_to_csv(f"qdev_metrics_{datetime.now().strftime('%Y%m%d')}.csv")
    json_file = exporter.export_to_json(f"qdev_metrics_{datetime.now().strftime('%Y%m%d')}.json")
    
    # 上传到S3或其他存储
    # upload_to_s3(csv_file, json_file)
```

#### 适用场景
- 数据仓库ETL流程
- 离线分析需求
- 大批量数据处理

---

### 方案5: 实时数据流 (最复杂)

#### 特点
- ✅ 真正的实时数据
- ✅ 支持流式处理
- ✅ 可扩展性好
- ❌ 实现复杂度高
- ❌ 需要额外基础设施

#### 实现方式
```python
# 使用Kafka + MySQL Binlog
from kafka import KafkaProducer, KafkaConsumer
import json
from pymysqlreplication import BinLogStreamReader
from pymysqlreplication.row_event import WriteRowsEvent, UpdateRowsEvent

class MySQLStreamer:
    def __init__(self, kafka_bootstrap_servers=['localhost:9092']):
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
        )
    
    def stream_mysql_changes(self):
        """监听MySQL变更并发送到Kafka"""
        stream = BinLogStreamReader(
            connection_settings={
                'host': '<EC2-PUBLIC-IP>',
                'port': 3306,
                'user': 'merico',
                'passwd': 'merico'
            },
            server_id=100,
            only_events=[WriteRowsEvent, UpdateRowsEvent],
            only_tables=['_tool_q_dev_user_metrics', '_tool_q_dev_user_data']
        )
        
        for binlogevent in stream:
            for row in binlogevent.rows:
                event_data = {
                    'table': binlogevent.table,
                    'event_type': binlogevent.__class__.__name__,
                    'data': row['values'] if hasattr(row, 'values') else row['after_values'],
                    'timestamp': binlogevent.timestamp
                }
                
                # 发送到Kafka
                self.producer.send('qdev_metrics_stream', event_data)

class StreamConsumer:
    def __init__(self, kafka_bootstrap_servers=['localhost:9092']):
        self.consumer = KafkaConsumer(
            'qdev_metrics_stream',
            bootstrap_servers=kafka_bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
    
    def process_stream(self, callback_func):
        """处理数据流"""
        for message in self.consumer:
            data = message.value
            callback_func(data)

# 使用示例
def handle_metrics_update(data):
    """处理指标更新"""
    if data['table'] == '_tool_q_dev_user_metrics':
        # 更新第三方系统
        update_external_system(data['data'])

streamer = MySQLStreamer()
consumer = StreamConsumer()

# 启动流处理
import threading
threading.Thread(target=streamer.stream_mysql_changes).start()
consumer.process_stream(handle_metrics_update)
```

#### 适用场景
- 实时监控系统
- 高频数据更新需求
- 大规模分布式系统

---

## 📋 方案对比总结

| 方案 | 复杂度 | 实时性 | 数据一致性 | 维护成本 | 适用场景 |
|------|--------|--------|------------|----------|----------|
| 直接数据库访问 | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | 内部系统，实时需求 |
| DevLake API | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | 标准集成，推荐方案 |
| Grafana API | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | 复用现有配置 |
| 文件导出 | ⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐ | 批处理，离线分析 |
| 实时数据流 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 大规模实时系统 |

## 🎯 推荐实施路径

### 阶段1: 快速启动 (1-2周)
选择**方案2: DevLake API接口**
- 开发标准REST API
- 实现基础数据查询功能
- 提供JSON格式数据输出

### 阶段2: 功能增强 (2-4周)
结合**方案4: 数据文件导出**
- 添加定时批量导出功能
- 支持多种数据格式 (CSV, JSON, Excel)
- 实现数据历史归档

### 阶段3: 高级特性 (1-2月)
根据需求选择**方案3或方案5**
- 如需复用Grafana配置，选择方案3
- 如需真正实时数据，选择方案5

## 🔧 技术实现建议

### API设计规范
```
GET /api/v1/qdev/metrics/users              # 获取用户列表
GET /api/v1/qdev/metrics/users/{user_id}    # 获取特定用户指标
GET /api/v1/qdev/metrics/daily              # 获取日常数据
GET /api/v1/qdev/metrics/export             # 导出数据
```

### 数据格式标准
```json
{
  "user_id": "<USER-ID-1>",
  "display_name": "User Name",
  "metrics": {
    "total_suggestions": 6,
    "total_acceptance": 3,
    "acceptance_rate": 0.5,
    "ai_code_lines": 3,
    "active_days": 1
  },
  "daily_data": [
    {
      "date": "2025-09-15",
      "suggestions": 6,
      "acceptance": 3,
      "chat_messages": 0
    }
  ]
}
```

这套方案可以根据具体需求和技术能力选择合适的实施路径，从简单到复杂逐步演进。
