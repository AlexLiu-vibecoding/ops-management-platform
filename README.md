# 运维管理平台

企业级一站式运维管理平台，支持 MySQL/PostgreSQL/Redis 多实例管理、监控告警、变更审批、回滚SQL生成、脚本执行、定时任务等功能。

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
docker-compose up -d --build

# 4. 访问系统
# http://localhost:5000
# 默认账号: admin / admin123
```

### 管理命令

```bash
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
- 🔐 **认证与权限**：JWT Token 认证、RBAC 权限模型、多角色支持
- 🌍 **多环境管理**：开发/测试/预发/生产环境隔离
- 🗄️ **实例管理**：MySQL/PostgreSQL/Redis 实例管理、连接测试
- 📝 **SQL 编辑器**：语法高亮、执行、风险检测
- 📋 **变更审批**：DDL/DML 变更审批、风险分析、分库分表支持
- 🔄 **回滚SQL生成**：自动分析SQL变更，生成回滚脚本，提升操作安全性
- 📊 **全维度监控**：性能监控、慢查询分析、高 CPU SQL 监控
- 📦 **Redis 管理**：键管理、服务器信息、慢查询日志、客户端监控
- 🔔 **消息通知**：钉钉/企业微信/飞书/邮件/Webhook 通知
- 📜 **脚本管理**：SQL 脚本管理、批量执行
- ⏰ **定时任务**：定时执行 SQL、审批定时执行
- 📒 **审计日志**：操作记录、查询导出

### 变更审批增强
- ✅ 变更申请与审批中心分离，流程更清晰
- ✅ 提交变更时自动生成回滚SQL
- ✅ 支持 MySQL DDL/DML 回滚SQL生成
- ✅ 支持 Redis 命令回滚建议
- ✅ 回滚SQL一键复制，方便快速恢复

### 分库分表变更审批
- ✅ 单库选择、多库选择
- ✅ 通配符匹配：`db_%` 或 `user_db_*` 等模式
- ✅ 全部数据库执行
- ✅ SQL 自动解析 `db.table` 格式

### Redis 实例管理
- ✅ 单机/集群/哨兵模式支持
- ✅ 键扫描、查看、编辑、删除
- ✅ 服务器信息、内存使用、统计信息
- ✅ 慢查询日志、客户端列表
- ✅ 配置查看与修改

### 大文件存储管理
- ✅ 智能存储：大SQL文件自动切换到文件存储
- ✅ 多后端支持：本地存储 / AWS S3 / 阿里云 OSS
- ✅ 生命周期管理：自动清理过期SQL文件（默认30天）
- ✅ 历史记录永久保存：数据库记录保留，仅清理物理文件
- ✅ 配置灵活：支持阈值、保留天数、存储类型等配置
- ✅ 慢查询日志、客户端列表
- ✅ 配置查看与修改

---

## 🛠️ 技术栈

| 类型 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus + Pinia |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy |
| 数据库 | PostgreSQL / MySQL |
| 缓存 | Redis (可选) |
| 定时任务 | APScheduler |
| AI 集成 | 豆包大模型 (SQL优化建议) |

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

# 安全配置（可选，已有默认值）
# JWT_SECRET_KEY=your-custom-key
# AES_KEY=your-custom-32-char-aes-key!
# PASSWORD_SALT=your-custom-salt

# ====== 存储配置 ======
# 存储类型: local (本地), s3 (AWS S3), oss (阿里云OSS)
STORAGE_TYPE=local

# 本地存储路径（STORAGE_TYPE=local 时使用）
LOCAL_STORAGE_PATH=/app/data/sql_files

# 文件生命周期（天数）
SQL_FILE_RETENTION_DAYS=30

# 大文件阈值（字符数），超过此大小存文件而非数据库
SQL_FILE_SIZE_THRESHOLD=10000

# AWS S3 配置（STORAGE_TYPE=s3 时使用）
# AWS_ACCESS_KEY_ID=your-access-key
# AWS_SECRET_ACCESS_KEY=your-secret-key
# AWS_REGION=us-east-1
# S3_BUCKET_NAME=your-bucket
# S3_ENDPOINT_URL=https://s3.amazonaws.com  # 可选，用于兼容S3的服务

# 阿里云 OSS 配置（STORAGE_TYPE=oss 时使用）
# OSS_ACCESS_KEY_ID=your-access-key
# OSS_ACCESS_KEY_SECRET=your-secret-key
# OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
# OSS_BUCKET_NAME=your-bucket
```

---

## 💾 大文件存储架构

### 设计原则

1. **智能存储**：小SQL直接存数据库，大SQL自动存文件
2. **多后端支持**：本地存储、AWS S3、阿里云OSS 三种选择
3. **生命周期管理**：定时清理过期文件，控制存储成本
4. **历史永久保存**：数据库记录保留，仅清理物理文件

### 存储策略

| 场景 | 存储位置 | 保留策略 |
|------|---------|---------|
| 小SQL（<10KB） | 数据库 `sql_content` 字段 | 永久保留 |
| 大SQL（≥10KB） | 文件存储（本地/S3/OSS） | 30天后清理 |
| 回滚SQL | 与原SQL相同策略 | 与原SQL相同 |
| 审批记录 | 数据库 `approval_records` 表 | 永久保留 |

### 文件清理规则

- **触发条件**：已执行/已拒绝/执行失败的审批
- **清理时间**：创建时间超过保留天数（默认30天）
- **清理内容**：仅删除物理文件，数据库记录保留
- **定时任务**：每天凌晨2点自动执行

---

## 🔒 安全配置说明

**开箱即用：系统已内置默认密钥，无需配置即可使用！**

| 配置项 | 用途 | 说明 |
|--------|------|------|
| `JWT_SECRET_KEY` | 签名用户登录 Token | 内置默认值，可自定义 |
| `AES_KEY` | 加密存储的数据库密码 | 内置默认值（32字符），可自定义 |
| `PASSWORD_SALT` | 用户密码加密盐值 | 内置默认值，可自定义 |

### 生产环境建议

默认密钥是公开的，如果对安全有高要求，请在 `.env` 中自定义：

```bash
JWT_SECRET_KEY=your-custom-secret-key-at-least-32-chars
AES_KEY=your-custom-32-character-aes-key!
PASSWORD_SALT=your-custom-salt
```

⚠️ **自定义密钥后需重置用户密码**

---

## 📁 项目结构

```
.
├── backend/                 # 后端代码
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── models/         # 数据库模型
│   │   ├── schemas/        # 请求响应模型
│   │   ├── services/       # 业务逻辑
│   │   │   ├── rollback_generator.py  # 回滚SQL生成
│   │   │   └── scheduler.py          # 定时任务调度
│   │   ├── utils/          # 工具类
│   │   │   └── redis_operations.py   # Redis操作工具
│   │   └── main.py         # 应用入口
│   └── requirements.txt
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── api/           # API 请求
│   │   ├── stores/        # 状态管理
│   │   ├── views/         # 页面组件
│   │   ├── components/    # 可复用组件
│   │   │   ├── SqlViewer.vue          # SQL显示组件
│   │   │   └── ApprovalDetailCard.vue # 审批详情卡片
│   │   └── router/        # 路由配置
│   └── package.json
├── docker/                 # Docker 配置
│   ├── nginx.conf         # Nginx 配置
│   └── entrypoint.sh      # 启动脚本
├── Dockerfile              # 统一 Docker 镜像
├── docker-compose.yml      # Docker Compose 配置
├── start.sh               # 本地启动脚本
└── README.md
```

---

## 🐳 Docker 部署详解

### 方式一：Docker Compose（推荐）

```bash
# 构建镜像
docker-compose build

# 后台启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 方式二：直接使用 Docker

```bash
# 构建镜像
docker build -t ops-platform:latest .

# 运行容器
docker run -d \
  --name ops-platform \
  -p 5000:5000 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  -e JWT_SECRET_KEY="your-secret-key" \
  -e AES_KEY="your-32-char-aes-key-here!!" \
  -e PASSWORD_SALT="your-salt" \
  ops-platform:latest
```

### 使用外部数据库

平台支持连接外部 PostgreSQL 或 MySQL 数据库：

```yaml
# docker-compose.yml
environment:
  - DATABASE_URL=postgresql://user:password@your-pg-host:5432/ops_platform
  # 或
  - MYSQL_HOST=your-mysql-host
  - MYSQL_PORT=3306
  - MYSQL_USER=root
  - MYSQL_PASSWORD=password
  - MYSQL_DATABASE=ops_platform
```

---

## 🔒 安全配置

| 变量 | 说明 | 要求 |
|------|------|------|
| `JWT_SECRET_KEY` | JWT 密钥 | 至少 32 字符 |
| `AES_KEY` | AES 加密密钥 | 必须 32 字符 |
| `PASSWORD_SALT` | 密码加密盐 | 任意字符串 |

⚠️ **生产环境务必修改默认密码和安全密钥！**

---

## 📖 API 文档

启动服务后访问：
- Swagger UI: http://localhost:5000/api/docs
- ReDoc: http://localhost:5000/api/redoc

---

## 🔧 常见问题

### 1. 端口被占用

```bash
# 修改 .env 中的端口
PORT=8080
```

### 2. 数据库连接失败

- 检查数据库服务是否启动
- 检查连接字符串是否正确
- 检查防火墙和网络连通性

### 3. Docker 构建失败

```bash
# 清理 Docker 缓存重新构建
docker-compose build --no-cache
```

---

## 📄 License

MIT
