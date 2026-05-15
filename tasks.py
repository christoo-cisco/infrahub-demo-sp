"""Invoke tasks for the SP demo MPLS L3VPN repo."""

from __future__ import annotations

import shlex
from pathlib import Path

from invoke.collection import Collection
from invoke.context import Context
from invoke.tasks import task

REPO_ROOT = Path(__file__).resolve().parent
COMPOSE_PROJECT = "sp-demo"


def _compose(c: Context, args: str, profile: str | None = None) -> None:
    """Run docker compose with the demo project name and optional profile."""
    profile_arg = f"--profile {profile}" if profile else ""
    c.run(f"docker compose -p {COMPOSE_PROJECT} {profile_arg} {args}", pty=True)


@task
def start(c: Context, build: bool = False, catalog: bool = False) -> None:
    """Start Infrahub containers. Use --catalog to enable the Streamlit sidecar."""
    build_arg = "--build" if build else ""
    profile = "service-catalog" if catalog else None
    _compose(c, f"up -d {build_arg}", profile=profile)


@task
def destroy(c: Context) -> None:
    """Tear down Infrahub containers and volumes."""
    _compose(c, "down -v", profile="service-catalog")


@task
def bootstrap(c: Context) -> None:
    """Load schemas, menus, and bootstrap object data into Infrahub."""
    c.run("uv run infrahubctl schema load schemas/", pty=True)
    c.run("uv run infrahubctl menu load menus/menu.yml", pty=True)
    for path in sorted(Path("objects").glob("*.yml")):
        c.run(f"uv run infrahubctl object load {shlex.quote(str(path))}", pty=True)
    c.run(
        "uv run infrahubctl protocols --branch main --output generators/schema_protocols.py",
        pty=True,
    )


@task(name="init")
def init_demo(c: Context) -> None:
    """Destroy, start, and bootstrap the demo end-to-end."""
    destroy(c)
    start(c, build=True)
    c.run("sleep 30", pty=True)
    bootstrap(c)


@task
def lint(c: Context) -> None:
    """Run the full lint suite: ruff, mypy, yamllint."""
    c.run("uv run ruff check .", pty=True)
    c.run("uv run ruff format --check .", pty=True)
    c.run("uv run mypy .", pty=True)
    c.run("uv run yamllint .", pty=True)


@task
def test(c: Context, kind: str = "unit") -> None:
    """Run pytest; kind in {unit, integration, catalog, all}."""
    if kind == "all":
        c.run("uv run pytest tests/", pty=True)
    else:
        c.run(f"uv run pytest tests/{kind}/", pty=True)


# Lab namespace (filled in Phase 8)
lab = Collection("lab")

ns = Collection()
ns.add_task(start)
ns.add_task(destroy)
ns.add_task(bootstrap)
ns.add_task(init_demo)
ns.add_task(lint)
ns.add_task(test)
ns.add_collection(lab)
