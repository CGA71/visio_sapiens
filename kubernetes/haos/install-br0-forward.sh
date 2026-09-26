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
# EN | Makes the Home Assistant OS VM reachable on IPv4 for good.
# FR | Rend la VM Home Assistant OS joignable en IPv4 pour de bon.
#
# EN | RUN IT ONCE, AS ROOT, ON THE K3S HOST:
# EN |   sudo sh kubernetes/haos/install-br0-forward.sh
# FR | A LANCER UNE FOIS, EN ROOT, SUR L HOTE K3S :
# FR |   sudo sh kubernetes/haos/install-br0-forward.sh
#
# EN | WHAT IT SOLVES. iptables rules live in kernel memory and nowhere
# EN | else: nothing on this host saves or replays them, so a reboot wipes
# EN | them. And k3s rebuilds the FORWARD chain every time it starts, with
# EN | the policy back to DROP. Both happened: the rules were added by hand
# EN | on 25 September, the host rebooted on the 26th at 23:34, and the VM
# EN | went unreachable on IPv4 while still answering perfectly on IPv6 -
# EN | because this cluster is IPv4-only and k3s never programs ip6tables.
# FR | CE QUE CECI RESOUT. Les regles iptables vivent dans la memoire du
# FR | noyau et nulle part ailleurs : rien sur cet hote ne les sauvegarde ni
# FR | ne les rejoue, un redemarrage les efface donc. Et k3s reconstruit la
# FR | chaine FORWARD a chaque demarrage, politique de nouveau a DROP. Les
# FR | deux se sont produits : regles posees a la main le 25 septembre, hote
# FR | redemarre le 26 a 23:34, et la VM injoignable en IPv4 alors qu elle
# FR | repondait parfaitement en IPv6 - parce que ce cluster est en IPv4 et
# FR | que k3s ne programme jamais ip6tables.
#
# EN | WHY TWO HOOKS AND NOT ONE. A NetworkManager dispatcher script runs
# EN | when br0 comes up, which covers a reboot. It does NOT cover k3s being
# EN | restarted afterwards - systemctl restart k3s, an upgrade, a crash -
# EN | because br0 never moves and no interface event fires. So the same
# EN | script is also hung off k3s itself, as ExecStartPost, and runs again
# EN | every single time k3s starts. Both callers are idempotent: the script
# EN | tests each rule with -C before inserting it.
# FR | POURQUOI DEUX ACCROCHES ET PAS UNE. Un script dispatcher de
# FR | NetworkManager s execute quand br0 monte, ce qui couvre un
# FR | redemarrage. Il ne couvre PAS un k3s redemarre ensuite - systemctl
# FR | restart k3s, une mise a jour, un plantage - car br0 ne bouge pas et
# FR | aucun evenement d interface ne part. Le meme script est donc aussi
# FR | accroche a k3s lui-meme, en ExecStartPost, et repasse a chaque
# FR | demarrage de k3s. Les deux appelants sont idempotents : le script
# FR | teste chaque regle avec -C avant de l inserer.
########################################################################
set -e

HERE=$(cd "$(dirname "$0")" && pwd)
SRC="$HERE/50-br0-forward"
SBIN=/usr/local/sbin/vssp-br0-forward
DISPATCH=/etc/NetworkManager/dispatcher.d/50-br0-forward
DROPIN_DIR=/etc/systemd/system/k3s.service.d
DROPIN="$DROPIN_DIR/10-vssp-br0-forward.conf"

[ "$(id -u)" = "0" ] || { echo "[ERR] run me as root (sudo sh $0)"; exit 1; }
[ -f "$SRC" ] || { echo "[ERR] $SRC not found - update the checkout first"; exit 1; }

echo "[i] installing $SBIN"
install -m 755 "$SRC" "$SBIN"

echo "[i] hooking NetworkManager ($DISPATCH)"
install -d -m 755 "$(dirname "$DISPATCH")"
install -m 755 "$SRC" "$DISPATCH"

# EN | The drop-in leaves the k3s unit file alone, so a k3s upgrade that
# EN | replaces its own unit cannot silently undo this.
# FR | Le drop-in laisse le fichier d unite de k3s intact : une mise a jour
# FR | de k3s qui remplace son unite ne peut donc pas defaire ceci en
# FR | silence.
if systemctl list-unit-files k3s.service >/dev/null 2>&1; then
  echo "[i] hooking k3s ($DROPIN)"
  install -d -m 755 "$DROPIN_DIR"
  cat > "$DROPIN" <<EOF
[Service]
ExecStartPost=$SBIN
EOF
  systemctl daemon-reload
else
  echo "[warn] no k3s.service here - only the NetworkManager hook is installed"
fi

echo "[i] applying now"
"$SBIN"

echo "[i] rules currently in the FORWARD chain:"
iptables -S FORWARD | grep br0 || echo "       none - something is wrong"

cat <<'EOF'

[OK] Installed. The rules are applied now, and they come back:
       - when br0 comes up          (NetworkManager dispatcher)
       - every time k3s starts      (systemd drop-in)

     Check from any machine on the network:
       curl -I http://192.168.1.200:8123
EOF
