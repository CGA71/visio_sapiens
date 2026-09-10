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
# Visio Sapiens — Assignment applier
#
# EN | Takes what the assignment form produced and writes it into the `slots:`
# EN | of house.yaml. This is the missing link between the discovery scan and
# EN | the generator: the scan says what exists, the form says where it goes,
# EN | this script records the decision, and generate_dashboards.py renders it.
# FR | Prend ce que le formulaire d assignation a produit et l ecrit dans les
# FR | `slots:` de house.yaml. C est le maillon manquant entre le scan de
# FR | decouverte et le generateur : le scan dit ce qui existe, le formulaire
# FR | dit ou cela va, ce script enregistre la decision, et
# FR | generate_dashboards.py la rend.
#
# EN | INPUT — json, either from a file or base64 on the command line:
# FR | ENTREE — json, depuis un fichier ou en base64 en ligne de commande :
#   {"assignments": [
#      {"entity_id": "light.living_ceiling", "room": "living_room", "slot": "switches"},
#      {"entity_id": "sensor.living_temperature", "room": "living_room", "slot": "sensors"}
#   ]}
#
# EN | An entity with an empty room or slot is REMOVED from the model. That is
# EN | how the form unassigns something, and it is why this script replaces the
# EN | slots wholesale rather than merging: a merge could never delete, so an
# EN | entity moved from one room to another would end up in both.
# FR | Une entite dont la piece ou le tableau est vide est RETIREE du modele.
# FR | C est ainsi que le formulaire desassigne, et c est pourquoi ce script
# FR | remplace les slots en bloc plutot que de fusionner : une fusion ne
# FR | pourrait jamais supprimer, donc une entite deplacee d une piece a une
# FR | autre se retrouverait dans les deux.
#
# EN | ORDER IS PRESERVED as the form sent it — you decide the TV comes before
# EN | the console without renaming an entity.
# FR | L ORDRE EST PRESERVE tel que le formulaire l a envoye — vous decidez
# FR | que la TV passe avant la console sans renommer d entite.
#
# EN | USAGE / FR | UTILISATION
#   python3 vssp_assign_apply.py --model house.yaml --json-file payload.json
#   python3 vssp_assign_apply.py --model house.yaml --json-b64 "eyJ..."
#   python3 vssp_assign_apply.py --model house.yaml --json-file p.json --dry-run
#
# EN | Dependency: ruamel.yaml, to keep the comments of house.yaml. The file
# EN | is heavily documented and rewriting it with PyYAML would strip every
# EN | explanation it carries.
# FR | Dependance : ruamel.yaml, pour conserver les commentaires de house.yaml.
# FR | Le fichier est fortement documente et le reecrire avec PyYAML effacerait
# FR | toutes les explications qu il porte.
# ============================================================================
from __future__ import annotations

import argparse
import base64
import binascii
import datetime as _dt
import json
import shutil
import sys
from pathlib import Path

try:
    from ruamel.yaml import YAML
    from ruamel.yaml.comments import CommentedMap, CommentedSeq
except ImportError:
    sys.exit("[ERR] ruamel.yaml is missing. Install it: pip install ruamel.yaml")

SLOTS = ["sensors", "switches", "appliances", "security", "infrastructure"]


def _yaml():
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)
    return y


def read_payload(args) -> dict:
    if args.json_file:
        raw = Path(args.json_file).read_text(encoding="utf-8")
    elif args.json_b64:
        try:
            raw = base64.b64decode(args.json_b64).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as exc:
            sys.exit(f"[ERR] --json-b64 is not valid base64 utf-8: {exc}")
    else:
        raw = sys.stdin.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.exit(f"[ERR] payload is not valid json: {exc}")


def validate(payload: dict, rooms: dict, slot_sets: dict) -> tuple[dict, list]:
    """
    EN | Groups the assignments per room and slot, rejecting what cannot be
    EN | rendered. Refusing here is the whole point: an entity dropped into a
    EN | slot its room does not have would be written to house.yaml, pass the
    EN | generator, and then never appear on screen — the silent failure this
    EN | project keeps running into.
    FR | Groupe les assignations par piece et tableau, en rejetant ce qui ne
    FR | peut pas etre rendu. Refuser ici est tout l interet : une entite
    FR | placee dans un tableau que sa piece ne possede pas serait ecrite dans
    FR | house.yaml, passerait le generateur, et n apparaitrait jamais a
    FR | l ecran — la panne silencieuse que ce projet rencontre sans cesse.
    """
    errors: list = []
    grouped: dict = {rid: {} for rid in rooms}

    for item in payload.get("assignments") or []:
        eid = (item.get("entity_id") or "").strip()
        room = (item.get("room") or "").strip()
        slot = (item.get("slot") or "").strip()

        if not eid:
            errors.append("an assignment has no entity_id")
            continue
        # EN | empty room or slot = unassign, simply skipped
        # FR | piece ou tableau vide = desassignation, simplement ignoree
        if not room or not slot:
            continue
        if "." not in eid:
            errors.append(f"{eid}: not an entity_id (domain.object expected)")
            continue
        if room not in rooms:
            errors.append(f"{eid}: unknown room `{room}`")
            continue
        if slot not in SLOTS:
            errors.append(f"{eid}: unknown slot `{slot}`")
            continue
        allowed = slot_sets.get(rooms[room].get("slot_set", "default"), SLOTS)
        if slot not in allowed:
            errors.append(
                f"{eid}: room `{room}` has no `{slot}` slot "
                f"(set `{rooms[room].get('slot_set', 'default')}` allows "
                f"{', '.join(allowed)})")
            continue
        grouped[room].setdefault(slot, []).append(eid)

    return grouped, errors


def apply(model, grouped: dict) -> int:
    """
    EN | Replaces the `slots:` of every room by what was grouped. Returns the
    EN | number of entities written.
    FR | Remplace les `slots:` de chaque piece par ce qui a ete groupe.
    FR | Renvoie le nombre d entites ecrites.
    """
    written = 0
    for room in model.get("rooms") or []:
        rid = room.get("id")
        assigned = grouped.get(rid, {})
        slots = CommentedMap()
        for slot_id in SLOTS:
            if slot_id not in assigned:
                continue
            value = assigned[slot_id]
            slots[slot_id] = CommentedSeq(value)
            written += len(value)
        room["slots"] = slots
    return written


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="/config/dashboards/model/house.yaml")
    ap.add_argument("--json-file", default=None)
    ap.add_argument("--json-b64", default=None)
    ap.add_argument("--dry-run", action="store_true",
                    help="Validate and report, write nothing")
    ap.add_argument("--status-file", default="/config/www/vssp/assign_status.json")
    args = ap.parse_args()

    model_path = Path(args.model)
    if not model_path.is_file():
        sys.exit(f"[ERR] model not found: {model_path}")

    payload = read_payload(args)
    y = _yaml()
    model = y.load(model_path.read_text(encoding="utf-8"))

    rooms = {r.get("id"): r for r in (model.get("rooms") or []) if r.get("id")}
    if not rooms:
        sys.exit("[ERR] the model declares no room — nothing to assign to")

    slot_sets = dict(model.get("slot_sets") or {})
    slot_sets.setdefault("default", SLOTS)

    grouped, errors = validate(payload, rooms, slot_sets)

    status = {
        "ok": not errors,
        "errors": errors,
        "dry_run": args.dry_run,
        "timestamp": _dt.datetime.now().isoformat(timespec="seconds"),
    }

    if errors:
        print(f"[ERR] {len(errors)} invalid assignment(s) — nothing written:")
        for e in errors:
            print(f"  - {e}")
    else:
        written = apply(model, grouped)
        status["written"] = written
        status["rooms"] = {rid: sum(
            len(v) for v in grouped.get(rid, {}).values()) for rid in rooms}
        if args.dry_run:
            print(f"[dry-run] {written} entity(ies) would be written")
        else:
            # EN | Backup before writing: house.yaml is the source of truth and
            # EN | a bad payload must never be a one-way trip.
            # FR | Sauvegarde avant ecriture : house.yaml est la source de
            # FR | verite et un payload errone ne doit jamais etre sans retour.
            backups = model_path.parent / "backups"
            backups.mkdir(parents=True, exist_ok=True)
            stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = backups / f"house_{stamp}.yaml"
            shutil.copy2(model_path, dest)
            print(f"[OK] backup: {dest}")

            tmp = model_path.with_suffix(".vssptmp")
            with open(tmp, "w", encoding="utf-8") as fh:
                y.dump(model, fh)
            tmp.replace(model_path)
            print(f"[OK] {model_path}: {written} entity(ies) assigned")
            for rid, n in sorted(status["rooms"].items()):
                if n:
                    print(f"       {rid}: {n}")

    if args.status_file:
        try:
            sp = Path(args.status_file)
            sp.parent.mkdir(parents=True, exist_ok=True)
            sp.write_text(json.dumps(status, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        except OSError as exc:
            print(f"[warn] status file not written: {exc}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
