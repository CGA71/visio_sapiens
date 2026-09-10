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
Visio Sapiens — Save SVG Floor Plan
===================================
Reçoit le contenu SVG via stdin ou fichier temp, le sauvegarde dans
/config/www/vssp/images/floorplan.svg

Appelé par shell_command depuis HA :
  osvision_save_svg: >-
    python3 /config/vssp/vssp_save_svg.py

Le contenu SVG est lu depuis /config/vssp/floorplan_pending.svg
(écrit préalablement par le wizard via l'API HA write_file ou template).
"""

import sys
import os
from pathlib import Path

PENDING = Path("/config/vssp/floorplan_pending.svg")
OUTPUT  = Path("/config/www/vssp/images/floorplan.svg")

def main():
    if not PENDING.exists():
        print(f"Fichier source introuvable : {PENDING}", file=sys.stderr)
        sys.exit(1)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    content = PENDING.read_text(encoding="utf-8")
    OUTPUT.write_text(content, encoding="utf-8")
    PENDING.unlink()  # nettoyage
    print(f"SVG sauvegardé : {OUTPUT} ({len(content)} octets)")

if __name__ == "__main__":
    main()
