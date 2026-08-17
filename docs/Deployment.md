# Deploying the device assignment feature

**English** · [Français](DEPLOYMENT.fr.md)

This feature closes the gap between the discovery scan and the dashboard
generator. Before it, the scan wrote a report nobody consumed and the
`slots:` of `house.yaml` had to be filled in by hand.

```
DISCOVERY SCAN  ->  report.json          what exists
prepare         ->  assign_data.json     what exists + where it already sits
the form        ->  webhook              where it should go
apply           ->  house.yaml           the decision, recorded
the generator   ->  dashboards/views/    the decision, rendered
```

## 1. Files to deploy

| File | State | MD5 |
|---|---|---|
| `vssp/vssp_assign_prepare.py` | new | `ea6c388b9ddcb112cef95d763fc5b8ca` |
| `vssp/vssp_assign_apply.py` | new | `72c5d285aaf67bdd2aecb5f06a27e57d` |
| `home-assistant/www/vssp/wizard/assign.html` | new | `588a17009f7f62e0d3f5038d49d66c0a` |
| `home-assistant/packages/vssp_assign.yaml` | new | `08e35fad6b341d12360e8a6354452830` |
| `home-assistant/dashboards/templates_j2/home.yaml.j2` | modified | `7a543ef4c1f75811766aefea025b2e70` |
| `home-assistant/dashboards/locales/en.yaml` | modified | `35f552320118c6561d34bb9c2063f619` |
| `home-assistant/dashboards/locales/fr.yaml` | modified | `f49b34e48f0ede1c90780f1a734bb144` |

Check before committing:

```bash
md5sum vssp/vssp_assign_prepare.py vssp/vssp_assign_apply.py \
       home-assistant/www/vssp/wizard/assign.html \
       home-assistant/packages/vssp_assign.yaml \
       home-assistant/dashboards/templates_j2/home.yaml.j2 \
       home-assistant/dashboards/locales/en.yaml \
       home-assistant/dashboards/locales/fr.yaml
```

The two Python scripts go in `vssp/`, which the build copies wholesale —
nothing to add to the pipeline. The HTML must be under
`home-assistant/www/`, the only directory Home Assistant serves to a
browser, reachable as `/local/`.

## 2. Prerequisites already in place

| What | Why | Check |
|---|---|---|
| `packages/vssp_generation.yaml` | the language and format selectors the ADMIN view references | `ls home-assistant/packages/vssp_generation.yaml` |
| `area_id` in the room model | lets a discovered entity propose its room | `grep -c area_id vssp/generate_dashboards.py` |
| `model/house.yaml` declares rooms | there is nothing to assign devices to otherwise | `grep -c "^  - id:" home-assistant/dashboards/model/house.yaml` |

If `house.yaml` declares no room, the form says so and refuses rather than
showing an empty dropdown.

## 3. Before deploying — two checks

**Duplicate package keys.** Home Assistant refuses to start when two
packages define the same key:

```bash
grep -n "vssp_assign\|vssp_language\|vssp_format" home-assistant/packages/*.yaml
```

Each name must appear once. If `vssp_admin.yaml` already declares one,
keep a single definition.

**ruamel.yaml on the pod.** `vssp_assign_apply.py` rewrites `house.yaml`
and must not strip the comments that document it:

```bash
kubectl -n homeassistant exec <pod> -c homeassistant -- \
  python3 -c "import ruamel.yaml; print(ruamel.yaml.__version__)"
```

If it is missing:

```bash
kubectl -n homeassistant exec <pod> -c homeassistant -- \
  pip install ruamel.yaml --break-system-packages
```

Without it the script stops immediately with a clear message — it does not
fall back to a lossy writer.

## 4. Deployment

Commit and push to `master`. The pipeline validates, builds, deploys to
staging and restarts Home Assistant. A restart is required here: the ADMIN
view gains a card, and `configuration.yaml` gains the package.

## 5. Verification

```bash
# the scripts arrived
ls -l /config/vssp/vssp_assign_*.py
# the form is served
curl -sI http://<ha>:8123/local/vssp/wizard/assign.html | head -1
# the entities exist (after a restart)
# Developer tools > States: input_select.vssp_language, sensor.vssp_deployed_locale
```

Then, in the interface:

1. ADMIN console > **DISCOVERY SCAN**. It now chains the scan and the form
   preparation — a scan whose result the form cannot read looks like a scan
   that did nothing.
2. The **DEVICE ASSIGNMENT** panel lists the discovered entities. Each one
   arrives with a room proposed from its Home Assistant area, and a slot
   proposed from its `device_class`.
3. Adjust, then **Save and regenerate**.

Expect a long list: the discovery reports *every* entity of every area,
sensors included. The filter field and the bulk assignment — which applies
to the visible rows only — exist for that.

## 6. What each guard refuses

| Situation | Behaviour |
|---|---|
| A slot the room does not have (a shutter in the garden) | the form does not offer it; the applier refuses the payload and writes nothing |
| An audio device without a `source` / `output` role | refused, nothing written |
| An empty room or slot | the entity is unassigned — that is how you remove one |
| A malformed payload | refused, a notification says so |

Nothing is ever half-written: the applier validates the whole payload
before touching `house.yaml`, and backs it up to `model/backups/` first.

## 7. Re-running a scan

A second scan does **not** reset the previous work. Already assigned
entities come back with their room and slot preselected, marked with a
green edge. That was the main risk of this design and it is tested.

## 8. Rollback

```bash
# the model
ls -t /config/dashboards/model/backups/ | head -3
cp /config/dashboards/model/backups/house_<stamp>.yaml \
   /config/dashboards/model/house.yaml
# then regenerate from the ADMIN console
```

The dashboards themselves need no rollback: they are generated, so
restoring the model and regenerating is enough.
