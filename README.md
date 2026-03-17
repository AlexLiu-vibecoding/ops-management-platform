# MySQL管理平台

企业级MySQL数据库管理平台，支持多实例管理、监控告警、变更审批等功能。

## 功能特性

### 核心功能
- 🔐 **认证与权限**：JWT Token认证、RBAC权限模型、多角色支持
- 🌍 **多环境管理**：开发/测试/预发/生产环境隔离、颜色标记
- 🗄️ **实例管理**：MySQL实例CRUD、连接测试、参数查看
- 📝 **SQL编辑器**：语法高亮、执行、风险检测、快照回滚
- 📋 **变更审批**：DDL/DML变更审批、风险分析、执行记录
- 📊 **全维度监控**：性能监控、慢查询分析、高CPU SQL监控、实例巡检
- 🔔 **钉钉通知**：审批通知、告警通知、操作通知
- 📒 **审计日志**：操作记录、查询导出、追溯分析

### 监控开关配置
- ✅ 全局监控开关：统一控制所有实例的监控功能
- ✅ 实例级开关：单独控制每个实例的监控类型
- ✅ 即时生效：配置修改后无需重启服务

### 安全特性
- 密码加密存储（加盐哈希 + AES加密）
- SQL风险检测与拦截
- 敏感操作审计日志
- 生产环境强制审批

## 技术栈

### 前端
- Vue 3 + Vite
- Element Plus
- Pinia状态管理
- Vue Router
- Axios
- ECharts（图表）

### 后端
- Python 3.11
- FastAPI
- SQLAlchemy
- PyMySQL
- Redis
- JWT认证

### 数据库
- MySQL 8.0（平台自身数据）
- Redis（缓存/Token）

## 快速开始

### 环境要求
- Node.js 20+
- Python 3.11+
- MySQL 8.0+
- Redis 6+

### 安装依赖

```bash
# 后端依赖
cd backend
pip install -r requirements.txt

# 前端依赖
cd ../frontend
pnpm install
```

### 配置

1. 复制后端配置文件
```bash
cd backend
cp .env.example .env
# 编辑.env文件，配置数据库、Redis等
```

2. 创建数据库
```sql
CREATE DATABASE mysql_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 启动

```bash
# 启动后端
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 启动前端
cd frontend
pnpm dev
```

### Docker部署

```bash
docker-compose up -d
```

## 默认账号

- 用户名：admin
- 密码：admin123

## 项目结构

```
.
├── backend/                # 后端代码
│   ├── app/
│   │   ├── api/           # API路由
│   │   ├── models/        # 数据库模型
│   │   ├── schemas/       # Pydantic模型
│   │   ├── utils/         # 工具函数
│   │   └── main.py        # 应用入口
│   └── requirements.txt
├── frontend/              # 前端代码
│   ├── src/
│   │   ├── api/          # API请求
│   │   ├── stores/       # 状态管理
│   │   ├── router/       # 路由配置
│   │   ├── views/        # 页面组件
│   │   └── layouts/      # 布局组件
│   └── package.json
├── docker-compose.yml
└── README.md
```

## 监控配置说明

### 全局监控开关
位于 `/monitor/settings` 页面，可控制：
- 慢查询监控开关
- 高CPU SQL监控开关
- 性能监控开关
- 实例巡检开关

### 实例级监控开关
在实例详情页面的"监控配置"标签，可单独控制每个实例的监控类型。

### 监控参数配置
- 性能采集间隔（默认10秒）
- 慢查询阈值（默认1秒）
- CPU告警阈值（默认80%）
- 数据保留天数（默认30天）

## API文档

启动后端服务后，访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

MIT
