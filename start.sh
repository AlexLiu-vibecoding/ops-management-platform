#!/bin/bash

# ============================================
# 运维管理平台 - 一键启动脚本
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# 配置文件
ENV_FILE="$PROJECT_DIR/.env"
PID_FILE="$PROJECT_DIR/.app.pid"
LOG_DIR="$PROJECT_DIR/logs"

# 打印带颜色的消息
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 打印横幅
print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║           运维管理平台 - Ops Management Platform          ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 未安装，请先安装 $1"
        return 1
    fi
    print_success "$1 已安装: $(command -v $1)"
    return 0
}

# 检查Python版本
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        print_error "Python 未安装，请先安装 Python 3.8+"
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    print_success "Python 版本: $PYTHON_VERSION"
}

# 检查Node.js
check_nodejs() {
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_success "Node.js 版本: $NODE_VERSION"
        return 0
    else
        print_warning "Node.js 未安装，跳过前端构建"
        return 1
    fi
}

# 检查数据库连接
check_database() {
    print_info "检查数据库连接..."
    
    # 从环境变量或.env文件读取数据库配置
    if [ -f "$ENV_FILE" ]; then
        export $(grep -v '^#' $ENV_FILE | xargs)
    fi
    
    # 检查是否有数据库URL
    if [ -n "$DATABASE_URL" ] || [ -n "$PGDATABASE_URL" ] || [ -n "$MYSQL_HOST" ]; then
        print_success "数据库配置已设置"
        return 0
    fi
    
    # 使用默认PostgreSQL
    if command -v psql &> /dev/null; then
        if psql -h localhost -U postgres -c '\q' 2>/dev/null; then
            print_success "PostgreSQL 连接成功"
            return 0
        fi
    fi
    
    # 使用默认MySQL
    if command -v mysql &> /dev/null; then
        if mysql -u root -e "SELECT 1" &>/dev/null; then
            print_success "MySQL 连接成功"
            return 0
        fi
    fi
    
    print_warning "无法验证数据库连接，请确保数据库服务已启动"
    return 0
}

# 安装Python依赖
install_python_deps() {
    print_info "安装Python依赖..."
    
    if [ -f "$PROJECT_DIR/backend/requirements.txt" ]; then
        $PYTHON_CMD -m pip install -r $PROJECT_DIR/backend/requirements.txt -q
        print_success "Python依赖安装完成"
    else
        print_error "未找到 requirements.txt"
        exit 1
    fi
}

# 构建前端（如果需要）
build_frontend() {
    print_info "检查前端构建..."
    
    if [ -d "$PROJECT_DIR/frontend/dist" ]; then
        print_success "前端已构建，跳过"
        return 0
    fi
    
    if ! command -v node &> /dev/null; then
        print_warning "Node.js未安装，跳过前端构建"
        return 0
    fi
    
    print_info "构建前端..."
    cd $PROJECT_DIR/frontend
    
    if [ -f "pnpm-lock.yaml" ] && command -v pnpm &> /dev/null; then
        pnpm install
        pnpm build
    elif [ -f "package-lock.json" ]; then
        npm install
        npm run build
    elif [ -f "yarn.lock" ]; then
        yarn instal
        yarn build
    fi
    
    cd $PROJECT_DIR
    print_success "前端构建完成"
}

# 创建必要的目录
create_dirs() {
    mkdir -p $LOG_DIR
    print_success "创建日志目录: $LOG_DIR"
}

# 创建环境配置文件
create_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        print_info "创建默认环境配置..."
        cat > $ENV_FILE << 'EOF'
# 数据库配置 (PostgreSQL 示例)
# DATABASE_URL=postgresql://postgres:password@localhost:5432/ops_platform

# 数据库配置 (MySQL 示例)  
# MYSQL_HOST=localhost
# MYSQL_PORT=3306
# MYSQL_USER=root
# MYSQL_PASSWORD=password
# MYSQL_DATABASE=ops_platform

# Redis配置 (可选)
# REDIS_HOST=localhost
# REDIS_PORT=6379
# REDIS_PASSWORD=

# JWT密钥 (请修改为随机字符串)
JWT_SECRET_KEY=your-super-secret-key-please-change-this

# 服务端口
PORT=5000
EOF
        print_success "已创建 .env 配置文件，请根据需要修改"
    fi
}

# 启动服务
start_service() {
    print_info "启动服务..."
    
    # 检查是否已运行
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null 2>&1; then
            print_warning "服务已在运行中 (PID: $PID)"
            return 0
        fi
        rm -f $PID_FILE
    fi
    
    # 创建日志目录
    create_dirs
    
    # 启动后端服务
    cd $PROJECT_DIR/backend
    nohup $PYTHON_CMD -m uvicorn app.main:app --host 0.0.0.0 --port 5000 > $LOG_DIR/app.log 2>&1 &
    echo $! > $PID_FILE
    
    cd $PROJECT_DIR
    
    # 等待服务启动
    sleep 3
    
    # 检查服务是否启动成功
    if curl -s http://localhost:5000/api/init/status > /dev/null 2>&1; then
        print_success "服务启动成功！"
        echo ""
        print_info "访问地址: http://localhost:5000"
        print_info "默认账号: admin / admin123"
        echo ""
        print_info "日志文件: $LOG_DIR/app.log"
        print_info "停止服务: ./start.sh stop"
    else
        print_error "服务启动失败，请检查日志: $LOG_DIR/app.log"
        exit 1
    fi
}

# 停止服务
stop_service() {
    print_info "停止服务..."
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null 2>&1; then
            kill $PID
            sleep 2
            if ps -p $PID > /dev/null 2>&1; then
                kill -9 $PID
            fi
            print_success "服务已停止"
        else
            print_warning "服务未运行"
        fi
        rm -f $PID_FILE
    else
        print_warning "未找到PID文件，尝试查找并停止服务..."
        pkill -f "uvicorn app.main:app" 2>/dev/null || true
        print_success "服务已停止"
    fi
}

# 重启服务
restart_service() {
    stop_service
    sleep 2
    start_service
}

# 查看状态
show_status() {
    echo ""
    print_info "服务状态:"
    
    # 检查端口是否被监听
    PORT_STATUS=""
    if command -v ss &> /dev/null; then
        PORT_STATUS=$(ss -tlnp 2>/dev/null | grep ":5000 " | grep LISTEN)
    elif command -v netstat &> /dev/null; then
        PORT_STATUS=$(netstat -tlnp 2>/dev/null | grep ":5000 " | grep LISTEN)
    fi
    
    if [ -n "$PORT_STATUS" ]; then
        # 从端口信息提取PID
        LISTEN_PID=$(echo "$PORT_STATUS" | grep -oP 'pid=\K[0-9]+' | head -1)
        if [ -n "$LISTEN_PID" ]; then
            print_success "服务运行中 (PID: $LISTEN_PID)"
        else
            print_success "服务运行中"
        fi
        
        # 检查API响应
        if curl -s http://localhost:5000/api/init/status > /dev/null 2>&1; then
            print_success "API 响应正常"
        else
            print_warning "API 无响应"
        fi
    elif [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null 2>&1; then
            print_success "服务运行中 (PID: $PID)"
        else
            print_warning "服务未运行 (PID文件过期)"
            rm -f $PID_FILE
        fi
    else
        print_warning "服务未运行"
    fi
    
    echo ""
    print_info "端口状态:"
    if [ -n "$PORT_STATUS" ]; then
        echo "$PORT_STATUS"
    else
        print_warning "端口 5000 未被监听"
    fi
}

# 查看日志
show_logs() {
    if [ -f "$LOG_DIR/app.log" ]; then
        tail -f $LOG_DIR/app.log
    else
        print_error "日志文件不存在: $LOG_DIR/app.log"
    fi
}

# 初始化数据库
init_database() {
    print_info "初始化数据库..."
    cd $PROJECT_DIR/backend
    $PYTHON_CMD -c "
from app.database import engine, Base
from app.models import *
Base.metadata.create_all(bind=engine)
print('数据库表创建完成')
"
    cd $PROJECT_DIR
    print_success "数据库初始化完成"
}

# 完整安装
full_install() {
    print_banner
    
    print_info "=== 环境检查 ==="
    check_python
    check_nodejs
    
    print_info "=== 安装依赖 ==="
    install_python_deps
    
    print_info "=== 配置检查 ==="
    create_env_file
    create_dirs
    
    print_info "=== 构建前端 ==="
    build_frontend
    
    print_info "=== 数据库检查 ==="
    check_database
    
    print_info "=== 启动服务 ==="
    start_service
    
    print_success "=== 安装完成 ==="
}

# 显示帮助
show_help() {
    print_banner
    echo "用法: ./start.sh [命令]"
    echo ""
    echo "命令:"
    echo "  start       启动服务 (默认)"
    echo "  stop        停止服务"
    echo "  restart     重启服务"
    echo "  status      查看服务状态"
    echo "  logs        查看实时日志"
    echo "  install     安装依赖"
    echo "  build       构建前端"
    echo "  init        初始化数据库"
    echo "  all         完整安装并启动"
    echo "  help        显示帮助信息"
    echo ""
    echo "示例:"
    echo "  ./start.sh              # 启动服务"
    echo "  ./start.sh all          # 完整安装并启动"
    echo "  ./start.sh logs         # 查看日志"
}

# 主入口
case "${1:-start}" in
    start)
        print_banner
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        print_banner
        show_status
        ;;
    logs)
        show_logs
        ;;
    install)
        print_banner
        install_python_deps
        ;;
    build)
        print_banner
        build_frontend
        ;;
    init)
        init_database
        ;;
    all)
        full_install
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "未知命令: $1"
        show_help
        exit 1
        ;;
esac
