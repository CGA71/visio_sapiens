#!/bin/sh
########################################################################
# EN | One-shot setup of the Visio Sapiens safe, over the HTTP API.
# FR | Mise en place unique du coffre Visio Sapiens, via l API HTTP.
#
# EN | Same job as bootstrap.sh, without needing to be inside the
# EN | container. That matters because on Home Assistant OS you cannot get
# EN | inside it: the Supervisor owns the Docker daemon and `docker exec`
# EN | is unsupported. This script only needs curl, python3 and a route to
# EN | the safe, so it runs from the k3s host, from your PC, or from the
# EN | HAOS SSH add-on — against either deployment.
# FR | Meme travail que bootstrap.sh, sans avoir besoin d etre dans le
# FR | conteneur. Cela compte parce que sur Home Assistant OS on ne peut
# FR | pas y entrer : le Superviseur possede le demon Docker et
# FR | `docker exec` n est pas supporte. Ce script n a besoin que de curl,
# FR | de python3 et d une route vers le coffre : il tourne donc depuis
# FR | l hote k3s, depuis ton PC, ou depuis l add-on SSH de HAOS — contre
# FR | l un ou l autre deploiement.
#
# EN | Usage — the root token is passed as an environment variable of this
# EN | one call, so it lands in no file and in no repository:
# FR | Usage — le token root passe en variable d environnement de ce seul
# FR | appel, il n atterrit donc dans aucun fichier ni aucun depot :
#
#     VAULT_ADDR=http://192.168.1.11:8200 \
#     HA_URL=http://192.168.1.11:8123 \
#     VAULT_TOKEN=<YOUR-ROOT-TOKEN> \
#     sh vault/bootstrap-api.sh
#
# EN | It does end up in your shell history — clear it afterwards, or
# EN | prefix the command with a space if your shell honours HISTCONTROL.
# EN | Idempotent: safe to re-run after changing a policy.
# FR | Il finit en revanche dans l historique de ton shell — efface-le
# FR | apres coup, ou prefixe la commande d une espace si ton shell honore
# FR | HISTCONTROL. Idempotent : re-executable sans risque apres
# FR | modification d une policy.
#
# EN | Initialising and unsealing are deliberately NOT here. Both hand out
# EN | material that must be written down off the machine — five unseal
# EN | keys and a root token — and a script that did it for you would have
# EN | to print them into a terminal log. Do those two in the web UI at
# EN | $VAULT_ADDR/ui, or with `vault operator init` where the CLI exists.
# FR | L initialisation et le descellement ne sont volontairement PAS ici.
# FR | Les deux delivrent de la matiere qui doit etre notee hors de la
# FR | machine — cinq cles de descellement et un token root — et un script
# FR | qui le ferait a ta place devrait les imprimer dans un journal de
# FR | terminal. Faire ces deux-la dans l interface web sur $VAULT_ADDR/ui,
# FR | ou avec `vault operator init` la ou la CLI existe.
########################################################################
set -e

VAULT_ADDR="${VAULT_ADDR:-http://192.168.1.11:8200}"
HA_URL="${HA_URL:-http://192.168.1.11:8123}"
ADMIN_USER="${ADMIN_USER:-neo}"
HERE="$(dirname "$0")"

if [ -z "$VAULT_TOKEN" ]; then
  echo "[ERR] VAULT_TOKEN is not set. Pass your root token to this one call:"
  echo "      VAULT_TOKEN=<YOUR-ROOT-TOKEN> sh $0"
  exit 1
fi

command -v curl    >/dev/null || { echo "[ERR] curl is required";    exit 1; }
command -v python3 >/dev/null || { echo "[ERR] python3 is required"; exit 1; }

# EN | Every call goes through here so the token appears in exactly one
# EN | place, and is passed with -H rather than in the URL: a token in a
# EN | URL is a token in every access log between here and the safe.
# FR | Chaque appel passe par ici pour que le token n apparaisse qu a un
# FR | seul endroit, et il est passe avec -H plutot que dans l URL : un
# FR | token dans une URL est un token dans chaque journal d acces entre
# FR | ici et le coffre.
api() {
  _method="$1"; _path="$2"; _body="$3"
  if [ -n "$_body" ]; then
    curl -sS -X "$_method" \
      -H "X-Vault-Token: $VAULT_TOKEN" \
      -H "Content-Type: application/json" \
      -d "$_body" \
      "$VAULT_ADDR/v1/$_path"
  else
    curl -sS -X "$_method" \
      -H "X-Vault-Token: $VAULT_TOKEN" \
      "$VAULT_ADDR/v1/$_path"
  fi
}

# EN | Reads one field out of a JSON blob on stdin. python3 rather than jq
# EN | because python3 is already a dependency of every other vssp script,
# EN | and jq is not present on HAOS.
# FR | Lit un champ d un blob JSON sur l entree standard. python3 plutot
# FR | que jq parce que python3 est deja une dependance de tous les autres
# FR | scripts vssp, et que jq est absent de HAOS.
jget() {
  python3 -c "import sys,json
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
for k in '$1'.split('.'):
    if isinstance(d,dict) and k in d: d=d[k]
    else: sys.exit(0)
print(d if not isinstance(d,(dict,list)) else json.dumps(d))"
}

# EN | Turns a file into a JSON string. Policies are multi-line HCL with
# EN | quotes and braces; embedding one by hand would break on the first
# EN | newline.
# FR | Transforme un fichier en chaine JSON. Les policies sont du HCL
# FR | multiligne avec guillemets et accolades ; en integrer une a la main
# FR | casserait des le premier retour a la ligne.
json_file() {
  python3 -c "import json,sys
print(json.dumps({'policy': open(sys.argv[1], encoding='utf-8').read()}))" "$1"
}

# EN | This one is pure string matching and needs no Vault at all, so it
# EN | runs BEFORE the seal check. A sealed safe and a placeholder token are
# EN | two separate mistakes, and checking the safe first would have you fix
# EN | the sealing, re-run, and only then discover the token — two round
# EN | trips for two things knowable at once.
# FR | Celui-ci est de la simple comparaison de chaine et n a besoin
# FR | d aucun Vault, il tourne donc AVANT le controle de scellement. Un
# FR | coffre scelle et un token d exemple sont deux erreurs distinctes, et
# FR | verifier le coffre d abord ferait corriger le descellement, relancer,
# FR | et seulement alors decouvrir le token — deux allers-retours pour deux
# FR | choses connaissables d un coup.
case "$VAULT_TOKEN" in
  hvs.xxx*|"<"*|*your-root-token*|*ton-token-root*)
    echo "[ERR] VAULT_TOKEN is the example text from the documentation, not a token."
    echo "      Use the real root token printed once by 'vault operator init',"
    echo "      the line reading 'Initial Root Token: hvs....'."
    exit 1 ;;
esac

echo "[0/6] Reaching $VAULT_ADDR"
SEALED="$(curl -sS "$VAULT_ADDR/v1/sys/seal-status" | jget sealed)"
if [ -z "$SEALED" ]; then
  echo "[ERR] No answer from $VAULT_ADDR. Is the safe running?"
  exit 1
fi
if [ "$SEALED" = "True" ] || [ "$SEALED" = "true" ]; then
  echo "[ERR] The safe is sealed. Unseal it first (web UI at $VAULT_ADDR/ui,"
  echo "      or vault operator unseal, three times)."
  exit 1
fi


# EN | Fail here, on purpose, rather than at the first real call. Without
# EN | this the script walked straight into step 1 and answered a wrong
# EN | token with two raw 403 dumps naming sys/mounts — which reads as
# EN | "the safe is broken" when the actual cause is a token that was
# EN | never valid. The commonest wrong token is the placeholder from the
# EN | documentation, pasted verbatim, so that case is named outright.
# FR | Echouer ici, a dessein, plutot qu au premier appel reel. Sans ceci
# FR | le script fonçait a l etape 1 et repondait a un mauvais token par
# FR | deux 403 bruts nommant sys/mounts — ce qui se lit « le coffre est
# FR | casse » alors que la vraie cause est un token qui n a jamais ete
# FR | valide. Le mauvais token le plus frequent est le texte d exemple de
# FR | la documentation, colle tel quel : ce cas est donc nomme
# FR | explicitement.
if [ -z "$(api GET auth/token/lookup-self | jget data.id)" ]; then
  echo "[ERR] Vault refuses this token (permission denied / invalid token)."
  echo "      It is not the root token, or it has expired or been revoked."
  echo "      The safe itself is fine - it is unsealed and answering."
  exit 1
fi

echo "[1/6] KV v2 engine at secret/"
if api GET sys/mounts | grep -q '"secret/"'; then
  echo "      already mounted"
else
  api POST sys/mounts/secret \
    '{"type":"kv","options":{"version":"2"},"description":"Visio Sapiens"}' >/dev/null
  echo "      created"
fi

echo "[2/6] Policies"
api PUT sys/policies/acl/vssp-ha    "$(json_file "$HERE/policies/vssp-ha.hcl")"    >/dev/null
api PUT sys/policies/acl/vssp-admin "$(json_file "$HERE/policies/vssp-admin.hcl")" >/dev/null
echo "      vssp-ha, vssp-admin"

echo "[3/6] userpass auth for the SAFE screen"
if api GET sys/auth | grep -q '"userpass/"'; then
  echo "      already enabled"
else
  api POST sys/auth/userpass '{"type":"userpass"}' >/dev/null
  echo "      enabled"
fi

EXISTING="$(api GET "auth/userpass/users/$ADMIN_USER" | jget data.token_policies)"
if [ -n "$EXISTING" ]; then
  echo "      user '$ADMIN_USER' already exists — leaving its password alone"
else
  printf "      password for the SAFE screen (user '%s'): " "$ADMIN_USER"
  stty -echo 2>/dev/null || true
  read ADMIN_PASS
  stty echo 2>/dev/null || true
  echo
  # EN | Built with json.dumps so a password containing a quote, a
  # EN | backslash or an accent survives intact — and so it is never
  # EN | interpolated into a shell word where it could be re-parsed.
  # FR | Construit avec json.dumps pour qu un mot de passe contenant un
  # FR | guillemet, une barre oblique inverse ou un accent survive intact —
  # FR | et pour qu il ne soit jamais interpole dans un mot du shell ou il
  # FR | pourrait etre re-analyse.
  BODY="$(ADMIN_PASS="$ADMIN_PASS" python3 -c "import json,os
print(json.dumps({'password': os.environ['ADMIN_PASS'],
                  'token_policies': 'vssp-admin',
                  'token_ttl': '1h',
                  'token_max_ttl': '8h'}))")"
  ADMIN_PASS=""
  printf '%s' "$BODY" | curl -sS -X POST \
    -H "X-Vault-Token: $VAULT_TOKEN" -H "Content-Type: application/json" \
    -d @- "$VAULT_ADDR/v1/auth/userpass/users/$ADMIN_USER" >/dev/null
  BODY=""
  echo "      user '$ADMIN_USER' created"
fi

echo "[4/6] CORS for the SAFE screen"
# EN | The screen is served by Home Assistant and calls Vault on another
# EN | port — a different origin as far as the browser is concerned.
# EN | Without this, every request from it is blocked before it leaves,
# EN | with nothing in Vault's log to explain it.
# FR | L ecran est servi par Home Assistant et appelle Vault sur un autre
# FR | port — une origine differente du point de vue du navigateur. Sans
# FR | ceci, chaque requete qui en vient est bloquee avant de partir, sans
# FR | rien dans le journal de Vault pour l expliquer.
CORS_BODY="$(HA_URL="$HA_URL" python3 -c "import json,os
print(json.dumps({'enabled': True,
                  'allowed_origins': [os.environ['HA_URL']],
                  'allowed_headers': ['X-Vault-Token','Content-Type','X-Requested-With']}))")"
api PUT sys/config/cors "$CORS_BODY" >/dev/null
echo "      allowed origin: $HA_URL"

echo "[5/6] Branch layout"
# EN | A placeholder per branch so a LIST on an untouched one returns an
# EN | empty list instead of 404 — the SAFE screen then says "no entry"
# EN | rather than showing an error on a safe that is merely new.
# FR | Un marqueur par branche pour qu un LIST sur une branche vierge
# FR | renvoie une liste vide plutot qu un 404 — l ecran COFFRE-FORT dit
# FR | alors « aucune entree » au lieu d afficher une erreur sur un coffre
# FR | simplement neuf.
for branch in infra accounts apps; do
  if api GET "secret/metadata/vssp/$branch/.keep" | grep -q '"created_time"'; then
    echo "      secret/vssp/$branch already laid out"
  else
    api POST "secret/data/vssp/$branch/.keep" \
      '{"data":{"note":"branch placeholder - safe to destroy once this branch holds real entries"}}' >/dev/null
    echo "      secret/vssp/$branch created"
  fi
done

echo "[6/6] Token for Home Assistant"
# EN | Periodic rather than fixed-TTL: it never reaches a maximum TTL, it
# EN | only has to be renewed within its period, which the automation in
# EN | packages/vssp_vault.yaml does daily. Otherwise the safe would simply
# EN | stop answering one day, for no visible reason.
# EN | It carries vssp-ha: names, never values. Even copied out of
# EN | secrets.yaml it opens nothing.
# FR | Periodique plutot qu a TTL fixe : il n atteint jamais de TTL
# FR | maximum, il doit seulement etre renouvele dans sa periode, ce que
# FR | fait quotidiennement l automatisation de
# FR | packages/vssp_vault.yaml. Sinon le coffre cesserait simplement de
# FR | repondre un jour, sans raison visible.
# FR | Il porte vssp-ha : les noms, jamais les valeurs. Meme recopie depuis
# FR | secrets.yaml, il n ouvre rien.
echo
echo "  Paste the token below into Home Assistant's /config/secrets.yaml as:"
echo "      vault_ha_token: <token>"
echo "  It grants entry NAMES and deletion, never a single value."
echo
api POST auth/token/create \
  '{"policies":["vssp-ha"],"period":"720h","display_name":"visio-sapiens-ha"}' \
  | jget auth.client_token

echo
echo "[OK] Safe ready. Next: docs/platform/Vault.md, section \"After bootstrap\"."
