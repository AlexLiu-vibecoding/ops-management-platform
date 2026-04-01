#!/bin/bash

echo "======================================"
echo "通知功能架构优化 - 快速验证脚本"
echo "======================================"
echo ""

echo "1. 检查后端服务状态..."
if curl -s http://localhost:5000/api/v1/notification/channel-types > /dev/null 2>&1; then
    echo "   ✅ 后端服务运行正常"
else
    echo "   ❌ 后端服务未启动"
    exit 1
fi

echo ""
echo "2. 检查新增API路由..."
API_COUNT=$(curl -s http://localhost:5000/openapi.json | jq -r '.paths | keys[]' | grep "notification/config" | wc -l)
if [ "$API_COUNT" -ge 4 ]; then
    echo "   ✅ 新增API路由已加载（共${API_COUNT}个）"
    echo "   - /api/v1/notification/config/silence-rules"
    echo "   - /api/v1/notification/config/rate-limit-rules"
else
    echo "   ❌ API路由未正确加载"
    exit 1
fi

echo ""
echo "3. 检查前端构建..."
if [ -f "/workspace/projects/frontend/dist/assets/config-DbII-R4P.js" ]; then
    SIZE=$(ls -lh /workspace/projects/frontend/dist/assets/config-DbII-R4P.js | awk '{print $5}')
    echo "   ✅ 前端页面已构建（大小：${SIZE}）"
else
    echo "   ❌ 前端页面未构建"
    exit 1
fi

echo ""
echo "======================================"
echo "✅ 所有检查通过！"
echo "======================================"
echo ""
echo "📱 访问页面："
echo "   http://localhost:5000/notification-config"
echo ""
echo "🔐 登录账号："
echo "   用户名: admin"
echo "   密码: admin123"
echo ""
echo "📋 功能列表："
echo "   1. 静默规则管理（一次性/每日/每周）"
echo "   2. 频率限制管理（时间窗口/冷却期）"
echo "   3. 权限关联管理（6个权限编码）"
echo ""
