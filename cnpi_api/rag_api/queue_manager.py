"""
Queue Manager for Chat API - Concurrent User Limiting
======================================================
Limits active chat requests to 3 concurrent users.
Additional users are placed in a waiting queue.
"""

import time
from threading import Lock
from collections import OrderedDict
from typing import Optional, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class ChatQueueManager:
    """
    Thread-safe queue manager for limiting concurrent chat API requests.
    
    Features:
    - Max 3 active concurrent users
    - Automatic queue management
    - Position tracking for waiting users
    - Timeout handling for stale requests
    """
    
    # Maximum concurrent active users
    MAX_ACTIVE_USERS = 3
    
    # Request timeout (5 minutes - matches gunicorn timeout)
    REQUEST_TIMEOUT = 300
    
    def __init__(self):
        self._lock = Lock()
        # Active requests: {session_id: timestamp}
        self._active: OrderedDict[str, float] = OrderedDict()
        # Waiting queue: {session_id: timestamp}
        self._queue: OrderedDict[str, float] = OrderedDict()
    
    def can_proceed(self, session_id: str) -> Tuple[bool, Optional[int], Optional[int]]:
        """
        Check if a session can proceed with chat request.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Tuple of (can_proceed, queue_position, estimated_wait_seconds)
            - can_proceed: True if user can make request now
            - queue_position: Position in queue (None if can proceed)
            - estimated_wait_seconds: Estimated wait time (None if can proceed)
        """
        with self._lock:
            current_time = time.time()
            
            # Clean up stale requests
            self._cleanup_stale_requests(current_time)
            
            # Check if user is already active
            if session_id in self._active:
                # Update timestamp
                self._active[session_id] = current_time
                return (True, None, None)
            
            # Check if there's room for new active user
            if len(self._active) < self.MAX_ACTIVE_USERS:
                # Add to active requests
                self._active[session_id] = current_time
                logger.info(f"Session {session_id} added to active requests. Active: {len(self._active)}/{self.MAX_ACTIVE_USERS}")
                return (True, None, None)
            
            # User must wait - add to queue if not already there
            if session_id not in self._queue:
                self._queue[session_id] = current_time
                logger.info(f"Session {session_id} added to waiting queue. Queue length: {len(self._queue)}")
            
            # Calculate queue position and estimated wait time
            queue_position = list(self._queue.keys()).index(session_id) + 1
            
            # Estimate: each user takes ~30 seconds average
            # But check actual active request ages
            estimated_wait = self._estimate_wait_time(queue_position, current_time)
            
            return (False, queue_position, estimated_wait)
    
    def release(self, session_id: str):
        """
        Release a session from active requests.
        Automatically promotes next user from queue.
        
        Args:
            session_id: Session to release
        """
        with self._lock:
            # Remove from active
            if session_id in self._active:
                del self._active[session_id]
                logger.info(f"Session {session_id} released. Active: {len(self._active)}/{self.MAX_ACTIVE_USERS}")
            
            # Remove from queue if present
            if session_id in self._queue:
                del self._queue[session_id]
            
            # Promote next user from queue if available
            self._promote_from_queue()
    
    def get_status(self, session_id: str) -> Dict:
        """
        Get current queue status for a session.
        
        Returns:
            Dict with status information
        """
        with self._lock:
            current_time = time.time()
            self._cleanup_stale_requests(current_time)
            
            is_active = session_id in self._active
            in_queue = session_id in self._queue
            
            status = {
                'is_active': is_active,
                'in_queue': in_queue,
                'active_count': len(self._active),
                'queue_length': len(self._queue),
                'max_active': self.MAX_ACTIVE_USERS,
            }
            
            if in_queue:
                queue_position = list(self._queue.keys()).index(session_id) + 1
                estimated_wait = self._estimate_wait_time(queue_position, current_time)
                status['queue_position'] = queue_position
                status['estimated_wait_seconds'] = estimated_wait
            
            return status
    
    def _cleanup_stale_requests(self, current_time: float):
        """Remove requests that have exceeded timeout."""
        # Clean active requests
        stale_active = [
            sid for sid, timestamp in self._active.items()
            if current_time - timestamp > self.REQUEST_TIMEOUT
        ]
        for sid in stale_active:
            del self._active[sid]
            logger.warning(f"Removed stale active session: {sid}")
        
        # Clean queue (users who gave up waiting)
        stale_queue = [
            sid for sid, timestamp in self._queue.items()
            if current_time - timestamp > self.REQUEST_TIMEOUT * 2  # Allow longer wait
        ]
        for sid in stale_queue:
            del self._queue[sid]
            logger.warning(f"Removed stale queued session: {sid}")
        
        # Promote users if slots opened
        if stale_active:
            self._promote_from_queue()
    
    def _promote_from_queue(self):
        """Promote next user from queue to active if slots available."""
        while len(self._active) < self.MAX_ACTIVE_USERS and self._queue:
            # Get first user in queue
            next_session_id, timestamp = self._queue.popitem(last=False)
            self._active[next_session_id] = time.time()
            logger.info(f"Promoted session {next_session_id} from queue to active. Active: {len(self._active)}/{self.MAX_ACTIVE_USERS}")
    
    def _estimate_wait_time(self, queue_position: int, current_time: float) -> int:
        """
        Estimate wait time in seconds based on queue position and active request ages.
        
        Args:
            queue_position: Position in queue (1-indexed)
            current_time: Current timestamp
            
        Returns:
            Estimated wait time in seconds
        """
        if not self._active:
            return 0
        
        # Calculate average age of active requests
        active_ages = [current_time - ts for ts in self._active.values()]
        avg_age = sum(active_ages) / len(active_ages)
        
        # Assume each request takes 30-60 seconds on average
        # Use actual data if available, else default to 45 seconds
        estimated_request_duration = max(45 - avg_age, 10)  # At least 10 seconds
        
        # Calculate wait time: (position - 1) / max_active * duration
        # Example: position 4, max 3 → needs 1 slot to free → 1/3 * duration
        slots_needed = (queue_position - 1) // self.MAX_ACTIVE_USERS + 1
        estimated_wait = int(slots_needed * estimated_request_duration)
        
        # Cap at reasonable maximum
        return min(estimated_wait, 300)  # Max 5 minutes
    
    def reset(self):
        """Reset queue (for testing/admin purposes)."""
        with self._lock:
            self._active.clear()
            self._queue.clear()
            logger.info("Queue manager reset")


# Global singleton instance
_queue_manager = ChatQueueManager()


def get_queue_manager() -> ChatQueueManager:
    """Get the global queue manager instance."""
    return _queue_manager
