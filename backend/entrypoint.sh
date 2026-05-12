#!/bin/bash
set -e

LOG_DIR="/logs/runner"
mkdir -p "${LOG_DIR}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

run_migration() {
    echo "=============================="
    echo "  数据库迁移  $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=============================="
    echo "DATABASE_URL: ${DATABASE_URL:-未设置}"
    LOG_FILE="${LOG_DIR}/migration_${TIMESTAMP}.log"

    echo "[1/2] 生成迁移脚本..." | tee -a "${LOG_FILE}"
    alembic revision --autogenerate -m "auto_${TIMESTAMP}" 2>&1 | tee -a "${LOG_FILE}"

    echo "[2/2] 执行迁移..." | tee -a "${LOG_FILE}"
    alembic upgrade head 2>&1 | tee -a "${LOG_FILE}"

    echo "迁移完成: ${LOG_FILE}"
}

run_seed() {
    echo "=============================="
    echo "  初始化管理员  $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=============================="
    LOG_FILE="${LOG_DIR}/seed_${TIMESTAMP}.log"

    python -c "
import asyncio
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User, Role, UserRole
from sqlalchemy import select

async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as s:
        role = (await s.execute(select(Role).where(Role.code == 'ADMIN'))).scalar_one_or_none()
        if not role:
            role = Role(code='ADMIN', name='管理员', description='系统管理员', permissions=['*'])
            s.add(role); await s.flush()
        admin = (await s.execute(select(User).where(User.username == 'admin'))).scalar_one_or_none()
        if not admin:
            admin = User(username='admin', password_hash=hash_password('admin@123'), email='admin@example.com', real_name='管理员', is_active=True)
            s.add(admin); await s.flush()
            s.add(UserRole(user_id=admin.id, role_id=role.id))
        await s.commit()
        print('管理员初始化完成: admin / admin@123')

asyncio.run(seed())
" 2>&1 | tee "${LOG_FILE}"

    echo "初始化完成: ${LOG_FILE}"
}

run_test() {
    echo "=============================="
    echo "  单元测试  $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=============================="
    LOG_FILE="${LOG_DIR}/test_${TIMESTAMP}.log"
    REPORT_FILE="${LOG_DIR}/test_report_${TIMESTAMP}.xml"

    pytest tests/ -v --tb=short --junitxml="${REPORT_FILE}" 2>&1 | tee "${LOG_FILE}"
    EXIT_CODE=${PIPESTATUS[0]}

    echo ""
    echo "测试日志: ${LOG_FILE}"
    echo "测试报告: ${REPORT_FILE}"
    exit ${EXIT_CODE}
}

run_all() {
    run_migration
    echo ""
    run_seed
    echo ""
    run_test
}

show_help() {
    echo "========================================="
    echo "  自动化测试平台 - Runner 容器"
    echo "========================================="
    echo ""
    echo "用法: docker compose --profile tools run --rm runner <command>"
    echo ""
    echo "命令:"
    echo "  migrate   生成并执行数据库迁移"
    echo "  seed      初始化默认管理员 (admin / admin@123)"
    echo "  test      执行单元测试"
    echo "  all       迁移 + 初始化 + 测试（默认）"
    echo "  help      显示帮助"
    echo ""
    echo "日志输出: /opt/auto-test/logs/runner/"
}

case "${1:-all}" in
    migrate)  run_migration ;;
    seed)     run_seed ;;
    test)     run_test ;;
    all)      run_all ;;
    help)     show_help ;;
    *)        echo "未知命令: $1"; show_help; exit 1 ;;
esac
