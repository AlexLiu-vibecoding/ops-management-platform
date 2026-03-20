# ============================================================
# 运维管理平台 - 统一 Docker 镜像
# 包含前端和后端，使用 Nginx 作为 Web 服务器
# ============================================================

# -------------------- 第一阶段：构建前端 --------------------
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# 安装 pnpm
RUN npm install -g pnpm

# 复制前端依赖文件
COPY frontend/package*.json frontend/pnpm-lock.yaml ./

# 安装依赖
RUN pnpm install --frozen-lockfile

# 复制前端源码
COPY frontend/ ./

# 构建前端
RUN pnpm build

# -------------------- 第二阶段：构建后端 --------------------
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

# 安装运行时依赖和 Nginx
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    curl \
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

# 复制 Nginx 配置
COPY docker/nginx.conf /etc/nginx/sites-available/default
RUN rm -f /etc/nginx/sites-enabled/default \
    && ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# 复制启动脚本
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 创建日志目录
RUN mkdir -p /app/logs && chown -R appuser:appuser /app

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/api/init/status || exit 1

# 启动
ENTRYPOINT ["/entrypoint.sh"]
