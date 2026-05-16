"""Containerlab topology transform for the MPLS backbone."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from infrahub_sdk.transforms import InfrahubTransform
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


class ClabTopology(InfrahubTransform):
    """Render a containerlab YAML topology for the lab-deployable subset of PEs."""

    query = "clab_topology"

    async def transform(self, data: dict[str, Any]) -> str:
        """Render the clab topology template.

        Args:
            data: Result of the ``clab_topology`` GraphQL query.

        Returns:
            Rendered containerlab YAML as plain text.
        """
        env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        template = env.get_template("clab_topology.j2")
        return template.render(data=data)
