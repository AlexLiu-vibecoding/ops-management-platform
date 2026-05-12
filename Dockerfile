# ============================================================
# 运维管理平台 - 单容器全栈部署镜像
# 包含: PostgreSQL + Redis + Nginx + 后端 + 前端
# ============================================================

# -------------------- 第一阶段：构建前端 --------------------
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# 安装 pnpm
RUN npm install -g pnpm

# 复制前端依赖文件
COPY frontend/package*.json frontend/pnpm-lock.yaml ./

# 安装依赖
RUN pnpm install

# 复制前端源码
COPY frontend/ ./

# 构建前端
RUN pnpm build

# -------------------- 第二阶段：构建后端依赖 --------------------
FROM python:3.11-slim AS backend-builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制依赖文件并安装
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -------------------- 第三阶段：运行镜像 --------------------
FROM python:3.11-slim

WORKDIR /app

# 安装运行时依赖：Nginx、PostgreSQL、Redis、Supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    curl \
    postgresql \
    postgresql-client \
    redis-server \
    supervisor \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash appuser

# 复制虚拟环境
COPY --from=backend-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制后端代码
COPY backend/ ./backend/

# 复制前端构建产物到 Nginx 目录
COPY --from=frontend-builder /app/frontend/dist /var/www/html

# 复制配置文件
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/opscenter.conf
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 创建必要目录
RUN mkdir -p /app/logs /run/postgresql /var/run/redis \
    && chown -R postgres:postgres /run/postgresql \
    && chown -R redis:redis /var/run/redis

# 数据持久化目录
VOLUME ["/var/lib/postgresql/data", "/app/logs"]

# 暴露端口 (LB 代理此端口)
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# 启动
ENTRYPOINT ["/entrypoint.sh"]
