#!/bin/bash
# 运维管理平台 - Docker 入口脚本
# 同时启动 Nginx 和后端服务

set -e

echo "=========================================="
echo "  运维管理平台 - 启动中..."
echo "=========================================="

# 启动 Nginx（后台）
echo "[1/2] 启动 Nginx..."
nginx
echo "✓ Nginx 已启动"

# 启动后端服务（前台）
echo "[2/2] 启动后端 API..."
cd /app/backend
exec python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
