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
       │ Separate channel, partitions + K3s:        │
       │ vssp_core_stats.py (ssh, every 5 min)      │
       │ → /local/vssp/core_stats.json   (§4.4)     │
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

The page borrows the **tablet's own Home Assistant session** from the CORE dashboard around
the iframe (same origin, `sandbox allow-same-origin`): `window.parent.document
.querySelector('home-assistant').hass.auth`. `hass.auth` refreshes its short-lived token by
itself, which matters here since the page polls every 30 s for as long as it stays open. A
new tablet therefore only has to log in to Home Assistant.

The pasted long-lived token (`localStorage` key `vssp_ha_token`) is only the fallback for
`core.html` opened on its own, outside the dashboard; without a session and without it, the
page shows a small login form.

`/local/` files (`core_stats.json`, `core_scan_*.json`, `infra_updates.json`) need no token,
and the SCAN webhook is unauthenticated but `local_only`.

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

### 4.4 Partitions and k3s — the host collector

Glances, through Home Assistant, reports `/` once and then every kubelet volume bind-mounted
from it (dozens of identical rows, never `/boot/efi`), and knows nothing about the cluster.
Both come from **`vssp/vssp_core_stats.py`**, run every 5 minutes (and 2 minutes after a
Home Assistant start) by the automation *CORE : collecte hôte et cluster*
(`packages/vssp_core.yaml`):

```
vssp_core_stats.py ──ssh (credentials from the safe, vssp-maint)──► host
   LC_ALL=C df -P -T -B1 / df -P -i      → partitions (kubelet bind mounts filtered out)
   nproc, /etc/os-release, uname -r      → cores, OS, kernel
   systemctl is-active k3s, k3s --version
   k3s kubectl get nodes,pods,deployments,statefulsets,daemonsets,pvc,services,namespaces -A -o json
   k3s kubectl get events -A --field-selector type=Warning -o json
   k3s kubectl top nodes                 → CPU / memory load (metrics-server)
   openssl x509 -enddate (API server certificate)
        │
        ▼
/config/www/vssp/core_stats.json  →  /local/vssp/core_stats.json
```

- Same door as `vssp_infra_updates.py` (it reuses its `Safe` and `open_host`): the host
  credentials live in the safe, the script holds them for one run, Home Assistant only ever
  sees the JSON. `kubectl` goes through `run_maybe_sudo` — `k3s.yaml` is `0600 root` on this
  host. **Every command is a read**; nothing is written on the host.
- **Sealed safe** (the usual state after a host reboot): the file is rewritten with the last
  measurement marked `stale` and the safe's `message_key`; the page says so, shows the
  partitions from Glances, and for the cluster falls back to the old host timer's file (next
  point).
- **The old host timer.** Until now the panel was fed by `/opt/osvision/k3s_stats.sh`, a root
  systemd timer (`k3s-stats.timer`, every 60 s) installed by hand on the host, outside this
  repository, writing into the HA volume at `www/osvision_v2/k3s_stats.json`. Its version is
  always empty (`kubectl version --short` no longer exists) and its event messages are cut to
  their last word. `core.html` only reads it when `core_stats.json` has no cluster data, and
  labels it *basic data only*. Once the collector is confirmed, the timer can be removed:
  `sudo systemctl disable --now k3s-stats.timer osvision-k3s-stats.timer`.

Main fields of `core_stats.json`:

```json
{
  "ok": true, "stale": false, "message_key": "stats.ok", "generated": "…", "measured": "…",
  "host": {"cpus": 24, "os": "Ubuntu 26.04.1 LTS", "kernel": "…",
           "partitions": [{"mount": "/", "device": "/dev/sda2", "fs": "ext4",
                           "size": 490164953088, "used": …, "avail": …, "pct": 26, "inodes_pct": 4}]},
  "k3s": {"service": "active", "version": "v1.36.4+k3s1", "reachable": true,
          "nodes": [{"name": "k3s-master", "ready": true, "pressure": [], "cpu_pct": 6, "mem_pct": 41, "pods_capacity": 110, …}],
          "pods": {"total": 12, "running": 11, "pending": 0, "failed": 0, "not_ready": 0, "restarts": 3},
          "problem_pods": [{"ns": "…", "name": "…", "reason": "CrashLoopBackOff", "restarts": 14}],
          "workloads": {"deployments": 8, "unavailable": [], "top": […]},
          "pvc": {"total": 3, "not_bound": []}, "events": [{"time": "…", "reason": "BackOff", …}],
          "cert_days": 320}
}
```

`/config/www/vssp/` is replaced on every deployment: the file disappears with it and comes
back at the next run (at most 5 minutes, or 2 minutes after the restart that follows the
deployment).

---

## 5. Refresh loop

`cycle()` runs `refresh()` every 30 s and **reschedules itself in `finally`**: a network error
shows a red box and the next cycle clears it (it used to stop the loop for good). Each cycle:

1. `GET /api/states` (all entities) and keyword discovery,
2. `core_stats.json`, `infra_updates.json` (and, as a fallback, the old `k3s_stats.json`),
3. gauges, partitions, temperatures, the K3s panel, both recommendation boxes,
4. the **four 5-day history charts only every 5 minutes** — Glances itself refreshes every
   60 s, and four five-day queries every 30 s weighed on the recorder for nothing.

| Stage | Latency |
|---|---|
| Glances → system read | ~1 s (internal) |
| HA → Glances polling | 60 s by default (`scan_interval`) |
| Host collector (partitions, k3s) | 5 min |
| core.html → HA / files | 30 s |

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
- **Error handling**: `refresh()` runs inside `cycle()`'s `try/catch/finally`; an error shows
  a red box at the bottom of the page, and the next cycle — always rescheduled — clears it.
- **Cache-busting**: the iframe URL in `core.yaml.j2` carries `?v={{ build_stamp }}` (and
  `&lang={{ locale }}`), so a deployment reaches every tablet; "CLEAR CACHE" keeps both
  parameters when it reloads.

---

## 8. Points of attention / improvement ideas

| Problem | Impact | Status / suggested fix |
|---|---|---|
| ~~K3s path `/local/osvision_v2/`~~ | K3s panel fed by an out-of-repo timer | **Fixed**: `vssp_core_stats.py` → `/local/vssp/core_stats.json`; the old file is a fallback only |
| ~~`setTimeout` inside the `try`~~ | The loop died on the first network error | **Fixed**: rescheduled in `finally` |
| ~~4 five-day history requests every 30 s~~ | Needless load on the recorder | **Fixed**: every 5 min |
| ~~French only~~ | CORE in French on an English interface | **Fixed**: `?lang=` from `core.yaml.j2` |
| ~~No `?v=` on the iframe~~ | Stale version after deployment | **Fixed**: `?v={{ build_stamp }}&lang={{ locale }}` |
| ~~Hardcoded `pods_total / 330`~~ | Wrong ratio | **Fixed**: sum of the nodes' allocatable pods |
| Keyword-based discovery | Silent breakage on entity rename | Explicit `entity_id` config as an override |
| Hardcoded room exclusions | Every new room pollutes the temperature table | Filter on the HA Area instead of the name |
| Chart.js via CDN | Charts missing offline | Host the file under `/local/vssp/js/` |
| Orphaned Glances entities (one per kubelet volume) | Hundreds of `unavailable` sensors | Hide `/var/lib/kubelet/.*` in `glances.conf` (the page recommends it when there are ≥ 10) |
| Temperature Min/Max | Removed (they were always `--`) | Track extremes via HA history if wanted |

---

## 9. Recommendations and SCAN

### Recommendation boxes

Two framed boxes, **SYSTEM RECOMMENDATIONS** (next to the partitions) and **K3S
RECOMMENDATIONS** (under the cluster KPIs), turn what is on screen into advice. They are
computed in the page (`systemRecs()`, `k3sRecs()`), in the language of `?lang=`, every
cycle. Each finding has a severity, a sentence, and the read-only command to start with; the
worst severity colours the frame.

| Box | Rules |
|---|---|
| System | CPU ≥ 75/90 %, RAM ≥ 80/90 %, swap ≥ 50 %, 15-min load above the core count (×1.5 = critical), component ≥ 75/85 °C, partition ≥ 80/90 % (specific advice for `/` — kubelet image GC at 85 %, eviction at 90 % — and `/boot`), inodes ≥ 85 %, ≥ 10 orphaned Glances entities, collector missing / blocked by a sealed safe / older than 15 min |
| K3s | k3s service not `active`, API not answering, node NotReady, Disk/Memory/PID pressure, node CPU/memory ≥ 85 %, pods in CrashLoopBackOff / image pull failure / OOMKilled / Pending > 5 min / Failed, ≥ 10 restarts, workloads not fully available, PVC not bound, warning events in the last 24 h, pods ≥ 80 % of capacity, API certificate < 90 / < 30 days, k3s update pending on the UPDATES screen |

### SCAN

Each box has a **SCAN** button that asks the chat assistant configured in the console to look
its findings up **on the internet** and bring back what to do, with its sources.

```
core.html ──POST /api/webhook/vssp_core_scan {payload_b64}──► automation (local_only, base64 checked)
   ──► shell_command.vssp_core_scan ──► vssp_core_scan.py --detach
         writes core_scan_<scope>.json {state: "running"}, forks, returns (HA kills a shell_command at 60 s)
         child: provider + web search → core_scan_<scope>.json {state: "done", summary, items, citations}
core.html polls /local/vssp/core_scan_<scope>.json every 3 s until it carries its request_id
```

- **Provider**: `input_select.vssp_chatbot_provider` and its key file (`/config/vssp/.<provider>_key`),
  shared with the chat bubble (the key is set with `input_text.vssp_<provider>_api_key` then
  `script.vssp_save_<provider>_key`). Claude runs on `claude-opus-5` with the `web_search_20260209`
  tool (5 searches at most, server-side fallback on refusal), whatever older model the chat
  uses; Gemini uses `google_search` grounding and ChatGPT the Responses API `web_search`
  tool, each with the model set in the console. The custom provider has no web search: SCAN
  says so. Only the Claude path has been exercised end to end.
- **What leaves the house**: the finding texts as the page wrote them, the OS, kernel and k3s
  versions, the core count and the memory size. Never the hostname; anything shaped like an
  IPv4 address is masked by the script anyway. Each scan is a paid API call: it only ever runs
  on a press of the button.
- **Result**: summary, one item per finding (advice, commands, sources), then the pages cited.
  The last result of each box stays on screen until the next deployment. The page reminds the
  reader to check the sources before applying anything.
