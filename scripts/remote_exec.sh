#!/bin/bash
# 远程执行脚本 — 自动化测试平台
# 用法: ./scripts/remote_exec.sh "命令"
# 示例: ./scripts/remote_exec.sh "cd /home/shareDIR/TDD-auto-platform/backend && python -m pytest"

REMOTE_HOST="192.168.3.200"
REMOTE_USER="root"
REMOTE_PORT="22"
REMOTE_PASS="Huawei@12345"
REMOTE_DIR="/home/shareDIR/TDD-auto-platform"

# 使用 sshpass 进行非交互式 SSH
if [ -z "$1" ]; then
    echo "用法: $0 \"要执行的命令\""
    echo "示例: $0 \"cd ${REMOTE_DIR}/backend && python -m pytest -v\""
    exit 1
fi

sshpass -p "${REMOTE_PASS}" ssh -o StrictHostKeyChecking=no -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST} "$1"
