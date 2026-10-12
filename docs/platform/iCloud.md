# iCloud Photos — moving a library onto storage you own

**English** · [Français](iCloud.fr.md)

iCloud fills up. The usual answer is to pay for more of it. This screen is the
other answer: bring the photos and videos you want to keep onto storage this
house owns — a partition on the Ubuntu host, or a NAS share — and only then
free the copy that sits at Apple.

The order matters and is enforced in code: **nothing is ever removed from
iCloud before the file has been written somewhere else and its size read back
from disk.**

---

## 1. What the screen does

ADMIN console → **iCLOUD PHOTOS**.

| | |
|---|---|
| **Counters** | how many photos, how many videos, what they weigh, how much is left on the destination |
| **Picker** | a filmstrip of thumbnails — switchable to a grid — with filters (all / not transferred / already stored / photos / videos) |
| **Transfer** | the ticked items, or everything still missing, to your storage |
| **Release** | delete from iCloud what the ledger proves is stored here |
| **Storage** | the destination's free space, and growing the volume behind it |

---

## 2. The engine: one `pip install`

The screen's INSTALL ENGINE button runs `pip install icloudpd`. That single
package delivers both halves of what this feature needs:

- **the `icloudpd` command** — a download loop hardened against Apple for
  years: resumable, rate-limit aware, and carrying `--keep-icloud-recent-days`,
  the one option that expresses this whole feature in a single pass (download,
  then delete in iCloud what was just stored, except the last N days);
- **the `pyicloud_ipd` module**, vendored inside that same distribution — the
  library the command itself talks to. Importing it gives per-asset access (an
  id, a size, a thumbnail), which the command line cannot express: no icloudpd
  flag means *"these 37 items I ticked"*.

So the two paths are not two ways of doing the same thing — they are the only
two things each tool can do:

```
PICK   a thumbnail grid, hand-picked items   ->  the library
BULK   everything still missing locally      ->  the command
```

Both write into the same tree (`<dest>/YYYY/MM/`) and the same ledger, and both
ride on **one** trusted session in **one** cookie directory. That shared
session is why the library used is `pyicloud_ipd` and not plain `pyicloud`: the
session files icloudpd reads are the ones its own library writes.

`pyicloud` is accepted as a fallback for the picker. On an instance that only
has it, the grid works and the bulk button explains why it is unavailable.

> **On Home Assistant OS, a core update replaces the container and wipes
> anything pip installed into it.** The screen will then say *Engine missing* —
> press INSTALL ENGINE again. This dependency is deliberately **not** in
> `vssp/requirements.yaml` and **not** installed by the deploy: the manifest
> covers what the control centre needs in order to be drawn, and a house that
> never opens this screen should not carry fifteen transitive packages.

---

## 3. Signing in

**Use the real Apple ID password.** Apple's app-specific passwords only open
the published CalDAV/IMAP services; the photo library is not one of them.

**The password never becomes a Home Assistant entity**, and that is a
deliberate departure from how the Google client secret next door is handled.
An `input_text` with `mode: password` only masks the box in the UI: the value
itself lives in the state machine, is written to the recorder database, is
broadcast over the websocket to every connected frontend, and is readable by
any Home Assistant user and any integration. A Google OAuth client id tolerates
that — it is half of a public pair. An Apple ID password opens photos, backups,
Find My and the account itself.

So it goes from the form to the webhook to a 0600 file at
`/config/vssp/.icloud_password`, handed to the writer as a service-call
variable, without ever entering the state machine. It is base64-wrapped on the
way through — not for secrecy but for quoting: the value is interpolated into a
shell command inside single quotes, and a password containing an apostrophe,
a backtick or `$(…)` would otherwise be handed to the shell as code.

### The one step that cannot be automated

Apple sends a six-digit code to your trusted devices. No form can read it from
there, exactly as OAuth is designed so the account owner clicks consent in
Google's own UI. Enter it in step 2 of the embedded form.

Once validated, the session is trusted for **about two months** and nothing
asks again — including every `icloudpd` run, which reuses it rather than being
handed a password.

**SEND A NEW CODE** is a button you press knowingly: asking Apple for a new
code *voids the one already on your phone*. Nothing in this feature requests a
code on its own, because doing so during the very call that validates a code is
an endless prompt — type a code, a fresh one is requested, the typed one is now
stale, repeat. With HSA2 Apple sends the code by itself when the sign-in
happens, so the one that arrives after SAVE & CONNECT is the one to type.

The code is taken by the library rather than by `icloudpd --auth-only` for one
practical reason: icloudpd reads the code from a console prompt or a web UI and
has no flag to be handed one, while the library has `validate_2fa_code()`. The
session that comes out is the same session, in the same directory.

---

## 4. Where the files go

| Field | Meaning |
|---|---|
| **Destination** | the path as *Home Assistant* sees it, e.g. `/media/icloud` |
| **Host path** | the same place as the *Ubuntu host* sees it, e.g. `/srv/photos` |

A partition or a NAS share added in **Settings → System → Storage** appears
under `/media` and needs no further plumbing. For a NAS, that is all — leave
the host path empty.

The host path exists only for the resize, and only this field can supply it: a
bind mount hides its own origin, so the container cannot deduce which host path
— and therefore which logical volume — is underneath it.

Files land as `<dest>/YYYY/MM/<filename>`, the same shape icloudpd writes with
`--folder-structure {:%Y/%m}`, so the two paths fill one tree rather than two.
When a name is already taken the asset id is appended: Apple reuses
`IMG_0001.HEIC` across years and devices, and collapsing two different photos
onto one path would lose one of them silently.

---

## 5. Growing the volume

GROW VOLUME runs `lvextend -r -L +<size>` on the Ubuntu host, over the SSH
transport of `vssp_infra_updates.py`, with the credentials already in the safe
as `host_ssh`. A **sealed Vault** therefore answers *"the safe is shut"* here
too — unseal it first (see [Unseal](Unseal.md)).

**Growing only.** Shrinking and repartitioning are refused by name, with the
reason:

- `lvextend -r` on a mounted volume is online, journalled and recoverable by
  growing again — LVM and ext4/xfs both support it while the data is in use;
- shrinking is none of those: xfs cannot shrink at all, ext4 must be unmounted,
  and a mistake takes the photo library with it;
- repartitioning is further still from anything a dashboard button should
  reach.

A network destination is not growable from here either — a NAS is grown on the
NAS. The screen says which case it is in.

---

## 6. Freeing iCloud

Two routes, both of which refuse to delete anything that is not provably here.

**Per item** — tick in the picker, then REMOVE SELECTED FROM iCLOUD. The proof
is deliberately narrow: the ledger names a path, that path exists, and its size
on disk equals the size recorded at transfer. An item failing any of the three
is skipped and counted, never deleted.

**In bulk** — switch on **FREE iCLOUD AFTER A BULK TRANSFER** and set **DAYS
KEPT IN iCLOUD** (30 by default), then TRANSFER EVERYTHING. icloudpd stores
each file and then removes it from iCloud, keeping anything inside the window.
The confirmation dialog says so, rather than assuming the switch was noticed.

Deleted items go to Apple's *Recently Deleted* for 30 days, so there is one
more net underneath — but do not rely on it.

---

## 7. A note on the thumbnails

Home Assistant serves `/config/www` as `/local/` **without authentication**:
any browser that can reach the instance can read a file there if it can name
it. The picker needs thumbnails in a browser, and an iframe has no Bearer token
to offer, so no authenticated path is available to it.

Rather than pretend the directory is private, the names are made unguessable
and the stay short:

- each thumbnail is `HMAC-SHA256(salt, asset id)[:32].jpg`, the salt in a 0600
  file created once per instance;
- a transferred item's thumbnail is erased the moment the file lands;
- only the page being looked at is ever materialised;
- ERASE THUMBNAILS clears the rest.

---

## 8. Files

| File | Role |
|---|---|
| `vssp/vssp_icloud.py` | the bridge — link, scan, page, transfer, bulk, release, storage, grow |
| `home-assistant/packages/vssp_icloud.yaml` | helpers, commands, sensors, scripts, the webhook |
| `home-assistant/www/vssp/wizard/vssp_icloud.html` | the embedded form and the picker |
| `/config/vssp/icloud_index.json` | the library index (id, name, kind, size, date) |
| `/config/vssp/icloud_ledger.json` | what is stored where — the record that authorises a deletion |
| `/config/www/vssp/icloud_status.json` | polled by the console's sensors and the form |
| `/config/www/vssp/icloud_page.json` | one screenful of thumbnails, rewritten on every scroll |
| `/config/vssp/icloud.log` | output of the detached runs |

Long actions (scan, transfer, bulk, release) relaunch themselves detached,
because a `shell_command` is killed at 60 seconds and none of these is a
60-second job. A pid lock keeps two from running at once, and a stale lock —
the process is gone after a container restart — is taken over rather than left
to block the screen.

---

## 9. Troubleshooting

| Symptom | Cause |
|---|---|
| *Engine missing* | `icloudpd` is not installed, or a core update wiped it. Press INSTALL ENGINE. |
| *Code required* returns every time | Three distinct causes, and the message now names which: the code was **rejected** (it is single-use — press SEND A NEW CODE and type the one that arrives); the code was **accepted but the session was not trusted** (check `/config/vssp/.icloud_session` survives restarts, and that the Apple ID has no Advanced Data Protection); or the **session directory is not writable**, so every run starts a new session and every code is stale on arrival. |
| The bulk button is greyed out | the `icloudpd` **command** is missing although the module is present — only the picker works. Press INSTALL ENGINE. |
| *icloudpd stopped with code …: session expired* | the trusted session aged out. Sign in again in step 1; no password reaches icloudpd's command line. |
| Nothing was removed from iCloud | none of the ticked items is in the ledger with a matching size on disk. Transfer them first. |
| *not an LVM logical volume* | the destination is not on LVM, or the host path is wrong. Check `findmnt --target <host path>` on the host. |
| The resize says the safe is shut | Vault reseals on every restart by design — see [Unseal](Unseal.md). |
| The grid is empty | no index yet. Press SCAN LIBRARY; the first pass on a large library takes a while and reports as it goes. |
