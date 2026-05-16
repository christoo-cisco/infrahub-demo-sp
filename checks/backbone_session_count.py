"""Check that the iBGP backbone mesh is intact."""

from __future__ import annotations

from collections import Counter
from typing import Any

from infrahub_sdk.checks import InfrahubCheck


class BackboneSessionCountCheck(InfrahubCheck):
    """Each PE must have N-1 INTERNAL sessions where N is total PE count."""

    query = "backbone_session_count"

    async def validate(self, data: dict[str, Any]) -> None:  # type: ignore[override]
        """Log errors when any PE is missing expected iBGP sessions.

        Args:
            data: Result of the ``backbone_session_count`` GraphQL query.
        """
        pe_count = int(data.get("DcimDevice", {}).get("count", 0))
        expected_per_pe = pe_count - 1
        counts: Counter[str] = Counter()
        for edge in data.get("RoutingBGPSession", {}).get("edges", []):
            counts[edge["node"]["device"]["node"]["name"]["value"]] += 1

        for pe_edge in data.get("DcimDevice", {}).get("edges", []):
            name = pe_edge["node"]["name"]["value"]
            actual = counts.get(name, 0)
            if actual != expected_per_pe:
                self.log_error(
                    message=(
                        f"PE {name} has {actual} INTERNAL BGP sessions, expected {expected_per_pe}"
                    ),
                )
