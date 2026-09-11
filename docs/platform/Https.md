# HTTPS — Home Assistant behind Traefik

Adds encryption on port **443** by reusing the Traefik that k3s already runs.
**Port 8123 keeps serving plain HTTP, unchanged.**

---

## Why

Today your Home Assistant password and every one of your long-lived tokens
cross the network **in clear** on port 8123. That is the whole argument, and
it is enough.

It is, however, **not needed for unsealing**: the [`vssp-unseal`](Unseal.md)
service has its own TLS on 8443, with mutual TLS, and the passphrase never
passes through Home Assistant. The two subjects are independent.

## Additive, not a switch

8123 stays open, deliberately:

- the CI smoke test targets `$STAGING_URL`;
- the `command_line` sensors and internal scripts point at it;
- **it is your way back in** if the proxy configuration is wrong.

Replacing 8123 instead of adding to it would mean a mistake in
`trusted_proxies` locks you out of the machine that holds the fix.

---

## The proxy problem

**This is the trap in this setup, and it is a silent one.**

With no proxy, Home Assistant sees the browser's address. Behind Traefik it no
longer does: **every request reaches it from Traefik's pod address**, and the
client's real address survives only in the `X-Forwarded-For` header.

Three behaviours follow, and none of them is obvious:

| Configuration | What happens |
|---|---|
| Nothing set | Every client becomes one address. IP banning bans everyone or nobody, `trusted_networks` stops meaning anything, and the logs are useless. |
| `use_x_forwarded_for: true` **without** `trusted_proxies` | Home Assistant **refuses the configuration** at startup. |
| Header received from an untrusted address | Home Assistant **refuses the request with 400**. |

The third is the nasty one. An ingress applied without the matching `http:`
block produces **a site that answers nothing but errors**, with the cause in a
log nobody is looking at yet. From the browser it looks like a server
failure.

### The solution

In `configuration.yaml`, then restart Home Assistant:

```yaml
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 10.42.0.0/16      # the k3s pod network — CHECK yours, see below
```

Requests arriving **directly on 8123** carry no `X-Forwarded-For`: these two
lines do not affect them. That is what makes the move safe.

### Finding the right value

`10.42.0.0/16` is the k3s default pod network, not a guarantee.
`kubernetes/deploy/apply-https.sh` reads it from the cluster and prints it for you:

```bash
kubectl get nodes -o jsonpath='{.items[0].spec.podCIDR}'
kubectl get pods -A -l app.kubernetes.io/name=traefik -o jsonpath='{.items[*].status.podIP}'
```

**The authority on this is neither: it is Home Assistant.** If it answers 400,
its log names the exact address:

```bash
kubectl logs -n homeassistant -l app=homeassistant --tail=50 | grep -i forwarded
```

> `Received X-Forwarded-For header from an untrusted proxy 10.42.0.14`

Put **that** address, or a CIDR containing it, in `trusted_proxies`. A
tutorial that assumed a different CNI will hand you a plausible, wrong value.

### Trust the proxy and nothing else

`trusted_proxies` is a list of machines allowed to **assert who the client
is**. Putting `0.0.0.0/0` there lets anyone declare themselves any address: IP
banning and `trusted_networks` become bypassable with a forged header. The
list holds the proxy, and nothing else.

---

## The second trap: mixed content

A page served over **HTTPS cannot call an `http://` address** — the browser
blocks the request, silently except in the console. Any page served by Home
Assistant that reaches a plain-HTTP service therefore stops working the day
Home Assistant moves to HTTPS.

**Checked on this repository:** no page under `www/vssp/` is affected. The
wizards' `fetch` calls are relative to Home Assistant, so same-origin, and
they follow the page's protocol. The one `http://` found —
`http://192.168.1.50:11434` in `vssp_chatbot.html` — is a **placeholder** in
an input field: the call to Ollama is made by the server, not the browser.

Worth remembering for any page added later.

---

## Installation

```bash
# 1. Home Assistant's certificate, signed by the authority your devices
#    already trust for unsealing
sudo -u vssp-unseal vssp-unseal issue-cert homeassistant --host 192.168.1.11

# 2. the TLS secret and the ingress (inspect first)
sudo sh kubernetes/deploy/apply-https.sh --dry-run
sudo sh kubernetes/deploy/apply-https.sh

# 3. the http: block above in configuration.yaml, then restart HA
```

### Why this is manual

The pipeline cannot do it for you, and that is not a choice. The runner's Role
(`kubernetes/rbac/role.yaml`) covers `pods`, `pods/exec` and `pods/log` only:
it may create neither `secrets` nor `ingresses`. Widening that Role would give
CI the power to read every secret in the namespace — a steep price for saving
one command run once.

The script discovers the Home Assistant service instead of assuming it: a
manifest with a hard-coded backend that does not exist produces an ingress
that accepts the `apply` and then serves 503 — a slower and more confusing
failure than refusing up front.

### One authority

Home Assistant's certificate is signed by **the same authority** as the
unseal service's device certificates. You install one `ca.crt` on the phone
and get both. A second private CA would mean one more thing to install and
trust everywhere; trusting it is a single decision, made once.

### Why the ingress has no `host:`

An Ingress `host:` must be a **DNS name**. This cluster is reached by IP:
`host: 192.168.1.11` is rejected as invalid, and a name nobody resolves
matches nothing. Omitting it makes a catch-all router — which is what an
IP-addressed LAN service needs — and Traefik then serves the certificate named
in `tls.secretName`. It is the certificate that carries the IP as a
`subjectAltName`, and that is what the browser actually checks.

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| `400 Bad Request` on everything | `trusted_proxies` missing or wrong — read the log, it names the address |
| Home Assistant will not start | `use_x_forwarded_for: true` without `trusted_proxies` |
| Certificate warning | the `ca.crt` is not trusted on the device |
| `503` from Traefik | the ingress backend does not point at the right service |
| `404` on 443 | no ingress rule matches — the apply never happened |
| A page stops loading a resource | mixed content: it calls an `http://` address |
| Everything is broken | 8123 is still there, in clear, unchanged |

## Files

| Path | Contents |
|---|---|
| `kubernetes/deploy/apply-https.sh` | TLS secret, ingress, and `trusted_proxies` detection |
| `/var/lib/vssp-unseal/certs/homeassistant.{crt,key}` | the certificate Traefik serves |
| `/etc/vssp-unseal/ca.crt` | the authority to trust on the devices |

## See also

- [Unseal.md](Unseal.md) — unsealing, its mutual TLS, and why a password must
  not become a Home Assistant entity
- [Vault.md](Vault.md) — the safe itself
