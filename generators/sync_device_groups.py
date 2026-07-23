"""
Generator: Sync device group membership based on role and platform.

Runs whenever a device's role is set. Queries RoleGroupMapping to find
matching (role, platform) entries and adds the device to those groups.
"""

import logging
from typing import Any

from infrahub_sdk.generator import InfrahubGenerator

LOG = logging.getLogger("device-group-sync-generator")


class DeviceGroupSyncGenerator(InfrahubGenerator):
    """Sync device group membership based on role/platform attributes."""

    query = "sync_device_groups"
    infrahub_node = "sync_device_groups"

    async def generate(self, data: dict[str, Any] | None = None) -> None:
        """
        Sync groups for all devices with roles set.

        data: Optional - if provided, contains {"device_id": "<id>"} to sync a single device
        """
        # Get all devices with roles
        devices = await self.client.filters(
            kind="DcimDevice",
            role__value__isnull=False,
            branch=self.branch,
        )

        LOG.info(f"Syncing group membership for {len(devices)} devices with roles set")

        for device in devices:
            await self._sync_device_groups(device)

        LOG.info("Device group sync completed")

    async def _sync_device_groups(self, device: Any) -> None:
        """Sync groups for a single device based on role/platform."""
        device_name = device.name.value
        role = device.role.value if device.role else None
        platform = device.platform.name.value if device.platform else None

        if not role:
            LOG.debug(f"Skipping {device_name} - no role set")
            return

        LOG.info(f"Processing device {device_name} (role={role}, platform={platform})")

        # Query RoleGroupMapping to find matching entries
        mappings = await self.client.filters(
            kind="DcimRoleGroupMapping",
            role__value=role,
            branch=self.branch,
        )

        target_groups = set()

        for mapping in mappings:
            mapping_platform = mapping.platform.value if mapping.platform else None

            # Match if:
            # 1. Mapping has no platform (applies to all platforms), OR
            # 2. Mapping platform matches device platform
            if not mapping_platform or mapping_platform == platform:
                LOG.debug(
                    f"Mapping '{mapping.name.value}' matches {device_name} "
                    f"(platform: {mapping_platform} vs {platform})"
                )
                # Add all groups from this mapping
                for group_rel in mapping.groups:
                    if group_rel.node:
                        target_groups.add(group_rel.node.id)

        if not target_groups:
            LOG.info(f"{device_name}: No matching role/platform mappings found")
            return

        # Get device's current groups
        current_groups = set()
        for group_rel in device.member_of_groups:
            if group_rel.node:
                current_groups.add(group_rel.node.id)

        # Determine adds/removes
        groups_to_add = target_groups - current_groups
        groups_to_remove = current_groups - target_groups

        # Apply adds
        for group_id in groups_to_add:
            try:
                group = await self.client.get(kind="CoreStandardGroup", id=group_id)
                device.member_of_groups.append(group)
                LOG.info(f"Added {device_name} to group: {group.name.value}")
            except Exception as e:
                LOG.error(f"Failed to add {device_name} to group {group_id}: {e}")

        # Apply removes (only for managed groups - be conservative)
        MANAGED_GROUPS = {
            "pe_arista_eos",
            "pe_cisco_iosxr",
            "pe_juniper_junos",
            "pe_nokia_sros",
            "core_cisco_iosxr",
            "pes",
        }

        for group_rel in device.member_of_groups:
            if group_rel.node and group_rel.node.id in groups_to_remove:
                group_name = group_rel.node.name.value
                if group_name in MANAGED_GROUPS:
                    device.member_of_groups.remove(group_rel)
                    LOG.info(f"Removed {device_name} from group: {group_name}")

        # Save device with updated groups
        try:
            await device.save(allow_upsert=True)
            LOG.info(f"Saved group membership for {device_name}")
        except Exception as e:
            LOG.error(f"Failed to save {device_name} groups: {e}")
