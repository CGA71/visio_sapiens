#!/usr/bin/env python3
# ============================================================================
# Visio Sapiens — vssp_sanitize_resources.py
#
# Corrige l'effet du bug de fusion de lovelace.resources : le patcher
# déduplique par URL COMPLÈTE, or le CI change le `?v=<token>` à chaque
# build — chaque déploiement AJOUTAIT donc 6 entrées au lieu de les
# remplacer (constaté : 342 entrées accumulées sur ~57 déploiements).
#
# Ce script déduplique la liste `resources:` par URL DE BASE (sans query
# string), en conservant la DERNIÈRE occurrence de chaque fichier — c'est
# toujours celle portant le token le plus récent, le patcher ajoutant en
# fin de liste. Idempotent : au 2e passage, plus rien à faire.
#
# Zéro dépendance (stdlib) : édition textuelle — tout ce qui est hors du
# bloc `resources:` est préservé octet pour octet.
#
# Usage :  python3 vssp_sanitize_resources.py --config /config/configuration.yaml
# Sortie : 0 si OK (nettoyé ou déjà propre), 1 si erreur.
# ============================================================================
import argparse
import re
import shutil
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description="Deduplique lovelace.resources")
    ap.add_argument("--config", required=True, help="Chemin de configuration.yaml")
    args = ap.parse_args()

    try:
        with open(args.config, encoding="utf-8", newline="") as fh:
            text = fh.read()
    except FileNotFoundError:
        print(f"[ERR] {args.config} introuvable")
        return 1

    eol = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(eol)

    # ── Localiser le bloc `resources:` (indenté sous lovelace:) ───────────
    res_idx = None
    for i, ln in enumerate(lines):
        if re.match(r"^\s+resources\s*:\s*(#.*)?$", ln):
            res_idx = i
            break
    if res_idx is None:
        print("[OK] Pas de bloc resources — rien a faire")
        return 0

    res_indent = len(lines[res_idx]) - len(lines[res_idx].lstrip())

    # Fin du bloc : première ligne non vide, NON commentaire, dont
    # l'indentation est <= celle de `resources:` (clé sœur ou clé racine).
    # Un commentaire ne termine jamais un bloc YAML — ceux rencontrés en
    # pleine liste (déplacés là par les fusions successives) sont collectés
    # et réémis à la fin du bloc, devant la clé suivante.
    end = len(lines)
    for j in range(res_idx + 1, len(lines)):
        ln = lines[j]
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        indent = len(ln) - len(ln.lstrip())
        if indent <= res_indent:
            end = j
            break

    block = lines[res_idx + 1 : end]

    # ── Parser les entrées `- url:` (+ lignes suivantes de la même entrée) ─
    entries = []          # [(base_url, [lignes de l entree])]
    preamble = []         # commentaires AVANT la premiere entree (conserves)
    displaced = []        # commentaires pleine-marge egares DANS la liste
    current = None
    for ln in block:
        stripped = ln.strip()
        indent = len(ln) - len(ln.lstrip())
        if stripped.startswith("#") and indent <= res_indent:
            displaced.append(ln)
            continue
        if re.match(r"^\s*-\s+url\s*:", ln):
            if current:
                entries.append(current)
            url = ln.split("url:", 1)[1].strip().strip("'\"")
            base = url.split("?", 1)[0]
            current = (base, [ln])
        elif current:
            current[1].append(ln)
        else:
            preamble.append(ln)
    if current:
        entries.append(current)

    if not entries:
        print("[OK] Bloc resources vide — rien a faire")
        return 0

    # ── Dédup par URL de base, DERNIÈRE occurrence gagnante, ordre stable ──
    latest = {}
    order = []
    for base, entry_lines in entries:
        if base not in latest:
            order.append(base)
        latest[base] = entry_lines
    removed = len(entries) - len(order)

    if removed == 0:
        print(f"[OK] {len(entries)} ressource(s), aucune dupliquee — rien a faire")
        return 0

    new_block = list(preamble)
    for base in order:
        new_block.extend(latest[base])
    if displaced:
        new_block.append("")
        new_block.extend(displaced)

    lines = lines[: res_idx + 1] + new_block + lines[end:]

    backup = args.config + ".pre-sanitize.bak"
    shutil.copy2(args.config, backup)
    try:
        with open(args.config, "w", encoding="utf-8", newline="") as fh:
            fh.write(eol.join(lines))
    except Exception as exc:
        print(f"[ERR] Ecriture impossible : {exc}")
        shutil.copy2(backup, args.config)
        return 1

    print(f"[OK] {removed} doublon(s) supprime(s) — {len(order)} ressource(s) conservee(s)")
    print(f"[i] Sauvegarde : {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
