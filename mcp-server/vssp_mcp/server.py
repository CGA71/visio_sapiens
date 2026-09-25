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
# Visio Sapiens - vssp_mcp/server.py
#
# EN | WHAT THIS IS, AND WHAT IT IS NOT. The community Home Assistant MCP
# EN | servers expose Lovelace CRUD, and they only work on STORAGE-mode
# EN | dashboards - the ones a person clicks together in the UI. Visio
# EN | Sapiens dashboards are YAML-mode, rendered by
# EN | vssp/generate_dashboards.py from templates_j2 against the house
# EN | model. A generic server writing storage-mode cards cannot touch
# EN | them, and a card it wrote would be erased by the next regeneration.
# EN | So this server does not reimplement the generator. It reads the
# EN | things the generator reasons about - rooms, devices, dashboard
# EN | presence, dependency and update state - and hands them to whatever
# EN | assistant is on the other end, in the vocabulary this project
# EN | already uses.
# EN |
# EN | READ ONLY, ON PURPOSE, FOR NOW. Every tool below answers a question;
# EN | none of them changes anything. The acting surface already exists and
# EN | is deliberate: the ADMIN console's own buttons, backed by
# EN | script.vssp_*, each with its confirmation and its status sensor.
# EN | Wiring those in is a second step, taken once the reading half has
# EN | been exercised against a live instance - not before.
# FR | CE QUE C'EST, ET CE QUE CE N'EST PAS. Les serveurs MCP
# FR | communautaires pour Home Assistant exposent du CRUD Lovelace, et ne
# FR | fonctionnent que sur les dashboards en mode STORAGE - ceux qu'une
# FR | personne assemble en cliquant dans l'interface. Les dashboards Visio
# FR | Sapiens sont en mode YAML, rendus par vssp/generate_dashboards.py
# FR | depuis templates_j2 contre le modele de la maison. Un serveur
# FR | generique qui ecrit des cartes en mode storage ne peut pas les
# FR | toucher, et une carte qu'il aurait ecrite serait effacee a la
# FR | regeneration suivante.
# FR | Ce serveur ne reimplemente donc pas le generateur. Il lit ce sur
# FR | quoi le generateur raisonne - pieces, appareils, presence des
# FR | dashboards, etat des dependances et des mises a jour - et le remet a
# FR | l'assistant qui se trouve a l'autre bout, dans le vocabulaire que ce
# FR | projet emploie deja.
# FR |
# FR | LECTURE SEULE, VOLONTAIREMENT, POUR L'INSTANT. Chaque outil
# FR | ci-dessous repond a une question ; aucun ne change quoi que ce soit.
# FR | La surface d'action existe deja et elle est voulue : les boutons de
# FR | la console ADMIN, adosses a script.vssp_*, chacun avec sa
# FR | confirmation et son capteur d'etat. Les brancher est une seconde
# FR | etape, prise une fois la moitie lecture eprouvee contre une instance
# FR | vivante - pas avant.
# ============================================================================
from __future__ import annotations

from typing import Any

from mcp.server import MCPServer

from . import ha

mcp = MCPServer(
    name="visio-sapiens",
    instructions=(
        "Read-only access to a Visio Sapiens Home Assistant instance.\n\n"
        "Visio Sapiens dashboards are YAML-mode and are RENDERED from "
        "Jinja templates by vssp/generate_dashboards.py against the house "
        "model, which is dashboards/model/house.yaml ON THE INSTANCE - not "
        "Home Assistant's area registry, and not the empty copy of that "
        "file in the git checkout. "
        "Never propose editing a Visio Sapiens dashboard through "
        "Lovelace's storage API: the next regeneration erases it. To "
        "change what a dashboard shows, change the house model or the "
        "template, then regenerate from the ADMIN console.\n\n"
        "Call vssp_instance first. It reports whether the target is a "
        "Home Assistant OS appliance or a k3s pod, and those two have "
        "different update surfaces - an OS appliance has no k3s layer, so "
        "k3s versions are not a thing to offer it."
    ),
)


# -- EN | Small shared helpers / FR | Petites aides partagees ------------
def _by_id(state_list: list[dict]) -> dict[str, dict]:
    return {s.get("entity_id", ""): s for s in state_list}


def _shape(state: dict | None, entity_id: str) -> dict:
    """EN | One entity, reported the same way everywhere - including when
    EN | it does not exist. A missing vssp_* entity is not an error, it is
    EN | information: that package is not deployed on this instance.
    FR | Une entite, rapportee de la meme maniere partout - y compris
    FR | quand elle n'existe pas. Une entite vssp_* absente n'est pas une
    FR | erreur, c'est une information : ce paquet n'est pas deploye sur
    FR | cette instance."""
    if state is None:
        return {"entity_id": entity_id, "present": False,
                "note": "not on this instance"}
    attrs = dict(state.get("attributes") or {})
    return {
        "entity_id": entity_id,
        "present": True,
        "state": state.get("state"),
        "name": attrs.pop("friendly_name", None),
        "last_changed": state.get("last_changed"),
        "attributes": attrs,
    }


# -- EN | The tools / FR | Les outils ------------------------------------
@mcp.tool()
def vssp_instance() -> dict:
    """Identify the Home Assistant instance this server is pointed at.

    Reports the Core version, the installation type, and the Visio Sapiens
    version and interface language deployed on it. Call this first: an OS
    appliance and a k3s pod do not have the same update surface, and
    offering one the other's layers is wasted advice.
    """
    config = ha.rest("/api/config") or {}
    components = set(config.get("components") or [])
    # EN | `hassio` in the component list is how Core itself knows it is
    # EN | running under a Supervisor. It is the same fact vssp_infra_
    # EN | updates.py reads from SUPERVISOR_TOKEN, seen from the outside.
    # FR | `hassio` dans la liste des composants est la maniere dont Core
    # FR | sait lui-meme qu'il tourne sous un Superviseur. C'est le meme
    # FR | fait que vssp_infra_updates.py lit dans SUPERVISOR_TOKEN, vu de
    # FR | l'exterieur.
    supervised = "hassio" in components
    by_id = _by_id(ha.states())
    return {
        "url": ha.base_url(),
        "location": config.get("location_name"),
        "core_version": config.get("version"),
        "installation": "Home Assistant OS / Supervised" if supervised else "Core (container / k3s pod)",
        "has_supervisor": supervised,
        "infrastructure_layers_apply": not supervised,
        "vssp_locale": (by_id.get("sensor.vssp_deployed_locale") or {}).get("state"),
        "vssp_entities": sum(1 for e in by_id if "vssp" in e),
    }


@mcp.tool()
def vssp_rooms() -> dict:
    """List the Home Assistant areas this instance knows, with how many
    entities each one holds, alongside what the Visio Sapiens model has
    actually kept.

    These two are not the same thing and the difference matters. The
    dashboard generator does NOT read the area registry: its input is
    `dashboards/model/house.yaml` ON THE INSTANCE, whose `rooms:` key is
    written by the ADMIN console's room form and topped up by the
    discovery wizard, which is the one thing that reads areas (through the
    template API, `{{ areas() }}`). The copy of house.yaml in the git
    checkout is empty by design.

    So an empty `areas` list here does not mean the house has no rooms,
    and a populated one does not mean the dashboards use them. Read
    `model` in the same answer before concluding anything.
    """
    areas, devices, entities = ha.registries()
    device_area = {d.get("id"): d.get("area_id") for d in devices}
    counts: dict[str, int] = {}
    for ent in entities:
        # EN | An entity's own area_id wins; otherwise it inherits its
        # EN | device's. That is Home Assistant's own rule, and a room
        # EN | counted any other way would not match what the UI shows.
        # FR | L'area_id propre a l'entite l'emporte ; sinon elle herite
        # FR | de celui de son appareil. C'est la regle de Home Assistant
        # FR | lui-meme, et une piece comptee autrement ne correspondrait
        # FR | pas a ce que l'interface affiche.
        area_id = ent.get("area_id") or device_area.get(ent.get("device_id"))
        if area_id:
            counts[area_id] = counts.get(area_id, 0) + 1
    rooms = sorted(
        ({"area_id": a.get("area_id"),
          "name": a.get("name"),
          "floor_id": a.get("floor_id"),
          "icon": a.get("icon"),
          "entities": counts.get(a.get("area_id"), 0)} for a in areas),
        key=lambda r: (r["name"] or "").lower(),
    )
    # EN | The model's own counters, from the instance. Without them an
    # EN | empty `areas` list is unreadable: it looks exactly like a broken
    # EN | tool. Both instances of this project currently report zero areas
    # EN | and zero active rooms - that is a house whose room form has not
    # EN | been filled, not a failed call, and only these two numbers side
    # EN | by side say so.
    # FR | Les compteurs du modele lui-meme, depuis l'instance. Sans eux
    # FR | une liste `areas` vide est illisible : elle ressemble trait pour
    # FR | trait a un outil casse. Les deux instances de ce projet
    # FR | rapportent aujourd'hui zero zone et zero piece active - c'est
    # FR | une maison dont le formulaire de pieces n'a pas ete rempli, pas
    # FR | un appel echoue, et seuls ces deux nombres cote a cote le
    # FR | disent.
    by_id = _by_id(ha.states())
    return {
        "areas": rooms,
        "area_count": len(rooms),
        "assigned_entities": sum(counts.values()),
        "unassigned_entities": len(entities) - sum(counts.values()),
        "model": {
            "active_rooms": _shape(by_id.get("sensor.vssp_pieces_actives"),
                                   "sensor.vssp_pieces_actives"),
            "devices": _shape(by_id.get("sensor.vssp_total_appareils"),
                              "sensor.vssp_total_appareils"),
        },
        "note": (
            "areas = Home Assistant's registry. model.active_rooms = what "
            "house.yaml on the instance actually holds, which is what the "
            "dashboards are rendered from. Zero active rooms means the "
            "ADMIN console's room form has not been filled."
        ),
    }


@mcp.tool()
def vssp_room(room: str) -> dict:
    """List every entity in one Home Assistant area, with its current state.

    `room` is matched against the area id first, then case-insensitively
    against the area name, so both "salon" and "Salon" find the same one.

    This reads the area registry, which is what the discovery wizard
    harvests into the house model - it is not the model itself. See
    vssp_rooms for why the two differ.
    """
    areas, devices, entities = ha.registries()
    needle = room.strip().lower()
    match = next((a for a in areas if a.get("area_id") == room), None)
    if match is None:
        candidates = [a for a in areas if needle in (a.get("name") or "").lower()]
        if not candidates:
            # EN | "Known rooms: " followed by nothing is what an empty
            # EN | registry produced, and it reads as a broken tool rather
            # EN | than as an empty house - which is the actual state of
            # EN | both instances of this project today.
            # FR | « Known rooms : » suivi de rien est ce que produisait un
            # FR | registre vide, et cela se lit comme un outil casse
            # FR | plutot que comme une maison vide - ce qui est l'etat
            # FR | reel des deux instances de ce projet aujourd'hui.
            if not areas:
                raise ha.HAError(
                    "This instance has no Home Assistant areas at all, so "
                    "no room can match. Areas are created in Settings > "
                    "Areas, or harvested by the discovery wizard; the "
                    "dashboards themselves are rendered from house.yaml on "
                    "the instance, which is filled by the ADMIN console's "
                    "room form."
                )
            names = ", ".join(sorted((a.get("name") or "?") for a in areas))
            raise ha.HAError(f"No room matches {room!r}. Known rooms: {names}")
        match = candidates[0]

    area_id = match.get("area_id")
    device_area = {d.get("id"): d.get("area_id") for d in devices}
    mine = [e for e in entities
            if (e.get("area_id") or device_area.get(e.get("device_id"))) == area_id]
    by_id = _by_id(ha.states())
    rows = []
    for ent in sorted(mine, key=lambda e: e.get("entity_id") or ""):
        entity_id = ent.get("entity_id") or ""
        live = by_id.get(entity_id) or {}
        rows.append({
            "entity_id": entity_id,
            "domain": entity_id.split(".")[0] if "." in entity_id else None,
            "name": ent.get("name") or ent.get("original_name"),
            "state": live.get("state"),
            "device_class": (live.get("attributes") or {}).get("device_class"),
            "unit": (live.get("attributes") or {}).get("unit_of_measurement"),
            "disabled": bool(ent.get("disabled_by")),
            "hidden": bool(ent.get("hidden_by")),
        })
    return {"area_id": area_id, "name": match.get("name"),
            "entity_count": len(rows), "entities": rows}


@mcp.tool()
def vssp_dashboards() -> dict:
    """Report which Visio Sapiens dashboards currently exist on the box.

    HOME, CORE and ENERGY are created on demand and are protected from
    regeneration, so a declared dashboard whose file was never written
    answers 404 in the browser while looking perfectly configured in
    configuration.yaml. These sensors test the file itself.
    """
    by_id = _by_id(ha.states())
    watched = sorted(e for e in by_id if "vssp_dashboard_" in e)
    return {
        "dashboards": [_shape(by_id.get(e), e) for e in watched],
        "note": (
            "'on' means the YAML file exists on disk. A dashboard declared "
            "in configuration.yaml with no file behind it serves an error "
            "page - create it from the ADMIN console rather than by hand."
        ),
    }


@mcp.tool()
def vssp_dependencies() -> dict:
    """Report the frontend cards, integrations and Lovelace resources that
    Visio Sapiens needs, and which of them are missing on this instance.

    Populated by the CHECK DEPENDENCIES button in the ADMIN console. If it
    has never run, or if the instance has no saved token, the status entity
    says so and the report is empty rather than wrong.
    """
    by_id = _by_id(ha.states())
    report = _shape(by_id.get("sensor.vssp_dependencies"), "sensor.vssp_dependencies")
    status = _shape(by_id.get("sensor.vssp_dependencies_status"),
                    "sensor.vssp_dependencies_status")
    return {
        "report": report,
        "status": status,
        "remedy": (
            "Missing items are installed by the INSTALL DEPENDENCIES button "
            "in the ADMIN console's UPDATES screen. It needs a long-lived "
            "token saved on the instance first - the TOKEN REQUIRED card "
            "appears in that same row when one is missing."
        ),
    }


@mcp.tool()
def vssp_updates() -> dict:
    """Report every pending update Visio Sapiens tracks on this instance.

    Families: Home Assistant core and add-ons, HACS frontend cards, device
    firmware, and - only where they exist - the infrastructure layers
    (host, k3s, GitLab, runner). On a Home Assistant OS appliance the
    infrastructure family reports 'n/a': there is no k3s under it, and an
    OS box must never be offered a k3s version.
    """
    by_id = _by_id(ha.states())
    # EN | sensor.* only. A substring match on "vssp_updates_" also catches
    # EN | input_boolean.vssp_updates_auto, input_datetime.vssp_updates_
    # EN | auto_time and three script.vssp_updates_* - the CONTROLS of the
    # EN | UPDATES screen, not its counts. Caught by running this tool
    # EN | against the production instance's real state list, where they
    # EN | came back mixed in among the families as if "off" were a number
    # EN | of pending updates.
    # FR | sensor.* uniquement. Une correspondance de sous-chaine sur
    # FR | « vssp_updates_ » attrape aussi input_boolean.vssp_updates_auto,
    # FR | input_datetime.vssp_updates_auto_time et trois
    # FR | script.vssp_updates_* - les COMMANDES de l'ecran MISES A JOUR,
    # FR | pas ses comptes. Repere en executant cet outil contre la liste
    # FR | d'etats reelle de la production, ou ils revenaient meles aux
    # FR | familles comme si « off » etait un nombre de mises a jour.
    watched = sorted(e for e in by_id
                     if e.startswith("sensor.")
                     and ("vssp_updates_" in e or e.endswith("vssp_infra_auto")))
    families = [_shape(by_id.get(e), e) for e in watched]
    infra = next((f for f in families if f["entity_id"].endswith("_infra")), None)
    return {
        "families": families,
        "infrastructure_applies": bool(infra and infra.get("state") != "n/a"),
    }


@mcp.tool()
def find_entities(pattern: str, limit: int = 50) -> dict:
    """Search this instance's entities by id or friendly name.

    `pattern` is matched case-insensitively as a substring against both the
    entity id and the friendly name. Use it to find what a room or a
    template should point at before proposing a change.
    """
    needle = pattern.strip().lower()
    if not needle:
        raise ha.HAError("pattern is empty - give something to search for.")
    hits: list[dict[str, Any]] = []
    for state in ha.states():
        entity_id = state.get("entity_id") or ""
        name = (state.get("attributes") or {}).get("friendly_name") or ""
        if needle in entity_id.lower() or needle in name.lower():
            hits.append({"entity_id": entity_id, "name": name or None,
                         "state": state.get("state")})
    hits.sort(key=lambda h: h["entity_id"])
    return {"matched": len(hits), "returned": min(len(hits), limit),
            "entities": hits[:limit]}


def main() -> None:
    # EN | stdio: the transport every desktop MCP client speaks, and the
    # EN | only one that needs no port, no certificate and no listener on
    # EN | the home network. The client starts this process itself.
    # FR | stdio : le transport que parle tout client MCP de bureau, et le
    # FR | seul qui ne demande ni port, ni certificat, ni service a
    # FR | l'ecoute sur le reseau domestique. Le client demarre lui-meme ce
    # FR | processus.
    mcp.run()


if __name__ == "__main__":
    main()
