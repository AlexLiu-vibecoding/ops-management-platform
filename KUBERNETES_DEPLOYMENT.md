# OpsCenter - Kubernetes 云原生部署指南

## 目录

- [概述](#概述)
- [前置要求](#前置要求)
- [快速开始](#快速开始)
- [部署方式](#部署方式)
- [配置管理](#配置管理)
- [监控与日志](#监控与日志)
- [故障排查](#故障排查)
- [升级与回滚](#升级与回滚)
- [最佳实践](#最佳实践)

---

## 概述

OpsCenter 现已支持完整的云原生部署方案，提供以下特性：

### ✅ 支持的云原生特性

- **弹性伸缩**: HPA（Horizontal Pod Autoscaler）自动扩缩容
- **滚动更新**: 零停机部署更新
- **自我修复**: 自动重启失败的 Pod
- **负载均衡**: Service + Ingress 负载均衡
- **配置管理**: ConfigMap + Secret 分离配置
- **持久化存储**: PVC 持久化数据库数据
- **服务发现**: Kubernetes Service DNS 服务发现
- **健康检查**: Liveness/Readiness/Startup Probe
- **资源限制**: CPU/内存资源配额
- **Pod 反亲和性**: 高可用部署

### 🏗️ 架构组件

| 组件 | 类型 | 说明 |
|------|------|------|
| `opscenter-backend` | Deployment | 后端 FastAPI 应用 |
| `opscenter-frontend` | Deployment | 前端 Nginx 静态服务 |
| `opscenter-backend-service` | Service | 后端服务暴露 |
| `opscenter-frontend-service` | Service | 前端服务暴露 |
| `opscenter-ingress` | Ingress | HTTP 入口路由 |
| **外部依赖** | - | **Amazon RDS PostgreSQL（必需） + Amazon ElastiCache Redis（可选）** |

---

## 前置要求

### 系统要求

- Kubernetes 1.24+
- kubectl 1.24+
- Helm 3.0+（可选，用于 Helm Chart 部署）
- **AWS 账号**（用于 Amazon RDS，可选用于 Amazon ElastiCache Redis）
- AWS CLI（可选）

### 网络要求

- 集群内部 DNS 正常工作
- 有可用的 LoadBalancer 或 Ingress Controller
- 集群可以访问 AWS RDS 和 ElastiCache
- 端口 5000（后端）、80（前端）

### AWS 要求

- **Amazon RDS PostgreSQL**（推荐）
  - 实例类型：db.t3.medium 或更高
  - 版本：PostgreSQL 15.x
  - 存储：至少 20Gi
  - VPC 安全组：允许 Kubernetes Worker 节点访问
  
- **Amazon ElastiCache Redis**（可选，推荐用于缓存优化）
  - 节点类型：cache.t3.medium 或更高
  - 版本：Redis 7.x
  - 集群模式：禁用（单节点）或启用（多节点）
  - VPC 安全组：允许 Kubernetes Worker 节点访问
  - **注意**: 不配置 Redis 时，系统将禁用缓存功能，但仍可正常运行

- PostgreSQL: 至少 20Gi
- Redis: 至少 5Gi
- StorageClass 已配置

---

## 快速开始

### 方式一：使用 YAML 清单部署（推荐）

#### 1. 克隆项目

```bash
git clone <repository-url>
cd opscenter
```

#### 2. 配置环境变量

编辑 `k8s/02-secret.yaml`，修改敏感配置：

```yaml
stringData:
  POSTGRES_PASSWORD: "your-secure-password"
  MYSQL_PASSWORD: "your-secure-password"
  REDIS_PASSWORD: "your-secure-password"  # 可选，仅在配置 Redis 时需要
  JWT_SECRET_KEY: "your-jwt-secret-key-min-32-chars-long"
  AES_KEY: "your-32-char-aes-key!!"
  PASSWORD_SALT: "your-random-salt"
  # ... 其他配置
```

#### 3. 创建 TLS 证书

```bash
# 生成自签名证书（仅用于测试）
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key \
  -out tls.crt \
  -subj "/CN=opscenter.example.com"

# 创建 TLS Secret
kubectl create secret tls opscenter-tls-secret \
  --cert=tls.crt \
  --key=tls.key \
  -n opscenter
```

#### 4. 配置 AWS 数据库（AWS RDS + 可选的 ElastiCache Redis）

编辑 `k8s/01-configmap.yaml`，修改数据库配置为 AWS 托管服务：

```yaml
data:
  # PostgreSQL - Amazon RDS（必需）
  POSTGRES_HOST: "opscenter-postgres.xxxxxx.us-east-1.rds.amazonaws.com"
  POSTGRES_PORT: "5432"
  POSTGRES_DATABASE: "opscenter"

  # MySQL - Amazon RDS（如需要）
  MYSQL_HOST: "opscenter-mysql.xxxxxx.us-east-1.rds.amazonaws.com"
  MYSQL_PORT: "3306"
  MYSQL_DATABASE: "opscenter"

  # Redis - Amazon ElastiCache（可选）
  REDIS_ENABLED: "true"  # 设为 "false" 可禁用 Redis
  REDIS_HOST: "opscenter-redis.xxxxxx.cache.amazonaws.com"
  REDIS_PORT: "6379"
  REDIS_DB: "0"
```
  REDIS_PORT: "6379"
  REDIS_DB: "0"
```

编辑 `k8s/02-secret.yaml`，添加数据库密码：

```yaml
stringData:
  # AWS RDS 密码
  POSTGRES_PASSWORD: "your-rds-password"
  MYSQL_PASSWORD: "your-rds-mysql-password"

  # AWS ElastiCache 密码（如果启用了 AUTH）
  REDIS_PASSWORD: "your-elasticache-password"
```

#### 5. 部署到 Kubernetes

```bash
# 按顺序部署
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-configmap.yaml
kubectl apply -f k8s/02-secret.yaml
kubectl apply -f k8s/09-rbac.yaml
kubectl apply -f k8s/03-backend-deployment.yaml
kubectl apply -f k8s/04-backend-service.yaml
kubectl apply -f k8s/05-frontend-deployment.yaml
kubectl apply -f k8s/06-frontend-service.yaml
```

#### 5. 验证部署

```bash
# 检查 Pod 状态
kubectl get pods -n opscenter

# 检查 Service
kubectl get svc -n opscenter

# 检查 Ingress
kubectl get ingress -n opscenter

# 查看日志
kubectl logs -f deployment/opscenter-backend -n opscenter
```

#### 6. 访问应用

```bash
# 获取 Ingress 地址
kubectl get ingress opscenter-ingress -n opscenter

# 或通过端口转发访问
kubectl port-forward svc/opscenter-frontend-service 8080:80 -n opscenter
# 浏览器访问: http://localhost:8080
```

### 方式二：使用 Helm Chart 部署

#### 1. 安装 Helm（如未安装）

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

#### 2. 配置 values.yaml

编辑 `helm/opscenter/values.yaml`，根据需求调整配置。

#### 3. 部署

```bash
# 部署到生产环境（使用 AWS RDS + ElastiCache）
helm install opscenter ./helm/opscenter \
  --namespace opscenter \
  --create-namespace \
  --values helm/opscenter/values.yaml \
  --set postgresql.enabled=false \
  --set redis.enabled=false \
  --set config.aws.rds.endpoint="opscenter-postgres.xxxxxx.us-east-1.rds.amazonaws.com" \
  --set config.aws.redis.endpoint="opscenter-redis.xxxxxx.cache.amazonaws.com"

# 或使用自定义 values 文件
helm install opscenter ./helm/opscenter \
  --namespace opscenter \
  --create-namespace \
  --values helm/opscenter/values-prod.yaml
```

#### 4. 升级

```bash
helm upgrade opscenter ./helm/opscenter \
  --namespace opscenter \
  --values helm/opscenter/values.yaml
```

#### 5. 回滚

```bash
# 查看历史版本
helm history opscenter -n opscenter

# 回滚到上一个版本
helm rollback opscenter -n opscenter

# 回滚到指定版本
helm rollback opscenter 2 -n opscenter
```

---

## 部署方式

### 生产环境部署

#### 1. 使用 AWS 托管数据库

OpsCenter 已配置为使用 AWS 托管服务（Amazon RDS + Amazon ElastiCache），无需部署内置数据库。

##### 1.1 创建 AWS RDS PostgreSQL

通过 AWS 控制台或 CLI 创建 PostgreSQL 数据库：

```bash
# AWS CLI 示例
aws rds create-db-instance \
  --db-instance-identifier opscenter-postgres \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 15.7 \
  --master-username opscenter \
  --master-user-password YourSecurePassword123! \
  --allocated-storage 20 \
  --storage-type gp2 \
  --publicly-accessible false \
  --vpc-security-group-ids sg-xxxxx \
  --db-subnet-group-name default
```

##### 1.2 创建 AWS ElastiCache Redis

```bash
# AWS CLI 示例
aws elasticache create-cache-cluster \
  --cache-cluster-id opscenter-redis \
  --cache-node-type cache.t3.medium \
  --engine redis \
  --engine-version 7.0 \
  --num-cache-nodes 1 \
  --cache-parameter-group default.redis7 \
  --security-group-ids sg-xxxxx \
  --cache-subnet-group-name default
```

##### 1.3 配置 Kubernetes 连接 AWS 数据库

修改 `k8s/01-configmap.yaml`：

```yaml
data:
  # PostgreSQL - Amazon RDS
  POSTGRES_HOST: "opscenter-postgres.xxxxxx.us-east-1.rds.amazonaws.com"
  POSTGRES_PORT: "5432"
  POSTGRES_DATABASE: "opscenter"

  # MySQL - Amazon RDS（如需要）
  MYSQL_HOST: "opscenter-mysql.xxxxxx.us-east-1.rds.amazonaws.com"
  MYSQL_PORT: "3306"
  MYSQL_DATABASE: "opscenter"

  # Redis - Amazon ElastiCache
  REDIS_HOST: "opscenter-redis.xxxxxx.cache.amazonaws.com"
  REDIS_PORT: "6379"
  REDIS_DB: "0"
```

修改 `k8s/02-secret.yaml`：

```yaml
stringData:
  # AWS RDS 密码
  POSTGRES_PASSWORD: "your-rds-password"
  MYSQL_PASSWORD: "your-rds-mysql-password"

  # AWS ElastiCache 密码（如果启用了 AUTH）
  REDIS_PASSWORD: "your-elasticache-password"
```

#### 2. 禁用内置数据库

修改 `helm/opscenter/values.yaml`（已默认禁用）：

```yaml
postgresql:
  enabled: false

redis:
  enabled: false
```

#### 3. 配置网络访问

确保 Kubernetes 集群可以访问 AWS RDS 和 ElastiCache：

```bash
# 添加 RDS 安全组入站规则
aws ec2 authorize-security-group-ingress \
  --group-id sg-rds-security-group-id \
  --protocol tcp \
  --port 5432 \
  --source-group sg-kubernetes-worker-security-group

# 添加 ElastiCache 安全组入站规则
aws ec2 authorize-security-group-ingress \
  --group-id sg-elasticache-security-group-id \
  --protocol tcp \
  --port 6379 \
  --source-group sg-kubernetes-worker-security-group
```

#### 4. 配置 Ingress

修改 `k8s/06-frontend-service.yaml` 或 `values.yaml`：

```yaml
ingress:
  enabled: true
  className: nginx
  hosts:
    - host: opscenter.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: your-tls-secret
      hosts:
        - opscenter.yourdomain.com
```

#### 4. 配置 HPA

修改 `k8s/04-backend-service.yaml`：

```yaml
spec:
  minReplicas: 5
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
```

### 开发环境部署

使用 Minikube 或 Kind 进行本地测试：

```bash
# 使用 Minikube
minikube start
kubectl apply -f k8s/

# 使用 Port Forward 访问
kubectl port-forward svc/opscenter-frontend-service 8080:80 -n opscenter
```

---

## 配置管理

### ConfigMap 配置

修改 `k8s/01-configmap.yaml` 更新非敏感配置：

```yaml
data:
  APP_ENV: "production"
  LOG_LEVEL: "info"
  MAX_WORKERS: "4"
  ENABLE_SCHEDULER: "true"
```

### Secret 管理

#### 使用 kubectl 创建 Secret

```bash
# 从文件创建
kubectl create secret generic opscenter-secret \
  --from-file=POSTGRES_PASSWORD=./postgres-password.txt \
  --from-file=MYSQL_PASSWORD=./mysql-password.txt \
  -n opscenter

# 从字面量创建
kubectl create secret generic opscenter-secret \
  --from-literal=POSTGRES_PASSWORD=your-password \
  --from-literal=JWT_SECRET_KEY=your-secret \
  -n opscenter
```

#### 使用 Sealed Secrets（推荐）

```bash
# 安装 Sealed Secrets
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# 加密 Secret
kubeseal -f k8s/02-secret.yaml -w k8s/02-secret-sealed.yaml

# 部署加密的 Secret
kubectl apply -f k8s/02-secret-sealed.yaml
```

#### 使用 External Secrets Operator

```bash
# 从 AWS Secrets Manager 同步
# 或从 HashiCorp Vault 同步
# 具体配置参考 External Secrets Operator 文档
```

---

## 监控与日志

### Prometheus 监控

部署清单已包含 Prometheus 注解：

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "9090"
  prometheus.io/path: "/metrics"
```

启用 ServiceMonitor（如使用 Prometheus Operator）：

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: opscenter-backend
  namespace: opscenter
spec:
  selector:
    matchLabels:
      app: opscenter
      component: backend
  endpoints:
    - port: metrics
      interval: 30s
```

### 日志收集

#### 查看 Pod 日志

```bash
# 查看后端日志
kubectl logs -f deployment/opscenter-backend -n opscenter

# 查看前端日志
kubectl logs -f deployment/opscenter-frontend -n opscenter

# 查看所有 Pod 日志
kubectl logs -l app=opscenter -n opscenter --all-containers=true -f
```

#### 配置 ELK Stack

```yaml
# 添加 Fluentd DaemonSet
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd
  namespace: logging
spec:
  # ... Fluentd 配置
```

---

## 故障排查

### Pod 无法启动

```bash
# 查看 Pod 状态
kubectl describe pod <pod-name> -n opscenter

# 查看 Pod 日志
kubectl logs <pod-name> -n opscenter

# 查看事件
kubectl get events -n opscenter --sort-by='.lastTimestamp'
```

### 服务无法访问

```bash
# 检查 Service
kubectl get svc -n opscenter
kubectl describe svc <service-name> -n opscenter

# 检查 Endpoint
kubectl get endpoints -n opscenter

# 测试服务连通性
kubectl run -it --rm debug --image=busybox --restart=Never -n opscenter -- wget -O- http://opscenter-backend-service:5000/api/init/status
```

### HPA 不工作

```bash
# 检查 HPA 状态
kubectl get hpa -n opscenter
kubectl describe hpa opscenter-backend-hpa -n opscenter

# 检查 Metrics Server
kubectl get apiservice v1beta1.metrics.k8s.io
```

### 数据库连接失败

```bash
# 检查后端 Pod 日志
kubectl logs -f deployment/opscenter-backend -n opscenter

# 测试 AWS RDS 连接
kubectl run -it --rm db-test --image=postgres:15-alpine --restart=Never -n opscenter -- \
  psql -h opscenter-postgres.xxxxxx.us-east-1.rds.amazonaws.com \
  -U postgres \
  -d opscenter \
  -c "SELECT 1"

# 测试 AWS ElastiCache 连接
kubectl run -it --rm redis-test --image=redis:7-alpine --restart=Never -n opscenter -- \
  redis-cli -h opscenter-redis.xxxxxx.cache.amazonaws.com \
  -p 6379 \
  ping
```

---

## 升级与回滚

### 滚动更新

```bash
# 更新镜像
kubectl set image deployment/opscenter-backend \
  backend=opscenter/backend:v2.0.0 \
  -n opscenter

# 查看滚动更新状态
kubectl rollout status deployment/opscenter-backend -n opscenter

# 查看更新历史
kubectl rollout history deployment/opscenter-backend -n opscenter
```

### 回滚

```bash
# 回滚到上一个版本
kubectl rollout undo deployment/opscenter-backend -n opscenter

# 回滚到指定版本
kubectl rollout undo deployment/opscenter-backend --to-revision=2 -n opscenter
```

---

## 最佳实践

### 1. 资源限制

始终设置资源请求和限制：

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

### 2. 安全性

- 不要在 ConfigMap 中存储敏感信息
- 使用 Secret 管理密码和密钥
- 使用 RBAC 限制 Pod 权限
- 使用 NetworkPolicy 限制网络访问
- 定期更新镜像版本

### 3. 高可用

- 部署多个副本（至少 2 个）
- 使用 Pod 反亲和性分散 Pod
- 配置 PodDisruptionBudget
- 使用多可用区部署

### 4. 备份与恢复

```bash
# 备份 PostgreSQL
kubectl exec postgresql-0 -n opscenter -- pg_dump -U postgres opscenter > backup.sql

# 恢复 PostgreSQL
kubectl exec -i postgresql-0 -n opscenter -- psql -U postgres opscenter < backup.sql
```

### 5. 监控告警

配置 Prometheus + Grafana 监控关键指标：
- CPU 使用率
- 内存使用率
- Pod 重启次数
- 请求延迟
- 错误率

---

## 支持与反馈

如有问题，请：

1. 查看 [故障排查](#故障排查) 章节
2. 提交 Issue 到 GitHub
3. 联系运维团队

---

## 附录

### 部署清单文件说明

| 文件 | 说明 |
|------|------|
| `00-namespace.yaml` | 命名空间配置 |
| `01-configmap.yaml` | 应用配置（包含 AWS 数据库配置） |
| `02-secret.yaml` | 敏感配置（包含 AWS 数据库密码） |
| `03-backend-deployment.yaml` | 后端部署 |
| `04-backend-service.yaml` | 后端服务 + HPA + PDB |
| `05-frontend-deployment.yaml` | 前端部署 |
| `06-frontend-service.yaml` | 前端服务和 Ingress |
| `09-rbac.yaml` | RBAC 权限配置 |

**注意**: PostgreSQL 和 Redis 使用 AWS 托管服务（Amazon RDS + Amazon ElastiCache），无需部署内置数据库。

### 环境变量完整列表

详见 `k8s/01-configmap.yaml` 和 `k8s/02-secret.yaml`。

---

**文档版本**: v1.0.0
**最后更新**: 2025-01-09
