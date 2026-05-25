"""System metrics collector for worker agent."""

import logging
import os
import platform
from typing import Dict, Any

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects system metrics (CPU, memory, disk usage)."""

    def __init__(self):
        self._psutil = None
        self._try_import_psutil()

    def _try_import_psutil(self):
        """Try to import psutil for metrics collection."""
        try:
            import psutil
            self._psutil = psutil
        except ImportError:
            logger.warning("psutil not installed, metrics collection will be limited")

    def collect(self) -> Dict[str, Any]:
        """Collect current system metrics."""
        metrics = {
            "hostname": platform.node(),
            "platform": platform.system(),
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "disk_usage": 0.0,
        }

        if self._psutil:
            try:
                # CPU usage (average across all cores)
                metrics["cpu_usage"] = self._psutil.cpu_percent(interval=0.1)

                # Memory usage
                memory = self._psutil.virtual_memory()
                metrics["memory_usage"] = memory.percent

                # Disk usage (root partition)
                disk = self._psutil.disk_usage("/")
                metrics["disk_usage"] = disk.percent

            except Exception as e:
                logger.warning(f"Failed to collect metrics: {e}")
        else:
            # Fallback: try to read from /proc on Linux
            metrics.update(self._collect_linux_metrics())

        return metrics

    def _collect_linux_metrics(self) -> Dict[str, float]:
        """Fallback metrics collection for Linux without psutil."""
        metrics = {}

        try:
            # CPU usage from /proc/stat
            if os.path.exists("/proc/stat"):
                with open("/proc/stat", "r") as f:
                    line = f.readline()
                    parts = line.split()
                    # user, nice, system, idle, iowait, irq, softirq
                    total = sum(int(p) for p in parts[1:])
                    idle = int(parts[4])
                    # Simple approximation
                    metrics["cpu_usage"] = round((1 - idle / total) * 100, 2) if total > 0 else 0.0

            # Memory usage from /proc/meminfo
            if os.path.exists("/proc/meminfo"):
                with open("/proc/meminfo", "r") as f:
                    lines = f.readlines()
                    mem_info = {}
                    for line in lines[:5]:  # Only need first few lines
                        parts = line.split(":")
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = int(parts[1].strip().split()[0])
                            mem_info[key] = value

                    if "MemTotal" in mem_info and "MemAvailable" in mem_info:
                        total = mem_info["MemTotal"]
                        available = mem_info["MemAvailable"]
                        metrics["memory_usage"] = round((1 - available / total) * 100, 2) if total > 0 else 0.0

            # Disk usage using statvfs
            try:
                stat = os.statvfs("/")
                total = stat.f_blocks * stat.f_frsize
                free = stat.f_bfree * stat.f_frsize
                metrics["disk_usage"] = round((1 - free / total) * 100, 2) if total > 0 else 0.0
            except Exception:
                pass

        except Exception as e:
            logger.warning(f"Failed to collect Linux metrics: {e}")

        return metrics
