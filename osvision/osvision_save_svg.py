#!/usr/bin/env python3
"""
OSVision V2 — Save SVG Floor Plan
===================================
Reçoit le contenu SVG via stdin ou fichier temp, le sauvegarde dans
/config/www/osvision_v2/images/floorplan.svg

Appelé par shell_command depuis HA :
  osvision_save_svg: >-
    python3 /config/osvision/osvision_save_svg.py

Le contenu SVG est lu depuis /config/osvision/floorplan_pending.svg
(écrit préalablement par le wizard via l'API HA write_file ou template).
"""

import sys
import os
from pathlib import Path

PENDING = Path("/config/osvision/floorplan_pending.svg")
OUTPUT  = Path("/config/www/osvision_v2/images/floorplan.svg")

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
