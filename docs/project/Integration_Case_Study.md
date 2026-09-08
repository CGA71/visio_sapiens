# Case study: integrating TECHNICAL ROOM into the `visio-sapiens` repo

**English** · [Français](Integration_Case_Study.fr.md)

> **Status: integration complete.** The files are in place, the fragment
> declares both dashboards, the pipeline embeds the LAN probe and the Livebox
> secret. This document is now a **reference sheet**: what's in place, how it
> works, and the two trade-offs that remain open.

---

## 1. Files in place — VSSP project

| File | Path in the repo | Final path in `/config` | State |
|---|---|---|---|
| Desktop view | `home-assistant/dashboards/views/technical_room.yaml` | `dashboards/views/technical_room.yaml` | ✅ |
| Mobile view | `home-assistant/dashboards/views/technical_room_mobile.yaml` | `dashboards/views/technical_room_mobile.yaml` | ✅ |
| HA package | `home-assistant/packages/vssp_technical_room.yaml` | `packages/vssp_technical_room.yaml` | ✅ |
| LAN probe | `vssp/vssp_lan_probe.py` | `/config/vssp/vssp_lan_probe.py` | ✅ deployed by CI |
| Box settings | `vssp/livebox.env` | `/config/vssp/livebox.env` | ✅ versioned |
| Box secret | *(generated at deploy time)* | `/config/vssp/.livebox.env` | ✅ CI/CD variable |

Still to add: `home-assistant/www/vssp/backgrounds/technical.png` (the
background for both views). In the meantime, `energy.png` or `core.png` do
the job — just change the URL in the final `card_mod` block of each
dashboard.

The package loads on its own: `config-fragment.yaml` sets
`homeassistant: packages: !include_dir_named packages`, and `deploy:*` copies
`packages/` **additively** (non-Visio Sapiens packages are preserved).

---

## 2. Declaration in `config-fragment.yaml` ✅ applied

Present in the fragment, right after `visio-sapiens-energy-m`:

```yaml
    visio-sapiens-technical:
      mode: yaml
      title: Technical Room
      icon: mdi:tools
      show_in_sidebar: false
      filename: dashboards/views/technical_room.yaml
    visio-sapiens-technical-m:
      mode: yaml
      title: Technical Room
      icon: mdi:cellphone-cog
      show_in_sidebar: false
      filename: dashboards/views/technical_room_mobile.yaml
```

These two `url_path` values weren't picked at random: the sidebar of
`core.yaml`, `energy.yaml` and `computer.yaml` points to
`/visio-sapiens-technical/technical`, and the **TECH** chip in
`energy_mobile.yaml` points to `/visio-sapiens-technical-m/technical`. No
existing navigation had to be changed — dead links became live ones.

Since `OSV_PREFIX` is now `"visio-sapiens"`, both entries are correctly
written into `configuration.yaml` by `vssp_apply_config.py`.

---

## 3. `.gitlab-ci.yml` ✅ patched

All three patches are in the current pipeline.

**`validate`**:

```yaml
    - test -f vssp/vssp_lan_probe.py || { echo "[ERR] vssp/vssp_lan_probe.py manquant"; exit 1; }
    - test -f vssp/livebox.env       || { echo "[ERR] vssp/livebox.env manquant"; exit 1; }
    - |
      if [ -f vssp/.livebox.env ]; then
        echo "[ERR] vssp/.livebox.env est versionne — il contient le mot de passe."
        echo "      git rm --cached vssp/.livebox.env  puis ajouter au .gitignore"
        exit 1
      fi
```

**`build`**:

```yaml
    - cp vssp/vssp_lan_probe.py dist/vssp/
    - cp vssp/livebox.env       dist/vssp/
```

**`deploy:staging`**, inside the `kubectl exec`:

```sh
        cp /config/.osv_stage/vssp/vssp_lan_probe.py /config/vssp/
        cp /config/.osv_stage/vssp/livebox.env      /config/vssp/
        chmod +x /config/vssp/vssp_lan_probe.py
```

**`deploy:production`**, inside the `ssh ha` block — the copy is essential
there: it's HA's `command_line` sensors that run the probe, whereas the
patchers themselves run inside the GitLab runner.

`hass --script check_config` validates the package; the `!include` check in
the `build` job still passes, since both dashboards only include
`../templates/button_card_templates.yaml` and
`../templates/decluttering_templates.yaml`, both present in
`dist/dashboards/templates/`.

---

## 4. Livebox credentials ✅ in place

Only one element is a secret: the box's admin password. Everything else
(`LIVEBOX_HOST`, `LIVEBOX_USER`, `LIVEBOX_IP_MODE`, `NETGEAR_PORTS`) is not a
secret — the pipeline already versions `HA_HOST: "192.168.1.26"` and
`STAGING_URL: "http://192.168.1.11:8123"`. These settings therefore live in
`vssp/livebox.env` and get changed by commit like everything else.

The password follows the same mechanism as `HA_SSH_KEY` and
`HA_TOKEN_STAGING`: a masked CI/CD variable, written into the container at
deploy time.

| Key | Value | Options |
|---|---|---|
| `LIVEBOX_PASSWORD` | Livebox admin password | Masked ✔ · Protected ✔ |

**⚠️ The Protected option has a side effect on staging.** A protected
variable is only exposed to **protected** branches and tags. Staging deploys
from MRs on `fix/*` / `features/*` branches: the variable will always be
empty there, the job will print `[avert] LIVEBOX_PASSWORD absente` and the
probes will stay in demo mode. That's consistent behavior in production
(protected tags). If you want live probes on staging, uncheck **Protected** —
knowing that the secret then becomes readable by any committer able to open
an MR.

### How the secret is transmitted

The pipeline **never** puts the password on a command line.

On staging, it's passed as an argument to the remote shell, retrieved via
`$1` — invisible in `ps` and in the logs:

```yaml
    - |
      if [ -z "$LIVEBOX_PASSWORD" ]; then
        echo "[avert] LIVEBOX_PASSWORD absente — sondes Livebox inactives."
      else
        kubectl exec -n $K3S_NAMESPACE $HA_POD -c $K3S_CONTAINER -- sh -c \
          'umask 077; printf "LIVEBOX_PASSWORD=%s\n" "$1" > /config/vssp/.livebox.env' \
          sh "$LIVEBOX_PASSWORD"
        echo "[OK] Secret Livebox deploye"
      fi
```

On production, it goes through **stdin**:

```yaml
    - |
      if [ -z "$LIVEBOX_PASSWORD" ]; then
        echo "[avert] LIVEBOX_PASSWORD absente — sondes Livebox inactives."
      else
        printf 'LIVEBOX_PASSWORD=%s\n' "$LIVEBOX_PASSWORD" \
          | ssh ha "umask 077; cat > $HA_CFG/vssp/.livebox.env"
        echo "[OK] Secret Livebox deploye"
      fi
```

The `if [ -z … ]` guard keeps the pipeline from breaking as long as the
variable doesn't exist yet: the deployment still passes, only the Livebox
probes stay `unavailable`.

`.gitignore` must contain:

```
vssp/.livebox.env
```

One-off diagnostic, without changing anything:

```sh
kubectl exec -n homeassistant <pod> -c homeassistant -- \
  python3 /config/vssp/vssp_lan_probe.py dhcp
```

---

## 5. Points noted in the repo

### 5.1 `OSV_PREFIX` ✅ fixed

`vssp/vssp_apply_config.py` now declares `OSV_PREFIX = "visio-sapiens"`, and
`OSV_RESOURCE_MARK = "/local/vssp/"`. The fragment's dashboards are therefore
correctly merged into `configuration.yaml`. The `validate` job prints, on
every run, the list of any keys that got ignored, which makes a regression
immediately visible.

The alternative — renaming the fragment's keys to `vssp-*` — remains ruled
out: it would require reworking every `navigation_path` in `home.yaml`,
`core.yaml`, `computer.yaml`, `energy.yaml`, `energy_mobile.yaml` and
`home_mobile.yaml`.

### 5.2 The `_energie` suffix has two contradictory meanings ⚠️ still open

`packages/spvs_energy_totaux.yaml` sums every `*_energie` sensor to produce
`sensor.home_energy_total`, and its note specifies that these sensors must be
**cumulative** counters — never one that resets to zero every day. But
`energy.yaml` and `energy_mobile.yaml` display these same
`sensor.technical_room_*_energie` entities under the header **"Energy
(today)."**

The two readings can't both be true at once.
`vssp_technical_room.yaml` settles the question in favor of the scan's rule:
its `*_energie` entities are `total_increasing` aliases of the Shelly
counters, and the daily counters exist in parallel under `*_energie_jour`.

To display the daily value in the device rows, replace, in both dashboards:

```yaml
energy_entity: sensor.technical_room_<appareil>_energie
# →
energy_entity: sensor.technical_room_<appareil>_energie_jour
```

The same trade-off applies to the 8 technical-room devices already listed in
`energy.yaml`, which currently point to the `*_energie` entities.

> Once `energy.yaml` is generated from `model/house.yaml` (see
> [Dashboard_Generator.md](../dashboards/Dashboard_Generator.md)), this fix will be made **in the model**, a
> single time, and will propagate to both views on the next generation. It
> may be worth waiting for that moment rather than patching both YAML files
> by hand now.

### 5.3 Missing `technical.png` background ⚠️ open

Both views reference `/local/vssp/backgrounds/technical.png`, which is absent
from the repo. Rendering falls back to an empty background. The resource
check proposed under G1 of `CI_CD.md` only covers `lovelace.resources`
entries: images referenced through `card_mod` aren't checked by anything.
