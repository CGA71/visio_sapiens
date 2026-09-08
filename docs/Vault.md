# Safe — HashiCorp Vault

Screen **ADMIN → SAFE**. Holds server access secrets (SSH, k3s, router),
accounts and application passwords, with create, modify and delete from Home
Assistant.

---

## The design argument, in one page

Anything Home Assistant reads becomes an entity state. And **every entity state
is written in clear text to `home-assistant_v2.db`** by the recorder, shown in
Developer Tools → States to any administrator, and liable to surface in an
automation trace. A safe whose contents are copied into that database the
second they are displayed protects nothing.

So the feature is split in two, and **that split is the whole security
argument**:

| | What it sees | How |
|---|---|---|
| **Home Assistant** | entry **names**, dates, versions, seal state | native RESTful sensors, token carrying the `vssp-ha` policy |
| **The screen's iframe** | the **values** | talks to Vault directly, its own session token |

The Home Assistant token is granted `secret/metadata/*` and **nothing at all on
`secret/data/*`**. In KV v2 those are two separate paths: metadata holds the
names, data holds the values. Home Assistant may list, describe and delete an
entry — and is **refused by Vault** if it ever asks what one contains.

This is not a rule the templates promise to respect: it is a rule they cannot
break. Even if `home-assistant_v2.db` leaks, no secret leaks with it.

What follows from that:

- **Create, modify, reveal** → the iframe. The value goes from the safe to the
  screen and nowhere else.
- **List, state, delete, restore** → the native cards. None of those operations
  involves a value.

---

## What this is not

- **No TLS.** The safe listens over HTTP on the LAN, as Home Assistant itself
  does. The day it becomes reachable from outside, enable TLS in
  `vault/config/vault.hcl` and point `api_addr` and the CORS origin at
  `https://`.
- **No auto-unseal.** Vault reseals itself on every restart and refuses
  everything until 3 of the 5 keys are entered. That operational cost is
  accepted on purpose: the alternatives are a cloud KMS (an external dependency
  in a local-only setup) or unseal keys sitting on the same disk (which defeats
  sealing entirely).
- **Not a browser password manager.** No extension, no autofill.

---

## Install

### 1. Docker access

The host has Docker and Compose v2. The `neo` account is not in the `docker`
group:

```bash
sudo usermod -aG docker neo   # then log back in
```

Be aware: membership of the `docker` group is equivalent to root on that
machine. Otherwise, keep `sudo` in front of every `docker` command below.

### 2. Start the safe

```bash
sudo mkdir -p /opt/vssp-vault && sudo chown neo /opt/vssp-vault
# copy vault/ from the repository into /opt/vssp-vault/
cd /opt/vssp-vault && docker compose up -d
```

### 3. Initialise

```bash
docker exec -it vssp-vault vault operator init
```

**Five unseal keys and a root token are printed. This is the only time.**

Write them down **off this machine** — on paper, or in a password manager on
another device. That is the break-glass: without them the safe is shut for
good, and with them alone someone opens it completely.

### 4. Unseal

```bash
docker exec -it vssp-vault vault operator unseal   # three times, different key
```

### 5. Configure

```bash
docker exec -e VAULT_TOKEN=hvs.xxxxx -it vssp-vault sh /vault/bootstrap.sh
```

The script mounts KV v2, writes both policies, enables `userpass`, prompts
interactively for your screen password, allows Home Assistant's origin in the
CORS config, creates the three branches, then **prints the Home Assistant
token**.

### 6. Wire Home Assistant

Paste the printed token into `/config/secrets.yaml`:

```yaml
vault_ha_token: hvs.xxxxxxxx
```

The key is already there, empty: the deploy adds it with
`vssp_ensure_secret.py`. That is deliberate — a missing `!secret` does not break
a sensor, it **stops Home Assistant from starting**.

Then restart Home Assistant.

---

## Day to day

After **every host restart** the safe is sealed. The screen says so in an
orange banner, with how many keys have been supplied. Unseal:

```bash
docker exec -it vssp-vault vault operator unseal   # three times
```

**Reveal** shows a password masked; one click shows it in clear, and it
re-masks itself after 45 seconds.

**Copy** uses the `execCommand` fallback: the modern clipboard API does not
exist outside a secure context, and this console is served over HTTP.

**Delete**, from the iframe or the MAINTENANCE card, is a *soft* delete — the
version is hidden and stays restorable. **DESTROY** takes the entry and its
whole history, with no undo.

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| "SAFE UNREACHABLE" | container stopped, **or** the origin is missing from Vault's CORS config. Re-run step 4 of `bootstrap.sh`. |
| The 3 branch sensors unavailable, the seal sensor fine | safe sealed (the branch sensors are authenticated) or `vault_ha_token` empty/expired. |
| The seal sensor unavailable too | Vault is not running at all. |
| "Refused by Vault" on reveal | you are logged in as an account whose policy is not `vssp-admin`. |
| The safe stops answering HA after weeks | the periodic token was not renewed. The `vssp_vault_renew` automation does it at 04:17; check it is not disabled. |

---

## Files

| Path | Role |
|---|---|
| `vault/docker-compose.yml` | the container |
| `vault/config/vault.hcl` | server configuration |
| `vault/policies/vssp-ha.hcl` | Home Assistant policy — names, never values |
| `vault/policies/vssp-admin.hcl` | administrator policy — the values |
| `vault/bootstrap.sh` | one-shot setup |
| `home-assistant/packages/vssp_vault.yaml` | sensors, commands, scripts |
| `home-assistant/www/vssp/wizard/vssp_vault.html` | the screen |
| `vssp/vssp_ensure_secret.py` | seeds `vault_ha_token` in `secrets.yaml` |
