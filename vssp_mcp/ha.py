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
# EN | entities - exist only on the websocket.
# EN |
# EN | TWO WAYS IN, TRIED IN ORDER, NOT ASSUMED. This server runs on the
# EN | instance itself, and where it runs decides how it authenticates:
# EN |   - as a Home Assistant OS ADD-ON, the Supervisor is right there and
# EN |     SUPERVISOR_TOKEN should be enough, with no long-lived token for
# EN |     anyone to create, paste or revoke;
# EN |   - as a container beside a k3s pod, there is no Supervisor at all
# EN |     and a long-lived token is the only option.
# EN | The Supervisor route is TRIED, never assumed. This project has
# EN | already been wrong about it twice: v1.0.8 sent SUPERVISOR_TOKEN in
# EN | the websocket auth message, v1.0.9 added it as an HTTP header, and
# EN | both failed with "Invalid access" because /core/websocket
# EN | authenticates ADD-ONS (sys_apps.from_token()) and the caller then
# EN | was vssp_dependencies.py, running inside Core's own container, which
# EN | is not an add-on. An add-on IS one, so the route should work here -
# EN | but "should" is exactly the word that was wrong twice, and it cannot
# EN | be tested from a workstation. So each route is probed, the first one
# EN | that answers wins, and the add-on keeps a token option as a fallback
# EN | that costs nothing if the proxy behaves.
# FR | LE SEUL ENDROIT OU CE SERVEUR TOUCHE HOME ASSISTANT. Deux
# FR | transports, parce que Home Assistant en a reellement deux : l'API
# FR | REST repond pour les etats et /api/config, et les registres - zones,
# FR | appareils, entites - n'existent que sur le websocket.
# FR |
# FR | DEUX VOIES D'ENTREE, ESSAYEES, PAS SUPPOSEES. Ce serveur tourne sur
# FR | l'instance elle-meme, et l'endroit ou il tourne decide de son
# FR | authentification :
# FR |   - en ADD-ON Home Assistant OS, le Superviseur est juste la et
# FR |     SUPERVISOR_TOKEN devrait suffire, sans aucun jeton longue duree
# FR |     a creer, coller ou revoquer ;
# FR |   - en conteneur a cote d'un pod k3s, il n'y a pas de Superviseur du
# FR |     tout et un jeton longue duree est la seule option.
# FR | La route Superviseur est ESSAYEE, jamais supposee. Ce projet s'est
# FR | deja trompe deux fois dessus : v1.0.8 envoyait SUPERVISOR_TOKEN dans
# FR | le message auth du websocket, v1.0.9 l'ajoutait en en-tete HTTP, et
# FR | les deux ont echoue sur « Invalid access » parce que /core/websocket
# FR | authentifie les ADD-ONS (sys_apps.from_token()) et que l'appelant
# FR | etait alors vssp_dependencies.py, dans le conteneur de Core, qui
# FR | n'en est pas un. Un add-on en est un, la route devrait donc marcher
# FR | ici - mais « devrait » est precisement le mot qui s'est trompe deux
# FR | fois, et cela ne peut pas se tester depuis un poste de travail. Donc
# FR | chaque route est sondee, la premiere qui repond gagne, et l'add-on
# FR | garde une option jeton en secours, qui ne coute rien si le proxy se
# FR | comporte bien.
# ============================================================================
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# EN | ONE WEBSOCKET CLIENT, NOT TWO. vssp/vssp_ws.py exists precisely
# EN | because a second hand-rolled copy of RFC 6455 drifts in the worst
# EN | possible way: quietly, and only on the instance nobody is looking
# EN | at. So this imports that file instead of carrying its own frames -
# EN | and because both run on the instance now, it is literally the same
# EN | file the rest of the tooling uses, not a copy of it.
# EN | Where it sits depends on who is asking: /config/vssp on a deployed
# EN | instance, /homeassistant/vssp when the Supervisor maps the config
# EN | directory under its newer name, or ../vssp from a git checkout. All
# EN | three are probed rather than picked, because getting this wrong
# EN | produces an ImportError at start with no hint of which path was
# EN | expected.
# FR | UN SEUL CLIENT WEBSOCKET, PAS DEUX. vssp/vssp_ws.py existe justement
# FR | parce qu'une seconde copie ecrite a la main de la RFC 6455 diverge
# FR | de la pire maniere : en silence, et seulement sur l'instance que
# FR | personne ne regarde. Ceci importe donc ce fichier au lieu de porter
# FR | ses propres trames - et comme les deux tournent desormais sur
# FR | l'instance, c'est litteralement le meme fichier que le reste de
# FR | l'outillage, pas une copie.
# FR | Son emplacement depend de qui demande : /config/vssp sur une
# FR | instance deployee, /homeassistant/vssp quand le Superviseur mappe le
# FR | repertoire de configuration sous son nom plus recent, ou ../vssp
# FR | depuis un clone git. Les trois sont sondes plutot que choisis, parce
# FR | que se tromper ici produit une ImportError au demarrage sans
# FR | indiquer quel chemin etait attendu.
_CANDIDATES = [
    os.environ.get("VSSP_DIR", "").strip(),
    "/config/vssp",
    "/homeassistant/vssp",
    str(Path(__file__).resolve().parent.parent / "vssp"),
]


def _locate_vssp() -> str:
    for cand in _CANDIDATES:
        if cand and (Path(cand) / "vssp_ws.py").is_file():
            return cand
    raise ImportError(
        "vssp_ws.py not found. Looked in: "
        + ", ".join(c for c in _CANDIDATES if c)
        + ". On an instance it is deployed to /config/vssp by the pipeline; "
        "set VSSP_DIR to override."
    )


_VSSP_DIR = _locate_vssp()
if _VSSP_DIR not in sys.path:
    sys.path.insert(0, _VSSP_DIR)

import vssp_ws  # noqa: E402


class HAError(RuntimeError):
    """EN | Anything the caller could plausibly fix: no credential, wrong
    EN | URL, instance down, command refused. Raised with a sentence rather
    EN | than a traceback, because an MCP client shows it to a person.
    FR | Tout ce que l'appelant peut raisonnablement corriger : pas
    FR | d'identifiant, mauvaise URL, instance arretee, commande refusee.
    FR | Levee avec une phrase plutot qu'une trace, parce qu'un client MCP
    FR | la montre a une personne."""


# -- EN | The ways in / FR | Les voies d'entree ---------------------------
@dataclass(frozen=True)
class Route:
    label: str
    rest_base: str      # EN | "/api/..." is appended / FR | on y ajoute "/api/..."
    ws_url: str
    ws_path: str
    bearer: str | None  # EN | HTTP header on the upgrade / FR | en-tete HTTP
    ws_token: str       # EN | token in the auth message / FR | jeton du message auth


def supervisor_token() -> str | None:
    tok = os.environ.get("SUPERVISOR_TOKEN", "").strip()
    return tok or None


def long_lived_token() -> str | None:
    return vssp_ws.resolve_token(
        None,
        token_file=os.environ.get("VSSP_HA_TOKEN_FILE", "/config/vssp/.ha_token"),
    )


def direct_url() -> str:
    """EN | Where Home Assistant answers when we are beside it rather than
    EN | inside the appliance. On k3s that is the pod's own service.
    FR | Ou repond Home Assistant quand on est a cote de lui plutot que
    FR | dans l'appareil. Sur k3s, c'est le service du pod lui-meme."""
    return os.environ.get("VSSP_HA_URL", "http://localhost:8123").rstrip("/")


def routes() -> list[Route]:
    out: list[Route] = []
    sup = supervisor_token()
    if sup:
        # EN | The Supervisor's proxy for add-ons reaching Core. Its own
        # EN | gate is the HTTP Authorization header; Core's auth_required
        # EN | exchange still happens behind it, so the same token goes in
        # EN | both places and whichever one the proxy actually reads, the
        # EN | handshake completes.
        # FR | Le proxy du Superviseur pour les add-ons qui atteignent
        # FR | Core. Sa propre porte est l'en-tete HTTP Authorization ;
        # FR | l'echange auth_required de Core a toujours lieu derriere,
        # FR | donc le meme jeton va aux deux endroits et quelle que soit
        # FR | celle que le proxy lit vraiment, la poignee de main aboutit.
        out.append(Route(
            label="supervisor proxy (add-on)",
            rest_base="http://supervisor/core",
            ws_url="http://supervisor",
            ws_path="/core/websocket",
            bearer=sup,
            ws_token=sup,
        ))
    tok = long_lived_token()
    if tok:
        out.append(Route(
            label=f"long-lived token -> {direct_url()}",
            rest_base=direct_url(),
            ws_url=direct_url(),
            ws_path="/api/websocket",
            bearer=None,
            ws_token=tok,
        ))
    if not out:
        raise HAError(
            "No way to authenticate to Home Assistant. As a Home Assistant "
            "OS add-on, SUPERVISOR_TOKEN is provided automatically and "
            "`homeassistant_api: true` must be set in the add-on config. "
            "Anywhere else, supply a long-lived token: HA_TOKEN in the "
            "environment, or a file named by VSSP_HA_TOKEN_FILE."
        )
    return out


_active: Route | None = None


def _rest_once(route: Route, path: str, timeout: float) -> Any:
    url = f"{route.rest_base}{path}"
    headers = {"Content-Type": "application/json"}
    token = route.bearer or route.ws_token
    headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise HAError(f"{url} refused the credential (HTTP {exc.code})") from exc
        raise HAError(f"{url} -> HTTP {exc.code} {exc.reason}") from exc
    except OSError as exc:
        raise HAError(f"{url} unreachable: {exc}") from exc
    return json.loads(body) if body.strip() else None


def active_route() -> Route:
    """EN | The first route that actually answers, remembered. Probing
    EN | costs one GET at start-up and removes a whole class of wrong
    EN | assumption about the Supervisor's proxy.
    FR | La premiere route qui repond vraiment, memorisee. Le sondage coute
    FR | un GET au demarrage et supprime toute une classe de suppositions
    FR | fausses sur le proxy du Superviseur."""
    global _active
    if _active is not None:
        return _active
    failures = []
    for route in routes():
        try:
            _rest_once(route, "/api/config", 10.0)
        except HAError as exc:
            failures.append(f"  - {route.label}: {exc}")
            continue
        _active = route
        return route
    raise HAError("No usable route to Home Assistant:\n" + "\n".join(failures))


def route_label() -> str:
    return active_route().label


# -- EN | REST: states and config / FR | REST : etats et configuration ----
def rest(path: str, timeout: float = 15.0) -> Any:
    return _rest_once(active_route(), path, timeout)


def states() -> list[dict]:
    """EN | Every entity and its current state, in one call.
    FR | Chaque entite et son etat courant, en un seul appel."""
    return rest("/api/states") or []


# -- EN | Websocket: the registries / FR | Websocket : les registres ------
def ws_many(payloads: list[dict], timeout: float = 20.0) -> list:
    """EN | Several commands over ONE connection. The registries are almost
    EN | always wanted together - a room's entities are an area joined to
    EN | devices joined to entities - and separate connections would mean a
    EN | handshake and an authentication each, for one answer.
    FR | Plusieurs commandes sur UNE connexion. Les registres sont presque
    FR | toujours voulus ensemble - les entites d'une piece sont une zone
    FR | jointe aux appareils joints aux entites - et des connexions
    FR | separees signifieraient une poignee de main et une
    FR | authentification chacune, pour une seule reponse."""
    route = active_route()
    try:
        conn = vssp_ws.connected(route.ws_url, route.ws_token, timeout=timeout,
                                 path=route.ws_path, bearer=route.bearer)
    except vssp_ws.WSError as exc:
        raise HAError(
            f"{route.label}: the websocket refused the credential ({exc}). "
            f"REST works on this route, so this is the websocket gate alone. "
            f"If this is the Supervisor proxy, set a long-lived token in the "
            f"add-on options and it will be used instead."
        ) from exc
    except OSError as exc:
        raise HAError(f"{route.label}: websocket unreachable: {exc}") from exc
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
    """EN | areas, devices, entities - fetched together.
    FR | zones, appareils, entites - recuperees ensemble."""
    areas, devices, entities = ws_many([
        {"type": "config/area_registry/list"},
        {"type": "config/device_registry/list"},
        {"type": "config/entity_registry/list"},
    ])
    return areas or [], devices or [], entities or []
