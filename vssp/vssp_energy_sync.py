#!/usr/bin/env python3
"""Visio Sapiens — synchronisation du dashboard ENERGY avec la maison réelle.

ENERGY n'est pas un dashboard de pièce : il liste TOUS les appareils
mesurés de la maison. Ce script maintient cette liste automatiquement.

Ce qu'il fait à chaque exécution :
  1. interroge Home Assistant (API REST) pour connaître les entités
     réellement présentes ;
  2. apparie les capteurs d'un même appareil (puissance + énergie) ;
  3. détecte les circuits du tableau électrique (switch.*) ;
  4. compare avec model/energy_devices.yaml et applique le diff :
       + nouvel appareil détecté      → ajouté
       - appareil disparu de HA       → retiré
       = appareil déjà connu          → conservé AVEC vos personnalisations
                                        (name, icon, model, ordre, amp…)
  5. n'écrit rien si le résultat est identique (pas de commit inutile).

Les totaux (jour/mois/année) n'ont PAS besoin de ce script : ils sont
calculés à l'exécution par packages/vssp_energy_totaux.yaml, qui somme
dynamiquement tous les capteurs *_puissance et *_energie. Un appareil
ajouté ou retiré y entre ou en sort tout seul, sans régénération.

Usage :
    python3 vssp/vssp_energy_sync.py --token "$HA_TOKEN"
    python3 vssp/vssp_energy_sync.py --token … --dry-run   # diff seul
    python3 vssp/vssp_energy_sync.py --token … --prune     # applique les retraits

Par prudence, les retraits ne sont PAS appliqués sans --prune : un
Shelly momentanément hors ligne ne doit pas faire disparaître sa ligne
du dashboard. Le diff les signale quand même.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import yaml

# ── Conventions de nommage (cf. packages/vssp_energy_totaux.yaml) ────
# *_puissance / *_power        → puissance instantanée (W ou kW)
# *_energie / *_energy         → compteur CUMULATIF (kWh, lifetime)
# *_energie_jour / *_energy_today → compteur journalier (exclu des scans)
POWER_SUFFIXES = ("_puissance", "_power")
ENERGY_CUMUL_SUFFIXES = ("_energie", "_energy")
ENERGY_DAILY_SUFFIXES = ("_energie_jour", "_energy_today", "_energy_daily")

# Entités techniques à ne jamais présenter comme un appareil de la maison
EXCLUDE_PATTERNS = (
    r"^sensor\.home_", r"^sensor\.solar_", r"^sensor\.grid_",
    r"^sensor\.vssp_", r"_room_power$", r"_room_energy",
    r"battery", r"_rssi", r"_signal",
)

ICON_RULES = [
    (r"aspirateur|vacuum", "mdi:vacuum"),
    (r"congel|freezer", "mdi:snowflake"),
    (r"frigo|refrigerat|fridge", "mdi:fridge"),
    (r"lave.?linge|washing", "mdi:washing-machine"),
    (r"seche.?linge|dryer", "mdi:tumble-dryer"),
    (r"lave.?vaisselle|dishwash", "mdi:dishwasher"),
    (r"four|oven", "mdi:toaster-oven"),
    (r"chauffe.?eau|ballon|boiler|ecs", "mdi:water-boiler"),
    (r"clim|air.?cond", "mdi:air-conditioner"),
    (r"alarme|alarm|verisure", "mdi:alarm"),
    (r"livebox|provider|router|box", "mdi:web"),
    (r"netgear|commutateur|switch|lan", "mdi:lan"),
    (r"synology|nas", "mdi:nas"),
    (r"piscine|pool", "mdi:pool"),
    (r"tv|television", "mdi:television"),
    (r"eclairage|lumiere|light|plafonnier", "mdi:lightbulb-on-outline"),
    (r"bureau|desk", "mdi:desk-lamp"),
    (r"prise|plug|socket", "mdi:power-socket-fr"),
]


def guess_icon(text: str) -> str:
    low = text.lower()
    for pattern, icon in ICON_RULES:
        if re.search(pattern, low):
            return icon
    return "mdi:power-plug"


def excluded(entity_id: str) -> bool:
    return any(re.search(p, entity_id) for p in EXCLUDE_PATTERNS)


def strip_suffix(object_id: str, suffixes: tuple) -> str | None:
    """Retire le suffixe reconnu → radical commun de l'appareil."""
    for suf in suffixes:
        if object_id.endswith(suf):
            return object_id[: -len(suf)]
    return None


# ── Accès Home Assistant ─────────────────────────────────────────────
def ha_states(url: str, token: str) -> list[dict]:
    req = urllib.request.Request(
        f"{url.rstrip('/')}/api/states",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


# ── Découverte ───────────────────────────────────────────────────────
def discover(states: list[dict]) -> tuple[list[dict], list[dict]]:
    """→ (appareils mesurés, circuits du tableau électrique)."""
    powers: dict[str, str] = {}      # radical → entity_id puissance
    energies: dict[str, str] = {}    # radical → entity_id énergie cumulée
    friendly: dict[str, str] = {}    # radical → nom lisible
    areas: dict[str, str] = {}       # radical → pièce (si exposée)

    for s in states:
        eid = s["entity_id"]
        if not eid.startswith("sensor.") or excluded(eid):
            continue
        oid = eid.split(".", 1)[1]
        attrs = s.get("attributes") or {}
        dev_class = attrs.get("device_class")

        # Compteur journalier : utile au dashboard mais jamais comme
        # source d'énergie cumulée (cf. note du package totaux).
        if strip_suffix(oid, ENERGY_DAILY_SUFFIXES):
            stem = strip_suffix(oid, ENERGY_DAILY_SUFFIXES)
            energies.setdefault(stem + "\x00daily", eid)
            continue

        stem_p = strip_suffix(oid, POWER_SUFFIXES)
        if stem_p and dev_class in (None, "power"):
            powers[stem_p] = eid
            friendly.setdefault(stem_p, attrs.get("friendly_name", stem_p))
            continue

        stem_e = strip_suffix(oid, ENERGY_CUMUL_SUFFIXES)
        if stem_e and dev_class in (None, "energy"):
            energies[stem_e] = eid
            friendly.setdefault(stem_e, attrs.get("friendly_name", stem_e))

    devices = []
    for stem, power_eid in sorted(powers.items()):
        # Énergie du même appareil : cumulée en priorité, sinon journalière
        energy_eid = energies.get(stem) or energies.get(stem + "\x00daily")
        if not energy_eid:
            continue  # une ligne du tableau a besoin des deux colonnes
        raw_name = friendly.get(stem, stem)
        name = clean_name(raw_name)
        devices.append({
            "name": name,
            "icon": guess_icon(stem + " " + raw_name),
            "model": "",              # complété manuellement, puis préservé
            "room": areas.get(stem, ""),
            "power_entity": power_eid,
            "energy_entity": energy_eid,
        })

    circuits = []
    for s in states:
        eid = s["entity_id"]
        if not eid.startswith("switch.") or excluded(eid):
            continue
        attrs = s.get("attributes") or {}
        name = clean_name(attrs.get("friendly_name", eid.split(".", 1)[1]))
        circuits.append({
            "name": name,
            "icon": guess_icon(eid + " " + name),
            "entity": eid,
            "model": "",
            "amp": "",
        })
    circuits.sort(key=lambda c: c["entity"])
    return devices, circuits


def clean_name(raw: str) -> str:
    """« Shelly Lave-linge Puissance » → « Lave-linge »."""
    # Les underscores d'abord : « _puissance » n'a pas de limite de mot,
    # donc sans cette étape un entity_id brut ne serait jamais nettoyé.
    n = re.sub(r"_+", " ", raw)
    n = re.sub(r"\b(puissance|power|energie|energy|today|jour|"
               r"consommation)\b", "", n, flags=re.I)
    # « Shelly » / « Technical Room » sont des préfixes techniques, mais on
    # ne supprime que le mot lui-même : « Shelly Bureau » doit rester « Bureau ».
    n = re.sub(r"\b(shelly|technical\s+room)\b", "", n, flags=re.I)
    n = re.sub(r"\s+", " ", n).strip(" -_")  # les traits d'union sont préservés
    if not n:
        return raw
    return n[:1].upper() + n[1:]


# ── Fusion non destructive ───────────────────────────────────────────
PRESERVED_DEVICE = ("name", "icon", "model", "room", "keep")
PRESERVED_CIRCUIT = ("name", "icon", "model", "amp", "keep")


def merge(existing: list[dict], found: list[dict], key: str,
          preserved: tuple, prune: bool) -> tuple[list[dict], dict]:
    """Applique le diff en gardant l'ordre et les champs personnalisés.

    Un item marqué `keep: true` n'est jamais retiré, même absent de HA
    (utile pour un appareil saisonnier ou temporairement hors ligne).
    """
    by_key = {e.get(key): e for e in existing}
    found_keys = {f[key] for f in found}
    report = {"added": [], "removed": [], "kept_offline": [], "unchanged": 0}

    result = []
    for item in existing:
        k = item.get(key)
        if k in found_keys:
            result.append(item)          # personnalisations préservées
            report["unchanged"] += 1
        elif item.get("keep"):
            result.append(item)
            report["kept_offline"].append(item.get("name", k))
        elif prune:
            report["removed"].append(item.get("name", k))
        else:
            result.append(item)
            report["removed"].append(item.get("name", k))  # signalé, non retiré

    for f in found:
        if f[key] not in by_key:
            result.append(f)
            report["added"].append(f.get("name", f[key]))
    return result, report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8123")
    ap.add_argument("--token", required=True, help="Jeton longue durée HA")
    ap.add_argument("--devices",
                    default="home-assistant/dashboards/model/energy_devices.yaml")
    ap.add_argument("--dry-run", action="store_true",
                    help="Affiche le diff sans rien écrire")
    ap.add_argument("--prune", action="store_true",
                    help="Retire réellement les appareils absents de HA")
    ap.add_argument("--status-file", default=None)
    args = ap.parse_args()

    try:
        states = ha_states(args.url, args.token)
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        print(f"✗ Home Assistant injoignable ({args.url}) : {exc}")
        return 1

    found_devices, found_circuits = discover(states)

    path = Path(args.devices)
    doc = {}
    if path.exists():
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    existing_devices = doc.get("devices") or []
    existing_circuits = doc.get("circuits") or []

    devices, dev_report = merge(existing_devices, found_devices,
                                "power_entity", PRESERVED_DEVICE, args.prune)
    circuits, cir_report = merge(existing_circuits, found_circuits,
                                 "entity", PRESERVED_CIRCUIT, args.prune)

    # Rapport lisible
    print(f"APPAREILS  : {len(devices)} au total")
    for n in dev_report["added"]:
        print(f"  + {n}")
    for n in dev_report["removed"]:
        print(f"  - {n}" + ("" if args.prune else "  (absent de HA — "
                            "--prune pour retirer, keep: true pour garder)"))
    for n in dev_report["kept_offline"]:
        print(f"  = {n}  (keep: true — conservé bien qu'absent)")

    print(f"CIRCUITS   : {len(circuits)} au total")
    for n in cir_report["added"]:
        print(f"  + {n}")
    for n in cir_report["removed"]:
        print(f"  - {n}" + ("" if args.prune else "  (absent de HA)"))

    changed = bool(dev_report["added"] or cir_report["added"]
                   or (args.prune and (dev_report["removed"]
                                       or cir_report["removed"])))

    header = (
        "########################################################################\n"
        "# Visio Sapiens — appareils du dashboard ENERGY\n"
        "#\n"
        "# Liste PLATE : ENERGY n'est pas un dashboard de piece, il affiche\n"
        "# tous les appareils mesures de la maison. `room` n'est qu'un\n"
        "# libelle de provenance.\n"
        "#\n"
        "# Maintenu par vssp/vssp_energy_sync.py — vos personnalisations\n"
        "# (name, icon, model, amp, ordre) sont preservees a chaque scan.\n"
        "# Ajoutez `keep: true` a un appareil pour qu'il ne soit jamais\n"
        "# retire, meme temporairement absent de Home Assistant.\n"
        f"# Derniere synchronisation : {datetime.now():%Y-%m-%d %H:%M}\n"
        "########################################################################\n"
    )
    out = header + yaml.safe_dump(
        {"devices": devices, "circuits": circuits},
        allow_unicode=True, sort_keys=False, default_flow_style=False)

    if args.dry_run:
        print("\n(--dry-run : aucun fichier écrit)")
    elif not changed and path.exists() and existing_devices:
        print("\n= Aucun changement — fichier laissé tel quel.")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(out, encoding="utf-8")
        print(f"\n✓ {path} mis à jour — lancez generate_dashboards.py "
              "pour régénérer ENERGY.")

    if args.status_file:
        Path(args.status_file).parent.mkdir(parents=True, exist_ok=True)
        Path(args.status_file).write_text(json.dumps({
            "ok": True, "timestamp": datetime.now().isoformat(timespec="seconds"),
            "devices": len(devices), "circuits": len(circuits),
            "devices_report": dev_report, "circuits_report": cir_report,
            "changed": changed, "pruned": args.prune,
        }, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
