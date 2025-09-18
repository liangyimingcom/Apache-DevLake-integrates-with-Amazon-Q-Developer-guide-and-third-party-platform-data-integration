# Amazon Q Developer S3 权限错误解决方案

## 错误描述

**错误信息**：
```
Failed to update Amazon Q Developer profile.
Amazon Q doesn't have sufficient permissions to access the provided S3 bucket. Please verify your S3/KMS permissions and retry.
```

**配置场景**：
- AWS Profile: oversea1
- 区域: N. Virginia (us-east-1)
- 功能: Q Developer user activity report
- 状态: 尝试启用用户活动指标收集并创建 S3 存储桶日报告

## 错误原因分析

### 1. 缺少服务角色
- Amazon Q Developer 需要专门的 IAM 服务角色来访问 S3 资源
- 系统中没有预配置的 Q Developer 服务角色

### 2. S3 存储桶权限不足
- 目标存储桶 `qdev-user-metrics-collection-yiming` 缺少必要的存储桶策略
- 没有授权 Amazon Q Developer 服务主体访问权限

### 3. 服务主体配置缺失
- 缺少对 `codewhisperer.amazonaws.com` 和 `amazonq.amazonaws.com` 服务的信任关系
- 没有配置适当的跨服务访问权限

## 解决步骤

### 1. 创建 IAM 服务角色

**信任策略** (`trust-policy.json`)：
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "codewhisperer.amazonaws.com",
                    "amazonq.amazonaws.com"
                ]
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

**权限策略** (`permissions-policy.json`)：
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket",
                "s3:GetBucketLocation"
            ],
            "Resource": [
                "arn:aws:s3:::qdev-user-metrics-collection-yiming",
                "arn:aws:s3:::qdev-user-metrics-collection-yiming/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt",
                "kms:GenerateDataKey"
            ],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "kms:ViaService": "s3.us-east-1.amazonaws.com"
                }
            }
        }
    ]
}
```

### 2. 配置 S3 存储桶策略

**存储桶策略** (`bucket-policy.json`)：
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowQDeveloperServiceAccess",
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "codewhisperer.amazonaws.com",
                    "amazonq.amazonaws.com"
                ]
            },
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket",
                "s3:GetBucketLocation"
            ],
            "Resource": [
                "arn:aws:s3:::qdev-user-metrics-collection-yiming",
                "arn:aws:s3:::qdev-user-metrics-collection-yiming/*"
            ]
        },
        {
            "Sid": "AllowQDeveloperRoleAccess",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::153705321444:role/AmazonQDeveloperServiceRole"
            },
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket",
                "s3:GetBucketLocation"
            ],
            "Resource": [
                "arn:aws:s3:::qdev-user-metrics-collection-yiming",
                "arn:aws:s3:::qdev-user-metrics-collection-yiming/*"
            ]
        }
    ]
}
```

### 3. 执行命令

```bash
# 创建服务角色
aws iam create-role \
    --role-name AmazonQDeveloperServiceRole \
    --assume-role-policy-document file://trust-policy.json \
    --description "Service role for Amazon Q Developer user activity reporting" \
    --profile oversea1 \
    --region us-east-1

# 附加权限策略
aws iam put-role-policy \
    --role-name AmazonQDeveloperServiceRole \
    --policy-name QDeveloperS3AccessPolicy \
    --policy-document file://permissions-policy.json \
    --profile oversea1 \
    --region us-east-1

# 应用存储桶策略
aws s3api put-bucket-policy \
    --bucket qdev-user-metrics-collection-yiming \
    --policy file://bucket-policy.json \
    --profile oversea1 \
    --region us-east-1
```

### 4. 验证配置

```bash
# 验证角色创建
aws iam get-role \
    --role-name AmazonQDeveloperServiceRole \
    --profile oversea1 \
    --region us-east-1

# 验证存储桶策略
aws s3api get-bucket-policy \
    --bucket qdev-user-metrics-collection-yiming \
    --profile oversea1 \
    --region us-east-1
```

## 故障排除

### 常见问题

1. **权限传播延迟**
   - IAM 权限可能需要几分钟才能生效
   - 建议等待 2-5 分钟后重试

2. **存储桶区域不匹配**
   - 确保存储桶在正确的区域 (us-east-1)
   - 检查 KMS 条件中的区域设置

3. **服务主体名称**
   - 确保使用正确的服务主体名称
   - `codewhisperer.amazonaws.com` 和 `amazonq.amazonaws.com`

### 验证步骤

1. 返回 Amazon Q Developer 控制台
2. 重新尝试启用 "Q Developer user activity report" 功能
3. 选择 S3 存储桶：`qdev-user-metrics-collection-yiming`
4. 如需要，指定服务角色：`AmazonQDeveloperServiceRole`

---

# 解决方案总结

## 问题根因
Amazon Q Developer 用户活动报告功能需要特定的 IAM 权限和 S3 存储桶策略才能正常工作，但系统中缺少这些必要的权限配置。

## 解决方案
1. **创建专用服务角色**：`AmazonQDeveloperServiceRole`
2. **配置 S3 存储桶策略**：允许 Q Developer 服务访问指定存储桶
3. **设置适当权限**：包含 S3 操作和 KMS 解密权限

## 关键配置要素
- **服务主体**：`codewhisperer.amazonaws.com`, `amazonq.amazonaws.com`
- **必需 S3 权限**：`GetObject`, `PutObject`, `DeleteObject`, `ListBucket`, `GetBucketLocation`
- **KMS 权限**：`Decrypt`, `GenerateDataKey`（用于加密存储桶）
- **资源范围**：存储桶及其所有对象

## 最佳实践
1. 使用最小权限原则，仅授予必要的权限
2. 定期审查和更新 IAM 策略
3. 监控 S3 存储桶的访问日志
4. 确保存储桶加密配置正确

## 相关文档
- [Amazon Q Developer 用户指南](https://docs.aws.amazon.com/amazonq/)
- [IAM 角色和策略](https://docs.aws.amazon.com/IAM/latest/UserGuide/)
- [S3 存储桶策略](https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html)
