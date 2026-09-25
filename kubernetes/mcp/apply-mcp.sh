#!/bin/sh
# Visio Sapiens - Neural Home Interface for Home Assistant
# Copyright (C) 2026 Expanse IT <expanse-it@outlook.fr>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301 USA.

########################################################################
# EN | Puts the Visio Sapiens MCP server on k3s, beside the staging Home
# EN | Assistant pod. Run it from a checkout, on the k3s host:
# EN |
# EN |   HA_TOKEN=<long-lived token> \
# EN |   MCP_API_TOKEN=<a long random string> \
# EN |     sh kubernetes/mcp/apply-mcp.sh
# EN |
# EN | Both tokens are read from the environment and never appear in a
# EN | command line, a manifest or this script - the project's rule for
# EN | every other secret it handles.
# FR | Place le serveur MCP Visio Sapiens sur k3s, a cote du pod Home
# FR | Assistant de preproduction. A lancer depuis un clone, sur l hote
# FR | k3s :
# FR |
# FR |   HA_TOKEN=<jeton longue duree> \
# FR |   MCP_API_TOKEN=<une longue chaine aleatoire> \
# FR |     sh kubernetes/mcp/apply-mcp.sh
# FR |
# FR | Les deux jetons sont lus dans l environnement et n apparaissent
# FR | jamais dans une ligne de commande, un manifeste ni ce script - la
# FR | regle du projet pour tous les autres secrets qu il manipule.
########################################################################
set -e

NS=${K3S_NAMESPACE:-homeassistant}
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
DRY=""
[ "$1" = "--dry-run" ] && DRY="--dry-run=client"

say() { echo "[vssp-mcp] $*"; }
die() { echo "[ERR] $*" >&2; exit 1; }

command -v kubectl >/dev/null 2>&1 || die "kubectl not found"

# EN | Same trap as apply-haos.sh hit for real: k3s ships its own kubectl
# EN | wrapper which reads /etc/rancher/k3s/k3s.yaml first, a file only root
# EN | can read, so an account with a perfectly good ~/.kube/config still
# EN | gets "permission denied" on a file it never named. "try sudo" was the
# EN | wrong advice - none of this needs root, it needs a readable config.
# FR | Meme piege que celui rencontre pour de vrai par apply-haos.sh : k3s
# FR | embarque son propre kubectl qui lit d abord /etc/rancher/k3s/k3s.yaml,
# FR | un fichier que seul root peut lire, donc un compte avec un
# FR | ~/.kube/config parfaitement valide obtient « permission denied » sur
# FR | un fichier qu il n a jamais nomme. « try sudo » etait un mauvais
# FR | conseil - rien ici ne demande root, cela demande une config lisible.
if [ -z "$KUBECONFIG" ] && [ -r "$HOME/.kube/config" ]; then
  export KUBECONFIG="$HOME/.kube/config"
  say "using $KUBECONFIG"
fi

kubectl version >/dev/null 2>&1 || die "kubectl cannot reach the cluster.
      Give yourself a readable copy of the k3s kubeconfig once:
        sudo install -D -o \$USER -g \$USER -m 600 \
          /etc/rancher/k3s/k3s.yaml \$HOME/.kube/config"
[ -n "$HA_TOKEN" ] || die "HA_TOKEN is not set. There is no Supervisor on k3s, so a long-lived token is the only way in."

# ---------------------------------------------------------------------------
# EN | FIND THE SERVICE RATHER THAN ASSUME ITS NAME. Same reasoning as
# EN | apply-https.sh: a manifest carrying a guessed service name fails at
# EN | runtime, inside a container, with a connection error that names
# EN | nothing useful. Here the failure would be worse than usual, because
# EN | the server would start perfectly and only fail on the first tool
# EN | call.
# FR | TROUVER LE SERVICE PLUTOT QUE SUPPOSER SON NOM. Meme raisonnement
# FR | qu apply-https.sh : un manifeste portant un nom de service devine
# FR | echoue a l execution, dans un conteneur, avec une erreur de connexion
# FR | qui ne nomme rien d utile. Ici l echec serait pire que d habitude,
# FR | car le serveur demarrerait parfaitement et n echouerait qu au premier
# FR | appel d outil.
# ---------------------------------------------------------------------------
SVC=$(kubectl get svc -n "$NS" -l app=homeassistant \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
[ -z "$SVC" ] && SVC=$(kubectl get svc -n "$NS" \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
[ -z "$SVC" ] && die "no service found in namespace $NS - is this the right namespace?"

PORT=$(kubectl get svc -n "$NS" "$SVC" \
        -o jsonpath='{.spec.ports[0].port}' 2>/dev/null || echo 8123)
HA_URL="http://$SVC.$NS.svc.cluster.local:$PORT"
say "home assistant service: $SVC (port $PORT)"
say "the server will read:   $HA_URL"

# ---------------------------------------------------------------------------
# EN | THE CODE, FROM THE REPOSITORY, EVERY TIME. A ConfigMap rebuilt from
# EN | the checkout on each apply means there is exactly one copy of this
# EN | server in git and no image to rebuild for a one-line change. The
# EN | shared websocket client travels the same way, so the pod runs the
# EN | same vssp_ws.py as everything else in the project.
# FR | LE CODE, DEPUIS LE DEPOT, A CHAQUE FOIS. Une ConfigMap reconstruite
# FR | depuis le clone a chaque application signifie qu il existe exactement
# FR | une copie de ce serveur dans git et aucune image a reconstruire pour
# FR | une modification d une ligne. Le client websocket partage voyage de
# FR | la meme facon, donc le pod execute le meme vssp_ws.py que tout le
# FR | reste du projet.
# ---------------------------------------------------------------------------
for f in "$ROOT/vssp_mcp/__init__.py" "$ROOT/vssp_mcp/ha.py" \
         "$ROOT/vssp_mcp/server.py" "$ROOT/vssp/vssp_ws.py"; do
  [ -f "$f" ] || die "missing $f - run this from a full checkout"
done

say "building ConfigMap vssp-mcp-code"
kubectl create configmap vssp-mcp-code -n "$NS" \
  --from-file="__init__.py=$ROOT/vssp_mcp/__init__.py" \
  --from-file="ha.py=$ROOT/vssp_mcp/ha.py" \
  --from-file="server.py=$ROOT/vssp_mcp/server.py" \
  --from-file="vssp_ws.py=$ROOT/vssp/vssp_ws.py" \
  --dry-run=client -o yaml | kubectl apply $DRY -f -

# ---------------------------------------------------------------------------
# EN | The two secrets. MCP_API_TOKEN may be empty, and the server then says
# EN | so loudly at every start instead of pretending a read-only port is
# EN | harmless - but leaving it empty here is a choice, not an accident.
# FR | Les deux secrets. MCP_API_TOKEN peut etre vide, et le serveur le dit
# FR | alors haut et fort a chaque demarrage plutot que de pretendre qu un
# FR | port en lecture seule est inoffensif - mais le laisser vide ici est
# FR | un choix, pas un accident.
# ---------------------------------------------------------------------------
if [ -z "$MCP_API_TOKEN" ]; then
  say "WARNING: MCP_API_TOKEN is empty - the endpoint will accept anyone on the LAN"
fi

say "writing Secret vssp-mcp"
kubectl create secret generic vssp-mcp -n "$NS" \
  --from-literal="ha_token=$HA_TOKEN" \
  --from-literal="api_token=$MCP_API_TOKEN" \
  --dry-run=client -o yaml | kubectl apply $DRY -f -

say "applying Deployment and Service"
sed "s#__HA_URL__#$HA_URL#" "$HERE/deployment.yaml" | kubectl apply $DRY -f -

if [ -n "$DRY" ]; then
  say "dry run only - nothing was changed"
  exit 0
fi

# EN | A rollout restart, because neither the ConfigMap nor the Secret
# EN | changing is something Kubernetes propagates to a running pod on its
# EN | own. Without this, an apply after a code change appears to succeed
# EN | and serves the previous version.
# FR | Un redemarrage du rollout, parce que ni la ConfigMap ni le Secret qui
# FR | changent ne sont propages tout seuls par Kubernetes a un pod en cours
# FR | d execution. Sans cela, une application apres une modification de
# FR | code semble reussir et sert la version precedente.
kubectl rollout restart deployment/vssp-mcp -n "$NS"
kubectl rollout status deployment/vssp-mcp -n "$NS" --timeout=180s

# EN | A node can carry more than one InternalIP - this one has an IPv4 and
# EN | an IPv6 - and that jsonpath returns every match, space separated. The
# EN | url printed at the end came out as
# EN |   http://192.168.1.11 2a01:cb1c:...:1953:30123
# EN | which is not an address anyone can paste. Take the first, and prefer
# EN | the IPv4: it is what a browser on this LAN and the CI job both use.
# FR | Un noeud peut porter plusieurs InternalIP - celui-ci a une IPv4 et une
# FR | IPv6 - et ce jsonpath renvoie toutes les correspondances, separees par
# FR | des espaces. L url affichee a la fin sortait sous la forme
# FR |   http://192.168.1.11 2a01:cb1c:...:1953:30123
# FR | qui n est une adresse collable par personne. Prendre la premiere, et
# FR | preferer l IPv4 : c est celle qu utilisent le navigateur du LAN et le
# FR | job CI.
NODE=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}'        | tr ' ' '
' | grep -m1 -E '^[0-9]+(\.[0-9]+){3}$'        || kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}' | awk '{print $1}')
say "ready: http://${NODE:-<node-ip>}:30099/mcp"
say "logs:  kubectl logs -n $NS deployment/vssp-mcp"
