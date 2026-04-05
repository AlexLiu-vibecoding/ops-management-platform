# AWS 托管服务迁移指南

## 概述

本指南帮助您从内置数据库（PostgreSQL + Redis）迁移到 AWS 托管服务（Amazon RDS + Amazon ElastiCache）。

**重要说明**:
- **PostgreSQL**: 必需配置，用于元数据存储
- **Redis**: **可选配置**，用于缓存和会话管理。不配置 Redis 时，系统将禁用缓存功能，但仍可正常运行

## 迁移优势

### 使用 AWS 托管服务的优势

| 特性 | 内置数据库 | AWS 托管服务 |
|------|-----------|-------------|
| **可靠性** | 单点故障风险 | 多可用区部署，自动故障转移 |
| **备份** | 手动配置 | 自动备份 + 时间点恢复（最多 35 天） |
| **性能** | 受限于 K8s 节点资源 | 独立计算资源，可扩展实例类型 |
| **监控** | 手动配置 Prometheus | AWS CloudWatch 集成监控 |
| **维护** | 手动升级和补丁 | 自动更新和补丁管理 |
| **安全性** | 需要自行配置安全策略 | VPC 安全组、加密、审计日志 |
| **成本** | 包含在 K8s 节点成本中 | 按使用付费，更灵活 |

---

## 迁移前准备

### 1. 创建 AWS 资源

#### 1.1 创建 Amazon RDS PostgreSQL

使用 AWS Console 或 AWS CLI 创建 RDS PostgreSQL 实例：

**AWS Console**:
1. 登录 AWS Console
2. 导航到 Amazon RDS
3. 点击 "Create database"
4. 选择 "PostgreSQL"
5. 选择标准创建（Standard create）

**配置建议**:
- **引擎版本**: PostgreSQL 15.x
- **模板**: Production
- **实例规格**: db.t3.medium 或更高（取决于负载）
- **存储**: 20Gi 或更高
- **多可用区**: 启用（生产环境推荐）
- **数据库标识符**: `opscenter-postgres`
- **主用户名**: `postgres` 或自定义
- **数据库端口**: 5432

**VPC 安全组配置**:
- 创建安全组，允许 Kubernetes Worker 节点访问
- 入站规则: `5432` 允许来自 K8s 节点 CIDR 的流量

**VPC 和子网组**:
- 选择与 Kubernetes 集群相同的 VPC
- 创建 DB 子网组，包含至少 2 个不同可用区的子网

**AWS CLI 示例**:
```bash
# 创建 DB 子网组
aws rds create-db-subnet-group \
  --db-subnet-group-name opscenter-subnet-group \
  --db-subnet-group-description "Subnet group for OpsCenter" \
  --subnet-ids subnet-xxxxxx subnet-yyyyyy

# 创建 RDS PostgreSQL 实例
aws rds create-db-instance \
  --db-instance-identifier opscenter-postgres \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 15.4 \
  --master-username postgres \
  --master-user-password your-secure-password \
  --allocated-storage 20 \
  --db-subnet-group-name opscenter-subnet-group \
  --vpc-security-group-ids sg-xxxxxx \
  --multi-az \
  --backup-retention-period 30 \
  --publicly-accessible false
```

#### 1.2 创建 Amazon ElastiCache Redis（可选）

**注意**: Redis 是可选的，不配置时系统将禁用缓存功能。如果需要缓存优化性能，请创建 ElastiCache Redis。

**AWS Console**:
1. 导航到 Amazon ElastiCache
2. 点击 "Create cluster"
3. 选择 "Redis"
4. 选择 "Valkey" 或 "Redis OSS"

**配置建议**:
- **引擎版本**: Redis 7.x
- **节点类型**: cache.t3.medium 或更高
- **集群模式**: 禁用（单节点）或启用（多节点，根据需求）
- **复制**: 启用（主从复制，生产环境推荐）
- **集群名称**: `opscenter-redis`
- **端口**: 6379
- **自动备份**: 启用，保留期 7 天

**VPC 安全组配置**:
- 创建安全组，允许 Kubernetes Worker 节点访问
- 入站规则: `6379` 允许来自 K8s 节点 CIDR 的流量

**AWS CLI 示例**:
```bash
# 创建 Redis 子网组
aws elasticache create-replication-group \
  --replication-group-id opscenter-redis \
  --replication-group-description "Redis for OpsCenter" \
  --num-node-groups 1 \
  --replicas-per-node-group 1 \
  --node-type cache.t3.medium \
  --engine redis \
  --engine-version 7.0 \
  --cache-parameter-group default.redis7 \
  --cache-subnet-group-name opscenter-cache-subnet-group \
  --security-group-ids sg-xxxxxx \
  --automatic-failover-enabled \
  --snapshot-retention-limit 7 \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled
```

### 2. 准备迁移数据

#### 2.1 备份现有数据

**PostgreSQL 数据备份**:
```bash
# 从现有 PostgreSQL StatefulSet 备份数据
kubectl exec -it postgresql-0 -n opscenter -- pg_dump -U postgres opscenter > postgres-backup.sql

# 验证备份文件
ls -lh postgres-backup.sql
```

**Redis 数据备份**:
```bash
# 从现有 Redis StatefulSet 备份数据
kubectl exec -it redis-master-0 -n opscenter -- redis-cli BGSAVE

# 等待保存完成
kubectl exec -it redis-master-0 -n opscenter -- redis-cli LASTSAVE

# 导出数据（可选）
kubectl exec -it redis-master-0 -n opscenter -- redis-cli --rdb /data/dump.rdb
kubectl cp opscenter/redis-master-0:/data/dump.rdb redis-backup.rdb
```

#### 2.2 验证备份完整性

```bash
# PostgreSQL 验证
pg_restore --list postgres-backup.sql | head -20

# Redis 验证
file redis-backup.rdb
```

---

## 迁移步骤

### 步骤 1: 导入数据到 AWS RDS

#### 1.1 获取 RDS endpoint

```bash
aws rds describe-db-instances \
  --db-instance-identifier opscenter-postgres \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text

# 输出示例: opscenter-postgres.xxxxxx.us-east-1.rds.amazonaws.com
```

#### 1.2 导入数据

```bash
# 导入数据到 RDS
psql -h opscenter-postgres.xxxxxx.us-east-1.rds.amazonaws.com \
     -p 5432 \
     -U postgres \
     -d opscenter \
     -f postgres-backup.sql

# 验证导入
psql -h opscenter-postgres.xxxxxx.us-east-1.rds.amazonaws.com \
     -p 5432 \
     -U postgres \
     -d opscenter \
     -c "\dt"
```

### 步骤 2: 导入数据到 AWS ElastiCache（可选）

**注意**: 如果不需要 Redis 缓存功能，可以跳过此步骤，直接在配置中禁用 Redis（设置 REDIS_ENABLED=false）。

#### 2.1 获取 ElastiCache endpoint

```bash
aws elasticache describe-replication-groups \
  --replication-group-id opscenter-redis \
  --query 'ReplicationGroups[0].PrimaryEndpoint.Address' \
  --output text

# 输出示例: opscenter-redis.xxxxxx.cache.amazonaws.com
```

#### 2.2 导入数据

**方法 1: 使用 redis-cli**:
```bash
# 从备份 RDB 文件导入
redis-cli -h opscenter-redis.xxxxxx.cache.amazonaws.com \
         -p 6379 \
         --pipe < redis-backup.rdb
```

**方法 2: 使用迁移工具**:
```bash
# 使用 redis-copy 工具
redis-copy --source redis://old-redis-host:6379 \
           --destination redis://opscenter-redis.xxxxxx.cache.amazonaws.com:6379 \
           --password your-redis-password
```

**验证导入**:
```bash
# 连接到新 Redis 实例
redis-cli -h opscenter-redis.xxxxxx.cache.amazonaws.com -p 6379

# 检查数据
DBSIZE
INFO keyspace
```

### 步骤 3: 更新 Kubernetes 配置

#### 3.1 更新 ConfigMap

编辑 `k8s/01-configmap.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: opscenter-config
  namespace: opscenter
data:
  POSTGRES_HOST: "opscenter-postgres.xxxxxx.us-east-1.rds.amazonaws.com"
  POSTGRES_PORT: "5432"
  POSTGRES_DB: "opscenter"
  POSTGRES_USER: "postgres"
  
  # Redis 配置（可选）
  REDIS_ENABLED: "true"  # 设为 "false" 可禁用 Redis
  REDIS_HOST: "opscenter-redis.xxxxxx.cache.amazonaws.com"
  REDIS_PORT: "6379"
  REDIS_DB: "0"
```

应用配置:
```bash
kubectl apply -f k8s/01-configmap.yaml
```

#### 3.2 更新 Secret

编辑 `k8s/02-secret.yaml`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: opscenter-secret
  namespace: opscenter
type: Opaque
stringData:
  POSTGRES_PASSWORD: "your-rds-password"
  REDIS_PASSWORD: "your-elasticache-password"  # 可选，仅在 REDIS_ENABLED=true 时需要
```

应用配置:
```bash
kubectl apply -f k8s/02-secret.yaml
```

### 步骤 4: 重启应用

```bash
# 重启后端 Pod
kubectl rollout restart deployment opscenter-backend -n opscenter

# 重启前端 Pod（如果需要）
kubectl rollout restart deployment opscenter-frontend -n opscenter

# 等待 Pod 就绪
kubectl rollout status deployment opscenter-backend -n opscenter
```

### 步骤 5: 验证迁移

#### 5.1 检查 Pod 日志

```bash
# 检查后端日志
kubectl logs -f deployment/opscenter-backend -n opscenter

# 应该看到类似以下日志:
# Database connection established: RDS PostgreSQL
# Redis connection established: Amazon ElastiCache
```

#### 5.2 测试数据库连接

```bash
# 进入后端 Pod
kubectl exec -it deployment/opscenter-backend -n opscenter -- /bin/bash

# 测试 PostgreSQL 连接
python -c "
import psycopg2
conn = psycopg2.connect(
    host='${POSTGRES_HOST}',
    port=5432,
    database='opscenter',
    user='postgres',
    password='${POSTGRES_PASSWORD}'
)
print('PostgreSQL connection successful!')
conn.close()
"

# 测试 Redis 连接
python -c "
import redis
r = redis.Redis(
    host='${REDIS_HOST}',
    port=6379,
    db=0,
    password='${REDIS_PASSWORD}'
)
print('Redis connection successful!', r.ping())
"
```

#### 5.3 功能测试

1. 访问 OpsCenter 界面
2. 测试登录功能
3. 测试数据查询（SQL 编辑器）
4. 测试缓存功能（监控数据刷新）
5. 验证所有功能正常

---

## 迁移后清理

### 1. 备份旧数据（可选但推荐）

```bash
# 备份 PostgreSQL 数据
kubectl exec -it postgresql-0 -n opscenter -- pg_dump -U postgres opscenter > postgres-final-backup.sql

# 备份 Redis 数据
kubectl cp opscenter/redis-master-0:/data/dump.rdb redis-final-backup.rdb
```

### 2. 移除内置数据库

**⚠️ 警告**: 执行前确保新服务运行正常！

```bash
# 删除 PostgreSQL StatefulSet
kubectl delete statefulset postgresql -n opscenter

# 删除 Redis StatefulSet
kubectl delete statefulset redis -n opscenter

# 删除 PVC（可选，取决于是否需要保留数据）
kubectl delete pvc -l app=postgresql -n opscenter
kubectl delete pvc -l app=redis -n opscenter

# 删除 Service
kubectl delete service postgresql-service -n opscenter
kubectl delete service redis-master -n opscenter
```

### 3. 移除部署清单文件

```bash
# 删除内置数据库部署清单
rm k8s/07-postgresql.yaml
rm k8s/08-redis.yaml

# 提交变更
git add -A
git commit -m "feat: migrate to AWS managed services (RDS + ElastiCache)"
```

---

## 回滚方案

如果迁移后发现问题，可以快速回滚到内置数据库：

### 1. 恢复配置

```bash
# 恢复 ConfigMap（使用备份）
kubectl apply -f k8s/01-configmap.yaml.backup

# 恢复 Secret（使用备份）
kubectl apply -f k8s/02-secret.yaml.backup
```

### 2. 重新部署内置数据库

```bash
# 恢复 PostgreSQL
kubectl apply -f k8s/07-postgresql.yaml

# 恢复 Redis
kubectl apply -f k8s/08-redis.yaml

# 等待数据库就绪
kubectl wait --for=condition=ready pod -l app=postgresql -n opscenter --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n opscenter --timeout=300s
```

### 3. 导入数据

```bash
# 导入 PostgreSQL 数据
kubectl exec -i postgresql-0 -n opscenter -- psql -U postgres opscenter < postgres-final-backup.sql

# 导入 Redis 数据
kubectl cp redis-final-backup.rdb opscenter/redis-master-0:/data/dump.rdb
kubectl exec -it redis-master-0 -n opscenter -- redis-cli SHUTDOWN
```

### 4. 重启应用

```bash
kubectl rollout restart deployment opscenter-backend -n opscenter
kubectl rollout status deployment opscenter-backend -n opscenter
```

---

## 监控和优化

### 1. 监控 RDS 性能

使用 AWS CloudWatch 监控以下指标:
- CPU Utilization
- Freeable Memory
- Database Connections
- Read/Write Latency
- Read/Write IOPS
- Free Storage Space

**设置告警**:
- CPU 使用率 > 80% 持续 5 分钟
- Freeable Memory < 256MB 持续 5 分钟
- Database Connections > 100
- Read Latency > 100ms

### 2. 监控 ElastiCache 性能

使用 AWS CloudWatch 监控以下指标:
- CPU Utilization
- Freeable Memory
- CurrConnections
- Evictions
- CacheHits / CacheMisses
- SwapUsage

**设置告警**:
- CPU 使用率 > 80% 持续 5 分钟
- Freeable Memory < 128MB 持续 5 分钟
- Evictions > 0
- Cache Hit Rate < 80%

### 3. 优化建议

**RDS 优化**:
- 根据负载调整实例类型
- 启用多可用区部署（生产环境）
- 配置自动备份和快照
- 定期执行 VACUUM ANALYZE
- 使用连接池（如 PgBouncer）

**ElastiCache 优化**:
- 根据负载调整节点类型
- 配置 Redis 集群模式（高并发场景）
- 启用自动故障转移
- 配置内存策略（如 allkeys-lru）
- 使用 Redis 集群分片（大数据量）

---

## 常见问题

### Q1: 如何选择 RDS 实例类型？

**A**: 根据负载选择:
- 开发/测试: db.t3.micro / db.t3.small
- 小规模生产: db.t3.medium / db.t3.large
- 中等规模: db.r6g.xlarge / db.r6g.2xlarge
- 大规模: db.r6g.4xlarge 或更高

### Q2: RDS 和 ElastiCache 需要在同一个 VPC 吗？

**A**: 推荐在同一个 VPC，但不同 VPC 也可以通过 VPC Peering 连接。确保网络可达性。

### Q3: 迁移过程中会影响服务吗？

**A**: 如果使用数据库复制（PostgreSQL 逻辑复制、Redis 主从复制），可以实现零停机迁移。否则需要短暂的停机窗口。

### Q4: 如何测试迁移是否成功？

**A**:
1. 检查数据库连接日志
2. 验证数据完整性（记录数对比）
3. 测试关键功能（登录、查询、缓存）
4. 监控性能指标（延迟、错误率）

### Q5: 如何处理数据库升级？

**A**: AWS RDS 支持主版本升级（如从 PostgreSQL 14 升级到 15）:
```bash
aws rds modify-db-instance \
  --db-instance-identifier opscenter-postgres \
  --engine-version 15.4 \
  --allow-major-version-upgrade \
  --apply-immediately
```

### Q6: 如何处理数据加密？

**A**: AWS RDS 和 ElastiCache 支持两种加密:
- **传输中加密**: SSL/TLS
- **静态加密**: AWS KMS

配置示例:
```bash
# RDS 创建时启用加密
aws rds create-db-instance \
  --storage-encrypted \
  --kms-key-id your-kms-key-id \
  ...

# ElastiCache 创建时启用加密
aws elasticache create-replication-group \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled \
  --auth-token your-password \
  ...
```

---

## 成本估算

### RDS 成本

| 实例类型 | 每月成本（约） | 适用场景 |
|---------|--------------|---------|
| db.t3.micro | ~$15 | 开发/测试 |
| db.t3.medium | ~$35 | 小规模生产 |
| db.r6g.xlarge | ~$200 | 中等规模 |
| db.r6g.4xlarge | ~$800 | 大规模 |

存储成本: ~$0.1/GB/月（通用 SSD）
备份成本: ~$0.095/GB/月

### ElastiCache 成本

| 节点类型 | 每月成本（约） | 适用场景 |
|---------|--------------|---------|
| cache.t3.micro | ~$15 | 开发/测试 |
| cache.t3.medium | ~$35 | 小规模生产 |
| cache.r6g.xlarge | ~$250 | 中等规模 |
| cache.r6g.4xlarge | ~$1000 | 大规模 |

**总成本估算**:
- 开发/测试: ~$30/月
- 小规模生产: ~$70/月
- 中等规模: ~$450/月
- 大规模: ~$1800/月

---

## 参考资料

- [Amazon RDS 文档](https://docs.aws.amazon.com/rds/)
- [Amazon ElastiCache 文档](https://docs.aws.amazon.com/elasticache/)
- [AWS Database Migration Service](https://aws.amazon.com/dms/)
- [Kubernetes StatefulSet](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)

---

*文档版本: v1.0*
*最后更新: 2026-04-02*
