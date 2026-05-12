#!/bin/bash
# 远程文件同步脚本 — 自动化测试平台
# 用法: ./scripts/remote_copy.sh [local_path] [remote_path]
# 示例: ./scripts/remote_copy.sh  (同步整个项目)
#       ./scripts/remote_copy.sh backend/app /home/shareDIR/TDD-auto-platform/backend/app

REMOTE_HOST="192.168.3.200"
REMOTE_USER="root"
REMOTE_PORT="22"
REMOTE_PASS="Huawei@12345"
LOCAL_DIR="E:/shareDIR/TDD-auto-platform"
REMOTE_DIR="/home/shareDIR/TDD-auto-platform"

if [ -n "$1" ] && [ -n "$2" ]; then
    echo "同步 ${1} -> ${REMOTE_HOST}:${2}"
    sshpass -p "${REMOTE_PASS}" rsync -avz -e "ssh -p ${REMOTE_PORT}" --exclude='.git' --exclude='__pycache__' --exclude='node_modules' --exclude='.venv' "${LOCAL_DIR}/${1}/" ${REMOTE_USER}@${REMOTE_HOST}:"${2}/"
else
    echo "同步整个项目 ${LOCAL_DIR} -> ${REMOTE_HOST}:${REMOTE_DIR}"
    sshpass -p "${REMOTE_PASS}" rsync -avz -e "ssh -p ${REMOTE_PORT}" --exclude='.git' --exclude='__pycache__' --exclude='node_modules' --exclude='.venv' "${LOCAL_DIR}/" ${REMOTE_USER}@${REMOTE_HOST}:"${REMOTE_DIR}/"
fi
