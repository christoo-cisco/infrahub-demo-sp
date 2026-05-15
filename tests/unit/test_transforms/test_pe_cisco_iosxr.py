"""Render-and-assert test for the Cisco IOS-XR PE template."""

from __future__ import annotations

import pytest

from transforms.pe_cisco_iosxr import PeCiscoIosXr

from .fixtures import pe_fixture

FIXTURE = pe_fixture(
    name="pe-fra-cisco",
    loopback="10.0.0.2/32",
    net_id="49.0001.0100.0000.0002.00",
)


@pytest.mark.asyncio
async def test_renders_hostname_and_loopback() -> None:
    """Template renders hostname and Loopback0 IPv4 address."""
    rendered = await PeCiscoIosXr.__new__(PeCiscoIosXr).transform(FIXTURE)
    assert "hostname pe-fra-cisco" in rendered
    assert "interface Loopback0" in rendered
    assert "10.0.0.2" in rendered


@pytest.mark.asyncio
async def test_renders_isis_net_id() -> None:
    """Template renders ISIS NET identifier with IOS-XR level-2-only keyword."""
    rendered = await PeCiscoIosXr.__new__(PeCiscoIosXr).transform(FIXTURE)
    assert "router isis 1" in rendered
    assert "net 49.0001.0100.0000.0002.00" in rendered
    assert "is-type level-2-only" in rendered


@pytest.mark.asyncio
async def test_renders_ibgp_and_vpnv4_families() -> None:
    """Template renders iBGP neighbor and vpnv4/vpnv6 unicast address families."""
    rendered = await PeCiscoIosXr.__new__(PeCiscoIosXr).transform(FIXTURE)
    assert "router bgp 65000" in rendered
    assert "address-family vpnv4 unicast" in rendered
    assert "route-policy PASS-ALL" in rendered
