#!/usr/bin/env python3
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


# ============================================================================
# Visio Sapiens - vssp_mcp/ha.py
#
# EN | THE ONE PLACE THIS SERVER TOUCHES HOME ASSISTANT. Two transports,
# EN | because Home Assistant genuinely has two: the REST API answers for
# EN | states and /api/config, and the registries - areas, devices,
# EN | entities - exist only on the websocket. Every tool in server.py goes
# EN | through the functions below and nowhere else, so there is a single
# EN | place to look when a credential or a URL is wrong.
# FR | LE SEUL ENDROIT OU CE SERVEUR TOUCHE HOME ASSISTANT. Deux
# FR | transports, parce que Home Assistant en a reellement deux : l'API
# FR | REST repond pour les etats et /api/config, et les registres - zones,
# FR | appareils, entites - n'existent que sur le websocket. Chaque outil
# FR | de server.py passe par les fonctions ci-dessous et nulle part
# FR | ailleurs, donc il y a un seul endroit ou regarder quand un
# FR | identifiant ou une URL est faux.
# ============================================================================
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# EN | ONE WEBSOCKET CLIENT, NOT TWO. vssp/vssp_ws.py exists precisely
# EN | because a second hand-rolled copy of RFC 6455 drifts in the worst
# EN | possible way: quietly, and only on the instance nobody is looking
# EN | at. That argument does not weaken because the second caller happens
# EN | to sit on a desktop instead of inside /config - so this server
# EN | imports that file rather than carrying its own frames.
# EN | vssp/ has no __init__.py: it is a folder of standalone scripts
# EN | copied flat into /config/vssp, not a package. A path insert is what
# EN | reaches it, and it costs nothing here because this server always
# EN | runs from a checkout of this repository.
# FR | UN SEUL CLIENT WEBSOCKET, PAS DEUX. vssp/vssp_ws.py existe justement
# FR | parce qu'une seconde copie ecrite a la main de la RFC 6455 diverge
# FR | de la pire maniere : en silence, et seulement sur l'instance que
# FR | personne ne regarde. Cet argument ne faiblit pas parce que le second
# FR | appelant se trouve sur un poste de travail plutot que dans /config -
# FR | donc ce serveur importe ce fichier au lieu de porter ses propres
# FR | trames.
# FR | vssp/ n'a pas d'__init__.py : c'est un dossier de scripts autonomes
# FR | copies a plat dans /config/vssp, pas un paquet. Un ajout de chemin
# FR | est ce qui l'atteint, et cela ne coute rien ici puisque ce serveur
# FR | s'execute toujours depuis un clone de ce depot.
REPO_ROOT = Path(__file__).resolve().parents[2]
_VSSP_DIR = REPO_ROOT / "vssp"
if str(_VSSP_DIR) not in sys.path:
    sys.path.insert(0, str(_VSSP_DIR))

import vssp_ws  # noqa: E402


class HAError(RuntimeError):
    """EN | Anything the caller could plausibly fix: no token, wrong URL,
    EN | instance down, command refused. Raised with a sentence rather than
    EN | a traceback, because an MCP client shows it to a person.
    FR | Tout ce que l'appelant peut raisonnablement corriger : pas de
    FR | jeton, mauvaise URL, instance arretee, commande refusee. Levee
    FR | avec une phrase plutot qu'une trace, parce qu'un client MCP la
    FR | montre a une personne."""


# -- EN | Where, and with what / FR | Ou, et avec quoi -------------------
def base_url() -> str:
    """EN | The instance to talk to. Staging and production are different
    EN | machines; which one this server drives is the client's choice, set
    EN | once in its config, never guessed here.
    FR | L'instance a qui parler. La preproduction et la production sont
    FR | des machines differentes ; laquelle ce serveur pilote est le choix
    FR | du client, fixe une fois dans sa configuration, jamais devine
    FR | ici."""
    return os.environ.get("VSSP_HA_URL", "http://localhost:8123").rstrip("/")


def token() -> str:
    """EN | --token > $HA_TOKEN > token file, the order every script in
    EN | this project follows, reused verbatim from vssp_ws so that a
    EN | half-filled helper reading "unknown" is rejected here exactly as
    EN | it is on an instance.
    FR | --token > $HA_TOKEN > fichier de jeton, l'ordre suivi par chaque
    FR | script de ce projet, repris tel quel de vssp_ws pour qu'un helper
    FR | a moitie rempli valant "unknown" soit rejete ici exactement comme
    FR | il l'est sur une instance."""
    tok = vssp_ws.resolve_token(
        None,
        token_file=os.environ.get("VSSP_HA_TOKEN_FILE", "/config/vssp/.ha_token"),
    )
    if not tok:
        raise HAError(
            "No Home Assistant token. Set HA_TOKEN in this server's env "
            "block, or point VSSP_HA_TOKEN_FILE at a file holding one. "
            "A token is minted from your Home Assistant profile page, "
            "under 'Long-lived access tokens' - nothing else can mint one."
        )
    return tok


# -- EN | REST: states and config / FR | REST : etats et configuration ---
def rest(path: str, timeout: float = 15.0) -> Any:
    url = f"{base_url()}{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token()}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise HAError(
                f"{url} refused the token (HTTP 401). It is expired, "
                "revoked, or belongs to the other instance."
            ) from exc
        raise HAError(f"{url} -> HTTP {exc.code} {exc.reason}") from exc
    except OSError as exc:
        raise HAError(f"{url} unreachable: {exc}") from exc
    return json.loads(body) if body.strip() else None


def states() -> list[dict]:
    """EN | Every entity and its current state, in one call.
    FR | Chaque entite et son etat courant, en un seul appel."""
    return rest("/api/states") or []


# -- EN | Websocket: the registries / FR | Websocket : les registres -----
def ws_many(payloads: list[dict], timeout: float = 20.0) -> list:
    """EN | Several commands over ONE connection. The registries are almost
    EN | always wanted together - a room's entities are an area joined to
    EN | devices joined to entities - and three separate connections would
    EN | mean three handshakes and three authentications for one answer.
    FR | Plusieurs commandes sur UNE connexion. Les registres sont presque
    FR | toujours voulus ensemble - les entites d'une piece sont une zone
    FR | jointe aux appareils joints aux entites - et trois connexions
    FR | separees signifieraient trois poignees de main et trois
    FR | authentifications pour une seule reponse."""
    try:
        conn = vssp_ws.connected(base_url(), token(), timeout=timeout)
    except vssp_ws.WSError as exc:
        raise HAError(f"{base_url()} refused the websocket: {exc}") from exc
    except OSError as exc:
        raise HAError(f"{base_url()} unreachable on the websocket: {exc}") from exc
    try:
        out = []
        for payload in payloads:
            try:
                out.append(conn.command(payload))
            except vssp_ws.WSError as exc:
                raise HAError(f"{payload.get('type')} -> {exc}") from exc
        return out
    finally:
        conn.close()


def ws(payload: dict, timeout: float = 20.0) -> Any:
    return ws_many([payload], timeout=timeout)[0]


def registries() -> tuple[list, list, list]:
    """EN | areas, devices, entities - the three lists the dashboard
    EN | generator is built on, fetched together.
    FR | zones, appareils, entites - les trois listes sur lesquelles le
    FR | generateur de dashboards est construit, recuperees ensemble."""
    areas, devices, entities = ws_many([
        {"type": "config/area_registry/list"},
        {"type": "config/device_registry/list"},
        {"type": "config/entity_registry/list"},
    ])
    return areas or [], devices or [], entities or []
