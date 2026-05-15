"""Shared fixture factory for PE config transform tests."""

from __future__ import annotations


def pe_fixture(name: str, loopback: str, net_id: str) -> dict:
    """Return a parametrised PE query-result fixture.

    Args:
        name: Device hostname (e.g. ``"pe-fra-cisco"``).
        loopback: Loopback0 address in CIDR notation (e.g. ``"10.0.0.2/32"``).
        net_id: ISIS NET identifier (e.g. ``"49.0001.0100.0000.0002.00"``).

    Returns:
        Dictionary matching the shape returned by the ``pe`` GraphQL query.
    """
    loopback_ip = loopback.split("/")[0]
    return {
        "DcimDevice": {
            "edges": [
                {
                    "node": {
                        "id": "d1",
                        "name": {"value": name},
                        "platform": {"node": {"name": {"value": "generic"}}},
                        "asn": {"node": {"asn": {"value": 65000}}},
                        "interfaces": {
                            "edges": [
                                {
                                    "node": {
                                        "__typename": "InterfaceVirtual",
                                        "id": "lo",
                                        "name": {"value": "Loopback0"},
                                        "description": {"value": ""},
                                        "status": {"value": "active"},
                                        "role": {"value": "management"},
                                        "mtu": {"value": 1500},
                                        "ip_addresses": {
                                            "edges": [
                                                {
                                                    "node": {
                                                        "address": {"value": loopback},
                                                        "vrf": None,
                                                    }
                                                }
                                            ]
                                        },
                                    }
                                },
                                {
                                    "node": {
                                        "__typename": "InterfacePhysical",
                                        "id": "e1",
                                        "name": {"value": "GigabitEthernet0/0/0/0"},
                                        "description": {"value": "To backbone peer"},
                                        "status": {"value": "active"},
                                        "role": {"value": "core"},
                                        "mtu": {"value": 9000},
                                        "ip_addresses": {
                                            "edges": [
                                                {
                                                    "node": {
                                                        "address": {"value": "10.1.0.2/31"},
                                                        "vrf": None,
                                                    }
                                                }
                                            ]
                                        },
                                    }
                                },
                            ]
                        },
                    }
                }
            ]
        },
        "MplsIsisProcess": {
            "edges": [
                {
                    "node": {
                        "area_id": {"value": "49.0001"},
                        "level": {"value": "level-2-only"},
                        "net_id": {"value": net_id},
                        "interfaces": {"edges": []},
                    }
                }
            ]
        },
        "MplsLdpProcess": {
            "edges": [
                {
                    "node": {
                        "router_id": {"value": loopback_ip},
                        "transport_address": None,
                        "interfaces": {"edges": []},
                    }
                }
            ]
        },
        "MplsBgpProcess": {
            "edges": [
                {
                    "node": {
                        "router_id": {"value": loopback_ip},
                        "address_families": {"value": ["vpnv4", "vpnv6"]},
                        "sessions": {
                            "edges": [
                                {
                                    "node": {
                                        "description": {"value": "iBGP to peer"},
                                        "session_type": {"value": "INTERNAL"},
                                        "local_ip": {
                                            "node": {"address": {"value": loopback}}
                                        },
                                        "remote_ip": {
                                            "node": {"address": {"value": "10.0.0.1/32"}}
                                        },
                                        "local_as": {"node": {"asn": {"value": 65000}}},
                                        "remote_as": {"node": {"asn": {"value": 65000}}},
                                    }
                                }
                            ]
                        },
                    }
                }
            ]
        },
        "ServiceL3VpnSite": {"edges": []},
    }
