# Visio Sapiens — AI Assistant (voice diagnostics, alerts, guided repair)

**English** · [Français](AI_Assistant.fr.md)

> **STATUS — SPECIFICATION, NOT YET IMPLEMENTED.**
> Nothing described here ships in the current release. No file listed in
> section 8 exists yet. This document is the agreed design and the
> deployment procedure to follow once the code is written; every other
> document in `docs/` describes shipped behaviour, this one does not.

## Principle

Three needs were expressed: voice diagnostics of a failing device, voice
announcement of important events (intrusion, watering failure, any
connected device down), and guided recovery. They look like one feature.
They are not.

**The split is by criticality, not by location.**

| Path | Requirement | Consequence |
|---|---|---|
| **Alert** | must *never* fail | local, deterministic, **no LLM on the critical path** |
| **Diagnosis** | may fail without harm | LLM, on demand |

An intrusion can begin by cutting the internet connection. Anything that
must be spoken that day is local and pre-written. That single sentence is
the reason this feature is split in two rather than built as one
conversational agent.

```
┌─ INFERENCE HOST (Ubuntu + Docker + GPU) ─────────────┐
│   Ollama :11434    Piper :10200    Whisper :10300    │
└───────────────▲──────────────────────▲───────────────┘
                │ LAN                  │ LAN
    ┌───────────┴───────┐   ┌──────────┴───────────────┐
    │ STAGING (k3s pod) │   │ PRODUCTION (HAOS 18.1)   │
    │ no Supervisor     │   │ hassio.* available       │
    │ output = notify   │   │ output = network speaker │
    └───────────────────┘   └──────────────────────────┘

  ALERT PATH      anomaly sensor ──► fixed phrase (locales) ──► Piper
                  no internet, no LLM, no cloud

  DIAGNOSIS PATH  voice/text ──► broker ──► Ollama ──► constrained JSON
                                    │
                                    └──► whitelist of script.vssp_fix_*
                                         (always confirmed by the user)
```

## 1. Why the alert path carries no LLM

A security announcement must be immediate, identical every time, and
independent of any service that can be unavailable. A model — local or
remote — fails all three: it adds latency, it can rephrase, and it can be
down. The alert therefore reads a **fixed string from the existing locale
files** (`home.alarm.intrusion` and its siblings already exist in
`dashboards/locales/`) and hands it to Piper.

The LLM may enrich an alert *after* it has been spoken. It is never on the
path between detection and speech.

## 2. Delivery 1 — the anomaly engine

No AI, no voice. This is the foundation: without it the assistant has
nothing to analyse and the alerts have nothing to announce.

A `sensor.vssp_anomalies` whose state is the count and whose attributes
carry the list, each entry with a `severity` of `critical` or `warning`.

| Source | Detects | Notes |
|---|---|---|
| Entities `unavailable` / `unknown` beyond N minutes | any connected device that stopped answering | the general "device down" case |
| `last_triggered` of an automation vs. its expected schedule | **the watering case** | detects *absence of action*, not failure |
| Battery level below threshold | dying sensors, before they go silent | |
| Home Assistant's own issue registry (Repairs panel) | HA's self-reported problems | free signal, no detection code to write |
| `sensor.vssp_core_health` | CPU / RAM | already exists, `packages/vssp_home_status.yaml` |
| `binary_sensor.vssp_energy_health` | production vs. consumption | already exists |
| `vssp/vssp_lan_probe.py` | unknown MAC on the LAN | the IT-intrusion half; see the limit in section 5 |

The "expected schedule vs. `last_triggered`" rule is the one worth
implementing carefully. A watering automation that never fired reports no
error anywhere: every entity is healthy, nothing is `unavailable`, and no
integration complains. It is the most commonly missed failure class in a
home automation system, and it is the one the user named.

## 3. Delivery 2 — voice and alerts

**Piper and Whisper run as plain Docker containers on the inference host,
not as HAOS add-ons.** Both are Wyoming protocol servers, and Home
Assistant reaches them through the core `wyoming` integration over TCP.
One installation, the same integration and the same configuration shape on
both environments — only the address differs. Add-ons would have been
simpler on production and impossible on staging.

### The two tiers

| Tier | Examples | Path | LLM |
|---|---|---|---|
| **Critical** | intrusion, smoke, water leak | fixed phrase → Piper → under a second, works with the WAN down | never |
| **Important** | watering silent, device down, disk full | grouped, phrased naturally | may enrich |

### Output routing

An `input_select.vssp_voice_output_mode` helper with `speaker`,
`notification`, `both`. Production announces on the network speaker;
staging writes a `persistent_notification` and a log line. Same code on
both sides, and the whole chain stays testable on staging without ever
emitting a sound — which is what you want there anyway: you are testing
the sequence, not the acoustics. See section 6 for why staging cannot
reach a Cast speaker at all.

## 4. Delivery 3 — the ADMIN "AI ASSISTANT" screen

A seventh screen in the admin console. The screen list is a single tuple
list in `dashboards/templates_j2/admin.yaml.j2`, plus two locale keys per
language.

### The broker — the model never holds a token

The model is never given a Home Assistant account. The direction is
inverted:

```
Home Assistant builds a targeted, redacted context
        ▼
Ollama — replies in a constrained JSON shape:
        { diagnostic, action_id, confidence, sources }
        ▼
Home Assistant validates action_id against a WHITELIST
        ▼
The user confirms — always, for every action
        ▼
script.vssp_fix_<action_id> runs
```

The whitelist contains **names of project scripts**
(`script.vssp_fix_reload_integration`), never raw service names. The model
returns an identifier; Home Assistant maps it. **The model never composes
a service call.** This is what makes a prompt injection survivable: its
best outcome is a wrong suggestion drawn from a known list, not an
arbitrary action.

This matters because injection vectors are already present. Calendar event
titles arrive from anyone who can send an invitation
(`packages/vssp_google.yaml`), and entity friendly names, notification
bodies and discovered device names are all text the household does not
fully control. A model holding an admin token could be instructed, by a
calendar invitation, to disarm the alarm — and an admin token can call
*any* service, including this project's own `shell_command.*` entries,
which amounts to arbitrary code execution inside the Home Assistant
container.

### The model, and why the engine enforces the schema

Ollama is the inference engine; the model it serves is a separate choice.

**The schema is enforced by the engine, not trusted to the model.** Ollama
accepts a full JSON schema in the `format` parameter of `/api/chat`, and
its OpenAI-compatible endpoint maps
`response_format: {"type": "json_schema", ...}` onto the same mechanism.
Combined with `temperature: 0`, the reply is constrained at generation
time rather than parsed hopefully afterwards. This is the single most
important implementation detail of the broker: it makes the whitelist
contract structural instead of a matter of the model behaving well.

| Model | Verdict for this job |
|---|---|
| **Qwen (8B class), instruct variant** | **Recommended.** Best instruction-following and structured output at this size, solid French, roughly 5 GB at Q4 — fits even a 6 GB card. Disable any "thinking" mode: the broker wants a compact answer, not a reasoning trace. |
| **Gemma 3 (12B)** | Good alternative **if the card really has 12 GB**. Better French prose, long context. Not Gemma **2** — it is superseded and its 8 K context is a real constraint once entity states, history and the whitelist are all in the prompt. |
| **DeepSeek (R1 distills)** | **Not for this job.** They are reasoning models that emit long thinking traces: latency inflates, and schema enforcement gags the very reasoning that makes them good. Fine models, wrong role. The full V3/R1 are far too large to run locally. |

Pick on measurement, not on benchmarks: run the same ten real anomalies
through two candidates and count how many produce a valid, whitelisted
`action_id` in correct French. A general benchmark says nothing about how
a 7B model handles *"l'arrosage ne s'est pas déclenché"* against this
project's specific action list.

Check what is current in the Ollama library at build time — this class of
model moves fast, and the table above states a shape (size, instruct
variant, no reasoning traces) more than a fixed name.

### The action ladder

| Level | Example | Who decides |
|---|---|---|
| **L0 — read** | states, history, logs, changelog | the model, freely |
| **L1 — reversible** | reload an integration, re-run an automation, restart an add-on | **the model proposes, the user confirms** |
| **L2 — disruptive** | `homeassistant.restart`, `hassio.host_reboot` | explicit confirmation |
| **L3 — destructive** | `hassio.restore_full` | on-screen confirmation, never voice alone |

L1 always asks. That is a deliberate choice: it is the only setting that
stays sound if injected text ever reaches the context.

`hassio.*` services exist on production only — see section 6.

An assistant that reboots the system it lives in cannot report the
outcome. The intent is written to a file before the reboot, read back on
startup, and the result announced then.

### Looking up fixes

Two sources, in order:

1. **Home Assistant release notes.** Compare the installed version to the
   latest and read the breaking changes across the gap. Most "it worked
   yesterday" failures are an update side effect. A structured, reliable
   source, reachable with `urllib` alone — the same stdlib-only discipline
   as `vssp_chatbot_send.py`.
2. **Open web search — later, optional.** A local model has no web access
   of its own. If needed, a self-hosted SearxNG container on the inference
   host lets the broker search and inject results, without any household
   data reaching a third party. Findings are always cited and **never
   applied automatically**.

## 5. What this feature cannot do

**If Home Assistant is dead, the assistant is dead.** The whole chain —
webhook, `shell_command`, Python, iframe — runs inside Home Assistant.

| State | Assistant |
|---|---|
| Degraded (a device down, an automation silent) | works, and is useful |
| Dead (will not start, invalid configuration) | unavailable — which is exactly when "restore the system" is wanted |

The last-resort recovery therefore lives **outside** Home Assistant, and
already exists: `rollback:production` in `.gitlab-ci.yml` runs
`ha backups restore <slug>` over SSH on port 22222, independent of whether
Home Assistant runs at all. The assistant covers *degraded* states; the CI
rollback covers *dead* ones.

**An LLM does not detect computer viruses or network intrusion.** That is
an IDS's job, not a conversational assistant's. `vssp_lan_probe.py` can
raise "an unknown MAC appeared on the LAN", and the assistant can *explain*
that alert — it cannot *produce* it. Anything beyond that needs a real IDS
and is outside this feature's scope.

## 6. Staging and production are not the same Home Assistant

Three divergences, all of which must be handled in code rather than
discovered at runtime.

| | Staging (k3s pod) | Production (HAOS 18.1) |
|---|---|---|
| Supervisor | **absent** — a containerised Home Assistant has none | present |
| `hassio.*` services | **do not exist** — no `restore_full`, no `host_reboot`, no `backup_full` | available |
| Add-ons | do not exist | available (unused here — Wyoming runs on the inference host) |
| Cast / Sonos discovery | **impossible** — mDNS multicast does not cross a CNI overlay without `hostNetwork: true` | works |
| Voice output mode | `notification` | `speaker` |

**Guard for `hassio.*`:** Home Assistant does not validate service
existence when loading a script, only when calling it — the configuration
loads on both sides, and on staging the call fails silently. A
`binary_sensor.vssp_supervisor_available` (driven by the presence of a
Supervisor-provided entity — pin the exact entity id against the live
instance) gates the L2/L3 scripts, which then announce "action unavailable
on this environment" instead of failing quietly.

## 7. Deployment procedure

### 7.1 Inference host — one time, outside the CI

The host is a plain Ubuntu Server machine with the NVIDIA drivers and
Docker. Home Assistant is **not** installed on it: HAOS carries no NVIDIA
driver and no CUDA, so putting HAOS on the GPU machine would waste the
card. Keeping them separate is what makes the GPU usable.

Three containers, reachable from the LAN:

| Service | Port | Role |
|---|---|---|
| Ollama | 11434 | **inference engine** — serves the diagnosis model (section 4) |
| Piper | 10200 | text to speech (Wyoming) |
| Whisper | 10300 | speech to text (Wyoming) |

Ollama is the runtime, not the intelligence. Which model it serves is a
separate decision, documented in section 4 — and one that can be changed
later with `ollama pull` without touching a line of this project's code.

Verify from **both** environments before going further — if these three do
not answer, nothing else in this feature can work:

```bash
ollama pull <model>                                # see section 4 for the choice
curl -s http://<inference-host>:11434/api/tags     # the model is served
nc -z <inference-host> 10200 && echo "piper ok"
nc -z <inference-host> 10300 && echo "whisper ok"
```

### 7.2 What the CI carries on its own

The `build` job works on a **blacklist** principle: `cp -r vssp/.` ships
the entire folder, so **every new Python script reaches staging and
production without touching `.gitlab-ci.yml`**. The same holds for
`home-assistant/packages/`, `home-assistant/dashboards/` and
`home-assistant/www/`, each copied wholesale.

`vssp_ensure_packages.py` guarantees
`homeassistant: packages: !include_dir_named packages` in
`configuration.yaml`, so a new package file is loaded with no CI change
either.

**The one thing that would need a CI change** is a new *top-level* folder.
`deploy:production` fails loudly on any packaged file it did not deploy:

```
[ERR] Files packaged but never deployed:
      Add their deployment to deploy:staging AND deploy:production.
```

This feature adds no top-level folder, so no CI change is expected.

### 7.3 Staging (automatic, on `master`)

Commit and push. `deploy:staging` builds, copies the archive into the pod,
swaps the folders and restarts Home Assistant. A restart is required here:
the ADMIN view gains a screen and new entities appear.

```bash
NS=<namespace>; POD=<pod>; C=homeassistant

# the new scripts arrived
kubectl -n $NS exec $POD -c $C -- ls -l /config/vssp/vssp_anomalies.py \
                                       /config/vssp/vssp_ai_broker.py
# the package is in place
kubectl -n $NS exec $POD -c $C -- ls -l /config/packages/vssp_ai.yaml
# the anomaly pass runs (writes nothing)
kubectl -n $NS exec $POD -c $C -- python3 /config/vssp/vssp_anomalies.py --dry-run
```

Remember that a pod restart recreates the container from the image and
wipes anything pip-installed into the previous one. This feature adds no
Python dependency — stdlib only, the same rule as `vssp_chatbot_send.py` —
specifically so this never becomes a concern.

### 7.4 Production (manual, on tag)

`deploy:production` is `when: manual` and tag-only. It takes a `pre-<tag>`
HAOS backup before touching anything, swaps the folders over SSH on port
22222, patches `configuration.yaml` from the runner, runs `ha core check`,
and restarts. On a failed check it rolls the folders back on its own.

```bash
# after the deploy, over the same SSH access
ssh ha "ls -l /config/vssp/vssp_anomalies.py /config/packages/vssp_ai.yaml"
ssh ha "ha core check"
```

### 7.5 Manual steps the CI cannot perform

Config-entry integrations are added through the UI and stored in
`.storage`, which is gitignored and never deployed. These are one-time per
environment, and they are the steps most likely to be forgotten:

1. **Settings > Devices & Services > Add integration > Wyoming** —
   `<inference-host>:10200` (Piper), then again for
   `<inference-host>:10300` (Whisper).
2. **The inference endpoint.** Point the existing chatbot `custom` provider
   at `http://<inference-host>:11434/v1/chat/completions`, and set the
   model name to whichever model was pulled in 7.1. That provider already
   speaks the OpenAI contract (`vssp_chatbot_send.py`), which Ollama
   serves — so no new transport code is needed. Set it from the ADMIN
   provider popup, not by editing files.
3. **Production only — the network speaker.** Confirm the Cast/Sonos
   `media_player` entity exists and note its entity id. It will not appear
   on staging; that is expected, see section 6.
4. **Both — set `vssp_voice_output_mode`**: `notification` on staging,
   `speaker` on production.

### 7.6 End-to-end verification

In this order — each step is meaningless if the previous one failed:

1. `sensor.vssp_anomalies` exists and reports a plausible count.
2. Force one anomaly (unplug a test device, wait past the threshold) and
   confirm it appears in the attributes.
3. Trigger a critical-tier announcement: spoken on production, notified on
   staging.
4. Ask the assistant a diagnosis question and confirm it replies with valid
   JSON carrying a whitelisted `action_id`.
5. Confirm an L1 action **asks before acting**, and that declining it does
   nothing.
6. Confirm an L2/L3 action is refused on staging with the "unavailable on
   this environment" message rather than failing silently.

Step 6 is the one that gets skipped and the one that will bite: it is the
only check that proves the Supervisor guard works.

### 7.7 Rollback

Production: `rollback:production`, manual, restores the `pre-<tag>` backup
taken at deploy time. Staging: redeploy the previous commit.

## 8. Files

None of these exist yet. Paths are the agreed destinations.

| File | Role |
|---|---|
| `home-assistant/packages/vssp_ai.yaml` | anomaly sensor, alert automations, whitelisted `script.vssp_fix_*`, Supervisor guard |
| `vssp/vssp_anomalies.py` | the anomaly detection pass |
| `vssp/vssp_ai_broker.py` | context building, Ollama call, JSON validation against the whitelist |
| `home-assistant/www/vssp/wizard/vssp_ai.html` | the assistant iframe |
| `home-assistant/dashboards/templates_j2/admin.yaml.j2` | one tuple added to `screens` |
| `home-assistant/dashboards/locales/{fr,en}.yaml` | menu keys, fixed alert phrases |

## See also

- [Chatbot_Integration.md](Chatbot_Integration.md) — the provider bridge this feature reuses
- [Security.md](Security.md) — secret handling conventions
- [CI_CD.md](CI_CD.md) — the two deploy jobs referenced throughout section 7
- [Troubleshooting.md](Troubleshooting.md)
