"""Task dispatcher - distributes tasks to available worker nodes."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.node import TestNode
from app.models.test_case import TestCase
from app.models.enums import NodeType, NodeStatus
from app.services.queue_manager import queue_manager

logger = logging.getLogger(__name__)

# Heartbeat threshold - consider node offline if no heartbeat for this duration
HEARTBEAT_THRESHOLD_SECONDS = 30


class TaskDispatcher:
    """Distributes tasks to available worker nodes with weighted load balancing."""

    async def find_available_nodes(
        self,
        db: AsyncSession,
        case_type: str,
    ) -> List[TestNode]:
        """Find nodes that can handle the given case type.

        A node is available if:
        - status is ONLINE
        - node_type matches case_type or is MIXED
        - current_tasks < max_concurrent
        - last_heartbeat is within threshold
        """
        # Determine which node types can handle this case
        if case_type == "UI":
            valid_types = [NodeType.PLAYWRIGHT, NodeType.MIXED]
        elif case_type == "PERFORMANCE":
            valid_types = [NodeType.LOCUST, NodeType.MIXED]
        else:  # API
            valid_types = [NodeType.MIXED]  # API tests run on mixed nodes

        # Calculate heartbeat threshold
        threshold = datetime.now(timezone.utc) - timedelta(
            seconds=HEARTBEAT_THRESHOLD_SECONDS
        )

        # Query available nodes
        query = (
            select(TestNode)
            .where(
                and_(
                    TestNode.deleted_at.is_(None),
                    TestNode.status == NodeStatus.ONLINE,
                    TestNode.node_type.in_([t.value for t in valid_types]),
                    TestNode.current_tasks < TestNode.max_concurrent,
                    TestNode.last_heartbeat_at >= threshold,
                )
            )
            .order_by(TestNode.current_tasks.asc())
        )

        result = await db.execute(query)
        nodes = result.scalars().all()

        logger.info(
            f"Found {len(nodes)} available nodes for case_type={case_type}"
        )
        return nodes

    def select_best_node(self, nodes: List[TestNode]) -> Optional[TestNode]:
        """Select the best node using weighted load balancing.

        Weight calculation:
        - CPU weight: 40% (lower CPU = higher weight)
        - Memory weight: 30% (lower memory = higher weight)
        - Task weight: 30% (fewer tasks = higher weight)
        """
        if not nodes:
            return None

        def calculate_weight(node: TestNode) -> float:
            # CPU weight (0-1, higher is better)
            cpu_usage = float(node.cpu_usage) if node.cpu_usage else 0
            cpu_weight = 1 - (cpu_usage / 100)

            # Memory weight (0-1, higher is better)
            mem_usage = float(node.memory_usage) if node.memory_usage else 0
            mem_weight = 1 - (mem_usage / 100)

            # Task weight (0-1, higher is better)
            task_ratio = node.current_tasks / node.max_concurrent if node.max_concurrent else 0
            task_weight = 1 - task_ratio

            # Combined weight
            return cpu_weight * 0.4 + mem_weight * 0.3 + task_weight * 0.3

        # Select node with highest weight
        best_node = max(nodes, key=calculate_weight)

        logger.info(
            f"Selected node {best_node.id} ({best_node.name}) "
            f"with weight score, CPU: {best_node.cpu_usage}%, "
            f"Memory: {best_node.memory_usage}%, "
            f"Tasks: {best_node.current_tasks}/{best_node.max_concurrent}"
        )
        return best_node

    async def dispatch_task(
        self,
        db: AsyncSession,
        task_id: str,
        case: TestCase,
        priority: int = 0,
    ) -> Dict[str, Any]:
        """Dispatch a task to an available worker node.

        Returns:
            Dict with dispatch info:
            - dispatched: bool
            - node_id: str (if dispatched)
            - queue_key: str (if dispatched)
        """
        # Find available nodes
        nodes = await self.find_available_nodes(db, case.type)

        if not nodes:
            logger.info(
                f"No available nodes for task {task_id}/{case.id}, "
                f"will execute locally"
            )
            return {"dispatched": False, "node_id": None, "queue_key": None}

        # Select best node
        selected_node = self.select_best_node(nodes)
        if not selected_node:
            return {"dispatched": False, "node_id": None, "queue_key": None}

        # Prepare case data for queue
        case_data = self._prepare_case_data(case)

        # Push task to Redis queue
        queue_key = await queue_manager.enqueue_task(
            task_id=task_id,
            case_id=str(case.id),
            case_type=case.type,
            case_data=case_data,
            priority=priority,
        )

        # Increment node task count in Redis
        await queue_manager.increment_node_tasks(str(selected_node.id))

        logger.info(
            f"Task {task_id}/{case.id} dispatched to node "
            f"{selected_node.id} ({selected_node.name}) via {queue_key}"
        )

        return {
            "dispatched": True,
            "node_id": str(selected_node.id),
            "node_name": selected_node.name,
            "queue_key": queue_key,
        }

    def _prepare_case_data(self, case: TestCase) -> Dict[str, Any]:
        """Prepare case data for transmission to worker node."""
        data = {
            "id": str(case.id),
            "name": case.name,
            "type": case.type,
        }

        if case.type == "UI":
            data.update({
                "ui_script": case.ui_script,
                "ui_screenshots": case.ui_screenshots,
            })
        elif case.type == "PERFORMANCE":
            data.update({
                "perf_script": case.perf_script,
                "perf_url": case.perf_url,
                "perf_vusers": case.perf_vusers or 10,
                "perf_spawn_rate": case.perf_spawn_rate or 1,
                "perf_duration": case.perf_duration or 60,
                "perf_assertions": case.perf_assertions,
            })
        elif case.type == "API":
            data.update({
                "api_url": case.api_url,
                "api_method": case.api_method,
                "api_headers": case.api_headers,
                "api_body": case.api_body,
                "api_body_type": case.api_body_type,
                "api_timeout": case.api_timeout,
                "api_assertions": case.api_assertions,
            })

        return data

    async def wait_for_result(
        self,
        task_id: str,
        case_id: str,
        timeout: int = 600,
    ) -> Optional[Dict[str, Any]]:
        """Wait for a task result from a worker node.

        Polls Redis for the result with exponential backoff.
        """
        import asyncio

        start_time = datetime.now(timezone.utc)
        poll_interval = 0.5  # Start with 500ms
        max_interval = 5.0  # Max 5 seconds

        while True:
            # Check timeout
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if elapsed >= timeout:
                logger.warning(
                    f"Timeout waiting for result: {task_id}/{case_id}"
                )
                return None

            # Check for result
            result = await queue_manager.get_task_result(task_id, case_id)
            if result:
                # Decrement node task count
                node_id = result.get("node_id")
                if node_id:
                    await queue_manager.decrement_node_tasks(node_id)
                return result

            # Wait before next poll
            await asyncio.sleep(poll_interval)

            # Exponential backoff
            poll_interval = min(poll_interval * 1.5, max_interval)


# Module-level singleton
task_dispatcher = TaskDispatcher()
