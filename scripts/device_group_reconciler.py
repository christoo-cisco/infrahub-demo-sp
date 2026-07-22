#!/usr/bin/env python3
"""
Device group reconciliation service.

Listens for DcimDevice webhooks and automatically manages group membership
based on device role and platform attributes.

Rules:
  - role=pe + platform=arista_eos → add to pe_arista_eos
  - role=pe + platform=cisco_iosxr → add to pe_cisco_iosxr
  - role=pe + platform=juniper_junos → add to pe_juniper_junos
  - role=pe + platform=nokia_sros → add to pe_nokia_sros
  - role=core + platform=cisco_iosxr → add to core_cisco_iosxr
  - role=pe (any platform) → add to pes
  - Otherwise → remove from all above groups

Usage:
  python scripts/device_group_reconciler.py

  # Or with custom settings
  INFRAHUB_ADDRESS=http://localhost:8000 \
  INFRAHUB_API_TOKEN=<token> \
  RECONCILER_PORT=8050 \
  python scripts/device_group_reconciler.py

Environment Variables:
  INFRAHUB_ADDRESS: Infrahub server URL (default: http://localhost:8000)
  INFRAHUB_API_TOKEN: API token (default: env var or .env)
  RECONCILER_PORT: Webhook listener port (default: 8050)
"""

import asyncio
import json
import logging
import os
from typing import Any

import httpx
from aiohttp import web
from infrahub_sdk import InfrahubClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
LOG = logging.getLogger("device-group-reconciler")

# Configuration
INFRAHUB_ADDRESS = os.getenv("INFRAHUB_ADDRESS", "http://localhost:8000")
INFRAHUB_API_TOKEN = os.getenv(
    "INFRAHUB_API_TOKEN", "06438eb2-8019-4776-878c-0941b1f1d1ec"
)
RECONCILER_PORT = int(os.getenv("RECONCILER_PORT", "8050"))

# Group membership rules: (role, platform) → group_name
ROLE_PLATFORM_GROUPS = {
    ("pe", "arista_eos"): "pe_arista_eos",
    ("pe", "cisco_iosxr"): "pe_cisco_iosxr",
    ("pe", "juniper_junos"): "pe_juniper_junos",
    ("pe", "nokia_sros"): "pe_nokia_sros",
    ("core", "cisco_iosxr"): "core_cisco_iosxr",
}

# Role-based groups (all platforms)
ROLE_GROUPS = {
    "pe": "pes",
}

# All managed groups (for cleanup)
ALL_MANAGED_GROUPS = {
    "pe_arista_eos",
    "pe_cisco_iosxr",
    "pe_juniper_junos",
    "pe_nokia_sros",
    "core_cisco_iosxr",
    "pes",
}


async def get_device(client: InfrahubClient, device_id: str) -> dict[str, Any] | None:
    """Fetch device with role and platform details."""
    try:
        device = await client.get(
            kind="DcimDevice",
            id=device_id,
            include=["role", "platform__name"],
        )
        return {
            "id": device.id,
            "name": device.name.value,
            "role": (device.role or None),
            "platform": (device.platform.name.value if device.platform else None),
        }
    except Exception as e:
        LOG.warning(f"Failed to fetch device {device_id}: {e}")
        return None


async def reconcile_device_groups(
    client: InfrahubClient, device: dict[str, Any]
) -> None:
    """Reconcile group membership for a device based on role/platform."""
    device_id = device["id"]
    device_name = device["name"]
    role = device["role"]
    platform = device["platform"]

    LOG.info(
        f"Reconciling groups for device {device_name} (role={role}, platform={platform})"
    )

    # Determine target groups
    target_groups = set()

    if role and platform:
        # Check role + platform combo
        if (role, platform) in ROLE_PLATFORM_GROUPS:
            target_groups.add(ROLE_PLATFORM_GROUPS[(role, platform)])

    if role:
        # Check role-only groups
        if role in ROLE_GROUPS:
            target_groups.add(ROLE_GROUPS[role])

    # Get current group memberships
    try:
        current_groups_response = await client.execute_graphql(
            query="""
            query GetDeviceGroups($device_id: String!) {
              DcimDevice(id: $device_id) {
                member_of_groups {
                  edges {
                    node {
                      name {
                        value
                      }
                    }
                  }
                }
              }
            }
            """,
            variables={"device_id": device_id},
        )
        current_groups = {
            group["node"]["name"]["value"]
            for group in current_groups_response.get("DcimDevice", {})
            .get("member_of_groups", {})
            .get("edges", [])
        }
    except Exception as e:
        LOG.warning(f"Failed to fetch current groups for {device_name}: {e}")
        current_groups = set()

    # Determine adds/removes (only for managed groups)
    to_add = (target_groups & ALL_MANAGED_GROUPS) - current_groups
    to_remove = (current_groups & ALL_MANAGED_GROUPS) - target_groups

    # Apply changes
    for group_name in to_add:
        try:
            group = await client.get(kind="CoreStandardGroup", name__value=group_name)
            device_obj = await client.get(kind="DcimDevice", id=device_id)
            device_obj.member_of_groups.append(group)
            await device_obj.save(allow_upsert=True)
            LOG.info(f"  ✓ Added {device_name} to group {group_name}")
        except Exception as e:
            LOG.error(f"  ✗ Failed to add {device_name} to {group_name}: {e}")

    for group_name in to_remove:
        try:
            device_obj = await client.get(kind="DcimDevice", id=device_id)
            group_to_remove = None
            for g in device_obj.member_of_groups:
                if g.name.value == group_name:
                    group_to_remove = g
                    break
            if group_to_remove:
                device_obj.member_of_groups.remove(group_to_remove)
                await device_obj.save(allow_upsert=True)
                LOG.info(f"  ✓ Removed {device_name} from group {group_name}")
        except Exception as e:
            LOG.error(f"  ✗ Failed to remove {device_name} from {group_name}: {e}")


async def webhook_handler(request: web.Request) -> web.Response:
    """Handle incoming device webhook and reconcile groups."""
    try:
        payload = await request.json()
        event_type = payload.get("event_type", "unknown")
        data = payload.get("data", {})

        if not data:
            LOG.warning("Received webhook with empty data")
            return web.json_response({"status": "skipped", "reason": "no data"})

        device_id = data.get("id") or data.get("data", {}).get("id")
        if not device_id:
            LOG.warning("Received webhook without device ID")
            return web.json_response({"status": "skipped", "reason": "no device id"})

        LOG.info(f"Received {event_type} webhook for device {device_id}")

        # Initialize Infrahub client
        async with InfrahubClient(
            address=INFRAHUB_ADDRESS,
            token=INFRAHUB_API_TOKEN,
            timeout=30.0,
        ) as client:
            device = await get_device(client, device_id)
            if device:
                await reconcile_device_groups(client, device)
                return web.json_response(
                    {"status": "success", "device": device["name"]}
                )

        return web.json_response(
            {"status": "error", "reason": "failed to fetch device"}
        )

    except json.JSONDecodeError as e:
        LOG.error(f"Invalid JSON in webhook: {e}")
        return web.json_response(
            {"status": "error", "reason": "invalid json"}, status=400
        )
    except Exception as e:
        LOG.error(f"Webhook processing error: {e}", exc_info=True)
        return web.json_response({"status": "error", "reason": str(e)}, status=500)


async def health_handler(request: web.Request) -> web.Response:
    """Health check endpoint."""
    try:
        async with InfrahubClient(
            address=INFRAHUB_ADDRESS,
            token=INFRAHUB_API_TOKEN,
            timeout=5.0,
        ) as client:
            await client.execute_graphql(query="{ me { username } }")
        return web.json_response({"status": "healthy", "infrahub": "connected"})
    except Exception as e:
        return web.json_response(
            {"status": "unhealthy", "reason": str(e)},
            status=503,
        )


async def main():
    """Start the webhook listener."""
    app = web.Application()
    app.router.add_post("/reconcile", webhook_handler)
    app.router.add_get("/health", health_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", RECONCILER_PORT)

    LOG.info(f"🚀 Starting device group reconciler on port {RECONCILER_PORT}")
    LOG.info(f"   Infrahub: {INFRAHUB_ADDRESS}")
    LOG.info(f"   Webhook: POST http://localhost:{RECONCILER_PORT}/reconcile")
    LOG.info(f"   Health: GET http://localhost:{RECONCILER_PORT}/health")
    LOG.info("")
    LOG.info("To enable the webhook in Infrahub, run:")
    LOG.info("  1. Load webhook: uv run invoke bootstrap-webhooks")
    LOG.info(
        "  2. Enable it: Update CoreWebhook.device-role-group-reconciler → enabled: true"
    )

    await site.start()

    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        LOG.info("Shutting down...")
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
