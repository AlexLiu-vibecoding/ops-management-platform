#!/bin/bash
# 更新 Python 依赖锁定文件
# 
# 使用方法:
#   ./scripts/update_deps.sh           # 更新 requirements.lock.txt
#   ./scripts/update_deps.sh --pip-compile  # 使用 pip-compile (需要网络稳定)

set -e

cd "$(dirname "$0")/.."

echo "=== 更新 Python 依赖 ==="

if [ "$1" = "--pip-compile" ]; then
    echo "使用 pip-compile 生成锁定文件..."
    python3 -m venv venv
    source venv/bin/activate
    pip install pip-tools
    pip-compile backend/requirements.in --output-file=backend/requirements.lock.txt
    echo "已生成 backend/requirements.lock.txt"
else
    echo "使用 pip freeze 生成锁定文件..."
    source venv/bin/activate
    pip freeze > backend/requirements.lock.txt
    echo "已生成 backend/requirements.lock.txt"
fi

echo "=== 依赖更新完成 ==="
