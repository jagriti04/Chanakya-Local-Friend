"""
Tests for src/chanakya/services/mcp_wrapper.py

Focus: JSON filtering logic — valid JSON passes through stdout,
non-JSON messages are diverted to stderr.
"""

import io
import json
import sys
import subprocess
import os
import tempfile
import unittest


WRAPPER_PATH = os.path.join(
    os.path.dirname(__file__),
    '..', 'src', 'chanakya', 'services', 'mcp_wrapper.py',
)
WRAPPER_PATH = os.path.abspath(WRAPPER_PATH)


class TestMcpWrapperFiltering(unittest.TestCase):
    """Test that the wrapper correctly filters stdout lines."""

    def _run_wrapper(self, child_script_content: str, timeout: int = 10):
        """
        Helper: write a temporary Python child script, run the wrapper
        around it, and return (stdout, stderr).
        """
        with tempfile.NamedTemporaryFile(
            suffix='.py', mode='w', delete=False
        ) as f:
            f.write(child_script_content)
            child_path = f.name

        try:
            proc = subprocess.run(
                [sys.executable, WRAPPER_PATH, sys.executable, child_path],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return proc.stdout, proc.stderr, proc.returncode
        finally:
            os.unlink(child_path)

    def test_valid_json_passes_through_stdout(self):
        """Valid JSON lines should appear on stdout."""
        child = 'import json, sys; print(json.dumps({"jsonrpc":"2.0","id":1})); sys.stdout.flush()'
        stdout, stderr, _ = self._run_wrapper(child)
        self.assertIn('"jsonrpc"', stdout)
        parsed = json.loads(stdout.strip())
        self.assertEqual(parsed['jsonrpc'], '2.0')

    def test_non_json_diverted_to_stderr(self):
        """Non-JSON lines should be diverted to stderr and NOT appear on stdout."""
        child = 'import sys; print("This server is running on stdio"); sys.stdout.flush()'
        stdout, stderr, _ = self._run_wrapper(child)
        self.assertEqual(stdout.strip(), '')
        self.assertIn('This server is running on stdio', stderr)

    def test_mixed_output_filtered_correctly(self):
        """With a mix of JSON and non-JSON lines, only JSON appears on stdout."""
        child = (
            'import json, sys\n'
            'print("Starting up...")\n'
            'sys.stdout.flush()\n'
            'print(json.dumps({"jsonrpc":"2.0","method":"init"}))\n'
            'sys.stdout.flush()\n'
            'print("Ready")\n'
            'sys.stdout.flush()\n'
            'print(json.dumps({"jsonrpc":"2.0","id":2,"result":"ok"}))\n'
            'sys.stdout.flush()\n'
        )
        stdout, stderr, _ = self._run_wrapper(child)

        stdout_lines = [l for l in stdout.strip().split('\n') if l.strip()]
        self.assertEqual(len(stdout_lines), 2)

        for line in stdout_lines:
            parsed = json.loads(line)
            self.assertEqual(parsed['jsonrpc'], '2.0')

        self.assertIn('Starting up', stderr)
        self.assertIn('Ready', stderr)

    def test_empty_lines_ignored(self):
        """Empty / whitespace-only lines should be silently dropped."""
        child = (
            'import sys\n'
            'print("")\n'
            'print("   ")\n'
            'print("")\n'
            'sys.stdout.flush()\n'
        )
        stdout, stderr, _ = self._run_wrapper(child)
        self.assertEqual(stdout.strip(), '')

    def test_invalid_json_diverted_to_stderr(self):
        """A line starting with '{' but containing invalid JSON should go to stderr."""
        child = 'print("{not valid json}"); import sys; sys.stdout.flush()'
        stdout, stderr, _ = self._run_wrapper(child)
        self.assertEqual(stdout.strip(), '')
        self.assertIn('{not valid json}', stderr)

    def test_json_array_line_passes_through(self):
        """A valid JSON array should NOT pass through (only objects starting with '{' are checked)."""
        child = 'import json, sys; print(json.dumps([1,2,3])); sys.stdout.flush()'
        stdout, stderr, _ = self._run_wrapper(child)
        # The wrapper only checks for lines starting with '{', so arrays go to stderr
        self.assertEqual(stdout.strip(), '')

    def test_no_args_returns_error(self):
        """Running the wrapper with no arguments should exit with an error."""
        proc = subprocess.run(
            [sys.executable, WRAPPER_PATH],
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertNotEqual(proc.returncode, 0)


class TestMcpWrapperStdinForwarding(unittest.TestCase):
    """Test that stdin is correctly forwarded to the child process."""

    def test_stdin_forwarded_to_child(self):
        """Data sent to wrapper's stdin should reach the child process."""
        child_content = (
            'import sys, json\n'
            'line = sys.stdin.readline()\n'
            'print(json.dumps({"echo": line.strip()}))\n'
            'sys.stdout.flush()\n'
        )

        with tempfile.NamedTemporaryFile(
            suffix='.py', mode='w', delete=False
        ) as f:
            f.write(child_content)
            child_path = f.name

        try:
            proc = subprocess.run(
                [sys.executable, WRAPPER_PATH, sys.executable, child_path],
                input='hello from stdin\n',
                capture_output=True,
                text=True,
                timeout=10,
            )
            parsed = json.loads(proc.stdout.strip())
            self.assertEqual(parsed['echo'], 'hello from stdin')
        finally:
            os.unlink(child_path)


if __name__ == '__main__':
    unittest.main()
