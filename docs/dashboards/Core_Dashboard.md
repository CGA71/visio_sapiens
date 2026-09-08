# core.html — Visio Sapiens System Dashboard

**English** · [Français](Core_Dashboard.fr.md)

Documentation of how the page actually works: where the metrics come from, how they travel
up to the page, and how often.

**Real location in the repo:** `home-assistant/www/vssp/core.html`
→ deployed to `/config/www/vssp/core.html` → served at `/local/vssp/core.html`.

---

## 1. Overview

`core.html` is a **standalone static page** (inline HTML + CSS + JS, no build step, no
framework). It collects **no metrics itself**: it is a pure display client that queries the
Home Assistant REST API.

It is not opened directly by the user: the Lovelace dashboard `dashboards/views/core.yaml`
(url_path `visio-sapiens-core`) embeds it in an **iframe**. That file was actually fixed to
stop stacking two versions of the same content — the native HA cards (gauge, apexcharts,
auto-entities) that duplicated the iframe were removed. The CORE view now contains only:
sidebar (`nav`), first row of the header band (`header`), iframe, footer HUD.

The full chain is as follows:

```
┌──────────────┐   psutil / lm-sensors
│   Host Linux │   (reads /proc, /sys)
└──────┬───────┘
       │
┌──────▼──────────────┐
│ Glances (Python)     │  glances -w daemon
│ REST API :61208      │  → real-time JSON (CPU, RAM, swap, load, temps, disk, net)
└──────┬──────────────┘
       │ polling (scan_interval, 60 s by default)
┌──────▼──────────────────────────┐
│ Home Assistant                   │
│  • "Glances" integration         │ → creates sensor.* entities
│  • recorder (SQLite/MariaDB)     │ → keeps a history of states
│  • REST API /api/states          │
│  • API /api/history/period       │
│  • static server /local/         │
└──────┬──────────────────────────┘
       │ fetch() + Bearer token, every 30 s
┌──────▼───────┐
│  core.html   │  SVG gauges + Chart.js
└──────────────┘

       ┌───────────────────────────────────────────┐
       │ Separate channel for K3s:                  │
       │ cron k3s_stats.sh → k3s_stats.json         │
       │ → /config/www/vssp/ → /local/vssp/...      │
       └───────────────────────────────────────────┘
```

**Key point:** `HA_URL = window.location.origin`. The page **must** be served by Home
Assistant itself. Opened via `file://` or from another domain, every API call fails (wrong
origin + CORS). The iframe in `core.yaml` respects this constraint since it points to a
`/local/` URL on the same instance.

---

## 2. The collection layer: Glances

The collection dependency is **Glances**, a Python monitoring tool (built on `psutil`). The
header subtitle confirms it: `Glances Monitoring`.

### Host-side installation

```bash
pip install "glances[web]"
# or: apt install glances
glances -w                      # web server mode + REST API on port 61208
```

As a systemd service:

```ini
[Unit]
Description=Glances
After=network.target

[Service]
ExecStart=/usr/local/bin/glances -w --disable-webui
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

- REST API: `http://<host>:61208/api/4/all` (v3: `/api/3/all`)
- Temperatures come from the `sensors` plugin, which requires **`lm-sensors`** installed and
  configured on the host (`sensors-detect`). Without it, the "Component temperature" section
  stays empty.

### Home Assistant side

**Glances** integration (Settings → Devices & services → Add → Glances), with host + port +
API version. HA polls Glances every 60 s by default and creates entities such as:

| Metric | Typical entity |
|---|---|
| CPU | `sensor.<host>_cpu_used_percent` / `..._utilisation_cpu` |
| RAM | `sensor.<host>_memory_use_percent` / `..._utilisation_memoire` |
| Swap | `sensor.<host>_swap_use_percent` |
| Load | `sensor.<host>_cpu_load_1m` / `..._charge_processeur_1` |
| Temperatures | `sensor.<host>_cpu_temp`, `..._package_id_0`, `..._nvme`, `..._edge` |
| Disk | `sensor.<host>_disk_use_percent` / `..._espace` |
| Network | `sensor.<host>_<iface>_rx` |

HA's `recorder` is what stores the history later queried by the charts.

---

## 3. Authentication

```js
var HA_URL = window.location.origin,
    TOKEN  = localStorage.getItem('osv_ha_token') || '';
```

- On first load, if no token is cached, `init()` replaces the entire content of `.page` with
  a small login form.
- `saveToken()` writes the token to `localStorage` under the key **`osv_ha_token`**, then
  calls `init()` again.
- The token is an HA **Long-Lived Access Token** (user profile → bottom of page → "Create
  Token").
- It is then sent on every request: `Authorization: Bearer <TOKEN>`.

⚠️ The token is stored in plaintext in `localStorage` and stays valid for a very long time —
treat it as a secret granting full access to Home Assistant. The `osv_ha_token` key name is a
naming leftover: renaming it would break the session of every browser already paired, so it
should only be done with an explicit migration (read the old key, rewrite it under the new
one, delete the old one).

---

## 4. Fetching real-time metrics

### 4.1 Instant state — `haGet('states')`

```js
async function haGet(p){
  var r = await fetch(HA_URL+'/api/'+p, {headers:{Authorization:'Bearer '+TOKEN}});
  if(!r.ok) throw new Error(p+': '+r.status);
  return r.json();
}
```

A **single call** to `GET /api/states` retrieves every entity in Home Assistant (often
several hundred JSON objects). The entire dashboard is then built from this array, with no
further per-metric request.

### 4.2 Automatic entity discovery

The dashboard hardcodes **no `entity_id`** at all. It does *fuzzy matching* on the
`entity_id + friendly_name` pair:

```js
function findEntity(s,k,x){          // k = required keywords, x = excluded keywords
  return s.find(function(e){
    var c = (e.entity_id+' '+(e.attributes.friendly_name||'')).toLowerCase();
    return k.every(w => c.includes(w.toLowerCase()))
        && !x.some(w => c.includes(w.toLowerCase()));
  });
}
```

`findEntities()` is the variant that returns **all** matches (used for the temperature
sensors).

The search is a **cascade with fallbacks**, which supports both English and French entity
names:

```js
var cpu = findEntity(states,['cpu','use'],['core','temp','temperature'])
       || findEntity(states,['cpu_percent'])
       || findEntity(states,['utilisation','cpu'],['core','temp']);
```

Same logic for RAM (`ram+use` → `memory+use` → `utilisation+memoire`), load
(`charge+processeur+1` → `load+1m`), temperature (`cpu+temp` → `package+temp` →
`edge+temp`), disk (`disk+use` → `espace`).

**Consequence:** renaming an entity in HA can silently break a gauge (it will show `0` or
`--` with no error).

**Side effect to be aware of:** the temperature table's exclusions explicitly list rooms
(`bedroom`, `kitchen`, `living`, `garden`, `spa`, `secret`, `computer_room_temp`,
`technical_room_temp`). Every new room added by the Room Engine has to be added to this
list, otherwise its ambient sensor will show up in the hardware components table.

### 4.3 History — `haHistory(entity, days)`

```js
GET /api/history/period/<start_iso>
      ?filter_entity_id=<entity>
      &end_time=<now_iso>
      &minimal_response
      &no_attributes
```

- Window: **5 days** (`d*864e5` ms), called with `d = 5`.
- `minimal_response` + `no_attributes` significantly lighten the payload.
- On failure, returns `[]` (the chart stays empty, no exception).

`processHistory()` then cleans up the series:

1. filters out non-numeric points (`unavailable`, `unknown`…),
2. formats the label as `DD/MM` (`fr-FR` locale),
3. **downsamples** to ~200 points max (`step = floor(len/200)`), otherwise Chart.js would
   collapse under 5 days of minute-by-minute readings.

### 4.4 K3s statistics — separate channel 🔴 broken path

The Kubernetes cluster **does not go through the HA API**:

```js
var k3r = await fetch(HA_URL+'/local/osvision_v2/k3s_stats.json?t='+Date.now());
```

**This path is stale.** The project's `www/` folder is now called `vssp/`
(`home-assistant/www/vssp/` → `/local/vssp/`), and the pipeline no longer deploys anything
under `/local/osvision_v2/`. The `fetch` therefore always returns a 404, the `catch`
swallows the error, and the panel permanently shows *"K3s stats unavailable. Install the
k3s_stats.sh cron on the host."* — even when the cron is running fine.

**Fix, a one-line change in `core.html`:**

```js
var k3r = await fetch(HA_URL+'/local/vssp/k3s_stats.json?t='+Date.now());
```

And make sure the cron actually writes to the new folder:

```sh
# k3s_stats.sh, host side
OUT=/config/www/vssp/k3s_stats.json
```

How it works once fixed:

- A `k3s_stats.sh` script (run via cron on the host) calls `kubectl` and writes a JSON file
  to `/config/www/vssp/k3s_stats.json`.
- HA serves `/config/www/` under the `/local/` URL — no token needed here.
- The `?t=<timestamp>` parameter acts as a **cache-buster**.
- If the file is missing or invalid, `renderK3s(null)` displays the help message.

Expected JSON structure:

```json
{
  "version": "v1.29.4+k3s1",
  "node_count": 3,
  "pods_total": 87,
  "pods_running": 85,
  "deployments": 24,
  "services": 31,
  "namespaces": 12,
  "nodes": [{"name":"node1","status":"Ready","role":"control-plane",
             "cpu_capacity":"8","memory_capacity":"32Gi"}],
  "top_namespaces":  [{"ns":"default","count":14}],
  "top_deployments": [{"name":"nginx","ready":"3/3"}],
  "events": [{"time":"14:32","type":"Warning","object":"pod/x","message":"..."}]
}
```

> `k3s_stats.json` is produced on the host, not in the repo: it must **not** be versioned,
> and deployment (`rm -rf /config/www/vssp` then `mv`) overwrites it on every run. If you
> want it to survive deployments, have it write elsewhere
> (e.g. `/config/www/vssp_runtime/`) — a folder the CI does not replace.

---

## 5. Refresh loop

```js
setTimeout(init, 30000);   // last line of init()'s try block
```

There is **no WebSocket, no SSE, no EventSource**: it's **recursive polling every 30
seconds**, which replays the entire cycle:

1. `GET /api/states` (all entities),
2. entity re-discovery by keywords,
3. re-rendering the 5 gauges,
4. **4 history calls over 5 days** (CPU, RAM, network, disk),
5. destroying + recreating the 4 Chart.js instances,
6. fetching the K3s JSON,
7. rescheduling the timer.

Effective "real time" is therefore bounded by the full chain:

| Stage | Latency |
|---|---|
| Glances → system read | ~1 s (internal) |
| HA → Glances polling | 60 s by default (`scan_interval`) |
| core.html → HA polling | 30 s |
| **Actual freshness shown** | **up to ~90 s** |

Refreshing the page faster than the Glances integration's `scan_interval` therefore gains
nothing. For true real time, either lower the `scan_interval` on the HA side, or switch to
the HA WebSocket with `subscribe_events` / `state_changed`.

---

## 6. Rendering

### SVG gauges — `renderGauge(id, value, max, unit, color, subtitle)`

A **270°** arc drawn by hand in SVG (starting at −225°, radius 50, center 60/60), generated
by trigonometry with no library. Automatic color coding:

| Fill level | Color |
|---|---|
| > 80% | `#FF3D71` (red) |
| > 60% | `#FF9800` (orange) |
| otherwise | color passed as parameter |

Load Average does not use a gauge: it's a plain text block showing 1m / 5m / 15m.

### Charts — `createChart()`

**Chart.js 4.4.1** loaded from `cdnjs.cloudflare.com` (⚠️ Internet dependency). `line`-type
curves, `fill: true`, `tension: .3`, `pointRadius: 0`. The previous instance is `destroy()`'d
before recreation, which avoids memory leaks on every cycle.

### Temperature table — `renderTemps()`

Two levels of filtering:

1. `findEntities(states, ['temp'], [...])` excludes weather, forecasts, house rooms,
2. keeps only hardware sensors whose `entity_id` contains `cpu`, `core`, `nvme`, `ssd`,
   `package`, `edge`, `board`, `k10`, `it87`.

Progress bar on a **0–85 °C** scale, alert threshold **> 70 °C** (`WARN`). The Min/Max
columns are currently unfed `--` placeholders.

### Display security

`esc()` escapes `&`, `<`, `>` on every value injected via `innerHTML` — XSS protection for
data coming from HA, and especially for K3s event messages.

---

## 7. Miscellaneous

- **`clearCache()`** (the "↻ CLEAR CACHE" button): purges the browser's Cache API, then
  reloads the page with `?nocache=<timestamp>`. Useful when the HA service worker is serving
  a stale version of the file.
- **Error handling**: the whole of `init()` is wrapped in a `try/catch`; an error displays a
  red box at the bottom of the page. Note — on error, **the `setTimeout` is never reached**,
  so the loop stops for good until the page is manually reloaded.
- **CI cache-busting**: the `build` job's `find … sed` only rewrites the `?v=` of the
  `*.yaml` files in `dist/`. `core.html` is **not** covered, and isn't declared as a Lovelace
  resource anyway: it's the iframe URL in `core.yaml` that should carry a `?v=` if you want
  to force a reload after deployment. Without that, only the "CLEAR CACHE" button can unstick
  a browser that has cached the page.

---

## 8. Points of attention / improvement ideas

| Problem | Impact | Suggested fix |
|---|---|---|
| **K3s path `/local/osvision_v2/`** | K3s panel always empty, no visible error | Switch to `/local/vssp/` (§4.4) |
| `setTimeout` inside the `try` | The loop dies on the first network error | Move it into a `finally` |
| `saveToken()` calls `init()` again | Risk of multiple concurrent loops | Keep the timer id and `clearTimeout` it |
| 4 five-day history requests every 30 s | Needless load on the HA recorder | Refresh history only every 5–10 min |
| Keyword-based discovery | Silent breakage on entity rename | Explicit `entity_id` config as an override |
| Hardcoded room exclusions | Every new room pollutes the temperature table | Filter on the HA Area instead of the name |
| Chart.js via CDN | Dashboard broken offline | Host the file under `/local/vssp/js/` |
| Token in `localStorage` | Full HA access exposed to XSS | Dedicated / time-limited token |
| Hardcoded `pods_total / 330` | Wrong ratio if the node count changes | Compute `node_count × 110` |
| Temperature Min/Max columns | Always `--` | Track extremes via HA history |
| 30 s polling vs. 60 s scan | Half the cycles carry no new data | HA WebSocket `state_changed` |
| No `?v=` on the iframe | Stale version served after deployment | Add a version token to `core.yaml` |
