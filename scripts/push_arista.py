"""Push a config file to a running clab cEOS node over netmiko."""

from __future__ import annotations

import sys
from pathlib import Path

from netmiko import ConnectHandler


def main(config_path: str, node_name: str) -> int:
    """Push ``config_path`` to clab node ``node_name``.

    Args:
        config_path: Path to the rendered configuration file.
        node_name: Short clab node name (e.g. ``pe-lon-arista``).  The
            hostname used for the SSH connection is ``clab-<node_name>``.

    Returns:
        Exit code (0 on success).
    """
    text = Path(config_path).read_text(encoding="utf-8")
    conn = ConnectHandler(
        device_type="arista_eos",
        host=f"clab-{node_name}",
        username="admin",
        password="admin",
    )
    conn.send_config_set(text.splitlines())
    conn.save_config()
    conn.disconnect()
    print(f"Pushed {len(text.splitlines())} lines to {node_name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
