"""Render-and-assert test for the Nokia SR OS PE template."""

from __future__ import annotations

import pytest

from transforms.pe_nokia_sros import PeNokiaSrOs

from .fixtures import pe_fixture, pe_fixture_with_site

FIXTURE = pe_fixture(
    name="pe-nyc-nokia",
    loopback="10.0.0.4/32",
    net_id="49.0001.0100.0000.0004.00",
)


@pytest.mark.asyncio
async def test_renders_configure_and_system_interface() -> None:
    """Template renders top-level configure block with system interface."""
    rendered = await PeNokiaSrOs.__new__(PeNokiaSrOs).transform(FIXTURE)
    assert "configure {" in rendered
    assert 'interface "system"' in rendered
    assert "10.0.0.4" in rendered


@pytest.mark.asyncio
async def test_renders_isis_and_area_address() -> None:
    """Template renders isis 1 block with area-address."""
    rendered = await PeNokiaSrOs.__new__(PeNokiaSrOs).transform(FIXTURE)
    assert "isis 1 {" in rendered
    assert "area-address 49.0001" in rendered


@pytest.mark.asyncio
async def test_renders_bgp_vpn_families() -> None:
    """Template renders BGP ibgp-mesh group with vpn-ipv4 and vpn-ipv6 families."""
    rendered = await PeNokiaSrOs.__new__(PeNokiaSrOs).transform(FIXTURE)
    assert "vpn-ipv4" in rendered
    assert "vpn-ipv6" in rendered
    assert 'group "ibgp-mesh"' in rendered


@pytest.mark.asyncio
async def test_nokia_system_id_extracted_from_net() -> None:
    """system-id is derived from NET parts [2].[3].[4], not [1].[2].[3]."""
    rendered = await PeNokiaSrOs.__new__(PeNokiaSrOs).transform(
        pe_fixture("pe-par-nokia", "10.0.0.4/32", "49.0001.0100.0000.0004.00")
    )
    assert "system-id 0100.0000.0004" in rendered


@pytest.mark.asyncio
async def test_renders_l3vpn_vrf_block_when_site_present() -> None:
    """Template renders vprn service block with service-id when a site is attached."""
    rendered = await PeNokiaSrOs.__new__(PeNokiaSrOs).transform(
        pe_fixture_with_site("pe-nyc-nokia", "10.0.0.4/32", "49.0001.0100.0000.0004.00")
    )
    assert "vprn" in rendered
    assert "service-id 100" in rendered
