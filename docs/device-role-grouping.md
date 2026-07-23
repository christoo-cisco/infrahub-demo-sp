# Device Role → Group Reconciliation

Automatically sync device group membership based on `role` and `platform` attributes via a webhook listener running in Docker.

## Overview

This system provides:
- **Reconciliation Service**: Docker container listening on port 8050
- **Webhook Listener**: Receives `DcimDevice` create/update events from Infrahub
- **Auto-Sync**: Device group membership updated based on role + platform rules

| Role | Platform | Target Group |
|------|----------|--------------|
| `pe` | `arista_eos` | `pe_arista_eos` |
| `pe` | `cisco_iosxr` | `pe_cisco_iosxr` |
| `pe` | `juniper_junos` | `pe_juniper_junos` |
| `pe` | `nokia_sros` | `pe_nokia_sros` |
| `core` | `cisco_iosxr` | `core_cisco_iosxr` |
| `pe` | (any platform) | `pes` |

## Setup

### 1. Start Infrahub (Device Reconciler Included)

The reconciliation service runs automatically:

```bash
uv run invoke init
```

Or just start the service:

```bash
uv run invoke start
```

The service listens on `http://localhost:8050/reconcile`

### 2. Create Webhook in Infrahub UI

The webhook must be configured manually via the Infrahub web interface:

1. Open Infrahub at **http://localhost:8000**
2. Navigate to **Administration → Webhooks** (or find the equivalent section in your UI)
3. Click **Create webhook** (or **New webhook**)
4. Configure:
   - **Name**: `device-role-group-reconciler`
   - **URL**: `http://device-group-reconciler:8050/reconcile` (Docker network URL)
   - **Events**: Select `created` and `updated`
   - **Target**: Select `DcimDevice`
   - **Shared Key** (or **Secret**): Use any strong random string (or leave empty if your Infrahub version doesn't require it)
5. Save and note the generated shared key

### 3. Configure Shared Key (if using authentication)

If Infrahub generated a shared key, set it in your `.env` file:

```bash
WEBHOOK_SHARED_KEY=<shared-key-from-infrahub-ui>
```

Then restart the reconciler:

```bash
docker compose -p sp-demo restart device-group-reconciler
```

If your Infrahub doesn't support shared keys, you can leave `WEBHOOK_SHARED_KEY` empty (authentication will be disabled).

### 4. Test It

Create or update a device to trigger the webhook:

```bash
# Update any device in the UI, then check the reconciler logs:
docker logs device-group-reconciler -f
```

## How It Works

1. **Device mutation** (create/update)
2. **Webhook fires** → POST to `http://device-group-reconciler:8050/reconcile`
3. **Service receives payload**:
   - Fetches device details (role, platform, current groups)
   - Determines target groups
   - Adds device to target groups
   - Removes device from obsolete groups
4. **Group membership updated**

## Usage Examples

### Adding a new Arista PE device via bootstrap

```yaml
---
apiVersion: infrahub.app/v1
kind: Object
spec:
  kind: DcimDevice
  data:
    - name: pe-new
      role: pe
      platform: arista_eos
      location: lon
      device_type: 7280R3
```

**Result**: Device automatically added to:
- ✓ `pe_arista_eos` (role=pe + platform=arista_eos)
- ✓ `pes` (role=pe)

### Changing a device's role via the UI

Change a device from `role: pe` to `role: core`:

**Result**: Device automatically:
- ✗ Removed from `pe_arista_eos`
- ✗ Removed from `pes`
- ✓ Added to `core_cisco_iosxr` (if platform=cisco_iosxr)

## Monitoring

### Health Check

```bash
curl http://localhost:8050/health
# Response: {"status": "healthy", "infrahub": "connected"}
```

### View Logs

```bash
# If running directly
# Logs appear in your terminal

# If running via Docker
docker logs device-group-reconciler -f
```

### Manually Test Webhook

```bash
curl -X POST http://localhost:8050/reconcile \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "updated",
    "data": {"id": "<device-id>"}
  }'
```

## Configuration

Environment variables (set in `.env` or at runtime):

```bash
# Infrahub server
INFRAHUB_ADDRESS=http://localhost:8000
INFRAHUB_API_TOKEN=<your-token>

# Webhook listener
RECONCILER_PORT=8050
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│           Infrahub Server                        │
│  ┌───────────────────────────────────────────┐  │
│  │ DcimDevice                                │  │
│  │ - name: pe-01                             │  │
│  │ - role: pe                                │  │
│  │ - platform: arista_eos                    │  │
│  └───────────────────────────────────────────┘  │
│            │                                     │
│            │ (mutation detected)                │
│            ▼                                     │
│  ┌───────────────────────────────────────────┐  │
│  │ CoreWebhook                               │  │
│  │ - device-role-group-reconciler            │  │
│  │ - POST /reconcile                         │  │
│  └───────────────────────────────────────────┘  │
└────────────┬────────────────────────────────────┘
             │
             │ (webhook POST)
             ▼
┌──────────────────────────────────────┐
│ Device Group Reconciler              │
│ (scripts/device_group_reconciler.py) │
│                                      │
│ 1. Fetch device role + platform      │
│ 2. Determine target groups           │
│ 3. Update group membership           │
│ 4. Return result                     │
└──────────────────────────────────────┘
             │
             │ (SDK calls)
             ▼
┌─────────────────────────────────────────────────┐
│ Infrahub Server (Groups Updated)                │
│ - pe_arista_eos: [pe-01, ...]                   │
│ - pes: [pe-01, ...]                             │
└─────────────────────────────────────────────────┘
```

## Troubleshooting

### Webhook not firing

1. Check webhook is **enabled** in Infrahub UI
2. Verify reconciler service is running: `curl http://localhost:8050/health`
3. Check Infrahub task queue for webhook delivery errors
4. View reconciler logs: `docker logs device-group-reconciler`

### Device not added to group

1. Verify device has both `role` and `platform` set (both required)
2. Verify the combination matches a rule (see table above)
3. Check reconciler logs for error messages
4. Manually test reconciliation:
   ```bash
   curl -X POST http://localhost:8050/reconcile \
     -H "Content-Type: application/json" \
     -d '{"event_type": "updated", "data": {"id": "<device-id>"}}'
   ```

### Service won't start

1. Check dependencies: `uv sync`
2. Verify Infrahub is reachable: `curl http://localhost:8000/api/graphql`
3. Check API token: `echo $INFRAHUB_API_TOKEN`
4. View detailed logs: `python scripts/device_group_reconcizer.py` (direct mode)

## Disabling

To disable automatic group syncing:

1. Open Infrahub UI → Administration → Webhooks
2. Set **device-role-group-reconciler → Enabled** to `false`
3. Webhook will no longer fire (but reconciler service can remain running)

## Extending

To add new role + platform combinations:

1. Edit `scripts/device_group_reconciler.py`:
   ```python
   ROLE_PLATFORM_GROUPS = {
       ("pe", "arista_eos"): "pe_arista_eos",
       # Add new rule here:
       ("pe", "my_platform"): "pe_my_platform",
   }
   ```

2. Create corresponding group in `objects/55_groups.yml`:
   ```yaml
   - name: pe_my_platform
     description: PEs running MyPlatform.
   ```

3. Restart reconciler service
4. Existing devices will be auto-synced on next webhook fire (or manually trigger via UI mutation)

## Related Files

- `objects/events/01_device_role_webhook.yml` — Webhook configuration
- `scripts/device_group_reconciler.py` — Reconciliation service
- `Dockerfile.reconciler` — Docker image
- `docker-compose.override.yml` — Docker Compose service (optional)
- `tasks.py` → `bootstrap-webhooks` task
