# Docker Compose 到 Kubernetes 迁移指南

## 概述

本文档说明如何将 OpsCenter 从 Docker Compose 部署迁移到 Kubernetes 云原生部署。

---

## 架构对比

### Docker Compose 架构

```
┌─────────────────────────────────┐
│   Docker Compose               │
│                                │
│  ┌─────────────────────────┐   │
│  │  ops-platform (单容器) │   │
│  │  ├── Nginx (前端)       │   │
│  │  ├── FastAPI (后端)     │   │
│  │  └── 共享文件系统       │   │
│  └─────────────────────────┘   │
│                                │
│  外部依赖:                      │
│  ├── PostgreSQL               │
│  ├── MySQL                    │
│  └── Redis                    │
└─────────────────────────────────┘
```

### Kubernetes 架构

```
┌─────────────────────────────────────┐
│   Kubernetes Cluster                │
│                                     │
│  ┌────────────────────────────┐    │
│  │  Namespace: opscenter     │    │
│  │                            │    │
│  │  ┌──────────────────────┐ │    │
│  │  │  Ingress             │ │    │
│  │  └──────────────────────┘ │    │
│  │              ↓             │    │
│  │  ┌──────────────────────┐ │    │
│  │  │  Frontend Service    │ │    │
│  │  │  ┌────────────────┐  │ │    │
│  │  │  │  Frontend Pod  │  │ │    │
│  │  │  │  └────────────┘  │ │    │
│  │  │  └────────────────┘  │ │    │
│  │                         │    │
│  │  ┌──────────────────────┐ │    │
│  │  │  Backend Service     │ │    │
│  │  │  ┌────────────────┐  │ │    │
│  │  │  │  Backend Pod 1 │  │ │    │
│  │  │  │  Backend Pod 2 │  │ │    │
│  │  │  │  Backend Pod 3 │  │ │    │
│  │  │  └────────────────┘  │ │    │
│  │  └──────────────────────┘ │    │
│  │                            │    │
│  │  ┌──────────────────────┐ │    │
│  │  │  PostgreSQL          │ │    │
│  │  │  ┌────────────────┐  │ │    │
│  │  │  │  PG Pod 0      │  │ │    │
│  │  │  └────────────────┘  │ │    │
│  │  └──────────────────────┘ │    │
│  │                            │    │
│  │  ┌──────────────────────┐ │    │
│  │  │  Redis               │ │    │
│  │  │  ┌────────────────┐  │ │    │
│  │  │  │  Redis Pod 0   │  │ │    │
│  │  │  └────────────────┘  │ │    │
│  │  └──────────────────────┘ │    │
│  └────────────────────────────┘    │
└─────────────────────────────────────┘
```

---

## 配置映射

### 环境变量映射

| Docker Compose | Kubernetes | 说明 |
|----------------|------------|------|
| `PORT` | `DEPLOY_RUN_PORT` | 服务端口 |
| `DATABASE_URL` | `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DATABASE`, `POSTGRES_PASSWORD` | PostgreSQL 连接 |
| `PGDATABASE_URL` | 同上 | PostgreSQL 连接 |
| `MYSQL_HOST` | `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_PASSWORD` | MySQL 连接 |
| `REDIS_HOST` | `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD` | Redis 连接 |
| `JWT_SECRET_KEY` | `JWT_SECRET_KEY` | JWT 密钥 |
| `AES_KEY` | `AES_KEY` | AES 加密密钥 |
| `PASSWORD_SALT` | `PASSWORD_SALT` | 密码盐 |

### 端口映射

| Docker Compose | Kubernetes | Service |
|----------------|------------|---------|
| `5000:5000` | `5000` | `opscenter-backend-service` |
| `80` | `80` | `opscenter-frontend-service` |

---

## 迁移步骤

### 1. 准备工作

```bash
# 克隆项目
git clone <repository-url>
cd opscenter

# 检查 kubectl 连接
kubectl cluster-info

# 检查命名空间
kubectl get namespaces
```

### 2. 导出配置

从 Docker Compose 导出环境变量：

```bash
# 加载 .env 文件
source .env

# 生成 Kubernetes Secret
kubectl create secret generic opscenter-secret \
  --from-literal=POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
  --from-literal=MYSQL_PASSWORD=$MYSQL_PASSWORD \
  --from-literal=REDIS_PASSWORD=$REDIS_PASSWORD \
  --from-literal=JWT_SECRET_KEY=$JWT_SECRET_KEY \
  --from-literal=AES_KEY=$AES_KEY \
  --from-literal=PASSWORD_SALT=$PASSWORD_SALT \
  -n opscenter
```

### 3. 配置外部数据库

如果使用外部数据库，修改 `k8s/01-configmap.yaml`：

```yaml
data:
  POSTGRES_HOST: "your-postgres-host"
  POSTGRES_PORT: "5432"
  MYSQL_HOST: "your-mysql-host"
  MYSQL_PORT: "3306"
  REDIS_HOST: "your-redis-host"
  REDIS_PORT: "6379"
```

### 4. 部署到 Kubernetes

```bash
# 使用部署脚本
./deploy-k8s.sh

# 或手动部署
kubectl apply -f k8s/
```

### 5. 数据迁移

如果需要迁移数据库数据：

```bash
# 从 Docker Compose 导出数据
docker exec ops-platform pg_dump -U postgres opscenter > backup.sql

# 导入到 Kubernetes
kubectl exec -it postgresql-0 -n opscenter -- psql -U postgres opscenter < backup.sql
```

### 6. 验证部署

```bash
# 检查 Pod 状态
kubectl get pods -n opscenter

# 检查服务
kubectl get svc -n opscenter

# 测试 API
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n opscenter \
  -- curl http://opscenter-backend-service:5000/api/init/status
```

### 7. 切换流量

```bash
# 更新 DNS 指向 Ingress 地址
# 或使用 LoadBalancer Service

# 测试新环境
curl https://opscenter.example.com/api/init/status
```

---

## 功能对比

| 功能 | Docker Compose | Kubernetes |
|------|----------------|------------|
| 单容器部署 | ✅ | ❌（分离部署） |
| 多容器部署 | ✅ | ✅ |
| 自动重启 | ✅ | ✅ |
| 滚动更新 | ❌ | ✅ |
| 弹性伸缩 | ❌ | ✅（HPA） |
| 自我修复 | ✅ | ✅ |
| 配置管理 | .env 文件 | ConfigMap + Secret |
| 服务发现 | 容器名 | DNS |
| 负载均衡 | Nginx | Service + Ingress |
| 持久化存储 | Volumes | PVC |
| 健康检查 | depends_on | Probes |
| 资源限制 | ✅ | ✅ |
| 监控集成 | 需手动 | Prometheus 注解 |
| 日志收集 | Docker logs | 集成到日志系统 |
| 集群管理 | ❌ | ✅ |

---

## 常见问题

### Q1: 为什么前端和后端要分离部署？

**A**: 分离部署可以独立扩缩容，提高资源利用率：
- 前端主要是静态文件，资源需求小
- 后端计算密集，需要更多资源
- 可以独立更新，互不影响

### Q2: 如何保持会话一致性？

**A**: Kubernetes 部署中使用 Sticky Session：

```yaml
service:
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 10800
```

### Q3: 如何处理文件上传？

**A**: 使用对象存储（S3/OSS）：

```yaml
env:
  - name: STORAGE_TYPE
    value: "s3"
  - name: STORAGE_ACCESS_KEY
    valueFrom:
      secretKeyRef:
        name: opscenter-secret
        key: STORAGE_ACCESS_KEY
```

### Q4: 如何处理定时任务？

**A**: 使用 Kubernetes CronJob：

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: backup-database
  namespace: opscenter
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: opscenter/backend:latest
            command: ["python", "-m", "app.scripts.backup"]
```

### Q5: 如何监控应用性能？

**A**: 部署清单已包含 Prometheus 注解，配置 Prometheus 后会自动收集指标：

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "9090"
  prometheus.io/path: "/metrics"
```

---

## 迁移检查清单

### 迁移前

- [ ] 备份数据库数据
- [ ] 备份配置文件
- [ ] 记录环境变量
- [ ] 准备 Kubernetes 集群
- [ ] 准备 Ingress Controller
- [ ] 准备 StorageClass

### 迁移中

- [ ] 创建命名空间
- [ ] 创建 ConfigMap 和 Secret
- [ ] 部署数据库（PostgreSQL, Redis）
- [ ] 迁移数据
- [ ] 部署应用
- [ ] 配置 Ingress
- [ ] 配置 DNS

### 迁移后

- [ ] 验证 Pod 状态
- [ ] 验证服务连通性
- [ ] 验证数据完整性
- [ ] 验证功能正常
- [ ] 配置监控告警
- [ ] 配置日志收集
- [ ] 配置自动扩缩容
- [ ] 删除 Docker Compose 环境

---

## 回滚方案

如果迁移失败，可以快速回滚到 Docker Compose：

```bash
# 停止 Kubernetes 部署
kubectl delete namespace opscenter

# 启动 Docker Compose
docker-compose up -d

# 验证服务
curl http://localhost:5000/api/init/status
```

---

## 最佳实践

### 1. 使用外部数据库

生产环境建议使用云数据库（RDS、云 PostgreSQL）：

```yaml
# k8s/01-configmap.yaml
data:
  POSTGRES_HOST: "your-rds-endpoint.rds.amazonaws.com"
  POSTGRES_PORT: "5432"
```

### 2. 使用 Sealed Secrets

管理敏感信息：

```bash
# 安装 Sealed Secrets
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# 加密 Secret
kubeseal -f k8s/02-secret.yaml -w k8s/02-secret-sealed.yaml
```

### 3. 配置 PodDisruptionBudget

保证最小可用副本：

```yaml
spec:
  minAvailable: 2
```

### 4. 使用 Pod 反亲和性

提高高可用性：

```yaml
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          topologyKey: kubernetes.io/hostname
```

### 5. 配置资源限制

避免资源争抢：

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

---

## 支持与反馈

如有迁移问题，请：

1. 查看 [KUBERNETES_DEPLOYMENT.md](KUBERNETES_DEPLOYMENT.md)
2. 查看 [KUBERNETES.md](KUBERNETES.md)
3. 提交 Issue 到 GitHub

---

**文档版本**: v1.0.0
**最后更新**: 2025-01-09
