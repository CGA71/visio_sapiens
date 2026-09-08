#!/bin/sh
########################################################################
# EN | One-shot setup of the Visio Sapiens safe, run ONCE after the safe
# EN | has been initialised and unsealed. Run it from inside the
# EN | container, handing it your root token for the duration of the call
# EN | only:
# FR | Mise en place unique du coffre Visio Sapiens, a lancer UNE FOIS le
# FR | coffre initialise et descelle. A executer depuis le conteneur, en
# FR | lui passant ton token root pour la duree de l appel seulement :
#
#     docker exec -e VAULT_TOKEN=<YOUR-ROOT-TOKEN> -it vssp-vault sh /vault/bootstrap.sh
#
# EN | The token is passed as an environment variable of that one exec, so
# EN | it lands in neither the image, nor a file, nor this repository. It
# EN | does end up in your shell history — clear it afterwards, or prefix
# EN | the command with a space if your shell honours HISTCONTROL.
# EN | Idempotent: safe to re-run after changing a policy.
# FR | Le token passe en variable d environnement de ce seul exec : il ne
# FR | finit ni dans l image, ni dans un fichier, ni dans ce depot. Il
# FR | atterrit en revanche dans l historique de ton shell — efface-le
# FR | apres coup, ou prefixe la commande d une espace si ton shell honore
# FR | HISTCONTROL.
# FR | Idempotent : re-executable sans risque apres modification d une
# FR | policy.
########################################################################
set -e

VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
export VAULT_ADDR

HA_URL="${HA_URL:-http://192.168.1.11:8123}"
ADMIN_USER="${ADMIN_USER:-neo}"

if [ -z "$VAULT_TOKEN" ]; then
  echo "[ERR] VAULT_TOKEN is not set. Pass your root token to this one exec:"
  echo "      docker exec -e VAULT_TOKEN=<YOUR-ROOT-TOKEN> -it vssp-vault sh /vault/bootstrap.sh"
  exit 1
fi

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

if vault status 2>/dev/null | grep -q "Sealed *true"; then
  echo "[ERR] The safe is sealed. Unseal it first:"
  echo "      docker exec -it vssp-vault vault operator unseal   (three times)"
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
if ! vault token lookup >/dev/null 2>&1; then
  echo "[ERR] Vault refuses this token (permission denied / invalid token)."
  echo "      It is not the root token, or it has expired or been revoked."
  echo "      The safe itself is fine - it is unsealed and answering."
  exit 1
fi

echo "[1/6] KV v2 engine at secret/"
# EN | A non-dev Vault mounts nothing by default — `secret/` has to be
# EN | created. v2 rather than v1 for the version history: overwriting a
# EN | password by mistake stays recoverable instead of final.
# FR | Un Vault non-dev ne monte rien par defaut — `secret/` doit etre
# FR | cree. v2 plutot que v1 pour l historique de versions : ecraser un
# FR | mot de passe par erreur reste rattrapable au lieu d etre definitif.
if vault secrets list -format=json | grep -q '"secret/"'; then
  echo "      already mounted"
else
  vault secrets enable -path=secret kv-v2
fi

echo "[2/6] Policies"
vault policy write vssp-ha    /vault/policies/vssp-ha.hcl
vault policy write vssp-admin /vault/policies/vssp-admin.hcl

echo "[3/6] userpass auth for the ADMIN screen"
if vault auth list -format=json | grep -q '"userpass/"'; then
  echo "      already enabled"
else
  vault auth enable userpass
fi
# EN | No password on this command line: -password is prompted for
# EN | interactively by the CLI, so it stays out of the process list and
# EN | out of your shell history.
# FR | Aucun mot de passe sur cette ligne de commande : -password est
# FR | demande interactivement par la CLI, il reste donc hors de la liste
# FR | des processus et hors de ton historique de shell.
if vault read -format=json "auth/userpass/users/$ADMIN_USER" >/dev/null 2>&1; then
  echo "      user '$ADMIN_USER' already exists — leaving its password alone"
else
  printf "      password for the VAULT screen (user '%s'): " "$ADMIN_USER"
  stty -echo 2>/dev/null || true
  read ADMIN_PASS
  stty echo 2>/dev/null || true
  echo
  vault write "auth/userpass/users/$ADMIN_USER" \
    password="$ADMIN_PASS" \
    token_policies="vssp-admin" \
    token_ttl="1h" \
    token_max_ttl="8h"
  ADMIN_PASS=""
fi

echo "[4/6] CORS for the ADMIN iframe"
# EN | The VAULT screen is served from Home Assistant on port 8123 and
# EN | talks to Vault on 8200 — a different origin as far as the browser
# EN | is concerned. Without this every request from the iframe is blocked
# EN | before it leaves, with nothing in Vault's log to explain it.
# FR | L ecran COFFRE-FORT est servi par Home Assistant sur le port 8123
# FR | et parle a Vault sur le 8200 — une origine differente du point de
# FR | vue du navigateur. Sans ceci, chaque requete de l iframe est
# FR | bloquee avant de partir, sans rien dans le journal de Vault pour
# FR | l expliquer.
vault write sys/config/cors \
  enabled=true \
  allowed_origins="$HA_URL" \
  allowed_headers="X-Vault-Token,Content-Type,X-Requested-With"

echo "[5/6] Branch layout"
# EN | Three branches, created with a placeholder so a LIST on an
# EN | untouched branch returns an empty list instead of 404 — the ADMIN
# EN | screen then shows "no entry yet" rather than an error on a safe
# EN | that is merely new.
# FR | Trois branches, creees avec un marqueur pour qu un LIST sur une
# FR | branche vierge renvoie une liste vide plutot qu un 404 — l ecran
# FR | ADMIN affiche alors « aucune entree » au lieu d une erreur sur un
# FR | coffre simplement neuf.
for branch in infra accounts apps; do
  if vault kv get "secret/vssp/$branch/.keep" >/dev/null 2>&1; then
    echo "      secret/vssp/$branch already laid out"
  else
    vault kv put "secret/vssp/$branch/.keep" note="branch placeholder — safe to destroy once this branch holds real entries" >/dev/null
    echo "      secret/vssp/$branch created"
  fi
done

echo "[6/6] Token for Home Assistant"
# EN | Periodic rather than fixed-TTL: a periodic token never reaches a
# EN | max TTL, it only has to be renewed within its period. Home
# EN | Assistant renews it on its own (see the rest_command in
# EN | packages/vssp_vault.yaml), so the safe does not silently go
# EN | unreadable a month after setup.
# EN | This token carries vssp-ha: names, never values. Even copied out of
# EN | secrets.yaml it opens nothing.
# FR | Periodique plutot qu a TTL fixe : un token periodique n atteint
# FR | jamais de TTL maximum, il doit seulement etre renouvele dans sa
# FR | periode. Home Assistant le renouvelle tout seul (voir le
# FR | rest_command dans packages/vssp_vault.yaml), donc le coffre ne
# FR | devient pas illisible en silence un mois apres l installation.
# FR | Ce token porte vssp-ha : les noms, jamais les valeurs. Meme recopie
# FR | depuis secrets.yaml, il n ouvre rien.
echo
echo "  Paste the token below into Home Assistant's /config/secrets.yaml as:"
echo "      vault_ha_token: <token>"
echo "  It grants entry NAMES and deletion, never a single value."
echo
# EN | -field=token, not JSON scraped with grep. The previous version
# EN | matched '"client_token":"..."' with no space after the colon, and
# EN | Vault pretty-prints -format=json as '"client_token": "hvs..."' WITH
# EN | one — so it matched nothing and printed an empty line where the token
# EN | should be. set -e did not catch it either: a pipeline's exit status is
# EN | the last command's, and `cut` succeeds happily on empty input, so the
# EN | script announced success having handed over nothing.
# EN | -field asks Vault for the one value, with no format to parse and
# EN | nothing that can get out of step with it.
# FR | -field=token, pas du JSON racle au grep. La version precedente
# FR | cherchait '"client_token":"..."' sans espace apres les deux-points, or
# FR | Vault met en forme -format=json en '"client_token": "hvs..."' AVEC
# FR | une espace — elle ne trouvait donc rien et imprimait une ligne vide la
# FR | ou devait etre le token. set -e ne l a pas vu non plus : le code de
# FR | sortie d un pipeline est celui du dernier maillon, et `cut` reussit
# FR | tres bien sur une entree vide, donc le script annoncait la reussite
# FR | sans avoir rien remis.
# FR | -field demande a Vault la seule valeur voulue, sans format a analyser
# FR | ni rien qui puisse s en desaccorder.
HA_TOKEN="$(vault token create \
  -policy=vssp-ha \
  -period=720h \
  -display-name=visio-sapiens-ha \
  -field=token)"

if [ -z "$HA_TOKEN" ]; then
  echo "[ERR] Vault created no token. Nothing to paste into secrets.yaml."
  echo "      Create one by hand with:"
  echo "      docker exec -e VAULT_TOKEN=<root> -it vssp-vault \\"
  echo "        vault token create -policy=vssp-ha -period=720h -field=token"
  exit 1
fi
printf '%s\n' "$HA_TOKEN"

echo
echo "[OK] Safe ready. Next: docs/platform/Vault.md, section \"After bootstrap\"."
