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

### Getting the two files off the host

`/var/lib/vssp-unseal/devices` and `/etc/vssp-unseal` are **0700, owned by the
service account**, so `scp` as your own user fails with `Permission denied`
before it reads a byte. Copy them out and change ownership in the same breath:

```bash
sudo ls /var/lib/vssp-unseal/devices/        # the exact file name

sudo install -o neo -g neo -m 600 \
     /var/lib/vssp-unseal/devices/<name>.p12 /home/neo/
sudo install -o neo -g neo -m 644 /etc/vssp-unseal/ca.crt /home/neo/
```

From the workstation:

```bash
scp neo@192.168.1.11:/home/neo/<name>.p12 .
scp neo@192.168.1.11:/home/neo/ca.crt .
```

Then destroy the intermediate copies — a readable identity has no business
lingering in a home directory:

```bash
shred -u /home/neo/<name>.p12 && rm -f /home/neo/ca.crt
```

### Two files, two stores

This is where it goes wrong most often. The `.p12` and the `ca.crt` do **not**
go to the same place, and installing one of them is not half the job:

| File | What it is | Where it goes |
|---|---|---|
| `<name>.p12` | **your identity** — certificate *and* private key | the personal / user store |
| `ca.crt` | **the authority** that signed the server | the trusted-root store |

Without the `.p12`, the service drops the connection during the handshake.
Without the `ca.crt`, your own client rejects the server. The two failures
look nothing alike; the troubleshooting table names both.

### Windows

In **PowerShell**, from the folder holding the two files:

```powershell
certutil -user -addstore Root ca.crt
certutil -user -importpfx My <name>.p12
Get-ChildItem Cert:\CurrentUser\My |
  Where-Object { $_.Subject -like "*<name>*" } |
  Select-Object Thumbprint, Subject, NotAfter
```

`certutil -importpfx` asks for the export password and does not echo it. The
thumbprint printed by the third command is the client certificate's address
from then on:

```powershell
curl.exe --ssl-no-revoke --cert "CurrentUser\MY\<THUMBPRINT>" `
         https://192.168.1.11:8443/status
```

Chrome and Edge read this store. Firefox keeps its own: Settings → Privacy →
Certificates → View Certificates → Your Certificates → Import.

#### Why not `--cert <file>.p12` on Windows

Because Windows `curl` is built against **schannel**, and schannel **never
prompts for a .p12 password**. Handed the file alone, curl tries an empty
password and reports something that reads like a wrong one:

```
curl: (58) schannel: Failed to import cert file EXPANSE-IT.p12, password is bad
```

The file form therefore needs the password glued to the path —
`--cert-type P12 --cert "C:\path\name.p12:password"` — which leaves a secret in
the shell history and breaks outright if the password itself contains a `:`.
The store route has neither problem. (The `C:` of a Windows path is not
mistaken for that separator: curl recognises a drive letter.) And if schannel
answers `--cacert is not supported`, drop the flag — the authority is already
in the root store from the first command.


#### `CRYPT_E_NO_REVOCATION_CHECK`

```
curl: (35) schannel: next InitializeSecurityContext failed:
CRYPT_E_NO_REVOCATION_CHECK - the revocation function was unable to check
revocation for the certificate
```

This one arrives **after** the client certificate was accepted: it is your own
machine refusing the server. Windows tries to check whether the server's
certificate has been revoked, and a private authority publishes neither a CRL
nor an OCSP responder, so there is nothing to ask and schannel fails closed.

```powershell
curl.exe --ssl-no-revoke --cert "CurrentUser\MY\<THUMBPRINT>" `
         https://192.168.1.11:8443/status
```

That flag is not a security shortcut here. There is no revocation service to
reach for this CA, deliberately: **you** are the authority, and revoking a
device means deleting its certificate on the host — `rm
/var/lib/vssp-unseal/devices/<name>.p12` and reissuing, after which the old
certificate still validates and the only real protection is the passphrase.
Browsers soft-fail this check on their own; Windows `curl` is the strict one.

### Android

Settings → Security → **Encryption & credentials** → *Install a certificate*,
**twice**, because Android sorts the two itself:

- *CA certificate* for `ca.crt`. It will warn you about what a private
  authority means; that warning is accurate, and the answer is that you are the
  authority.
- *VPN & app user certificate* for the `.p12`, which asks for the export
  password.

### iOS / iPadOS

Open each file, then Settings → General → **VPN & Device Management** →
Install. Then the step everybody misses: Settings → General → About →
**Certificate Trust Settings**, and switch on full trust for `VSSP Unseal CA`.
A CA installed but not trusted there does nothing at all, silently.

### Checking it works

On Linux or macOS, where curl is built against OpenSSL and the file form is
fine:

```bash
curl --cert-type P12 --cert '<name>.p12:<export password>' \
     --cacert ca.crt https://192.168.1.11:8443/status
```

Expected, from a safe that is currently open:

```json
{"sealed": false, "t": 3, "n": 5, "progress": 0}
```

`Failed to connect to 192.168.1.11 port 8443` is a different statement: the
service is not running. `systemctl is-active vssp-unseal` on the host, and
`ss -ltn | grep 8443` to see it listening.

Once imported, delete the `.p12` from the device's filesystem — the certificate
store holds it now, and the file is a second copy of an identity.

## Day to day

`GET /status` and `POST /unseal` on `https://<host>:8443`, client certificate
required.

```bash
# Linux / macOS — OpenSSL curl takes the .p12 straight from the file
curl --cert-type P12 --cert 'phone.p12:<export password>' --cacert ca.crt \
     https://192.168.1.11:8443/status
curl --cert-type P12 --cert 'phone.p12:<export password>' --cacert ca.crt \
     -X POST -d '{"passphrase":"..."}' https://192.168.1.11:8443/unseal
```

```powershell
# Windows — from the certificate store, see "Why not --cert <file>.p12" above
curl.exe --ssl-no-revoke --cert "CurrentUser\MY\<THUMBPRINT>" `
         https://192.168.1.11:8443/status
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
| `502 vault unreachable`, or `Connection refused` during enrolment | the safe is not where the tool is looking — see below. A stopped container looks the same; check both |
| `schannel: ... password is bad` | Windows curl was handed the `.p12` as a file; schannel never asks for its password — use the certificate store |
| `scp: Permission denied` on the `.p12` | it is 0600 inside a 0700 directory owned by the service account; copy it out with `sudo install -o <you>` first |
| TLS `certificate required`, or the handshake closes | the `.p12` is not in the personal store, or the client was not told to present it |
| `CRYPT_E_NO_REVOCATION_CHECK` | Windows cannot check revocation against a private CA, which publishes none — add `--ssl-no-revoke` |
| `unknown CA`, `self-signed certificate in chain` | the `ca.crt` is not in the trusted-root store — that is the other half of the job |
| A certificate installed on iOS changes nothing | Certificate Trust Settings was never switched on for the CA |

### `Connection refused` when the container is running

Docker publishes a port **on one address**, and on this host it chose
the LAN address:

```
vssp-vault | Up 2 hours (healthy) | 192.168.1.11:8200->8200/tcp
```

A binding written like that answers there **and nowhere else** — a
client aiming at `127.0.0.1` is refused, which reads like an outage
while the safe is healthy. Ask docker instead of guessing:

```bash
docker port vssp-vault 8200/tcp
curl -s http://192.168.1.11:8200/v1/sys/seal-status
```

`install.sh` reads that binding and writes it into the unit as
`Environment=VSSP_VAULT_ADDR=`; `systemctl cat vssp-unseal` shows the
address in use. For a one-off command, prefix it:
`sudo -u vssp-unseal env VSSP_VAULT_ADDR=http://192.168.1.11:8200 vssp-unseal enroll-keys`.

Logs are in `journalctl -u vssp-unseal`. They carry the timestamp, the
certificate name, the IP, the MAC seen and the outcome — **never** the
passphrase or a share.

## See also

- [Vault.md](Vault.md) — the safe itself, and why secrets do not cross Home
  Assistant's state machine
- [../dashboards/Updates.md](../dashboards/Updates.md) — why a sealed safe no
  longer empties the UPDATES screen
