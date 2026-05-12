#!/bin/bash
# 交互式 SSH 连接脚本 — 自动化测试平台
# 用法: ./scripts/remote_ssh.sh
# 直接登录远程机器进行交互式操作

REMOTE_HOST="192.168.3.200"
REMOTE_USER="root"
REMOTE_PORT="22"
REMOTE_PASS="Huawei@12345"

echo "正在连接 ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PORT} ..."
sshpass -p "${REMOTE_PASS}" ssh -o StrictHostKeyChecking=no -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST}
