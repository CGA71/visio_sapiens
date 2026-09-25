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
# EN | Entry point of the Visio Sapiens MCP add-on.
# FR | Point d entree de l add-on Visio Sapiens MCP.
#
# EN | Its whole job is to find the code and hand over. The server itself
# EN | lives in /config/vssp_mcp, deployed by the pipeline, so this script
# EN | changes only when the way in changes - not when the server does.
# FR | Son seul travail est de trouver le code et de passer la main. Le
# FR | serveur lui-meme vit dans /config/vssp_mcp, deploye par le pipeline,
# FR | donc ce script ne change que si la voie d acces change - pas quand
# FR | le serveur change.
########################################################################
set -e

OPTIONS=/data/options.json

read_opt() {
  [ -f "$OPTIONS" ] && jq -r ".$1 // empty" "$OPTIONS" 2>/dev/null || true
}

# EN | WHERE THE CONFIGURATION DIRECTORY LANDS DEPENDS ON THE SUPERVISOR'S
# EN | AGE. `homeassistant_config` mounts at /homeassistant on current
# EN | versions; the older `config` mapping used /config, and plenty of
# EN | instances still present that. Probing both costs one test and turns
# EN | a silent ImportError at start into a working add-on.
# FR | OU ATTERRIT LE REPERTOIRE DE CONFIGURATION DEPEND DE L AGE DU
# FR | SUPERVISEUR. `homeassistant_config` monte sur /homeassistant sur les
# FR | versions actuelles ; l ancien mappage `config` utilisait /config, et
# FR | beaucoup d instances presentent encore celui-la. Sonder les deux
# FR | coute un test et transforme une ImportError silencieuse au demarrage
# FR | en add-on qui fonctionne.
CFG=""
for cand in /homeassistant /config; do
  if [ -d "$cand/vssp_mcp" ]; then
    CFG="$cand"
    break
  fi
done

if [ -z "$CFG" ]; then
  echo "[vssp-mcp] FATAL: vssp_mcp/ not found in /homeassistant or /config."
  echo "[vssp-mcp] It is deployed there by the pipeline, alongside vssp/."
  echo "[vssp-mcp] Deploy Visio Sapiens to this instance, then restart this"
  echo "[vssp-mcp] add-on. Nothing else is wrong."
  exit 1
fi

API_TOKEN="$(read_opt api_token)"
HA_TOKEN_OPT="$(read_opt ha_token)"
LOG_LEVEL="$(read_opt log_level)"
[ -z "$LOG_LEVEL" ] && LOG_LEVEL="info"

export PYTHONPATH="$CFG"
export VSSP_DIR="$CFG/vssp"
export VSSP_MCP_HOST="0.0.0.0"
export VSSP_MCP_PORT="8099"
export VSSP_MCP_TOKEN="$API_TOKEN"

# EN | Only exported when the operator actually set one. An empty HA_TOKEN
# EN | in the environment is not the same as no HA_TOKEN: resolve_token
# EN | treats the placeholders as absent, but leaving it unset keeps the
# EN | route list honest about what is available.
# FR | Exporte seulement si l exploitant en a reellement mis un. Un HA_TOKEN
# FR | vide dans l environnement n est pas la meme chose qu aucun HA_TOKEN :
# FR | resolve_token traite les sentinelles comme absentes, mais le laisser
# FR | non defini garde la liste des routes honnete sur ce qui existe.
if [ -n "$HA_TOKEN_OPT" ]; then
  export HA_TOKEN="$HA_TOKEN_OPT"
  echo "[vssp-mcp] a long-lived token is configured as a fallback route"
fi

echo "[vssp-mcp] config directory: $CFG"
echo "[vssp-mcp] package:          $CFG/vssp_mcp"
echo "[vssp-mcp] shared client:    $VSSP_DIR/vssp_ws.py"

exec python -m vssp_mcp.server
