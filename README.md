# OpsCenter - 一站式运维管理平台

企业级一站式运维管理平台，支持 MySQL/PostgreSQL/Redis 多实例管理、监控告警、变更审批、SQL 优化闭环、脚本执行、定时任务等功能。

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/vue-3.5+-green.svg)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.115+-teal.svg)](https://fastapi.tiangolo.com/)

## ⚡ 快速开始

### Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/AlexLiu-vibecoding/ops-management-platform.git
cd ops-management-platform

# 2. 创建配置文件
cp .env.example .env
# 编辑 .env 文件，配置数据库和安全密钥

# 3. 构建并启动
cd release
docker-compose up -d --build

# 4. 访问系统
# http://localhost:5000
# 默认账号: admin / admin123
```

### 管理命令

```bash
cd release
docker-compose up -d          # 启动服务
docker-compose down           # 停止服务
docker-compose logs -f        # 查看日志
docker-compose restart        # 重启服务
docker-compose ps             # 查看状态
```

### 本地开发

```bash
# 一键启动（需要 Python 和数据库）
chmod +x start.sh
./start.sh all     # 完整安装并启动
./start.sh         # 启动服务
./start.sh stop    # 停止服务
./start.sh logs    # 查看日志
```

---

## ✨ 功能特性

### 核心功能
- 🔐 **认证与权限**：JWT Token 认证、RBAC 权限模型、多角色支持（super_admin/approval_admin/operator/developer）
- 🌍 **多环境管理**：开发/测试/预发/生产环境隔离、环境权限控制
- 🗄️ **实例管理**：MySQL/PostgreSQL/Redis 实例管理、AWS RDS 支持、连接测试
- 📝 **SQL 编辑器**：语法高亮、自动补全、执行、风险检测
- 🚀 **SQL 优化器**：EXPLAIN 分析、索引建议、AI 深度优化建议（豆包大模型）
- 📋 **变更审批**：DDL/DML/Redis 变更审批、风险分析、分库分表支持
- 🔄 **回滚SQL生成**：自动分析SQL变更，生成回滚脚本，支持MySQL DDL/DML/Redis命令
- 📊 **全维度监控**：性能监控、慢查询分析、高 CPU SQL 监控、CloudWatch 集成
- 📦 **Redis 管理**：键管理、服务器信息、慢查询日志、客户端监控、配置管理
- 🔔 **消息通知**：钉钉/企业微信/飞书/邮件/Webhook 多渠道通知
- 📜 **脚本管理**：Python/Bash/SQL 脚本管理、批量执行
- ⏰ **定时任务**：定时执行脚本、审批定时执行
- 📒 **审计日志**：操作记录、查询导出、安全审计
- ⚙️ **系统配置**：动态菜单、数据库类型配置、存储策略配置

### 🔁 SQL 性能优化闭环（新功能）
完整的 SQL 性能优化生命周期管理：
- **自动采集**：定时采集慢 SQL，支持自定义阈值和调度周期
- **文件上传分析**：支持上传慢日志文件（.log/.txt）进行离线分析
- **智能分析**：LLM 驱动的 SQL 分析，自动检测性能问题
- **优化建议**：索引建议、SQL 改写、配置优化
- **一键变更**：采用建议自动创建变更申请，走审批流程
- **效果验证**：变更执行后自动验证优化效果
- **数据保留**：上传文件 30 天自动清理，分析历史保留 1 年

### 变更管理增强
- 变更申请与审批中心分离，流程更清晰
- 提交变更时自动生成回滚 SQL
- 分库分表支持：单库/多库选择、通配符匹配、全部数据库执行
- 变更窗口管理：定义维护窗口，支持自动审批

### 监控与告警
- 性能监控：实时性能指标、历史趋势图表
- 慢查询监控：慢查询列表、SQL 分析、优化建议
- 告警规则：灵活配置告警阈值、多渠道通知
- 定时巡检：自动生成巡检报告、异常告警

### AWS RDS 支持
- RDS 实例管理：支持 AWS RDS MySQL/PostgreSQL
- CloudWatch 监控：自动采集 RDS 性能指标
- 区域配置：支持全球 31 个 AWS 区域动态配置

### 大文件存储管理
- 智能存储：大 SQL 文件自动切换到文件存储
- 多后端支持：本地存储 / AWS S3 / 阿里云 OSS
- 生命周期管理：自动清理过期 SQL 文件（默认 30 天）
- 历史记录永久保存：数据库记录保留，仅清理物理文件

---

## 🛠️ 技术栈

| 类型 | 技术 |
|------|------|
| 前端框架 | Vue 3.5 + Vite 6 + Element Plus 2.9 |
| 状态管理 | Pinia 3 |
| 后端框架 | Python 3.11 + FastAPI 0.115 + SQLAlchemy 2 |
| 数据库 | PostgreSQL 16 / MySQL 8 |
| 缓存 | Redis 7 (可选，用于会话和缓存) |
| 定时任务 | APScheduler 3 |
| AI 集成 | 豆包大模型 (SQL优化建议) |
| AWS 集成 | boto3 (RDS CloudWatch 监控) |
| 对象存储 | AWS S3 / 阿里云 OSS |

---

## 📦 环境配置

创建 `.env` 文件：

```bash
# 服务端口
PORT=5000

# 数据库 (必填，PostgreSQL 推荐)
DATABASE_URL=postgresql://user:password@host:5432/dbname

# 或 MySQL
# MYSQL_HOST=localhost
# MYSQL_PORT=3306
# MYSQL_USER=root
# MYSQL_PASSWORD=your-password
# MYSQL_DATABASE=ops_platform

# Redis (可选，用于缓存和会话)
# REDIS_HOST=localhost
# REDIS_PORT=6379

# 安全配置（可选，已有默认值）
# JWT_SECRET_KEY=your-custom-key
# AES_KEY=your-custom-32-char-aes-key!
# PASSWORD_SALT=your-custom-salt

# ====== 存储配置 ======
# 存储类型: local (本地), s3 (AWS S3), oss (阿里云OSS)
STORAGE_TYPE=local

# 本地存储路径
LOCAL_STORAGE_PATH=/app/data/sql_files

# 文件生命周期
SQL_FILE_RETENTION_DAYS=30
SQL_FILE_SIZE_THRESHOLD=10000

# AWS S3 配置
# AWS_ACCESS_KEY_ID=your-access-key
# AWS_SECRET_ACCESS_KEY=your-secret-key
# AWS_REGION=us-east-1
# S3_BUCKET_NAME=your-bucket

# 阿里云 OSS 配置
# OSS_ACCESS_KEY_ID=your-access-key
# OSS_ACCESS_KEY_SECRET=your-secret-key
# OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
# OSS_BUCKET_NAME=your-bucket

# ====== AI 配置 ======
# 豆包大模型 (SQL优化建议)
# DOUBAO_API_KEY=your-api-key
# DOUBAO_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
# DOUBAO_MODEL=ep-xxxx
```

---

## 💾 数据保留策略

| 数据类型 | 存储位置 | 保留时间 | 清理方式 |
|---------|---------|---------|---------|
| 小 SQL（<10KB） | 数据库 | 永久 | - |
| 大 SQL（≥10KB） | 文件存储 | 30 天 | 定时清理 |
| 慢日志上传文件 | 文件存储 | 30 天 | 定时清理 |
| SQL 分析历史 | 数据库 | 1 年 | 定时清理 |
| 审批记录 | 数据库 | 永久 | - |

---

## 🔒 安全配置

**开箱即用**：系统已内置默认密钥，无需配置即可使用！

| 配置项 | 用途 | 说明 |
|--------|------|------|
| `JWT_SECRET_KEY` | 签名用户登录 Token | 内置默认值，可自定义 |
| `AES_KEY` | 加密存储的数据库密码 | 内置默认值（32字符），可自定义 |
| `PASSWORD_SALT` | 用户密码加密盐值 | 内置默认值，可自定义 |

⚠️ **生产环境建议**：请在 `.env` 中自定义密钥，自定义后需重置用户密码。

---

## 📁 项目结构

```
.
├── backend/                    # 后端代码
│   ├── app/
│   │   ├── api/               # API 路由 (35+ 模块)
│   │   │   ├── auth.py                # 认证接口
│   │   │   ├── instances.py           # 实例管理
│   │   │   ├── rdb_instances.py       # RDB 实例管理
│   │   │   ├── redis_instances.py     # Redis 实例管理
│   │   │   ├── sql.py                 # SQL 操作
│   │   │   ├── sql_optimizer.py       # SQL 优化器
│   │   │   ├── sql_optimization.py    # SQL 优化闭环
│   │   │   ├── approval.py            # 审批接口
│   │   │   ├── monitor.py             # 监控接口
│   │   │   ├── alerts.py              # 告警管理
│   │   │   ├── scripts.py             # 脚本管理
│   │   │   ├── scheduled_tasks.py     # 定时任务
│   │   │   └── ...
│   │   ├── models/            # 数据库模型
│   │   ├── schemas/           # 请求响应模型
│   │   ├── services/          # 业务逻辑
│   │   │   ├── rollback_generator.py    # 回滚SQL生成
│   │   │   ├── sql_optimization_service.py  # SQL优化闭环服务
│   │   │   ├── scheduler.py            # 定时任务调度
│   │   │   ├── storage.py              # 存储服务
│   │   │   └── notification.py         # 通知服务
│   │   ├── utils/             # 工具类
│   │   ├── config.py          # 配置管理
│   │   ├── database.py        # 数据库连接
│   │   └── main.py            # FastAPI 入口
│   └── requirements.txt
│
├── frontend/                   # 前端代码
│   ├── src/
│   │   ├── api/               # API 请求封装
│   │   ├── stores/            # Pinia 状态管理
│   │   ├── views/             # 页面组件 (30+ 页面)
│   │   │   ├── dashboard/              # 仪表盘
│   │   │   ├── instances/              # 实例管理
│   │   │   ├── sql-editor/             # SQL 编辑器
│   │   │   ├── sql-optimizer/          # SQL 优化器
│   │   │   ├── change/                 # 变更审批
│   │   │   ├── monitor/                # 监控中心
│   │   │   │   ├── performance/        # 性能监控
│   │   │   │   ├── slow-query/         # 慢查询监控
│   │   │   │   │   ├── index.vue       # 主页面
│   │   │   │   │   ├── SlowQueryList.vue
│   │   │   │   │   ├── OptimizationSuggestions.vue
│   │   │   │   │   ├── CollectionTasks.vue
│   │   │   │   │   ├── FileUpload.vue
│   │   │   │   │   └── AnalysisHistory.vue
│   │   │   │   └── alerts/             # 告警中心
│   │   │   ├── scripts/                # 脚本管理
│   │   │   ├── permissions/            # 权限管理
│   │   │   └── ...
│   │   ├── components/        # 可复用组件
│   │   ├── layouts/           # 布局组件
│   │   └── router/            # 路由配置
│   └── package.json
│
├── .vibecoding/               # 协作文档
│   ├── specs/                 # 功能规格 (16个)
│   └── VIBECODING.md          # 协作经验
│
├── release/                   # 部署相关文件
│   ├── docker/                # Docker 配置
│   │   ├── entrypoint.sh      # 容器启动脚本
│   │   └── nginx.conf         # Nginx 配置
│   ├── Dockerfile             # 统一 Docker 镜像
│   ├── docker-compose.yml     # Docker Compose 配置
│   ├── k8s/                   # Kubernetes 部署清单
│   ├── helm/opscenter/        # Helm Chart
│   ├── docs/                  # 部署文档
│   ├── deploy-k8s.sh          # K8s 部署脚本
│   └── README.md              # 部署说明
│
├── start.sh                   # 本地启动脚本
├── AGENTS.md                  # AI 开发指南
└── README.md
```

---

## 🐳 Docker 部署

### 快速部署

```bash
# 1. 克隆项目
git clone https://github.com/AlexLiu-vibecoding/ops-management-platform.git
cd ops-management-platform

# 2. 创建配置文件
cp .env.example .env
# 编辑 .env 文件，配置数据库

# 3. 构建并启动
docker-compose up -d --build

# 4. 访问系统
# http://localhost:5000
# 默认账号: admin / admin123
```

### 常用命令

```bash
docker-compose up -d          # 启动服务
docker-compose down           # 停止服务
docker-compose logs -f        # 查看日志
docker-compose restart        # 重启服务
docker-compose ps             # 查看状态
```

---

## 📖 API 文档

启动服务后访问：
- Swagger UI: http://localhost:5000/api/docs
- ReDoc: http://localhost:5000/api/redoc

---

## 🔧 常见问题

### 端口被占用
修改 `.env` 中的 `PORT=8080`

### 数据库连接失败
- 检查数据库服务是否启动
- 检查连接字符串是否正确
- 检查防火墙和网络连通性

### Docker 构建失败
```bash
docker-compose build --no-cache
```

---

## 📄 License

MIT
