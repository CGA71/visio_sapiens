# Prerequisites — what an instance needs before a version lands on it

**English** · [Français](Prerequisites.fr.md)

The same release produced a working instance on the development pod and a
blank screen on a freshly deployed Home Assistant OS. The code was identical —
the generator and the templates matched byte for byte. What differed was
everything the deployment had never owned.

This page is the contract: what an instance must have for the **control
centre** to be drawn, how the pipeline enforces it, and how to do the same by
hand on an instance that has no pipeline at all.

---

## 1. The line: control centre, not house

A prerequisite is what the **control centre** needs in order to exist. It is
never a connected device.

A house with no camera, no smart plug and no room declared must still receive a
working Visio Sapiens — navigation rail, header, ADMIN console, all of it. The
cameras and thermostats come afterwards, from the ADMIN console, and their
absence is reported without failing anything.

That line runs through every tool below: `vssp_verify.py` fails on a missing
`sensor.vssp_*` and forgives a missing `camera.*`, and the manifest lists no
device at all.

The same line separates **structure** from **content** after a deployment:

| Structure — a defect, the pipeline fails | Content — reported, never fails |
|---|---|
| HOME, CORE, ENERGY, ADMIN and their mobile variants serve a configuration | a room dashboard whose house model no longer declares it |
| every `sensor.vssp_*` the screens name exists | a camera, a vacuum, a plug this house does not own |
| every registered resource answers | the photovoltaic placeholders, listed as tolerated |
| the theme is selected, the blocking cards installed | an optional card feeding one tile |

Which dashboards are structural is not guessed: `vssp_verify.py` reads
`config-fragment.yaml`, the fragment this project writes. What the house's own
model declares is content by construction.

---

## 2. The manifest

[`vssp/requirements.yaml`](../../vssp/requirements.yaml) is the single source of
truth. Three programs read it, so they cannot drift apart:

| Program | When | What it does |
|---|---|---|
| `vssp_preflight.py` | before a deploy | refuses an instance that cannot host the release |
| `vssp_prepare.py` | when the preflight refuses | installs what can be installed, names the rest |
| `vssp_dependencies.py` | from the ADMIN console | reports and installs, CHECK / INSTALL DEPENDENCIES |

It holds four sections: the **minimum Home Assistant version**, **HACS**, the
**cards** (pinned to `owner/name`, each marked blocking or not), the HACS
**integrations**, and the **core integrations** Home Assistant ships itself.

**Blocking** means the interface cannot be drawn at all: `button-card` carries
every tile, `card-mod` every style, `layout-card` every view layout,
`browser_mod` the ADMIN pop-ups. Everything else feeds one card, and its
absence costs that card, not the screen.

Cards are pinned to `owner/name` because two repositories can share a folder
name: `kalkih/simple-weather-card` and `I-Simen-I/simple-weather-card` both end
in `simple-weather-card`, the interface is written with the options of the
fork, and an instance that received the other one drew nothing where the
weather tile should be.

---

## 3. In the pipeline

```
validate → build → preflight → deploy → test
                       │                  └── verify:*   (after)
                       └── prepare:*      (manual, when preflight refuses)
```

`preflight:staging`, `preflight:staging-haos` and `preflight:production` query
the **target**, not the code. Each deploy waits for its own: a release never
lands on an instance that cannot host it. `prepare:*` sits in the same stage,
manual, because installing a dozen third-party repositories into someone's
instance is a decision, not a side effect of pushing code.

After the deploy, `verify:*` checks what a person would look at — every
dashboard serves a configuration, every Visio Sapiens entity exists, every
resource answers, the theme is selected. See
[CI_CD.md](../ci-cd/CI_CD.md).

---

## 4. Without a pipeline, by hand

An instance installed from HACS, or any house that has no runner, does the
same thing with the same scripts. They talk over the network only, and the
token is read from the environment or a file — never from an argument, which
would be visible in the machine's process list.

**On the instance** (Terminal add-on, or the Home Assistant container):

```sh
export HA_TOKEN="<a long-lived token>"        # Profile > Security
python3 /config/vssp/vssp_preflight.py --url http://localhost:8123
```

It answers one of two ways. Either `[OK] the instance can host the control
centre`, and you deploy. Or `[STOP]`, followed by the exact list of what is
missing and why each is needed.

Then:

```sh
python3 /config/vssp/vssp_prepare.py --url http://localhost:8123
```

It installs the cards and the Visio Sapiens resources, creates the core
integrations whose setup needs no answer of yours — Open-Meteo on the home
zone, Time & Date, System Monitor, a local calendar — and selects the theme.
Pass `--city 13960` to add Météo-France, which needs a city no script can
guess.

Run the preflight again. It should now say `[OK]`.

---

## 5. What no script will ever do

Four things are yours, and the tools name them rather than pretending:

- **Install HACS.** Its GitHub authorization is a device-code flow tied to your
  account. Settings → Devices and services → Add integration → HACS. Without
  HACS no card can ever be installed, which is why the preflight stops there.
- **Mint a long-lived token.** Profile → Security → Long-lived access tokens.
  The instance-side scripts need it; write it to `/config/vssp/.ha_token` with
  `0600`, or paste it in the ADMIN console.
- **Pair a device.** The Hue bridge button, a Synology password, an Apple TV
  code. These are the house, not the control centre.
- **Unseal the vault.** See [Unseal.md](Unseal.md).

---

## 6. After a first deploy

Two things a deployment cannot decide for you:

- **Restart once.** The first deploy writes the `homeassistant.packages`
  block, and a reload does not load a packages block it has just created. The
  entities appear after a restart.
- **Create the on-demand dashboards.** HOME, CORE and ENERGY start absent by
  design; the ADMIN console has a CREATE button for each, or one generator run
  with `--only home,core,energy`.

Both are listed by `verify:*`, so nothing has to be remembered.
