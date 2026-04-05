# OpsCenter 部署文件

本目录包含 OpsCenter 的所有部署相关文件。

## 目录结构

```
release/
├── k8s/              # Kubernetes 部署清单（生产环境）
├── helm/opscenter/   # Helm Chart
├── docs/             # 部署文档
├── deploy-k8s.sh     # Kubernetes 部署脚本
└── docker-compose.yml # Docker Compose 配置（开发环境）
```

## 快速开始

### Kubernetes 部署（生产环境）

```bash
# 进入 release 目录
cd release

# 使用部署脚本（推荐）
./deploy-k8s.sh

# 或手动部署
kubectl apply -f k8s/
```

### Docker Compose 部署（开发环境）

```bash
# 进入 release 目录
cd release

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 文档说明

- [KUBERNETES_DEPLOYMENT.md](docs/KUBERNETES_DEPLOYMENT.md) - 详细的 Kubernetes 部署文档
- [KUBERNETES.md](docs/KUBERNETES.md) - 快速部署指南
- [MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md) - AWS 托管服务迁移指南

## 配置说明

### 必需配置

1. **AWS RDS PostgreSQL**（必需）
   - 编辑 `k8s/01-configmap.yaml`，配置 `POSTGRES_HOST`
   - 编辑 `k8s/02-secret.yaml`，配置 `POSTGRES_PASSWORD`

2. **TLS 证书**（生产环境推荐）
   - 配置 `k8s/06-frontend-service.yaml` 中的 Ingress TLS

### 可选配置

1. **AWS ElastiCache Redis**（可选）
   - 编辑 `k8s/01-configmap.yaml`，配置 `REDIS_HOST` 和 `REDIS_ENABLED="true"`
   - 不配置 Redis 时，系统将禁用缓存功能

2. **对象存储**（可选）
   - 编辑 `k8s/01-configmap.yaml`，配置 `STORAGE_TYPE` 和相关参数

## 环境变量

| 变量 | 说明 | 默认值 | 必需 |
|------|------|--------|------|
| `POSTGRES_HOST` | AWS RDS PostgreSQL endpoint | - | ✅ |
| `POSTGRES_PASSWORD` | AWS RDS PostgreSQL 密码 | - | ✅ |
| `REDIS_ENABLED` | 是否启用 Redis | "true" | ❌ |
| `REDIS_HOST` | AWS ElastiCache Redis endpoint | - | ❌ |

## 常用命令

```bash
# 查看部署状态
kubectl get pods -n opscenter
kubectl get services -n opscenter

# 查看日志
kubectl logs -f deployment/opscenter-backend -n opscenter

# 重启部署
kubectl rollout restart deployment opscenter-backend -n opscenter

# 卸载
kubectl delete namespace opscenter
```

## 注意事项

1. **生产环境**:
   - 必须使用 AWS RDS PostgreSQL
   - 推荐启用 TLS/HTTPS
   - 推荐配置 Redis 缓存

2. **开发环境**:
   - 可使用 docker-compose.yml
   - TLS 可选

3. **安全性**:
   - 不要将 `k8s/02-secret.yaml` 提交到版本控制
   - 使用 SealedSecrets 或 Vault 管理敏感配置
   - 定期更新数据库密码

## 故障排查

### Pod 启动失败

```bash
# 查看 Pod 状态
kubectl describe pod <pod-name> -n opscenter

# 查看日志
kubectl logs <pod-name> -n opscenter
```

### 数据库连接失败

1. 检查 AWS RDS endpoint 是否正确
2. 检查 VPC 安全组配置
3. 检查数据库密码是否正确

### Redis 连接失败（可选组件）

如果未配置 Redis，可以忽略此类错误。系统会自动禁用缓存功能。

## 获取帮助

详细文档请参考 [docs/](./docs/) 目录。
