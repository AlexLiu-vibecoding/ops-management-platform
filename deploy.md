# 运维管理平台 - 部署指南

## 快速部署

### 1. 环境要求

- Python 3.8+
- PostgreSQL 或 MySQL
- Redis (可选)

### 2. 一键安装

```bash
# 克隆项目
git clone https://github.com/AlexLiu-vibecoding/ops-management-platform.git
cd ops-management-platform

# 运行安装脚本
chmod +x install.sh
./install.sh

# 启动服务
./start.sh
```

### 3. 访问系统

- 访问地址: http://localhost:5000
- 默认账号: `admin`
- 默认密码: `admin123`

---

## 详细部署

### 环境准备

#### Ubuntu/Debian

```bash
# 安装Python
sudo apt update
sudo apt install python3 python3-pip -y

# 安装PostgreSQL (可选)
sudo apt install postgresql postgresql-contrib -y

# 安装MySQL (可选)
sudo apt install mysql-server -y

# 安装Redis (可选)
sudo apt install redis-server -y
```

#### CentOS/RHEL

```bash
# 安装Python
sudo yum install python3 python3-pip -y

# 安装PostgreSQL (可选)
sudo yum install postgresql-server postgresql-contrib -y
sudo postgresql-setup initdb
sudo systemctl start postgresql

# 安装MySQL (可选)
sudo yum install mysql-server -y
sudo systemctl start mysqld

# 安装Redis (可选)
sudo yum install redis -y
sudo systemctl start redis
```

### 数据库配置

#### PostgreSQL

```bash
# 创建数据库
sudo -u postgres psql
CREATE DATABASE ops_platform;
CREATE USER ops_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE ops_platform TO ops_user;
\q

# 配置环境变量
export DATABASE_URL="postgresql://ops_user:your_password@localhost:5432/ops_platform"
```

#### MySQL

```bash
# 创建数据库
mysql -u root -p
CREATE DATABASE ops_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'ops_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON ops_platform.* TO 'ops_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# 配置环境变量
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=ops_user
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=ops_platform
```

### 配置文件

创建 `.env` 文件:

```bash
# 数据库配置 (PostgreSQL)
DATABASE_URL=postgresql://ops_user:your_password@localhost:5432/ops_platform

# 或 MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=ops_user
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=ops_platform

# Redis配置 (可选)
REDIS_HOST=localhost
REDIS_PORT=6379

# JWT密钥 (请修改为随机字符串)
JWT_SECRET_KEY=your-random-secret-key-here

# 服务端口
PORT=5000
```

### 启动服务

```bash
# 完整安装并启动
./start.sh all

# 或分步操作
./start.sh install   # 安装依赖
./start.sh init      # 初始化数据库
./start.sh start     # 启动服务
```

### 管理命令

```bash
./start.sh start     # 启动服务
./start.sh stop      # 停止服务
./start.sh restart   # 重启服务
./start.sh status    # 查看状态
./start.sh logs      # 查看日志
./start.sh help      # 查看帮助
```

---

## Docker 部署 (可选)

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY backend/ ./backend/
COPY frontend/dist/ ./frontend/dist/

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "5000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/ops_platform
      - REDIS_HOST=redis
      - JWT_SECRET_KEY=your-secret-key
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=ops_platform
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redisdata:/data

volumes:
  pgdata:
  redisdata:
```

### 启动

```bash
docker-compose up -d
```

---

## 生产环境建议

1. **使用 HTTPS**: 配置 Nginx 反向代理和 SSL 证书
2. **修改默认密码**: 登录后立即修改 admin 密码
3. **配置防火墙**: 只开放必要端口
4. **定期备份**: 备份配置和数据库
5. **日志轮转**: 配置日志切割避免磁盘占满

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Systemd 服务

创建 `/etc/systemd/system/ops-platform.service`:

```ini
[Unit]
Description=Ops Management Platform
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ops-platform
ExecStart=/usr/bin/python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 5000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ops-platform
sudo systemctl start ops-platform
```

---

## 常见问题

### 1. 端口被占用

```bash
# 查找占用端口的进程
lsof -i:5000
# 或
ss -tlnp | grep 5000

# 修改端口
export PORT=8080
./start.sh start
```

### 2. 数据库连接失败

- 检查数据库服务是否启动
- 检查用户名密码是否正确
- 检查防火墙是否允许连接

### 3. 权限问题

```bash
# 给脚本执行权限
chmod +x start.sh install.sh

# 给日志目录写权限
chmod 755 logs
```

---

## 技术支持

- GitHub: https://github.com/AlexLiu-vibecoding/ops-management-platform
