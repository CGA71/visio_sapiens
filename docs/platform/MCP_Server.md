# The MCP server

A [Model Context Protocol](https://modelcontextprotocol.io) server that lets an
AI client — Claude Desktop, Claude Code, any MCP client — read a live Visio
Sapiens instance: its rooms, its entities, its dashboards, its dependencies and
its pending updates.

**It runs on the instance, not on your workstation.** Only the *client* is on
your machine; the server is a service on the box it reads, reached over HTTP.
There is nothing to install on a desktop.

| Target | Wrapper | Credential |
|---|---|---|
| Home Assistant OS | `addons/vssp-mcp/` — a local add-on | none: the Supervisor |
| k3s (staging) | `kubernetes/mcp/` — a Deployment | a long-lived token in a Secret |

Both run the same Python package, `vssp_mcp/`, deployed to `/config/vssp_mcp`
by the pipeline. One copy of the code, two ways to serve it.

## Why not the Home Assistant MCP server

Two other things carry that name, and neither does this job.

**Home Assistant's own `mcp_server` integration** makes HA itself an MCP
server, but exposes only what the configured LLM API exposes — Assist intents,
on the entities you have exposed to the voice assistant. No dashboards, no
registries, no update state. (It is not enabled on either of this project's
instances.)

**Community servers** expose Lovelace CRUD, and only for **storage-mode**
dashboards — the ones a person clicks together in the UI. Visio Sapiens
dashboards are **YAML-mode**, rendered by `vssp/generate_dashboards.py` from
`dashboards/templates_j2/`. A card written through the storage API would be
erased by the next regeneration.

So this server does not reimplement the generator. It reads what the generator
reasons about, in this project's own vocabulary.

## Installing on Home Assistant OS

Copy `addons/vssp-mcp/` to `/addons/vssp-mcp` on the instance, then
**Settings → Add-ons → Add-on store → ⋮ → Check for updates**. It appears under
*Local add-ons*. Same procedure as `vssp-vault` beside it.

Deploy Visio Sapiens first: the add-on reads its code from
`/config/vssp_mcp`, and refuses to start with an explicit message if that is
not there yet.

### No token, and why that took three attempts

`homeassistant_api: true` in the add-on config is what makes the Supervisor
accept the container at `http://supervisor/core` with `SUPERVISOR_TOKEN`. No
long-lived token to create, paste or revoke.

That route failed twice before, for `vssp_dependencies.py` (v1.0.8, v1.0.9),
and the reason is structural: `/core/websocket` authenticates **add-ons**, and
that script runs inside Core's own container, which is not one. An add-on is
one, so the route should work here.

*Should* is the word that was wrong twice, and it cannot be tested from a
workstation. So the server **probes** each route at start-up and uses the first
that answers, logging which one it picked. If the proxy refuses, set `ha_token`
in the add-on options and it is used instead — the add-on keeps working either
way. See `routes()` in `vssp_mcp/ha.py`.

## Installing on k3s

There is no Supervisor, so a long-lived token is the only way in. From a
checkout, on the k3s host:

```sh
HA_TOKEN=<long-lived token> \
MCP_API_TOKEN=<a long random string> \
  sudo -E sh kubernetes/mcp/apply-mcp.sh
```

Both tokens are read from the environment and never appear in a command line,
a manifest or the script. `--dry-run` shows what would change.

The script finds Home Assistant's service rather than assuming its name, builds
a ConfigMap from the repository (the package plus `vssp/vssp_ws.py`), writes the
Secret, applies the Deployment and Service, and restarts the rollout — because
neither a ConfigMap nor a Secret change reaches a running pod on its own.

No private image is involved: this GitLab has no container registry, so the
runtime is the public `python:3.12-alpine` and an init container installs the
two dependencies into an `emptyDir`.

## Connecting a client

The endpoint is `http://<instance>:8099/mcp` (NodePort `30099` on k3s).

```json
{
  "mcpServers": {
    "visio-sapiens": {
      "type": "http",
      "url": "http://homeassistant.local:8099/mcp",
      "headers": { "Authorization": "Bearer <api_token>" }
    }
  }
}
```

### Set the token

An MCP endpoint on the home LAN with no token is an unauthenticated window onto
every entity state in the house. The tools are read-only, but reading is exactly
what leaks.

`api_token` (add-on) / `MCP_API_TOKEN` (k3s) is compared in constant time on
every request; without it the server says so in its log at every start rather
than pretending a read-only port is harmless. The SDK's own auth is
OAuth-shaped and wants an authorization server, which is a great many moving
parts for one household — a shared secret is the proportionate answer.

## The tools

All read-only.

| Tool | Answers |
|---|---|
| `vssp_instance` | Core version, OS appliance vs k3s pod, which credential it used |
| `vssp_rooms` | Home Assistant's areas, **and** what the house model holds |
| `vssp_room(room)` | one area's entities, with live states |
| `vssp_dashboards` | which Visio Sapiens dashboards exist **as files** |
| `vssp_dependencies` | missing cards, integrations and Lovelace resources |
| `vssp_updates` | pending updates, by family |
| `find_entities(pattern)` | substring search over ids and friendly names |

`vssp_instance` is the one to call first, and the server's own instructions say
so. A Home Assistant OS appliance has no k3s layer under it, and the
infrastructure family correctly reports `n/a` there — an assistant that skips
this step will offer an OS box a k3s upgrade that does not exist.

### Rooms are not where you would expect

`vssp_rooms` reports the **area registry**. The dashboard generator does not
read it. Its input is `dashboards/model/house.yaml` **on the instance**, whose
`rooms:` key is written by the ADMIN console's room form and topped up by the
discovery wizard — which is the one thing that reads areas, and does it through
the template API (`{{ areas() }}`). The copy in the git checkout is empty by
design.

At the time of writing, both instances report **zero areas and zero active
rooms**. That is a house whose room form has not been filled, not a broken
call, so the tool returns the model's own counters beside the registry list —
an empty answer that cannot be read is indistinguishable from a failure.

## Read-only, on purpose

None of these tools change anything. The acting surface already exists and is
deliberate: the ADMIN console's buttons, backed by `script.vssp_*`, each with
its confirmation and its status sensor. Wiring those in is a separate step.

## What has been verified

- All seven tools register with the SDK and expose the schemas above.
- Every tool ran end to end against **both live instances**, authenticated, and
  the two were told apart correctly:

  | | staging (k3s pod) | production (HAOS) |
  |---|---|---|
  | `installation` | Core (container / k3s pod) | Home Assistant OS / Supervised |
  | `infrastructure_layers_apply` | `true` | `false` |
  | entities | 2734 | 702 |
  | dashboards present | none | all three |
  | dependencies missing | 5 | 0 |
  | updates pending | 55 | 10 |

- Over HTTP with a shared secret: `401` with no token, a wrong token and a
  wrong-length token; `200` and a real tool result with the right one.
- Two defects were found by running the tools against real payloads rather than
  by reading the code: `vssp_updates` was returning the UPDATES screen's
  *controls* mixed in with its counts, and `vssp_room` answered "Known rooms:"
  followed by nothing on a house with no areas.

### Not verified

- The **Supervisor route** on a real Home Assistant OS add-on. It cannot be,
  from a workstation. That is why the server probes instead of assuming, and
  why `ha_token` exists as a fallback.
- **Neither wrapper has been started yet.** The package deploys correctly —
  `/config/vssp_mcp` lands on staging, proven by the pipeline's own
  "packaged but never deployed" guard passing — but the add-on still has to be
  installed from the Add-on store, and `apply-mcp.sh` still has to be run on
  the k3s host, which needs `sudo` there. Everything verified above was
  verified by running the same package directly against both instances.
