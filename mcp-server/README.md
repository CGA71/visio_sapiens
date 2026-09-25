# Visio Sapiens — MCP server

A [Model Context Protocol](https://modelcontextprotocol.io) server that lets an
AI client — Claude Desktop, Claude Code, or any other MCP client — read a live
Visio Sapiens instance: its rooms, its entities, its dashboards, its
dependencies and its pending updates.

## Why this is not the community Home Assistant MCP server

The community servers expose Lovelace CRUD, and they only work on
**storage-mode** dashboards — the ones a person clicks together in the UI.

Visio Sapiens dashboards are **YAML-mode**. They are rendered by
`vssp/generate_dashboards.py` from `home-assistant/dashboards/templates_j2/`
against the house model held in Home Assistant's registries. A generic server
writing storage-mode cards cannot touch them, and a card it did write would be
erased by the next regeneration.

So this server does not reimplement the generator. It reads what the generator
reasons about, and hands it to the assistant in this project's own vocabulary.

## Why it lives outside `vssp/`

Everything under `vssp/` is copied into `/config/vssp` on every instance by the
deploy pipeline, and is therefore restricted to **stdlib + pyyaml** — a Home
Assistant OS appliance is not somewhere you ask a user to run `pip install`.

This server runs on a desktop and depends on the MCP SDK. Keeping it in a
top-level directory the pipeline never reads is what keeps that rule intact.
The directory is named `mcp-server`, with a hyphen, so that it cannot shadow
the `mcp` package on `sys.path` when Python is started from the repository
root.

It does **not** carry its own copy of the websocket client: it imports
`vssp/vssp_ws.py`, for the same reason that file was extracted in the first
place — two hand-rolled copies of RFC 6455 drift quietly.

## Install

```bash
cd mcp-server
uv sync            # or: pip install -e .
```

## Configure

Two environment variables, both set by the MCP client:

| Variable | Meaning | Default |
|---|---|---|
| `VSSP_HA_URL` | the instance to read | `http://localhost:8123` |
| `HA_TOKEN` | a long-lived access token for it | — |
| `VSSP_HA_TOKEN_FILE` | a file holding one, instead of `HA_TOKEN` | `/config/vssp/.ha_token` |

A token is minted from your Home Assistant profile page, under **Long-lived
access tokens**. Nothing else can mint one — not the Supervisor, not this
server. (Two earlier attempts to authenticate through the Supervisor's
`/core/websocket` proxy failed for a structural reason: that proxy
authenticates **add-ons**, and Core's own container is not one. See the comment
on `auth_routes()` in `vssp/vssp_dependencies.py`.)

Staging and production are different machines with different tokens. Point one
server at one instance; run two entries if you want both.

### Claude Desktop / Claude Code

```json
{
  "mcpServers": {
    "visio-sapiens": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/Visio-Sapiens/mcp-server",
               "run", "vssp-mcp"],
      "env": {
        "VSSP_HA_URL": "http://192.168.1.11:8123",
        "HA_TOKEN": "..."
      }
    }
  }
}
```

## Try it

```bash
uv run mcp dev vssp_mcp/server.py
```

That opens the MCP Inspector, where each tool can be called by hand before any
client is wired up.

## Tools

All read-only.

| Tool | Answers |
|---|---|
| `vssp_instance` | Core version, OS appliance vs k3s pod, deployed locale |
| `vssp_rooms` | every room with its entity count |
| `vssp_room(room)` | one room's entities, with live states |
| `vssp_dashboards` | which Visio Sapiens dashboards exist **as files** |
| `vssp_dependencies` | missing cards, integrations and Lovelace resources |
| `vssp_updates` | pending updates, by family |
| `find_entities(pattern)` | substring search over ids and friendly names |

`vssp_instance` is the one to call first. A Home Assistant OS appliance has no
k3s layer under it, and the infrastructure family correctly reports `n/a`
there — an assistant that skips this step will offer an OS box a k3s upgrade
that does not exist.

## Rooms are not where you would expect

`vssp_rooms` reports Home Assistant's **area registry**. The dashboard
generator does not read it. Its input is `dashboards/model/house.yaml` **on the
instance**, whose `rooms:` key is written by the ADMIN console's room form and
topped up by the discovery wizard — which is the one thing that reads areas, and
does it through the template API (`{{ areas() }}`), not the registry. The copy
of `house.yaml` in the git checkout is empty by design.

At the time of writing, both instances of this project report **zero areas and
zero active rooms**. That is a house whose room form has not been filled, not a
broken call. `vssp_rooms` returns the model's own counters next to the registry
list precisely so that an empty answer is readable rather than alarming.

## What has been verified

- The seven tools register with the SDK and expose the schemas above.
- Every tool body was run against the production instance's real registry and
  state payloads. Two defects were found and fixed that way: `vssp_updates` was
  returning the UPDATES screen's *controls* (`input_boolean`, `input_datetime`,
  three `script.*`) mixed in with its counts, and `vssp_room` answered "Known
  rooms:" followed by nothing on a house with no areas.
- Both transports fail with a readable sentence when the token is wrong
  (HTTP 401 on REST, `Invalid access token` on the websocket).
- **Every tool ran end to end against both live instances**, authenticated, and
  the two were told apart correctly:

  | | staging (k3s pod) | production (HAOS) |
  |---|---|---|
  | `installation` | Core (container / k3s pod) | Home Assistant OS / Supervised |
  | `infrastructure_layers_apply` | `true` | `false` |
  | entities | 2732 | 702 |
  | dashboards present | none | all three |
  | dependencies missing | 5 | 0 |
  | updates pending | 55 | 10 |

  That last distinction is the point: an OS appliance has no k3s under it, and
  a client calling `vssp_instance` first cannot offer it a k3s version.

## Read-only, on purpose

None of these tools change anything. The acting surface already exists and is
deliberate: the ADMIN console's buttons, backed by `script.vssp_*`, each with
its confirmation and its status sensor. Wiring those in is a second step, taken
once the reading half has been exercised against a live instance.
