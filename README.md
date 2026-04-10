# OpsCenter - 一站式运维管理平台

企业级一站式运维管理平台，支持 MySQL/PostgreSQL/Redis 多实例管理、监控告警、变更审批、SQL 优化闭环、脚本执行、定时任务等功能。

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/vue-3.5+-green.svg)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.115+-teal.svg)](https://fastapi.tiangolo.com/)

## 快速开始

### Docker 部署（推荐）

```bash
git clone https://github.com/AlexLiu-vibecoding/ops-management-platform.git
cd ops-management-platform
cp .env.example .env                    # 配置数据库和安全密钥
cd release && docker-compose up -d    # 构建并启动
```

访问 http://localhost:5000，默认账号: `admin` / `admin123`

### 管理命令

```bash
cd release
docker-compose up -d       # 启动
docker-compose down        # 停止
docker-compose logs -f     # 查看日志
docker-compose restart     # 重启
```

### 本地开发

```bash
./ops.sh dev     # 开发模式
./ops.sh start   # 生产模式
./ops.sh build   # 构建前端
./ops.sh logs    # 查看日志
```

---

## 功能特性

### 核心功能

| 模块 | 功能 |
|------|------|
| 实例管理 | MySQL/PostgreSQL/Redis、AWS RDS、连接测试 |
| SQL 编辑器 | 语法高亮、自动补全、风险检测 |
| SQL 优化器 | EXPLAIN 分析、索引建议、AI 优化建议 |
| 变更审批 | DDL/DML 审批、自动回滚 SQL、风险分析 |
| 监控告警 | 性能监控、慢查询、告警规则、定时巡检 |
| 脚本任务 | Python/Bash/SQL 脚本、定时执行 |
| 消息通知 | 钉钉/企微/飞书/邮件/Webhook |
| 审计日志 | 操作记录、查询导出 |
| 密钥轮换 | 数据库密码、JWT Token 自动轮换 |
| AI 辅助 | SQL 优化建议、脚本生成、报告解读 |

### 特色功能

- **SQL 优化闭环**：采集 → 分析 → 建议 → 审批 → 执行 → 验证
- **回滚 SQL 生成**：自动分析变更，生成回滚脚本
- **大文件存储**：自动切换到 S3/OSS，支持 30 天自动清理
- **分库分表**：单库/多库选择、通配符匹配
- **变更窗口**：定义维护窗口，支持自动审批

---

## 技术栈

| 类型 | 技术 |
|------|------|
| 前端 | Vue 3.5 + Vite 6 + Element Plus 2.9 + Pinia 3 |
| 后端 | Python 3.11 + FastAPI 0.115 + SQLAlchemy 2 |
| 数据库 | PostgreSQL 16 / MySQL 8 |
| 缓存 | Redis 7 |
| 定时任务 | APScheduler 3 |
| AI | 豆包大模型 |
| 云服务 | AWS RDS/CloudWatch、S3、阿里云 OSS |

---

## 环境配置

参考 `.env.example` 配置文件，主要配置项：

```bash
# 数据库（必填）
DATABASE_URL=postgresql://user:password@host:5432/dbname
# 或 MySQL
# MYSQL_HOST=localhost; MYSQL_PORT=3306; ...

# 安全（可选，已有默认值）
# JWT_SECRET_KEY=your-custom-key
# AES_KEY=your-custom-32-char-aes-key!

# 存储
STORAGE_TYPE=local        # local / s3 / oss
LOCAL_STORAGE_PATH=/app/data/sql_files

# AI（可选）
# DOUBAO_API_KEY=your-api-key
```

> 详细配置见 `.env.example`，系统内置默认值，开箱即用。

---

## 数据保留策略

| 数据类型 | 存储位置 | 保留时间 |
|---------|---------|---------|
| 小 SQL（<10KB） | 数据库 | 永久 |
| 大 SQL（≥10KB） | 文件存储 | 30 天 |
| 慢日志文件 | 文件存储 | 30 天 |
| SQL 分析历史 | 数据库 | 1 年 |

---

## 项目结构

```
.
├── backend/                    # 后端
│   ├── app/
│   │   ├── api/               # API 路由 (35+ 模块)
│   │   ├── models/            # 数据模型
│   │   ├── services/          # 业务逻辑
│   │   └── main.py            # FastAPI 入口
│   ├── requirements.in         # 顶层依赖
│   └── requirements.lock.txt   # 锁定依赖
│
├── frontend/                   # 前端
│   ├── src/
│   │   ├── api/               # API 请求封装
│   │   ├── views/             # 页面组件 (30+)
│   │   └── router/            # 路由配置
│   └── package.json
│
├── release/                    # 部署文件
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── k8s/                   # K8s 部署清单
│
├── scripts/                    # 脚本
│   └── update_deps.sh         # 依赖更新
│
├── ops.sh                     # 管理脚本
└── README.md
```

---

## 依赖管理

```bash
# 更新依赖
./scripts/update_deps.sh

# 添加新依赖
# 1. 编辑 backend/requirements.in
# 2. 运行 ./scripts/update_deps.sh
```

---

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:5000/api/docs
- ReDoc: http://localhost:5000/api/redoc

---

## 常见问题

**端口被占用** → 修改 `.env` 中的 `PORT=8080`

**数据库连接失败** → 检查数据库服务、连接字符串、防火墙

**Docker 构建失败** → `docker-compose build --no-cache`

---

## License

MIT
