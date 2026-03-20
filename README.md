# 运维管理平台

企业级数据库运维管理平台，支持 MySQL/PostgreSQL 多实例管理、监控告警、变更审批、脚本执行、定时任务等功能。

## ⚡ 快速开始

### Linux 一键部署

```bash
# 克隆项目
git clone https://github.com/AlexLiu-vibecoding/ops-management-platform.git
cd ops-management-platform

# 一键安装
chmod +x install.sh && ./install.sh

# 启动服务
./start.sh

# 访问系统 http://localhost:5000
# 默认账号: admin / admin123
```

### 管理命令

```bash
./start.sh          # 启动服务
./start.sh stop     # 停止服务
./start.sh restart  # 重启服务
./start.sh status   # 查看状态
./start.sh logs     # 查看日志
./start.sh help     # 查看帮助
```

---

## 功能特性

### 核心功能
- 🔐 **认证与权限**：JWT Token认证、RBAC权限模型、多角色支持
- 🌍 **多环境管理**：开发/测试/预发/生产环境隔离、颜色标记
- 🗄️ **实例管理**：MySQL/PostgreSQL 实例管理、连接测试、参数查看
- 📝 **SQL编辑器**：语法高亮、执行、风险检测、快照回滚
- 📋 **变更审批**：DDL/DML变更审批、风险分析、分库分表支持
- 📊 **全维度监控**：性能监控、慢查询分析、高CPU SQL监控、实例巡检
- 🔔 **钉钉通知**：审批通知、告警通知、操作通知
- 📜 **脚本管理**：SQL脚本管理、批量执行
- ⏰ **定时任务**：定时执行SQL、审批定时执行
- 📒 **审计日志**：操作记录、查询导出、追溯分析

### 分库分表变更审批
- ✅ 单库选择：传统的单数据库选择
- ✅ 多库选择：可多选数据库（支持搜索、折叠显示）
- ✅ 通配符匹配：输入 `db_%` 或 `user_db_*` 等模式匹配分库
- ✅ 全部数据库：对实例上所有数据库执行
- ✅ SQL自动解析：从SQL中解析 `db.table` 格式的数据库引用

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
- ECharts（图表）

### 后端
- Python 3.11
- FastAPI
- SQLAlchemy
- PyMySQL / psycopg2
- Redis
- APScheduler（定时任务）

### 数据库
- PostgreSQL / MySQL（平台自身数据）
- Redis（缓存/Token）

---

## 详细部署

详细部署文档请参考 [deploy.md](deploy.md)

### 方式一：Docker Compose 部署（推荐）

#### 1. 环境准备
```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

#### 2. 克隆项目
```bash
git clone <your-repo-url>
cd mysql-platform
```

#### 3. 配置环境变量
```bash
# 创建 .env 文件
cat > .env << 'EOF'
# 数据库密码
MYSQL_ROOT_PASSWORD=your-strong-root-password
MYSQL_PASSWORD=your-strong-admin-password

# 安全密钥（至少32字符）
SECRET_KEY=your-super-secret-key-at-least-32-characters-long

# 密码加密盐
PASSWORD_SALT=your-password-salt

# AES加密密钥（必须32字符）
AES_KEY=your-aes-key-must-be-32-chars!!

# 调试模式（生产环境设为false）
DEBUG=false
EOF
```

#### 4. 启动服务
```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

#### 5. 访问系统
- 前端地址：http://your-server-ip:5000
- API文档：http://your-server-ip:8000/docs
- 默认账号：admin / admin123

#### 6. 停止服务
```bash
docker-compose down

# 同时删除数据卷（清空数据）
docker-compose down -v
```

---

### 方式二：手动部署

#### 1. 环境准备

```bash
# 安装 Python 3.11
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# 安装 Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs

# 安装 pnpm
npm install -g pnpm

# 安装 MySQL 8.0
sudo apt install mysql-server

# 安装 Redis
sudo apt install redis-server
```

#### 2. 创建数据库

```sql
-- 登录 MySQL
mysql -u root -p

-- 创建数据库
CREATE DATABASE mysql_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户
CREATE USER 'mysql_platform'@'localhost' IDENTIFIED BY 'your-password';
GRANT ALL PRIVILEGES ON mysql_platform.* TO 'mysql_platform'@'localhost';
FLUSH PRIVILEGES;
```

#### 3. 后端部署

```bash
cd backend

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cat > .env << 'EOF'
# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=mysql_platform
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=mysql_platform

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379

# 安全配置
SECRET_KEY=your-super-secret-key-at-least-32-characters-long
PASSWORD_SALT=your-password-salt
AES_KEY=your-aes-key-must-be-32-chars!!

DEBUG=false
EOF

# 初始化数据库（首次部署）
# 系统会自动创建表结构

# 启动服务（开发模式）
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 生产环境使用 Gunicorn
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

#### 4. 前端部署

```bash
cd frontend

# 安装依赖
pnpm install

# 配置后端API地址（如果前后端分离部署）
# 编辑 vite.config.js，修改 proxy 配置

# 构建
pnpm build

# 部署到 Nginx
sudo apt install nginx

# 复制构建产物
sudo cp -r dist/* /var/www/html/

# 配置 Nginx
sudo cat > /etc/nginx/sites-available/mysql-platform << 'EOF'
server {
    listen 80;
    server_name your-domain.com;
    
    root /var/www/html;
    index index.html;
    
    # 前端路由
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # API代理
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# 启用站点
sudo ln -s /etc/nginx/sites-available/mysql-platform /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

### 方式三：使用 Systemd 管理服务（生产推荐）

#### 1. 创建后端服务

```bash
sudo cat > /etc/systemd/system/mysql-platform-api.service << 'EOF'
[Unit]
Description=MySQL Platform API
After=network.target mysql.service redis.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/mysql-platform/backend
Environment="PATH=/opt/mysql-platform/backend/venv/bin"
ExecStart=/opt/mysql-platform/backend/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

#### 2. 启动服务

```bash
sudo systemctl daemon-reload
sudo systemctl enable mysql-platform-api
sudo systemctl start mysql-platform-api

# 查看状态
sudo systemctl status mysql-platform-api

# 查看日志
sudo journalctl -u mysql-platform-api -f
```

---

## 环境变量配置说明

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `SECRET_KEY` | JWT密钥，至少32字符 | - | ✅ |
| `AES_KEY` | AES加密密钥，必须32字符 | - | ✅ |
| `PASSWORD_SALT` | 密码加密盐 | - | ✅ |
| `MYSQL_HOST` | MySQL主机 | localhost | |
| `MYSQL_PORT` | MySQL端口 | 3306 | |
| `MYSQL_USER` | MySQL用户名 | root | |
| `MYSQL_PASSWORD` | MySQL密码 | - | |
| `MYSQL_DATABASE` | MySQL数据库 | mysql_platform | |
| `REDIS_HOST` | Redis主机 | localhost | |
| `REDIS_PORT` | Redis端口 | 6379 | |
| `REDIS_PASSWORD` | Redis密码 | - | |
| `DEBUG` | 调试模式 | false | |

### PostgreSQL 支持

平台也支持使用 PostgreSQL 作为数据库：

```bash
# 使用 DATABASE_URL 环境变量
DATABASE_URL=postgresql://user:password@host:5432/dbname

# 或使用 DB_* 变量
DB_HOST=your-pg-host
DB_PORT=5432
DB_USER=your-user
DB_PASSWORD=your-password
DB_NAME=mysql_platform
```

---

## Nginx 配置（前后端分离）

如果前后端部署在不同服务器：

```nginx
# 前端服务器
server {
    listen 80;
    server_name your-domain.com;
    
    root /var/www/html;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # API 转发到后端服务器
    location /api {
        proxy_pass http://backend-server-ip:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

---

## HTTPS 配置（生产推荐）

使用 Let's Encrypt 免费证书：

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

---

## 监控与日志

### 查看日志

```bash
# Docker 部署
docker-compose logs -f backend
docker-compose logs -f frontend

# 手动部署
sudo journalctl -u mysql-platform-api -f
```

### 健康检查

```bash
# 检查后端健康
curl http://localhost:8000/health

# 检查数据库连接
curl http://localhost:8000/api/instances
```

---

## 数据备份

```bash
# 备份 MySQL 数据
mysqldump -u root -p mysql_platform > backup_$(date +%Y%m%d).sql

# Docker 环境备份
docker exec mysql-platform-db mysqldump -u root -p${MYSQL_ROOT_PASSWORD} mysql_platform > backup.sql
```

---

## 常见问题

### 1. 密码解密失败
如果遇到 "密码解密失败" 错误，说明数据库中存储的密码是用旧密钥加密的。解决方法：
- 重新保存实例密码
- 或确保 `AES_KEY` 与加密时使用的密钥一致

### 2. 跨域问题
确保后端 CORS 配置正确，或使用 Nginx 反向代理。

### 3. 连接 MySQL 超时
检查网络连通性和防火墙设置：
```bash
telnet mysql-host 3306
```

---

## 默认账号

- 用户名：admin
- 密码：admin123

**⚠️ 生产环境请务必修改默认密码！**

---

## 项目结构

```
.
├── backend/                # 后端代码
│   ├── app/
│   │   ├── api/           # API路由
│   │   ├── models/        # 数据库模型
│   │   ├── schemas/       # Pydantic模型
│   │   ├── utils/         # 工具函数
│   │   ├── config.py      # 配置文件
│   │   └── main.py        # 应用入口
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/              # 前端代码
│   ├── src/
│   │   ├── api/          # API请求
│   │   ├── stores/       # 状态管理
│   │   ├── router/       # 路由配置
│   │   ├── views/        # 页面组件
│   │   └── layouts/      # 布局组件
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── init/                  # 初始化脚本
│   └── init.sql
├── docker-compose.yml
└── README.md
```

---

## API文档

启动后端服务后，访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## License

MIT
