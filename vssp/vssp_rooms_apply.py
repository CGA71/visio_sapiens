#!/usr/bin/env python3
# ============================================================================
# Visio Sapiens — Room structure applier
#
# EN | Syncs house.yaml's `rooms:` list from the Home Assistant Area registry.
# EN | house.yaml's own header comment has always claimed "step 1 — the room
# EN | form writes/completes `rooms:`", but vssp_rooms_floors.html's Apply
# EN | button only ever wrote to the HA Area/Floor registry (via the frontend
# EN | WebSocket API) — nothing propagated that into house.yaml. The result:
# EN | the ASSIGN screen's room dropdown (built from house.yaml by
# EN | vssp_assign_prepare.py) could show a completely different room list
# EN | than the one PIECES & ETAGES had just created, because the two were
# EN | never the same data. This script is that missing link.
# FR | Synchronise la liste `rooms:` de house.yaml depuis le registre Zones
# FR | de Home Assistant. Le commentaire d en-tete de house.yaml a toujours
# FR | annonce « etape 1 — le formulaire de pieces ecrit/complete `rooms:` »,
# FR | mais le bouton Appliquer de vssp_rooms_floors.html n a jamais ecrit
# FR | que dans le registre Zones/Etages de HA (via l API WebSocket du
# FR | frontend) — rien ne propageait cela dans house.yaml. Resultat : le
# FR | menu deroulant de pieces de l ecran ASSIGN (construit depuis
# FR | house.yaml par vssp_assign_prepare.py) pouvait afficher une liste de
# FR | pieces completement differente de celle que PIECES & ETAGES venait
# FR | de creer, car les deux n etaient jamais la meme donnee. Ce script est
# FR | ce maillon manquant.
#
# EN | INPUT — json, either from a file or base64 on the command line:
# FR | ENTREE — json, depuis un fichier ou en base64 en ligne de commande :
#   {"rooms": [{"area_id": "living_room_ab12", "name": "Salon"}, ...]}
#
# EN | NEVER touches `slots:`. A room already linked to an area_id keeps its
# EN | id, type and slots untouched — this script only adds rooms for areas
# EN | it has not seen before, and best-effort LINKS an existing, still
# EN | unlinked room to an area of the same name rather than creating a
# EN | duplicate (house.yaml today has no area_id on any room — every room
# EN | is "unlinked" the first time this runs). A room whose area was
# EN | deleted in HA is left in place rather than removed: silently
# EN | dropping a room could silently drop everything assigned to it.
# FR | NE TOUCHE JAMAIS `slots:`. Une piece deja liee a un area_id garde son
# FR | id, son type et ses slots intacts — ce script ne fait qu ajouter des
# FR | pieces pour les zones qu il n a jamais vues, et RELIE en best-effort
# FR | une piece existante pas encore liee a une zone de meme nom plutot que
# FR | d en creer un doublon (house.yaml n a aujourd hui aucun area_id sur
# FR | aucune piece — chaque piece est "non liee" au premier lancement).
# FR | Une piece dont la zone a ete supprimee dans HA est laissee en place
# FR | plutot que retiree : supprimer une piece en silence pourrait
# FR | supprimer en silence tout ce qui lui est assigne.
#
# EN | Dependency: ruamel.yaml, same reason as vssp_assign_apply.py — house.yaml
# EN | is heavily documented and a PyYAML round-trip would strip every comment.
# FR | Dependance : ruamel.yaml, meme raison que vssp_assign_apply.py —
# FR | house.yaml est fortement documente et un aller-retour PyYAML
# FR | effacerait tous ses commentaires.
# ============================================================================
from __future__ import annotations

import argparse
import base64
import binascii
import datetime as _dt
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

try:
    from ruamel.yaml import YAML
    from ruamel.yaml.comments import CommentedMap
except ImportError:
    sys.exit("[ERR] ruamel.yaml is missing. Install it: pip install ruamel.yaml")

# EN | Recognised room types (locales/*.yaml `room:` catalogue, and
# EN | house.yaml's own `room_icons:`) with the keywords — English, French,
# EN | and the id itself — used to guess a type from an HA area name. Order
# EN | matters: checked top to bottom, first match wins, so a more specific
# EN | keyword should sit above a broader one.
# FR | Types de piece reconnus (catalogue `room:` de locales/*.yaml, et
# FR | `room_icons:` de house.yaml lui-meme) avec les mots-cles — anglais,
# FR | francais, et l id lui-meme — utilises pour deviner un type depuis un
# FR | nom de zone HA. L ordre compte : verifie de haut en bas, le premier
# FR | qui correspond gagne, donc un mot-cle plus specifique doit passer
# FR | avant un plus general.
TYPE_KEYWORDS = [
    ("bathroom",   ["bathroom", "salle de bain", "salle d'eau", "salle deau"]),
    ("bedroom",    ["bedroom", "chambre"]),
    ("dining_room",["dining", "salle a manger"]),
    ("living_room",["living", "salon", "sejour"]),
    ("kitchen",    ["kitchen", "cuisine"]),
    ("laundry",    ["laundry", "buanderie"]),
    ("toilet",     ["toilet", "wc", "toilette"]),
    ("entrance",   ["entrance", "entree", "hall", "vestibule"]),
    ("technical",  ["technical", "technique"]),
    ("computer",   ["computer", "server", "serveur", "desk", "bureau"]),
    ("secret",     ["secret"]),
    ("garage",     ["garage"]),
    ("cellar",     ["cellar", "cave"]),
    ("jacuzzi",    ["jacuzzi", "spa"]),
    ("pool",       ["pool", "piscine"]),
    ("garden",     ["garden", "jardin"]),
    ("roof",       ["roof", "toit"]),
]

# EN | Slot set guess, same idea, narrower list — most rooms want "default"
# EN | (checked last, implicitly, as the fallback) so only the exceptions
# EN | are listed. Mirrors DEFAULT_SLOT_SETS in vssp_assign_prepare.py.
# FR | Estimation du jeu de tableaux, meme idee, liste plus etroite — la
# FR | plupart des pieces veulent "default" (verifie en dernier,
# FR | implicitement, comme repli), donc seules les exceptions sont
# FR | listees. Reprend DEFAULT_SLOT_SETS de vssp_assign_prepare.py.
SLOT_SET_KEYWORDS = [
    ("toilet",   ["toilet", "wc", "toilette"]),
    ("garden",   ["garden", "jardin", "pool", "piscine", "jacuzzi", "spa"]),
    ("utility",  ["garage", "cellar", "cave", "laundry", "buanderie", "technical", "technique"]),
    ("entrance", ["entrance", "entree", "hall", "vestibule"]),
    ("minimal",  ["corridor", "couloir", "landing", "palier", "roof", "toit"]),
]


def normalize(s: str) -> str:
    """EN | Lowercase, strip accents/punctuation, collapse whitespace.
    FR | Minuscules, sans accents/ponctuation, espaces reduits."""
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    return s


def guess(name_norm: str, keywords) -> str | None:
    for key, words in keywords:
        for w in words:
            if w in name_norm:
                return key
    return None


def slugify(name: str, taken: set) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", normalize(name)).strip("_") or "room"
    slug = base
    n = 2
    while slug in taken:
        slug = f"{base}_{n}"
        n += 1
    return slug


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


def sync_rooms(model, incoming: list) -> dict:
    """
    EN | Returns a summary: {"linked": [...], "created": [...], "unchanged": n}.
    EN | Mutates model["rooms"] in place, appending new entries — existing
    EN | ones are only ever given an area_id, never rewritten otherwise.
    FR | Renvoie un resume : {"linked": [...], "created": [...], "unchanged": n}.
    FR | Modifie model["rooms"] sur place, en ajoutant de nouvelles entrees —
    FR | les existantes ne reçoivent jamais qu un area_id, jamais reecrites
    FR | autrement.
    """
    rooms = model.get("rooms")
    if rooms is None:
        rooms = model["rooms"] = []

    by_area_id = {r.get("area_id"): r for r in rooms if r.get("area_id")}
    unlinked = [r for r in rooms if not r.get("area_id")]
    taken_ids = {r.get("id") for r in rooms if r.get("id")}

    summary = {"linked": [], "created": [], "unchanged": 0}

    for area in incoming:
        area_id = (area.get("area_id") or "").strip()
        name = (area.get("name") or "").strip()
        if not area_id or not name:
            continue
        if area_id in by_area_id:
            summary["unchanged"] += 1
            continue

        name_norm = normalize(name)
        match = next(
            (r for r in unlinked
             if normalize(r.get("id", "")) == name_norm
             or normalize(r.get("type", "")) == name_norm),
            None,
        )
        if match:
            match["area_id"] = area_id
            unlinked.remove(match)
            by_area_id[area_id] = match
            summary["linked"].append({"id": match.get("id"), "area_id": area_id, "name": name})
            continue

        rtype = guess(name_norm, TYPE_KEYWORDS) or slugify(name, taken_ids)
        slot_set = guess(name_norm, SLOT_SET_KEYWORDS) or "default"
        rid = slugify(name, taken_ids)
        taken_ids.add(rid)

        new_room = CommentedMap()
        new_room["id"] = rid
        new_room["type"] = rtype
        new_room["slot_set"] = slot_set
        new_room["area_id"] = area_id
        new_room["slots"] = CommentedMap()
        rooms.append(new_room)
        by_area_id[area_id] = new_room
        summary["created"].append({"id": rid, "area_id": area_id, "name": name, "type": rtype, "slot_set": slot_set})

    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="/config/dashboards/model/house.yaml")
    ap.add_argument("--json-file", default=None)
    ap.add_argument("--json-b64", default=None)
    ap.add_argument("--dry-run", action="store_true",
                    help="Compute and report, write nothing")
    ap.add_argument("--status-file", default="/config/www/vssp/rooms_sync_status.json")
    args = ap.parse_args()

    model_path = Path(args.model)
    if not model_path.is_file():
        sys.exit(f"[ERR] model not found: {model_path}")

    payload = read_payload(args)
    incoming = payload.get("rooms")
    if not isinstance(incoming, list):
        sys.exit("[ERR] payload has no `rooms` list")

    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)
    model = y.load(model_path.read_text(encoding="utf-8"))

    summary = sync_rooms(model, incoming)
    status = {
        "ok": True,
        "dry_run": args.dry_run,
        "timestamp": _dt.datetime.now().isoformat(timespec="seconds"),
        **summary,
    }

    if args.dry_run:
        print(f"[dry-run] {len(summary['linked'])} would be linked, "
              f"{len(summary['created'])} would be created, "
              f"{summary['unchanged']} already in sync")
    elif not summary["linked"] and not summary["created"]:
        print(f"[OK] {model_path}: already in sync ({summary['unchanged']} room(s))")
    else:
        # EN | Backup before writing, same reflex as vssp_assign_apply.py:
        # EN | house.yaml is the source of truth, so a bad sync must never
        # EN | be a one-way trip.
        # FR | Sauvegarde avant ecriture, meme reflexe que
        # FR | vssp_assign_apply.py : house.yaml est la source de verite,
        # FR | donc une synchronisation ratee ne doit jamais etre sans
        # FR | retour.
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

        print(f"[OK] {model_path}: {len(summary['linked'])} room(s) linked, "
              f"{len(summary['created'])} room(s) created")
        for r in summary["linked"]:
            print(f"       linked  {r['id']} <- {r['name']} ({r['area_id']})")
        for r in summary["created"]:
            print(f"       created {r['id']} (type={r['type']}, slot_set={r['slot_set']}) <- {r['name']}")

    if args.status_file:
        try:
            sp = Path(args.status_file)
            sp.parent.mkdir(parents=True, exist_ok=True)
            sp.write_text(json.dumps(status, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        except OSError as exc:
            print(f"[warn] status file not written: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
