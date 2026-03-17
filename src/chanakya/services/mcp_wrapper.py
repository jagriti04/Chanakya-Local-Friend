"""
MCP (Model Context Protocol) wrapper for subprocess communication.

Handles stdin/stdout forwarding to MCP tools. For internal use only.
"""

import json
import subprocess
import sys
import threading


def forward_stdin(proc):
    """Forward stdin lines to the subprocess until EOF."""
    try:
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            proc.stdin.write(line)
            proc.stdin.flush()
    except Exception:
        pass
    proc.stdin.close()


def main():
    """Entry point: wrap a subcommand and forward I/O."""
    if len(sys.argv) < 2:
        sys.exit("Usage: mcp_wrapper.py <command> [args...]")

    cmd = sys.argv[1:]
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,  # Forward stderr directly
        text=True,
        bufsize=1,
    )

    t = threading.Thread(target=forward_stdin, args=(proc,), daemon=True)
    t.start()

    try:
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            line_stripped = line.strip()
            if not line_stripped:
                continue

            if line_stripped.startswith("{"):
                try:
                    # Quick check if it's remotely valid JSON before forwarding
                    json.loads(line_stripped)
                    sys.stdout.write(line)
                    sys.stdout.flush()
                    continue
                except ValueError:
                    pass

            # If we get here, it's not JSON, so we forward to stderr to hide it from MCP SDK
            sys.stderr.write(f"[mcp_wrapper/{cmd[0]}] {line}")
            sys.stderr.flush()
    except Exception:
        pass
    proc.wait()


if __name__ == "__main__":
    main()
