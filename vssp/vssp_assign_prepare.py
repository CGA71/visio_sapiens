#!/usr/bin/env python3
# ============================================================================
# Visio Sapiens — Assignment data builder
#
# EN | Reads what the discovery scan found (report.json) and what the home
# EN | model already declares (house.yaml), and writes ONE json the assignment
# EN | form can consume: /config/www/vssp/assign_data.json, served to the
# EN | browser as /local/vssp/assign_data.json.
# FR | Lit ce que le scan de decouverte a trouve (report.json) et ce que le
# FR | modele de la maison declare deja (house.yaml), puis ecrit UN seul json
# FR | que le formulaire d assignation peut consommer :
# FR | /config/www/vssp/assign_data.json, servi au navigateur comme
# FR | /local/vssp/assign_data.json.
#
# EN | WHY A SEPARATE FILE RATHER THAN READING report.json DIRECTLY
# EN | report.json lives in /config/vssp/, which Home Assistant does not
# EN | serve. Only /config/www/ is reachable from a browser, as /local/.
# EN | Copying it would also lose the current assignment, and the form needs
# EN | both: what exists, and where each device already sits. A device that is
# EN | already assigned must show its room and slot preselected, otherwise
# EN | every scan would silently reset the work done before it.
# FR | POURQUOI UN FICHIER SEPARE PLUTOT QUE LIRE report.json DIRECTEMENT
# FR | report.json vit dans /config/vssp/, que Home Assistant ne sert pas.
# FR | Seul /config/www/ est joignable depuis un navigateur, sous /local/.
# FR | Le recopier perdrait aussi l assignation courante, et le formulaire a
# FR | besoin des deux : ce qui existe, et ou chaque appareil se trouve deja.
# FR | Un appareil deja assigne doit afficher sa piece et son tableau
# FR | preselectionnes, sinon chaque scan reinitialiserait en silence le
# FR | travail precedent.
#
# EN | USAGE / FR | UTILISATION
#   python3 vssp_assign_prepare.py \
#       --report  /config/vssp/report.json \
#       --model   /config/dashboards/model/house.yaml \
#       --locales /config/dashboards/locales \
#       --out     /config/www/vssp/assign_data.json
#
# EN | Read-only on the model. Writes only the json.
# FR | Lecture seule sur le modele. N ecrit que le json.
# ============================================================================
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required")

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import vssp_i18n
except ImportError:
    vssp_i18n = None

# EN | Canonical slot order, same list as generate_dashboards.py.
# FR | Ordre canonique des tableaux, meme liste que generate_dashboards.py.
SLOTS = ["sensors", "switches", "appliances", "security", "infrastructure"]

DEFAULT_SLOT_SETS = {
    "default":       ["sensors", "switches", "appliances", "security"],
    "toilet":        ["sensors", "switches"],
    "garden":        ["sensors", "switches", "appliances", "security"],
    "utility":       ["sensors", "switches", "appliances", "security"],
    "entrance":      ["switches", "security"],
    "minimal":       ["switches", "security"],
    # EN | Server, network switch, ISP box, firewall — no HA domain or
    # EN | device_class reliably tells this apart from an ordinary sensor or
    # EN | switch, so unlike every other slot this one has no automatic
    # EN | suggestion in DEVICE_CLASS_HINT/DOMAIN_HINT below: the admin picks
    # EN | it by hand in the assignment form.
    # FR | Serveur, switch reseau, box FAI, firewall — aucun domaine ni
    # FR | device_class Home Assistant ne distingue fiablement cela d un
    # FR | capteur ou interrupteur ordinaire, donc contrairement a tout autre
    # FR | tableau celui-ci n a pas de suggestion automatique dans
    # FR | DEVICE_CLASS_HINT/DOMAIN_HINT ci-dessous : l administrateur le
    # FR | choisit a la main dans le formulaire d assignation.
    "computer_room": ["sensors", "switches", "infrastructure", "security"],
}

# EN | Suggested slot per Home Assistant domain. A SUGGESTION only: the form
# EN | preselects it and the user overrides freely. Guessing is useful because
# EN | assigning eighty entities by hand is what makes people give up; being
# EN | only a suggestion is what keeps the guess from being harmful.
# FR | Tableau suggere par domaine Home Assistant. Une SUGGESTION uniquement :
# FR | le formulaire la preselectionne et l utilisateur la remplace librement.
# FR | Deviner est utile car assigner quatre-vingts entites a la main est ce
# FR | qui fait abandonner ; n etre qu une suggestion est ce qui empeche la
# FR | supposition de nuire.
# EN | Suggested slot per device_class. Checked BEFORE the domain, because a
# EN | device_class is far more specific: `cover` alone could be a shutter, a
# EN | garage door or a curtain, while `shutter` is unambiguous. And
# EN | media_player splits into two different slots — `tv` and `receiver` are
# EN | appliances, `speaker` is audio — which the domain can never tell apart.
# FR | Tableau suggere par device_class. Consulte AVANT le domaine, car un
# FR | device_class est bien plus specifique : `cover` seul peut etre un volet,
# FR | une porte de garage ou un rideau, alors que `shutter` est sans
# FR | ambiguite. Et media_player se scinde en deux tableaux differents — `tv`
# FR | et `receiver` sont des appareils, `speaker` est de l audio — ce que le
# FR | domaine ne peut jamais distinguer.
DEVICE_CLASS_HINT = {
    "temperature": "sensors", "humidity": "sensors", "pressure": "sensors",
    "carbon_dioxide": "sensors", "pm25": "sensors", "battery": "sensors",
    "shutter": "switches", "blind": "switches", "curtain": "switches",
    "awning": "switches", "shade": "switches",
    "garage": "appliances", "door": "security", "window": "security",
    "motion": "security", "occupancy": "security", "smoke": "security",
    "gas": "security", "moisture": "security", "safety": "security",
    "lock": "security", "tamper": "security", "sound": "security",
    "tv": "appliances", "receiver": "appliances", "speaker": "appliances",
    "outlet": "appliances", "switch": "appliances",
    "power": "appliances", "energy": "appliances",
}

DOMAIN_HINT = {
    "climate": "sensors",
    "water_heater": "sensors",
    "light": "switches",
    "switch": "appliances",
    # EN | Ventilation (VMC): grouped with the environmental readings it
    # EN | affects, not with the general appliances catch-all.
    # FR | Ventilation (VMC) : regroupe avec les mesures environnementales
    # FR | qu elle influence, pas avec le fourre-tout appareils.
    "fan": "sensors",
    "vacuum": "appliances",
    "humidifier": "appliances",
    "media_player": "appliances",
    "cover": "switches",
    "alarm_control_panel": "security",
    "camera": "security",
    "lock": "security",
    "binary_sensor": "security",
    "sensor": "sensors",
}


def load_json(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def extract_entities(report) -> list:
    """
    EN | Pulls the entity list out of report.json.
    EN | The shape vssp_discovery.py actually writes is
    EN |   {area_id: {"name": ..., "entities_by_device_class": {dc: [entity]}}}
    EN | so that is handled first and explicitly. The looser fallbacks below
    EN | exist because this format has already changed once, and a form that
    EN | silently shows zero device on a key rename is worse than one that
    EN | fails loudly.
    FR | Extrait la liste des entites de report.json.
    FR | La forme que vssp_discovery.py ecrit reellement est
    FR |   {area_id: {"name": ..., "entities_by_device_class": {dc: [entite]}}}
    FR | elle est donc traitee en premier et explicitement. Les replis plus
    FR | souples ci-dessous existent car ce format a deja change une fois, et
    FR | un formulaire qui affiche zero appareil en silence sur un renommage de
    FR | cle est pire qu un formulaire qui echoue franchement.
    """
    out, seen = [], set()

    def add(item, area_id="", area_name="", device_class=""):
        if isinstance(item, str):
            eid, name = item, item
        elif isinstance(item, dict):
            eid = (item.get("entity_id") or item.get("entity")
                   or item.get("id") or "")
            name = (item.get("friendly_name") or item.get("name") or eid)
        else:
            return
        if not eid or eid in seen:
            return
        seen.add(eid)
        # EN | The discovery script writes "(domaine: light)" when the entity
        # EN | has no device_class. That is a label, not a class — keep it out.
        # FR | Le script de decouverte ecrit « (domaine: light) » quand
        # FR | l entite n a pas de device_class. C est un libelle, pas une
        # FR | classe — ne pas le retenir.
        dc = "" if device_class.startswith("(") else device_class
        out.append({"entity_id": eid, "name": name, "area": area_id,
                    "area_name": area_name, "device_class": dc})

    # EN | The real format: area_id -> entities_by_device_class
    # FR | Le format reel : area_id -> entities_by_device_class
    if isinstance(report, dict) and any(
            isinstance(v, dict) and "entities_by_device_class" in v
            for v in report.values()):
        for area_id, block in report.items():
            if not isinstance(block, dict):
                continue
            area_name = block.get("name") or area_id
            for dc, items in (block.get("entities_by_device_class") or {}).items():
                for item in items or []:
                    add(item, area_id, area_name, str(dc))
        return out

    # EN | Fallbacks / FR | Replis
    if isinstance(report, list):
        for item in report:
            add(item)
    elif isinstance(report, dict):
        for key in ("entities", "devices", "results", "items"):
            value = report.get(key)
            if isinstance(value, list):
                for item in value:
                    add(item)
                return out
            if isinstance(value, dict):
                for area, items in value.items():
                    for item in (items or []):
                        add(item, area, area)
                return out
        for area, items in report.items():
            if isinstance(items, list):
                for item in items:
                    add(item, area, area)
    return out


def current_assignment(model: dict) -> dict:
    """
    EN | entity_id -> {room, slot} as the model declares it today.
    FR | entity_id -> {room, slot} tel que le modele le declare
    FR | aujourd hui.
    """
    where = {}
    for room in (model.get("rooms") or []):
        rid = room.get("id")
        for slot_id, value in (room.get("slots") or {}).items():
            for ent in (value or []):
                where[ent] = {"room": rid, "slot": slot_id}
    return where


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default="/config/vssp/report.json")
    ap.add_argument("--model", default="/config/dashboards/model/house.yaml")
    ap.add_argument("--locales", default="/config/dashboards/locales")
    ap.add_argument("--out", default="/config/www/vssp/assign_data.json")
    args = ap.parse_args()

    model = yaml.safe_load(Path(args.model).read_text(encoding="utf-8")) or {}
    house = model.get("house") or {}
    locale = house.get("locale") or "en"

    labels = {"room": {}, "slot": {}}
    if vssp_i18n is not None:
        try:
            cat = vssp_i18n.load_catalog(locale, Path(args.locales))
            labels["room"] = cat.get("room") or {}
            labels["slot"] = cat.get("slot") or {}
        except (FileNotFoundError, ValueError) as exc:
            print(f"[warn] catalogue unavailable, raw ids will be shown: {exc}")

    slot_sets = {**DEFAULT_SLOT_SETS, **(model.get("slot_sets") or {})}

    rooms = []
    for room in (model.get("rooms") or []):
        rid = room.get("id")
        rtype = room.get("type", rid)
        label = labels["room"].get(rtype, rtype)
        if room.get("index"):
            label = f"{label} {room['index']}"
        # EN | A room synced from the HA Area registry carries its live
        # EN | name (see vssp_rooms_apply.py) — preferred over the generic
        # EN | type label so this dropdown matches the navigation rail
        # EN | instead of showing a different name for the same room.
        # FR | Une piece synchronisee depuis le registre Zones HA porte son
        # FR | nom en direct (voir vssp_rooms_apply.py) — prefere au libelle
        # FR | generique de type pour que ce menu deroulant corresponde au
        # FR | bandeau de navigation au lieu d afficher un nom different pour
        # FR | la meme piece.
        label = room.get("name") or label
        set_name = room.get("slot_set", "default")
        rooms.append({
            "id": rid,
            "label": label,
            "slot_set": set_name,
            # EN | Only the slots this room may hold. The form uses this to
            # EN | narrow the slot list per room, so an invalid pair such as a
            # EN | shutter in a garden simply cannot be selected — cheaper
            # EN | than validating it afterwards and explaining the refusal.
            # FR | Uniquement les tableaux que cette piece peut porter. Le
            # FR | formulaire s en sert pour restreindre la liste par piece,
            # FR | donc une paire invalide comme un volet dans le jardin ne
            # FR | peut simplement pas etre selectionnee — moins couteux que
            # FR | de la valider apres coup et d expliquer le refus.
            "slots": slot_sets.get(set_name, SLOTS),
        })

    # EN | area_id -> room id, so a discovered entity can propose its room.
    # FR | area_id -> id de piece, pour qu une entite decouverte propose sa piece.
    area_to_room = {}
    for room in (model.get("rooms") or []):
        rid = room.get("id")
        area_to_room[room.get("area_id") or rid] = rid

    assigned = current_assignment(model)
    entities = []
    for ent in extract_entities(load_json(Path(args.report))):
        eid = ent["entity_id"]
        domain = eid.split(".", 1)[0]
        cur = assigned.get(eid, {})
        dc = ent.get("device_class") or ""
        hint = DEVICE_CLASS_HINT.get(dc) or DOMAIN_HINT.get(domain, "appliances")
        # EN | The report groups entities by Home Assistant area, and the model
        # EN | records an area_id per room. When they match, the room is
        # EN | preselected: that is the difference between assigning eighty
        # EN | devices and confirming eighty devices.
        # FR | Le rapport groupe les entites par zone Home Assistant, et le
        # FR | modele enregistre un area_id par piece. Quand ils correspondent,
        # FR | la piece est preselectionnee : c est la difference entre
        # FR | assigner quatre-vingts appareils et en confirmer quatre-vingts.
        suggested_room = area_to_room.get(ent.get("area", ""), "")
        entities.append({
            "entity_id": eid,
            "name": ent["name"],
            "domain": domain,
            "area": ent.get("area", ""),
            "room": cur.get("room", ""),
            "slot": cur.get("slot", ""),
            "device_class": dc,
            "area_name": ent.get("area_name", ""),
            "suggested_slot": hint,
            "suggested_room": suggested_room,
            "assigned": bool(cur),
        })
    entities.sort(key=lambda e: (not e["assigned"], e["domain"], e["name"].lower()))

    payload = {
        "locale": locale,
        "slots": SLOTS,
        "slot_labels": {s: labels["slot"].get(s, s) for s in SLOTS},
        "rooms": rooms,
        "entities": entities,
        "counts": {
            "total": len(entities),
            "assigned": sum(1 for e in entities if e["assigned"]),
        },
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"[OK] {out}: {len(entities)} entity(ies), "
          f"{payload['counts']['assigned']} already assigned, "
          f"{len(rooms)} room(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
