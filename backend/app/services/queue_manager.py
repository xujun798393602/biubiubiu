"""Redis-based task queue manager for distributed task execution."""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import redis.asyncio as redis

from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)

# Queue keys
QUEUE_UI_PENDING = "queue:ui:pending"
QUEUE_PERF_PENDING = "queue:perf:pending"
QUEUE_API_PENDING = "queue:api:pending"

# Node keys
NODE_HEARTBEAT_PREFIX = "node:heartbeat:"
NODE_TASKS_PREFIX = "node:tasks:"
NODE_STATUS_PREFIX = "node:status:"

# Task keys
TASK_DATA_PREFIX = "task:data:"
TASK_RESULT_PREFIX = "task:result:"
TASK_NODE_PREFIX = "task:node:"

# TTL settings
HEARTBEAT_TTL = 30  # seconds
TASK_DATA_TTL = 3600  # 1 hour
TASK_RESULT_TTL = 86400  # 24 hours


class QueueManager:
    """Manages task queues and node state in Redis."""

    def __init__(self):
        self._redis: Optional[redis.Redis] = None

    @property
    def redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = get_redis_client()
        return self._redis

    # ── Task Queue Operations ──────────────────────────────────────

    async def enqueue_task(
        self,
        task_id: str,
        case_id: str,
        case_type: str,
        case_data: Dict[str, Any],
        priority: int = 0,
    ) -> str:
        """Push a task to the appropriate queue.

        Returns the queue key the task was pushed to.
        """
        task_data = {
            "task_id": task_id,
            "case_id": case_id,
            "case_type": case_type,
            "case_data": case_data,
            "priority": priority,
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        }

        # Store task data
        data_key = f"{TASK_DATA_PREFIX}{task_id}:{case_id}"
        await self.redis.setex(data_key, TASK_DATA_TTL, json.dumps(task_data))

        # Select queue based on case type
        if case_type == "UI":
            queue_key = QUEUE_UI_PENDING
        elif case_type == "PERFORMANCE":
            queue_key = QUEUE_PERF_PENDING
        else:
            queue_key = QUEUE_API_PENDING

        # Push to queue (left push = high priority at front)
        await self.redis.lpush(queue_key, json.dumps(task_data))

        logger.info(f"Task {task_id}/{case_id} enqueued to {queue_key}")
        return queue_key

    async def dequeue_task(
        self, node_type: str, node_id: str
    ) -> Optional[Dict[str, Any]]:
        """Pop a task from the appropriate queue for the given node type.

        Returns None if no tasks are available.
        """
        # Determine which queues this node can consume
        if node_type == "PLAYWRIGHT":
            queues = [QUEUE_UI_PENDING]
        elif node_type == "LOCUST":
            queues = [QUEUE_PERF_PENDING]
        else:  # MIXED
            queues = [QUEUE_UI_PENDING, QUEUE_PERF_PENDING, QUEUE_API_PENDING]

        # Try each queue
        for queue_key in queues:
            # Use BRPOPLPUSH for atomic pop with backup
            result = await self.redis.rpop(queue_key)
            if result:
                task_data = json.loads(result)
                task_data["status"] = "dispatched"
                task_data["node_id"] = node_id
                task_data["dispatched_at"] = datetime.now(timezone.utc).isoformat()

                # Record task assignment
                task_key = f"{TASK_NODE_PREFIX}{task_data['task_id']}:{task_data['case_id']}"
                await self.redis.setex(task_key, TASK_DATA_TTL, node_id)

                logger.info(
                    f"Task {task_data['task_id']}/{task_data['case_id']} "
                    f"dispatched to node {node_id}"
                )
                return task_data

        return None

    async def get_queue_depth(self, case_type: Optional[str] = None) -> Dict[str, int]:
        """Get the number of pending tasks in each queue."""
        if case_type:
            if case_type == "UI":
                return {"UI": await self.redis.llen(QUEUE_UI_PENDING)}
            elif case_type == "PERFORMANCE":
                return {"PERFORMANCE": await self.redis.llen(QUEUE_PERF_PENDING)}
            else:
                return {"API": await self.redis.llen(QUEUE_API_PENDING)}

        return {
            "UI": await self.redis.llen(QUEUE_UI_PENDING),
            "PERFORMANCE": await self.redis.llen(QUEUE_PERF_PENDING),
            "API": await self.redis.llen(QUEUE_API_PENDING),
        }

    # ── Task Result Operations ─────────────────────────────────────

    async def store_task_result(
        self,
        task_id: str,
        case_id: str,
        result: Dict[str, Any],
    ) -> None:
        """Store the result of a task execution."""
        result_key = f"{TASK_RESULT_PREFIX}{task_id}:{case_id}"
        result_data = {
            **result,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.redis.setex(result_key, TASK_RESULT_TTL, json.dumps(result_data))

        # Clean up task assignment
        task_key = f"{TASK_NODE_PREFIX}{task_id}:{case_id}"
        await self.redis.delete(task_key)

        logger.info(f"Task result stored: {task_id}/{case_id}")

    async def get_task_result(
        self, task_id: str, case_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get the result of a task execution."""
        result_key = f"{TASK_RESULT_PREFIX}{task_id}:{case_id}"
        result = await self.redis.get(result_key)
        return json.loads(result) if result else None

    # ── Node State Operations ──────────────────────────────────────

    async def update_node_heartbeat(
        self,
        node_id: str,
        metrics: Dict[str, Any],
    ) -> None:
        """Update node heartbeat and metrics."""
        heartbeat_key = f"{NODE_HEARTBEAT_PREFIX}{node_id}"
        heartbeat_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cpu_usage": metrics.get("cpu_usage", 0),
            "memory_usage": metrics.get("memory_usage", 0),
            "disk_usage": metrics.get("disk_usage", 0),
        }
        await self.redis.setex(
            heartbeat_key, HEARTBEAT_TTL, json.dumps(heartbeat_data)
        )

    async def is_node_alive(self, node_id: str) -> bool:
        """Check if a node is alive (has recent heartbeat)."""
        heartbeat_key = f"{NODE_HEARTBEAT_PREFIX}{node_id}"
        return await self.redis.exists(heartbeat_key) > 0

    async def get_node_heartbeat(
        self, node_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get the last heartbeat data for a node."""
        heartbeat_key = f"{NODE_HEARTBEAT_PREFIX}{node_id}"
        data = await self.redis.get(heartbeat_key)
        return json.loads(data) if data else None

    async def increment_node_tasks(self, node_id: str) -> int:
        """Increment the task count for a node."""
        tasks_key = f"{NODE_TASKS_PREFIX}{node_id}"
        return await self.redis.incr(tasks_key)

    async def decrement_node_tasks(self, node_id: str) -> int:
        """Decrement the task count for a node."""
        tasks_key = f"{NODE_TASKS_PREFIX}{node_id}"
        count = await self.redis.decr(tasks_key)
        return max(0, count)

    async def get_node_task_count(self, node_id: str) -> int:
        """Get the current task count for a node."""
        tasks_key = f"{NODE_TASKS_PREFIX}{node_id}"
        count = await self.redis.get(tasks_key)
        return int(count) if count else 0

    # ── Utility Methods ────────────────────────────────────────────

    async def get_all_online_nodes(self) -> list[str]:
        """Get all node IDs that have recent heartbeats."""
        pattern = f"{NODE_HEARTBEAT_PREFIX}*"
        keys = []
        async for key in self.redis.scan_iter(match=pattern):
            node_id = key.replace(NODE_HEARTBEAT_PREFIX, "")
            keys.append(node_id)
        return keys

    async def cleanup_expired(self) -> int:
        """Clean up expired task data and results."""
        cleaned = 0

        # Clean up old task data
        pattern = f"{TASK_DATA_PREFIX}*"
        async for key in self.redis.scan_iter(match=pattern):
            ttl = await self.redis.ttl(key)
            if ttl == -1:  # No TTL set
                await self.redis.delete(key)
                cleaned += 1

        return cleaned


# Module-level singleton
queue_manager = QueueManager()
