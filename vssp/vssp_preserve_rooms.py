#!/usr/bin/env python3
# ============================================================================
# Visio Sapiens — Room-state preserver across deployments
#
# EN | house.yaml's `rooms:` list stopped being purely git-authored the day
# EN | vssp_rooms_apply.py started writing to it live, from the ROOMS &
# EN | FLOORS admin form / the HA Area registry. But deploy:staging and
# EN | deploy:production both replace the whole `dashboards/` directory
# EN | wholesale on every deploy — correct for generated views, wrong for a
# EN | file that is now partly instance state. Confirmed live: a CI deploy
# EN | reverted a freshly emptied `rooms:` back to the repository's
# EN | hand-written placeholder rooms, and the next room sync then left
# EN | those placeholders behind as unlinked ghosts alongside the real ones.
# EN | This script merges just the ONE key that is pod-owned — `rooms:` —
# EN | from the previous deployment's house.yaml into the freshly deployed
# EN | one. Every other key (house.name, nav_system, room_icons,
# EN | slot_sets, locale/format...) comes from the fresh build, so a git
# EN | commit that touches those still reaches production normally — this
# EN | is NOT a whole-file preservation like house_rooms.yaml or
# EN | energy_devices.yaml, which have no build-time content worth keeping.
# FR | La liste `rooms:` de house.yaml a cesse d etre purement redigee via
# FR | Git le jour ou vssp_rooms_apply.py a commence a l ecrire en direct,
# FR | depuis le formulaire ROOMS & FLOORS / le registre Zones HA. Mais
# FR | deploy:staging et deploy:production remplacent tous deux le
# FR | dossier `dashboards/` en bloc a chaque deploiement — correct pour les
# FR | vues generees, faux pour un fichier qui est desormais en partie de
# FR | l etat d instance. Confirme en direct : un deploiement CI a fait
# FR | revenir un `rooms:` fraichement vide a la version du depot (les
# FR | pieces placeholder ecrites a la main), et la synchro suivante a
# FR | laisse ces placeholders comme fantomes non lies a cote des vraies
# FR | pieces.
# FR | Ce script fusionne UNE SEULE cle appartenant au pod — `rooms:` —
# FR | depuis le house.yaml du deploiement precedent vers celui qui vient
# FR | d etre deploye. Toutes les autres cles (house.name, nav_system,
# FR | room_icons, slot_sets, locale/format...) viennent du build frais,
# FR | donc un commit Git qui les touche atteint quand meme la production
# FR | normalement — ce n est PAS une preservation du fichier entier comme
# FR | house_rooms.yaml ou energy_devices.yaml, qui n ont aucun contenu de
# FR | build a garder.
#
# EN | Dependency: ruamel.yaml, same reason as vssp_rooms_apply.py.
# FR | Dependance : ruamel.yaml, meme raison que vssp_rooms_apply.py.
# ============================================================================
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from ruamel.yaml import YAML
except ImportError:
    sys.exit("[ERR] ruamel.yaml is missing. Install it: pip install ruamel.yaml")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True,
                    help="house.yaml from the PREVIOUS deployment "
                         "(e.g. dashboards.old/model/house.yaml)")
    ap.add_argument("--new", required=True,
                    help="house.yaml just written by this deployment, "
                         "to merge rooms: into in place")
    args = ap.parse_args()

    old_path = Path(args.old)
    new_path = Path(args.new)

    if not new_path.is_file():
        sys.exit(f"[ERR] {new_path} not found")

    # EN | No previous deployment (first-ever deploy): nothing to preserve,
    # EN | the fresh build's own rooms: (whatever the repo declares) stands.
    # FR | Aucun deploiement precedent (tout premier deploiement) : rien a
    # FR | preserver, le rooms: du build frais (ce que declare le depot)
    # FR | reste tel quel.
    if not old_path.is_file():
        print(f"[i] no previous house.yaml at {old_path} — nothing to preserve")
        return 0

    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)

    old_model = y.load(old_path.read_text(encoding="utf-8")) or {}
    old_rooms = old_model.get("rooms")
    if not old_rooms:
        print(f"[i] {old_path} declares no rooms — nothing to preserve")
        return 0

    new_model = y.load(new_path.read_text(encoding="utf-8")) or {}
    new_model["rooms"] = old_rooms

    tmp = new_path.with_suffix(".vssptmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        y.dump(new_model, fh)
    tmp.replace(new_path)

    print(f"[OK] {new_path}: preserved {len(old_rooms)} room(s) "
          f"from the previous deployment")
    return 0


if __name__ == "__main__":
    sys.exit(main())
