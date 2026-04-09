#!/bin/bash
# 快速测试脚本：只运行单元测试，跳过慢测试

cd "$(dirname "$0")/.."

echo "🚀 运行快速测试..."
python -m pytest tests/ \
    -m "not slow and not e2e" \
    --tb=short \
    -q \
    --no-cov

echo ""
echo "✅ 快速测试完成"
