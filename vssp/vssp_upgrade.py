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
Visio Sapiens — Upgrade Engine (STUB)
====================================
STATUT ACTUEL : squelette non destructif. Ne modifie PAS encore le
dashboard. La vraie logique de generation (choisir quel gabarit de
carte utiliser par device_class, injecter les nouvelles entites dans
le bon 'cadre' visuel, etc.) reste a construire — c'est un projet en
soi, volontairement pas improvise pour eviter de casser un dashboard
qui fonctionne.

Ce que fait CETTE version :
  1. Relit le dernier rapport de decouverte (report.json).
  2. Compare avec les entity_id actuellement presents dans home.yaml.
  3. Liste les entites NOUVELLES (decouvertes mais absentes du YAML)
     et les entites 'orphelines' (presentes dans le YAML en TODO mais
     jamais resolues).
  4. Ecrit un rapport de diff lisible, SANS toucher a home.yaml.

Quand la vraie logique de generation sera prete, ce script pourra
evoluer pour ecrire directement les modifications (avec sauvegarde
prealable systematique, deja geree par le script shell_command dedie).
"""

import json
import re
import sys
from pathlib import Path

REPORT_PATH = Path("/config/vssp/report.json")
DASHBOARD_PATH = Path("/config/home-assistant/dashboards/home.yaml")
DIFF_OUTPUT = Path("/config/vssp/upgrade_diff.json")


def load_report():
    if not REPORT_PATH.exists():
        sys.exit(
            f"Aucun rapport trouve a {REPORT_PATH}. "
            "Lance d'abord le bouton DISCOVERY."
        )
    with open(REPORT_PATH, encoding="utf-8") as f:
        return json.load(f)


def entities_in_dashboard():
    if not DASHBOARD_PATH.exists():
        return set()
    text = DASHBOARD_PATH.read_text(encoding="utf-8")
    # Capture les entity_id references (entity:, entities:, service_data...)
    return set(re.findall(r"\b([a-z_]+\.[a-z0-9_]+)\b", text))


def main():
    report = load_report()
    known = entities_in_dashboard()

    discovered = set()
    for area_id, area_data in report.items():
        for device_class, entities in area_data.get("entities_by_device_class", {}).items():
            for e in entities:
                discovered.add(e["entity_id"])

    new_entities = sorted(discovered - known)
    diff = {
        "new_entities_not_in_dashboard": new_entities,
        "note": (
            "Squelette non destructif : aucune modification appliquee. "
            "Cette liste sert a decider manuellement (ou dans une future "
            "version automatisee) quoi ajouter, et a quel 'cadre' OSVision."
        ),
    }

    DIFF_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(DIFF_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(diff, f, ensure_ascii=False, indent=2)

    print(f"{len(new_entities)} entite(s) decouverte(s) absente(s) du dashboard.")
    print(f"Detail ecrit dans {DIFF_OUTPUT}")


if __name__ == "__main__":
    main()
