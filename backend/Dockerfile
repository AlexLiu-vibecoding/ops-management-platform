# ============================================================
# 第一阶段：构建
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# ============================================================
# 第二阶段：运行
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# 只安装运行时依赖（减小镜像体积）
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    curl \
    && useradd --create-home --shell /bin/bash appuser \
    && rm -rf /var/lib/apt/lists/*

# 复制虚拟环境（从 builder）
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制应用代码
COPY --from=builder /app /app

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
