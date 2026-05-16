"""Unit tests for backbone_session_count check."""

from __future__ import annotations

import pytest

from checks.backbone_session_count import BackboneSessionCountCheck


def _pe(name: str) -> dict:
    """Build a minimal DcimDevice edge node for testing.

    Args:
        name: PE device name.

    Returns:
        A dict shaped like a GraphQL edge node.
    """
    return {"node": {"name": {"value": name}}}


def _session(device: str) -> dict:
    """Build a minimal RoutingBGPSession edge node for testing.

    Args:
        device: Device name the session belongs to.

    Returns:
        A dict shaped like a GraphQL edge node.
    """
    return {"node": {"device": {"node": {"name": {"value": device}}}}}


@pytest.mark.asyncio
async def test_full_mesh_passes() -> None:
    """4 PEs each with 3 iBGP sessions = full mesh, no errors."""
    data = {
        "DcimDevice": {
            "count": 4,
            "edges": [_pe("p1"), _pe("p2"), _pe("p3"), _pe("p4")],
        },
        "RoutingBGPSession": {
            "edges": (
                [_session("p1")] * 3
                + [_session("p2")] * 3
                + [_session("p3")] * 3
                + [_session("p4")] * 3
            )
        },
    }
    check = BackboneSessionCountCheck(branch="main")
    await check.validate(data)
    assert check.errors == []


@pytest.mark.asyncio
async def test_missing_session_fails() -> None:
    """One PE with 2 sessions instead of 3 produces one error mentioning that PE."""
    data = {
        "DcimDevice": {
            "count": 4,
            "edges": [_pe("p1"), _pe("p2"), _pe("p3"), _pe("p4")],
        },
        "RoutingBGPSession": {
            "edges": (
                [_session("p1")] * 2
                + [_session("p2")] * 3
                + [_session("p3")] * 3
                + [_session("p4")] * 3
            )
        },
    }
    check = BackboneSessionCountCheck(branch="main")
    await check.validate(data)
    assert len(check.errors) == 1
    msg = check.errors[0]["message"]
    assert "p1" in msg
    assert "expected 3" in msg


@pytest.mark.asyncio
async def test_empty_data_produces_no_errors() -> None:
    """Empty query result (0 PEs) produces no errors."""
    data: dict = {"DcimDevice": {"count": 0, "edges": []}, "RoutingBGPSession": {"edges": []}}
    check = BackboneSessionCountCheck(branch="main")
    await check.validate(data)
    assert check.errors == []
