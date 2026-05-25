"""Worker Agent main entry point."""

import asyncio
import logging
import os
import signal
import sys

from .agent import WorkerAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point for the worker agent."""
    # Get configuration from environment
    backend_url = os.environ.get("BACKEND_URL", "http://localhost:8000")
    node_type = os.environ.get("NODE_TYPE", "MIXED")
    api_key = os.environ.get("API_KEY", "")
    node_name = os.environ.get("NODE_NAME", "")
    heartbeat_interval = int(os.environ.get("HEARTBEAT_INTERVAL", "10"))
    max_concurrent = int(os.environ.get("MAX_CONCURRENT", "5"))

    # Validate configuration
    if not backend_url:
        logger.error("BACKEND_URL environment variable is required")
        return 1

    # Create agent
    agent = WorkerAgent(
        backend_url=backend_url,
        node_type=node_type,
        api_key=api_key,
        node_name=node_name,
        heartbeat_interval=heartbeat_interval,
        max_concurrent=max_concurrent,
    )

    # Handle shutdown signals
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(agent.stop()))

    try:
        logger.info(f"Starting worker agent (type={node_type}, max_concurrent={max_concurrent})")
        await agent.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Agent error: {e}")
        return 1
    finally:
        await agent.stop()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
