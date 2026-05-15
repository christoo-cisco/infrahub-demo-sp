"""Check that PE interfaces are not double-claimed by L3VPN sites."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from infrahub_sdk.checks import InfrahubCheck


class PeInterfaceAllocCheck(InfrahubCheck):
    """No PE interface is bound to more than one L3VPN site."""

    query = "pe_interface_alloc"

    async def validate(self, data: dict[str, Any]) -> list[str]:  # type: ignore[override]
        """Fail when any (pe, interface) tuple is claimed by 2+ sites.

        Args:
            data: Result of the ``pe_interface_alloc`` GraphQL query.

        Returns:
            List of human-readable failure messages.
        """
        groups: dict[tuple[str, str], list[str]] = defaultdict(list)
        for edge in data.get("ServiceL3VpnSite", {}).get("edges", []):
            node = edge["node"]
            if not node.get("pe_interface"):
                continue
            key = (node["pe"]["node"]["name"]["value"], node["pe_interface"]["node"]["id"])
            groups[key].append(node["name"]["value"])

        errors: list[str] = []
        for (pe, _), sites in groups.items():
            if len(sites) > 1:
                errors.append(f"PE {pe} interface double-claimed by sites: {', '.join(sites)}")
        return errors
