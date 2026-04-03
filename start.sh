#!/bin/bash

# OpsCenter - 运维管理平台启动脚本
# 支持：开发模式、生产模式、前端构建、依赖安装

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目目录
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$PROJECT_DIR/frontend"
BACKEND_DIR="$PROJECT_DIR/backend"

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
OpsCenter 运维管理平台启动脚本

用法: $0 [命令] [选项]

命令:
    dev         启动开发模式（前后端热重载）
    start       启动生产模式（构建后的前端 + 后端）
    build       构建前端项目
    install     安装所有依赖（前端 + 后端）
    restart     重启服务
    help        显示此帮助信息

选项:
    --build     启动前强制重新构建前端（仅对 dev/start 有效）
    --skip-build 启动时跳过前端构建（仅对 start 有效）

示例:
    $0 dev                    # 开发模式启动
    $0 dev --build           # 重新构建前端后开发模式启动
    $0 start                 # 生产模式启动
    $0 start --build         # 重新构建前端后生产模式启动
    $0 build                 # 仅构建前端
    $0 install               # 安装所有依赖
    $0 restart               # 重启服务

EOF
}

# 安装后端依赖
install_backend_deps() {
    print_info "安装后端依赖..."
    cd "$BACKEND_DIR"
    if [ -f "requirements.txt" ]; then
        python -m pip install -r requirements.txt -q
        print_success "后端依赖安装完成"
    else
        print_warning "未找到 requirements.txt"
    fi
}

# 安装前端依赖
install_frontend_deps() {
    print_info "安装前端依赖..."
    cd "$FRONTEND_DIR"
    if [ -f "package.json" ]; then
        pnpm install
        print_success "前端依赖安装完成"
    else
        print_warning "未找到 package.json"
    fi
}

# 安装所有依赖
install_deps() {
    print_info "开始安装所有依赖..."
    install_backend_deps
    install_frontend_deps
    print_success "所有依赖安装完成"
}

# 构建前端
build_frontend() {
    print_info "开始构建前端..."
    cd "$FRONTEND_DIR"

    # 检查 node_modules 是否存在
    if [ ! -d "node_modules" ]; then
        print_warning "未找到 node_modules，先安装依赖..."
        pnpm install
    fi

    # 执行构建
    print_info "执行 pnpm build..."
    pnpm build

    # 检查构建结果
    if [ -d "dist" ] && [ -f "dist/index.html" ]; then
        print_success "前端构建成功: $FRONTEND_DIR/dist"
    else
        print_error "前端构建失败，未找到 dist/index.html"
        exit 1
    fi
}

# 启动后端服务（开发模式）
start_backend_dev() {
    print_info "启动后端服务（开发模式）..."
    cd "$BACKEND_DIR"
    python -m uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload &
    BACKEND_PID=$!
    print_success "后端服务已启动 (PID: $BACKEND_PID)"
    echo $BACKEND_PID > "$PROJECT_DIR/.backend.pid"
}

# 启动后端服务（生产模式）
start_backend_prod() {
    print_info "启动后端服务（生产模式）..."
    cd "$BACKEND_DIR"
    python -m uvicorn app.main:app --host 0.0.0.0 --port 5000 &
    BACKEND_PID=$!
    print_success "后端服务已启动 (PID: $BACKEND_PID)"
    echo $BACKEND_PID > "$PROJECT_DIR/.backend.pid"
}

# 停止服务
stop_services() {
    if [ -f "$PROJECT_DIR/.backend.pid" ]; then
        PID=$(cat "$PROJECT_DIR/.backend.pid")
        if ps -p "$PID" > /dev/null 2>&1; then
            print_info "停止后端服务 (PID: $PID)..."
            kill "$PID" 2>/dev/null || true
            rm -f "$PROJECT_DIR/.backend.pid"
            print_success "后端服务已停止"
        fi
    fi
}

# 开发模式
cmd_dev() {
    print_info "启动开发模式..."

    local should_build=false

    # 解析参数
    for arg in "$@"; do
        case $arg in
            --build)
                should_build=true
                ;;
        esac
    done

    # 安装依赖（如果不存在）
    if [ ! -d "$BACKEND_DIR/venv" ] && [ ! -d "$BACKEND_DIR/__pycache__" ]; then
        install_backend_deps
    fi

    # 构建前端（如果需要）
    if [ "$should_build" = true ]; then
        build_frontend
    fi

    # 启动后端（开发模式带热重载）
    stop_services
    start_backend_dev

    print_success "开发模式已启动"
    print_info "后端服务: http://localhost:5000"
    print_info "前端静态文件由后端提供"
    print_info "按 Ctrl+C 停止服务"

    # 等待中断信号
    wait
}

# 生产模式
cmd_start() {
    print_info "启动生产模式..."

    local should_build=true
    local skip_build=false

    # 解析参数
    for arg in "$@"; do
        case $arg in
            --build)
                should_build=true
                ;;
            --skip-build)
                skip_build=true
                ;;
        esac
    done

    # 检查是否跳过构建
    if [ "$skip_build" = true ]; then
        should_build=false
        print_info "跳过前端构建"
    fi

    # 检查前端构建产物
    if [ "$should_build" = true ]; then
        build_frontend
    else
        if [ ! -d "$FRONTEND_DIR/dist" ]; then
            print_warning "未找到前端构建产物，执行构建..."
            build_frontend
        else
            print_info "使用已存在的前端构建产物"
        fi
    fi

    # 停止已存在的服务
    stop_services

    # 启动后端（生产模式）
    start_backend_prod

    print_success "生产模式已启动"
    print_info "访问地址: http://localhost:5000"
    print_info "日志文件: /app/work/logs/bypass/app.log"

    # 等待中断信号
    wait
}

# 重启服务
cmd_restart() {
    print_info "重启服务..."
    stop_services
    sleep 1

    # 检查是否有构建产物
    if [ -d "$FRONTEND_DIR/dist" ]; then
        start_backend_prod
    else
        print_warning "未找到前端构建产物，请先执行: $0 build"
        exit 1
    fi

    print_success "服务已重启"
}

# 主函数
main() {
    cd "$PROJECT_DIR"

    case "${1:-help}" in
        dev)
            shift
            cmd_dev "$@"
            ;;
        start)
            shift
            cmd_start "$@"
            ;;
        build)
            build_frontend
            ;;
        install)
            install_deps
            ;;
        restart)
            cmd_restart
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
}

# 捕获退出信号
trap stop_services EXIT

# 执行主函数
main "$@"
