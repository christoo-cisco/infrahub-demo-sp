# infrahub-demo-sp

An [Infrahub](https://github.com/opsmill/infrahub) example repository that
models a multi-vendor MPLS backbone (Arista EOS, Cisco IOS-XR, Juniper Junos,
Nokia SR OS) and provisions L3VPNs as a service through a Streamlit Service
Catalog.

**Full documentation:** <https://docs.infrahub.app/demo-sp/>

---

## Quick start

```bash
git clone https://github.com/opsmill/infrahub-demo-sp.git
cd infrahub-demo-sp
cp .env.example .env
source .env
uv sync
uv run invoke init
```

Visit <http://localhost:8000> (admin / infrahub) for the Infrahub UI. To
enable the Streamlit Service Catalog sidecar set
`INFRAHUB_SERVICE_CATALOG="true"` in `.env` and re-run `uv run invoke start`.

See the [quickstart guide](https://docs.infrahub.app/demo-sp/quickstart) for
the step-by-step walkthrough.
