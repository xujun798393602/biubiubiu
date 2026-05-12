"""远程执行工具 — 通过 SSH 在远程 Linux 机器上执行命令。

用法:
    python scripts/remote.py "命令"
    python scripts/remote.py shell          # 交互式 shell 提示符
    python scripts/remote.py pytest         # 运行后端测试
    python scripts/remote.py status         # 检查服务状态

SSH 配置自动保存在 scripts/.ssh_config.json
"""

import sys
import os
import json
import paramiko

# ── SSH 配置 ──────────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(__file__), ".ssh_config.json")

DEFAULT_CONFIG = {
    "host": "192.168.3.200",
    "port": 22,
    "user": "root",
    "password": "Huawei@12345",
    "remote_dir": "/home/shareDIR/TDD-auto-platform",
}


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
            # merge with defaults
            for k, v in DEFAULT_CONFIG.items():
                cfg.setdefault(k, v)
            return cfg
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def get_client(cfg: dict) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=cfg["host"],
        port=cfg["port"],
        username=cfg["user"],
        password=cfg["password"],
        timeout=10,
    )
    return client


def exec_remote(cmd: str, cfg: dict = None) -> tuple[int, str, str]:
    """在远程机器执行命令，返回 (exit_code, stdout, stderr)。"""
    cfg = cfg or load_config()
    client = get_client(cfg)
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=300)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        return exit_code, out, err
    finally:
        client.close()


# ── 快捷命令 ──────────────────────────────────────────────
SHORTCUTS = {
    "pytest": f"cd {DEFAULT_CONFIG['remote_dir']}/backend && python -m pytest -v --tb=short 2>&1",
    "pytest-auth": f"cd {DEFAULT_CONFIG['remote_dir']}/backend && python -m pytest tests/test_auth.py -v --tb=short 2>&1",
    "pytest-cases": f"cd {DEFAULT_CONFIG['remote_dir']}/backend && python -m pytest tests/test_cases.py -v --tb=short 2>&1",
    "pytest-tasks": f"cd {DEFAULT_CONFIG['remote_dir']}/backend && python -m pytest tests/test_tasks.py -v --tb=short 2>&1",
    "pytest-nodes": f"cd {DEFAULT_CONFIG['remote_dir']}/backend && python -m pytest tests/test_nodes.py -v --tb=short 2>&1",
    "pytest-system": f"cd {DEFAULT_CONFIG['remote_dir']}/backend && python -m pytest tests/test_system.py -v --tb=short 2>&1",
    "status": "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || echo 'Docker not running'; echo '---'; systemctl is-active postgresql 2>/dev/null || echo 'systemd pg not found'; redis-cli ping 2>/dev/null || echo 'redis not reachable'",
    "pip-install": f"cd {DEFAULT_CONFIG['remote_dir']}/backend && pip install -r requirements.txt -q 2>&1 | tail -5",
    "logs": f"cd {DEFAULT_CONFIG['remote_dir']} && ls -la data/logs/ 2>/dev/null || echo 'no logs dir'",
    "env": "uname -a; python3 --version 2>/dev/null; docker --version 2>/dev/null; echo '---'; df -h / | tail -1; free -h | head -2",
}


def main():
    cfg = load_config()

    if len(sys.argv) < 2:
        print("用法: python scripts/remote.py <命令|快捷命令>")
        print("\n快捷命令:")
        for name, cmd in SHORTCUTS.items():
            print(f"  {name:16s} {cmd[:60]}...")
        print(f"\nSSH: {cfg['user']}@{cfg['host']}:{cfg['port']}")
        return

    arg = sys.argv[1]

    # 保存配置
    save_config(cfg)

    # 快捷命令
    if arg in SHORTCUTS:
        cmd = SHORTCUTS[arg]
    elif arg == "shell":
        print(f"远程 Shell: {cfg['user']}@{cfg['host']}")
        print("输入 'exit' 退出\n")
        while True:
            try:
                cmd_input = input(f"{cfg['host']}$ ")
                if cmd_input.strip() in ("exit", "quit"):
                    break
                if not cmd_input.strip():
                    continue
                code, out, err = exec_remote(cmd_input, cfg)
                if out:
                    print(out, end="")
                if err:
                    print(err, end="", file=sys.stderr)
                if code != 0:
                    print(f"[exit code: {code}]")
            except (EOFError, KeyboardInterrupt):
                print()
                break
        return
    else:
        cmd = arg

    # 执行
    print(f">> {cmd}")
    print("-" * 60)
    code, out, err = exec_remote(cmd, cfg)
    if out:
        print(out, end="")
    if err:
        print(err, end="", file=sys.stderr)
    print("-" * 60)
    print(f"[exit code: {code}]")
    sys.exit(code)


if __name__ == "__main__":
    main()
