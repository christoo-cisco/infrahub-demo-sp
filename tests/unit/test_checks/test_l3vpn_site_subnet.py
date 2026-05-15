"""Unit test for l3vpn_site_subnet check."""

from __future__ import annotations

import pytest

from checks.l3vpn_site_subnet import L3VpnSiteSubnetCheck


def _vpn(name: str, sites: list[tuple[str, str]]) -> dict:
    return {"node": {"name": {"value": name}, "sites": {"edges": [
        {"node": {"name": {"value": s}, "customer_subnet": {"node": {"prefix": {"value": p}}}}}
        for s, p in sites
    ]}}}


@pytest.mark.asyncio
async def test_disjoint_subnets_pass() -> None:
    data = {"ServiceL3Vpn": {"edges": [_vpn("acme", [("a", "10.1.0.0/24"), ("b", "10.2.0.0/24")])]}}
    assert await L3VpnSiteSubnetCheck.__new__(L3VpnSiteSubnetCheck).validate(data) == []


@pytest.mark.asyncio
async def test_overlapping_subnets_fail() -> None:
    data = {"ServiceL3Vpn": {"edges": [_vpn("acme", [("a", "10.1.0.0/16"), ("b", "10.1.5.0/24")])]}}
    errors = await L3VpnSiteSubnetCheck.__new__(L3VpnSiteSubnetCheck).validate(data)
    assert errors and "overlaps" in errors[0]
