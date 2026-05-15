"""Unit test for pe_interface_alloc check."""

from __future__ import annotations

import pytest

from checks.pe_interface_alloc import PeInterfaceAllocCheck


def _site(name: str, pe: str, iface_id: str | None) -> dict:
    return {"node": {
        "name": {"value": name},
        "pe": {"node": {"name": {"value": pe}}},
        "pe_interface": (
            {"node": {"id": iface_id, "name": {"value": "Ethernet1"}}} if iface_id else None
        ),
    }}


@pytest.mark.asyncio
async def test_unique_pe_interface_passes() -> None:
    data = {"ServiceL3VpnSite": {"edges": [
        _site("a", "pe-lon-arista", "iface-1"),
        _site("b", "pe-par-nokia", "iface-2"),
    ]}}
    assert await PeInterfaceAllocCheck.__new__(PeInterfaceAllocCheck).validate(data) == []


@pytest.mark.asyncio
async def test_double_claimed_interface_fails() -> None:
    data = {"ServiceL3VpnSite": {"edges": [
        _site("a", "pe-lon-arista", "iface-1"),
        _site("b", "pe-lon-arista", "iface-1"),
    ]}}
    errors = await PeInterfaceAllocCheck.__new__(PeInterfaceAllocCheck).validate(data)
    assert errors and "double-claimed" in errors[0]


@pytest.mark.asyncio
async def test_sites_without_interface_are_ignored() -> None:
    data = {"ServiceL3VpnSite": {"edges": [_site("a", "pe-lon-arista", None)]}}
    assert await PeInterfaceAllocCheck.__new__(PeInterfaceAllocCheck).validate(data) == []
