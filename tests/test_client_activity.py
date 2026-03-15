"""
Tests for src/chanakya/web/client_activity.py

Focus: update_client_activity, remove_inactive_clients,
thread-safety, and inactive threshold logic.
"""

import os
import sys
import time
import threading
import unittest
from unittest.mock import patch


def _clean_chanakya_modules():
    for key in list(sys.modules.keys()):
        if 'chanakya' in key:
            del sys.modules[key]


class TestUpdateClientActivity(unittest.TestCase):
    """Tests for update_client_activity."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('APP_SECRET_KEY', 'test-client-activity')
        os.environ.setdefault('FLASK_DEBUG', 'True')
        os.environ.setdefault('DATABASE_PATH', ':memory:')
        os.environ.setdefault('LLM_PROVIDER', 'ollama')

    def setUp(self):
        _clean_chanakya_modules()
        from src.chanakya.web.client_activity import (
            update_client_activity,
            active_clients,
        )
        self.update = update_client_activity
        self.clients = active_clients
        self.clients.clear()

    def test_new_client_added(self):
        """Calling update should add the client ID to active_clients."""
        self.update('192.168.1.1')
        self.assertIn('192.168.1.1', self.clients)

    def test_timestamp_updated(self):
        """Calling update twice should update the timestamp."""
        self.update('client-1')
        first_time = self.clients['client-1']
        time.sleep(0.01)
        self.update('client-1')
        second_time = self.clients['client-1']
        self.assertGreaterEqual(second_time, first_time)

    def test_multiple_clients_tracked(self):
        """Multiple clients should all appear in active_clients."""
        for i in range(5):
            self.update(f'client-{i}')
        self.assertEqual(len(self.clients), 5)


class TestRemoveInactiveClients(unittest.TestCase):
    """Tests for remove_inactive_clients."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('APP_SECRET_KEY', 'test-client-activity')
        os.environ.setdefault('FLASK_DEBUG', 'True')
        os.environ.setdefault('DATABASE_PATH', ':memory:')
        os.environ.setdefault('LLM_PROVIDER', 'ollama')
        os.environ.setdefault('CLIENT_INACTIVE_THRESHOLD', '1')

    def setUp(self):
        _clean_chanakya_modules()
        from src.chanakya.web.client_activity import (
            update_client_activity,
            remove_inactive_clients,
            active_clients,
        )
        self.update = update_client_activity
        self.remove = remove_inactive_clients
        self.clients = active_clients
        self.clients.clear()

    def test_active_clients_not_removed(self):
        """Clients with recent activity should NOT be removed."""
        self.update('active-client')
        self.remove()
        self.assertIn('active-client', self.clients)

    def test_inactive_clients_removed(self):
        """Clients older than INACTIVE_THRESHOLD should be removed."""
        # Manually set an old timestamp
        self.clients['stale-client'] = time.time() - 100
        self.remove()
        self.assertNotIn('stale-client', self.clients)

    def test_mixed_active_and_inactive(self):
        """Only inactive clients should be removed from a mixed set."""
        self.update('active-1')
        self.clients['stale-1'] = time.time() - 100
        self.clients['stale-2'] = time.time() - 200
        self.update('active-2')

        self.remove()

        self.assertIn('active-1', self.clients)
        self.assertIn('active-2', self.clients)
        self.assertNotIn('stale-1', self.clients)
        self.assertNotIn('stale-2', self.clients)

    def test_empty_dict_no_error(self):
        """Calling remove on an empty dict should not raise."""
        self.clients.clear()
        self.remove()  # Should not raise
        self.assertEqual(len(self.clients), 0)


class TestClientActivityThreadSafety(unittest.TestCase):
    """Basic thread-safety test for the client_activity module."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('APP_SECRET_KEY', 'test-client-activity')
        os.environ.setdefault('FLASK_DEBUG', 'True')
        os.environ.setdefault('DATABASE_PATH', ':memory:')
        os.environ.setdefault('LLM_PROVIDER', 'ollama')

    def setUp(self):
        _clean_chanakya_modules()

    def test_concurrent_updates_dont_crash(self):
        """Multiple threads updating concurrently should not raise."""
        from src.chanakya.web.client_activity import (
            update_client_activity,
            active_clients,
        )
        active_clients.clear()
        errors = []

        def worker(cid):
            try:
                for _ in range(50):
                    update_client_activity(cid)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(f'c-{i}',)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(active_clients), 10)


if __name__ == '__main__':
    unittest.main()
