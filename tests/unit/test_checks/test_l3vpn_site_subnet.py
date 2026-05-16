"""Unit tests for l3vpn_site_subnet check."""

from __future__ import annotations

import pytest

from checks.l3vpn_site_subnet import L3VpnSiteSubnetCheck


def _vpn(name: str, sites: list[tuple[str, str]]) -> dict:
    """Build a minimal ServiceL3Vpn edge node for testing.

    Args:
        name: VPN name.
        sites: List of (site_name, prefix_cidr) tuples.

    Returns:
        A dict shaped like a GraphQL edge node.
    """
    return {
        "node": {
            "name": {"value": name},
            "sites": {
                "edges": [
                    {
                        "node": {
                            "name": {"value": s},
                            "customer_subnet": {"node": {"prefix": {"value": p}}},
                        }
                    }
                    for s, p in sites
                ]
            },
        }
    }


@pytest.mark.asyncio
async def test_disjoint_subnets_pass() -> None:
    """Two sites with non-overlapping subnets produce no errors."""
    data = {"ServiceL3Vpn": {"edges": [_vpn("acme", [("a", "10.1.0.0/24"), ("b", "10.2.0.0/24")])]}}
    check = L3VpnSiteSubnetCheck(branch="main")
    await check.validate(data)
    assert check.errors == []


@pytest.mark.asyncio
async def test_overlapping_subnets_fail() -> None:
    """Two sites with overlapping subnets produce one error."""
    data = {"ServiceL3Vpn": {"edges": [_vpn("acme", [("a", "10.1.0.0/16"), ("b", "10.1.5.0/24")])]}}
    check = L3VpnSiteSubnetCheck(branch="main")
    await check.validate(data)
    assert len(check.errors) == 1
    assert "overlaps" in check.errors[0]["message"]


@pytest.mark.asyncio
async def test_single_site_always_passes() -> None:
    """A VPN with a single site cannot have intra-VPN overlap."""
    data = {"ServiceL3Vpn": {"edges": [_vpn("contoso", [("only", "192.168.1.0/24")])]}}
    check = L3VpnSiteSubnetCheck(branch="main")
    await check.validate(data)
    assert check.errors == []
