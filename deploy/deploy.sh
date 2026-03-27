#!/bin/bash
# ============================================================
# 运维管理平台 - 部署脚本
# ============================================================
#
# 功能：
# - 自动检测 Git 更新
# - 数据库迁移（Alembic）
# - 前端构建
# - 版本备份与回滚
# - 健康检查
#
# 用法：
#   ./deploy.sh check              # 检查更新
#   ./deploy.sh deploy [--env=dev|prod]  # 部署
#   ./deploy.sh rollback [version] # 回滚
#   ./deploy.sh status             # 查看状态
#   ./deploy.sh history            # 查看历史
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

# 项目根目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# 目录配置
DEPLOY_DIR="$PROJECT_DIR/deploy"
RELEASES_DIR="$PROJECT_DIR/releases"
LOG_DIR="$PROJECT_DIR/logs"
STATE_FILE="$PROJECT_DIR/.deploy.json"
PID_FILE="$PROJECT_DIR/.app.pid"

# 版本备份保留数量
KEEP_VERSIONS=5

# 当前 Git 信息
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
CURRENT_VERSION=$(git describe --tags --always 2>/dev/null || echo "dev")

# ==================== 工具函数 ====================

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║           运维管理平台 - 部署管理系统                      ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_step() { echo -e "${CYAN}[STEP]${NC} $1"; }

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 未安装"
        return 1
    fi
    return 0
}

# ==================== 环境检测 ====================

detect_environment() {
    local env_arg=""
    
    # 解析命令行参数
    for arg in "$@"; do
        case $arg in
            --env=*)
                env_arg="${arg#*=}"
                ;;
            --env)
                # 下一个参数是环境值
                ;;
        esac
    done
    
    # 优先使用参数指定的环境
    if [ -n "$env_arg" ]; then
        DEPLOY_ENV="$env_arg"
    # 根据分支判断环境
    elif [ "$CURRENT_BRANCH" = "master" ] || [ "$CURRENT_BRANCH" = "main" ]; then
        DEPLOY_ENV="prod"
    else
        DEPLOY_ENV="dev"
    fi
    
    # 加载环境配置文件
    local env_file="$PROJECT_DIR/.env.$DEPLOY_ENV"
    if [ -f "$env_file" ]; then
        print_info "加载环境配置: $env_file"
        set -a
        source "$env_file"
        set +a
    fi
    
    print_info "部署环境: ${GREEN}$DEPLOY_ENV${NC} (分支: $CURRENT_BRANCH)"
}

check_environment() {
    print_step "检查运行环境..."
    
    local errors=0
    
    # 检查 Python
    if check_command python3; then
        PYTHON_CMD="python3"
        PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
        print_success "Python: $PYTHON_VERSION"
    elif check_command python; then
        PYTHON_CMD="python"
        PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
        print_success "Python: $PYTHON_VERSION"
    else
        print_error "Python 未安装"
        ((errors++))
    fi
    
    # 检查 Node.js
    if check_command node; then
        NODE_VERSION=$(node --version)
        print_success "Node.js: $NODE_VERSION"
    else
        print_warning "Node.js 未安装，将跳过前端构建"
        SKIP_FRONTEND=true
    fi
    
    # 检查 pnpm
    if check_command pnpm; then
        PNPM_VERSION=$(pnpm --version)
        print_success "pnpm: $PNPM_VERSION"
    elif [ -z "$SKIP_FRONTEND" ]; then
        print_warning "pnpm 未安装，尝试使用 npm"
    fi
    
    # 检查 Git
    if check_command git; then
        GIT_VERSION=$(git --version | awk '{print $3}')
        print_success "Git: $GIT_VERSION"
    else
        print_error "Git 未安装"
        ((errors++))
    fi
    
    if [ $errors -gt 0 ]; then
        print_error "环境检查失败，请安装缺失的依赖"
        return 1
    fi
    
    print_success "环境检查通过"
    return 0
}

# ==================== Git 操作 ====================

check_git_update() {
    print_step "检测 Git 更新..."
    
    # 获取远程分支名
    local remote_branch="origin/$CURRENT_BRANCH"
    
    # 拉取远程信息
    git fetch origin --quiet 2>/dev/null
    
    # 获取本地和远程 commit
    local local_commit=$(git rev-parse HEAD)
    local remote_commit=$(git rev-parse $remote_branch 2>/dev/null)
    
    if [ -z "$remote_commit" ]; then
        print_warning "无法获取远程分支信息"
        return 2
    fi
    
    if [ "$local_commit" = "$remote_commit" ]; then
        print_success "代码已是最新版本"
        print_info "当前版本: $CURRENT_VERSION ($local_commit)"
        return 0
    else
        # 获取变更信息
        local changes=$(git log --oneline $local_commit..$remote_commit 2>/dev/null)
        local changes_count=$(echo "$changes" | grep -c '^' || echo 0)
        
        print_info "检测到新版本 (${YELLOW}$changes_count${NC} 个提交):"
        echo "$changes" | head -5
        if [ $changes_count -gt 5 ]; then
            print_info "... 还有 $((changes_count - 5)) 个提交"
        fi
        
        return 1
    fi
}

pull_latest_code() {
    print_step "拉取最新代码..."
    
    # 暂存本地修改
    if [ -n "$(git status --porcelain)" ]; then
        print_info "暂存本地修改..."
        git stash push -m "auto stash before deploy at $(date +%Y%m%d_%H%M%S)"
        STASHED=true
    fi
    
    # 拉取代码
    git pull origin "$CURRENT_BRANCH"
    
    print_success "代码拉取完成"
}

# ==================== 备份与恢复 ====================

backup_current_version() {
    print_step "备份当前版本..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local version_name="${CURRENT_VERSION}_${timestamp}"
    local backup_dir="$RELEASES_DIR/$version_name"
    
    mkdir -p "$backup_dir"
    
    # 记录 Git 信息
    echo "$CURRENT_COMMIT" > "$backup_dir/git_commit"
    echo "$CURRENT_VERSION" > "$backup_dir/git_version"
    echo "$CURRENT_BRANCH" > "$backup_dir/git_branch"
    echo "$DEPLOY_ENV" > "$backup_dir/deploy_env"
    echo "$(date -Iseconds)" > "$backup_dir/backup_time"
    
    # 备份前端构建产物
    if [ -d "$PROJECT_DIR/frontend/dist" ]; then
        print_info "备份前端构建产物..."
        cp -r "$PROJECT_DIR/frontend/dist" "$backup_dir/frontend_dist"
    fi
    
    # 备份数据库迁移状态
    if [ -d "$PROJECT_DIR/backend/alembic/versions" ]; then
        print_info "备份数据库迁移状态..."
        cd "$PROJECT_DIR/backend"
        local db_revision=$(alembic current 2>/dev/null | head -1 | awk '{print $1}' || echo "none")
        echo "$db_revision" > "$backup_dir/db_revision"
        cd "$PROJECT_DIR"
    fi
    
    # 更新软链接
    ln -sfn "$backup_dir" "$RELEASES_DIR/current"
    
    # 更新状态文件
    update_deploy_state "$version_name" "$backup_dir" "backup"
    
    print_success "版本备份完成: $backup_dir"
    
    BACKUP_DIR="$backup_dir"
}

restore_version() {
    local target_version=$1
    
    print_step "恢复版本: $target_version"
    
    # 查找备份目录
    local backup_dir=$(ls -dt $RELEASES_DIR/${target_version}* 2>/dev/null | head -1)
    
    if [ -z "$backup_dir" ]; then
        print_error "未找到版本: $target_version"
        return 1
    fi
    
    print_info "备份目录: $backup_dir"
    
    # 恢复 Git 状态
    if [ -f "$backup_dir/git_commit" ]; then
        local git_commit=$(cat "$backup_dir/git_commit")
        print_info "恢复 Git 状态: $git_commit"
        git checkout "$git_commit" 2>/dev/null || print_warning "Git checkout 失败，继续恢复..."
    fi
    
    # 恢复前端构建产物
    if [ -d "$backup_dir/frontend_dist" ]; then
        print_info "恢复前端构建产物..."
        rm -rf "$PROJECT_DIR/frontend/dist"
        cp -r "$backup_dir/frontend_dist" "$PROJECT_DIR/frontend/dist"
    fi
    
    # 回滚数据库（如果需要）
    if [ -f "$backup_dir/db_revision" ]; then
        local target_db_rev=$(cat "$backup_dir/db_revision")
        if [ "$target_db_rev" != "none" ]; then
            print_info "回滚数据库到: $target_db_rev"
            cd "$PROJECT_DIR/backend"
            alembic downgrade "$target_db_rev" 2>/dev/null || print_warning "数据库回滚失败"
            cd "$PROJECT_DIR"
        fi
    fi
    
    print_success "版本恢复完成"
}

cleanup_old_versions() {
    print_step "清理旧版本备份..."
    
    # 获取所有版本（排除 current 软链接）
    local versions=$(ls -dt $RELEASES_DIR/*/ 2>/dev/null | grep -v "current" || true)
    local count=$(echo "$versions" | grep -c '/' || echo 0)
    
    if [ "$count" -gt "$KEEP_VERSIONS" ]; then
        local to_delete=$(echo "$versions" | tail -n +$((KEEP_VERSIONS + 1)))
        print_info "删除 $((count - KEEP_VERSIONS)) 个旧版本..."
        echo "$to_delete" | xargs rm -rf
    fi
    
    print_success "清理完成，保留最近 $KEEP_VERSIONS 个版本"
}

# ==================== 依赖管理 ====================

install_dependencies() {
    print_step "更新依赖..."
    
    # Python 依赖
    print_info "安装 Python 依赖..."
    cd "$PROJECT_DIR/backend"
    $PYTHON_CMD -m pip install -r requirements.txt --quiet
    cd "$PROJECT_DIR"
    
    # Node.js 依赖
    if [ -z "$SKIP_FRONTEND" ]; then
        print_info "安装 Node.js 依赖..."
        cd "$PROJECT_DIR/frontend"
        if command -v pnpm &> /dev/null; then
            pnpm install --frozen-lockfile
        else
            npm ci
        fi
        cd "$PROJECT_DIR"
    fi
    
    print_success "依赖更新完成"
}

# ==================== 数据库迁移 ====================

run_database_migration() {
    print_step "执行数据库迁移..."
    
    cd "$PROJECT_DIR/backend"
    
    # 检测是否有未应用的迁移
    local current_rev=$(alembic current 2>/dev/null | head -1 | awk '{print $1}' || echo "")
    local head_rev=$(alembic heads 2>/dev/null | head -1 | awk '{print $1}' || echo "")
    
    print_info "当前版本: ${current_rev:-无}"
    print_info "目标版本: ${head_rev:-无}"
    
    # 检测模型变更并生成迁移文件
    if [ "$DEPLOY_ENV" = "dev" ]; then
        print_info "检测模型变更..."
        alembic revision --autogenerate -m "auto migration $(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
    fi
    
    # 执行迁移
    if [ "$current_rev" != "$head_rev" ] || [ -z "$current_rev" ]; then
        print_info "执行迁移..."
        
        # 备份数据库（生产环境）
        if [ "$DEPLOY_ENV" = "prod" ]; then
            print_warning "生产环境迁移，建议先备份数据库！"
            # 这里可以添加数据库备份逻辑
        fi
        
        alembic upgrade head
        print_success "数据库迁移完成"
    else
        print_success "数据库已是最新版本"
    fi
    
    cd "$PROJECT_DIR"
}

# ==================== 前端构建 ====================

detect_frontend_changes() {
    # 检查 package.json 或 pnpm-lock.yaml 是否更新
    if [ "frontend/package.json" -nt "frontend/dist" ] 2>/dev/null; then
        return 0
    fi
    
    # 检查 src 目录是否有变更
    if git diff --name-only HEAD~1 HEAD 2>/dev/null | grep -qE "^frontend/src/"; then
        return 0
    fi
    
    # dist 目录不存在
    if [ ! -d "frontend/dist" ]; then
        return 0
    fi
    
    return 1
}

build_frontend() {
    print_step "构建前端..."
    
    if [ -n "$SKIP_FRONTEND" ]; then
        print_warning "跳过前端构建（Node.js 未安装）"
        return 0
    fi
    
    cd "$PROJECT_DIR/frontend"
    
    local need_build=false
    
    case "$DEPLOY_ENV" in
        prod)
            # 生产环境：强制完整构建
            print_info "生产环境，执行完整构建..."
            need_build=true
            rm -rf dist
            ;;
        dev)
            # 开发环境：检测变更才构建
            if detect_frontend_changes; then
                print_info "检测到前端变更，开始构建..."
                need_build=true
            else
                print_success "前端无变更，跳过构建"
            fi
            ;;
    esac
    
    if [ "$need_build" = true ]; then
        if command -v pnpm &> /dev/null; then
            pnpm build
        else
            npm run build
        fi
        print_success "前端构建完成"
    fi
    
    cd "$PROJECT_DIR"
}

# ==================== 服务管理 ====================

# 获取服务 PID
get_service_pid() {
    local pid=""
    
    # 优先从 PID 文件获取
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if ps -p $pid > /dev/null 2>&1; then
            echo $pid
            return 0
        fi
    fi
    
    # 从端口获取
    pid=$(ss -lptn 'sport = :5000' 2>/dev/null | grep -oP 'pid=\K[0-9]+' | head -1)
    if [ -n "$pid" ] && ps -p $pid > /dev/null 2>&1; then
        echo $pid
        return 0
    fi
    
    return 1
}

# 检查服务是否运行
is_service_running() {
    local pid=$(get_service_pid)
    [ -n "$pid" ]
}

# 优雅重载服务（零中断）
# 原理：Gunicorn/Uvicorn 收到 HUP 信号后会重新加载 worker
graceful_reload() {
    print_step "优雅重载服务..."
    
    local pid=$(get_service_pid)
    
    if [ -z "$pid" ]; then
        print_warning "服务未运行，直接启动"
        start_service
        return $?
    fi
    
    print_info "发送 HUP 信号到进程 $pid..."
    
    # 发送 HUP 信号
    kill -HUP $pid 2>/dev/null
    
    # 等待重载完成
    sleep 2
    
    # 验证服务状态
    if is_service_running; then
        print_success "服务优雅重载成功 (PID: $(get_service_pid))"
        return 0
    else
        print_warning "优雅重载失败，尝试正常重启"
        restart_service
        return $?
    fi
}

stop_service() {
    print_info "停止服务..."
    
    local pid=$(get_service_pid)
    
    if [ -z "$pid" ]; then
        print_info "服务未运行"
        rm -f "$PID_FILE"
        return 0
    fi
    
    # 先尝试优雅停止 (TERM 信号)
    kill $pid 2>/dev/null
    
    # 等待最多 10 秒
    local wait=0
    while ps -p $pid > /dev/null 2>&1 && [ $wait -lt 10 ]; do
        sleep 1
        wait=$((wait + 1))
    done
    
    # 如果还在运行，强制停止
    if ps -p $pid > /dev/null 2>&1; then
        print_warning "服务未响应，强制停止..."
        kill -9 $pid 2>/dev/null
        sleep 1
    fi
    
    rm -f "$PID_FILE"
    print_success "服务已停止 (PID: $pid)"
}

start_service() {
    print_step "启动服务..."
    
    # 检查是否已运行
    if is_service_running; then
        print_warning "服务已在运行中 (PID: $(get_service_pid))"
        return 0
    fi
    
    # 创建日志目录
    mkdir -p "$LOG_DIR"
    
    cd "$PROJECT_DIR/backend"
    
    # 根据环境选择启动方式
    local reload_flag=""
    if [ "$DEPLOY_ENV" = "dev" ]; then
        # 开发环境：启用热重载
        reload_flag="--reload"
    fi
    
    nohup $PYTHON_CMD -m uvicorn app.main:app --host 0.0.0.0 --port 5000 $reload_flag > "$LOG_DIR/app.log" 2>&1 &
    local new_pid=$!
    echo $new_pid > "$PID_FILE"
    
    cd "$PROJECT_DIR"
    
    # 等待服务启动
    sleep 2
    
    if ps -p $new_pid > /dev/null 2>&1; then
        print_success "服务启动成功 (PID: $new_pid)"
    else
        print_error "服务启动失败，请检查日志: $LOG_DIR/app.log"
        return 1
    fi
}

restart_service() {
    local mode=${1:-"graceful"}
    
    case "$mode" in
        graceful)
            # 优先优雅重载
            if is_service_running; then
                graceful_reload
            else
                start_service
            fi
            ;;
        hard)
            # 硬重启（停止再启动）
            stop_service
            sleep 2
            start_service
            ;;
    esac
}

# ==================== 健康检查 ====================

health_check() {
    print_step "健康检查..."
    
    local max_retries=30
    local retry=0
    
    while [ $retry -lt $max_retries ]; do
        if curl -sf http://localhost:5000/api/v1/init/status > /dev/null 2>&1; then
            print_success "服务健康检查通过"
            return 0
        fi
        
        retry=$((retry + 1))
        echo -n "."
        sleep 1
    done
    
    echo ""
    print_error "健康检查失败，服务可能未正常启动"
    print_info "查看日志: tail -f $LOG_DIR/app.log"
    return 1
}

# ==================== 状态管理 ====================

update_deploy_state() {
    local version=$1
    local backup_dir=$2
    local status=$3
    
    $PYTHON_CMD << EOF
import json
import os
from datetime import datetime

state_file = "$STATE_FILE"
state = {"current_version": "", "last_deploy": "", "deploy_history": []}

if os.path.exists(state_file):
    try:
        with open(state_file) as f:
            state = json.load(f)
    except:
        pass

record = {
    "version": "$version",
    "env": "$DEPLOY_ENV",
    "branch": "$CURRENT_BRANCH",
    "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo unknown)",
    "timestamp": datetime.now().isoformat(),
    "backup_dir": "$backup_dir",
    "status": "$status"
}

if "$status" == "success":
    state["current_version"] = "$version"
    state["last_deploy"] = datetime.now().isoformat()
    state["git_commit"] = record["git_commit"]

state["deploy_history"].insert(0, record)
state["deploy_history"] = state["deploy_history"][:50]

with open(state_file, 'w') as f:
    json.dump(state, f, indent=2, ensure_ascii=False)
EOF
}

show_status() {
    print_banner
    
    echo -e "${CYAN}=== 服务状态 ===${NC}"
    
    # 检查端口
    local port_status=$(ss -lptn 'sport = :5000' 2>/dev/null | grep LISTEN)
    if [ -n "$port_status" ]; then
        local pid=$(echo "$port_status" | grep -oP 'pid=\K[0-9]+' | head -1)
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
    print_info "当前分支: $CURRENT_BRANCH"
    print_info "当前版本: $CURRENT_VERSION"
    print_info "当前提交: $CURRENT_COMMIT"
    
    echo ""
    echo -e "${CYAN}=== 部署状态 ===${NC}"
    if [ -f "$STATE_FILE" ]; then
        $PYTHON_CMD -c "
import json
with open('$STATE_FILE') as f:
    state = json.load(f)
    print(f\"当前版本: {state.get('current_version', 'N/A')}\")
    print(f\"最后部署: {state.get('last_deploy', 'N/A')}\")
"
    else
        print_info "暂无部署记录"
    fi
    
    echo ""
    echo -e "${CYAN}=== 版本备份 ===${NC}"
    local backup_count=$(ls -d $RELEASES_DIR/*/ 2>/dev/null | grep -v current | wc -l)
    print_info "备份数量: $backup_count"
    
    if [ -L "$RELEASES_DIR/current" ]; then
        local current_backup=$(readlink "$RELEASES_DIR/current")
        print_info "当前备份: $current_backup"
    fi
}

show_history() {
    print_banner
    echo -e "${CYAN}=== 部署历史 ===${NC}"
    
    if [ -f "$STATE_FILE" ]; then
        $PYTHON_CMD -c "
import json
with open('$STATE_FILE') as f:
    state = json.load(f)
    for i, record in enumerate(state.get('deploy_history', [])[:10]):
        status_color = '\033[92m' if record['status'] == 'success' else '\033[91m'
        print(f\"{i+1}. {record['timestamp'][:19]} [{status_color}{record['status']}\033[0m] {record['version']} ({record['env']})\")
"
    else
        print_info "暂无部署历史"
    fi
}

# ==================== 主命令 ====================

cmd_check() {
    print_banner
    detect_environment "$@"
    check_environment
    check_git_update
}

cmd_deploy() {
    print_banner
    detect_environment "$@"
    
    local force=false
    local reload_mode="graceful"
    
    # 解析参数
    for arg in "$@"; do
        case $arg in
            --force|-f) force=true ;;
            --hard-reload) reload_mode="hard" ;;
        esac
    done
    
    # 1. 环境检查
    check_environment || exit 1
    
    # 2. Git 更新检测
    local update_status
    check_git_update
    update_status=$?
    
    if [ $update_status -eq 0 ] && [ "$force" = false ]; then
        print_info "无更新，使用 --force 强制重新部署"
        exit 0
    fi
    
    # 3. 备份当前版本
    backup_current_version
    
    # 4. 拉取最新代码
    if [ $update_status -eq 1 ]; then
        pull_latest_code
    fi
    
    # 5. 更新依赖
    install_dependencies
    
    # 6. 数据库迁移
    run_database_migration
    
    # 7. 构建前端
    build_frontend
    
    # 8. 重启服务（开发环境优雅重载，生产环境默认也是优雅重载）
    # 使用 --hard-reload 强制硬重启
    print_info "重载模式: $reload_mode"
    restart_service "$reload_mode"
    
    # 9. 健康检查
    if health_check; then
        # 更新部署状态
        update_deploy_state "$CURRENT_VERSION" "$BACKUP_DIR" "success"
        
        # 清理旧版本
        cleanup_old_versions
        
        print_success "=== 部署完成 ==="
        print_info "访问地址: http://localhost:5000"
    else
        # 部署失败
        update_deploy_state "$CURRENT_VERSION" "$BACKUP_DIR" "failed"
        
        print_error "部署失败，正在回滚..."
        restore_version "$CURRENT_VERSION"
        restart_service "hard"
        
        exit 1
    fi
}

cmd_reload() {
    print_banner
    detect_environment "$@"
    
    local mode="graceful"
    
    for arg in "$@"; do
        case $arg in
            --hard|-h) mode="hard" ;;
        esac
    done
    
    print_step "重载服务 (模式: $mode)..."
    
    restart_service "$mode"
    health_check
    
    print_success "服务重载完成"
}

cmd_rollback() {
    print_banner
    
    local target_version=$1
    local mode="graceful"
    
    # 解析参数
    for arg in "$@"; do
        case $arg in
            --hard|-h) mode="hard" ;;
        esac
    done
    
    if [ -z "$target_version" ]; then
        # 显示可用版本
        echo -e "${CYAN}可回滚版本:${NC}"
        ls -dt $RELEASES_DIR/*/ 2>/dev/null | grep -v current | head -5 | while read dir; do
            local name=$(basename "$dir")
            local time=$(cat "$dir/backup_time" 2>/dev/null || echo "N/A")
            echo "  - $name (备份时间: $time)"
        done
        echo ""
        print_info "用法: ./deploy.sh rollback <version> [--hard]"
        exit 0
    fi
    
    restore_version "$target_version"
    restart_service "$mode"
    health_check
    
    print_success "回滚完成"
}

# ==================== 入口 ====================

case "${1:-help}" in
    check)
        cmd_check "$@"
        ;;
    deploy)
        cmd_deploy "$@"
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
        print_banner
        echo "用法: ./deploy/deploy.sh <命令> [选项]"
        echo ""
        echo "命令:"
        echo "  check              检查更新和环境"
        echo "  deploy             部署到当前环境（默认优雅重载）"
        echo "  reload             重载服务（不更新代码）"
        echo "  rollback [version] 回滚到指定版本"
        echo "  status             查看服务状态"
        echo "  history            查看部署历史"
        echo ""
        echo "选项:"
        echo "  --env=dev|prod     指定部署环境"
        echo "  --force, -f        强制重新部署（即使无更新）"
        echo "  --hard-reload      硬重启服务（停止再启动）"
        echo "  --hard, -h         用于 reload/rollback，硬重载"
        echo ""
        echo "重载模式说明:"
        echo "  默认（优雅重载）   kill -HUP，零中断"
        echo "  --hard-reload      停止再启动，短暂中断"
        echo ""
        echo "示例:"
        echo "  ./deploy/deploy.sh check"
        echo "  ./deploy/deploy.sh deploy --env=prod"
        echo "  ./deploy/deploy.sh deploy --force            # 强制部署"
        echo "  ./deploy/deploy.sh deploy --hard-reload      # 硬重启部署"
        echo "  ./deploy/deploy.sh reload                    # 优雅重载"
        echo "  ./deploy/deploy.sh reload --hard             # 硬重载"
        echo "  ./deploy/deploy.sh rollback v1.2.3_20240327"
        ;;
    *)
        print_error "未知命令: $1"
        exit 1
        ;;
esac
