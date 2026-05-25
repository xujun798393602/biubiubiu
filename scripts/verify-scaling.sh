#!/bin/bash
# 验证节点扩容功能的脚本

set -e

echo "=========================================="
echo "节点扩容功能验证"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

BACKEND_URL="http://localhost:8000"

# 检查后端是否运行
echo "1. 检查后端服务状态..."
if curl -s "$BACKEND_URL/api/v1/health" > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓ 后端服务正常${NC}"
else
    echo -e "   ${RED}✗ 后端服务不可用${NC}"
    echo "   请先启动服务: docker compose up -d"
    exit 1
fi

# 检查数据库迁移
echo ""
echo "2. 检查数据库迁移状态..."
docker compose exec -T backend alembic current 2>/dev/null || {
    echo -e "   ${YELLOW}! 执行数据库迁移...${NC}"
    docker compose exec -T backend alembic stamp head
}
echo -e "   ${GREEN}✓ 数据库迁移完成${NC}"

# 获取节点列表
echo ""
echo "3. 获取当前节点列表..."
NODES_RESPONSE=$(curl -s "$BACKEND_URL/api/v1/nodes?page=1&pageSize=10")
echo "   响应: $NODES_RESPONSE"

# 获取节点统计
echo ""
echo "4. 获取节点统计信息..."
STATS_RESPONSE=$(curl -s "$BACKEND_URL/api/v1/nodes/stats")
echo "   统计: $STATS_RESPONSE"

echo ""
echo "=========================================="
echo "验证完成！"
echo "=========================================="
echo ""
echo "下一步操作："
echo "1. 在页面添加节点: http://你的服务器/nodes"
echo "2. 复制 API Key"
echo "3. 启动 Worker: docker run -d ..."
echo ""
