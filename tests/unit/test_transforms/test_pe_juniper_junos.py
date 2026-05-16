"""Render-and-assert test for the Juniper Junos PE template."""

from __future__ import annotations

import pytest

from transforms.pe_juniper_junos import PeJuniperJunos

from .fixtures import pe_fixture, pe_fixture_with_site

FIXTURE = pe_fixture(
    name="pe-ams-juniper",
    loopback="10.0.0.3/32",
    net_id="49.0001.0100.0000.0003.00",
)


@pytest.mark.asyncio
async def test_renders_hostname_and_loopback() -> None:
    """Template renders Junos host-name and lo0 interface."""
    rendered = await PeJuniperJunos.__new__(PeJuniperJunos).transform(FIXTURE)
    assert "host-name pe-ams-juniper" in rendered
    assert "lo0" in rendered
    assert "10.0.0.3" in rendered


@pytest.mark.asyncio
async def test_renders_isis_net_id() -> None:
    """Template renders ISIS NET address on lo0.0."""
    rendered = await PeJuniperJunos.__new__(PeJuniperJunos).transform(FIXTURE)
    assert "49.0001.0100.0000.0003.00" in rendered
    assert "family iso" in rendered


@pytest.mark.asyncio
async def test_renders_ibgp_and_vpn_families() -> None:
    """Template renders iBGP group with inet-vpn family and type internal."""
    rendered = await PeJuniperJunos.__new__(PeJuniperJunos).transform(FIXTURE)
    assert "family inet-vpn" in rendered
    assert "type internal" in rendered
    assert "10.0.0.1" in rendered


@pytest.mark.asyncio
async def test_renders_l3vpn_vrf_block_when_site_present() -> None:
    """Template renders routing-instance with instance-type vrf and route-distinguisher."""
    rendered = await PeJuniperJunos.__new__(PeJuniperJunos).transform(
        pe_fixture_with_site("pe-ams-juniper", "10.0.0.3/32", "49.0001.0100.0000.0003.00")
    )
    assert "instance-type vrf" in rendered
    assert "route-distinguisher 65000:100" in rendered
