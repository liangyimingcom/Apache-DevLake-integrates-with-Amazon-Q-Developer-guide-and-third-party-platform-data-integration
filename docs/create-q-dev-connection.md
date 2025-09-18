# 创建Amazon Q Developer数据连接

## 请求信息

### API端点
```
POST http://<EC2-PUBLIC-IP>:8080/plugins/q_dev/connections
```

### 请求头
```
Content-Type: application/json
```

### 请求参数替换
- **YOUR_ACCESS_KEY_ID**: AKIAXXXXXXXXXXXXXXXX
- **YOUR_SECRET_ACCESS_KEY**: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
- **AWS_REGION**: us-east-1
- **YOUR_S3_BUCKET_NAME**: <YOUR-S3-BUCKET-NAME>
- **YOUR_IDENTITY_STORE_ID**: <YOUR-IDENTITY-STORE-ID>
- **YOUR_IDENTITY_CENTER_REGION**: us-east-1

### 完整请求命令
```bash
curl 'http://<EC2-PUBLIC-IP>:8080/plugins/q_dev/connections' \
--header 'Content-Type: application/json' \
--data-raw '{
    "name": "q_dev_connection",
    "accessKeyId": "AKIAXXXXXXXXXXXXXXXX",
    "secretAccessKey": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "region": "us-east-1",
    "bucket": "<YOUR-S3-BUCKET-NAME>",
    "identityStoreId": "<YOUR-IDENTITY-STORE-ID>",
    "identityStoreRegion": "us-east-1",
    "rateLimitPerHour": 20000
}'
```

## 执行结果

### ✅ 请求成功

**HTTP状态**: 200 OK

**响应JSON**:
```json
{
  "name": "q_dev_connection",
  "id": 1,
  "createdAt": "2025-09-16T12:56:04.444Z",
  "updatedAt": "2025-09-16T12:56:04.444Z",
  "accessKeyId": "AKIAXXXXXXXXXXXXXXXX",
  "secretAccessKey": "AC************************************32",
  "region": "us-east-1",
  "bucket": "<YOUR-S3-BUCKET-NAME>",
  "rateLimitPerHour": 20000
}
```

### 🎯 重要信息
- **Connection ID**: `1` ⭐ (后续配置需要使用此ID)
- **连接名称**: q_dev_connection
- **创建时间**: 2025-09-16T12:56:04.444Z
- **S3桶**: <YOUR-S3-BUCKET-NAME>
- **AWS区域**: us-east-1
- **速率限制**: 20000/小时

### 📝 总结
Amazon Q Developer数据连接已成功创建！Connection ID为 `1`，可以用于后续的数据同步和配置操作。
