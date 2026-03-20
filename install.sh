#!/bin/bash

# ============================================
# 运维管理平台 - 快速安装脚本
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║           运维管理平台 - 快速安装                         ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}[警告]${NC} 建议不要使用root用户运行此脚本"
fi

# 项目目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo -e "${BLUE}[1/5]${NC} 检查Python环境..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}[错误]${NC} 未安装Python，请先安装 Python 3.8+"
    echo "Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "CentOS/RHEL: sudo yum install python3 python3-pip"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python: $($PYTHON_CMD --version)"

echo -e "${BLUE}[2/5]${NC} 安装Python依赖..."
$PYTHON_CMD -m pip install -r backend/requirements.txt --quiet
echo -e "${GREEN}✓${NC} 依赖安装完成"

echo -e "${BLUE}[3/5]${NC} 创建配置文件..."
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# JWT密钥 (请修改为随机字符串)
JWT_SECRET_KEY=change-this-to-random-string

# 服务端口
PORT=5000
EOF
    echo -e "${GREEN}✓${NC} 已创建 .env 配置文件"
else
    echo -e "${GREEN}✓${NC} 配置文件已存在"
fi

echo -e "${BLUE}[4/5]${NC} 创建日志目录..."
mkdir -p logs
echo -e "${GREEN}✓${NC} 日志目录: logs/"

echo -e "${BLUE}[5/5]${NC} 设置脚本权限..."
chmod +x start.sh
echo -e "${GREEN}✓${NC} start.sh 已设置为可执行"

echo ""
echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
echo -e "${GREEN} 安装完成！${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
echo ""
echo "启动服务: ./start.sh"
echo "停止服务: ./start.sh stop"
echo "查看日志: ./start.sh logs"
echo "查看状态: ./start.sh status"
echo ""
echo -e "${YELLOW}提示:${NC} 请确保数据库(PostgreSQL或MySQL)已启动"
echo ""
