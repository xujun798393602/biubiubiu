#!/bin/bash
# Worker 节点启动脚本
# 使用方法: ./scripts/start-workers.sh [locust|playwright|all] [start|stop|restart|status]

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置文件
COMPOSE_FILE="docker-compose.worker.yml"
ENV_FILE=".env.worker"

# 函数：打印帮助信息
show_help() {
    echo -e "${BLUE}Worker 节点管理脚本${NC}"
    echo ""
    echo "使用方法:"
    echo "  $0 [服务类型] [操作]"
    echo ""
    echo "服务类型:"
    echo "  locust      - Locust 性能测试 Worker"
    echo "  playwright  - Playwright UI测试 Worker"
    echo "  all         - 所有 Worker"
    echo ""
    echo "操作:"
    echo "  start       - 启动服务"
    echo "  stop        - 停止服务"
    echo "  restart     - 重启服务"
    echo "  status      - 查看状态"
    echo "  logs        - 查看日志"
    echo "  build       - 构建镜像"
    echo "  config      - 显示当前配置"
    echo ""
    echo "示例:"
    echo "  $0 locust start      # 启动 Locust Worker"
    echo "  $0 all start         # 启动所有 Worker"
    echo "  $0 all stop          # 停止所有 Worker"
    echo "  $0 locust logs       # 查看 Locust Worker 日志"
    echo "  $0 all config        # 显示当前配置"
}

# 函数：检查配置文件
check_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${YELLOW}警告: $ENV_FILE 不存在${NC}"
        echo -e "正在从示例文件创建..."
        cp .env.worker.example "$ENV_FILE"
        echo -e "${GREEN}已创建 $ENV_FILE，请修改其中的 API Key 配置${NC}"
        echo -e "配置文件位置: $(pwd)/$ENV_FILE"
        exit 1
    fi

    # 检查 API Key 是否配置
    source "$ENV_FILE"
    if [ -z "$LOCUST_WORKER_API_KEY" ] && [ -z "$PLAYWRIGHT_WORKER_API_KEY" ]; then
        echo -e "${YELLOW}警告: 未配置任何 Worker API Key${NC}"
        echo -e "请编辑 $ENV_FILE 文件，填入在界面获取的 API Key"
        echo ""
        echo -e "配置示例:"
        echo -e "  LOCUST_WORKER_API_KEY=你的locust节点api_key"
        echo -e "  PLAYWRIGHT_WORKER_API_KEY=你的playwright节点api_key"
        echo ""
        exit 1
    fi
}

# 函数：构建镜像
build_images() {
    local service=$1
    check_env_file
    echo -e "${BLUE}构建 Worker 镜像...${NC}"
    if [ "$service" = "all" ]; then
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build
    else
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build "${service}-worker-1"
    fi
    echo -e "${GREEN}镜像构建完成${NC}"
}

# 函数：启动服务
start_services() {
    local service=$1
    check_env_file

    echo -e "${BLUE}启动 $service 服务...${NC}"

    if [ "$service" = "all" ]; then
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
    else
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d "${service}-worker-1"
    fi

    echo -e "${GREEN}服务启动完成${NC}"
    show_status
}

# 函数：停止服务
stop_services() {
    local service=$1

    echo -e "${BLUE}停止 $service 服务...${NC}"

    if [ "$service" = "all" ]; then
        docker compose -f "$COMPOSE_FILE" down
    else
        docker compose -f "$COMPOSE_FILE" stop "${service}-worker-1"
    fi

    echo -e "${GREEN}服务已停止${NC}"
}

# 函数：重启服务
restart_services() {
    local service=$1
    stop_services "$service"
    start_services "$service"
}

# 函数：显示状态
show_status() {
    echo ""
    echo -e "${BLUE}=== Worker 服务状态 ===${NC}"
    docker compose -f "$COMPOSE_FILE" ps
    echo ""
}

# 函数：显示配置
show_config() {
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${YELLOW}配置文件不存在: $ENV_FILE${NC}"
        return
    fi

    echo -e "${BLUE}=== 当前 Worker 配置 ===${NC}"

    # 读取配置值
    local locust_key=$(grep -E "^LOCUST_WORKER_API_KEY=" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    local locust_concurrent=$(grep -E "^LOCUST_MAX_CONCURRENT=" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    local playwright_key=$(grep -E "^PLAYWRIGHT_WORKER_API_KEY=" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    local playwright_concurrent=$(grep -E "^PLAYWRIGHT_MAX_CONCURRENT=" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"' | tr -d "'")

    echo -e "Locust Worker:"
    if [ -n "$locust_key" ] && [ "$locust_key" != "your_locust_api_key_here" ]; then
        echo -e "  API Key: ${locust_key:0:8}...${locust_key: -4}"
    else
        echo -e "  API Key: ${RED}未配置${NC}"
    fi
    echo -e "  最大并发: ${locust_concurrent:-5}"

    echo -e "Playwright Worker:"
    if [ -n "$playwright_key" ] && [ "$playwright_key" != "your_playwright_api_key_here" ]; then
        echo -e "  API Key: ${playwright_key:0:8}...${playwright_key: -4}"
    else
        echo -e "  API Key: ${RED}未配置${NC}"
    fi
    echo -e "  最大并发: ${playwright_concurrent:-3}"
    echo ""
}

# 函数：查看日志
show_logs() {
    local service=$1

    if [ "$service" = "all" ]; then
        docker compose -f "$COMPOSE_FILE" logs -f
    else
        docker compose -f "$COMPOSE_FILE" logs -f "${service}-worker-1"
    fi
}

# 主函数
main() {
    local service=${1:-"help"}
    local action=${2:-"help"}

    # 切换到项目根目录
    cd "$(dirname "$0")/.."

    case "$action" in
        start)
            start_services "$service"
            ;;
        stop)
            stop_services "$service"
            ;;
        restart)
            restart_services "$service"
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$service"
            ;;
        build)
            build_images "$service"
            ;;
        config)
            show_config
            ;;
        *)
            show_help
            ;;
    esac
}

main "$@"
