# Visio Sapiens — CI/CD, complete reference

**English** · [Français](CI_CD.fr.md)

Reference document for the `.gitlab-ci.yml` pipeline **as it actually stands
in the repository**, followed by the remaining gaps and their fixes.

This document folds in and supersedes `CI_Integration.md`, which described a
single earlier evolution (the `configuration.yaml` patch) and still used the
old `osvision/` naming. A short summary of that design decision is kept at
the end, under [Design history](#design-history--how-we-got-here).

---

## 1. Overview

A package is built **exactly once** and deployed as-is to both targets; only
the transport channel changes.

```
                          ┌──────────────┐
   MR / master  ─────────►│              │──► deploy:staging  (kubectl cp)  ──► k3s
                          │    build     │
   tag          ─────────►│  visio-      │──► deploy:production (ssh/scp)   ──► HAOS 18.1
                          │  sapiens.tgz │
                          └──────────────┘
```

| Stage | Jobs | Trigger |
|---|---|---|
| `validate` | `validate` | MR, `master`, tag |
| `build` | `build`, `package:hacs` | `build`: MR/master/tag · `package:hacs`: tag |
| `deploy` | `deploy:staging`, `deploy:production` | staging: MR/master · prod: tag + **manual gate** |
| `test` | `test:staging`, `test:production`, `rollback:production` | same, rollback manual |
| `release` | `release` | tag |

### The `workflow:` rule — pitfall #1

```yaml
workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == "master"
    - if: $CI_COMMIT_TAG
    - when: never
```

A push to `fix/*` or `features/*` **with no open MR triggers no pipeline at
all**. This is the first thing to check when diagnosing "nothing's moving on
staging".

### Versioned variables (`variables:`)

`PACKAGE_NAME: visio-sapiens` · `K3S_NAMESPACE: homeassistant` ·
`K3S_CONTAINER: homeassistant` · `STAGING_URL: http://192.168.1.11:8123` ·
`HA_HOST: 192.168.1.26` · `HA_SSH_PORT: 22222` · `HA_SSH_USER: root` ·
`PROD_URL: http://192.168.1.26:8123` · `PROD_RESTART_CORE: "true"`

### CI/CD variables to create (Settings → CI/CD → Variables)

| Key | Type | Options | Role |
|---|---|---|---|
| `HA_SSH_KEY` | File | Protected ✔ | private key to reach HAOS |
| `HA_TOKEN_STAGING` | masked | — | long-lived k3s token (restart + smoke test) |
| `HA_TOKEN_PROD` | masked | — | long-lived HAOS token (smoke test) |
| `LIVEBOX_PASSWORD` | masked | Masked ✔ | Livebox admin password |

> **Watch the "Protected" option on `LIVEBOX_PASSWORD`.** A protected
> variable is only exposed to protected branches and tags. But staging
> deploys from MRs on `fix/*` / `features/*`, which are not protected: the
> variable will always come through empty and the job will print
> `[avert] LIVEBOX_PASSWORD absente`. In production (protected tags) it goes
> through fine. Two options: uncheck **Protected** (the secret becomes
> readable by any committer allowed to open an MR), or accept that the
> Livebox probes stay in demo mode on staging. That's a trade-off, not a bug.

---

## 2. Job `validate`

`alpine` image, `python3 + py3-yaml`. It checks, in order:

1. **Structure**: `home-assistant/dashboards`, `home-assistant/templates`,
   `themes/visio_sapiens.yaml` (at the **repo root**, required by HACS),
   `home-assistant/www/vssp`, `hacs.json`, `repository.yaml`.
2. **Config patch**: `home-assistant/config-fragment.yaml`,
   `vssp/vssp_apply_config.py`, `vssp/vssp_ensure_packages.py`,
   `vssp/vssp_sanitize_resources.py`.
3. **LAN probe**: `vssp/vssp_lan_probe.py`, `vssp/livebox.env`.
4. **Secret leak**: fails if `vssp/.livebox.env` is checked in.
5. **`OSV_PREFIX` consistency** (non-blocking): reads the prefix from
   `vssp_apply_config.py`, compares it to the `lovelace.dashboards` keys in
   the fragment, and lists the ones that would be ignored.
6. **Single theme source**: fails if `home-assistant/themes/` still exists
   (duplicate source alongside the root-level `themes/`).
7. **YAML syntax** of `home-assistant/**/*.yaml` + `themes/*.yaml`, using a
   multi-constructor that accepts HA tags (`!include`, `!secret`, …) without
   interpreting them.

---

## 3. Job `build`

Produces `dist/`, a mirror image of `/config`:

```
dist/
├── dashboards/            ← home-assistant/dashboards/. (incl. views/, model/, templates_j2/)
│   └── templates/         ← home-assistant/templates/.   (target of !include ../templates/)
├── themes/                ← themes/.  (root)
├── www/                   ← home-assistant/www/.
├── packages/              ← home-assistant/packages/.
├── vssp/                  ← patchers + LAN probe + livebox.env
├── config-fragment.yaml
└── OSVISION_VERSION
```

Points worth knowing:

- **Cache-busting**: `find dist -name '*.yaml' ! -name 'config-fragment.yaml'`
  replaces `?v=…` in the `/local/vssp/…` URLs. The fragment is **excluded**
  since it uses the `__VTOKEN__` placeholder, substituted later by
  `--vtoken`.
- **`!include` check**: a Python script walks `dist/**/*.yaml` and verifies
  that every `!include` / `!include_dir_*` target exists **in the tree as it
  will be laid out on `/config`**, not in the repo. That's why
  `home-assistant/templates/` is copied to `dist/dashboards/templates/`.
- **Artifacts**: `visio-sapiens.tar.gz` + `.osv_version` (30 days).

`package:hacs` (tags only) builds a separate, theme-only package:
`themes/`, `hacs.json`, `repository.yaml`, `README.md`, `CHANGELOG.md`,
`VERSION`.

### `vssp_mcp/` — deployed, but not run by Home Assistant

`dist/vssp_mcp/` carries the [MCP server](../platform/MCP_Server.md)'s Python
package, and both deploy jobs copy it to `/config/vssp_mcp`. It is the only
thing in the package that Home Assistant itself never imports: it is *stored*
on the instance and *read* by whichever container serves it — the `vssp-mcp`
add-on on Home Assistant OS, or the k3s pod in `kubernetes/mcp/`.

That is why it sits beside `vssp/` rather than inside it. Everything under
`vssp/` is executed by Home Assistant, through `command_line` sensors and
`shell_command`s, so it must stay **stdlib + pyyaml** — a Home Assistant OS
appliance is not somewhere you ask a user to run `pip install`. The MCP server
needs the MCP SDK, and gets it from its container. The rule was never "no
dependencies"; it was "nothing the appliance has to install for you", and this
separation is what keeps it absolute instead of becoming "stdlib, except when".

Shipping the code this way means a new version of the server arrives with an
ordinary deploy — no add-on rebuild, no image to push, and nothing that needs a
container registry (this GitLab has none enabled).

Unlike `vssp/`, the copy is **wholesale, not additive**: `/config/vssp_mcp` is
removed and rewritten on every deploy. Nothing local belongs in it, so a file
deleted from the repository has to disappear from the instance too.

---

## 4. Job `deploy:staging` (k3s)

`bitnami/kubectl` image. Actual sequence:

1. resolve the pod (`-l app=homeassistant`, falling back to the first pod in
   the namespace);
2. `kubectl cp` the package to `/config/.osv.tar.gz`;
3. `kubectl exec`: untar into `/config/.osv_stage`, swap `dashboards`/`themes`
   (with an `.old` safety copy), replace `/config/www/vssp`, copy the
   `vssp/` scripts, `config-fragment.yaml`, `chmod +x` the probe, **additive**
   copy of `packages/`;
4. write the Livebox secret — the password is passed as a shell **argument**
   on the remote side (`sh "$LIVEBOX_PASSWORD"` → `$1`), never inline in the
   command: invisible in `ps` and in the logs;
5. verify `ruamel.yaml` imports on the pod, installing it
   (`pip install ruamel.yaml --break-system-packages`) if it does not, and
   failing the job if it still doesn't import afterward — needed by
   `vssp_apply_config.py` next, and by `vssp_assign_apply.py` /
   `vssp_rooms_apply.py` later at runtime;
6. `vssp_apply_config.py` → `vssp_ensure_packages.py` →
   `vssp_sanitize_resources.py`;
7. `hass --script check_config`; on failure: restore `dashboards`/`themes`
   from `.old` **and** `configuration.yaml` from the latest
   `/config/backups/configuration_*.bak`, then `exit 1`;
8. clean up the `.old` / `.osv_stage` leftovers;
9. **restart Home Assistant**: `POST /api/services/homeassistant/restart`
   with `HA_TOKEN_STAGING`, falling back to `kubectl delete pod` if the token
   is missing or the HTTP code isn't 200;
10. wait for the API to come back (36 × 5 s) so that `test:staging` doesn't
    run against an instance that's still starting up;
11. **re-resolve the pod name and re-verify `ruamel.yaml`**: the
    `kubectl delete pod` fallback in step 9 recreates the pod from the
    image, wiping whatever step 5 installed into the old one's filesystem.
    Re-checking against whichever pod is serving now (same install-or-fail
    logic as step 5) is what catches that case instead of leaving
    `vssp_assign_apply.py` broken on a pod nobody suspects just restarted;
12. log the version actually present in the container.

Step 9 is essential: `lovelace.dashboards` and `homeassistant.packages`
**cannot** be hot-reloaded (see [Troubleshooting.md](Troubleshooting.md)).

---

## 5. Job `deploy:production` (HAOS via SSH)

Tags only, `when: manual`.

1. `HA_CFG` detected (`/homeassistant` or `/config`);
2. `ha backups new --name pre-$CI_COMMIT_TAG`;
3. package sent via `cat … | ssh ha "tar xzf -"`;
4. same folder swap, plus copying `vssp_lan_probe.py` and `livebox.env` to
   the HAOS side — mandatory, since it's HA's own `command_line` sensors
   that execute it (the patchers themselves run in the runner);
5. Livebox secret sent via **stdin** (`printf … | ssh ha "cat > …"`);
6. `configuration.yaml` patched **inside the runner**: `scp` the file down,
   `vssp_apply_config.py` + `vssp_ensure_packages.py` +
   `vssp_sanitize_resources.py`, `scp` it back up. More reliable than
   installing `ruamel.yaml` on HAOS;
7. `ha core check`; on failure, roll back the folders and restore the
   pre-patch `configuration.yaml` kept on the runner;
8. `ha core restart` (or `ha core reload` if `PROD_RESTART_CORE != "true"`);
9. verify `ruamel.yaml` imports **inside the `homeassistant` Docker
   container** (`docker exec homeassistant python3 -c "import ruamel.yaml"`,
   reachable directly from this SSH session since HAOS's port 22222 lands
   on the host with Docker access), installing it there if needed and
   failing the job if it still doesn't import — this is a different
   concern from step 6's runner-side install: `vssp_assign_apply.py` and
   `vssp_rooms_apply.py` run inside HAOS at runtime, invoked by HA's own
   `shell_command`, so what the runner has never reaches them;
10. cleanup.

`rollback:production` (manual) looks up the `pre-$CI_COMMIT_TAG` backup slug
via `ha backups --raw-json` + `jq` and restores it.

---

### The second staging: Home Assistant OS in a KubeVirt VM

`deploy:staging` targets a Home Assistant **Core container** in the
`homeassistant` namespace. It has no Supervisor, no `/addons`, no `ha` CLI, so
half of this project could never be exercised before production — the add-on
copy step, `ha backups new`, the add-on store, and the Supervisor
authentication route the `vssp-mcp` add-on depends on.

`deploy:staging-haos` targets a real appliance: Home Assistant OS running as a
KubeVirt VM in the `haos` namespace (see [kubernetes/haos/](../../kubernetes/haos/)).
Same script as production — `.deploy_appliance`, reached over ssh — because it
is the same kind of machine.

| | staging (pod) | staging-haos (VM) | production |
|---|---|---|---|
| kind | Core container | HAOS appliance | HAOS appliance |
| Supervisor | no | yes | yes |
| transport | `kubectl exec` | ssh | ssh |
| trigger | master, automatic | master, **manual** | tag, **manual** |
| address | `192.168.1.11:8123` | `192.168.1.200:8123` | `homeassistant.local:8123` |

**The pod staging is not replaced, and must not be.** It is a k3s pod, so it is
the only instance where the INFRASTRUCTURE update family (host, k3s, GitLab,
runner) applies at all — an appliance reports `n/a` for it by design.

`deploy:staging-haos` is manual and its rule requires `$HAOS_SSH_KEY`, so it
does not appear until the VM has been given a key. A job that went red on every
pipeline while waiting would only teach everyone to ignore it.

**Host prerequisites**, both outside Kubernetes and needing root once: a bridge
over the spare NIC, and the dispatcher script in `kubernetes/haos/` that allows
IPv4 across it — k3s sets the FORWARD policy to `DROP`, and without that rule
the VM gets a working IPv6 and no IPv4 at all, which looks like a DHCP problem
and is not. Both are documented in `kubernetes/haos/haos-vm.yaml`.

**Appliance prerequisites**, inside the VM and done once. Installing the
Terminal & SSH add-on is not enough to make ssh reachable: it ships with
`"network": {"22/tcp": null}`, that is, no host port at all. And the `ha` CLI
has no `options` command, so both the authorized key and the port mapping go
through the Supervisor API, from the appliance itself:

```sh
ha addons install core_ssh
docker exec hassio_cli sh -c 'curl -s -X POST   -H "Authorization: Bearer $SUPERVISOR_TOKEN"   -H "Content-Type: application/json" -d @/tmp/o.json   http://supervisor/addons/core_ssh/options'
ha addons start core_ssh
```

with `/tmp/o.json` holding
`{"options":{"authorized_keys":["ssh-ed25519 ..."],"password":"","apks":[],"server":{"tcp_forwarding":false}},"network":{"22/tcp":22222}}`.
A VM that has no ssh yet is still reachable on its serial console —
`virtctl console haos -n haos` on the k3s host — which is where those two
commands were typed.

The appliance is named **`vssp-staging`** (`ha host options --hostname`). Out
of the box it was `homeassistant`, the same mDNS name as the production
appliance on the same LAN; two `homeassistant.local` on one network is the
kind of trap that only bites weeks later.

The matching private key goes into GitLab as `HAOS_SSH_KEY`, **File** type and
**protected** — `master` is a protected branch, so an unprotected variable
would never reach the job, and the rule would keep hiding it.

---

## 6. Smoke tests

`.smoke_test` loops up to 12 × 5 s on `$TARGET_URL/api/` with the matching
token, then checks that the JS engine and the CSS engine are served, and
counts `unavailable` entities.

---

# What's still missing — patches to apply

The following five points are real gaps in the current pipeline. The first
two are actively broken today.

---

## G1 — Resource URLs no longer match the files (fixed: issue 124) 🟢

Observed state in the repo:

| Declared in `config-fragment.yaml` | Actual file |
|---|---|
| `/local/vssp/css/osvision.css` | `home-assistant/www/vssp/css/**vssp.css**` |
| `/local/vssp/js/osvision.js` | `home-assistant/www/vssp/js/**osvision.js**` |

And in `.smoke_test`:

```sh
curl -sfI "$TARGET_URL/local/vssp/js/vssp.js"    # ← this file doesn't exist
curl -sfI "$TARGET_URL/local/vssp/css/vssp.css"  # ← this one does
```

The naming migration renamed the CSS file but not its URL, and renamed the
JS URL in the test but not the file. Consequences: **the CSS engine 404s on
every dashboard load**, and the smoke test fails on the JS
(`curl -sf … && echo` returns non-zero, so `test:staging` goes red).

**Fix — two renames, then a guardrail.**

1. Pick one name and stick with it. The most consistent with the rest
   (`www/vssp/`, `/local/vssp/`, `vssp_*` templates):

```sh
git mv home-assistant/www/vssp/js/osvision.js home-assistant/www/vssp/js/vssp.js
```

and in `config-fragment.yaml`:

```yaml
    - url: /local/vssp/css/vssp.css?v=__VTOKEN__
      type: css
    - url: /local/vssp/js/vssp.js?v=__VTOKEN__
      type: module
```

> `sanitize_resources` deduplicates by base URL: the old `osvision.css` /
> `osvision.js` entries already present in prod's `configuration.yaml` will
> **not** be removed automatically. Run `--prune-resources` once, or remove
> them by hand.

2. Add a check to `validate` that makes this kind of drift impossible:

```yaml
    # Every /local/vssp/... resource in the fragment must exist under www/vssp/
    - |
      python3 - <<'PY'
      import sys, os, yaml
      yaml.SafeLoader.add_multi_constructor('!', lambda l, s, n: None)
      with open('home-assistant/config-fragment.yaml', encoding='utf-8') as fh:
          frag = yaml.safe_load(fh) or {}
      res = ((frag.get('lovelace') or {}).get('resources') or [])
      err = 0
      for item in res:
          url = str((item or {}).get('url', ''))
          if not url.startswith('/local/vssp/'):
              continue
          rel = url[len('/local/vssp/'):].split('?')[0]
          path = os.path.join('home-assistant/www/vssp', rel)
          if not os.path.isfile(path):
              print(f"[ERR] resource {url}"); print(f"      -> {path} introuvable"); err = 1
      print("[OK] Toutes les resources /local/vssp/ existent" if not err
            else "[ERR] Resources Lovelace cassees")
      sys.exit(err)
      PY
```

3. And have the smoke test read the URLs instead of hard-coding them:

```yaml
    - |
      for u in $(grep -o '/local/vssp/[^ ?"'"'"']*' home-assistant/config-fragment.yaml | sort -u); do
        if curl -sfI "$TARGET_URL$u" >/dev/null; then
          echo "[OK] $u servi"
        else
          echo "[ERR] $u absent (404)"; exit 1
        fi
      done
```

---

## G2 — The ADMIN panel is never deployed (upgrade fix) 🟠

`build` only copies `vssp_apply_config.py`, `vssp_ensure_packages.py`,
`vssp_sanitize_resources.py`, `vssp_lan_probe.py` and `livebox.env`.

So the following **never** ship in the package: `vssp_discovery.py`,
`vssp_upgrade.py`, `vssp_patch_dashboard.py`, `vssp_admin_config.yaml`. The
DISCOVERY / UPGRADE / GENERATE buttons in the ADMIN panel call
`shell_command`s that point at `/config/vssp/vssp_*.py` — files absent on
both staging and production. They only work if someone dropped them in by
hand.

**Patch for `build`** — replace the individual `cp`s with a copy of the
whole folder:

```yaml
    # vssp/ scripts: patchers, LAN probe, admin tools, generator
    - mkdir -p dist/vssp
    - cp vssp/*.py   dist/vssp/
    - cp vssp/*.yaml dist/vssp/ 2>/dev/null || true
    - cp vssp/livebox.env dist/vssp/
    # The secret must never enter the package
    - rm -f dist/vssp/.livebox.env
```

**Patch for `deploy:staging`**, in the `kubectl exec`, replacing the
individual `cp`s to `/config/vssp/`:

```sh
        mkdir -p /config/vssp
        cp /config/.osv_stage/vssp/*.py   /config/vssp/
        cp /config/.osv_stage/vssp/*.yaml /config/vssp/ 2>/dev/null || true
        cp /config/.osv_stage/vssp/livebox.env /config/vssp/
        chmod +x /config/vssp/*.py
```

**Patch for `deploy:production`**, in the `ssh ha "set -e …"` block:

```sh
        mkdir -p $HA_CFG/vssp
        cp $HA_CFG/.osv_stage/vssp/*.py   $HA_CFG/vssp/
        cp $HA_CFG/.osv_stage/vssp/*.yaml $HA_CFG/vssp/ 2>/dev/null || true
        cp $HA_CFG/.osv_stage/vssp/livebox.env $HA_CFG/vssp/
        chmod +x $HA_CFG/vssp/*.py
```

**Patch for `validate`** — so the package can never ship without them again:

```yaml
    - test -f vssp/vssp_discovery.py || { echo "[ERR] vssp/vssp_discovery.py manquant"; exit 1; }
    - test -f vssp/vssp_upgrade.py   || { echo "[ERR] vssp/vssp_upgrade.py manquant"; exit 1; }
```

> See also point 5 of [Dashboard_Generator.md](../dashboards/Dashboard_Generator.md): `vssp_admin_config.yaml`
> points at `/config/home-assistant/dashboards/home.yaml`, a path that
> doesn't exist on the pod (the deployment lays dashboards out under
> `/config/dashboards/`). Backup and deletion are therefore currently no-ops.

---

## G3 — The dashboard generator isn't wired into the pipeline 🟠

`cp -r home-assistant/dashboards/.` does bring along `model/` and
`templates_j2/` if they exist — so the model and templates do reach
`/config`. But:

- `vssp/generate_dashboards.py` isn't copied (covered by G2 once the
  `cp vssp/*.py` patch is applied);
- **nothing guarantees that the checked-in `views/energy.yaml` matches the
  checked-in model.** If someone edits `model/house.yaml` without re-running
  the generator, the repo ships a stale dashboard and the pipeline says
  nothing;
- preview files (`*_preview.yaml`, `*.preview.yaml`, `preview_status.json`)
  would end up in `dist/` if accidentally committed.

**`validate` patch — anti-drift guard** (to place after the syntax check):

```yaml
    # Le dashboard genere doit correspondre au modele versionne
    - |
      if [ -f vssp/generate_dashboards.py ] && [ -f home-assistant/dashboards/model/house.yaml ]; then
        pip install jinja2 --quiet --break-system-packages 2>/dev/null || apk add --no-cache py3-jinja2 >/dev/null
        python3 vssp/generate_dashboards.py \
          --model     home-assistant/dashboards/model/house.yaml \
          --templates home-assistant/dashboards/templates_j2 \
          --out       /tmp/gen_views
        for f in /tmp/gen_views/*.yaml; do
          n=$(basename "$f")
          if ! diff -q "$f" "home-assistant/dashboards/views/$n" >/dev/null 2>&1; then
            echo "[ERR] views/$n differe de la generation depuis model/house.yaml"
            echo "      Relance : python3 vssp/generate_dashboards.py  puis commit"
            diff -u "home-assistant/dashboards/views/$n" "$f" | head -40
            exit 1
          fi
        done
        echo "[OK] Dashboards generes conformes au modele"
      else
        echo "[i] Generateur absent — controle de derive ignore"
      fi
```

**`build` patch — never package a preview:**

```yaml
    - find dist -name '*_preview.yaml' -o -name '*.preview.yaml' -o -name 'preview_status.json' | xargs -r rm -f
```

**`validate` patch — reject a checked-in preview:**

```yaml
    - |
      if git ls-files | grep -Eq '(_preview\.yaml|\.preview\.yaml|preview_status\.json)$'; then
        echo "[ERR] Des fichiers d'apercu sont versionnes. Ajoute-les au .gitignore."
        git ls-files | grep -E '(_preview\.yaml|\.preview\.yaml|preview_status\.json)$'
        exit 1
      fi
```

---

## G4 — Leftover `OSVISION` naming (upgrade fix: issue 125) 🟢

The pipeline still writes `dist/OSVISION_VERSION`, copied to
`/config/OSVISION_VERSION`. Diagnostic commands that read
`/config/VSSP_VERSION` therefore fail — it's not that the package is
missing, it's that the file is misnamed.

**`build` patch:**

```yaml
    - |
      cat > dist/VSSP_VERSION <<EOF
      version=$OSV_VERSION
      commit=$CI_COMMIT_SHA
      ref=$CI_COMMIT_REF_NAME
      pipeline=$CI_PIPELINE_ID
      built=$(date -u +%Y-%m-%dT%H:%M:%SZ)
      EOF
    - cp dist/VSSP_VERSION dist/OSVISION_VERSION   # transition, a retirer plus tard
```

Then in both deploy jobs, copy `VSSP_VERSION` alongside the existing file,
and switch the `cat /config/OSVISION_VERSION` calls in the logs and docs.
Remove the transition line once both targets have been redeployed.

---

## G5 — Deploy job robustness 🟡

Three additions that don't change nominal behavior:

```yaml
deploy:staging:
  resource_group: staging      # jamais deux deploiements concurrents sur le meme pod
  interruptible: true          # une nouvelle MR annule le run precedent

deploy:production:
  resource_group: production
  interruptible: false
```

And on `.smoke_test`, replace the `curl … && echo` calls with an explicit
form (see G1): today a 404 fails the job with no readable message.

---

## Recommended application order

1. **G1** — JS/CSS rename + `validate` check (unblocks the smoke test and
   the CSS engine).
2. **G2** — copy `vssp/*` (unblocks the ADMIN panel).
3. **G4** — `VSSP_VERSION` (makes diagnostics accurate).
4. **G3** — generator anti-drift guard, once `model/` and `templates_j2/`
   are checked in.
5. **G5** — quality of life.

Each is independent and can ship in its own MR.

---

## Resulting behavior summary (`configuration.yaml` patch)

| Situation | Result |
|---|---|
| First deployment | `visio-sapiens-*` entries added, rest of `configuration.yaml` untouched |
| Identical redeploy | `[OK] déjà conforme` — no write |
| Path/title changed in the fragment | Updated, `.bak` backup created |
| User's own custom dashboard/resource | **Always preserved** |
| `check_config` / `ha core check` failure | Folder rollback + restore from `.bak` / HAOS backup |
| Resource removed from the fragment | Kept by default; removed with `--prune-resources` |
| Renamed resource (G1) | **Old entry kept** until pruned |

---

## Design history — how we got here

Before this pipeline patched `configuration.yaml` automatically, the
`lovelace.dashboards`, `lovelace.resources`, `input_text`, `shell_command`
and `template` entries that Visio Sapiens needs had to be merged into each
target's `configuration.yaml` by hand — a manual, error-prone step on every
release. The original design added `home-assistant/config-fragment.yaml`
(the desired state, in the `vssp/` scripts' repo-root layout, not under
`home-assistant/`) and a single patcher, `vssp_apply_config.py`, invoked from
both `deploy:staging` and `deploy:production` to merge that fragment into the
live `configuration.yaml` idempotently, with a `.bak` backup on every write.

Two more scripts were added once that patcher was in production, to cover
what it deliberately leaves alone:

- **`vssp_ensure_packages.py`** — the patcher only touches `lovelace`,
  `input_text`, `shell_command` and `template`; the `homeassistant:` domain
  (and therefore `packages: !include_dir_named packages`) is out of scope by
  design, as a guardrail. This script sets that key idempotently.
- **`vssp_sanitize_resources.py`** — the patcher deduplicates `resources` by
  **full** URL. Since the `?v=` cache-busting token changes on every build,
  every deployment was adding six more duplicate entries. This script
  cleans the list up by deduplicating on the base URL instead.

This design record — including the original repo layout, the specific
`build`/`deploy:staging`/`deploy:production`/`validate` diffs, and the
rationale for patching `configuration.yaml` from the runner rather than
installing `ruamel.yaml` on HAOS itself — used to live in a standalone
document, `CI_Integration.md`. That document is now **superseded**: every
piece of it that's still current is folded into sections 2–5 above, and the
G1–G5 gaps it flagged as follow-up work are tracked here in full.
