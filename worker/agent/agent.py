"""Worker Agent - handles registration, heartbeats, and task consumption."""

import asyncio
import json
import logging
import os
import platform
import socket
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import httpx
import redis.asyncio as redis

from .executors import PlaywrightExecutor, LocustExecutor, ApiExecutor
from .metrics import MetricsCollector

logger = logging.getLogger(__name__)

# Redis keys
QUEUE_UI_PENDING = "queue:ui:pending"
QUEUE_PERF_PENDING = "queue:perf:pending"
QUEUE_API_PENDING = "queue:api:pending"
NODE_HEARTBEAT_PREFIX = "node:heartbeat:"
NODE_TASKS_PREFIX = "node:tasks:"
TASK_RESULT_PREFIX = "task:result:"


class WorkerAgent:
    """Worker agent that runs on remote nodes and executes test tasks."""

    def __init__(
        self,
        backend_url: str,
        node_type: str = "MIXED",
        api_key: str = "",
        node_name: str = "",
        heartbeat_interval: int = 10,
        max_concurrent: int = 5,
    ):
        self.backend_url = backend_url.rstrip("/")
        self.node_type = node_type
        self.api_key = api_key
        self.node_name = node_name or f"{platform.node()}-{os.getpid()}"
        self.heartbeat_interval = heartbeat_interval
        self.max_concurrent = max_concurrent

        self.node_id: Optional[str] = None
        self.running = False
        self.current_tasks = 0

        # Components
        self.metrics = MetricsCollector()
        self.redis: Optional[redis.Redis] = None
        self.http_client: Optional[httpx.AsyncClient] = None

        # Executors
        self.executors = {
            "UI": PlaywrightExecutor(),
            "PERFORMANCE": LocustExecutor(),
            "API": ApiExecutor(),
        }

        # Task slots
        self._task_slots = asyncio.Semaphore(max_concurrent)

    async def start(self):
        """Start the agent: register, connect Redis, start loops."""
        self.running = True
        self.http_client = httpx.AsyncClient(timeout=30.0)

        # Get Redis URL from environment or derive from backend URL
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        self.redis = redis.from_url(redis_url, decode_responses=True)

        try:
            # Register with backend
            await self._register()

            # Start background tasks
            await asyncio.gather(
                self._heartbeat_loop(),
                self._task_consumer_loop(),
                self._health_check_loop(),
            )
        except asyncio.CancelledError:
            logger.info("Agent tasks cancelled")
        except Exception as e:
            logger.error(f"Agent error: {e}")
            raise

    async def stop(self):
        """Stop the agent gracefully."""
        logger.info("Stopping agent...")
        self.running = False

        # Update status to offline
        if self.node_id and self.http_client:
            try:
                await self.http_client.post(
                    f"{self.backend_url}/api/v1/nodes/{self.node_id}/heartbeat",
                    json={"status": "OFFLINE"},
                    headers=self._auth_headers(),
                )
            except Exception:
                pass

        # Close connections
        if self.http_client:
            await self.http_client.aclose()
        if self.redis:
            await self.redis.close()

        logger.info("Agent stopped")

    def _auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def _register(self):
        """Register with the backend server."""
        logger.info(f"Registering with backend at {self.backend_url}")

        # Get local IP address
        host = self._get_local_ip()

        registration_data = {
            "name": self.node_name,
            "host": host,
            "port": 8080,  # Agent doesn't serve HTTP, but field is required
            "node_type": self.node_type,
            "capabilities": {
                "playwright": self.node_type in ("PLAYWRIGHT", "MIXED"),
                "locust": self.node_type in ("LOCUST", "MIXED"),
                "max_concurrent": self.max_concurrent,
            },
            "agent_version": "1.0.0",
        }

        try:
            # Try auto-register first
            response = await self.http_client.post(
                f"{self.backend_url}/api/v1/nodes/auto-register",
                json=registration_data,
                headers=self._auth_headers(),
            )

            if response.status_code == 201:
                data = response.json().get("data", {})
                self.node_id = data.get("id")
                self.api_key = data.get("api_key", self.api_key)
                logger.info(f"Registered successfully. Node ID: {self.node_id}")
            else:
                logger.error(f"Registration failed: {response.status_code} - {response.text}")
                raise RuntimeError(f"Registration failed: {response.status_code}")

        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to backend: {e}")
            raise

    def _get_local_ip(self) -> str:
        """Get the local IP address."""
        try:
            # Connect to a remote address to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    async def _heartbeat_loop(self):
        """Send heartbeat to backend periodically."""
        while self.running:
            try:
                metrics = self.metrics.collect()
                metrics["current_tasks"] = self.current_tasks

                # Update Redis heartbeat
                heartbeat_key = f"{NODE_HEARTBEAT_PREFIX}{self.node_id}"
                await self.redis.setex(
                    heartbeat_key,
                    self.heartbeat_interval * 3,  # TTL = 3x heartbeat interval
                    json.dumps({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        **metrics,
                    }),
                )

                # Update Redis task count
                tasks_key = f"{NODE_TASKS_PREFIX}{self.node_id}"
                await self.redis.set(tasks_key, str(self.current_tasks))

                # Send heartbeat to backend
                if self.http_client:
                    await self.http_client.post(
                        f"{self.backend_url}/api/v1/nodes/{self.node_id}/heartbeat",
                        json=metrics,
                        headers=self._auth_headers(),
                    )

            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")

            await asyncio.sleep(self.heartbeat_interval)

    async def _task_consumer_loop(self):
        """Consume tasks from Redis queue."""
        logger.info(f"Task consumer started (type={self.node_type})")

        while self.running:
            try:
                # Check if we have available slots
                if self.current_tasks >= self.max_concurrent:
                    await asyncio.sleep(1)
                    continue

                # Try to dequeue a task
                task_data = await self._dequeue_task()

                if task_data:
                    # Execute task in background
                    asyncio.create_task(self._execute_task_wrapper(task_data))
                else:
                    # No tasks available, wait before retrying
                    await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Task consumer error: {e}")
                await asyncio.sleep(1)

    async def _dequeue_task(self) -> Optional[Dict[str, Any]]:
        """Try to dequeue a task from Redis."""
        # Determine which queues to check
        if self.node_type == "PLAYWRIGHT":
            queues = [QUEUE_UI_PENDING]
        elif self.node_type == "LOCUST":
            queues = [QUEUE_PERF_PENDING]
        else:  # MIXED
            queues = [QUEUE_UI_PENDING, QUEUE_PERF_PENDING, QUEUE_API_PENDING]

        for queue_key in queues:
            result = await self.redis.rpop(queue_key)
            if result:
                task_data = json.loads(result)
                task_data["node_id"] = self.node_id
                return task_data

        return None

    async def _execute_task_wrapper(self, task_data: Dict[str, Any]):
        """Wrapper for task execution with error handling and result reporting."""
        async with self._task_slots:
            self.current_tasks += 1
            task_id = task_data.get("task_id", "unknown")
            case_id = task_data.get("case_id", "unknown")

            try:
                logger.info(f"Executing task {task_id}/{case_id}")

                # Get the appropriate executor
                case_type = task_data.get("case_type", "API")
                executor = self.executors.get(case_type)
                if not executor:
                    raise ValueError(f"Unknown case type: {case_type}")

                # Execute the task
                result = await executor.execute(task_data.get("case_data", {}))

                # Store result in Redis
                result_data = {
                    "task_id": task_id,
                    "case_id": case_id,
                    "node_id": self.node_id,
                    "status": result.get("status", "FAILED"),
                    "detail": result.get("detail", {}),
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }

                result_key = f"{TASK_RESULT_PREFIX}{task_id}:{case_id}"
                await self.redis.setex(
                    result_key,
                    3600,  # TTL 1 hour
                    json.dumps(result_data),
                )

                logger.info(f"Task {task_id}/{case_id} completed: {result.get('status')}")

            except Exception as e:
                logger.error(f"Task {task_id}/{case_id} failed: {e}")

                # Store error result
                result_data = {
                    "task_id": task_id,
                    "case_id": case_id,
                    "node_id": self.node_id,
                    "status": "FAILED",
                    "detail": {"error": str(e)},
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }

                result_key = f"{TASK_RESULT_PREFIX}{task_id}:{case_id}"
                await self.redis.setex(
                    result_key,
                    3600,
                    json.dumps(result_data),
                )

            finally:
                self.current_tasks -= 1

    async def _health_check_loop(self):
        """Periodic health check and self-healing."""
        while self.running:
            try:
                # Check Redis connection
                await self.redis.ping()

                # Check if we're still registered
                if self.node_id and self.http_client:
                    response = await self.http_client.get(
                        f"{self.backend_url}/api/v1/nodes/{self.node_id}",
                        headers=self._auth_headers(),
                    )
                    if response.status_code == 404:
                        logger.warning("Node not found in backend, re-registering...")
                        await self._register()

            except Exception as e:
                logger.warning(f"Health check failed: {e}")

            await asyncio.sleep(60)  # Check every minute
