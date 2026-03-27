#!/bin/bash
# ============================================================
# 运维管理平台 - 启动脚本
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║           运维管理平台 - Ops Management Platform          ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 进入后端目录
cd "$SCRIPT_DIR"

# 检查 Python 版本
echo -e "${BLUE}[1/4] 检查 Python 版本...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python 版本: $PYTHON_VERSION"

# 安装依赖
echo -e "${BLUE}[2/4] 安装/更新依赖...${NC}"
pip install -q -r requirements.txt 2>/dev/null || {
    echo -e "${YELLOW}警告: 部分依赖安装可能有问题，继续启动...${NC}"
}

# 运行启动自检
echo -e "${BLUE}[3/4] 运行启动自检...${NC}"
python3 -c "from app.startup_check import run_startup_check; exit(0 if run_startup_check() else 1)" || {
    echo -e "${RED}启动自检失败！请检查上述错误。${NC}"
    exit 1
}

# 启动服务
echo -e "${BLUE}[4/4] 启动服务...${NC}"
PORT=${PORT:-5000}
echo -e "${GREEN}服务启动在端口: $PORT${NC}"
echo -e "${GREEN}访问地址: http://localhost:$PORT${NC}"
echo -e "${GREEN}API 文档: http://localhost:$PORT/docs${NC}"
echo ""

exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --reload
