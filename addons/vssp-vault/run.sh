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
# EN | Entry point of the Visio Sapiens Vault add-on.
# FR | Point d entree de l add-on Visio Sapiens Vault.
#
# EN | The server configuration is written here at start rather than baked
# EN | into the image, because one value has to come from the add-on's
# EN | configuration form: api_addr. It must be the address the browser
# EN | actually uses, and only the operator knows it.
# FR | La configuration serveur est ecrite ici au demarrage plutot que
# FR | figee dans l image, parce qu une valeur doit venir du formulaire de
# FR | configuration de l add-on : api_addr. Elle doit etre l adresse
# FR | qu utilise reellement le navigateur, et seul l exploitant la
# FR | connait.
########################################################################
set -e

OPTIONS=/data/options.json

read_opt() {
  # EN | `// empty` rather than a default inside jq: it keeps "key absent"
  # EN | and "key set to null" indistinguishable from the caller's point of
  # EN | view, which is what the fallbacks below want.
  # FR | `// empty` plutot qu un defaut dans jq : cela rend « cle absente »
  # FR | et « cle a null » indistinguables du point de vue de l appelant,
  # FR | ce que veulent les replis ci-dessous.
  [ -f "$OPTIONS" ] && jq -r ".$1 // empty" "$OPTIONS" 2>/dev/null || true
}

API_ADDR="$(read_opt api_addr)"
LOG_LEVEL="$(read_opt log_level)"
[ -z "$API_ADDR" ]  && API_ADDR="http://homeassistant.local:8200"
[ -z "$LOG_LEVEL" ] && LOG_LEVEL="info"

# EN | /data is the add-on's own persistent volume: it survives a restart,
# EN | a rebuild and an update of the add-on. Nothing else in the container
# EN | does — writing the store anywhere else would lose the entire safe
# EN | the first time the add-on is updated.
# FR | /data est le volume persistant propre a l add-on : il survit a un
# FR | redemarrage, a une reconstruction et a une mise a jour de l add-on.
# FR | Rien d autre dans le conteneur ne le fait — ecrire le stockage
# FR | ailleurs perdrait le coffre entier a la premiere mise a jour de
# FR | l add-on.
mkdir -p /data/vault

cat > /tmp/vault.hcl <<EOF
storage "file" {
  path = "/data/vault"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
}

api_addr  = "${API_ADDR}"
ui        = true
log_level = "${LOG_LEVEL}"
EOF

echo "[vssp-vault] api_addr = ${API_ADDR}"
echo "[vssp-vault] storage  = /data/vault (persistent)"
# EN | Neither initialisation nor unsealing happens here, and neither ever
# EN | should: both hand out material — five unseal keys and a root token —
# EN | that must be written down off the machine. An add-on that did it for
# EN | you would have to put them in its log. Use the web UI on port 8200.
# FR | Ni l initialisation ni le descellement n ont lieu ici, et ne
# FR | devraient jamais y avoir lieu : les deux delivrent de la matiere —
# FR | cinq cles de descellement et un token root — qui doit etre notee
# FR | hors de la machine. Un add-on qui le ferait a ta place devrait les
# FR | ecrire dans son journal. Utiliser l interface web sur le port 8200.
echo "[vssp-vault] not initialised? open http://<instance>:8200/ui"

exec vault server -config=/tmp/vault.hcl
