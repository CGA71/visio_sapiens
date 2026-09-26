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
# Visio Sapiens - vssp_repairs.py
#
# EN | WHAT THIS IS FOR. Home Assistant raises repair issues - a unit that
# EN | changed under a statistic, an add-on that needs attention, a host
# EN | waiting for a restart - and shows them on its own settings page. The
# EN | control centre never looked, so an owner could work in it all day
# EN | while two warnings sat one menu away. Measured on the appliance
# EN | staging: a statistic whose unit changed, and a system reboot required
# EN | by the add-on work done that same night.
# FR | A QUOI CECI SERT. Home Assistant leve des corrections - une unite qui
# FR | a change sous une statistique, un add-on qui reclame de l attention,
# FR | un hote qui attend un redemarrage - et les affiche sur sa propre page
# FR | de reglages. Le centre de controle ne regardait jamais : un
# FR | proprietaire pouvait y travailler toute la journee pendant que deux
# FR | avertissements patientaient un menu plus loin. Mesure sur la
# FR | preproduction appareil : une statistique dont l unite a change, et un
# FR | redemarrage systeme reclame par le travail sur les add-ons de la nuit.
#
# EN | ON THE WORDING. Home Assistant stores a translation key, not a
# EN | sentence: "issue_system_reboot_required" becomes readable text only in
# EN | its own frontend, from its own catalogue. This script does not invent
# EN | that text. It carries the key, the domain and whether the issue can be
# EN | fixed, and the screen shows a sentence of ours for the keys we know
# EN | and "domain - key" for the rest, with a button that opens the page
# EN | where Home Assistant spells it out in full.
# FR | SUR LES LIBELLES. Home Assistant garde une cle de traduction, pas une
# FR | phrase : « issue_system_reboot_required » ne devient lisible que dans
# FR | son propre frontend, depuis son propre catalogue. Ce script n invente
# FR | pas ce texte. Il transporte la cle, le domaine et le caractere
# FR | reparable, et l ecran affiche une phrase a nous pour les cles que nous
# FR | connaissons, « domaine - cle » pour les autres, avec un bouton qui
# FR | ouvre la page ou Home Assistant l ecrit en toutes lettres.
#
# EN | It reports and never repairs. A repair is a flow with its own steps,
# EN | like a discovery: showing what waits and handing over beats a second,
# EN | poorer implementation of a screen Home Assistant already draws.
# FR | Il rapporte et ne repare jamais. Une correction est un flux avec ses
# FR | etapes propres, comme une decouverte : montrer ce qui attend et passer
# FR | la main vaut mieux qu une seconde implementation, moins bonne, d un
# FR | ecran que Home Assistant dessine deja.
#
# EN | USAGE / FR | UTILISATION
#   python3 vssp_repairs.py
#   python3 vssp_repairs.py --url http://192.168.1.200:8123 --out /tmp/r.json
#
# EN | Exit codes: 0 when the instance answered - no issue is an answer.
# EN | 1 when nothing could be read, so the screen tells "nothing to fix"
# EN | from "I could not look".
# FR | Codes de sortie : 0 des que l instance a repondu - aucune correction
# FR | est une reponse. 1 quand rien n a pu etre lu, pour que l ecran
# FR | distingue « rien a corriger » de « je n ai pas pu regarder ».
# ============================================================================
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vssp_ws import WSError, connected, resolve_token  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Visio Sapiens - list the repair issues Home Assistant "
                    "is holding")
    ap.add_argument("--url", default="http://localhost:8123")
    ap.add_argument("--token-file", default="/config/vssp/.ha_token")
    ap.add_argument("--out", default="/config/www/vssp/repairs.json")
    args = ap.parse_args()

    token = resolve_token(os.environ.get("HA_TOKEN"), args.token_file)
    if not token:
        print("[ERR] no token: set HA_TOKEN or pass --token-file",
              file=sys.stderr)
        return 1

    try:
        ws = connected(args.url, token)
        answer = ws.command({"type": "repairs/list_issues"}) or {}
        ws.close()
    except (WSError, OSError) as exc:
        print(f"[ERR] {exc}", file=sys.stderr)
        return 1

    raw = answer.get("issues") if isinstance(answer, dict) else answer
    items = []
    for issue in raw or []:
        if not isinstance(issue, dict):
            continue
        # EN | An issue someone dismissed is not waiting for anyone.
        # FR | Une correction ecartee n attend plus personne.
        if issue.get("dismissed_version"):
            continue
        items.append({
            "domain": str(issue.get("domain") or ""),
            "key": str(issue.get("translation_key")
                       or issue.get("issue_id") or ""),
            "severity": str(issue.get("severity") or ""),
            "fixable": bool(issue.get("is_fixable")),
            "created": str(issue.get("created") or ""),
        })

    items.sort(key=lambda row: (row["severity"] != "critical",
                                row["domain"], row["key"]))
    report = {"count": len(items), "items": items,
              "at": datetime.now().isoformat(timespec="seconds")}
    try:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                          encoding="utf-8")
    except OSError as exc:
        print(f"[ERR] {args.out}: {exc}", file=sys.stderr)
        return 1

    print(f"[OK] {len(items)} repair issue(s) waiting")
    for row in items:
        fix = "fixable" if row["fixable"] else "needs a decision"
        print(f"      - {row['domain']} · {row['key']}  ({fix})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
