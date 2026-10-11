# MCP Servers — Protocol & SDK Reference

> **Last verified:** 2026-10-09

## Protocol version

The four BountyLoop MCP servers implement the **Model Context Protocol (MCP)**.  
Protocol version and Python SDK version will be recorded here after Phase 9 implementation.

```
# Fill in after Phase 9:
MCP_SPEC_VERSION: UNVERIFIED
PYTHON_SDK_VERSION: UNVERIFIED
TRANSPORT: streamable-http (production) | stdio (local dev)
```

## Servers

| Server | Port | Purpose |
|---|---|---|
| `donation_ledger_mcp` | 8010 | Donation CRUD, recipient query, claim recording, impact logging |
| `routing_mcp` | 8011 | Geocoding (Nominatim), routing (OSRM), pickup optimization |
| `notify_mcp` | 8012 | FCM push (primary), SMS via Twilio (capped at SMS_DAILY_CAP) |
| `charity_directory_mcp` | 8013 | Recipient capacity, acceptance rules, partner directory |

## MCP Primitives Used

- **Tools** — agent-callable actions (the primary interface)
- **Resources** — readable data (donation/recipient records)
- **Prompts** — templates for the orchestrator's decision narrative

## Safety contracts

- `notify_mcp` MUST refuse `send_sms()` when the daily SMS cap is reached and log the refusal.
- All MCP servers wrap the backend's internal API via `INTERNAL_SERVICE_TOKEN` — no raw SQL.
- Every tool call writes an `agent_events` row for full auditability.
- The orchestrator's `AGENT_ENABLED=false` kill switch must degrade gracefully to Phase 7 manual matching.

## References

- [MCP specification](https://modelcontextprotocol.io)
- [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk)
