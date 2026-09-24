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


"""Visio Sapiens — RESTAURER LES DASHBOARDS SUPPRIMES (bouton de l'ADMIN).

Le bouton SUPPRIMER TOUS LES DASHBOARDS promet « une sauvegarde a ete
conservee dans /config/vssp/backups/ » — et rien, jusqu'ici, ne savait s'en
servir. Ce script est ce chainon : il remet en place ce qui manque.

MODE PAR DEFAUT : DESUPPRIMER, PAS ECRASER. Les sauvegardes sont parcourues
de la plus recente a la plus ancienne, et un fichier n'est repris que s'il
est ABSENT de views/. Consequence voulue : un dashboard regenere depuis
est laisse intact, un HOME edite a la main n'est jamais ecrase par une vieille
copie, et un fichier que seule une sauvegarde ancienne possede encore
revient quand meme (c'est le cas des pieces, quand une sauvegarde recente
a ete prise alors qu'elles avaient deja disparu). --overwrite force la
reprise complete depuis la sauvegarde la plus recente qui contient le
fichier, pour revenir en arriere apres une regeneration ratee.

Ce que ce script NE fait PAS : reconstituer le MODELE. Une piece n'existe
pour le generateur que si model/house_rooms.yaml la declare ; restaurer
kitchen.yaml rend la page a nouveau affichable, mais la prochaine
regeneration ne la reproduira pas tant que le modele ne la connait pas.
Le script le dit en clair a la fin plutot que de laisser croire le contraire.

Usage :
    python3 vssp_restore_dashboards.py
    python3 vssp_restore_dashboards.py --dry-run
    python3 vssp_restore_dashboards.py --overwrite --from views_20260924_121512
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def backup_dirs(root: Path, only: str | None) -> list[Path]:
    """EN | Backup directories, newest first (their name carries the date).
    FR | Les repertoires de sauvegarde, du plus recent au plus ancien (leur
    FR | nom porte la date)."""
    if not root.is_dir():
        return []
    dirs = [d for d in root.iterdir() if d.is_dir() and d.name.startswith("views_")]
    if only:
        dirs = [d for d in dirs if d.name == only]
    return sorted(dirs, key=lambda d: d.name, reverse=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--views", default="/config/dashboards/views",
                    help="Dossier des dashboards generes.")
    ap.add_argument("--backup-dir", default="/config/vssp/backups",
                    help="Ou chercher les sauvegardes views_<date>/.")
    ap.add_argument("--from", dest="only", default=None,
                    help="N'utiliser que cette sauvegarde (nom du dossier).")
    ap.add_argument("--overwrite", action="store_true",
                    help="Ecraser aussi les fichiers presents.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Dit ce qui serait restaure, sans rien ecrire.")
    args = ap.parse_args()

    views = Path(args.views)
    views.mkdir(parents=True, exist_ok=True)

    sources = backup_dirs(Path(args.backup_dir), args.only)
    if not sources:
        where = args.only or f"{args.backup_dir}/views_*"
        print(f"[ERR] aucune sauvegarde trouvee ({where}).")
        return 1

    # EN | Newest first, and the first copy found wins: a file restored from
    # EN | a recent backup is never overwritten by an older one.
    # FR | Du plus recent au plus ancien, et la premiere copie trouvee gagne :
    # FR | un fichier restaure depuis une sauvegarde recente n est jamais
    # FR | ecrase par une plus ancienne.
    restored, taken_from = [], {}
    for src in sources:
        for f in sorted(src.glob("*.yaml")):
            target = views / f.name
            if f.name in taken_from:
                continue
            if target.exists() and not args.overwrite:
                continue
            if args.dry_run:
                print(f"[DRY] {f.name} <- {src.name}")
            else:
                try:
                    shutil.copy2(f, target)
                except OSError as exc:
                    print(f"[ERR] {f.name} : {exc}")
                    return 1
                print(f"[OK] restaure {f.name} (depuis {src.name})")
            taken_from[f.name] = src.name
            restored.append(f.name)

    if not restored:
        print("[OK] rien a restaurer : tous les fichiers sauvegardes sont "
              "deja en place.")
        return 0

    print(f"[OK] {len(restored)} fichier(s) restaure(s) depuis "
          f"{len(set(taken_from.values()))} sauvegarde(s).")

    # EN | A restored room page is visible again but is NOT back in the model.
    # FR | Une page de piece restauree redevient visible mais n est PAS
    # FR | revenue dans le modele.
    rooms = [n for n in restored
             if not n.startswith(("home", "core", "energy", "admin"))]
    if rooms:
        print("[i] ATTENTION : ces pages sont restaurees mais le modele ne les "
              "declare peut-etre plus — la prochaine regeneration ne les "
              "reproduira pas tant que ROOMS & FLOORS n'a pas ete rejoue : "
              + ", ".join(sorted(rooms)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
