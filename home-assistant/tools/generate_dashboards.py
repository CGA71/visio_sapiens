#!/usr/bin/env python3
"""Générateur de dashboards Visio Sapiens.

Usage :
    python3 generate_dashboards.py [--model model/house.yaml]
                                   [--templates templates_j2/]
                                   [--out dashboards/views/]

Pipeline (étape 5 du processus admin) :
    house.yaml (modèle métier) + *.yaml.j2 (templates) → dashboards/views/*.yaml

Le rendu est validé (YAML parsable, tags !include tolérés) AVANT
d'écraser le fichier cible : jamais de dashboard cassé déployé.
Pensé pour être appelé par un shell_command Home Assistant à la fin
du processus scan/assignation.
"""
import argparse
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

# ── Dashboards à générer : (template, sortie, variables spécifiques) ──
DASHBOARDS = [
    ("energy.yaml.j2", "energy.yaml", {"active_nav": "energy"}),
    # Ajoutez ici vos futurs templates :
    # ("home.yaml.j2", "home.yaml", {"active_nav": "home"}),
    # ("room.yaml.j2", "livingroom.yaml", {"active_nav": "livingroom",
    #                                      "room_id": "livingroom"}),
]


class HaLoader(yaml.SafeLoader):
    """SafeLoader qui tolère les tags Home Assistant (!include, etc.)."""


for tag in ("!include", "!include_dir_list", "!include_dir_named",
            "!include_dir_merge_list", "!include_dir_merge_named",
            "!secret", "!env_var", "!input"):
    HaLoader.add_constructor(tag, lambda loader, node: node.value)


def validate_model(model: dict) -> list[str]:
    """Contrôles métier avant génération — renvoie la liste des erreurs."""
    errors = []
    seen_entities = {}
    for room in model.get("rooms", []):
        if not room.get("name"):
            errors.append(f"Pièce sans nom : {room}")
        for d in room.get("devices", []):
            for field in ("name", "icon", "model", "power_entity", "energy_entity"):
                if not d.get(field):
                    errors.append(
                        f"Appareil « {d.get('name', '?')} » "
                        f"({room.get('name')}) : champ manquant `{field}`")
            ent = d.get("power_entity")
            if ent in seen_entities:
                errors.append(
                    f"Entité {ent} assignée deux fois "
                    f"({seen_entities[ent]} et {room.get('name')})")
            seen_entities[ent] = room.get("name")
    for c in model.get("circuits", []):
        for field in ("name", "icon", "entity", "model", "amp"):
            if not c.get(field):
                errors.append(f"Circuit « {c.get('name', '?')} » : "
                              f"champ manquant `{field}`")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="house.yaml")
    ap.add_argument("--templates", default=".")
    ap.add_argument("--out", default="out")
    args = ap.parse_args()

    model = yaml.safe_load(Path(args.model).read_text(encoding="utf-8"))

    errors = validate_model(model)
    if errors:
        print("✗ Modèle invalide — génération annulée :")
        for e in errors:
            print(f"  - {e}")
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

    for tpl_name, out_name, extra in DASHBOARDS:
        context = {**model, **extra}
        rendered = env.get_template(tpl_name).render(**context)

        # Validation YAML AVANT écriture
        try:
            yaml.load(rendered, Loader=HaLoader)
        except yaml.YAMLError as exc:
            print(f"✗ {out_name} : YAML invalide après rendu — non écrit\n{exc}")
            return 1

        target = out_dir / out_name
        target.write_text(rendered, encoding="utf-8")
        n_dev = sum(len(r.get("devices", [])) for r in model.get("rooms", []))
        print(f"✓ {target} généré "
              f"({len(model.get('rooms', []))} pièces, {n_dev} appareils, "
              f"{len(model.get('circuits', []))} circuits)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
