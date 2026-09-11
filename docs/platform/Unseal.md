# Unseal — one password, from an enrolled device

The **`vssp-unseal`** service on the safe's host. Replaces typing three Shamir
keys after every restart with **one password**, provided the request comes
from a device carrying a certificate you issued.

---

## The trade, plainly

Vault reseals on **every restart**, by design. Today the five keys are nowhere
on the machine: even `root` cannot open the safe, a human has to type three
shares. That is the strongest arrangement available here.

This service gives some of that up, **deliberately**.

| | Before | After |
|---|---|---|
| Where the shares are | nowhere on the machine | on the machine, encrypted |
| Stolen disk or backup | nothing to steal | ciphertext, useless without the passphrase |
| Attacker already `root`, machine running | can do nothing | can wait for the typing and take the shares |
| What it takes to open | 3 keys of 5 | 1 passphrase |

**A 3-of-5 split whose three shares sleep in one file is a 1-of-1 secret.**
This service exists because that trade was made knowingly, not because it is
free. The passphrase must be long and must exist nowhere else.

Your five original keys stay valid and stay the way back in: losing the
passphrase does not lock you out of the safe, only out of this shortcut.

## What actually authenticates

Two factors, both real:

- **Something the device holds** — a client certificate, verified by **mutual
  TLS** against a private CA the tool creates. With no certificate the
  handshake fails: no error page, no 401, *nothing* — the host does not even
  reveal that a service is listening.
- **Something you know** — the passphrase, the only thing that can derive the
  key the shares are encrypted with.

### The MAC address does not count, and that is deliberate

It was asked for as a second factor. It is not one:

- it changes in a single command — `ip link set dev wlan0 address …`;
- it is **invisible the moment a router sits between** the client and the
  host: what arrives is the router's.

The service records the MAC it can see on its audit line and **lets it decide
nothing**. A MAC check would have added nothing while creating the impression
of a second factor — the worst of both worlds.

### Why not inside Home Assistant

The natural question, and the answer is the one that split the SAFE screen in
two (see [Vault.md](Vault.md)): **every entity state is written in clear to
`home-assistant_v2.db`** by the recorder, shown in Developer tools → States,
carried into backups and served to any token by `/api/states`. A password
typed into an `input_text` is a password written to disk. HTTPS would protect
the journey, not the storage — and the instance is plain HTTP anyway.

The button can live on the SAFE screen; the **typing** goes straight to this
service and never enters the state machine.

## What the service can and cannot do

It unseals. It cannot seal, cannot read a secret, cannot write one. It reaches
exactly two routes on the local Vault: `sys/seal-status` and `sys/unseal`.
**Compromising this service compromises the unseal step, not the safe's
contents.**

The systemd unit is hardened to match: `NoNewPrivileges`,
`ProtectSystem=strict`, `ProtectHome`, an empty `CapabilityBoundingSet`,
`MemoryDenyWriteExecute`, `SystemCallFilter=@system-service`, and no address
family but IP.

## Installation

On the host, in this order. Nothing is served before step 4.

```bash
sudo sh vault/unseal/install.sh          # account, directories, systemd unit

# 1. this host's certificate - every address your devices will use
sudo -u vssp-unseal vssp-unseal enroll-server 192.168.1.11

# 2. the keys. Prefer a SEALED safe: each key is then verified against Vault
#    before anything is written.
sudo -u vssp-unseal vssp-unseal enroll-keys

# 3. one certificate per device
sudo -u vssp-unseal vssp-unseal enroll-device 'phone'
sudo -u vssp-unseal vssp-unseal enroll-device 'laptop'

# 4. start it
sudo systemctl enable --now vssp-unseal
```

**Nothing is ever printed**: keys and passphrase go through `getpass`, so no
echo, no shell history, and nothing in `argv` where any user on the host could
read them out of `/proc`.

Step 2 **verifies each key** when the safe is sealed: it submits the key,
checks that Vault's counter advanced, and resets the counter at the end. A
typo is found there, not at two in the morning. With the safe open,
verification is impossible and the tool says so instead of implying otherwise.

### On the devices

Copy `/var/lib/vssp-unseal/devices/<name>.p12` and `/etc/vssp-unseal/ca.crt`
to the device, then import them:

- **iOS** — open the file, Settings → Profile Downloaded, then Settings →
  General → About → Certificate Trust Settings to trust the `ca.crt`.
- **Android** — Settings → Security → Encryption → Install a certificate.
- **Firefox** — Settings → Privacy → Certificates → View Certificates → Your
  Certificates → Import.
- **Chrome / Edge / Safari** — import into the system store.

The `.p12` is protected by an export password of its own, asked for in step 3:
the file has to travel to the device, and it should not be a usable identity
while in transit. Delete it once imported.

## Day to day

`GET /status` and `POST /unseal` on `https://<host>:8443`, client certificate
required.

```bash
curl --cert phone.pem --cacert ca.crt https://192.168.1.11:8443/status
curl --cert phone.pem --cacert ca.crt -X POST \
     -d '{"passphrase":"..."}' https://192.168.1.11:8443/unseal
```

Five wrong passphrases and the door stays shut for **fifteen minutes**,
including to the right one. The counter is persisted: restarting the service
does not clear it, and only `root` can restart it.

## Cryptography

| | |
|---|---|
| Derivation | `scrypt` (standard library), N=2¹⁷, r=8, p=1 → ~128 MB and ~0.3 s per attempt |
| Encryption | AES-256-GCM, salt and nonce drawn fresh on every write |
| Also authenticated | the version and **the KDF parameters**, so nobody can have the blob re-read under weaker settings |
| Certificates | ECDSA P-256, private CA, `CERT_REQUIRED` on the server |

The GCM tag makes a wrong passphrase fail as a **decryption error** rather
than as plausible-looking garbage that would then be posted to Vault as if it
were a key.

The service does not distinguish, in its answer, "wrong passphrase" from
"tampered file": saying which would tell an attacker, for free, whether the
file is intact.

> **A trap hit while writing this.** `hashlib.scrypt(..., maxmem=0)` reads as
> "no limit" and means "OpenSSL's own limit", which is 32 MB — while N=2¹⁷
> needs 128. The honest parameters therefore fail outright with `memory limit
> exceeded` until the ceiling matches them. It is computed from `n`, `r` and
> `p`, so raising the cost later cannot bring the failure back.

## Files

| Path | Contents |
|---|---|
| `/etc/vssp-unseal/shares.enc` | the three encrypted shares (0600) |
| `/etc/vssp-unseal/ca.{crt,key}` | the private authority |
| `/etc/vssp-unseal/server.{crt,key}` | the host's certificate |
| `/etc/vssp-unseal/state.json` | failure counters and lockouts |
| `/var/lib/vssp-unseal/devices/` | the issued `.p12` bundles |
| `vault/unseal/vssp_unseal.py` | the tool — enrolment and service |
| `vault/unseal/install.sh` | account, directories, systemd unit |

## Troubleshooting

| Symptom | Cause |
|---|---|
| The browser offers no certificate | the `.p12` is not imported, or the `ca.crt` is not trusted |
| `403 denied` | wrong passphrase — or a tampered file; the service does not say which |
| `429 locked` | five failures; wait, or `sudo rm /etc/vssp-unseal/state.json` |
| `503 not enrolled` | step 2 was never done |
| `502 vault unreachable` | the Vault container is stopped — that is not a seal problem |

Logs are in `journalctl -u vssp-unseal`. They carry the timestamp, the
certificate name, the IP, the MAC seen and the outcome — **never** the
passphrase or a share.

## See also

- [Vault.md](Vault.md) — the safe itself, and why secrets do not cross Home
  Assistant's state machine
- [../dashboards/Updates.md](../dashboards/Updates.md) — why a sealed safe no
  longer empties the UPDATES screen
