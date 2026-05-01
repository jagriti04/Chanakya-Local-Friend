"""
Client activity tracking for connection monitoring.

Manages active_clients dict and periodic cleanup of inactive sessions.
"""

import threading
import time

from .. import config

INACTIVE_THRESHOLD = config.CLIENT_INACTIVE_THRESHOLD
SAVE_INTERVAL = config.CLIENT_SAVE_INTERVAL
COUNT_FILE = config.CLIENT_COUNT_FILE
active_clients = {}
client_count_lock = threading.Lock()


def update_client_activity(client_id):
    """Record activity for a client by updating their last active timestamp."""
    with client_count_lock:
        active_clients[client_id] = time.time()


def remove_inactive_clients():
    """Remove clients that have been inactive beyond INACTIVE_THRESHOLD."""
    current_time = time.time()
    with client_count_lock:
        inactive_ids = [
            cid for cid, la in active_clients.items() if current_time - la > INACTIVE_THRESHOLD
        ]
        for cid in inactive_ids:
            del active_clients[cid]
