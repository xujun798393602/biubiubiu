#!/bin/bash
# 验证 Locust Worker 运行状态

set -e

# 配置
WORKER_NAME="${1:-locust-worker-1}"

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "验证 Locust Worker 状态"
echo "=========================================="
echo ""

# 检查容器是否运行
echo "1. 检查容器运行状态..."
if docker ps | grep -q "$WORKER_NAME"; then
    echo -e "   ${GREEN}✓ 容器 $WORKER_NAME 正在运行${NC}"
else
    echo -e "   ${RED}✗ 容器 $WORKER_NAME 未运行${NC}"
    echo ""
    echo "启动 Worker:"
    echo "  docker start $WORKER_NAME"
    echo "或查看日志排查问题:"
    echo "  docker logs $WORKER_NAME"
    exit 1
fi

# 检查容器日志
echo ""
echo "2. 检查容器日志..."
LOGS=$(docker logs --tail 20 "$WORKER_NAME" 2>&1)

if echo "$LOGS" | grep -q "Registered successfully"; then
    echo -e "   ${GREEN}✓ Worker 已成功注册${NC}"
else
    echo -e "   ${YELLOW}! Worker 可能未完成注册${NC}"
fi

if echo "$LOGS" | grep -q "Task consumer started"; then
    echo -e "   ${GREEN}✓ 任务消费者已启动${NC}"
else
    echo -e "   ${YELLOW}! 任务消费者可能未启动${NC}"
fi

if echo "$LOGS" | grep -q "ERROR"; then
    echo -e "   ${RED}✗ 发现错误:${NC}"
    echo "$LOGS" | grep "ERROR" | head -5
else
    echo -e "   ${GREEN}✓ 无错误日志${NC}"
fi

# 显示最近日志
echo ""
echo "3. 最近日志 (最后10行):"
echo "----------------------------------------"
docker logs --tail 10 "$WORKER_NAME" 2>&1
echo "----------------------------------------"

# 检查资源使用
echo ""
echo "4. 资源使用情况:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" "$WORKER_NAME" 2>/dev/null || echo "   无法获取资源信息"

echo ""
echo "=========================================="
echo "验证完成"
echo "=========================================="
echo ""
echo "常用命令："
echo "  查看实时日志: docker logs -f $WORKER_NAME"
echo "  重启 Worker: docker restart $WORKER_NAME"
echo "  停止 Worker: docker stop $WORKER_NAME"
echo "  进入容器: docker exec -it $WORKER_NAME bash"
