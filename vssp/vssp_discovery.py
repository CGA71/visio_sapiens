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

"""
Visio Sapiens — Discovery Tool
============================
Script de decouverte en lecture seule. Interroge ton Home Assistant pour
lister, PAR PIECE (Area), toutes les entites disponibles groupees par
device_class / domaine. Ne modifie RIEN sur ton HA (aucune ecriture).

PREREQUIS
---------
1. pip install requests
2. Cree un jeton d'acces longue duree :
   Profil (cliquer sur ton nom en bas a gauche) > tout en bas de la page
   > "Jetons d'acces longue duree" > Creer un jeton.
3. Renseigne HA_URL et HA_TOKEN ci-dessous (ou via variables d'environnement).

USAGE
-----
    export HA_URL="http://192.168.1.11:8123"
    export HA_TOKEN="eyJhbGciOi..."
    python3 vssp_discovery.py

    # Ou cible uniquement certaines pieces :
    python3 vssp_discovery.py --areas living_room,kitchen,garden

SORTIE
------
Un rapport lisible dans la console, ET un fichier JSON
(vssp_discovery_report.json) que tu peux me renvoyer directement
pour qu'on branche les entites dans le dashboard.
"""

import os
import sys
import json
import argparse
from collections import defaultdict

try:
    import requests
except ImportError:
    sys.exit("Le module 'requests' est requis. Installe-le avec : pip install requests")


def get_config():
    parser = argparse.ArgumentParser(description="Visio Sapiens - Discovery Tool")
    parser.add_argument("--url", default=os.environ.get("HA_URL"), help="URL de ton Home Assistant, ex: http://192.168.1.11:8123")
    parser.add_argument("--token", default=os.environ.get("HA_TOKEN"), help="Jeton d'acces longue duree")
    parser.add_argument("--areas", default=None, help="Liste d'area_id a cibler, separes par des virgules (sinon: toutes)")
    parser.add_argument("--output", default="vssp_discovery_report.json", help="Fichier JSON de sortie")
    args = parser.parse_args()

    if not args.url or not args.token:
        sys.exit(
            "Il manque HA_URL et/ou HA_TOKEN.\n"
            "Renseigne-les via variables d'environnement ou --url / --token.\n"
            "Voir l'en-tete du script pour comment creer un jeton."
        )
    args.url = args.url.rstrip("/")
    return args


def render_template(base_url, token, template):
    """Execute un template Jinja cote serveur via l'API REST de HA."""
    resp = requests.post(
        f"{base_url}/api/template",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"template": template},
        timeout=15,
    )
    resp.raise_for_status()
    # Le endpoint /api/template renvoie du texte brut (rendu Jinja).
    # On lui demande de rendre du JSON pour pouvoir le reparser proprement.
    return resp.text


def get_all_areas(base_url, token):
    """Recupere la liste de toutes les Areas (id + nom) via un template Jinja."""
    template = "{{ areas() | tojson }}"
    raw = render_template(base_url, token, template)
    area_ids = json.loads(raw)
    areas = {}
    for area_id in area_ids:
        name_template = f"{{{{ area_name('{area_id}') }}}}"
        name = render_template(base_url, token, name_template)
        areas[area_id] = name
    return areas


def get_area_entities(base_url, token, area_id):
    template = f"{{{{ area_entities('{area_id}') | tojson }}}}"
    raw = render_template(base_url, token, template)
    return json.loads(raw)


def get_state(base_url, token, entity_id):
    resp = requests.get(
        f"{base_url}/api/states/{entity_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if resp.status_code != 200:
        return None
    return resp.json()


def get_all_states(base_url, token):
    resp = requests.get(
        f"{base_url}/api/states",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# EN | area_entities() only ever returns what Home Assistant already has
# EN | filed under an Area — nothing else. On an instance where devices
# EN | haven't been organized into Areas yet, that makes the scan report
# EN | "nothing found" for entities that plainly exist, which is exactly
# EN | backwards for a tool whose whole job is helping assign devices to a
# EN | room. This is the curated "assignable device" domain list (same one
# EN | the old standalone wizard used before the area-scoped scan replaced
# EN | it) for the area-LESS fallback below — deliberately narrower than
# EN | the per-area scan above (which is unfiltered, sensors included: an
# EN | Area is already a bounded, deliberately-organized set, so listing
# EN | everything in it is fine, but doing that for the WHOLE instance
# EN | would dump every integration's diagnostic/battery/signal sensor that
# EN | has no Area, which is mostly noise here).
# FR | area_entities() ne renvoie jamais que ce que Home Assistant a deja
# FR | classe sous une Zone — rien d'autre. Sur une instance ou les
# FR | appareils n'ont pas encore ete organises en Zones, cela fait dire au
# FR | scan « rien trouve » pour des entites qui existent bel et bien, ce
# FR | qui est exactement a l'envers pour un outil dont le travail est
# FR | precisement d'aider a assigner des appareils a une piece. Voici la
# FR | liste des domaines « appareil assignable » (la meme que l'ancien
# FR | wizard autonome utilisait avant que le scan par zone ne le
# FR | remplace) pour le repli SANS zone ci-dessous — deliberement plus
# FR | etroite que le scan par zone ci-dessus (non filtre, capteurs
# FR | compris : une Zone est deja un ensemble borne et organise
# FR | deliberement, donc tout y lister ne pose pas de probleme, mais faire
# FR | pareil pour TOUTE l'instance deverserait le capteur
# FR | diagnostic/batterie/signal de chaque integration sans Zone, ce qui
# FR | est surtout du bruit ici).
UNASSIGNED_DOMAINS = [
    "light", "switch", "climate", "media_player", "cover", "camera",
    "alarm_control_panel", "vacuum", "fan", "lock", "input_boolean",
    "button", "remote",
]


def main():
    args = get_config()
    print(f"Connexion a {args.url} ...")

    all_areas = get_all_areas(args.url, args.token)
    if not all_areas:
        sys.exit("Aucune Area trouvee. Verifie que des Zones (Areas) existent bien dans HA.")

    if args.areas:
        wanted = set(a.strip() for a in args.areas.split(","))
        all_areas = {k: v for k, v in all_areas.items() if k in wanted}

    report = {}
    seen_entities = set()

    for area_id, area_name in all_areas.items():
        print(f"\n=== {area_name} ({area_id}) ===")
        entity_ids = get_area_entities(args.url, args.token, area_id)
        by_device_class = defaultdict(list)

        for entity_id in entity_ids:
            state = get_state(args.url, args.token, entity_id)
            if not state:
                continue
            seen_entities.add(entity_id)
            attrs = state.get("attributes", {})
            device_class = attrs.get("device_class") or f"(domaine: {entity_id.split('.')[0]})"
            by_device_class[device_class].append({
                "entity_id": entity_id,
                "friendly_name": attrs.get("friendly_name", entity_id),
                "state": state.get("state"),
                "unit": attrs.get("unit_of_measurement"),
            })

        report[area_id] = {
            "name": area_name,
            "entities_by_device_class": dict(by_device_class),
        }

        if not entity_ids:
            print("  (aucune entite assignee a cette zone)")
        for device_class, entities in by_device_class.items():
            print(f"  [{device_class}]")
            for e in entities:
                unit = f" {e['unit']}" if e["unit"] else ""
                print(f"    - {e['entity_id']}  =>  {e['state']}{unit}   ({e['friendly_name']})")

    # EN | Second pass, whole instance: anything of an assignable domain
    # EN | that no Area claimed above. Only when scanning everything — a
    # EN | caller who asked for --areas living_room,kitchen explicitly
    # EN | wants just those, not every unareaed device on top.
    # FR | Seconde passe, instance entiere : tout ce qui est d'un domaine
    # FR | assignable et qu'aucune Zone n'a reclame ci-dessus. Seulement
    # FR | quand on scanne tout — un appel avec --areas living_room,kitchen
    # FR | veut explicitement seulement ca, pas tous les appareils sans
    # FR | zone en plus.
    if not args.areas:
        print("\n=== (sans zone) ===")
        by_device_class = defaultdict(list)
        for state in get_all_states(args.url, args.token):
            entity_id = state["entity_id"]
            if entity_id in seen_entities:
                continue
            domain = entity_id.split(".", 1)[0]
            if domain not in UNASSIGNED_DOMAINS:
                continue
            attrs = state.get("attributes", {})
            device_class = attrs.get("device_class") or f"(domaine: {domain})"
            by_device_class[device_class].append({
                "entity_id": entity_id,
                "friendly_name": attrs.get("friendly_name", entity_id),
                "state": state.get("state"),
                "unit": attrs.get("unit_of_measurement"),
            })

        if by_device_class:
            report["__unassigned__"] = {
                "name": "(sans zone)",
                "entities_by_device_class": dict(by_device_class),
            }
            for device_class, entities in by_device_class.items():
                print(f"  [{device_class}]")
                for e in entities:
                    unit = f" {e['unit']}" if e["unit"] else ""
                    print(f"    - {e['entity_id']}  =>  {e['state']}{unit}   ({e['friendly_name']})")
        else:
            print("  (rien — tous les appareils assignables ont deja une zone)")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Rapport complet ecrit dans : {args.output}")
    print("Renvoie ce fichier (ou colle son contenu) pour qu'on branche les entites dans le dashboard.")


if __name__ == "__main__":
    main()
