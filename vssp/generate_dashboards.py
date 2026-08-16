#!/usr/bin/env python3
"""
Visio Sapiens dashboard generator.

EN | USAGE
FR | UTILISATION
    # EN | from the repo root (defaults match the tree)
    # FR | depuis la racine du repo (defauts alignes sur l'arborescence)
    python3 vssp/generate_dashboards.py                    # publish
    python3 vssp/generate_dashboards.py --locale fr        # French deliverable
    python3 vssp/generate_dashboards.py --format both      # tablet + mobile
    python3 vssp/generate_dashboards.py --preview          # isolated TEST dashboard
    python3 vssp/generate_dashboards.py --dry-run          # validation only
    # EN | or on the HA pod (see vssp/vssp_admin_config.yaml):
    # FR | ou sur le pod HA (voir vssp/vssp_admin_config.yaml) :
    python3 /config/vssp/generate_dashboards.py --model ... --templates ... --out ...

EN | PIPELINE (step 5 of the admin process)
FR | CHAINE (etape 5 du processus admin)
    house.yaml (home model) + locales/<code>.yaml + *.yaml.j2
        -> dashboards/views/*.yaml

EN | The render is validated (parsable YAML, !include tags tolerated) BEFORE
EN | the target file is overwritten: a broken dashboard is never deployed.
EN | Designed to be called by a Home Assistant shell_command at the end of the
EN | scan/assignment process.
FR | Le rendu est valide (YAML parsable, tags !include toleres) AVANT
FR | d'ecraser le fichier cible : jamais de dashboard casse deploye.
FR | Pense pour etre appele par un shell_command Home Assistant a la fin du
FR | processus scan/assignation.
"""
import argparse
import json
import re
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound

# EN | The i18n engine lives next to this script, whether the repo root or
# EN | /config/vssp/ is the working directory.
# FR | Le moteur i18n vit a cote de ce script, que le repertoire courant soit la
# FR | racine du repo ou /config/vssp/.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vssp_i18n  # noqa: E402

# ----------------------------------------------------------------------------
# EN | SYSTEM DASHBOARDS — the four mandatory ones. They depend on no room and
# EN | therefore never go through the room create/modify/delete form. They are
# EN | generated from the ADMIN console.
# FR | DASHBOARDS SYSTEME — les quatre obligatoires. Ils ne dependent d'aucune
# FR | piece et ne passent donc jamais par le formulaire de creation/
# FR | modification/suppression des pieces. Ils se generent depuis la console
# FR | ADMIN.
# ----------------------------------------------------------------------------
SYSTEM_DASHBOARDS = [
    ("home",   "home.yaml.j2",   "home.yaml",   {"active_nav": "home"}),
    ("core",   "core.yaml.j2",   "core.yaml",   {"active_nav": "core"}),
    ("energy", "energy.yaml.j2", "energy.yaml", {"active_nav": "energy"}),
    ("admin",  "admin.yaml.j2",  "admin.yaml",  {"active_nav": "admin"}),
]

# EN | One shared template renders every room. The differences live in the
# EN | data (slot set, device lists), never in a second template.
# FR | Un unique template partage rend toutes les pieces. Les differences
# FR | vivent dans la donnee (jeu de tableaux, listes d'appareils), jamais dans
# FR | un second template.
ROOM_TEMPLATE = "room.yaml.j2"

# EN | Canonical slot order. The identifier is used as the key in house.yaml,
# EN | as the CSS grid-area and as the section name in the template — the three
# EN | must be the same string. Never translated; only slot.<id> labels are.
# FR | Ordre canonique des tableaux. L'identifiant sert de cle dans house.yaml,
# FR | de grid-area CSS et de nom de section dans le template — les trois
# FR | doivent etre la meme chaine. Jamais traduit ; seuls les libelles
# FR | slot.<id> le sont.
SLOTS = ["climate", "lights", "appliances", "shutters", "security", "audio"]

# EN | Slot sets. `default` applies unless the room says otherwise.
# FR | Jeux de tableaux. `default` s'applique sauf mention contraire.
DEFAULT_SLOT_SETS = {
    "default": SLOTS,
    "toilet":  ["climate", "lights", "shutters", "audio"],
    "garden":  ["climate", "lights", "appliances", "security", "audio"],
}

# EN | At most one Visio Sapiens filler animation per dashboard, on the first
# EN | slot of this list that is in the room's set and holds no device.
# FR | Au plus une animation Visio Sapiens de remplissage par dashboard, sur le
# FR | premier tableau de cette liste appartenant au jeu de la piece et ne
# FR | contenant aucun appareil.
FILLER_PRIORITY = ["shutters", "audio"]

T_PLACEHOLDER = re.compile(r"__T:[A-Za-z0-9_.]+__")


class HaLoader(yaml.SafeLoader):
    """
    EN | SafeLoader tolerating Home Assistant tags (!include, etc.).
    FR | SafeLoader qui tolere les tags Home Assistant (!include, etc.).
    """


for _tag in ("!include", "!include_dir_list", "!include_dir_named",
             "!include_dir_merge_list", "!include_dir_merge_named",
             "!secret", "!env_var", "!input"):
    HaLoader.add_constructor(_tag, lambda loader, node: node.value)


# ----------------------------------------------------------------------------
# EN | Model validation
# FR | Validation du modele
# ----------------------------------------------------------------------------
def validate_model(model: dict) -> tuple[list, list]:
    """
    EN | Business checks — returns (blocking errors, warnings).
    FR | Controles metier — renvoie (erreurs bloquantes, avertissements).
    """
    errors: list = []
    warnings: list = []
    seen_entities = {}

    for d in model.get("energy_devices", []):
        # EN | Blocking: without these fields the card cannot render.
        # FR | Bloquant : sans ces champs, la carte ne peut pas s'afficher.
        for field in ("name", "icon", "power_entity", "energy_entity"):
            if not d.get(field):
                errors.append(f"Device \u00ab {d.get('name', '?')} \u00bb: "
                              f"missing field `{field}`")
        # EN | Informative: the model comes from the HA registry when available,
        # EN | otherwise it stays to be filled in — not a reason to refuse the
        # EN | whole dashboard.
        # FR | Informatif : le modele vient du registre HA quand il est
        # FR | disponible, sinon il reste a completer — ce n'est pas une raison
        # FR | de refuser tout le dashboard.
        if not d.get("model"):
            warnings.append(f"Device \u00ab {d.get('name', '?')} \u00bb: "
                            f"unknown model")
        ent = d.get("power_entity")
        if ent in seen_entities:
            errors.append(f"Entity {ent} listed twice "
                          f"(\u00ab {seen_entities[ent]} \u00bb and "
                          f"\u00ab {d.get('name')} \u00bb)")
        seen_entities[ent] = d.get("name")

    for c in model.get("circuits", []):
        for field in ("name", "icon", "entity"):
            if not c.get(field):
                errors.append(f"Circuit \u00ab {c.get('name', '?')} \u00bb: "
                              f"missing field `{field}`")
        # EN | The rating is never auto-discoverable: it is read off the
        # EN | breaker. Reported, never blocking.
        # FR | Le calibre n'est jamais decouvrable automatiquement : il se lit
        # FR | sur le disjoncteur. Signale, jamais bloquant.
        if not c.get("amp"):
            warnings.append(f"Circuit \u00ab {c.get('name', '?')} \u00bb: "
                            f"rating (amp) to fill in")

    # EN | Rooms: an unknown slot would silently never be rendered.
    # FR | Pieces : un tableau inconnu ne serait jamais rendu, en silence.
    slot_sets = {**DEFAULT_SLOT_SETS, **(model.get("slot_sets") or {})}
    seen_ids = set()
    for room in model.get("rooms", []) or []:
        rid = room.get("id")
        if not rid:
            errors.append("A room has no `id`")
            continue
        if rid in seen_ids:
            errors.append(f"Room id `{rid}` declared twice")
        seen_ids.add(rid)
        set_name = room.get("slot_set", "default")
        if set_name not in slot_sets:
            errors.append(f"Room `{rid}`: unknown slot set `{set_name}` "
                          f"(known: {', '.join(sorted(slot_sets))})")
        for slot_id in (room.get("slots") or {}):
            if slot_id not in SLOTS:
                errors.append(f"Room `{rid}`: unknown slot `{slot_id}` "
                              f"(known: {', '.join(SLOTS)})")

    return errors, warnings


# ----------------------------------------------------------------------------
# EN | Room and navigation composition
# FR | Composition des pieces et de la navigation
# ----------------------------------------------------------------------------
def normalise_slots(room: dict, slot_sets: dict) -> dict:
    """
    EN | Turns a room's raw slots into what the template consumes. Every slot in
    EN | the room's set is present in the output, with an explicit `state`:
    EN |   filled    — holds at least one device
    EN |   empty     — belongs to the set but holds nothing yet -> slot.empty
    EN |   filler    — empty, and carries the Visio Sapiens animation
    EN | Slots outside the set are absent entirely: the template collapses them
    EN | and lets neighbours expand.
    FR | Transforme les tableaux bruts d'une piece en ce que le template
    FR | consomme. Chaque tableau du jeu de la piece est present en sortie, avec
    FR | un `state` explicite :
    FR |   filled    — contient au moins un appareil
    FR |   empty     — appartient au jeu mais ne contient encore rien -> slot.empty
    FR |   filler    — vide, et porte l'animation Visio Sapiens
    FR | Les tableaux hors du jeu sont totalement absents : le template les
    FR | effondre et laisse les voisins s'etendre.
    """
    set_name = room.get("slot_set", "default")
    candidates = slot_sets.get(set_name, SLOTS)
    raw = room.get("slots") or {}

    out = {}
    for slot_id in SLOTS:
        if slot_id not in candidates:
            continue
        value = raw.get(slot_id)

        # EN | `audio` is the one slot with two roles: a stream exists
        # EN | independently of its output.
        # FR | `audio` est le seul tableau a deux roles : un flux existe
        # FR | independamment de sa sortie.
        if slot_id == "audio":
            if isinstance(value, dict):
                source = list(value.get("source") or [])
                output = list(value.get("output") or [])
            else:
                source = list(value or [])
                output = []
            entry = {"id": slot_id, "source": source, "output": output,
                     "entities": source + output,
                     "has_speaker": bool(output)}
            entry["state"] = "filled" if source else "empty"
        else:
            entities = list(value or [])
            entry = {"id": slot_id, "entities": entities,
                     "state": "filled" if entities else "empty"}

        out[slot_id] = entry

    # EN | One filler at most, first eligible slot wins.
    # FR | Un seul remplisseur au maximum, le premier tableau eligible gagne.
    for slot_id in FILLER_PRIORITY:
        entry = out.get(slot_id)
        if entry and entry["state"] == "empty":
            entry["state"] = "filler"
            break

    return out


def build_rooms(model: dict, ctx_t) -> list:
    """
    EN | Expands the model's rooms into what the template needs: display name,
    EN | path, icon and normalised slots. The identifier stays in English; only
    EN | the label goes through the catalogue.
    FR | Developpe les pieces du modele en ce dont le template a besoin : nom
    FR | affiche, chemin, icone et tableaux normalises. L'identifiant reste en
    FR | anglais ; seul le libelle passe par le catalogue.
    """
    slot_sets = {**DEFAULT_SLOT_SETS, **(model.get("slot_sets") or {})}
    icons = model.get("room_icons") or {}
    rooms = []

    for room in model.get("rooms", []) or []:
        rid = room["id"]
        rtype = room.get("type", rid)
        index = room.get("index")

        # EN | Label from the catalogue, with the index appended for (n) rooms.
        # FR | Libelle depuis le catalogue, index ajoute pour les pieces (n).
        try:
            label = ctx_t(f"room.{rtype}")
        except KeyError:
            label = room.get("label") or rid
        if index:
            label = f"{label} {index}"

        rooms.append({
            "id": rid,
            "type": rtype,
            "index": index,
            "label": label,
            "name": room.get("name") or label.upper(),
            "icon": room.get("icon") or icons.get(rtype, "mdi:home-outline"),
            "slot_set": room.get("slot_set", "default"),
            "slots": normalise_slots(room, slot_sets),
            "path": room.get("path") or f"/visio-sapiens-{rid}/{rid}",
            "path_mobile": room.get("path_mobile")
                           or f"/visio-sapiens-{rid}-m/{rid}",
        })
    return rooms


def build_nav(model: dict, rooms: list) -> list:
    """
    EN | Composes the navigation rail: the fixed system entries, with the
    EN | declared rooms inserted between them. This is what makes the rail
    EN | dynamic — its length is always 4 + the number of rooms, and no
    EN | navigation block is maintained by hand anywhere.
    FR | Compose le bandeau de navigation : les entrees systeme fixes, avec les
    FR | pieces declarees inserees entre elles. C'est ce qui rend le bandeau
    FR | dynamique — sa longueur vaut toujours 4 + le nombre de pieces, et aucun
    FR | bloc de navigation n'est maintenu a la main nulle part.
    """
    nav_system = model.get("nav_system") or {}
    before = list(nav_system.get("before_rooms") or [])
    after = list(nav_system.get("after_rooms") or [])

    room_entries = [{
        "id": r["id"],
        "name": r["name"],
        "label": r["label"],
        "icon": r["icon"],
        "path": r["path"],
        "path_mobile": r["path_mobile"],
    } for r in rooms]

    return before + room_entries + after


# ----------------------------------------------------------------------------
# EN | Legacy helpers, unchanged behaviour
# FR | Aides historiques, comportement inchange
# ----------------------------------------------------------------------------
def flatten_rooms(rooms: list) -> list:
    """
    EN | rooms -> flat device list, keeping the room as a label.
    FR | rooms -> liste plate d'appareils, en gardant la piece comme libelle.
    """
    flat = []
    for room in rooms:
        for d in room.get("devices", []) or []:
            item = dict(d)
            item.setdefault("room", room.get("name", ""))
            flat.append(item)
    return flat


def preview_context(context: dict) -> dict:
    """
    EN | Isolates the render into a TEST dashboard. The preview has its own
    EN | url_path, hence its own Lovelace entry: it coexists with the staging
    EN | dashboard without ever overwriting it. The title is marked to avoid
    EN | any visual confusion.
    FR | Isole le rendu dans un dashboard de TEST. L'apercu a sa propre
    FR | url_path, donc sa propre entree Lovelace : il coexiste avec le
    FR | dashboard de staging sans jamais l'ecraser. Le titre est marque pour
    FR | eviter toute confusion visuelle.
    """
    ctx = deepcopy(context)
    energy = ctx.get("energy", {})
    energy["url_path"] = energy.get("url_path", "vssp-energy") + "-preview"
    energy["title"] = energy.get("title", "ENERGY") + " \u29d7 PREVIEW"
    energy["subtitle"] = "PREVIEW — not deployed"
    ctx["energy"] = energy
    return ctx


def write_status(path, status: dict) -> None:
    """
    EN | JSON report read by the admin console (served under /local/vssp/...).
    FR | Rapport JSON lu par la console admin (servi en /local/vssp/...).
    """
    if not path:
        return
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(status, indent=2, ensure_ascii=False),
                     encoding="utf-8")
    except OSError as exc:
        print(f"[warn] status file not written: {exc}")


# ----------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model",
                    default="home-assistant/dashboards/model/house.yaml")
    ap.add_argument("--rooms",
                    default="home-assistant/dashboards/model/house_rooms.yaml",
                    help="Rooms fragment produced by the discovery wizard; if "
                         "present, its rooms: key replaces the model's")
    ap.add_argument("--devices",
                    default="home-assistant/dashboards/model/energy_devices.yaml",
                    help="Flat device list for the ENERGY dashboard "
                         "(maintained by vssp_energy_sync.py). Takes "
                         "precedence over flattening the rooms.")
    ap.add_argument("--templates",
                    default="home-assistant/dashboards/templates_j2")
    ap.add_argument("--out", default="home-assistant/dashboards/views")
    ap.add_argument("--locales-dir",
                    default="home-assistant/dashboards/locales")
    ap.add_argument("--locale", default=None,
                    help="Interface language. Overrides house.locale. English "
                         "is the reference: any key missing from another "
                         "catalogue falls back to it.")
    ap.add_argument("--format", default=None,
                    choices=["tablet", "mobile", "both"],
                    help="Target layout. Overrides house.format.")
    ap.add_argument("--preview", action="store_true",
                    help="Generates an isolated TEST dashboard "
                         "(energy_preview.yaml / url vssp-energy-preview) "
                         "without ever touching the staging dashboards")
    ap.add_argument("--only", default=None,
                    help="Generate only these dashboards (comma-separated "
                         "ids, e.g. energy,home, or a room id). Default: all.")
    ap.add_argument("--if-missing", action="store_true",
                    help="Generate only when the output file does not exist "
                         "yet. An existing dashboard is NEVER overwritten "
                         "(CREATE button of the ADMIN console).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Validates the model and the render, writes nothing")
    ap.add_argument("--status-file", default=None,
                    help="Writes a JSON report (readable by the console at "
                         "/local/vssp/preview_status.json)")
    args = ap.parse_args()

    status = {"ok": False, "preview": args.preview, "dry_run": args.dry_run,
              "generated": [], "skipped": [], "errors": [], "warnings": [],
              "timestamp": datetime.now().isoformat(timespec="seconds")}

    model = yaml.safe_load(Path(args.model).read_text(encoding="utf-8"))

    # --- EN | Language / FR | Langue -------------------------------------
    # EN | Precedence: --locale (console selector) > house.locale > 'en'.
    # EN | Passing it as an argument means the ADMIN console never has to
    # EN | rewrite house.yaml just to switch language.
    # FR | Priorite : --locale (selecteur de la console) > house.locale > 'en'.
    # FR | Le passer en argument evite que la console ADMIN doive reecrire
    # FR | house.yaml juste pour changer de langue.
    house = model.get("house") or {}
    locale = args.locale or house.get("locale") or vssp_i18n.BASE_LOCALE
    try:
        i18n = vssp_i18n.jinja_context(locale, Path(args.locales_dir))
    except FileNotFoundError as exc:
        print(f"[ERR] locale '{locale}': {exc}")
        status["errors"].append(str(exc))
        write_status(args.status_file, status)
        return 1
    print(f"[i] locale: {locale} ({i18n['locale_tag']})")

    # --- EN | Format / FR | Format ---------------------------------------
    fmt = args.format or house.get("format") or "tablet"
    formats = ["tablet", "mobile"] if fmt == "both" else [fmt]
    print(f"[i] format: {', '.join(formats)}")

    # --- EN | Rooms fragment from the discovery wizard (steps 2-4) -------
    # --- FR | Fragment rooms du Discovery Wizard (etapes 2-4) ------------
    todo_count = 0
    rooms_path = Path(args.rooms)
    if rooms_path.exists():
        text = rooms_path.read_text(encoding="utf-8")
        fragment = yaml.safe_load(text)
        todo_count = text.count("# TODO ")
        if fragment and fragment.get("rooms"):
            model["rooms"] = fragment["rooms"]
            print(f"[i] rooms: taken from {rooms_path} "
                  f"({len(fragment['rooms'])} room(s))")

    # --- EN | FLAT device list for the ENERGY dashboard ------------------
    # --- FR | Liste PLATE des appareils du dashboard ENERGY --------------
    # EN | ENERGY depends on no room: it shows every measured device in the
    # EN | home. Two possible sources, in this order:
    # EN |   1. model/energy_devices.yaml — maintained by vssp_energy_sync.py
    # EN |   2. otherwise, flattening the model's / wizard's rooms
    # FR | ENERGY ne depend d'aucune piece : il affiche tous les appareils
    # FR | mesures de la maison. Deux sources possibles, dans cet ordre :
    # FR |   1. model/energy_devices.yaml — maintenu par vssp_energy_sync.py
    # FR |   2. sinon, aplatissement des rooms du modele / du wizard
    devices_path = Path(args.devices)
    if devices_path.exists():
        dev_doc = yaml.safe_load(devices_path.read_text(encoding="utf-8")) or {}
        model["energy_devices"] = dev_doc.get("devices", [])
        if dev_doc.get("circuits") is not None:
            model["circuits"] = dev_doc["circuits"]
        print(f"[i] ENERGY devices: {devices_path} "
              f"({len(model['energy_devices'])} device(s), "
              f"{len(model.get('circuits', []))} circuit(s))")
    else:
        model["energy_devices"] = flatten_rooms(model.get("rooms", []))

    errors, warns = validate_model(model)
    status["warnings"] = warns
    if warns:
        print(f"[warn] {len(warns)} field(s) to complete in "
              f"model/energy_devices.yaml:")
        for w in warns[:5]:
            print(f"  - {w}")
        if len(warns) > 5:
            print(f"  ... and {len(warns) - 5} more")
    if errors:
        print("[ERR] invalid model — generation cancelled:")
        for e in errors:
            print(f"  - {e}")
        status["errors"] = errors
        write_status(args.status_file, status)
        return 1

    # --- EN | Rooms and dynamic navigation rail --------------------------
    # --- FR | Pieces et bandeau de navigation dynamique ------------------
    rooms = build_rooms(model, i18n["t"])
    model["rooms_rendered"] = rooms
    model["nav"] = build_nav(model, rooms)
    model["slots"] = SLOTS
    print(f"[i] navigation: {len(model['nav'])} entries "
          f"({len(model['nav']) - len(rooms)} system + {len(rooms)} room(s))")

    env = Environment(
        loader=FileSystemLoader(args.templates),
        # EN | missing variable = error, never a silent hole
        # FR | variable manquante = erreur, jamais de trou silencieux
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    n_dev = len(model.get("energy_devices", []))

    # --- EN | Build the job list: system dashboards + one per room -------
    # --- FR | Constitution des jobs : dashboards systeme + un par piece --
    jobs = list(SYSTEM_DASHBOARDS)
    for room in rooms:
        jobs.append((room["id"], ROOM_TEMPLATE, f"{room['id']}.yaml",
                     {"active_nav": room["id"], "room": room,
                      "room_id": room["id"]}))

    wanted = ({s.strip() for s in args.only.split(",") if s.strip()}
              if args.only else None)
    if wanted:
        unknown = wanted - {j[0] for j in jobs}
        if unknown:
            msg = f"unknown dashboard(s): {', '.join(sorted(unknown))}"
            print(f"[ERR] {msg}")
            status["errors"].append(msg)
            write_status(args.status_file, status)
            return 1

    for dash_id, tpl_name, out_name, extra in jobs:
        if wanted and dash_id not in wanted:
            continue

        for target_format in formats:
            context = {**model, **i18n, **extra, "format": target_format}
            name = out_name
            if target_format == "mobile":
                name = name.replace(".yaml", "_mobile.yaml")

            if args.preview:
                context = preview_context(context)
                name = name.replace(".yaml", "_preview.yaml")

            # EN | --if-missing: never overwrite an existing dashboard. The
            # EN | check uses the FINAL output name (including the _preview
            # EN | suffix), so a preview does not block creating the real one.
            # FR | --if-missing : ne jamais ecraser un dashboard existant. Le
            # FR | controle porte sur le nom de sortie FINAL (suffixe _preview
            # FR | compris), pour qu'un apercu ne bloque pas la creation du vrai.
            if args.if_missing and (out_dir / name).exists():
                print(f"= {out_dir / name} already exists — left intact "
                      f"(--if-missing)")
                status["skipped"].append(str(out_dir / name))
                continue

            # EN | A template that does not exist yet is not an error: the
            # EN | project ships them one at a time. Reported, then skipped.
            # FR | Un template pas encore ecrit n'est pas une erreur : le projet
            # FR | les livre un par un. Signale, puis saute.
            try:
                template = env.get_template(tpl_name)
            except TemplateNotFound:
                print(f"[skip] {tpl_name} not found — {dash_id} not generated")
                status["skipped"].append(f"{dash_id} ({tpl_name} missing)")
                continue

            rendered = template.render(**context)

            # EN | A __T: marker surviving the render means a template used the
            # EN | placeholder syntax instead of calling t(). It would reach the
            # EN | screen verbatim.
            # FR | Un marqueur __T: survivant au rendu signifie qu'un template a
            # FR | utilise la syntaxe de substitution au lieu d'appeler t(). Il
            # FR | arriverait tel quel a l'ecran.
            leftover = sorted(set(T_PLACEHOLDER.findall(rendered)))
            if leftover:
                msg = (f"{name}: {len(leftover)} unresolved placeholder(s) "
                       f"after render — {', '.join(leftover[:5])}")
                print(f"[ERR] {msg}")
                print("      Templates must call t('key'), not __T:key__.")
                status["errors"].append(msg)
                write_status(args.status_file, status)
                return 1

            # EN | YAML validation BEFORE writing
            # FR | Validation YAML AVANT ecriture
            try:
                yaml.load(rendered, Loader=HaLoader)
            except yaml.YAMLError as exc:
                msg = f"{name}: invalid YAML after render — not written"
                print(f"[ERR] {msg}\n{exc}")
                status["errors"].append(f"{msg} — {exc}")
                write_status(args.status_file, status)
                return 1

            target = out_dir / name
            if args.dry_run:
                print(f"[dry-run] {target} — render valid "
                      f"({len(rendered.splitlines())} lines) — NOT written")
            else:
                target.write_text(rendered, encoding="utf-8")
                print(f"[OK] {target} generated ({target_format}, {locale})")

            status["generated"].append({
                "file": str(target),
                "id": dash_id,
                "format": target_format,
                "locale": locale,
                "lines": len(rendered.splitlines()),
            })

    status["ok"] = True
    status["locale"] = locale
    status["formats"] = formats
    status["rooms"] = len(rooms)
    status["nav_entries"] = len(model["nav"])
    status["energy_devices"] = n_dev
    status["devices"] = n_dev
    status["circuits"] = len(model.get("circuits", []))
    status["todo_devices"] = todo_count
    if args.preview:
        print("\n-> Preview available at /vssp-energy-preview/energy "
              "— your staging dashboards were not modified.")
    write_status(args.status_file, status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
