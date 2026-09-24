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

"""Visio Sapiens — SUPPRIMER TOUS LES DASHBOARDS (bouton de l'ADMIN).

Sauvegarde d'abord tout dashboards/views/, puis supprime les dashboards
generes SAUF la console d'administration : sans elle, plus rien ne permet
de regenerer quoi que ce soit.

POURQUOI UN SCRIPT PLUTOT QU'UNE LIGNE SHELL — shell_command decoupe la
commande avec shlex avant de l'executer, ce qui RETIRE les guillemets
internes. La ligne

    sh -c "find .../views -maxdepth 1 -name '*.yaml' ! -name 'admin*.yaml' -delete"

arrivait donc a `sh` avec ses motifs nus : le shell developpait `*.yaml`
dans son propre repertoire courant avant que `find` ne le voie, find
echouait, et le bouton ne supprimait rien en silence. Un fichier Python
n'a ni guillemets a perdre ni glob a proteger.

Sortie : une ligne par fichier supprime, puis un resume. Code de retour 0
meme si rien n'etait a supprimer (le bouton n'est pas un echec parce que
les dashboards etaient deja absents), 1 seulement si la sauvegarde ou la
suppression a echoue.

Usage :
    python3 vssp_delete_dashboards.py
    python3 vssp_delete_dashboards.py --dry-run
    python3 vssp_delete_dashboards.py --views /config/dashboards/views \
        --backup-dir /config/vssp/backups --keep admin
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--views", default="/config/dashboards/views",
                     help="Dossier des dashboards generes.")
    ap.add_argument("--backup-dir", default="/config/vssp/backups",
                     help="Ou deposer la copie complete avant suppression.")
    ap.add_argument("--keep", default="admin",
                     help="Prefixe des fichiers conserves (defaut : admin, la console).")
    ap.add_argument("--dry-run", action="store_true",
                     help="Dit ce qui serait supprime, sans rien toucher.")
    args = ap.parse_args()

    views = Path(args.views)
    if not views.is_dir():
        print(f"[ERR] {views} n'existe pas — rien a supprimer.")
        return 1

    victims = sorted(p for p in views.glob("*.yaml") if not p.name.startswith(args.keep))
    kept = sorted(p.name for p in views.glob("*.yaml") if p.name.startswith(args.keep))

    if args.dry_run:
        for p in victims:
            print(f"[DRY] supprimerait {p.name}")
        print(f"[DRY] garderait {', '.join(kept) or 'rien'}")
        return 0

    if victims:
        dest = Path(args.backup_dir) / f"views_{datetime.now():%Y%m%d_%H%M%S}"
        try:
            dest.mkdir(parents=True, exist_ok=True)
            for p in views.glob("*.yaml"):
                shutil.copy2(p, dest / p.name)
        except OSError as exc:
            print(f"[ERR] sauvegarde impossible dans {dest} : {exc}")
            return 1
        print(f"[OK] sauvegarde de {len(list(dest.glob('*.yaml')))} fichier(s) dans {dest}")

    removed = 0
    for p in victims:
        try:
            p.unlink()
            removed += 1
            print(f"[OK] supprime {p.name}")
        except OSError as exc:
            print(f"[ERR] {p.name} : {exc}")
            return 1

    print(f"[OK] {removed} dashboard(s) supprime(s), conserve(s) : {', '.join(kept) or 'aucun'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
