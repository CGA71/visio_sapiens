#!/usr/bin/env python3
"""Générateur de dashboards Visio Sapiens.

Usage :
    # depuis la racine du repo (défauts alignés sur l'arborescence) :
    python3 vssp/generate_dashboards.py                 # publication
    python3 vssp/generate_dashboards.py --preview       # dashboard de TEST isolé
    python3 vssp/generate_dashboards.py --dry-run       # validation seule
    # ou sur le pod HA (voir vssp/vssp_admin_config.yaml) :
    python3 /config/vssp/generate_dashboards.py --model ... --templates ... --out ...

Pipeline (étape 5 du processus admin) :
    house.yaml (modèle métier) + *.yaml.j2 (templates) → dashboards/views/*.yaml

Le rendu est validé (YAML parsable, tags !include tolérés) AVANT
d'écraser le fichier cible : jamais de dashboard cassé déployé.
Pensé pour être appelé par un shell_command Home Assistant à la fin
du processus scan/assignation.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import yaml
from copy import deepcopy
from jinja2 import Environment, FileSystemLoader, StrictUndefined

# ── Dashboards à générer : (template, sortie, variables spécifiques) ──
# (id, template, sortie, variables) — l'id sert a --only.
# ENERGY et CORE sont des dashboards SYSTEME : ils ne dependent d'aucune
# piece et ne passent donc pas par le formulaire de creation/modification
# /suppression du wizard. Ils se generent depuis le panneau ADMIN.
DASHBOARDS = [
    ("energy", "energy.yaml.j2", "energy.yaml", {"active_nav": "energy"}),
    # Ajoutez ici vos futurs templates :
    # ("core", "core.yaml.j2", "core.yaml", {"active_nav": "core"}),
    # ("energy_mobile", "energy_mobile.yaml.j2", "energy_mobile.yaml",
    #  {"active_nav": "energy"}),
    # ("home", "home.yaml.j2", "home.yaml", {"active_nav": "home"}),
    # ("livingroom", "room.yaml.j2", "livingroom.yaml",
    #  {"active_nav": "livingroom", "room_id": "livingroom"}),
]


class HaLoader(yaml.SafeLoader):
    """SafeLoader qui tolère les tags Home Assistant (!include, etc.)."""


for tag in ("!include", "!include_dir_list", "!include_dir_named",
            "!include_dir_merge_list", "!include_dir_merge_named",
            "!secret", "!env_var", "!input"):
    HaLoader.add_constructor(tag, lambda loader, node: node.value)


def validate_model(model: dict) -> tuple[list[str], list[str]]:
    """Contrôles métier — renvoie (erreurs bloquantes, avertissements)."""
    errors: list[str] = []
    warnings: list[str] = []
    seen_entities = {}
    for d in model.get("energy_devices", []):
        # Bloquant : sans ces champs, la carte ne peut pas s'afficher.
        for field in ("name", "icon", "power_entity", "energy_entity"):
            if not d.get(field):
                errors.append(
                    f"Appareil « {d.get('name', '?')} » : "
                    f"champ manquant `{field}`")
        # Informatif : le modele vient du registre HA quand il est
        # disponible, sinon il reste a completer — ce n'est pas une
        # raison de refuser tout le dashboard.
        if not d.get("model"):
            warnings.append(f"Appareil « {d.get('name', '?')} » : "
                            f"modele inconnu")
        ent = d.get("power_entity")
        if ent in seen_entities:
            errors.append(
                f"Entité {ent} présente deux fois "
                f"(« {seen_entities[ent]} » et « {d.get('name')} »)")
        seen_entities[ent] = d.get("name")
    for c in model.get("circuits", []):
        for field in ("name", "icon", "entity"):
            if not c.get(field):
                errors.append(f"Circuit « {c.get('name', '?')} » : "
                              f"champ manquant `{field}`")
        # Le calibre n'est jamais decouvrable automatiquement : il se
        # lit sur le disjoncteur. Signale, jamais bloquant.
        if not c.get("amp"):
            warnings.append(f"Circuit « {c.get('name', '?')} » : "
                            f"calibre (amp) a renseigner")
    return errors, warnings


def flatten_rooms(rooms: list) -> list:
    """rooms → liste plate d'appareils, en gardant la pièce comme libellé."""
    flat = []
    for room in rooms:
        for d in room.get("devices", []) or []:
            item = dict(d)
            item.setdefault("room", room.get("name", ""))
            flat.append(item)
    return flat


def preview_context(context: dict) -> dict:
    """Isole le rendu dans un dashboard de TEST.

    Le dashboard d'aperçu a sa propre url_path, donc sa propre entrée
    Lovelace : il coexiste avec le dashboard de staging sans jamais
    l'écraser. Le titre est marqué pour éviter toute confusion visuelle.
    """
    ctx = deepcopy(context)
    energy = ctx.get("energy", {})
    energy["url_path"] = energy.get("url_path", "vssp-energy") + "-preview"
    energy["title"] = energy.get("title", "ENERGY") + " ⧗ PREVIEW"
    energy["subtitle"] = "APERÇU — non deploye"
    ctx["energy"] = energy
    return ctx


def write_status(path, status: dict) -> None:
    """Rapport JSON lu par le wizard (servi en /local/vssp/…)."""
    if not path:
        return
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(status, indent=2, ensure_ascii=False),
                     encoding="utf-8")
    except OSError as exc:
        print(f"⚠ status-file non écrit : {exc}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model",
                default="home-assistant/dashboards/model/house.yaml")
    ap.add_argument("--rooms",
                default="home-assistant/dashboards/model/house_rooms.yaml",
                help="Fragment rooms généré par le Discovery Wizard ; "
                     "s'il existe, sa clé rooms: remplace celle du modèle")
    ap.add_argument("--devices",
                default="home-assistant/dashboards/model/energy_devices.yaml",
                help="Liste plate des appareils du dashboard ENERGY "
                     "(maintenue par vssp_energy_sync.py). Prioritaire "
                     "sur l'aplatissement des rooms.")
    ap.add_argument("--templates",
                default="home-assistant/dashboards/templates_j2")
    ap.add_argument("--out",
                default="home-assistant/dashboards/views")
    ap.add_argument("--preview", action="store_true",
                help="Genere un dashboard de TEST isole "
                     "(energy_preview.yaml / url vssp-energy-preview) "
                     "sans jamais toucher aux dashboards de staging")
    ap.add_argument("--only", default=None,
                help="Ne generer que ces dashboards (ids separes par des "
                     "virgules, ex: energy). Par defaut : tous.")
    ap.add_argument("--if-missing", action="store_true",
                help="Ne generer que si le fichier de sortie n'existe pas "
                     "encore. Un dashboard deja en place n'est JAMAIS "
                     "ecrase (bouton CREER du panneau ADMIN).")
    ap.add_argument("--dry-run", action="store_true",
                help="Valide le modele et le rendu, n'ecrit aucun fichier")
    ap.add_argument("--status-file", default=None,
                help="Ecrit un rapport JSON (lisible par le wizard via "
                     "/local/vssp/preview_status.json)")
    args = ap.parse_args()

    status = {"ok": False, "preview": args.preview, "dry_run": args.dry_run,
              "generated": [], "skipped": [], "errors": [], "warnings": [],
              "timestamp": datetime.now().isoformat(timespec="seconds")}

    model = yaml.safe_load(Path(args.model).read_text(encoding="utf-8"))

    # Fusion du fragment du Discovery Wizard (étapes 2-4 du processus admin)
    todo_count = 0
    rooms_path = Path(args.rooms)
    if rooms_path.exists():
        fragment = yaml.safe_load(rooms_path.read_text(encoding="utf-8"))
        todo_count = rooms_path.read_text(encoding="utf-8").count("# TODO ")
        if fragment and fragment.get("rooms"):
            model["rooms"] = fragment["rooms"]
            print(f"ℹ rooms: repris depuis {rooms_path} "
                  f"({len(fragment['rooms'])} pièces)")

    # ── Liste PLATE des appareils du dashboard ENERGY ─────────────────
    # ENERGY ne dépend d'aucune pièce : il affiche tous les appareils
    # mesurés de la maison. Deux sources possibles, dans cet ordre :
    #   1. model/energy_devices.yaml — maintenu par vssp_energy_sync.py
    #      (ajout/retrait automatique selon les entités présentes)
    #   2. sinon, aplatissement des rooms du modèle / du wizard
    devices_path = Path(args.devices)
    if devices_path.exists():
        dev_doc = yaml.safe_load(devices_path.read_text(encoding="utf-8")) or {}
        model["energy_devices"] = dev_doc.get("devices", [])
        if dev_doc.get("circuits") is not None:
            model["circuits"] = dev_doc["circuits"]
        print(f"ℹ appareils ENERGY: {devices_path} "
              f"({len(model['energy_devices'])} appareils, "
              f"{len(model.get('circuits', []))} circuits)")
    else:
        model["energy_devices"] = flatten_rooms(model.get("rooms", []))

    errors, warns = validate_model(model)
    status["warnings"] = warns
    if warns:
        print(f"⚠ {len(warns)} champ(s) à compléter dans "
              f"model/energy_devices.yaml :")
        for w in warns[:5]:
            print(f"  - {w}")
        if len(warns) > 5:
            print(f"  … et {len(warns) - 5} autre(s)")
    if errors:
        print("✗ Modèle invalide — génération annulée :")
        for e in errors:
            print(f"  - {e}")
        status["errors"] = errors
        write_status(args.status_file, status)
        return 1

    env = Environment(
        loader=FileSystemLoader(args.templates),
        undefined=StrictUndefined,   # variable manquante = erreur, pas de trou silencieux
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    n_dev = len(model.get("energy_devices", []))

    wanted = ({s.strip() for s in args.only.split(",") if s.strip()}
              if args.only else None)
    if wanted:
        unknown = wanted - {d[0] for d in DASHBOARDS}
        if unknown:
            msg = f"dashboard(s) inconnu(s) : {', '.join(sorted(unknown))}"
            print(f"✗ {msg}")
            status["errors"].append(msg)
            write_status(args.status_file, status)
            return 1

    for dash_id, tpl_name, out_name, extra in DASHBOARDS:
        if wanted and dash_id not in wanted:
            continue
        context = {**model, **extra}

        if args.preview:
            context = preview_context(context)
            out_name = out_name.replace(".yaml", "_preview.yaml")

        # --if-missing : ne jamais ecraser un dashboard existant.
        # Le controle porte sur le nom de sortie FINAL (suffixe _preview
        # compris), pour qu'un apercu ne bloque pas la creation du vrai.
        if args.if_missing and (out_dir / out_name).exists():
            print(f"= {out_dir / out_name} existe déjà — laissé intact "
                  f"(--if-missing)")
            status["skipped"].append(str(out_dir / out_name))
            continue

        rendered = env.get_template(tpl_name).render(**context)

        # Validation YAML AVANT écriture
        try:
            yaml.load(rendered, Loader=HaLoader)
        except yaml.YAMLError as exc:
            msg = f"{out_name} : YAML invalide après rendu — non écrit"
            print(f"✗ {msg}\n{exc}")
            status["errors"].append(f"{msg} — {exc}")
            write_status(args.status_file, status)
            return 1

        target = out_dir / out_name
        if args.dry_run:
            print(f"● {target} — rendu valide ({len(rendered.splitlines())} "
                  f"lignes) — NON écrit (--dry-run)")
        else:
            target.write_text(rendered, encoding="utf-8")
            print(f"{'◑' if args.preview else '✓'} {target} généré "
                  f"({len(model.get('rooms', []))} pièces, {n_dev} appareils, "
                  f"{len(model.get('circuits', []))} circuits)")

        status["generated"].append({
            "file": str(target),
            "lines": len(rendered.splitlines()),
            "url": f"/{context['energy']['url_path']}/{context['energy']['view_path']}"
                   if "energy" in context else None,
        })

    status["ok"] = True
    status["rooms"] = len(model.get("rooms", []))
    status["energy_devices"] = n_dev
    status["devices"] = n_dev
    status["circuits"] = len(model.get("circuits", []))
    status["todo_devices"] = todo_count
    if args.preview:
        print("\n→ Aperçu disponible sur /vssp-energy-preview/energy "
              "— vos dashboards de staging n'ont pas été modifiés.")
    write_status(args.status_file, status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
