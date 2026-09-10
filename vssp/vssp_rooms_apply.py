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
#   {"rooms": [{"area_id": "living_room_ab12", "name": "Salon",
#               "slot_set": "default", "default_slot": "security"}, ...]}
#
# EN | `slot_set` is OPTIONAL per room. When present and one of
# EN | KNOWN_SLOT_SETS, it is trusted over this script's own name-keyword
# EN | guess (SLOT_SET_KEYWORDS below) — this is what lets the admin pick a
# EN | room's slot_set by hand in PIECES & ETAGES instead of only ever
# EN | getting whatever the room's name happens to guess to. Absent,
# EN | unknown, or blank: falls back to the guess (new room) or is left
# EN | untouched (existing room) exactly as before this existed.
# EN | `default_slot` is OPTIONAL too, but behaves slightly differently: it
# EN | has no name-keyword guess to fall back to (nothing about a room's name
# EN | says which of its panels should get the most screen space), so a
# EN | missing key just leaves the existing value untouched, while a present
# EN | key — including an explicit "" for "let the generator pick" — is
# EN | always applied when it's a member of KNOWN_SLOTS or empty. See
# EN | sync_rooms()'s docstring for the full "key absent vs empty value"
# EN | distinction this requires.
# FR | `slot_set` est OPTIONNEL par piece. Present et dans KNOWN_SLOT_SETS,
# FR | il prime sur l estimation par mot-cle du nom que fait ce script
# FR | (SLOT_SET_KEYWORDS plus bas) — c est ce qui permet a l administrateur
# FR | de choisir a la main le slot_set d une piece dans PIECES & ETAGES au
# FR | lieu de toujours recevoir ce que le nom de la piece devine. Absent,
# FR | inconnu ou vide : repli sur l estimation (piece nouvelle) ou laisse
# FR | intact (piece existante), exactement comme avant que ceci existe.
# FR | `default_slot` est OPTIONNEL aussi, mais se comporte legerement
# FR | different : il n a pas d estimation par mot-cle vers laquelle se
# FR | replier (rien dans le nom d une piece ne dit lequel de ses tableaux
# FR | doit recevoir le plus d espace ecran), donc une cle absente laisse
# FR | simplement la valeur existante intacte, alors qu une cle presente —
# FR | y compris un "" explicite pour « laisser le generateur choisir » —
# FR | est toujours appliquee des lors qu elle est un membre de KNOWN_SLOTS
# FR | ou vide. Voir la docstring de sync_rooms() pour la distinction
# FR | complete « cle absente contre valeur vide » que cela impose.
#
# EN | NEVER touches the `slots:` of a room it keeps. A room already linked
# EN | to an area_id keeps its id, type and slots untouched — this script
# EN | only adds rooms for areas it has not seen before, and best-effort
# EN | LINKS an existing, still unlinked room to an area of the same name
# EN | rather than creating a duplicate.
# EN | A LINKED room whose area_id is absent from the incoming list IS
# EN | removed. `incoming` is always the FULL current HA Area registry
# EN | snapshot (vssp_rooms_floors.html sends every area it just read, never
# EN | a partial list), so "linked but missing here" means the area was
# EN | genuinely deleted in HA — and the admin already confirmed that
# EN | deletion, with its own entity-count warning, before the registry
# EN | write that produced this snapshot. Repeating that confirmation here
# EN | would be redundant, and leaving the room behind would mean "Delete
# EN | all" in the room editor never actually empties house.yaml, no matter
# EN | how many times it's used.
# EN | An UNLINKED room (no area_id) is kept ONLY if this pass links it to
# EN | one of the incoming areas by matching id/type. Any unlinked room
# EN | still unmatched once every incoming area has been processed is
# EN | pruned too, as an orphan: `incoming` is the full current registry, so
# EN | vssp_rooms_floors.html has already created/renamed/deleted every HA
# EN | area BEFORE sending this snapshot — there is no longer a workflow
# EN | that leaves a room deliberately unlinked pending a later match. An
# EN | unlinked survivor is stale placeholder state (hand-written rooms
# EN | that predate this sync, or a room whose area was renamed into
# EN | something this pass's keyword guess no longer recognises), and
# EN | leaving it behind is exactly what made the nav rail show rooms no
# EN | longer in the HA Area registry.
# FR | NE TOUCHE JAMAIS les `slots:` d une piece qu il garde. Une piece deja
# FR | liee a un area_id garde son id, son type et ses slots intacts — ce
# FR | script ne fait qu ajouter des pieces pour les zones qu il n a jamais
# FR | vues, et RELIE en best-effort une piece existante pas encore liee a
# FR | une zone de meme nom plutot que d en creer un doublon.
# FR | Une piece LIEE dont l area_id est absent de la liste recue EST
# FR | retiree. `incoming` est toujours l instantane COMPLET et actuel du
# FR | registre Zones HA (vssp_rooms_floors.html envoie toutes les zones
# FR | qu il vient de lire, jamais une liste partielle), donc "liee mais
# FR | absente ici" signifie que la zone a vraiment ete supprimee dans HA —
# FR | et l administrateur a deja confirme cette suppression, avec son
# FR | propre avertissement sur le nombre d entites, avant l ecriture
# FR | registre qui a produit cet instantane. Repeter cette confirmation ici
# FR | serait redondant, et laisser la piece en place voudrait dire que
# FR | « Tout supprimer » dans l editeur de pieces ne vide jamais vraiment
# FR | house.yaml, quel que soit le nombre de fois qu on l utilise.
# FR | Une piece NON LIEE (pas d area_id) n est gardee que si ce passage la
# FR | relie a une des zones recues par correspondance id/type. Toute piece
# FR | non liee qui reste sans correspondance une fois toutes les zones
# FR | recues traitees est elle aussi retiree, comme orpheline :
# FR | `incoming` est l instantane complet et actuel du registre, donc
# FR | vssp_rooms_floors.html a deja cree/renomme/supprime chaque zone HA
# FR | AVANT d envoyer cet instantane — il n existe plus de parcours qui
# FR | laisse une piece deliberement non liee en attente d une
# FR | correspondance future. Une survivante non liee est un etat placeholder
# FR | perime (pieces ecrites a la main d avant cette synchro, ou piece dont
# FR | la zone a ete renommee en quelque chose que la devinette par mot-cle
# FR | de ce passage ne reconnait plus), et la laisser en place est
# FR | exactement ce qui faisait apparaitre dans le bandeau des pieces qui
# FR | n existent plus dans le registre Zones HA.
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

# EN | Every slot_set a room can legitimately carry — same identifiers as
# EN | DEFAULT_SLOT_SETS in generate_dashboards.py / vssp_assign_prepare.py,
# EN | kept in sync by hand, same as those two already are with each other.
# EN | Guards the incoming `slot_set` field: a payload from a compromised or
# EN | out-of-date browser tab must never write a nonsense value straight
# EN | into house.yaml.
# FR | Tout slot_set qu une piece peut legitimement porter — memes
# FR | identifiants que DEFAULT_SLOT_SETS dans generate_dashboards.py /
# FR | vssp_assign_prepare.py, tenus a jour a la main, comme ces deux-la le
# FR | sont deja l un avec l autre. Protege le champ `slot_set` recu : un
# FR | payload venant d un onglet compromis ou perime ne doit jamais ecrire
# FR | une valeur absurde directement dans house.yaml.
KNOWN_SLOT_SETS = {"default", "toilet", "garden", "utility", "entrance", "minimal", "computer"}

# EN | Same idea, for `default_slot` — same identifiers as SLOTS in
# EN | generate_dashboards.py. Empty string is valid (means "let
# EN | resolve_default_slot() pick automatically"), unlike KNOWN_SLOT_SETS
# EN | which always needs a real value.
# FR | Meme principe, pour `default_slot` — memes identifiants que SLOTS
# FR | dans generate_dashboards.py. Chaine vide valide (signifie « laisser
# FR | resolve_default_slot() choisir automatiquement »), contrairement a
# FR | KNOWN_SLOT_SETS qui a toujours besoin d une vraie valeur.
KNOWN_SLOTS = {"sensors", "switches", "appliances", "security", "infrastructure"}


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
    EN | Returns a summary:
    EN |   {"linked": [...], "created": [...], "renamed": [...],
    EN |    "slot_set_changed": [...], "default_slot_changed": [...],
    EN |    "removed": [...], "orphaned": [...], "unchanged": n}.
    EN | Mutates model["rooms"] in place: new entries are appended, a LINKED
    EN | room missing from `incoming` is dropped (see the module docstring
    EN | for why that is safe here), an UNLINKED room still unmatched after
    EN | every incoming area has been processed is dropped too ("orphaned"),
    EN | and `name` is kept up to date on every room this pass touches — so
    EN | a rename in the HA Area registry reaches the rendered navigation
    EN | rail on the next sync, the same way a deletion does. `id` and `type`
    EN | are never rewritten once set. `slot_set` and `default_slot` are a
    EN | live mirror of whatever the incoming payload explicitly sends (see
    EN | KNOWN_SLOT_SETS/KNOWN_SLOTS above) — these are the fields the admin
    EN | edits by hand in PIECES & ETAGES, so unlike `id`/`type` they are
    EN | expected to change after creation. `default_slot` alone accepts an
    EN | explicit "" as a real, applyable value — see the module docstring's
    EN | note on it. `slots` (the actual device assignments) is never
    EN | touched here at all — that is ASSIGN's job, not this script's.
    FR | Renvoie un resume :
    FR |   {"linked": [...], "created": [...], "renamed": [...],
    FR |    "slot_set_changed": [...], "default_slot_changed": [...],
    FR |    "removed": [...], "orphaned": [...], "unchanged": n}.
    FR | Modifie model["rooms"] sur place : les nouvelles entrees sont
    FR | ajoutees, une piece LIEE absente de `incoming` est retiree (voir la
    FR | docstring du module pour pourquoi c est sans risque ici), une piece
    FR | NON LIEE toujours sans correspondance une fois toutes les zones
    FR | recues traitees est retiree aussi (« orpheline »), et `name` est
    FR | tenu a jour sur chaque piece touchee par ce passage — pour qu un
    FR | renommage dans le registre Zones HA atteigne le bandeau de
    FR | navigation rendu au prochain sync, comme le fait deja une
    FR | suppression. `id` et `type` ne sont jamais reecrits une fois poses.
    FR | `slot_set` est un miroir vivant de ce que le payload recu envoie
    FR | explicitement (voir KNOWN_SLOT_SETS ci-dessus) — c est le seul champ
    FR | que l administrateur edite a la main dans PIECES & ETAGES, donc
    FR | contrairement a `id`/`type` il est cense changer apres la creation.
    FR | `slots` (les assignations d appareils reelles) n est jamais touche
    FR | ici — c est le travail d ASSIGN, pas celui de ce script.
    """
    rooms = model.get("rooms")
    if rooms is None:
        rooms = model["rooms"] = []

    incoming_area_ids = {
        (area.get("area_id") or "").strip() for area in incoming
    } - {""}

    summary = {"linked": [], "created": [], "renamed": [], "slot_set_changed": [],
               "default_slot_changed": [], "removed": [], "orphaned": [], "unchanged": 0}

    # EN | Prune first: a room whose area_id no longer appears in the fresh
    # EN | registry snapshot was deleted in HA. Doing this before the
    # EN | link/create pass below means a deleted-then-recreated area (same
    # EN | name, new area_id) is treated as genuinely new, not confused with
    # EN | the room being removed.
    # FR | Retirer d abord : une piece dont l area_id n apparait plus dans l
    # FR | instantane frais du registre a ete supprimee dans HA. Le faire
    # FR | avant la passe lien/creation ci-dessous fait qu une zone supprimee
    # FR | puis recreee (meme nom, nouvel area_id) est traitee comme
    # FR | vraiment nouvelle, sans etre confondue avec la piece qu on retire.
    kept = []
    for r in rooms:
        aid = r.get("area_id")
        if aid and aid not in incoming_area_ids:
            summary["removed"].append({"id": r.get("id"), "area_id": aid})
            continue
        kept.append(r)
    rooms[:] = kept

    by_area_id = {r.get("area_id"): r for r in rooms if r.get("area_id")}
    unlinked = [r for r in rooms if not r.get("area_id")]
    taken_ids = {r.get("id") for r in rooms if r.get("id")}

    for area in incoming:
        area_id = (area.get("area_id") or "").strip()
        name = (area.get("name") or "").strip()
        if not area_id or not name:
            continue
        incoming_slot_set = (area.get("slot_set") or "").strip()
        if incoming_slot_set not in KNOWN_SLOT_SETS:
            incoming_slot_set = None

        # EN | default_slot differs from slot_set in one way: "" is a
        # EN | legitimate, applyable value (means "let resolve_default_slot()
        # EN | pick automatically"), not "field absent, ignore it". So the key
        # EN | must be distinguished from its value — an old browser tab that
        # EN | never sends `default_slot` at all must leave the room's
        # EN | existing value untouched, while a tab that deliberately sends
        # EN | "" (the wizard's "(automatic)" option) must be able to clear a
        # EN | previously-set value.
        # FR | default_slot differe de slot_set sur un point : "" est une
        # FR | valeur legitime, applicable (signifie « laisser
        # FR | resolve_default_slot() choisir automatiquement »), pas
        # FR | « champ absent, ignorer ». La cle doit donc etre distinguee de
        # FR | sa valeur — un onglet perime qui n envoie jamais `default_slot`
        # FR | du tout doit laisser la valeur existante de la piece intacte,
        # FR | alors qu un onglet qui envoie deliberement "" (l option
        # FR | « automatique » de l assistant) doit pouvoir effacer une
        # FR | valeur precedemment posee.
        default_slot_present = "default_slot" in area
        incoming_default_slot = (area.get("default_slot") or "").strip()
        default_slot_valid = not incoming_default_slot or incoming_default_slot in KNOWN_SLOTS

        if area_id in by_area_id:
            room = by_area_id[area_id]
            touched = False
            if room.get("name") != name:
                old_name = room.get("name")
                room["name"] = name
                summary["renamed"].append(
                    {"id": room.get("id"), "area_id": area_id,
                     "from": old_name, "to": name})
                touched = True
            if incoming_slot_set and incoming_slot_set != room.get("slot_set"):
                old_slot_set = room.get("slot_set")
                room["slot_set"] = incoming_slot_set
                summary["slot_set_changed"].append(
                    {"id": room.get("id"), "area_id": area_id,
                     "from": old_slot_set, "to": incoming_slot_set})
                touched = True
            if (default_slot_present and default_slot_valid
                    and incoming_default_slot != room.get("default_slot", "")):
                old_default_slot = room.get("default_slot", "")
                room["default_slot"] = incoming_default_slot
                summary["default_slot_changed"].append(
                    {"id": room.get("id"), "area_id": area_id,
                     "from": old_default_slot, "to": incoming_default_slot})
                touched = True
            if not touched:
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
            match["name"] = name
            if incoming_slot_set and incoming_slot_set != match.get("slot_set"):
                old_slot_set = match.get("slot_set")
                match["slot_set"] = incoming_slot_set
                summary["slot_set_changed"].append(
                    {"id": match.get("id"), "area_id": area_id,
                     "from": old_slot_set, "to": incoming_slot_set})
            if (default_slot_present and default_slot_valid
                    and incoming_default_slot != match.get("default_slot", "")):
                old_default_slot = match.get("default_slot", "")
                match["default_slot"] = incoming_default_slot
                summary["default_slot_changed"].append(
                    {"id": match.get("id"), "area_id": area_id,
                     "from": old_default_slot, "to": incoming_default_slot})
            unlinked.remove(match)
            by_area_id[area_id] = match
            summary["linked"].append({"id": match.get("id"), "area_id": area_id, "name": name})
            continue

        rtype = guess(name_norm, TYPE_KEYWORDS) or slugify(name, taken_ids)
        slot_set = incoming_slot_set or guess(name_norm, SLOT_SET_KEYWORDS) or "default"
        default_slot = incoming_default_slot if default_slot_valid else ""
        rid = slugify(name, taken_ids)
        taken_ids.add(rid)

        new_room = CommentedMap()
        new_room["id"] = rid
        new_room["type"] = rtype
        new_room["slot_set"] = slot_set
        new_room["default_slot"] = default_slot
        new_room["area_id"] = area_id
        new_room["name"] = name
        new_room["slots"] = CommentedMap()
        rooms.append(new_room)
        by_area_id[area_id] = new_room
        summary["created"].append({"id": rid, "area_id": area_id, "name": name, "type": rtype, "slot_set": slot_set})

    # EN | Anything still in `unlinked` matched no incoming area — an
    # EN | orphan (see the module docstring for why that is safe to drop
    # EN | now that `incoming` is always the full, already-applied
    # EN | registry snapshot). Drop it from `rooms` too.
    # FR | Ce qui reste dans `unlinked` n a trouve aucune zone recue — une
    # FR | orpheline (voir la docstring du module pour pourquoi c est sans
    # FR | risque maintenant que `incoming` est toujours l instantane
    # FR | complet et deja applique du registre). La retirer de `rooms`
    # FR | aussi.
    if unlinked:
        orphan_ids = {id(r) for r in unlinked}
        rooms[:] = [r for r in rooms if id(r) not in orphan_ids]
        for r in unlinked:
            summary["orphaned"].append({"id": r.get("id"), "name": r.get("name")})

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
        # EN | Full snapshot of every room's current slot_set and
        # EN | default_slot, written on EVERY run regardless of what changed
        # EN | this pass (unlike the summary lists above, which only ever
        # EN | list this pass's actions). vssp_rooms_floors.html reads this to
        # EN | pre-fill each room's slot_set/default_slot <select> with the
        # EN | real value instead of always defaulting to "default"/""
        # EN | — see applyDraftSlotSets() there. default_slot is always
        # EN | present as a key, even when "" (auto) — that presence is what
        # EN | applyDraftSlotSets() uses to tell "the room has no priority
        # EN | slot" apart from "this snapshot predates default_slot".
        # FR | Instantane complet du slot_set et du default_slot actuels de
        # FR | chaque piece, ecrit a CHAQUE execution quel que soit ce qui a
        # FR | change cette passe (contrairement aux listes du resume
        # FR | ci-dessus, qui ne listent jamais que les actions de cette
        # FR | passe). vssp_rooms_floors.html lit ceci pour pre-remplir les
        # FR | <select> slot_set/default_slot de chaque piece avec la vraie
        # FR | valeur au lieu de toujours retomber sur "default"/"" — voir
        # FR | applyDraftSlotSets() la-bas. default_slot est toujours present
        # FR | comme cle, meme quand "" (auto) — cette presence est ce
        # FR | qu utilise applyDraftSlotSets() pour distinguer « la piece n a
        # FR | pas de tableau prioritaire » de « cet instantane precede
        # FR | default_slot ».
        "rooms": [
            {"id": r.get("id"), "area_id": r.get("area_id"),
             "name": r.get("name"), "slot_set": r.get("slot_set"),
             "default_slot": r.get("default_slot", "")}
            for r in model.get("rooms") or []
        ],
    }

    changed = (summary["linked"] or summary["created"] or summary["renamed"]
               or summary["slot_set_changed"] or summary["default_slot_changed"]
               or summary["removed"] or summary["orphaned"])

    if args.dry_run:
        print(f"[dry-run] {len(summary['linked'])} would be linked, "
              f"{len(summary['created'])} would be created, "
              f"{len(summary['renamed'])} would be renamed, "
              f"{len(summary['slot_set_changed'])} slot_set(s) would change, "
              f"{len(summary['default_slot_changed'])} default_slot(s) would change, "
              f"{len(summary['removed'])} would be removed, "
              f"{len(summary['orphaned'])} would be orphaned, "
              f"{summary['unchanged']} already in sync")
    elif not changed:
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
              f"{len(summary['created'])} room(s) created, "
              f"{len(summary['renamed'])} room(s) renamed, "
              f"{len(summary['slot_set_changed'])} slot_set(s) changed, "
              f"{len(summary['default_slot_changed'])} default_slot(s) changed, "
              f"{len(summary['removed'])} room(s) removed, "
              f"{len(summary['orphaned'])} room(s) orphaned")
        for r in summary["linked"]:
            print(f"       linked  {r['id']} <- {r['name']} ({r['area_id']})")
        for r in summary["created"]:
            print(f"       created {r['id']} (type={r['type']}, slot_set={r['slot_set']}) <- {r['name']}")
        for r in summary["renamed"]:
            print(f"       renamed {r['id']} ({r['area_id']}) {r['from']!r} -> {r['to']!r}")
        for r in summary["slot_set_changed"]:
            print(f"       slot_set {r['id']} ({r['area_id']}) {r['from']!r} -> {r['to']!r}")
        for r in summary["default_slot_changed"]:
            print(f"       default_slot {r['id']} ({r['area_id']}) {r['from']!r} -> {r['to']!r}")
        for r in summary["removed"]:
            print(f"       removed {r['id']} ({r['area_id']}) — area no longer in Home Assistant")
        for r in summary["orphaned"]:
            print(f"       orphaned {r['id']} ({r['name']}) — no area_id, matched no current HA area")

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
