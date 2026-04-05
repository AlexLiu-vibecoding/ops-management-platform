# OpsCenter - 云原生部署支持

## 📦 项目结构

```
opscenter/
├── k8s/                           # Kubernetes 部署清单
│   ├── 00-namespace.yaml          # 命名空间配置
│   ├── 01-configmap.yaml          # 应用配置（包含 AWS 数据库配置）
│   ├── 02-secret.yaml             # 敏感配置（包含 AWS 数据库密码）
│   ├── 03-backend-deployment.yaml  # 后端部署配置
│   ├── 04-backend-service.yaml    # 后端服务 + HPA + PDB
│   ├── 05-frontend-deployment.yaml # 前端部署配置
│   ├── 06-frontend-service.yaml   # 前端服务 + Ingress
│   └── 09-rbac.yaml               # RBAC 权限配置
├── helm/opscenter/                # Helm Chart
│   ├── Chart.yaml                 # Chart 元数据
│   ├── values.yaml                # 默认配置（禁用内置数据库）
│   └── templates/                 # 模板文件
│       └── _helpers.tpl           # 模板助手
├── deploy-k8s.sh                  # 一键部署脚本
├── docker-compose.yml             # Docker Compose 配置
├── Dockerfile                     # Docker 镜像构建
├── KUBERNETES_DEPLOYMENT.md       # 详细部署文档
├── KUBERNETES.md                  # 本文件
└── MIGRATION_GUIDE.md             # 迁移指南
```

**注意**: PostgreSQL 和 Redis 使用 AWS 托管服务（Amazon RDS + Amazon ElastiCache），无需部署内置数据库。

---

## 🚀 快速开始

### 前置要求

- Kubernetes 1.24+
- kubectl 1.24+
- Helm 3.0+（可选）
- **AWS 账号**（用于 Amazon RDS，可选用于 Amazon ElastiCache Redis）
- 集群可访问 AWS 托管服务

### 方式一：使用部署脚本（推荐）

```bash
# 1. 创建 AWS RDS PostgreSQL（必需）和 ElastiCache Redis（可选，见详细文档）
#    - 记录 RDS endpoint: opscenter-postgres.xxxxxx.us-east-1.rds.amazonaws.com
#    - 如需缓存，创建 ElastiCache Redis 并记录 endpoint

# 2. 修改 k8s/01-configmap.yaml，配置 AWS 数据库 endpoint
vim k8s/01-configmap.yaml
# 更新 POSTGRES_HOST
# 如需 Redis，更新 REDIS_HOST 并设置 REDIS_ENABLED="true"
# 如不需 Redis，设置 REDIS_ENABLED="false"

# 3. 修改 k8s/02-secret.yaml，配置 AWS 数据库密码
vim k8s/02-secret.yaml
# 更新 POSTGRES_PASSWORD
# 如需 Redis，更新 REDIS_PASSWORD

# 4. 运行部署脚本
./deploy-k8s.sh

# 5. 等待 Pod 就绪
kubectl get pods -n opscenter

# 6. 访问应用
kubectl port-forward svc/opscenter-frontend-service 8080:80 -n opscenter
# 浏览器访问: http://localhost:8080
```

### 方式二：手动部署

```bash
# 1. 创建命名空间
kubectl apply -f k8s/00-namespace.yaml

# 2. 应用配置
kubectl apply -f k8s/01-configmap.yaml
kubectl apply -f k8s/02-secret.yaml

# 3. 部署数据库
kubectl apply -f k8s/07-postgresql.yaml
kubectl apply -f k8s/08-redis.yaml

# 4. 部署应用
kubectl apply -f k8s/03-backend-deployment.yaml
kubectl apply -f k8s/04-backend-service.yaml
kubectl apply -f k8s/05-frontend-deployment.yaml
kubectl apply -f k8s/06-frontend-service.yaml

# 5. 验证部署
kubectl get pods,svc,ingress -n opscenter
```

### 方式三：使用 Helm Chart

```bash
# 1. 修改配置
vim helm/opscenter/values.yaml

# 2. 安装
helm install opscenter ./helm/opscenter \
  --namespace opscenter \
  --create-namespace

# 3. 升级
helm upgrade opscenter ./helm/opscenter \
  --namespace opscenter

# 4. 回滚
helm rollback opscenter -n opscenter
```

---

## ✨ 云原生特性

### 1. 弹性伸缩（HPA）

后端应用自动扩缩容配置：

```yaml
minReplicas: 3
maxReplicas: 10
metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### 2. 滚动更新

零停机部署更新：

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1        # 最多多1个 Pod
    maxUnavailable: 0   # 0个不可用
```

### 3. 自我修复

自动重启失败的 Pod：

```yaml
livenessProbe:
  httpGet:
    path: /api/init/status
    port: http
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 3
```

### 4. 配置管理

ConfigMap + Secret 分离配置：

```yaml
env:
  - name: APP_ENV
    valueFrom:
      configMapKeyRef:
        name: opscenter-config
        key: APP_ENV
  - name: POSTGRES_PASSWORD
    valueFrom:
      secretKeyRef:
        name: opscenter-secret
        key: POSTGRES_PASSWORD
```

### 5. 持久化存储

数据库数据持久化：

```yaml
volumes:
  - name: postgresql-data
    persistentVolumeClaim:
      claimName: postgresql-pvc
```

### 6. 高可用部署

Pod 反亲和性分散 Pod：

```yaml
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          topologyKey: kubernetes.io/hostname
```

---

## 📊 监控与日志

### Prometheus 监控

部署清单已包含 Prometheus 注解：

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "9090"
  prometheus.io/path: "/metrics"
```

### 查看日志

```bash
# 查看后端日志
kubectl logs -f deployment/opscenter-backend -n opscenter

# 查看前端日志
kubectl logs -f deployment/opscenter-frontend -n opscenter

# 查看数据库日志
kubectl logs -f statefulset/postgresql -n opscenter
```

---

## 🔧 配置管理

### 修改应用配置

编辑 `k8s/01-configmap.yaml`：

```yaml
data:
  APP_ENV: "production"
  LOG_LEVEL: "info"
  MAX_WORKERS: "4"
```

应用更新：

```bash
kubectl apply -f k8s/01-configmap.yaml
kubectl rollout restart deployment/opscenter-backend -n opscenter
```

### 修改敏感配置

```bash
# 方式1: 直接编辑 Secret
kubectl edit secret opscenter-secret -n opscenter

# 方式2: 重新创建 Secret
kubectl create secret generic opscenter-secret \
  --from-literal=POSTGRES_PASSWORD=new-password \
  --dry-run=client -o yaml | kubectl apply -f -
```

### 使用 Sealed Secrets（推荐生产环境）

```bash
# 安装 Sealed Secrets
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# 加密 Secret
kubeseal -f k8s/02-secret.yaml -w k8s/02-secret-sealed.yaml

# 部署加密的 Secret
kubectl apply -f k8s/02-secret-sealed.yaml
```

---

## 🔄 升级与回滚

### 滚动更新

```bash
# 更新镜像
kubectl set image deployment/opscenter-backend \
  backend=opscenter/backend:v2.0.0 \
  -n opscenter

# 查看更新状态
kubectl rollout status deployment/opscenter-backend -n opscenter

# 查看历史
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

## 🛠️ 故障排查

### Pod 无法启动

```bash
# 查看 Pod 状态
kubectl describe pod <pod-name> -n opscenter

# 查看日志
kubectl logs <pod-name> -n opscenter

# 查看事件
kubectl get events -n opscenter --sort-by='.lastTimestamp'
```

### 服务无法访问

```bash
# 检查 Service
kubectl get svc -n opscenter

# 检查 Endpoint
kubectl get endpoints -n opscenter

# 测试连通性
kubectl run -it --rm debug --image=busybox --restart=Never -n opscenter \
  -- wget -O- http://opscenter-backend-service:5000/api/init/status
```

### HPA 不工作

```bash
# 检查 HPA 状态
kubectl get hpa -n opscenter
kubectl describe hpa opscenter-backend-hpa -n opscenter

# 检查 Metrics Server
kubectl get apiservice v1beta1.metrics.k8s.io
```

---

## 📚 文档

- [KUBERNETES_DEPLOYMENT.md](KUBERNETES_DEPLOYMENT.md) - 详细部署文档
- [Helm Chart 文档](helm/opscenter/) - Helm Chart 配置说明

---

## 🤝 支持

如有问题，请：

1. 查看 [KUBERNETES_DEPLOYMENT.md](KUBERNETES_DEPLOYMENT.md)
2. 提交 Issue 到 GitHub
3. 联系运维团队

---

## 📝 License

Copyright © 2025 OpsCenter Team
