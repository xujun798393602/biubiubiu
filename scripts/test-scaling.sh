#!/bin/bash
# 完整的节点扩容测试脚本

set -e

echo "=========================================="
echo "节点扩容功能完整测试"
echo "=========================================="

# 配置
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
API_URL="$BACKEND_URL/api/v1"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 获取管理员 token（需要先登录）
get_admin_token() {
    echo -e "${BLUE}获取管理员 Token...${NC}"

    # 尝试使用默认管理员账号登录
    TOKEN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "admin123"}')

    TOKEN=$(echo $TOKEN_RESPONSE | grep -o '"token":"[^"]*"' | cut -d'"' -f4)

    if [ -z "$TOKEN" ]; then
        echo -e "${RED}无法获取 Token，请确保已创建管理员账号${NC}"
        echo "响应: $TOKEN_RESPONSE"
        exit 1
    fi

    echo -e "${GREEN}✓ Token 获取成功${NC}"
}

# 测试创建节点
test_create_node() {
    echo ""
    echo -e "${BLUE}测试创建节点...${NC}"

    CREATE_RESPONSE=$(curl -s -X POST "$API_URL/nodes" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TOKEN" \
        -d '{
            "name": "test-playwright-worker",
            "host": "192.168.3.200",
            "port": 8080,
            "node_type": "PLAYWRIGHT",
            "max_concurrent": 3
        }')

    echo "响应: $CREATE_RESPONSE"

    # 提取 node_id 和 api_key
    NODE_ID=$(echo $CREATE_RESPONSE | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
    API_KEY=$(echo $CREATE_RESPONSE | grep -o '"api_key":"[^"]*"' | cut -d'"' -f4)

    if [ -n "$NODE_ID" ] && [ -n "$API_KEY" ]; then
        echo -e "${GREEN}✓ 节点创建成功${NC}"
        echo "   Node ID: $NODE_ID"
        echo "   API Key: $API_KEY"
    else
        echo -e "${RED}✗ 节点创建失败${NC}"
        exit 1
    fi
}

# 测试节点列表
test_list_nodes() {
    echo ""
    echo -e "${BLUE}测试获取节点列表...${NC}"

    LIST_RESPONSE=$(curl -s "$API_URL/nodes?page=1&pageSize=10" \
        -H "Authorization: Bearer $TOKEN")

    echo "响应: $LIST_RESPONSE"
    echo -e "${GREEN}✓ 节点列表获取成功${NC}"
}

# 测试节点统计
test_node_stats() {
    echo ""
    echo -e "${BLUE}测试获取节点统计...${NC}"

    STATS_RESPONSE=$(curl -s "$API_URL/nodes/stats" \
        -H "Authorization: Bearer $TOKEN")

    echo "响应: $STATS_RESPONSE"
    echo -e "${GREEN}✓ 节点统计获取成功${NC}"
}

# 测试节点心跳
test_node_heartbeat() {
    echo ""
    echo -e "${BLUE}测试节点心跳...${NC}"

    HEARTBEAT_RESPONSE=$(curl -s -X POST "$API_URL/nodes/$NODE_ID/heartbeat" \
        -H "Content-Type: application/json" \
        -d '{
            "cpu_usage": 25.5,
            "memory_usage": 45.2,
            "disk_usage": 60.0,
            "current_tasks": 0
        }')

    echo "响应: $HEARTBEAT_RESPONSE"
    echo -e "${GREEN}✓ 心跳更新成功${NC}"
}

# 测试一键扩容
test_scale_nodes() {
    echo ""
    echo -e "${BLUE}测试一键扩容...${NC}"

    SCALE_RESPONSE=$(curl -s -X POST "$API_URL/nodes/scale" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TOKEN" \
        -d '{
            "name": "auto-worker",
            "host": "192.168.3.200",
            "port": 8080,
            "node_type": "LOCUST",
            "max_concurrent": 5,
            "count": 2
        }')

    echo "响应: $SCALE_RESPONSE"
    echo -e "${GREEN}✓ 一键扩容成功${NC}"
}

# 测试删除节点
test_delete_node() {
    echo ""
    echo -e "${BLUE}清理测试数据...${NC}"

    DELETE_RESPONSE=$(curl -s -X DELETE "$API_URL/nodes/$NODE_ID" \
        -H "Authorization: Bearer $TOKEN")

    echo "响应: $DELETE_RESPONSE"
    echo -e "${GREEN}✓ 节点删除成功${NC}"
}

# 主测试流程
main() {
    echo ""
    echo "开始测试..."
    echo ""

    get_admin_token
    test_create_node
    test_list_nodes
    test_node_stats
    test_node_heartbeat
    test_scale_nodes
    test_delete_node

    echo ""
    echo "=========================================="
    echo -e "${GREEN}所有测试通过！${NC}"
    echo "=========================================="
    echo ""
    echo "下一步："
    echo "1. 使用获取的 API Key 启动 Worker 容器"
    echo "2. 在页面验证节点状态为 ONLINE"
    echo "3. 创建测试任务验证分发功能"
}

main "$@"
