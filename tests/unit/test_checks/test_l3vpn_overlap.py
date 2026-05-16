"""Unit tests for l3vpn_overlap check."""

from __future__ import annotations

import pytest

from checks.l3vpn_overlap import L3VpnOverlapCheck


def _vpn_node(id_: str, name: str, vpn_id: int, rd: str | None) -> dict:
    """Build a minimal ServiceL3Vpn edge node for testing.

    Args:
        id_: Node ID.
        name: VPN name.
        vpn_id: VPN numeric ID.
        rd: Route Distinguisher value, or None to simulate a null vrf_rd.

    Returns:
        A dict shaped like a GraphQL edge node.
    """
    vrf_rd = {"value": rd} if rd is not None else {"value": None}
    return {
        "node": {
            "id": id_,
            "name": {"value": name},
            "vpn_id": {"value": vpn_id},
            "vrf": {"node": {"vrf_rd": vrf_rd}},
        }
    }


@pytest.mark.asyncio
async def test_no_overlap_passes() -> None:
    """Two VPNs with distinct RDs produce no errors."""
    data = {
        "ServiceL3Vpn": {
            "edges": [
                _vpn_node("1", "a", 100, "65000:100"),
                _vpn_node("2", "b", 101, "65000:101"),
            ]
        }
    }
    check = L3VpnOverlapCheck(branch="main")
    await check.validate(data)
    assert check.errors == []


@pytest.mark.asyncio
async def test_duplicate_rd_fails() -> None:
    """Two VPNs sharing the same RD produce one error."""
    data = {
        "ServiceL3Vpn": {
            "edges": [
                _vpn_node("1", "a", 100, "65000:100"),
                _vpn_node("2", "b", 101, "65000:100"),
            ]
        }
    }
    check = L3VpnOverlapCheck(branch="main")
    await check.validate(data)
    assert len(check.errors) == 1
    assert "duplicate RD" in check.errors[0]["message"]


@pytest.mark.asyncio
async def test_null_rd_is_skipped() -> None:
    """A VPN with a null vrf_rd is skipped and does not raise TypeError."""
    data = {
        "ServiceL3Vpn": {
            "edges": [
                _vpn_node("1", "a", 100, None),
                _vpn_node("2", "b", 101, "65000:101"),
            ]
        }
    }
    check = L3VpnOverlapCheck(branch="main")
    await check.validate(data)
    assert check.errors == []


@pytest.mark.asyncio
async def test_no_vrf_is_skipped() -> None:
    """A VPN with no VRF at all is skipped gracefully."""
    data = {
        "ServiceL3Vpn": {
            "edges": [
                {"node": {"id": "1", "name": {"value": "a"}, "vpn_id": {"value": 100}, "vrf": None}}
            ]
        }
    }
    check = L3VpnOverlapCheck(branch="main")
    await check.validate(data)
    assert check.errors == []
