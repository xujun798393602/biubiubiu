#!/bin/bash
# 批量启动 Locust Worker 脚本

set -e

# 配置
BACKEND_URL="${BACKEND_URL:-http://backend:8000}"
REDIS_URL="${REDIS_URL:-redis://redis:6379/0}"
NETWORK="${NETWORK:-tdd-auto-platform_auto-test-net}"
WORKER_COUNT="${1:-3}"
API_KEY="${2:-}"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "批量启动 Locust Worker"
echo "=========================================="
echo ""
echo "配置信息："
echo "  - Worker 数量: $WORKER_COUNT"
echo "  - Backend URL: $BACKEND_URL"
echo "  - Redis URL: $REDIS_URL"
echo "  - Network: $NETWORK"
echo ""

if [ -z "$API_KEY" ]; then
    echo -e "${YELLOW}警告: 未设置 API_KEY，Worker 将使用自动注册${NC}"
    echo ""
fi

# 启动 Worker
for i in $(seq 1 $WORKER_COUNT); do
    WORKER_NAME="locust-worker-$i"

    echo -e "${BLUE}启动 $WORKER_NAME...${NC}"

    # 停止已存在的同名容器
    docker rm -f "$WORKER_NAME" 2>/dev/null || true

    # 启动新容器
    docker run -d \
        --name "$WORKER_NAME" \
        --network "$NETWORK" \
        -e BACKEND_URL="$BACKEND_URL" \
        -e REDIS_URL="$REDIS_URL" \
        -e NODE_TYPE=LOCUST \
        -e NODE_NAME="$WORKER_NAME" \
        -e API_KEY="$API_KEY" \
        -e MAX_CONCURRENT=5 \
        -e HEARTBEAT_INTERVAL=10 \
        --restart unless-stopped \
        tdd-auto-platform-backend-worker:latest

    echo -e "${GREEN}✓ $WORKER_NAME 启动成功${NC}"
    sleep 2
done

echo ""
echo "=========================================="
echo -e "${GREEN}所有 Worker 启动完成！${NC}"
echo "=========================================="
echo ""
echo "查看运行状态："
echo "  docker ps | grep locust-worker"
echo ""
echo "查看日志："
echo "  docker logs -f locust-worker-1"
echo ""
echo "停止所有 Worker："
echo "  for i in \$(seq 1 $WORKER_COUNT); do docker stop locust-worker-\$i; done"
