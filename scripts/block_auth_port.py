#!/usr/bin/env python3
"""
block_auth_port.py
------------------
Simulates a blocked/occupied OAuth callback port (default: 4721) so you can
test the "Unable to upload" error path in QViewer without needing a corporate
VPN or firewall.

Run this script BEFORE triggering a login/upload in QGIS. QViewer should
immediately show the port-blocked error message instead of a silent failure.

Usage:
    python3 scripts/block_auth_port.py           # blocks port 4721
    python3 scripts/block_auth_port.py 4721      # same, explicit port
    python3 scripts/block_auth_port.py 9999      # blocks a different port

Press Ctrl+C to release the port when you're done testing.
"""

import signal
import socket
import sys
import time

DEFAULT_PORT = 4721


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Prevent SO_REUSEADDR so the bind truly holds the port exclusively
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)

    try:
        sock.bind(("127.0.0.1", port))
    except OSError as e:
        print(f"✗  Could not bind to port {port}: {e}")
        print("   Is another process already using it?")
        sys.exit(1)

    sock.listen(1)

    print(f"✓  Port {port} is now occupied on 127.0.0.1")
    print("   → Trigger a login/upload in QViewer to see the port-blocked error.")
    print("   Press Ctrl+C to release the port and restore normal behaviour.\n")

    # Handle Ctrl+C cleanly so the terminal doesn't show a traceback
    def _handle_sigint(sig, frame):  # noqa: ANN001
        print(f"\n✓  Released port {port}. Normal authentication should work again.")
        sock.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_sigint)

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
