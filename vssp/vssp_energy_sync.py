#!/usr/bin/env python3
"""Visio Sapiens — synchronisation du dashboard ENERGY avec la maison réelle.

ENERGY n'est pas un dashboard de pièce : il liste TOUS les appareils
mesurés de la maison. Ce script maintient cette liste automatiquement.

Ce qu'il fait à chaque exécution :
  1. interroge Home Assistant (API REST) pour connaître les entités
     réellement présentes ;
  2. apparie les capteurs d'un même appareil (puissance + énergie) ;
  3. détecte les circuits du tableau électrique (switch.*), et le
     matériel qui les porte — les MODULES physiques et leurs voies,
     dont est dessiné le tableau électrique virtuel ;
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

# Exclusions par defaut : equipements d'infrastructure qui ne doivent pas
# apparaitre comme des consommateurs. Surchargeable par la cle `ignore:`
# de energy_devices.yaml (preservee d'un scan a l'autre) ou par --exclude.
DEFAULT_IGNORE = [r"multiprise", r"power[_\s-]?strip[_\s-]?total"]

ICON_RULES = [
    (r"aspirateur|vacuum", "mdi:vacuum"),
    (r"congel|freezer", "mdi:snowflake"),
    (r"frigo|refrigerat|fridge", "mdi:fridge"),
    (r"lave.?linge|washing", "mdi:washing-machine"),
    (r"seche.?linge|dryer", "mdi:tumble-dryer"),
    # EN | "vaiselle" with one s is a common spelling in device names.
    # FR | « vaiselle » avec un seul s est courant dans les noms d'appareils.
    (r"lave.?vais?selle|dishwash", "mdi:dishwasher"),
    (r"cave.{0,3}vin|wine|cellier", "mdi:glass-wine"),
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
def ha_get(url: str, token: str, path: str):
    req = urllib.request.Request(
        f"{url.rstrip('/')}{path}",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def ha_states(url: str, token: str) -> list[dict]:
    return ha_get(url, token, "/api/states")


# Le registre (piece, fabricant, modele) n'est pas expose par /api/states.
# On le recupere en faisant evaluer un template par Home Assistant, qui a
# acces a area_name() et device_attr(). Une seule requete pour tout le
# parc, format ligne a ligne pour rester robuste au parsing.
#
# EN | The device_id / via_device_id pair is what makes the virtual breaker
# EN | panel possible: a Shelly Power Strip 4 Gen4 appears in Home Assistant
# EN | as one PARENT device plus one child device per outlet, and a Shelly
# EN | Pro 4PM as one parent plus one child per channel. Without the parent
# EN | link, four outlets look like four unrelated plugs; with it they are
# EN | four channels of ONE module — which is what a breaker panel draws.
# FR | Le couple device_id / via_device_id est ce qui rend possible le
# FR | tableau electrique virtuel : une Shelly Power Strip 4 Gen4 apparait
# FR | dans Home Assistant comme un appareil PARENT plus un appareil enfant
# FR | par prise, et une Shelly Pro 4PM comme un parent plus un enfant par
# FR | voie. Sans le lien parent, quatre prises ressemblent a quatre prises
# FR | sans rapport ; avec lui, ce sont quatre voies d'UN module — et c'est
# FR | cela qu'un tableau electrique dessine.
#
# EN | cover.* is scanned too: a Shelly Pro Dual Cover drives shutters, so
# EN | its channels are covers, not switches.
# FR | cover.* est scanne aussi : une Shelly Pro Dual Cover pilote des
# FR | volets, ses voies sont donc des covers, pas des switches.
REGISTRY_TEMPLATE = """
{%- set ns = namespace(lines=[]) -%}
{%- for s in (states.sensor | list) + (states.switch | list) + (states.cover | list) -%}
  {%- set eid = s.entity_id -%}
  {%- set did = device_id(eid) or '' -%}
  {%- set par = (device_attr(did, 'via_device_id') or did) if did else '' -%}
  {%- set ns.lines = ns.lines + [eid ~ '|' ~ (area_name(eid) or '') ~ '|' ~
      (device_attr(eid, 'model') or '') ~ '|' ~
      (device_attr(eid, 'name_by_user') or device_attr(eid, 'name') or '') ~ '|' ~
      did ~ '|' ~ par ~ '|' ~
      (device_attr(par, 'name_by_user') or device_attr(par, 'name') or '') ~ '|' ~
      (device_attr(par, 'model') or '') ~ '|' ~
      (device_attr(eid, 'manufacturer') or '')] -%}
{%- endfor -%}
{{ ns.lines | join('\n') }}
"""


def ha_registry(url: str, token: str) -> dict[str, dict]:
    """entity_id → {area, model, device_name}, via /api/template."""
    body = json.dumps({"template": REGISTRY_TEMPLATE}).encode()
    req = urllib.request.Request(
        f"{url.rstrip('/')}/api/template", data=body,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        method="POST",
    )
    out = {}
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:300]
        print(f"⚠ Registre inaccessible (HTTP {exc.code}) — pieces et "
              f"modeles a completer manuellement.\n   Reponse HA : {body}")
        return {}
    except urllib.error.URLError as exc:
        print(f"⚠ Registre inaccessible ({exc}) — pieces et modeles a "
              f"completer manuellement.")
        return {}
    for line in text.splitlines():
        parts = line.split("|")
        # EN | 9 fields = the template above. 4 = a Home Assistant that
        # EN | answered an older template (mid-deploy). The device topology is
        # EN | then unknown, so the modules stay empty instead of invented.
        # FR | 9 champs = le template ci-dessus. 4 = un Home Assistant qui a
        # FR | repondu a un template plus ancien (deploiement en cours). La
        # FR | topologie des appareils est alors inconnue : les modules restent
        # FR | vides plutot que d'etre inventes.
        if len(parts) == 9:
            out[parts[0]] = {"area": parts[1], "model": parts[2],
                             "device_name": parts[3], "device_id": parts[4],
                             "parent_id": parts[5], "parent_name": parts[6],
                             "parent_model": parts[7], "manufacturer": parts[8]}
        elif len(parts) == 4:
            out[parts[0]] = {"area": parts[1], "model": parts[2],
                             "device_name": parts[3]}
    return out


# ── Découverte ───────────────────────────────────────────────────────
def discover(states: list[dict], registry: dict | None = None,
             ignore: list[str] | None = None) -> tuple[list[dict], list[dict]]:
    """→ (appareils mesurés, circuits du tableau électrique).

    `registry` fournit piece / modele / nom d'appareil (via /api/template).
    `ignore` est une liste d'expressions regulieres : tout entity_id ou
    nom d'appareil qui correspond est ecarte — c'est la ou l'on met les
    multiprises et autres equipements d'infrastructure que l'on ne veut
    pas voir apparaitre comme des consommateurs.
    """
    registry = registry or {}
    ignore = ignore or []

    def ignored(eid: str) -> bool:
        dname = registry.get(eid, {}).get("device_name", "")
        return any(re.search(pat, eid, re.I) or (dname and re.search(pat, dname, re.I))
                   for pat in ignore)
    powers: dict[str, str] = {}      # radical → entity_id puissance
    energies: dict[str, str] = {}    # radical → entity_id énergie cumulée
    friendly: dict[str, str] = {}    # radical → nom lisible
    areas: dict[str, str] = {}       # radical → pièce (si exposée)

    for s in states:
        eid = s["entity_id"]
        if not eid.startswith("sensor.") or excluded(eid) or ignored(eid):
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
        reg = registry.get(power_eid, {})
        # Le nom de l'APPAREIL du registre est bien meilleur que le nom du
        # capteur : « Lavelinge » plutot que « Lavelinge Puissance ».
        raw_name = reg.get("device_name") or friendly.get(stem, stem)
        name = clean_name(raw_name)
        devices.append({
            "name": name,
            "icon": guess_icon(stem + " " + raw_name),
            "model": reg.get("model", ""),      # ex: Shelly Power Strip 4 Gen4
            "room": pretty_area(reg.get("area", "")),
            "power_entity": power_eid,
            "energy_entity": energy_eid,
        })

    # Radicaux des appareils mesures : seul un switch qui pilote l'un
    # d'eux est un vrai circuit du tableau electrique.
    device_stems = {d["power_entity"].split(".", 1)[1] for d in devices}
    device_stems = {strip_suffix(o, POWER_SUFFIXES) or o for o in device_stems}

    circuits = []
    skipped_switches = []
    for s in states:
        eid = s["entity_id"]
        if not eid.startswith("switch.") or excluded(eid) or ignored(eid):
            continue
        stem = eid.split(".", 1)[1]
        reg_model = (registry.get(eid, {}).get("model") or "")
        is_circuit = (
            stem in device_stems                      # pilote un appareil mesure
            or any(stem.startswith(d + "_") for d in device_stems)
            or "shelly" in reg_model.lower()          # module Shelly identifie
        )
        if not is_circuit:
            skipped_switches.append(eid)
            continue
        attrs = s.get("attributes") or {}
        reg = registry.get(eid, {})
        raw = reg.get("device_name") or attrs.get("friendly_name",
                                                  eid.split(".", 1)[1])
        name = clean_name(raw)
        circuits.append({
            "name": name,
            # EN | `stem`, not `eid`: the domain must stay out of the match,
            # EN | or every switch.* entity hits the network-switch rule.
            # FR | `stem`, pas `eid` : le domaine doit rester hors du match,
            # FR | sinon toute entite switch.* tombe sur la regle du
            # FR | commutateur reseau.
            "icon": guess_icon(stem + " " + raw),
            "entity": eid,
            "model": reg.get("model", ""),
            "amp": "",                # calibre : a renseigner, puis preserve
        })
    circuits.sort(key=lambda c: c["entity"])
    if skipped_switches:
        print(f"  {len(skipped_switches)} interrupteur(s) ignore(s) "
              f"— pas de mesure associee, donc pas un circuit :")
        for e in skipped_switches[:8]:
            print(f"      · {e}")
        if len(skipped_switches) > 8:
            print(f"      · … et {len(skipped_switches) - 8} autre(s)")
    return devices, circuits


# ── Modules physiques du tableau electrique ────────────────────
# EN | A module is the physical box screwed onto the rail (or plugged into
# EN | the wall): Shelly Pro 4PM, Shelly Pro Dual Cover, a 4-outlet strip, a
# EN | single plug. A CHANNEL is one way out of it. The list below is what
# EN | tells a real electrical module from the dozens of other devices that
# EN | also expose a switch — an NVR with a motion-detection toggle, a NAS
# EN | with a home-mode switch, a spa with a filter cycle. Those are not part
# EN | of the electrical installation and have no place on the rail.
# FR | Un module est le boitier physique visse sur le rail (ou branche au
# FR | mur) : Shelly Pro 4PM, Shelly Pro Dual Cover, une multiprise 4 voies,
# FR | une prise simple. Une VOIE en est une sortie. La liste ci-dessous est
# FR | ce qui distingue un vrai module electrique des dizaines d'autres
# FR | appareils qui exposent eux aussi un switch — un NVR avec une bascule
# FR | de detection de mouvement, un NAS avec un mode maison, un spa avec un
# FR | cycle de filtration. Ceux-la ne font pas partie de l'installation
# FR | electrique et n'ont rien a faire sur le rail.
MODULE_MODEL_PATTERNS = (
    r"shelly", r"qubino", r"fibaro", r"sonoff", r"nodon", r"tasmota",
    r"aeotec", r"heltun", r"legrand", r"schneider", r"hager", r"eaton",
    r"finder", r"wago", r"zbmini", r"micromodule",
)

# EN | Domains that can BE a channel: something you switch, or a shutter.
# FR | Domaines qui peuvent ETRE une voie : ce qui se commande, ou un volet.
CONTROL_DOMAINS = ("switch", "cover")


def is_module_model(model: str, manufacturer: str) -> bool:
    text = f"{model} {manufacturer}".lower()
    return any(re.search(pat, text) for pat in MODULE_MODEL_PATTERNS)


def _prefix_len(a: str, b: str) -> int:
    n = 0
    for ca, cb in zip(a, b):
        if ca != cb:
            break
        n += 1
    return n


def discover_modules(states: list[dict], registry: dict | None = None,
                     ignore: list[str] | None = None) -> list[dict]:
    """→ modules physiques, chacun avec ses voies (le tableau virtuel).

    Deux topologies coexistent chez Shelly, traitees toutes les deux :
      · un appareil PARENT + un appareil enfant par voie (Power Strip 4
        Gen4, Pro 4PM recents) — le parent est le module ;
      · un seul appareil portant plusieurs entites de commande (modules
        plus anciens) — l'appareil est le module, chaque entite une voie.

    Une voie sans commande mais avec un capteur de puissance est gardee :
    c'est un module de MESURE (un compteur ajoute au tableau), et il a sa
    place sur le rail au meme titre qu'un disjoncteur.
    """
    registry = registry or {}
    ignore = ignore or []

    def ignored(eid: str, name: str) -> bool:
        return any(re.search(pat, eid, re.I) or (name and re.search(pat, name, re.I))
                   for pat in ignore)

    # 1. Capteurs de puissance / energie cumulee, indexes par appareil.
    powers: dict[str, list[str]] = {}
    energies: dict[str, list[str]] = {}
    for s in states:
        eid = s["entity_id"]
        if not eid.startswith("sensor.") or excluded(eid):
            continue
        dev = (registry.get(eid) or {}).get("device_id")
        if not dev:
            continue
        oid = eid.split(".", 1)[1]
        dclass = (s.get("attributes") or {}).get("device_class")
        if strip_suffix(oid, POWER_SUFFIXES) and dclass in (None, "power"):
            powers.setdefault(dev, []).append(eid)
        elif strip_suffix(oid, ENERGY_CUMUL_SUFFIXES) and dclass in (None, "energy"):
            energies.setdefault(dev, []).append(eid)

    def sensor_for(cands: list[str], eid: str) -> str:
        """Le capteur du meme appareil ; si l'appareil en porte plusieurs,
        celui dont l'identifiant partage le plus long prefixe avec la voie
        (cas d'un module multi-voies expose comme un seul appareil)."""
        if not cands:
            return ""
        if len(cands) == 1:
            return cands[0]
        oid = eid.split(".", 1)[1]
        return max(cands, key=lambda c: _prefix_len(c.split(".", 1)[1], oid))

    # 2. Entites de commande, groupees par appareil. En dessous de deux, le
    #    nom de l'APPAREIL nomme la voie ; au-dessus il faut le nom de
    #    l'entite, sans quoi les quatre voies porteraient le meme libelle.
    controls: dict[str, list[dict]] = {}
    for s in states:
        eid = s["entity_id"]
        if eid.split(".", 1)[0] not in CONTROL_DOMAINS or excluded(eid):
            continue
        reg = registry.get(eid) or {}
        dev = reg.get("device_id")
        if not dev or ignored(eid, reg.get("device_name", "")):
            continue
        controls.setdefault(dev, []).append(s)

    modules: dict[str, dict] = {}

    def module_of(reg: dict) -> dict:
        """Le module qui porte cette entite : son appareil parent, ou
        lui-meme quand il n'a pas de parent."""
        dev = reg.get("device_id") or ""
        mid = reg.get("parent_id") or dev
        if mid not in modules:
            standalone = mid == dev
            raw = ("" if standalone else reg.get("parent_name")) or \
                reg.get("device_name") or mid
            modules[mid] = {
                "id": mid,
                "name": clean_name(raw),
                "model": ("" if standalone else reg.get("parent_model")) or
                         reg.get("model") or "",
                "manufacturer": reg.get("manufacturer", ""),
                "room": pretty_area(reg.get("area", "")),
                "channels": [],
            }
        return modules[mid]

    for dev, entities in controls.items():
        for s in entities:
            eid = s["entity_id"]
            reg = registry.get(eid) or {}
            attrs = s.get("attributes") or {}
            raw = (attrs.get("friendly_name") if len(entities) > 1
                   else reg.get("device_name")) or \
                attrs.get("friendly_name") or eid.split(".", 1)[1]
            module_of(reg)["channels"].append({
                "name": clean_name(raw),
                "icon": guess_icon(eid.split(".", 1)[1] + " " + raw),
                "entity": eid,
                "power_entity": sensor_for(powers.get(dev, []), eid),
                "energy_entity": sensor_for(energies.get(dev, []), eid),
            })

    # 3. Mesure seule : un appareil qui mesure sans rien commander est un
    #    compteur ajoute au tableau, pas un appareil sans interet.
    for dev, cands in powers.items():
        if dev in controls:
            continue
        eid = cands[0]
        reg = registry.get(eid) or {}
        raw = reg.get("device_name") or eid.split(".", 1)[1]
        if ignored(eid, raw):
            continue
        module_of(reg)["channels"].append({
            "name": clean_name(raw),
            "icon": guess_icon(eid.split(".", 1)[1] + " " + raw),
            "entity": "",                 # rien a commander : voie de mesure
            "power_entity": eid,
            "energy_entity": sensor_for(energies.get(dev, []), eid),
        })

    out = []
    for mod in modules.values():
        measured = any(c["power_entity"] for c in mod["channels"])
        # EN | Measured, or a recognised electrical model. A device that is
        # EN | neither is a toggle on something else entirely.
        # FR | Mesure, ou modele electrique reconnu. Un appareil qui n'est ni
        # FR | l'un ni l'autre est une bascule sur tout autre chose.
        if not (measured or is_module_model(mod["model"], mod["manufacturer"])):
            continue
        mod["channels"].sort(key=lambda c: c["entity"] or c["power_entity"])
        out.append(mod)
    out.sort(key=lambda m: ((m["model"] or "").lower(), (m["name"] or "").lower()))
    return out


def pretty_area(area: str) -> str:
    """« Technical_Room » → « Technical Room »."""
    return re.sub(r"[_\-]+", " ", area).strip() if area else ""


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
# EN | A module's CHANNELS are hardware: they are always re-read from the
# EN | scan, or a Shelly Pro 4PM whose fourth channel was wired last week
# EN | would keep showing three. Only what a human typed is preserved.
# FR | Les VOIES d'un module sont du materiel : elles sont toujours reprises
# FR | du scan, sinon une Shelly Pro 4PM dont la quatrieme voie a ete cablee
# FR | la semaine derniere en afficherait toujours trois. Seul ce qu'une
# FR | personne a saisi est preserve.
PRESERVED_MODULE = ("name", "model", "room", "keep")
PRESERVED_CHANNEL = ("name", "icon", "amp")


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


def merge_modules(existing: list[dict], found: list[dict],
                  prune: bool) -> tuple[list[dict], dict]:
    """Fusion des modules : meme regle de diff que merge(), mais les voies
    sont relues du materiel a chaque scan. Les libelles saisis a la main
    (nom de module, nom et calibre d'une voie) suivent leur entite."""
    found_by_id = {m["id"]: m for m in found}
    report = {"added": [], "removed": [], "kept_offline": [], "unchanged": 0}

    def with_labels(fresh: dict, old: dict) -> dict:
        merged = dict(fresh)
        for field in PRESERVED_MODULE:
            if old.get(field):
                merged[field] = old[field]
        typed = {(c.get("entity") or c.get("power_entity")): c
                 for c in old.get("channels") or []}
        channels = []
        for chan in fresh["channels"]:
            chan = dict(chan)
            was = typed.get(chan["entity"] or chan["power_entity"]) or {}
            for field in PRESERVED_CHANNEL:
                if was.get(field):
                    chan[field] = was[field]
            channels.append(chan)
        merged["channels"] = channels
        return merged

    result = []
    for mod in existing:
        mid = mod.get("id")
        if mid in found_by_id:
            result.append(with_labels(found_by_id[mid], mod))
            report["unchanged"] += 1
        elif mod.get("keep"):
            result.append(mod)
            report["kept_offline"].append(mod.get("name", mid))
        elif prune:
            report["removed"].append(mod.get("name", mid))
        else:
            result.append(mod)
            report["removed"].append(mod.get("name", mid))

    known = {m.get("id") for m in existing}
    for fresh in found:
        if fresh["id"] not in known:
            result.append(fresh)
            report["added"].append(fresh.get("name", fresh["id"]))
    return result, report


def resolve_token(args) -> str | None:
    """Jeton : argument, puis environnement, puis fichier.

    Un jeton vide donne un 401 « Login attempt failed » cote Home
    Assistant, sans autre explication — d'ou le message explicite ici.
    """
    import os

    if args.token and args.token.strip() not in ("", "unknown", "unavailable",
                                                 "None"):
        return args.token.strip()

    env = os.environ.get("HA_TOKEN", "").strip()
    if env:
        return env

    tf = Path(args.token_file)
    if tf.exists():
        val = tf.read_text(encoding="utf-8").strip()
        if val:
            return val
        print(f"✗ {tf} est vide.")
    else:
        print(f"✗ Aucun jeton fourni et {tf} est absent.")

    print("""
  Trois façons de fournir le jeton, par ordre de priorité :

    1. En ligne de commande :   --token "eyJhbGci..."
    2. Par l'environnement  :   export HA_TOKEN="eyJhbGci..."
    3. Par fichier (recommandé pour les shell_command) :

         printf '%s' "eyJhbGci..." > /config/vssp/.ha_token
         chmod 600 /config/vssp/.ha_token

  Le jeton se crée dans Home Assistant : votre profil → onglet
  Sécurité → Jetons d'accès longue durée → Créer un jeton.
  Sa valeur ne s'affiche qu'une seule fois.

  Le fichier évite que le jeton apparaisse en clair dans les journaux
  de Home Assistant et dans la table des processus, contrairement à un
  passage par argument.
""")
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8123")
    ap.add_argument("--token", default=None,
                    help="Jeton longue durée HA. À défaut : variable "
                         "d'environnement HA_TOKEN, puis --token-file.")
    ap.add_argument("--token-file", default="/config/vssp/.ha_token",
                    help="Fichier contenant le jeton (défaut : "
                         "/config/vssp/.ha_token). Utilisé si --token et "
                         "HA_TOKEN sont absents.")
    ap.add_argument("--devices",
                    default="home-assistant/dashboards/model/energy_devices.yaml")
    ap.add_argument("--dry-run", action="store_true",
                    help="Affiche le diff sans rien écrire")
    ap.add_argument("--prune", action="store_true",
                    help="Retire réellement les appareils absents de HA")
    ap.add_argument("--exclude", action="append", default=[],
                    help="Expression reguliere d'exclusion (repetable). "
                         "S'ajoute a la cle `ignore:` du fichier devices.")
    ap.add_argument("--status-file", default=None)
    args = ap.parse_args()

    # Les exclusions sont lues AVANT le scan : elles conditionnent la
    # decouverte elle-meme, pas seulement l'affichage.
    path = Path(args.devices)
    doc = {}
    if path.exists():
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    existing_devices = doc.get("devices") or []
    existing_circuits = doc.get("circuits") or []
    existing_modules = doc.get("modules") or []
    ignore = list(doc.get("ignore") or DEFAULT_IGNORE) + list(args.exclude)

    token = resolve_token(args)
    if not token:
        return 1

    try:
        states = ha_states(args.url, token)
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        print(f"✗ Home Assistant injoignable ({args.url}) : {exc}")
        return 1

    registry = ha_registry(args.url, token)
    print(f"Registre : {len(registry)} entites documentees "
          f"(piece / modele / nom d'appareil)")
    print(f"Exclusions : {', '.join(ignore) if ignore else 'aucune'}")

    found_devices, found_circuits = discover(states, registry, ignore)

    devices, dev_report = merge(existing_devices, found_devices,
                                "power_entity", PRESERVED_DEVICE, args.prune)
    circuits, cir_report = merge(existing_circuits, found_circuits,
                                 "entity", PRESERVED_CIRCUIT, args.prune)

    found_modules = discover_modules(states, registry, ignore)
    modules, mod_report = merge_modules(existing_modules, found_modules,
                                        args.prune)

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

    n_channels = sum(len(m.get("channels") or []) for m in modules)
    print(f"MODULES    : {len(modules)} module(s), {n_channels} voie(s)")
    for n in mod_report["added"]:
        print(f"  + {n}")
    for n in mod_report["removed"]:
        print(f"  - {n}" + ("" if args.prune else "  (absent de HA)"))

    # EN | `modules` absent from the file = it predates this key. The scan
    # EN | must write even when nothing else moved, otherwise the virtual
    # EN | breaker panel stays empty until some unrelated device changes.
    # FR | `modules` absent du fichier = il est anterieur a cette cle. Le
    # FR | scan doit ecrire meme si rien d'autre n'a bouge, sans quoi le
    # FR | tableau electrique virtuel reste vide jusqu'a ce qu'un appareil
    # FR | sans rapport change.
    schema_upgrade = "modules" not in doc
    changed = bool(dev_report["added"] or cir_report["added"]
                   or mod_report["added"] or schema_upgrade
                   or (args.prune and (dev_report["removed"]
                                       or cir_report["removed"]
                                       or mod_report["removed"])))

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
        "#\n"
        "# `ignore:` = expressions regulieres d'equipements a ne jamais\n"
        "# faire apparaitre (multiprises, agregats...). Testees sur\n"
        "# l'entity_id ET sur le nom de l'appareil du registre.\n"
        "#\n"
        "# `modules:` = le materiel du tableau electrique virtuel, groupe\n"
        "# par boitier physique (Shelly Pro 4PM, Pro Dual Cover, multiprise,\n"
        "# prise). Les VOIES sont relues du materiel a chaque scan ; le nom\n"
        "# du module, le nom et le calibre d'une voie sont preserves.\n"
        f"# Derniere synchronisation : {datetime.now():%Y-%m-%d %H:%M}\n"
        "########################################################################\n"
    )
    out = header + yaml.safe_dump(
        {"ignore": ignore, "devices": devices, "circuits": circuits,
         "modules": modules},
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
            "modules": len(modules), "channels": n_channels,
            "devices_report": dev_report, "circuits_report": cir_report,
            "modules_report": mod_report,
            "changed": changed, "pruned": args.prune,
        }, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
