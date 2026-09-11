# Visio Sapiens — Updates (ADMIN, UPDATES screen)

**English** · [Français](Updates.fr.md)

## Principle

Home Assistant already knows about every pending update. Each one is an
`update.*` entity carrying `installed_version`, `latest_version`, its
release notes, and an install service. Settings → Updates lists them —
but only there, and mixed in with everything else that screen does.

For its first three families the UPDATES screen adds **no data source at
all**: it reads the entities that already exist and adds the one thing a
dashboard cannot work out on its own, the **split by family**. The fourth
is different — the infrastructure has no entities, so it has a probe of
its own. That half is described in [The fourth family](#the-fourth-family--infrastructure).

| Family | What it is | How it is installed |
|---|---|---|
| **System** | Home Assistant itself, the Supervisor, the OS, add-ons | one row at a time |
| **Integrations & cards** | everything installed through HACS | one row at a time, **or all at once** |
| **Device firmware** | `device_class: firmware` — a physical device | one row at a time, never in bulk |
| **Infrastructure** | the host, k3s, GitLab, the runner, Vault | by tier — see [the fourth family](#the-fourth-family--infrastructure) |

That split is the whole point of the screen. Settings → Updates shows a
Lovelace card download and the flash of a wall plug as the same kind of
line; they are not the same kind of risk, and that is the one distinction
that decides whether you click without thinking or read the release notes
first.

## Where each piece lives

```
update.* entities (Home Assistant, already there)
        │
        ▼
packages/vssp_updates.yaml       5 sensors — a count and an entity list
        │                        per family, one grand total, and one
        │                        for what may install unattended
        ▼
templates_j2/admin.yaml.j2       the UPDATES screen renders those lists
```

The classification happens **in the package, not in the dashboard**.
Working out that `update.browser_mod_update` belongs to HACS requires
`integration_entities()`, a template function that exists on the Python
side only — a Lovelace card has no equivalent. So the sensors publish
each family as an `entity_ids` attribute, and the cards render the list
they are handed.

The system family is defined by **subtraction**: anything that is neither
HACS nor firmware. That is why the same file is right on this k3s
instance (where it catches the NAS) and on a HAOS production instance
(where it catches Core and the add-ons), with no edit.

### Entities created

| Entity | State | Attribute |
|---|---|---|
| `sensor.vssp_updates_pending` | total pending | `entity_ids` |
| `sensor.vssp_updates_system` | pending, system | `entity_ids` |
| `sensor.vssp_updates_hacs` | pending, HACS | `entity_ids` |
| `sensor.vssp_updates_firmware` | pending, firmware | `entity_ids` |
| `sensor.vssp_updates_auto` | pending, auto-installable | `entity_ids`, `protected` |
| `script.vssp_updates_check` | — | re-poll every update entity |
| `script.vssp_updates_install_hacs` | — | install every pending HACS update |
| `script.vssp_updates_install_auto` | — | the automatic pass, on demand |
| `input_boolean.vssp_updates_auto` | the option | off until you turn it on |
| `input_datetime.vssp_updates_auto_time` | the hour it runs | |
| `automation.vssp_updates_auto_nightly` | the nightly trigger | |

An update that has been **skipped** does not count, and that needs no
filter: Home Assistant reports such an entity as `off` for as long as the
skipped version is the latest one. Skipping from a row therefore empties
this screen exactly the way installing does.

## The screen

**UPDATE STATE** — the counts, at a glance, one row per family.

**TO INSTALL** — the inventory: every pending update, grouped by family,
with the two versions it sits between (`v3.2.2 → v3.2.3`). This is what
you read before deciding. A family with nothing pending shows an em dash.

**One card per family** — the actionable rows, and each card is absent
when its family is empty, so a fully up-to-date instance shows a screen
with nothing on it but the state and the maintenance controls.

Tapping a row opens **Home Assistant's own update dialog**: release
notes, the backup checkbox where the entity supports one, Install, and
Skip. That dialog is better than anything this console could rebuild, so
the console does not rebuild it.

**MAINTENANCE** — two buttons:

- **CHECK NOW** — integrations poll on their own schedule (HACS roughly
  hourly), so an empty screen means *nothing found last time we asked*.
  This button turns that into *nothing found just now*.
- **INSTALL EVERY INTEGRATION & CARD** — the one bulk install offered.

### Why the bulk install stops at HACS

Not a limitation — a decision.

A HACS update downloads files and is undone by reinstalling the previous
version from HACS. A Core or add-on update is not, and wants the backup
checkbox its own dialog offers — which a bulk call cannot tick, since
`update.install` refuses `backup: true` on any entity that does not
advertise BACKUP support, and would fail the whole call for a mixed list.
A firmware flash is undone by nothing at all.

So: HACS in bulk, everything else from its own row.

After a bulk HACS install a notification asks for a hard refresh
(Ctrl+Shift+R). A Lovelace card replaced on disk is still the old file in
this browser's cache, Home Assistant does not say so, and the symptom — a
card that keeps behaving like the version you just replaced — reads as a
failed update rather than a stale tab.

## Automatic updates — an option, and it is off

Nothing installs itself until `input_boolean.vssp_updates_auto` is turned
on from the AUTOMATIC UPDATES card. With the switch closed the automation
stays loaded and does nothing: the switch is a **condition**, not a
second trigger, so turning it back on later does not replay the nights it
sat out.

When it is on, once a night at the hour set beside it, the pass:

1. asks every update entity to re-poll, and waits for the answers;
2. reads `sensor.vssp_updates_auto` — the list of what may be installed
   unattended;
3. installs them **one at a time**, `continue_on_error`, twenty seconds
   apart;
4. posts a notification naming what was installed **and what was held
   back**.

The count on the card is read from that same sensor, so the number on the
row is the number of things that will be installed tonight — not a second
calculation that agrees with the first until one of them is edited.

**RUN THE PASS NOW** calls the same script the automation calls. Testing
the button tests the real nightly pass rather than a second copy of it
that will drift.

### Home Assistant Core is never installed automatically

It is the one update that can leave the house without a dashboard: a
broken Core takes down the interface you would use to notice, the console
you would use to roll back, and every automation in the file. It wants
the backup checkbox its own dialog offers, and a person watching.

The exclusion lives in **the sensor that feeds the automation**, not in
the automation — so the screen states it as a fact it reads back rather
than as a promise made in a comment, and the held-back entity is named in
the notification instead of silently missing.

Core is recognised two ways, because the two do not always coincide: by
`entity_id` (`update.home_assistant_core_update`, the identifier the
Supervisor gives it) and by the `title` attribute (`Home Assistant
Core`), which survives an entity someone renamed.

Neither exists on the k3s instance — Home Assistant runs there as a
container with no Supervisor to update it — so `protected` is empty and
the guard is dormant until the model moves to HAOS, which is exactly when
it has to already be there.

**What is not protected:** the Supervisor, the OS and the add-ons go with
everything else, as asked. Leaving the switch off is what holds those
back.

### Why one at a time

A single `update.install` over the whole list is one service call. The
first entity that refuses — a device that went offline between the
refresh and the install — raises, and everything queued behind it is
silently never attempted. Looping with `continue_on_error` costs a few
minutes at four in the morning and buys a pass that finishes what it can.

The delay between them also keeps two firmware flashes from overlapping,
which on mains-powered devices means two plugs rebooting at once.

## Implementation notes

**No iframe, no token.** Unlike ROOMS & FLOORS, DETECTED DEVICES or the
SAFE, this screen is entirely native cards. An update is an `update.*`
entity, so native cards reach all of it, and the native more-info dialog
does the acting.

**`custom:config-template-card` builds the rows.** An `entities` card
cannot filter: its list is fixed in YAML written months before the update
existed. config-template-card evaluates a value that starts with `${` and
assigns whatever comes back — an array included — so the list is read
from the sensor at render time. It re-renders when an entity in its own
`entities:` changes, hence the family sensor listed there, whose count
moves the moment an install finishes.

Inside that expression the state map is called **`states`**; there is no
`hass`. The `&& … || []` guard is not superstition: the sensor does not
exist for the few seconds between a restart and the first template pass,
and an entities card handed `undefined` throws rather than rendering
empty.

**The conditions spell out `unavailable` and `unknown` one by one.**
`state_not: "0"` alone is true for both, so on a half-started instance
the card would appear, ask the sensor for a list, and get nothing.

**The time field needs one CSS token, on the card.** The picker is a Web
Awesome control four shadow roots down (`ha-time-input` >
`ha-base-time-input` > `ha-input` > `wa-input`), and what paints it is
`.text-field` inside `wa-input`'s own shadow root — unreachable by any
selector written in the template. Left alone it renders `#f3f3f3`, a
white slab on a dark console. `--ha-color-form-background` set on the
`ha-card` is the one thing that changes it.

It has to go on the **card**, not on the downstream
`--wa-form-control-background-color`: a custom property is substituted
where it is *declared*, and Home Assistant declares that chain from this
token somewhere above the card, so by the time it reaches the field the
downstream name is already a resolved literal.

And when checking it in a browser, the field carries a background
transition — reading the computed style immediately after setting the
property returns the **old** colour, and a working fix looks like a
failed one.

**Two template engines on the markdown card.** The three family labels
are translated by the *generator*; the loop under them is executed by
*Home Assistant*. The boundary falls between them, so the set-tag is
emitted as text — `{{ '{%' }}` is an expression the generator evaluates
into two characters Home Assistant later reads as the start of a tag. An
expression is also immune to `lstrip_blocks`, which strips the
indentation in front of a *block* tag — the trap a raw block on that line
would have walked straight into, landing the template at column zero and
breaking the YAML. See [Troubleshooting.md](../ci-cd/Troubleshooting.md)
for the version of that mistake that shipped once already.

## The fourth family — INFRASTRUCTURE

Everything above this section reads entities Home Assistant already
holds. This one cannot, and that is the whole reason it exists.

Home Assistant knows a Core update is pending. It does not know the
Ubuntu host it runs on has five packages waiting and is asking for a
reboot, that k3s is two patch releases behind, or that the GitLab which
deploys it has shipped a fix. Those facts live on the other side of the
container boundary and no `update.*` entity carries them — so the screen
that claimed to hold *every* pending update was, until now, blind to the
machine underneath it.

### Three layers, not one flat list

The first question anyone asks of an infrastructure update is not "which
version" but **"what does restarting this take down with it"**. Recreating
the safe costs a reseal; restarting k3s takes Home Assistant with it, and
therefore the screen the button was pressed on. Those are two different
blast radiuses and they sat in the same list of seven rows, which never
named the difference.

So every component declares its **layer**, and the screen groups on it:

| Layer | What it is | What a restart takes with it |
|---|---|---|
| `host` | the Ubuntu install itself — apt packages, systemd units | everything, for the host reboot; nothing, for a package |
| `docker` | a container of the host's own Docker daemon, **beside** the cluster | that container alone |
| `k3s` | what runs **inside** the cluster | the pod, and Home Assistant if it is one of them |

| Component | Layer | Tier | Where the version comes from |
|---|---|---|---|
| Host packages | `host` | `auto` | `apt list --upgradable` on the host |
| Host restart | `host` | `manual` | `/var/run/reboot-required` |
| GitLab | `host` | `manual` | `apt-cache madison gitlab-ce`, or the instance's own API |
| GitLab runner | `host` | `auto` | `apt-cache madison gitlab-runner` |
| k3s cluster | `host` | `manual` | `k3s --version` against the k3s-io/k3s releases |
| Vault safe | `docker` | `manual` | `vault version` **inside** the container, against Docker Hub |
| Other Docker containers | `docker` | `locked` | `docker ps`, reported and not compared |
| Cluster workloads | `k3s` | `locked` | `k3s kubectl get deploy,sts,ds -A`, reported and not compared |

Two rows are new or moved, for precise reasons:

- **Cluster workloads.** The cluster appeared only as a version number and
  nothing of its contents appeared at all — Home Assistant, which serves
  this screen, was not on the screen. This row lists every deployment,
  statefulset and daemonset with the image it pulls, at the level where
  that image is declared: pods come and go, their controllers are what an
  upgrade edits.
- **The safe reads `vault version`, not its image tag.** The deployment
  pins `hashicorp/vault:1.20`, a floating alias for the newest patch in the
  series: the tag says `1.20` while the binary is `1.20.4`. A plan built on
  the tag therefore offered `1.20.4` as its first step — an upgrade to the
  version already running.

### One step per press — the path, not the horizon

**The problem.** A row published one pair: installed, and the highest
version upstream. On an apt package that pair is also the instruction —
apt goes from one to the other in a single step. On the safe it was a lie.
HashiCorp supports one minor series at a time, so a host on `1.20.4`
reaches `2.1.0` like this:

```
1.20.4  ──▶  1.21.4  ──▶  2.0.4  ──▶  2.1.0
```

Three upgrades, each with its own storage and seal migration. The row
printed `1.20.4 → 2.1.0` beside an INSTALL button: it was offering to skip
two of them. Kubernetes forbids skipping a minor in the same way, and
GitLab's database migrations run per minor.

**The fix.** The constraint belongs to each component, so it is declared
beside its tier, in `vssp_infra_updates.py`:

| Policy | What it allows | Who carries it |
|---|---|---|
| `POLICY_DIRECT` | any version to any version, in one move | host packages, GitLab runner |
| `POLICY_SERIES` | one `major.minor` series at a time, landing on its highest patch | Vault, k3s, GitLab |

The probe then publishes the whole path instead of its endpoint:

| Field | What it is |
|---|---|
| `next` | the **one** version a press installs |
| `path` | every stop, from `next` to the top |
| `steps` | how many upgrades that is |
| `latest` | the top. It stays on the row — how far behind you are is worth knowing — but is **no longer a target** |

What the screen now shows on the safe's row:

```
Vault safe             1.20.4 → 1.21.4          [INSTALL]
                       then 2.0.4 → 2.1.0 · 3 steps
```

The light on HOME still goes red on `latest`: being three series behind is
a major-version fact whatever the first step happens to be, and the light
is about how far behind the house is. But its list shows `next` beside the
arrow, because that is the version a press installs. The two used to be
one field, which is why the light and the button could describe different
upgrades.

**Nothing can skip a step, not even by accident.** `install_one` probes the
component *before* installing and hands the fresh row to the installer,
which installs the version that row names. Neither a stale sensor, nor a
card rendered before the last probe, nor a second operator can turn a press
on `1.21.4` into a jump to `2.1.0`. On the apt side that means
`apt-get install gitlab-ce=18.3.2-ce.0` and not `--only-upgrade`, which
would aim at the candidate, i.e. the top.

### A sealed safe does not empty the screen

Vault reseals on **every restart**, by design: no auto-unseal is configured,
and that is a choice rather than an oversight. The host's SSH access lives in
that safe. A sealed safe therefore makes seven of the eight rows
unmeasurable — everything on the server, plus what runs under Docker and
inside k3s.

For a long time the report written in that state said, for every one of those
rows, `installed: ""`, `pending: false`, `count: 0`. The screen rendered it
faithfully: **the host, GitLab and k3s updates listed an hour earlier simply
vanished**, and the counts went to zero. This was not a corner case — it was
every reboot.

"I could not measure this" and "there is nothing here" are different facts,
and the report was publishing the second one for the first.

`carry_forward()` now inherits, for every unmeasured row, the last real
measurement. Three separate fields carry the distinction:

| Field | The question it answers |
|---|---|
| `probed` | did **this** run measure the row? |
| `stale` | do the values come from an **earlier** run that did? |
| `measured` | **when** was that measurement taken? |

Only the **measurement** fields travel (`CARRIED` in
`vssp_infra_updates.py`): the name, the tier, the icon, the layer, the policy
and the warning keep coming from `COMPONENTS`, so that editing the table
still changes every row on the next run.

On screen, a remembered row keeps its numbers, loses its colour, and carries
its date on the second line: *"last measured 2026-09-11 14:00"*. It has no
INSTALL button — an install needs the same host access the probe lacked. The
amber banner at the foot of the card says why, and prints the command that
ends it.

**`measured` does not creep.** A row already carried keeps the timestamp of
the run that actually saw the machine, so a week of sealed reboots keeps
pointing at it instead of walking the date forward one probe at a time until
it looks fresh.

**The alternative was worse.** Writing nothing at all — what this file used to
do — leaves the previous report untouched on disk, and the screen renders
what is on disk: old versions shown as current, with nothing anywhere saying
they are old. The difference between the two is not the data, it is the label
on it.

**And to stop resealing?** There is no free path, and that is the point of a
seal: every automation amounts to handing the key to something else.
`seal "transit"` hands it to a second Vault, which only helps if that Vault
runs on a machine that does not reboot with this one. `seal "awskms"` /
`gcpckms` / `azurekeyvault` hand it to a remote KMS — the only option that
truly unseals by itself without a second server, at the price of a boot-time
dependency on the internet and an IAM credential sitting on the host. Putting
the keys in a file cancels the safe. PKCS#11/HSM is Vault Enterprise only.
Until one of those is chosen, what this section describes is the answer: a
seal costs three key entries, not a blank screen.

### Current is not running

The first real k3s upgrade installed the right binary and left the cluster
down for a quarter of an hour with nothing saying so.

What happened, because it will happen elsewhere:

1. `get.k3s.io` installs `v1.36.4+k3s1` and restarts the unit. Clean log.
2. A **`k3s agent` process from the previous version survives the stop** —
   systemd says so, "Found left-over process in control group while starting
   unit" — and keeps `127.0.0.1:6444`, the supervisor's port.
3. The new server starts, cannot bind, exits.
   `Failed with result 'protocol'`. systemd restarts it. **55 times.**
4. The workloads keep running under an orphaned `containerd`: Home Assistant
   answers 200 and a browser shows nothing wrong.
5. And the k3s row reads **"1.36.4 · up to date"**, because the probe read
   `k3s --version` — that is, **the binary on disk**.

Three faults, three fixes:

| Fault | Fix |
|---|---|
| The installer created the condition | it **stops** the unit, **waits** for 6444 to be released, and kills whatever still holds it after 5 s |
| It did not verify | it waits for `active`; failing that it frees the port and restarts **once**, then writes its verdict to `.state` |
| The probe read the version, not the state | it also asks `systemctl is-active k3s`; anything but `active` fills `health` |

The `health` field outranks everything else on screen: the row turns red and
names the systemd state, because `activating` and `failed` send you to
different places. `activating` counts as bad **on purpose** — it is the state
of a `Type=notify` unit that starts and never signals ready, which is exactly
what a crash loop looks like from outside.

**The lesson is not about k3s.** A version answers "is this current", never
"is this working", and this screen was built to show the first. Any component
whose service can die while keeping the right number deserves its `health`.

Manual recovery, should the automatic restart ever not be enough:

```bash
sudo /usr/local/bin/k3s-killall.sh   # stops leftovers, uninstalls nothing
sudo systemctl restart k3s
```

**And the second time was worse.** The same error came back at the next OS
reboot for a different reason — and this one would never have cleared itself:

```
/etc/systemd/system/k3s-agent.service       2026-07-01   <- enabled since July
multi-user.target.wants/k3s.service         2026-09-11   <- enabled by this upgrade
```

Two k3s units on one host. `k3s server` binds `127.0.0.1:6444` as its
supervisor port, `k3s agent` binds it as the client-side load balancer to an
apiserver: **one host cannot run both.** The agent unit had been dormant for
months because the server unit was not enabled at boot — installing k3s from
this screen enabled it. The next reboot started the two together, the agent
won the race, and the pods never came back: no Home Assistant.

So the installer stops the rival unit, and **disables** it. Killing the
process would not do: a `pkill` against a process systemd owns simply gets it
restarted, which turns one race into an endless one. As for disabling, it
changes what the host does at boot and that is more than an upgrade is asked
to do — the justification is that the two units are **mutually exclusive**: if
this screen is upgrading the server on this host, an agent unit beside it is
not a preference to respect, it is a configuration that cannot work. Left
enabled it breaks the cluster at every boot, silently, with the workloads
simply absent. So it is disabled and said plainly in the log, rather than left
as a trap.

The existence test is `systemctl cat`, not `list-unit-files`: the latter can
succeed with an empty result, and `is-active` can answer `unknown` instead of
`inactive` — enough to warn about a conflict nobody has.

### The three tiers

The other families already split by risk — HACS in bulk, firmware never.
This one applies the same idea to things that can take the house offline:

- **`auto`** — the nightly pass may install it unattended. Reversible, or
  cheap enough that a bad one is a nuisance rather than an outage.
- **`manual`** — one row, one button, never the pass, whatever the switch
  says. GitLab restarts every one of its services and wants a backup
  first; a host reboot is a host reboot.
- **`locked`** — reported and never installed from the console at all,
  **and each locked row says why in its own words**. One sentence used to
  cover all of them, so the LOCKED chip explained nothing about the row it
  sat on.

**k3s and Vault were `locked` and both were wrongly so**, for different
reasons.

- The safe is a plain Docker container **beside** the cluster, not in it
  (see [Vault.md](../platform/Vault.md) for why): recreating it touches
  neither Home Assistant nor k3s. It costs a reseal — three of the five
  keys to enter again — and that is exactly what its confirmation warns
  about before the press.
- k3s really does take Home Assistant with it. But so does the host
  reboot, which has been a button all along: the answer to "this kills the
  session that pressed it" is to **detach** the command, not to refuse the
  operation. `install_k3s` writes a script to the host and starts it under
  `setsid`, the way `install_os_reboot` leans on `shutdown -r +1`; the
  upgrade finishes on its own and the next probe reports the result.

What was actually dangerous about both was aiming them at the newest
release — and that is what the previous section fixes.

**Every heavy button now carries its own warning**, declared beside its
tier. A single sentence had the safe and the host reboot asking the same
question about two entirely different consequences: one reseals a
container, the other takes the house offline.

**The tier is declared in `vssp_infra_updates.py`, not in the dashboard.**
A card cannot promote a component by rendering it differently, and the
nightly pass filters on that field rather than on anything the interface
sent it.

### Where the privileges come from

Reading `apt list` needs an account on the host. Installing needs sudo.
Home Assistant must hold neither: everything it reads becomes an entity
state, written in clear text to `home-assistant_v2.db` by the recorder
and visible in Developer Tools to any administrator. That is the same
reasoning that shaped the safe (see [Vault.md](../platform/Vault.md)),
now applied to maintenance.

So the credentials live in the safe, under `vssp/infra/`, and **the
Python process reads them — not Home Assistant**:

```
ADMIN screen  ──▶ shell_command ──▶ vssp_infra_updates.py
                                        │
                                        ├── reads secret/data/vssp/infra/*
                                        │   with the vssp-maint token
                                        │   (/config/vssp/.vault_maint_token)
                                        ├── ssh to the host, apt / k3s / docker
                                        └── writes www/vssp/infra_updates.json
                                                │
                     sensor.vssp_updates_infra ◀┘   (command_line, cat)
```

The values exist in the memory of one short run, travel to `ssh` or to an
HTTPS call, and are never returned to the caller. The `shell_command`
that started the run gets back a count and a status message. Nothing
reaches an entity, so nothing reaches the database — the separation
survives, and it survives the way the rest of the safe enforces it: by
what Vault refuses, not by what a script promises.

`vssp-maint` grants `read` on `secret/data/vssp/infra/*` and nothing
else. It cannot list the safe, cannot see `accounts/` or `apps/`, and
cannot write.

### What to put in the safe

From the SAFE screen, category `infra`:

| Entry | Fields |
|---|---|
| `vssp/infra/host_ssh` | `host`, `user`, `port`, `private_key` |
| `vssp/infra/host_sudo` | `password` |
| `vssp/infra/gitlab` | `url`, `token` — only for a GitLab that is not an apt package |

Give it **its own SSH key**, created for this and nothing else, so
revoking maintenance access is deleting one line from the host's
`authorized_keys` rather than rotating a key someone also logs in with.

Then create the token and put it in the CI variable:

```bash
vault policy write vssp-maint vault/policies/vssp-maint.hcl
vault token create -policy=vssp-maint -period=768h -field=token
# → Settings > CI/CD > Variables, masked + protected, VAULT_MAINT_TOKEN
```

Without that variable nothing breaks: the deploy warns, and the family
reports itself as never probed.

### auto, manual, planned

The three ways this family moves, and they are the same three the rest of
the screen already offered:

| | What runs | Controlled by |
|---|---|---|
| **planned** | the probe, every 6 hours and 2 minutes after every restart | nothing — it only reads |
| **auto** | the `auto` tier, at the hour beside the switch | `input_boolean.vssp_updates_infra_auto` |
| **manual** | one component, from its own button | you |

**The infrastructure switch is a second switch, deliberately.** The one
above it installs Lovelace cards: a bad night costs a Ctrl+Shift+R. This
one runs `apt-get` on the server carrying the cluster Home Assistant
lives in. Folding them into one control would mean someone who enabled
automatic HACS updates months ago quietly starts upgrading their server
tonight, having agreed to no such thing.

### Two details that are easy to get wrong

**The host-packages row excludes GitLab and the runner.** Both are apt
packages with a row of their own; left in the count they would appear
twice, and the family total would overstate the work waiting. They are
removed from the row *and* from the upgrade command — `install
--only-upgrade <named packages>` rather than a bare `apt-get upgrade`,
which would otherwise install `gitlab-ce`, a manual-tier component, in
the middle of an unattended pass. The tier would have been enforced
everywhere except in the one command that installs.

**The upstream version is the apt candidate, not a release feed.** The
host is already subscribed to the vendor's repository, so the candidate
is by definition the version this machine would actually get — and it
stays right on a pinned or held package, which an upstream API cannot
know about. `apt-cache policy` is also **localised**: it prints
`Installed:` on an English host and `Installé :` on a French one, so the
probe pins `LC_ALL=C` before parsing. Without that it works on the
machine it was written on and reports every package as unknown everywhere
else.

### Entities added

| Entity | State |
|---|---|
| `sensor.vssp_updates_infra` | pending on the infrastructure; attributes `components`, `counts`, `generated` |
| `sensor.vssp_updates_all` | every pending update, both worlds together |
| `sensor.vssp_infra_auto` / `_manual` / `_locked` | the count per tier |
| `script.vssp_infra_check` | probe now |
| `script.vssp_infra_install_one` | install one component, by key |
| `script.vssp_infra_install_auto` | the `auto` tier pass |
| `input_boolean.vssp_updates_infra_auto` | the option, off until you turn it on |
| `automation.vssp_infra_probe_scheduled` | every 6 hours |
| `automation.vssp_infra_auto_nightly` | the pass, 10 minutes after the Home Assistant one |

`sensor.vssp_updates_infra` is a `command_line` sensor that **reads a
file** — it does not run the probe. The probe opens an SSH session and
calls three upstream APIs; running that on a sensor scan interval would
mean a connection to the host every minute for a number that changes
twice a day. A `cat` of a missing file exits non-zero and the sensor goes
unavailable, which is correct and visibly different from "nothing is
pending".

## The light on HOME

The fifth KPI panel of the HOME dashboard — desktop and mobile alike — is
a single traffic light labelled **UPGRADE**, and tapping it opens this
screen. It replaced the security/alarm panel, which moved into the third
slot where ROOMS & DEVICES used to sit.

| | Means | Shown when |
|---|---|---|
| 🟢 **PATCHED** | nothing is exposed to a known vulnerability | no security patch pending, no major version available |
| 🟠 **PATCHES DUE** | security patches are waiting | the host has packages from a `-security` pocket |
| 🔴 **MAJOR VERSION** | something needs a real migration | any component's *first* version number has moved |

**Three colours, never a fourth.** An estate that could not be inspected —
`sensor.vssp_updates_infra` unavailable because the probe has never run —
also wears the **orange**, with its own icon and the label NOT PROBED. It
is not green: green is a claim, *nothing here is exposed*, and making that
claim without having looked is the one failure mode a security light
cannot afford, because it is indistinguishable from the real thing exactly
when it matters. Orange says what is true — attention needed — and the
label says why.

**It is not a count of pending updates.** The screen already lists those.
A light that turns orange because a Lovelace card has a new version
teaches you to ignore it by the end of the week, so the question it
answers is deliberately narrow: *is anything unpatched, and is anything
about to need a migration?* An ordinary minor update leaves it green.

**Green is never shown over missing data.** A security light that reads
"all clear" when it has not looked is worse than no light at all, which
is why the fourth state exists. Home Assistant's own updates are always
known, so an unprobed host is the only thing that can grey it out.

**Major means the first number moved** — `1.20 → 2.1.0` is major,
`1.36.2 → 1.36.4` is not. Both worlds are read: the infrastructure
components from the probe's attribute, and the `update.*` entities Home
Assistant holds, whose `installed_version` and `latest_version` get the
same comparison. Anything with an unknown upstream is skipped rather than
guessed — an empty version is not evidence of being behind.

The verdict is computed once, in `variables`, which button-card evaluates
before the fields that read them; icon, colour, state and label therefore
all agree instead of each recomputing it and diverging on a slow frame.

## Related

- [Dashboard_Generator.md](Dashboard_Generator.md) — the generator, slots
  and locales
- [Backup_Retention.md](../platform/Backup_Retention.md) — what a backup
  before a Core update actually retains
