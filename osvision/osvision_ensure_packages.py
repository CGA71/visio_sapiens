#!/usr/bin/env python3
# ============================================================================
# OSVision V2 — osvision_ensure_packages.py
#
# Garantit la présence de :
#
#     homeassistant:
#       packages: !include_dir_named packages
#
# dans configuration.yaml, de façon IDEMPOTENTE et NON DESTRUCTIVE :
#   • si homeassistant.packages est déjà défini (quelle que soit sa valeur)
#     -> ne touche à rien ;
#   • si un bloc racine `homeassistant:` existe -> insère seulement la ligne
#     `packages:` dedans (jamais de bloc dupliqué) ;
#   • sinon -> ajoute le bloc complet en tête de fichier.
#
# Complète osvision_apply_config.py, qui ne gère pas le domaine
# « homeassistant ». Invoqué par le CI juste après le patcher (staging et
# production).
#
# Zéro dépendance (stdlib uniquement) : édition TEXTUELLE chirurgicale — le
# reste du fichier (commentaires, tags !include/!secret, indentation) est
# préservé octet pour octet, fins de ligne comprises.
#
# Usage :  python3 osvision_ensure_packages.py --config /config/configuration.yaml
# Sortie : code 0 si OK (posé ou déjà présent), 1 si erreur.
# ============================================================================
import argparse
import re
import shutil
import sys

PKG_LINE = "  packages: !include_dir_named packages"
HEADER = "# OSVision : chargement des packages multi-domaines (spvs_*.yaml)"


def main() -> int:
    ap = argparse.ArgumentParser(description="Garantit homeassistant.packages")
    ap.add_argument("--config", required=True, help="Chemin de configuration.yaml")
    args = ap.parse_args()

    try:
        with open(args.config, encoding="utf-8", newline="") as fh:
            text = fh.read()
    except FileNotFoundError:
        print(f"[ERR] {args.config} introuvable")
        return 1

    # Fins de ligne du fichier (préservées à l'écriture)
    eol = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(eol)

    # ── Localiser un bloc racine `homeassistant:` (hors commentaire) ──────
    ha_start = None
    for i, ln in enumerate(lines):
        if re.match(r"^homeassistant\s*:\s*(#.*)?$", ln):
            ha_start = i
            break

    if ha_start is not None:
        # Fin du bloc = prochaine ligne non vide/non commentaire SANS indentation
        ha_end = len(lines)
        for j in range(ha_start + 1, len(lines)):
            ln = lines[j]
            if ln.strip() and not ln.startswith((" ", "\t", "#")):
                ha_end = j
                break
        # `packages:` déjà défini dans ce bloc ?
        for j in range(ha_start + 1, ha_end):
            if re.match(r"^\s+packages\s*:", lines[j]):
                print("[OK] homeassistant.packages deja present — rien a faire")
                return 0
        # Insertion juste après la ligne `homeassistant:`
        lines.insert(ha_start + 1, PKG_LINE)
        action = "cle packages ajoutee au bloc homeassistant existant"
    else:
        # Aucun bloc : création en tête de fichier
        lines = [HEADER, "homeassistant:", PKG_LINE, ""] + lines
        action = "bloc homeassistant.packages cree en tete de fichier"

    # ── Filet local puis écriture ─────────────────────────────────────────
    backup = args.config + ".pre-packages.bak"
    shutil.copy2(args.config, backup)
    try:
        with open(args.config, "w", encoding="utf-8", newline="") as fh:
            fh.write(eol.join(lines))
    except Exception as exc:
        print(f"[ERR] Ecriture impossible : {exc}")
        shutil.copy2(backup, args.config)
        return 1

    print(f"[OK] {action}")
    print(f"[i] Sauvegarde : {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
