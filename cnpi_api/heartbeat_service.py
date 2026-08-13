"""
Heartbeat service to keep the server alive.
"""
import os
import logging
import requests
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

HEARTBEAT_URL = os.getenv("HEARTBEAT_TARGET_URL")


def send_heartbeat(target_url: Optional[str] = None) -> bool:
    """
    Send a heartbeat ping to a target URL.

    Args:
        target_url: URL to ping. If not provided, uses HEARTBEAT_TARGET_URL env var.

    Returns:
        True if request succeeded, False otherwise.
    """
    url = target_url or HEARTBEAT_URL
    if not url:
        logger.warning("HEARTBEAT_TARGET_URL not configured. Skipping heartbeat.")
        return False

    try:
        logger.info(f"Sending heartbeat to {url} at {datetime.now()}")
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        logger.info(f"Heartbeat successful. Status: {response.status_code}")
        return True
    except Exception as e:
        logger.error(f"Heartbeat failed: {e}")
        return False


if __name__ == "__main__":
    import os
    send_heartbeat()