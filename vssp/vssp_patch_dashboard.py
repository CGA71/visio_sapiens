#!/usr/bin/env python3
"""
Visio Sapiens — Patch Dashboard
================================
Lit /config/vssp/floorplan_config.json (généré par le wizard),
puis met à jour la zone "floor" dans /config/dashboards/home.yaml :
  - remplace les éléments picture-elements existants par les nouveaux
    overlays de température/appareils générés à partir de la config
  - met à jour l'image vers /local/vssp/images/floorplan.svg
  - recharge Lovelace via l'API HA

Usage (shell_command HA) :
  python3 /config/vssp/vssp_patch_dashboard.py
"""

import json
import sys
import re
import os
import urllib.request
import urllib.error
from pathlib import Path

CONFIG_PATH    = Path("/config/vssp/floorplan_config.json")
DASHBOARD_PATH = Path("/config/dashboards/home.yaml")
BACKUP_DIR     = Path("/config/vssp/backups")
HA_URL         = "http://localhost:8123"
TOKEN_PATH     = Path("/config/vssp/.ha_token")


def get_token():
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text().strip()
    return os.environ.get("HA_TOKEN", "")


def ha_post(path, data=None):
    token = get_token()
    url = f"{HA_URL}/api/{path}"
    body = json.dumps(data or {}).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"HA API {path}: {e.code}", file=sys.stderr)
        return None


def build_elements(config):
    """Génère les éléments picture-elements depuis la config du wizard."""
    elements = []
    devices = config.get("devices", [])
    house   = config.get("house", {})

    # Regrouper les appareils par pièce
    by_room = {}
    for d in devices:
        room = d.get("room")
        if room:
            by_room.setdefault(room, []).append(d)

    # Calculer les positions % par pièce selon l'étage
    floors  = house.get("floors", [])
    exteriors = house.get("exteriors", [])

    floor_count = len(floors) + (1 if exteriors else 0)
    if floor_count == 0:
        return elements

    # Position Y de départ pour chaque étage (approximative, 0-100%)
    floor_y_starts = []
    for fi in range(floor_count):
        floor_y_starts.append(5 + fi * (90 / floor_count))

    floor_h_pct = 85 / floor_count

    # Parcourir les pièces et générer les overlays
    for fi, floor in enumerate(floors):
        rooms = [r for r in floor.get("rooms", []) if r.get("name")]
        if not rooms:
            continue
        room_count = len(rooms)
        y_start = floor_y_starts[fi]

        for ri, room in enumerate(rooms):
            name = room["name"]
            # Position X centrée sur la pièce
            x_pct = (ri + 0.5) / room_count * 45  # moitié gauche = RDC
            y_pct = y_start + floor_h_pct * 0.5

            # Label nom de la pièce
            elements.append({
                "type": "state-label",
                "entity": "sensor.date",  # entité stable, on masque la valeur
                "prefix": name.upper(),
                "suffix": " ",
                "style": {
                    "top": f"{y_pct - 4:.1f}%",
                    "left": f"{x_pct:.1f}%",
                    "color": "#00E5FF",
                    "font-size": "10px",
                    "font-weight": "600",
                    "letter-spacing": "1px",
                    "background": "transparent",
                    "border": "none",
                    "white-space": "nowrap",
                },
                "card_mod": {"style": ".state { display: none; }"},
            })

            # Température si capteur disponible
            temp_entity = f"sensor.{name.lower().replace(' ', '_')}_temperature"
            elements.append({
                "type": "state-label",
                "entity": temp_entity,
                "prefix": "🌡 ",
                "suffix": "°C",
                "style": {
                    "top": f"{y_pct:.1f}%",
                    "left": f"{x_pct:.1f}%",
                    "color": "#00E5FF",
                    "font-size": "11px",
                    "font-weight": "bold",
                    "background": "rgba(0,229,255,0.12)",
                    "border": "1px solid rgba(0,229,255,0.4)",
                    "border-radius": "6px",
                    "padding": "2px 6px",
                    "white-space": "nowrap",
                },
            })

    return elements


def elements_to_yaml(elements, indent=10):
    """Convertit la liste d'éléments en YAML minimal."""
    pad = " " * indent
    pad2 = " " * (indent + 2)
    pad4 = " " * (indent + 4)
    lines = []
    for el in elements:
        lines.append(f"{pad}- type: {el['type']}")
        for k, v in el.items():
            if k == "type":
                continue
            if isinstance(v, dict):
                lines.append(f"{pad2}{k}:")
                for sk, sv in v.items():
                    if isinstance(sv, dict):
                        lines.append(f"{pad4}{sk}:")
                        for ssk, ssv in sv.items():
                            lines.append(f"{pad4}  {ssk}: {ssv}")
                    else:
                        sv_str = f'"{sv}"' if isinstance(sv, str) and " " in sv else sv
                        lines.append(f"{pad4}{sk}: {sv_str}")
            else:
                v_str = f'"{v}"' if isinstance(v, str) and (" " in v or "%" in v) else v
                lines.append(f"{pad2}{k}: {v_str}")
    return "\n".join(lines)


def patch_dashboard(elements_yaml):
    """Remplace le bloc picture-elements dans home.yaml."""
    text = DASHBOARD_PATH.read_text(encoding="utf-8")

    # Backup
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = BACKUP_DIR / f"home_{ts}.yaml"
    backup.write_text(text, encoding="utf-8")
    print(f"Backup : {backup}")

    new_floor_block = f"""      - type: picture-elements
        view_layout:
          grid-area: floor
        image: /local/vssp/images/floorplan.svg
        card_mod:
          style: |
            ha-card {{
              background: transparent !important;
              border: none !important;
              box-shadow: none !important;
              max-height: calc(100vh - 220px);
              height: calc(100vh - 220px);
              overflow: hidden;
            }}
            img {{
              width: 100% !important;
              height: 100% !important;
              object-fit: contain;
              object-position: left top;
            }}
        elements:
{elements_yaml}"""

    # Remplacer le bloc picture-elements existant
    pattern = re.compile(
        r"      - type: picture-elements\s+view_layout:\s+grid-area: fl(?:oor|oorplan).*?"
        r"(?=\n      - type:|\n      # ---|\Z)",
        re.DOTALL
    )
    if pattern.search(text):
        new_text = pattern.sub(new_floor_block + "\n", text, count=1)
        print("Bloc picture-elements remplacé.")
    else:
        print("Bloc picture-elements non trouvé, insertion impossible.", file=sys.stderr)
        sys.exit(1)

    DASHBOARD_PATH.write_text(new_text, encoding="utf-8")
    print(f"Dashboard mis à jour : {DASHBOARD_PATH}")


def reload_lovelace():
    result = ha_post("services/lovelace/reload")
    if result is not None:
        print("Lovelace rechargé.")
    else:
        print("Rechargement Lovelace échoué (API), recharge manuellement.", file=sys.stderr)


def main():
    if not CONFIG_PATH.exists():
        print(f"Config introuvable : {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    print(f"Config chargée : {len(config.get('devices', []))} appareils assignés")

    elements = build_elements(config)
    print(f"Éléments générés : {len(elements)}")

    elements_yaml = elements_to_yaml(elements)
    patch_dashboard(elements_yaml)
    reload_lovelace()
    print("✅ Dashboard patché et rechargé.")


if __name__ == "__main__":
    main()
