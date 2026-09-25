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
# EN | Brings up Home Assistant OS as a KubeVirt VM in the `haos`
# EN | namespace - a second staging instance that is the same KIND of
# EN | machine as production, Supervisor and add-ons included.
# EN |
# EN | Run on the k3s host, from a checkout:
# EN |     sudo sh kubernetes/haos/apply-haos.sh
# EN |     sudo sh kubernetes/haos/apply-haos.sh --dry-run
# EN |     HAOS_VERSION=18.3 sudo sh kubernetes/haos/apply-haos.sh
# EN |
# EN | It does NOT install the KubeVirt and CDI operators. Those are a
# EN | cluster-wide change with their own release cadence, and a script
# EN | that quietly installs operators is not something to run twice by
# EN | accident. If they are missing this says so and prints the commands.
# FR | Met en place Home Assistant OS en VM KubeVirt dans le namespace
# FR | `haos` - une seconde preproduction qui est le meme TYPE de machine
# FR | que la production, Superviseur et add-ons compris.
# FR |
# FR | A lancer sur l hote k3s, depuis un clone :
# FR |     sudo sh kubernetes/haos/apply-haos.sh
# FR |     sudo sh kubernetes/haos/apply-haos.sh --dry-run
# FR |     HAOS_VERSION=18.3 sudo sh kubernetes/haos/apply-haos.sh
# FR |
# FR | Il n installe PAS les operateurs KubeVirt et CDI. Ce sont des
# FR | changements a l echelle du cluster avec leur propre rythme de
# FR | publication, et un script qui installe des operateurs en silence
# FR | n est pas une chose a lancer deux fois par megarde. S ils manquent,
# FR | il le dit et affiche les commandes.
########################################################################
set -e

# EN | Pinned to what production runs, not to "latest". An iso-prod staging
# EN | that silently runs a different OS version is not iso-prod, and the
# EN | one job it has is to be the same machine. Bump this when production
# EN | moves - or pass HAOS_VERSION to test an upgrade BEFORE production
# EN | takes it, which is the other thing this instance is good for.
# FR | Fige sur ce que fait tourner la production, pas sur « latest ». Une
# FR | preproduction iso-prod qui execute en silence une autre version d OS
# FR | n est pas iso-prod, et son seul role est d etre la meme machine.
# FR | Mettre a jour quand la production bouge - ou passer HAOS_VERSION pour
# FR | tester une montee de version AVANT que la production la prenne, ce
# FR | qui est l autre utilite de cette instance.
HAOS_VERSION=${HAOS_VERSION:-18.2}

NS=haos
HERE=$(cd "$(dirname "$0")" && pwd)
DRY=""
[ "$1" = "--dry-run" ] && DRY="--dry-run=client"

say() { echo "[vssp-haos] $*"; }
die() { echo "[ERR] $*" >&2; exit 1; }

command -v kubectl >/dev/null 2>&1 || die "kubectl not found"
kubectl version >/dev/null 2>&1 || die "kubectl cannot reach the cluster (try sudo)"

# ---------------------------------------------------------------------------
# EN | HARDWARE FIRST. Without /dev/kvm the VM still starts - under software
# EN | emulation, at a speed that makes Home Assistant OS look broken rather
# EN | than slow. Saying so here beats discovering it an hour into a boot
# EN | that never finishes.
# FR | LE MATERIEL D ABORD. Sans /dev/kvm la VM demarre quand meme - en
# FR | emulation logicielle, a une vitesse qui fait passer Home Assistant OS
# FR | pour casse plutot que pour lent. Le dire ici vaut mieux que de le
# FR | decouvrir une heure apres un demarrage qui n aboutit jamais.
# ---------------------------------------------------------------------------
[ -e /dev/kvm ] || die "/dev/kvm is missing on this node - KVM is required.
      Check the CPU flags (grep -E ' (vmx|svm) ' /proc/cpuinfo) and, if this
      host is itself a VM, enable nested virtualisation."
say "/dev/kvm present"

for crd in virtualmachines.kubevirt.io datavolumes.cdi.kubevirt.io; do
  kubectl get crd "$crd" >/dev/null 2>&1 || die "$crd not found - the operator is not installed.

      KubeVirt:
        VER=\$(curl -s https://storage.googleapis.com/kubevirt-prow/release/kubevirt/kubevirt/stable.txt)
        kubectl apply -f https://github.com/kubevirt/kubevirt/releases/download/\$VER/kubevirt-operator.yaml
        kubectl apply -f https://github.com/kubevirt/kubevirt/releases/download/\$VER/kubevirt-cr.yaml

      CDI (imports the disk image):
        VER=\$(curl -s https://api.github.com/repos/kubevirt/containerized-data-importer/releases/latest | grep -o '\"tag_name\": *\"[^\"]*' | cut -d'\"' -f4)
        kubectl apply -f https://github.com/kubevirt/containerized-data-importer/releases/download/\$VER/cdi-operator.yaml
        kubectl apply -f https://github.com/kubevirt/containerized-data-importer/releases/download/\$VER/cdi-cr.yaml

      Then re-run this script."
done
say "KubeVirt and CDI operators are present"

# ---------------------------------------------------------------------------
# EN | The disk is imported once and kept. Re-running this script must not
# EN | wipe an instance somebody has onboarded and configured, so an
# EN | existing DataVolume is left strictly alone and only the VM and the
# EN | Service are re-applied.
# FR | Le disque est importe une fois et conserve. Relancer ce script ne doit
# FR | pas effacer une instance que quelqu un a initialisee et configuree,
# FR | donc une DataVolume existante est laissee strictement tranquille et
# FR | seuls la VM et le Service sont reappliques.
# ---------------------------------------------------------------------------
if kubectl get datavolume haos-disk -n "$NS" >/dev/null 2>&1; then
  say "haos-disk already exists - keeping it (delete it by hand to start over)"
  KEEP_DISK=1
else
  say "importing Home Assistant OS $HAOS_VERSION (about 540 MB compressed)"
  KEEP_DISK=0
fi

sed "s/__HAOS_VERSION__/$HAOS_VERSION/g" "$HERE/haos-vm.yaml" \
  | if [ "$KEEP_DISK" = "1" ]; then
      # EN | Drop the DataVolume document, keep the rest.
      # FR | Retirer le document DataVolume, garder le reste.
      awk 'BEGIN{RS="\n---\n"} !/^apiVersion: cdi\.kubevirt\.io/ {if(NR>1)print "---"; print}'
    else
      cat
    fi \
  | kubectl apply $DRY -f -

if [ -n "$DRY" ]; then
  say "dry run only - nothing was changed"
  exit 0
fi

if [ "$KEEP_DISK" = "0" ]; then
  say "waiting for the disk import (several minutes on a first run)"
  kubectl wait --for=condition=Ready datavolume/haos-disk -n "$NS" --timeout=1800s \
    || die "the import did not finish - kubectl describe datavolume haos-disk -n $NS"
fi

say "waiting for the VM to be ready"
kubectl wait --for=condition=Ready vmi/haos -n "$NS" --timeout=600s \
  || say "[warn] the VM is not Ready yet - kubectl get vmi -n $NS"

NODE=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
echo
say "Home Assistant OS is at  http://${NODE:-<node-ip>}:30123"
say "First boot takes several minutes while the appliance unpacks itself."
echo
say "NEXT, BY HAND, IN THAT ORDER:"
say "  1. open the URL and complete onboarding - this creates the first user"
say "  2. Settings > Add-ons > Terminal & SSH: install it, put a public key"
say "     in its authorized_keys option, and set its port to 22222"
say "  3. GitLab > Settings > CI/CD > Variables: HAOS_SSH_KEY (File type),"
say "     the matching private key. deploy:staging-haos appears only once"
say "     that variable exists."
echo
say "console:  kubectl virt console haos -n $NS"
say "logs:     kubectl logs -n $NS virt-launcher-haos-<suffix>"
