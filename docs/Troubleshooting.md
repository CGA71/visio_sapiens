# Visio Sapiens — Troubleshooting & postmortems

**English** · [Français](Troubleshooting.fr.md)

This document brings together three field postmortems: why the deployment
seemed to never reach staging, why the ENERGY tables stayed empty after a
sync that reported success, and an FAQ-style troubleshooting sheet for the
ADMIN panel. Each case keeps its narrative shape — symptom, cause, fix or
diagnostic commands — so it can double as source material for a future
"debugging sessions" video episode.

---

## 1. Deployment doesn't reach staging

> **Status: both historical causes below are fixed in the repo.**
> This section still earns its keep as a record of the symptom (green
> pipeline, unchanged staging) and, above all, for its verification
> procedure, which has been updated and completed with the gaps that are
> still open.

### Cause 1 — `deploy:staging` never restarted Home Assistant ✅ fixed

Original sequence of the job:

```
5.  kubectl cp of the package
6.  untar + copy of dashboards / www / packages / vssp
7.  writing the Livebox secret
8.  vssp_apply_config.py + ensure_packages + sanitize_resources
9.  hass --script check_config
10. cleanup
11. echo "[OK] Staging a jour"          ← end of job
```

`deploy:production` ran `ha core restart` at the equivalent step; staging
did not. But `configuration.yaml` is only re-read at startup:
`lovelace.dashboards` and `homeassistant.packages` cannot be hot-reloaded.
The patcher wrote correctly, `check_config` validated, the job went green —
and the instance kept serving the old configuration. Since the dashboard
files themselves were indeed replaced on disk, the result was the misleading
effect of a "half-applied" deployment.

**Current state of `.gitlab-ci.yml`** — the job now ends with:

1. `POST $STAGING_URL/api/services/homeassistant/restart` using `HA_TOKEN_STAGING`;
2. if the HTTP status is not 200 (or the token is missing): fall back to
   `kubectl delete pod` + `kubectl wait --for=condition=ready`;
3. wait for the API to respond (36 attempts × 5 s, i.e. 3 min) so that
   `test:staging` doesn't run against an instance that is still starting up;
4. print the version actually present in the container.

The job now concludes with `[OK] HA redemarre et joignable`.

### Cause 2 — `OSV_PREFIX` prevented dashboards from being written ✅ fixed

The patcher filtered which keys got merged:

```python
OSV_PREFIX = "vssp"                                   # old
_merge_named(dboards, src["dashboards"], only_prefix=OSV_PREFIX)
```

Since the fragment's keys were `visio-sapiens`, `visio-sapiens-core`,
`visio-sapiens-energy`, etc., and `"visio-sapiens".startswith("vssp")`
evaluated to `False`, no entry in `lovelace.dashboards` was ever written.
The `resources`, on the other hand, are merged with no prefix filter — which
is why visual updates went through while the new dashboards never appeared.

**Current state of `vssp/vssp_apply_config.py`**:

```python
OSV_PREFIX = "visio-sapiens"
OSV_RESOURCE_MARK = "/local/vssp/"
```

This was the option that preserves existing URLs and every `navigation_path`
already deployed. The `validate` job also carries a non-blocking check that
compares `OSV_PREFIX` against the fragment's keys and prints
`[OK] N dashboard(s) du fragment couverts par OSV_PREFIX='visio-sapiens'`.

### Gaps still open (to address before the next diagnostic)

If staging still looks incomplete, it's no longer the two causes above. The
current candidates, detailed in `CI_CD.md`:

| # | Observable symptom | Cause |
|---|---|---|
| G1 | Unstyled UI, 404 on `/local/vssp/css/osvision.css`; `test:staging` red on JS | The URLs in `config-fragment.yaml` and in the smoke test no longer match the real files (`css/vssp.css`, `js/osvision.js`) |
| G2 | DISCOVERY / UPGRADE buttons have no effect, `shell_command` errors | `vssp_discovery.py`, `vssp_upgrade.py`, `vssp_admin_config.yaml` are not copied into `dist/` |
| G4 | `cat /config/VSSP_VERSION` fails even though the deployment succeeded | The pipeline still writes `/config/OSVISION_VERSION` |
| — | Livebox sensors `unavailable` on staging only | `LIVEBOX_PASSWORD` is marked **Protected**: it isn't exposed to MRs on unprotected branches |

### Verify the real state of your staging

```sh
POD=$(kubectl get pod -n homeassistant -l app=homeassistant \
      -o jsonpath='{.items[0].metadata.name}')

# 1. Which version did the container actually receive?
#    (the pipeline still writes OSVISION_VERSION — see G4 in CI_CD.md)
kubectl exec -n homeassistant $POD -c homeassistant -- \
  sh -c 'cat /config/VSSP_VERSION 2>/dev/null || cat /config/OSVISION_VERSION'

# 2. Did the patcher write the dashboards?
kubectl exec -n homeassistant $POD -c homeassistant -- \
  sed -n '/^lovelace:/,/^[a-z]/p' /config/configuration.yaml

# 3. Does the deployed fragment actually contain the new entries?
kubectl exec -n homeassistant $POD -c homeassistant -- \
  grep -A2 technical /config/config-fragment.yaml

# 4. How long has the pod been running? (older than the deployment = never restarted)
kubectl get pod -n homeassistant $POD -o wide

# 5. Backups created by the patcher, in chronological order
kubectl exec -n homeassistant $POD -c homeassistant -- \
  ls -lt /config/backups/ | head

# 6. Do the declared resources actually exist on disk? (cause G1)
kubectl exec -n homeassistant $POD -c homeassistant -- \
  sh -c 'ls -l /config/www/vssp/css /config/www/vssp/js'
kubectl exec -n homeassistant $POD -c homeassistant -- \
  grep '/local/vssp/' /config/configuration.yaml

# 7. Are the ADMIN panel tools deployed? (cause G2)
kubectl exec -n homeassistant $POD -c homeassistant -- ls -l /config/vssp/

# 8. Did the Livebox secret arrive?
kubectl exec -n homeassistant $POD -c homeassistant -- \
  sh -c 'test -f /config/vssp/.livebox.env && echo present || echo absent'
```

#### Reading the results

- **1 shows the right version, 2 shows no dashboards** → the patcher is
  running and skipping the keys. Check `OSV_PREFIX` (should already be set
  correctly).
- **2 shows the dashboards fine, but the UI doesn't offer them** → HA hasn't
  restarted. Confirmed by the pod age in 4 (should already be fixed).
- **1 shows an old version, or fails** → either the package never arrived,
  or it's the filename (G4). On the pipeline side: `workflow:` only creates a
  pipeline on a Merge Request, on `master`, or on a tag. A push to `fix/*` or
  `features/*` without an MR triggers **nothing** — an easy case to miss.
- **6 shows a declared CSS/JS file that's absent from disk** → G1. The UI
  loads with no visual identity, with no error at all in the HA log.
- **7 only shows the patchers and the sensor** → G2, the ADMIN panel is
  inert.
- **8 shows `absent` on staging but `present` in production** → the
  **Protected** flag on `LIVEBOX_PASSWORD`, not a pipeline bug.

### Application order

1. ~~`OSV_PREFIX = "visio-sapiens"` in `vssp/vssp_apply_config.py`~~ ✅ done
2. ~~HA restart in `deploy:staging`~~ ✅ done
3. Fixes G1 → G5 from `CI_CD.md`
4. Open an MR or push to `master` — otherwise no pipeline runs at all

---

## 2. ENERGY sync writes nothing

### What your screenshots show

Good news first: the dashboard **is** now generated from the template. The
messages "Aucun appareil detecte" and "Aucun circuit detecte" are exactly
what the template displays when the model is empty — a hand-written file
would not contain them. The first two links in the chain (template +
generator) are working.

What's missing: `model/energy_devices.yaml` was never written by the scan.

### Why the notification claimed 10 devices

It was displaying `sensor.vssp_appareils_mesures`, which counts the
`*_power` entities exposed by Home Assistant — **not** what the scan
actually managed to write. Your 10 devices do exist in HA (the selftest
confirmed it), but the scan failed to produce the file. The notification
was therefore misleading: this is now fixed — it compares the two values
and reports an explicit failure when the model is empty.

Second fixed defect: `continue_on_error: true` on the scan step meant its
failure went unnoticed and generation ran anyway — overwriting the
dashboard with an empty model. Removed.

### The three commands that give you the answer

```sh
NS=homeassistant; POD=homeassistant-855dc8cb66-gbmvb; C=homeassistant

# 1. The last scan's report (the cause is written there in black and white)
sudo kubectl -n $NS exec $POD -c $C -- cat /config/www/vssp/energy_sync_status.json

# 2. Was the model actually written?
sudo kubectl -n $NS exec $POD -c $C -- ls -l /config/dashboards/model/

# 3. Is the token in place?
sudo kubectl -n $NS exec $POD -c $C -- sh -c 'ls -l /config/vssp/.ha_token 2>&1; wc -c < /config/vssp/.ha_token 2>/dev/null'
```

### The most likely cause

The "Login attempt failed" message you saw right before is the symptom: the
`shell_command` passes along the token read from `input_text.vssp_ha_token`,
which is empty. The scan receives an empty token, Home Assistant returns
401, and the scan stops without writing anything.

**Immediate fix** — create the token file on the pod:

```sh
sudo kubectl -n $NS exec $POD -c $C -- sh -c \
  'printf "%s" "VOTRE_NOUVEAU_JETON" > /config/vssp/.ha_token && chmod 600 /config/vssp/.ha_token'
```

Then verify the scan sees your devices, without writing anything:

```sh
sudo kubectl -n $NS exec $POD -c $C -- python3 /config/vssp/vssp_energy_sync.py \
  --dry-run --devices /config/dashboards/model/energy_devices.yaml
```

The output should list your 10 devices. Only after that should the SYNC
ENERGY button in the ADMIN panel write the model and regenerate the tables.

**Warning**: the `.ha_token` file lives in `/config/vssp/`, which gets wiped
on every CI deployment. For it to survive, use the `vssp_save_token` script
instead (it copies the helper back to the file after every deployment), or
declare the token in `secrets.yaml`.

### New diagnostic sensors

The package adds three sensors that make this diagnosis visible without a
command line:

| Sensor | Meaning |
|---|---|
| `sensor.vssp_appareils_mesures` | devices `*_power` exposed by HA |
| `sensor.vssp_modele_appareils` | devices actually written into the model |
| `sensor.vssp_modele_circuits` | circuits written into the model |
| `sensor.vssp_sync_resultat` | `ok`, `echec`, or `jamais_lance` |

A gap between the first two means exactly what you're experiencing: Home
Assistant knows about the devices, but the scan couldn't write them.

---

## 3. ADMIN panel FAQ

### "script.vssp_… not found" / "Entity not found"

Same cause in both cases: the ADMIN configuration file isn't being loaded by
Home Assistant. The `script.vssp_*`, `input_text.vssp_*`, and
`binary_sensor.vssp_dashboard_*` entities therefore don't exist, and the
buttons call unknown services.

**The simplest fix in your setup**: the file ships as a package,
`home-assistant/packages/vssp_admin.yaml`. Your CI already copies
`home-assistant/packages/.` into `dist/packages/` → `/config/packages/`, and
`config-fragment.yaml` sets `packages: !include_dir_named packages`. So it
gets loaded without adding anything to `configuration.yaml`.

**Check in this order:**

1. Is the file on the pod?
   `kubectl -n home-assistant exec home-assistant-0 -c home-assistant -- ls /config/packages/`
2. Is the loading key in place?
   `grep -A2 "^homeassistant:" /config/configuration.yaml`
   (it's set automatically by `vssp_ensure_packages.py`)
3. **Restart Home Assistant.** `input_text` and `command_line` declared in
   YAML do not hot-reload. For scripts alone, Developer Tools → YAML →
   Reload Scripts is enough.
4. Developer Tools → States, search `vssp`: the entities
   `script.vssp_run_energy_sync`, `binary_sensor.vssp_dashboard_energy_present`,
   and `input_text.vssp_ha_token` should appear.

If the file is indeed in `/config/packages/` but the entities still don't
appear, check Settings → Logs: a merge error (a key duplicated with another
package) will be explicit there.

### "Entity not found" (yellow banner) — detailed case

A card references an entity Home Assistant doesn't know about.

In the screenshot, it's the `entities` card in the DELETE zone, which shows
`input_text.vssp_pin_entry`. The helper doesn't exist yet: the `input_text`
entries from `vssp/vssp_admin_config.yaml` aren't loaded.

**Check** — Developer Tools → States, search for `input_text.vssp_`. If
there are no results:

1. Drop `vssp_admin.yaml` into `home-assistant/packages/` (see previous
   section), deploy, restart.
2. Set the admin code once: run the `vssp_set_admin_pin` script after
   putting your real value into it.
3. Fill in `input_text.vssp_ha_token` with a long-lived token
   (Profile → Long-Lived Access Tokens) — without it, `vssp_discovery` and
   `vssp_energy_sync` run with an empty token.

**Note**: the `input_text.vssp_ha_token` helper was missing from the
previous version of the file even though `vssp_discovery` and
`vssp_energy_sync` use it. It is now declared — without it, those commands
were running with an empty token.

### "ButtonCardJSTemplateError" (red banner)

A button-card JS template threw an exception. The most common cause:
accessing `.state` on an entity that's absent.

```js
// ✗ throws if the entity doesn't exist
states['sensor.x'].state

// ✓ systematic guard
var s = states['sensor.x'];
return s ? s.state : 'valeur par defaut';
```

This was the case for the CORE button, which read
`binary_sensor.vssp_dashboard_core_present` with no guard. Fixed in
`admin/system_dashboards.yaml`: both JS blocks are now guarded and tested
with zero entities available.

### The CREATE ENERGY button doesn't appear

Symptom visible in the screenshot: the "System dashboards" section only
shows SYNC ENERGY and CORE.

The two conditional cards were testing `state: "off"` and `state: "on"`.
When `binary_sensor.vssp_dashboard_energy_present` doesn't exist, the state
is neither one nor the other: **neither** button was displayed — exactly in
the situation where the CREATE button is needed most.

Fixed: the display condition for CREATE was changed to `state_not: "on"`,
which also covers a missing entity, `unknown`, or `unavailable`. The
guardrail against overwriting stays on the generator side (`--if-missing`),
not on the UI side — a button's visibility must never be the only
safeguard.

A diagnostic banner also now appears in the card when the state sensors are
unavailable, to signal that the ADMIN configuration isn't loaded rather than
leaving inert buttons.

### The buttons appear but "do nothing"

The `shell_command` entries run inside the Home Assistant container. Check
in this order:

1. **Are the Python scripts on the pod?**
   `ls /config/vssp/generate_dashboards.py /config/vssp/vssp_energy_sync.py`
   If missing: the CI `build` job isn't copying them into `dist/vssp/` yet —
   see `PATCH_gitlab-ci.md` (two lines to add).
2. **Are the dependencies present?** `python3 -c "import jinja2, yaml"` —
   if not, `pip install jinja2 pyyaml` inside the container, or add the
   dependency to your image.
3. **Do the target folders exist?**
   `mkdir -p /config/www/vssp /config/vssp/backups /config/home-assistant/dashboards/model`
4. **The JSON report** tells you the rest:
   `cat /config/www/vssp/energy_generate_status.json`
   (`errors` key when the model is invalid).

`shell_command` logs appear in Settings → Logs along with the command's
return code.

### The dashboard is generated but missing from the sidebar

The file exists (`binary_sensor.vssp_dashboard_energy_present` is `on`) but
no entry appears: it's the Lovelace declaration that's missing, not the
generation. Check the `lovelace: dashboards:` block in
`config-fragment.yaml` — `vssp-energy` must point to
`home-assistant/dashboards/views/energy.yaml`. A restart is required after
adding an entry (hot reload only covers content, not the declaration
itself).

### Note on pod paths

CI deploys `home-assistant/dashboards/` to **`/config/dashboards/`** (not
`/config/home-assistant/dashboards/`), `home-assistant/packages/` to
`/config/packages/`, `vssp/` to `/config/vssp/`, and `home-assistant/www/`
to `/config/www/`.

The `shell_command` paths are aligned with this:

| In the repo | On the pod |
|---|---|
| `home-assistant/dashboards/views/energy.yaml` | `/config/dashboards/views/energy.yaml` |
| `home-assistant/dashboards/model/house.yaml` | `/config/dashboards/model/house.yaml` |
| `home-assistant/dashboards/templates_j2/` | `/config/dashboards/templates_j2/` |
| `home-assistant/packages/vssp_admin.yaml` | `/config/packages/vssp_admin.yaml` |
| `vssp/generate_dashboards.py` | `/config/vssp/generate_dashboards.py` |

`generate_dashboards.py`'s defaults use **repo** paths (for running it from
the repository root); the `shell_command` entries pass **pod** paths
explicitly.

### "The action script.vssp_… uses action lovelace.reload which was not found"

`lovelace.reload` **does not exist** in Home Assistant. The `lovelace`
domain exposes only one service, `lovelace.reload_resources`, which
reloads the JS/CSS resources declared in `lovelace.resources` — not the
dashboards.

Home Assistant refuses to run a script when a step references an unknown
service: the script stops at that line, even if the previous steps
succeeded. That's why the message appears even though the sync itself may
well have completed successfully.

**Fixed**: the calls were removed from `vssp_admin.yaml` and
`vssp_energy_totaux.yaml`.

**Why nothing replaces them**: a dashboard in YAML mode is re-read
automatically. Home Assistant caches the configuration keyed on the file's
modification time and reloads it as soon as that changes. The only
remaining cache is the browser's, for a tab that's already open — hence the
prompt to press Ctrl+Shift+R in the notifications.

What does require a real restart, on the other hand, is adding an **entry**
to a dashboard in `lovelace: dashboards:` — not modifying its content.

#### Verify a service exists before calling it

Developer Tools → Actions: the picker only offers services that are
actually registered. Typing `lovelace.` there shows only
`reload_resources`, which confirms the diagnosis in two seconds.
