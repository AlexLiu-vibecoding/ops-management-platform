#!/bin/bash
# ============================================================
# OpsCenter - 运维管理平台统一管理脚本
# ============================================================
#
# 功能：
#   服务管理：dev, start, stop, restart, logs
#   构建与依赖：build, install
#   部署管理：check, deploy, reload, rollback
#   信息查询：status, history, help
#
# 用法：
#   ./ops.sh dev                    # 开发模式启动
#   ./ops.sh start                  # 生产模式启动
#   ./ops.sh stop                   # 停止服务
#   ./ops.sh restart                # 重启服务
#   ./ops.sh logs                   # 查看日志
#   ./ops.sh build                  # 构建前端
#   ./ops.sh install                # 安装依赖
#   ./ops.sh deploy                 # 部署（生产环境）
#   ./ops.sh check                  # 检查更新
#   ./ops.sh reload [--hard]        # 重载服务
#   ./ops.sh rollback [version]     # 回滚版本
#   ./ops.sh status                 # 查看状态
#   ./ops.sh history                # 查看历史
#
# ============================================================

set -e

# ==================== 全局配置 ====================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 项目目录
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
DEPLOY_DIR="$PROJECT_DIR/deploy"
RELEASES_DIR="$PROJECT_DIR/releases"
LOG_DIR="$PROJECT_DIR/logs"
STATE_FILE="$PROJECT_DIR/.deploy.json"
PID_FILE="$PROJECT_DIR/.app.pid"

# 版本备份保留数量
KEEP_VERSIONS=5

# ==================== 工具函数 ====================

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║           OpsCenter - 运维管理平台                          ║"
    echo "║           统一管理脚本                                      ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_step() { echo -e "${CYAN}[STEP]${NC} $1"; }

# ==================== 环境检测 ====================

detect_environment() {
    local env_arg=""
    
    for arg in "$@"; do
        case $arg in
            --env=*) env_arg="${arg#*=}" ;;
        esac
    done
    
    # 优先使用参数指定的环境
    if [ -n "$env_arg" ]; then
        DEPLOY_ENV="$env_arg"
    # 根据分支判断
    elif [ "$(git rev-parse --abbrev-ref HEAD 2>/dev/null)" = "main" ] || \
         [ "$(git rev-parse --abbrev-ref HEAD 2>/dev/null)" = "master" ]; then
        DEPLOY_ENV="prod"
    else
        DEPLOY_ENV="dev"
    fi
    
    # 加载环境配置
    local env_file="$PROJECT_DIR/.env.$DEPLOY_ENV"
    if [ -f "$env_file" ]; then
        print_info "加载环境配置: $env_file"
        set -a
        source "$env_file"
        set +a
    fi
}

check_dependencies() {
    print_step "检查依赖..."
    
    local errors=0
    
    # 检查 Python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        print_success "Python: $(python3 --version 2>&1 | awk '{print $2}')"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
        print_success "Python: $(python --version 2>&1 | awk '{print $2}')"
    else
        print_error "Python 未安装"
        ((errors++))
    fi
    
    # 检查 Node.js
    if command -v node &> /dev/null; then
        print_success "Node.js: $(node --version)"
    else
        print_warning "Node.js 未安装，将跳过前端构建"
        SKIP_FRONTEND=true
    fi
    
    # 检查 pnpm
    if command -v pnpm &> /dev/null; then
        print_success "pnpm: $(pnpm --version)"
    elif [ -z "$SKIP_FRONTEND" ]; then
        print_warning "pnpm 未安装，尝试使用 npm"
    fi
    
    if [ $errors -gt 0 ]; then
        print_error "依赖检查失败"
        return 1
    fi
    
    print_success "依赖检查通过"
    return 0
}

# ==================== 服务管理 ====================

get_service_pid() {
    # 优先从 PID 文件获取
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p $pid > /dev/null 2>&1; then
            echo $pid
            return 0
        fi
    fi
    
    # 从端口获取
    local pid=$(ss -lptn 'sport = :5000' 2>/dev/null | grep -oP 'pid=\K[0-9]+' | head -1)
    if [ -n "$pid" ] && ps -p $pid > /dev/null 2>&1; then
        echo $pid
        return 0
    fi
    
    return 1
}

is_service_running() {
    local pid=$(get_service_pid)
    [ -n "$pid" ]
}

stop_service() {
    print_info "停止服务..."
    
    local pid=$(get_service_pid)
    
    if [ -z "$pid" ]; then
        print_info "服务未运行"
        rm -f "$PID_FILE"
        return 0
    fi
    
    # 优雅停止
    kill $pid 2>/dev/null || true
    
    # 等待最多 10 秒
    local wait=0
    while ps -p $pid > /dev/null 2>&1 && [ $wait -lt 10 ]; do
        sleep 1
        wait=$((wait + 1))
    done
    
    # 强制停止
    if ps -p $pid > /dev/null 2>&1; then
        print_warning "强制停止..."
        kill -9 $pid 2>/dev/null || true
        sleep 1
    fi
    
    rm -f "$PID_FILE"
    print_success "服务已停止"
}

start_backend() {
    local mode=$1  # dev 或 prod
    
    print_step "启动后端服务 ($mode 模式)..."
    
    # 检查是否已运行
    if is_service_running; then
        print_warning "服务已在运行中 (PID: $(get_service_pid))"
        return 0
    fi
    
    cd "$BACKEND_DIR"
    
    # 根据模式选择启动方式
    local reload_flag=""
    if [ "$mode" = "dev" ]; then
        reload_flag="--reload"
    fi
    
    # 创建日志目录
    mkdir -p "$LOG_DIR"
    
    if [ "$mode" = "dev" ]; then
        # 开发模式：前台运行
        $PYTHON_CMD -m uvicorn app.main:app --host 0.0.0.0 --port 5000 $reload_flag
    else
        # 生产模式：后台运行
        nohup $PYTHON_CMD -m uvicorn app.main:app --host 0.0.0.0 --port 5000 $reload_flag \
            > "$LOG_DIR/app.log" 2>&1 &
        local new_pid=$!
        echo $new_pid > "$PID_FILE"
        
        sleep 2
        
        if ps -p $new_pid > /dev/null 2>&1; then
            print_success "服务启动成功 (PID: $new_pid)"
            print_info "访问地址: http://localhost:5000"
            print_info "日志文件: $LOG_DIR/app.log"
        else
            print_error "服务启动失败"
            return 1
        fi
    fi
    
    cd "$PROJECT_DIR"
}

restart_service() {
    local mode=$1
    
    print_info "重启服务 ($mode 模式)..."
    stop_service
    sleep 1
    start_backend "$mode"
}

# ==================== 构建与依赖 ====================

install_dependencies() {
    print_step "安装依赖..."
    
    # 后端依赖
    print_info "安装后端依赖..."
    cd "$BACKEND_DIR"
    $PYTHON_CMD -m pip install -r requirements.txt -q
    cd "$PROJECT_DIR"
    
    # 前端依赖
    if [ -z "$SKIP_FRONTEND" ]; then
        print_info "安装前端依赖..."
        cd "$FRONTEND_DIR"
        if command -v pnpm &> /dev/null; then
            pnpm install
        else
            npm install
        fi
        cd "$PROJECT_DIR"
    fi
    
    print_success "依赖安装完成"
}

build_frontend() {
    print_step "构建前端..."
    
    if [ -n "$SKIP_FRONTEND" ]; then
        print_warning "跳过前端构建"
        return 0
    fi
    
    cd "$FRONTEND_DIR"
    
    # 检查 node_modules
    if [ ! -d "node_modules" ]; then
        print_info "未找到 node_modules，先安装依赖..."
        if command -v pnpm &> /dev/null; then
            pnpm install
        else
            npm install
        fi
    fi
    
    # 执行构建
    if command -v pnpm &> /dev/null; then
        pnpm build
    else
        npm run build
    fi
    
    # 检查构建结果
    if [ -d "dist" ] && [ -f "dist/index.html" ]; then
        print_success "前端构建成功: $FRONTEND_DIR/dist"
    else
        print_error "前端构建失败"
        exit 1
    fi
    
    cd "$PROJECT_DIR"
}

# ==================== Git 操作 ====================

check_git_update() {
    print_step "检测 Git 更新..."
    
    local current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    
    git fetch origin --quiet 2>/dev/null || true
    
    local local_commit=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    local remote_commit=$(git rev-parse "origin/$current_branch" 2>/dev/null || echo "unknown")
    
    if [ "$local_commit" = "$remote_commit" ]; then
        print_success "代码已是最新版本"
        return 0
    else
        print_info "检测到新版本"
        git log --oneline "$local_commit..$remote_commit" 2>/dev/null | head -5
        return 1
    fi
}

# ==================== 部署相关 ====================

backup_current_version() {
    print_step "备份当前版本..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local current_version=$(git describe --tags --always 2>/dev/null || echo "unknown")
    local version_name="${current_version}_${timestamp}"
    local backup_dir="$RELEASES_DIR/$version_name"
    
    mkdir -p "$backup_dir"
    
    # 记录信息
    git rev-parse HEAD > "$backup_dir/git_commit" 2>/dev/null || true
    echo "$current_version" > "$backup_dir/version"
    echo "$timestamp" > "$backup_dir/timestamp"
    
    # 备份前端
    if [ -d "$FRONTEND_DIR/dist" ]; then
        cp -r "$FRONTEND_DIR/dist" "$backup_dir/"
    fi
    
    # 更新软链接
    ln -sfn "$backup_dir" "$RELEASES_DIR/current"
    
    print_success "备份完成: $backup_dir"
    echo "$backup_dir" > /tmp/last_backup.txt
}

run_migration() {
    print_step "执行数据库迁移..."
    
    cd "$BACKEND_DIR"
    
    if [ -d "alembic" ] && [ -f "alembic.ini" ]; then
        alembic upgrade head
        print_success "数据库迁移完成"
    else
        print_warning "未找到 Alembic 配置，跳过迁移"
    fi
    
    cd "$PROJECT_DIR"
}

# ==================== 信息查询 ====================

show_status() {
    print_banner
    
    echo -e "${CYAN}=== 服务状态 ===${NC}"
    
    if is_service_running; then
        local pid=$(get_service_pid)
        print_success "服务运行中 (PID: $pid)"
        
        if curl -sf http://localhost:5000/api/v1/init/status > /dev/null 2>&1; then
            print_success "API 响应正常"
        else
            print_warning "API 无响应"
        fi
    else
        print_warning "服务未运行"
    fi
    
    echo ""
    echo -e "${CYAN}=== Git 状态 ===${NC}"
    print_info "当前分支: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
    print_info "当前版本: $(git describe --tags --always 2>/dev/null || echo 'unknown')"
    print_info "当前提交: $(git rev-parse HEAD 2>/dev/null | cut -c1-8 || echo 'unknown')"
    
    echo ""
    echo -e "${CYAN}=== 版本备份 ===${NC}"
    local backup_count=$(ls -d "$RELEASES_DIR"/*/ 2>/dev/null | grep -v current | wc -l)
    print_info "备份数量: $backup_count"
}

show_history() {
    print_banner
    
    echo -e "${CYAN}=== 部署历史 ===${NC}"
    
    if [ -f "$STATE_FILE" ]; then
        python3 -c "
import json
try:
    with open('$STATE_FILE') as f:
        state = json.load(f)
        for i, record in enumerate(state.get('deploy_history', [])[:10]):
            status_color = '✓' if record['status'] == 'success' else '✗'
            print(f\"{i+1}. {record['timestamp'][:19]} [{status_color}] {record['version']} ({record['env']})\")
except:
    pass
" 2>/dev/null || print_info "暂无部署历史"
    else
        print_info "暂无部署历史"
    fi
    
    echo ""
    echo -e "${CYAN}=== 版本备份 ===${NC}"
    
    ls -dt "$RELEASES_DIR"/*/ 2>/dev/null | grep -v current | head -10 | while read dir; do
        local name=$(basename "$dir")
        local commit=$(cat "$dir/git_commit" 2>/dev/null | cut -c1-8 || echo "unknown")
        local time=$(cat "$dir/timestamp" 2>/dev/null || echo "unknown")
        echo "  - $name (提交: $commit, 时间: $time)"
    done
}

# ==================== 命令处理 ====================

cmd_dev() {
    print_banner
    detect_environment "$@"
    check_dependencies || exit 1
    
    # 开发模式：前台运行
    stop_service 2>/dev/null || true
    start_backend "dev"
}

cmd_start() {
    print_banner
    detect_environment "$@"
    
    local force_build=false
    
    for arg in "$@"; do
        case $arg in
            --build|-b) force_build=true ;;
        esac
    done
    
    check_dependencies || exit 1
    
    # 检查前端构建产物
    if [ "$force_build" = true ] || [ ! -d "$FRONTEND_DIR/dist" ]; then
        build_frontend
    fi
    
    stop_service 2>/dev/null || true
    start_backend "prod"
}

cmd_stop() {
    stop_service
}

cmd_restart() {
    local mode="prod"
    
    for arg in "$@"; do
        case $arg in
            --dev|-d) mode="dev" ;;
        esac
    done
    
    print_banner
    detect_environment "$@"
    restart_service "$mode"
}

cmd_logs() {
    if [ -f "$LOG_DIR/app.log" ]; then
        tail -f "$LOG_DIR/app.log"
    else
        print_error "日志文件不存在: $LOG_DIR/app.log"
        exit 1
    fi
}

cmd_build() {
    print_banner
    check_dependencies
    build_frontend
}

cmd_install() {
    print_banner
    check_dependencies
    install_dependencies
}

cmd_check() {
    print_banner
    detect_environment "$@"
    check_dependencies || exit 1
    check_git_update
}

cmd_deploy() {
    print_banner
    detect_environment "$@"
    
    local force=false
    
    for arg in "$@"; do
        case $arg in
            --force|-f) force=true ;;
        esac
    done
    
    check_dependencies || exit 1
    
    # 检查更新
    check_git_update
    local update_status=$?
    
    if [ $update_status -eq 0 ] && [ "$force" = false ]; then
        print_info "无更新，使用 --force 强制重新部署"
        exit 0
    fi
    
    # 备份
    backup_current_version
    
    # 拉取代码
    if [ $update_status -eq 1 ]; then
        print_step "拉取最新代码..."
        git pull origin "$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
    fi
    
    # 更新依赖
    install_dependencies
    
    # 数据库迁移
    run_migration
    
    # 构建前端
    build_frontend
    
    # 重启服务
    stop_service 2>/dev/null || true
    start_backend "prod"
    
    # 健康检查
    print_step "健康检查..."
    local retry=0
    while [ $retry -lt 30 ]; do
        if curl -sf http://localhost:5000/api/v1/init/status > /dev/null 2>&1; then
            print_success "部署完成"
            print_info "访问地址: http://localhost:5000"
            return 0
        fi
        retry=$((retry + 1))
        echo -n "."
        sleep 1
    done
    
    echo ""
    print_error "健康检查失败"
    return 1
}

cmd_reload() {
    local mode="graceful"
    
    for arg in "$@"; do
        case $arg in
            --hard|-h) mode="hard" ;;
        esac
    done
    
    print_banner
    detect_environment "$@"
    
    if [ "$mode" = "graceful" ] && is_service_running; then
        local pid=$(get_service_pid)
        print_info "发送 HUP 信号..."
        kill -HUP $pid 2>/dev/null || true
        sleep 2
    else
        restart_service "prod"
    fi
    
    print_success "服务重载完成"
}

cmd_rollback() {
    local target_version=$1
    
    print_banner
    
    if [ -z "$target_version" ]; then
        # 显示可用版本
        echo -e "${CYAN}可回滚版本:${NC}"
        ls -dt "$RELEASES_DIR"/*/ 2>/dev/null | grep -v current | head -5 | while read dir; do
            local name=$(basename "$dir")
            local time=$(cat "$dir/timestamp" 2>/dev/null || echo "unknown")
            echo "  - $name (备份时间: $time)"
        done
        echo ""
        print_info "用法: ./ops.sh rollback <version>"
        exit 0
    fi
    
    # 查找备份目录
    local backup_dir=$(ls -dt "$RELEASES_DIR/${target_version}"* 2>/dev/null | head -1)
    
    if [ -z "$backup_dir" ]; then
        print_error "未找到版本: $target_version"
        exit 1
    fi
    
    # 恢复 Git 状态
    if [ -f "$backup_dir/git_commit" ]; then
        print_info "恢复 Git 状态..."
        git checkout "$(cat "$backup_dir/git_commit")" 2>/dev/null || print_warning "Git checkout 失败"
    fi
    
    # 恢复前端
    if [ -d "$backup_dir/dist" ]; then
        print_info "恢复前端构建产物..."
        rm -rf "$FRONTEND_DIR/dist"
        cp -r "$backup_dir/dist" "$FRONTEND_DIR/"
    fi
    
    # 重启服务
    stop_service 2>/dev/null || true
    start_backend "prod"
    
    print_success "回滚完成"
}

show_help() {
    cat << EOF
${CYAN}
╔═══════════════════════════════════════════════════════════╗
║           OpsCenter - 运维管理平台                          ║
║           统一管理脚本                                      ║
╚═══════════════════════════════════════════════════════════╝
${NC}

用法: ./ops.sh <命令> [选项]

${CYAN}服务管理:${NC}
  dev              启动开发模式（热重载）
  start            启动生产模式
  stop             停止服务
  restart          重启服务 [--dev]
  logs             查看日志

${CYAN}构建与依赖:${NC}
  build            构建前端
  install          安装所有依赖

${CYAN}部署管理:${NC}
  check            检查更新
  deploy           部署 [--force]
  reload           重载服务 [--hard]
  rollback         回滚版本 [version]

${CYAN}信息查询:${NC}
  status           查看服务状态
  history          查看部署历史
  help             显示此帮助信息

${CYAN}示例:${NC}
  ./ops.sh dev                    # 开发模式启动
  ./ops.sh start                  # 生产模式启动
  ./ops.sh start --build          # 重新构建后启动
  ./ops.sh stop                   # 停止服务
  ./ops.sh restart                # 重启服务
  ./ops.sh logs                   # 查看日志
  ./ops.sh deploy                 # 部署
  ./ops.sh deploy --force         # 强制重新部署
  ./ops.sh rollback               # 查看可回滚版本
  ./ops.sh rollback v1.0.0_20240101_120000  # 回滚到指定版本

EOF
}

# ==================== 主入口 ====================

main() {
    cd "$PROJECT_DIR"
    
    case "${1:-help}" in
        dev)
            cmd_dev "${@:2}"
            ;;
        start)
            cmd_start "${@:2}"
            ;;
        stop)
            cmd_stop
            ;;
        restart)
            cmd_restart "${@:2}"
            ;;
        logs)
            cmd_logs
            ;;
        build)
            cmd_build
            ;;
        install)
            cmd_install
            ;;
        check)
            cmd_check "${@:2}"
            ;;
        deploy)
            cmd_deploy "${@:2}"
            ;;
        reload)
            cmd_reload "${@:2}"
            ;;
        rollback)
            cmd_rollback "${@:2}"
            ;;
        status)
            show_status
            ;;
        history)
            show_history
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

# 执行主函数
main "$@"
