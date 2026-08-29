#!/usr/bin/env python3
# ============================================================================
# Visio Sapiens — Design system applier
#
# EN | Takes what the THEME screen's graphical editor produced and writes it
# EN | into model/design_system.yaml. Same role, for the visual charter, as
# EN | vssp_assign_apply.py plays for device placement: the form decides, this
# EN | script records the decision, and generate_dashboards.py --only theme
# EN | renders it into themes/visio_sapiens.yaml.
# FR | Prend ce que l editeur graphique de l ecran THEME a produit et l ecrit
# FR | dans model/design_system.yaml. Meme role, pour la charte graphique, que
# FR | vssp_assign_apply.py pour le placement des appareils : le formulaire
# FR | decide, ce script enregistre la decision, et
# FR | generate_dashboards.py --only theme la rend dans
# FR | themes/visio_sapiens.yaml.
#
# EN | INPUT — json, either from a file or base64 on the command line. Only
# EN | the tokens actually present in "tokens" are touched; anything else in
# EN | design_system.yaml (including design.name) is left exactly as is:
# FR | ENTREE — json, depuis un fichier ou en base64 en ligne de commande.
# FR | Seuls les tokens presents dans "tokens" sont modifies ; tout le reste
# FR | de design_system.yaml (y compris design.name) reste inchange :
#   {"tokens": {
#      "primary": "#00E5FF",
#      "card_radius": "18px"
#   }}
#
# EN | VALIDATION IS THE WHOLE POINT — a malformed color or an out-of-range
# EN | radius must never reach design_system.yaml: it would pass YAML parsing
# EN | fine, render into themes/visio_sapiens.yaml, and only fail once Home
# EN | Assistant tries to apply it as CSS — a silent failure far from its
# EN | cause, the exact failure shape this project avoids everywhere else.
# FR | LA VALIDATION EST TOUT L INTERET — une couleur malformee ou un rayon
# FR | hors bornes ne doit jamais atteindre design_system.yaml : elle
# FR | passerait le parsing YAML sans probleme, se rendrait dans
# FR | themes/visio_sapiens.yaml, et n echouerait qu une fois que Home
# FR | Assistant tente de l appliquer en CSS — une panne silencieuse loin de
# FR | sa cause, exactement la forme de panne que ce projet evite partout
# FR | ailleurs.
#
# EN | USAGE / FR | UTILISATION
#   python3 vssp_theme_apply.py --model design_system.yaml --json-file payload.json
#   python3 vssp_theme_apply.py --model design_system.yaml --json-b64 "eyJ..."
#   python3 vssp_theme_apply.py --model design_system.yaml --json-file p.json --dry-run
#
# EN | Dependency: ruamel.yaml, to keep the comments of design_system.yaml —
# EN | same reason and same dependency as vssp_assign_apply.py.
# FR | Dependance : ruamel.yaml, pour conserver les commentaires de
# FR | design_system.yaml — meme raison et meme dependance que
# FR | vssp_assign_apply.py.
# ============================================================================
from __future__ import annotations

import argparse
import base64
import binascii
import datetime as _dt
import json
import shutil
import sys
from pathlib import Path

try:
    from ruamel.yaml import YAML
except ImportError:
    sys.exit("[ERR] ruamel.yaml is missing. Install it: pip install ruamel.yaml")

# EN | The i18n engine and generate_dashboards.py live next to this script,
# EN | whether the repo root or /config/vssp/ is the working directory.
# FR | Le moteur i18n et generate_dashboards.py vivent a cote de ce script,
# FR | que le repertoire courant soit la racine du repo ou /config/vssp/.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from vssp_design_fields import FIELDS, flatten, validate  # noqa: E402


def _yaml():
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)
    return y


def read_payload(args) -> dict:
    if args.json_file:
        raw = Path(args.json_file).read_text(encoding="utf-8")
    elif args.json_b64:
        try:
            raw = base64.b64decode(args.json_b64).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as exc:
            sys.exit(f"[ERR] --json-b64 is not valid base64 utf-8: {exc}")
    else:
        raw = sys.stdin.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.exit(f"[ERR] payload is not valid json: {exc}")


def reference_payload(reference_path: Path) -> dict:
    """
    EN | Builds a normal {"tokens": {...}} payload straight out of
    EN | design_system.default.yaml, so RESTORE REFERENCE goes through the
    EN | exact same validate()/apply()/backup path as a real editor
    EN | submission — no separate code path to keep in sync.
    FR | Construit un payload {"tokens": {...}} normal directement depuis
    FR | design_system.default.yaml, pour que RESTAURER LA REFERENCE passe
    FR | par exactement le meme chemin validate()/apply()/sauvegarde qu'une
    FR | vraie soumission de l'editeur — pas de second chemin de code a
    FR | maintenir en phase.
    """
    if not reference_path.is_file():
        sys.exit(f"[ERR] reference model not found: {reference_path}")
    y = _yaml()
    ref_doc = y.load(reference_path.read_text(encoding="utf-8"))
    ref_design = (ref_doc or {}).get("design")
    if ref_design is None:
        sys.exit(f"[ERR] {reference_path} has no top-level `design:` key")
    return {"tokens": flatten(ref_design)}


def apply(design, accepted: dict) -> int:
    """
    EN | Writes each accepted token into its place in `design:`, mutating the
    EN | existing nested mapping in place (never rebuilding it) so ruamel
    EN | keeps every comment design_system.yaml carries.
    FR | Ecrit chaque token accepte a sa place sous `design:`, en modifiant le
    FR | mapping imbrique existant sur place (jamais en le reconstruisant),
    FR | pour que ruamel conserve tous les commentaires de design_system.yaml.
    """
    written = 0
    for key, value in accepted.items():
        path, _, _ = FIELDS[key]
        node = design
        for segment in path[:-1]:
            node = node[segment]
        node[path[-1]] = value
        written += 1
    return written


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model",
                    default="/config/dashboards/model/design_system.yaml")
    ap.add_argument("--json-file", default=None)
    ap.add_argument("--json-b64", default=None)
    ap.add_argument("--restore-reference", default=None,
                     metavar="DESIGN_SYSTEM_DEFAULT_YAML",
                     help="Ignore --json-file/--json-b64/stdin and rebuild "
                          "the payload from this frozen reference file's "
                          "`design:` block instead (RESTORE REFERENCE)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Validate and report, write nothing")
    ap.add_argument("--status-file", default="/config/www/vssp/theme_status.json")
    args = ap.parse_args()

    model_path = Path(args.model)
    if not model_path.is_file():
        sys.exit(f"[ERR] model not found: {model_path}")

    if args.restore_reference:
        payload = reference_payload(Path(args.restore_reference))
    else:
        payload = read_payload(args)
    y = _yaml()
    doc = y.load(model_path.read_text(encoding="utf-8"))
    design = doc.get("design") if doc else None
    if design is None:
        sys.exit(f"[ERR] {model_path} has no top-level `design:` key")

    accepted, errors = validate(payload)

    status = {
        "ok": bool(accepted) or not errors,
        "written": list(accepted),
        "errors": errors,
        "dry_run": args.dry_run,
        "timestamp": _dt.datetime.now().isoformat(timespec="seconds"),
    }

    if not accepted:
        print("[ERR] no valid token in payload — nothing written:")
        for e in errors:
            print(f"  - {e}")
        status["ok"] = False
    else:
        if errors:
            print(f"[warn] {len(errors)} token(s) rejected, "
                  f"{len(accepted)} applied anyway:")
            for e in errors:
                print(f"  - {e}")

        written = apply(design, accepted)
        if args.dry_run:
            print(f"[dry-run] {written} token(s) would be written: "
                  f"{', '.join(sorted(accepted))}")
        else:
            # EN | Backup before writing — same convention as every other
            # EN | REGENERATE button in this project.
            # FR | Sauvegarde avant ecriture — meme convention que tous les
            # FR | autres boutons REGENERER de ce projet.
            backups = model_path.parent / "backups"
            backups.mkdir(parents=True, exist_ok=True)
            stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = backups / f"design_system_{stamp}.yaml"
            shutil.copy2(model_path, dest)
            print(f"[OK] backup: {dest}")

            tmp = model_path.with_suffix(".vssptmp")
            with open(tmp, "w", encoding="utf-8") as fh:
                y.dump(doc, fh)
            tmp.replace(model_path)
            print(f"[OK] {model_path}: {written} token(s) written "
                  f"({', '.join(sorted(accepted))})")

    if args.status_file:
        try:
            sp = Path(args.status_file)
            sp.parent.mkdir(parents=True, exist_ok=True)
            sp.write_text(json.dumps(status, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        except OSError as exc:
            print(f"[warn] status file not written: {exc}")

    return 0 if accepted else 1


if __name__ == "__main__":
    sys.exit(main())
