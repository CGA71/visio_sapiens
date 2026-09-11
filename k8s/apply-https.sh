#!/bin/sh
# EN | Puts Home Assistant behind the Traefik that k3s already runs, on 443,
# EN | with a certificate signed by the same authority as the unseal service.
# EN | ADDITIVE, NOT A SWITCH: port 8123 keeps serving plain HTTP exactly as it
# EN | does today. The CI smoke test, the command_line sensors and anything
# EN | else pointing at 8123 go on working, and — the part that matters — 8123
# EN | stays the way back in if the proxy configuration is wrong. Replacing
# EN | 8123 instead of adding to it would mean a mistake in trusted_proxies
# EN | locks the operator out of the machine that holds the fix.
# FR | Place Home Assistant derriere le Traefik que k3s fait deja tourner, sur
# FR | 443, avec un certificat signe par la meme autorite que le service de
# FR | descellement.
# FR | ADDITIF, PAS UNE BASCULE : le port 8123 continue de servir en HTTP clair
# FR | exactement comme aujourd hui. Le test de fumee de la CI, les capteurs
# FR | command_line et tout ce qui pointe sur 8123 continuent de marcher, et —
# FR | c est le point important — 8123 reste la porte de secours si la
# FR | configuration du proxy est fausse. Remplacer 8123 au lieu de s y ajouter
# FR | ferait qu une erreur dans trusted_proxies enfermerait l operateur dehors
# FR | de la machine qui contient le correctif.
set -e

NS=${K3S_NAMESPACE:-homeassistant}
SECRET=homeassistant-tls
INGRESS=homeassistant-https
CERT_DIR=${CERT_DIR:-/var/lib/vssp-unseal/certs}
CRT="$CERT_DIR/homeassistant.crt"
KEY="$CERT_DIR/homeassistant.key"
DRY=""
[ "$1" = "--dry-run" ] && DRY="--dry-run=client"

say() { echo "[vssp-https] $*"; }
die() { echo "[ERR] $*" >&2; exit 1; }

command -v kubectl >/dev/null 2>&1 || die "kubectl not found"
kubectl version >/dev/null 2>&1 || die "kubectl cannot reach the cluster (try sudo)"
[ -f "$CRT" ] || die "$CRT missing — run: vssp-unseal issue-cert homeassistant --host <ip>"
[ -f "$KEY" ] || die "$KEY missing"

# ---------------------------------------------------------------------------
# EN | Find the service rather than assume its name. A manifest with a
# EN | hard-coded backend that does not exist produces an Ingress that accepts
# EN | the apply and then serves 503, which is a slower and more confusing
# EN | failure than refusing here.
# FR | Trouver le service plutot que supposer son nom. Un manifeste au backend
# FR | code en dur qui n existe pas produit un Ingress qui accepte l apply puis
# FR | sert du 503 : un echec plus lent et plus deroutant que refuser ici.
# ---------------------------------------------------------------------------
SVC=$(kubectl get svc -n "$NS" -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' 2>/dev/null \
      | grep -i -m1 'home\|assistant' || true)
[ -n "$SVC" ] || die "no Home Assistant service found in namespace $NS"
PORT=$(kubectl get svc -n "$NS" "$SVC" -o jsonpath='{.spec.ports[0].port}')
say "backend -> service/$SVC:$PORT in namespace $NS"

# ---------------------------------------------------------------------------
# EN | THE PROXY TRAP, measured rather than guessed. Once Home Assistant sits
# EN | behind Traefik, every request reaches it from Traefik's pod address, and
# EN | the browser's real address arrives only in the X-Forwarded-For header.
# EN | Home Assistant ignores that header unless told to trust the sender, and
# EN | a request carrying it from an untrusted address is REFUSED with 400 —
# EN | so an ingress without the matching http: block produces a site that
# EN | answers nothing but errors, with the cause in a log nobody is looking
# EN | at yet.
# EN | The value to trust is therefore read from the cluster here, instead of
# EN | being copied from a tutorial that assumed a different CNI.
# FR | LE PIEGE DU PROXY, mesure plutot que devine. Des que Home Assistant est
# FR | derriere Traefik, chaque requete lui parvient depuis l adresse du pod
# FR | Traefik, et l adresse reelle du navigateur n arrive que dans l en-tete
# FR | X-Forwarded-For. Home Assistant ignore cet en-tete tant qu on ne lui dit
# FR | pas de faire confiance a l emetteur, et une requete qui le porte depuis
# FR | une adresse non approuvee est REFUSEE en 400 — un ingress sans le bloc
# FR | http: correspondant produit donc un site qui ne repond que des erreurs,
# FR | avec la cause dans un journal que personne ne regarde encore.
# FR | La valeur a approuver est donc lue dans le cluster ici, au lieu d etre
# FR | recopiee d un tutoriel qui supposait un autre CNI.
# ---------------------------------------------------------------------------
TRAEFIK_IP=$(kubectl get pods -A -l app.kubernetes.io/name=traefik \
             -o jsonpath='{.items[*].status.podIP}' 2>/dev/null || true)
[ -n "$TRAEFIK_IP" ] || TRAEFIK_IP=$(kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.status.podIP}{"\n"}{end}' \
             2>/dev/null | grep -m1 '^traefik' | awk '{print $2}' || true)
POD_CIDR=$(kubectl get nodes -o jsonpath='{.items[0].spec.podCIDR}' 2>/dev/null || true)
say "traefik pod address : ${TRAEFIK_IP:-not found}"
say "node pod CIDR       : ${POD_CIDR:-not found}"

cat <<MANIFEST > /tmp/vssp-ha-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: $INGRESS
  namespace: $NS
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
spec:
  ingressClassName: traefik
  tls:
    - secretName: $SECRET
  rules:
    - http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: $SVC
                port:
                  number: $PORT
MANIFEST

# EN | No `host:` and no `tls.hosts:`. An Ingress host must be a DNS name, and
# EN | this cluster is reached by IP — a rule with `host: 192.168.1.11` is
# EN | rejected as invalid, and one with a name nobody resolves matches
# EN | nothing. Omitting it makes a catch-all router, which is what an
# EN | IP-addressed LAN service needs, and Traefik then serves the certificate
# EN | named in tls.secretName. The certificate itself carries the IP as a
# EN | subjectAltName, which is what the browser actually checks.
# FR | Pas de `host:` ni de `tls.hosts:`. Un host d Ingress doit etre un nom
# FR | DNS, et ce cluster se joint par IP — une regle `host: 192.168.1.11` est
# FR | rejetee comme invalide, et une regle avec un nom que personne ne resout
# FR | ne correspond a rien. L omettre cree un routeur attrape-tout, ce dont a
# FR | besoin un service de LAN adresse par IP, et Traefik sert alors le
# FR | certificat nomme dans tls.secretName. Le certificat, lui, porte l IP en
# FR | subjectAltName, et c est cela que le navigateur verifie.
say "creating/updating secret $SECRET"
kubectl create secret tls "$SECRET" -n "$NS" \
  --cert="$CRT" --key="$KEY" --dry-run=client -o yaml \
  | kubectl apply $DRY -f -

say "applying the ingress"
kubectl apply $DRY -f /tmp/vssp-ha-ingress.yaml

[ -n "$DRY" ] && { say "dry run — nothing was changed"; exit 0; }

cat <<NEXT

────────────────────────────────────────────────────────────────────────────
NOT DONE YET. Home Assistant will answer 400 to every proxied request until
it is told to trust Traefik. Add this to configuration.yaml and restart HA:

http:
  use_x_forwarded_for: true
  trusted_proxies:
    - ${POD_CIDR:-10.42.0.0/16}

Port 8123 keeps working throughout, and that is your way back in if this is
wrong. Requests arriving directly on 8123 carry no X-Forwarded-For header and
are not affected by these two lines.

If https://<host>/ then returns 400, the log names the address to trust:
  kubectl logs -n $NS -l app=homeassistant --tail=50 | grep -i forwarded
It prints "Received X-Forwarded-For header from an untrusted proxy <ip>".
Put THAT address (or a CIDR containing it) in trusted_proxies — it is the
authority, not this script's guess.

Finally, trust the authority on each device, or every visit shows a warning:
  /etc/vssp-unseal/ca.crt
────────────────────────────────────────────────────────────────────────────
NEXT
