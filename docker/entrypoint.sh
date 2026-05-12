#!/bin/bash
# ============================================================
# 运维管理平台 - 单容器全栈部署入口脚本
# 启动顺序: PostgreSQL → Redis → 数据库迁移 → Nginx + 后端
# ============================================================
set -e

# ==================== 配置区 ====================
PG_USER="${PGUSER:-opscenter}"
PG_PASS="${PGPASSWORD:-OpsCenter@2024}"
PG_DB="${PGDATABASE:-opscenter}"
PG_DATA="/var/lib/postgresql/data"
PG_VERSION="15"

# ==================== 工具函数 ====================
log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
warn() { log "⚠ $*"; }
ok()   { log "✓ $*"; }

wait_for_pg() {
    local max=30 i=1
    while [ $i -le $max ]; do
        if pg_isready -h 127.0.0.1 -p 5432 -q 2>/dev/null; then
            return 0
        fi
        log "  等待 PostgreSQL 启动... ($i/$max)"
        sleep 1
        i=$((i+1))
    done
    return 1
}

# ==================== 1. 初始化 PostgreSQL ====================
log "=========================================="
log "  运维管理平台 - 单容器全栈部署"
log "=========================================="

log "[1/5] 初始化 PostgreSQL..."

# 查找 PostgreSQL 版本号
PG_BIN="/usr/lib/postgresql/$PG_VERSION/bin"
if [ ! -d "$PG_BIN" ]; then
    # 自动查找实际安装的版本
    PG_BIN=$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | head -1)
    if [ -z "$PG_BIN" ]; then
        log "✗ 未找到 PostgreSQL，请检查 Dockerfile"
        exit 1
    fi
    PG_VERSION=$(echo "$PG_BIN" | grep -oP '\d+')
fi

# 如果数据目录为空，执行 initdb
if [ ! -f "$PG_DATA/PG_VERSION" ]; then
    log "  首次启动，初始化数据库..."
    mkdir -p "$PG_DATA"
    chown postgres:postgres "$PG_DATA"
    su - postgres -c "$PG_BIN/initdb -D $PG_DATA" >/dev/null 2>&1
    ok "数据库目录初始化完成"
else
    log "  数据目录已存在，跳过初始化"
fi

# 配置 pg_hba.conf 允许本地连接
PG_HBA="$PG_DATA/pg_hba.conf"
cat > "$PG_HBA" << EOF
# TYPE  DATABASE  USER  ADDRESS         METHOD
local   all       all                   trust
host    all       all   127.0.0.1/32    md5
host    all       all   ::1/128         md5
EOF
chown postgres:postgres "$PG_HBA"

# 启动 PostgreSQL
su - postgres -c "$PG_BIN/pg_ctl -D $PG_DATA -l $PG_DATA/logfile -o \"-p 5432\" start" >/dev/null 2>&1

if wait_for_pg; then
    ok "PostgreSQL 已启动"
else
    log "✗ PostgreSQL 启动失败，查看日志: $PG_DATA/logfile"
    cat "$PG_DATA/logfile" 2>/dev/null | tail -n 20
    exit 1
fi

# 创建用户和数据库（仅首次）
if ! su - postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='$PG_USER'\"" 2>/dev/null | grep -q 1; then
    su - postgres -c "psql -c \"CREATE USER $PG_USER WITH PASSWORD '$PG_PASS' SUPERUSER;\"" >/dev/null 2>&1
    ok "用户 $PG_USER 创建成功"
fi

if ! su - postgres -c "psql -lqt" 2>/dev/null | cut -d \| -f 1 | grep -qw "$PG_DB"; then
    su - postgres -c "psql -c \"CREATE DATABASE $PG_DB OWNER $PG_USER;\"" >/dev/null 2>&1
    ok "数据库 $PG_DB 创建成功"
fi

# ==================== 2. 启动 Redis ====================
log "[2/5] 启动 Redis..."
redis-server --daemonize yes --bind 127.0.0.1 --port 6379 \
    --dir /tmp --pidfile /var/run/redis/redis-server.pid \
    >/dev/null 2>&1
if redis-cli ping >/dev/null 2>&1; then
    ok "Redis 已启动"
else
    warn "Redis 启动失败，部分功能不可用"
fi

# ==================== 3. 设置环境变量 ====================
log "[3/5] 配置环境变量..."

export DATABASE_URL="postgresql+psycopg2://${PG_USER}:${PG_PASS}@127.0.0.1:5432/${PG_DB}"
export PGHOST="127.0.0.1"
export PGPORT="5432"
export PGUSER="$PG_USER"
export PGPASSWORD="$PG_PASS"
export PGDATABASE="$PG_DB"
export REDIS_HOST="127.0.0.1"
export REDIS_PORT="6379"

# 安全密钥：未设置则自动生成
export JWT_SECRET_KEY="${JWT_SECRET_KEY:-$(head -c 32 /dev/urandom | base64 | head -c 32)}"
export PASSWORD_SALT="${PASSWORD_SALT:-opscenter-salt-$(date +%s)}"
export AES_KEY="${AES_KEY:-$(head -c 32 /dev/urandom | base64 | head -c 32)}"
export APP_ENV="${APP_ENV:-production}"

ok "环境变量已配置"

# ==================== 4. 运行数据库迁移 ====================
log "[4/5] 运行数据库迁移..."
cd /app/backend

if [ -f "alembic.ini" ] && [ -d "alembic" ]; then
    alembic upgrade head 2>&1 || warn "alembic 迁移失败，依赖应用自动建表"
else
    warn "未找到 alembic，依赖应用自动建表"
fi

ok "数据库迁移完成"

# ==================== 5. 启动应用服务 ====================
log "[5/5] 启动应用服务 (Nginx + Uvicorn)..."

# supervisord 会继承当前 shell 的所有环境变量
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/opscenter.conf
