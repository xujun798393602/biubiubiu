#!/bin/bash
# 导出所有容器日志到 /opt/auto-test/logs/
# 用法: bash scripts/dump-logs.sh

LOG_DIR="/opt/auto-test/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "${LOG_DIR}"/{postgres,redis,backend,nginx}

for svc in auto-test-postgres auto-test-redis auto-test-backend auto-test-frontend; do
    name="${svc#auto-test-}"
    docker logs "${svc}" > "${LOG_DIR}/${name}/${name}_${TIMESTAMP}.log" 2>&1
    echo "已导出: ${LOG_DIR}/${name}/${name}_${TIMESTAMP}.log"
done

echo "全部日志导出完成"
