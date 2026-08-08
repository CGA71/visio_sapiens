#!/usr/bin/env python3
# ============================================================================
# Visio Sapiens — Patcheur idempotent de configuration.yaml
#
# Fusionne home-assistant/config-fragment.yaml (état désiré des clés gérées par
# Vision Sapiens) dans le configuration.yaml de destination, en PRÉSERVANT :
#   • tout le reste du fichier (clés non-Visio Sapiens, ordre, commentaires, style),
#   • les tags Home Assistant (!include, !secret, !include_dir_merge_named...).
#
# Stratégie : merge DÉCLARATIF et CIBLÉ. On n'ajoute pas des lignes à l'aveugle,
# on impose l'état désiré clé par clé → idempotent par construction.
#
# Sauvegarde AVANT toute écriture :
#   <config>/backups/configuration_AAAAMMJJ_HHMMSS.bak
#
# Usage :
#   python3 vssp_apply_config.py \
#       --config   /config/configuration.yaml \
#       --fragment /config/.osv_stage/config-fragment.yaml \
#       [--vtoken  v1.2.3]         # remplace __VTOKEN__ dans les url resources
#       [--dry-run]                # affiche le diff sans écrire
#       [--prune-resources]        # retire les anciennes resources Visio Sapiens absentes du fragment
#
# Codes de sortie : 0 = OK (modifié ou déjà conforme), 1 = erreur.
#
# Dépendance : ruamel.yaml  (pip install ruamel.yaml)
# ============================================================================
import argparse
import datetime as _dt
import os
import shutil
import sys

try:
    from ruamel.yaml import YAML
    from ruamel.yaml.comments import CommentedMap, CommentedSeq
except ImportError:
    sys.stderr.write(
        "[ERR] ruamel.yaml manquant. Installe-le : pip install ruamel.yaml\n"
    )
    sys.exit(1)

# Préfixe identifiant les entrées « propriété de Visio Sapiens » (dashboards, helpers).
OSV_PREFIX = "vssp"
# Marqueur des ressources Visio Sapiens : toute url contenant ce segment est « à nous ».
OSV_RESOURCE_MARK = "/local/vssp/"

# Clés de premier niveau que le fragment peut fusionner. Toute autre clé du
# fragment est ignorée (garde-fou : le patcher ne touche que ce périmètre).
MERGEABLE_TOP_KEYS = ("lovelace", "input_text", "shell_command", "template")


def _yaml():
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096  # évite les repli de lignes intempestifs
    y.indent(mapping=2, sequence=4, offset=2)
    # Les tags HA (!include...) sont préservés automatiquement par ruamel car
    # ils apparaissent comme des scalaires taggés ; on n'a rien à enregistrer
    # tant qu'on ne cherche pas à les interpréter.
    return y


def _load(path, y):
    with open(path, encoding="utf-8") as fh:
        data = y.load(fh)
    return data if data is not None else CommentedMap()


def _backup(config_path):
    cfg_dir = os.path.dirname(os.path.abspath(config_path))
    backups = os.path.join(cfg_dir, "backups")
    os.makedirs(backups, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(backups, f"configuration_{stamp}.bak")
    shutil.copy2(config_path, dest)
    return dest


def _apply_vtoken(fragment, vtoken):
    """Remplace le placeholder __VTOKEN__ dans les url resources (cache-busting)."""
    if not vtoken:
        return
    lova = fragment.get("lovelace")
    if not isinstance(lova, CommentedMap):
        return
    resources = lova.get("resources")
    if not isinstance(resources, (list, CommentedSeq)):
        return
    for item in resources:
        if isinstance(item, CommentedMap) and "url" in item:
            item["url"] = str(item["url"]).replace("__VTOKEN__", vtoken)


def _merge_named(dst_map, src_map, only_prefix=None):
    """
    Fusionne src_map dans dst_map par clé.
    Si only_prefix est fourni, seules les clés commençant par ce préfixe sont
    écrites (les autres clés de src sont ignorées, celles de dst préservées).
    Retourne True si dst a changé.
    """
    changed = False
    for key, val in src_map.items():
        if only_prefix is not None and not str(key).startswith(only_prefix):
            continue
        if key not in dst_map or dst_map[key] != val:
            dst_map[key] = val
            changed = True
    return changed


def _merge_resources(dst_lovelace, src_resources, prune=False):
    """
    Fusionne la liste des resources par 'url' (dédupliqué).
    - Met à jour/ajoute les entrées présentes dans le fragment.
    - Préserve les resources non-Visio Sapiens de l'utilisateur.
    - Si prune=True, retire les resources Visio Sapiens (marquées OSV_RESOURCE_MARK)
      qui ne sont PLUS dans le fragment.
    Retourne True si changement.
    """
    changed = False
    existing = dst_lovelace.get("resources")
    if not isinstance(existing, (list, CommentedSeq)):
        existing = CommentedSeq()
        dst_lovelace["resources"] = existing

    # Index url -> position
    def url_of(item):
        return str(item.get("url")) if isinstance(item, CommentedMap) else None

    index = {url_of(it): i for i, it in enumerate(existing) if url_of(it)}

    src_urls = set()
    for item in src_resources:
        u = url_of(item)
        if u is None:
            continue
        src_urls.add(u)
        if u in index:
            if existing[index[u]] != item:
                existing[index[u]] = item
                changed = True
        else:
            existing.append(item)
            changed = True

    if prune:
        keep = CommentedSeq()
        for it in existing:
            u = url_of(it)
            is_osv = u and OSV_RESOURCE_MARK in u
            if is_osv and u not in src_urls:
                changed = True  # on retire cette ancienne resource visio sapiens
                continue
            keep.append(it)
        if changed:
            dst_lovelace["resources"] = keep

    return changed


def merge(config, fragment, prune_resources=False):
    """Applique la fusion ciblée. Retourne True si config a été modifié."""
    changed = False

    for top in MERGEABLE_TOP_KEYS:
        if top not in fragment:
            continue
        src = fragment[top]

        if top == "lovelace":
            dst = config.setdefault("lovelace", CommentedMap())
            if not isinstance(dst, CommentedMap):
                sys.stderr.write("[ERR] 'lovelace' cible n'est pas un mapping.\n")
                sys.exit(1)

            # dashboards : merge par sous-clé, uniquement les vssp-*
            if "dashboards" in src:
                dboards = dst.setdefault("dashboards", CommentedMap())
                if _merge_named(dboards, src["dashboards"], only_prefix=OSV_PREFIX):
                    changed = True

            # resources : merge par url
            if "resources" in src:
                if _merge_resources(dst, src["resources"], prune=prune_resources):
                    changed = True

            # autres sous-clés de lovelace éventuelles (mode...) : merge direct
            for k, v in src.items():
                if k in ("dashboards", "resources"):
                    continue
                if dst.get(k) != v:
                    dst[k] = v
                    changed = True

        else:
            # input_text / shell_command / template : merge par clé vssp_*
            dst = config.setdefault(top, CommentedMap())
            if top == "template":
                # 'template' peut être une liste ; on ne fusionne que si c'est
                # un mapping de helpers préfixés (cas rare). Sinon on laisse tel
                # quel pour ne pas casser la structure de l'utilisateur.
                if isinstance(dst, CommentedMap) and isinstance(src, CommentedMap):
                    if _merge_named(dst, src, only_prefix=OSV_PREFIX):
                        changed = True
            else:
                if isinstance(dst, CommentedMap) and isinstance(src, CommentedMap):
                    if _merge_named(dst, src, only_prefix=OSV_PREFIX):
                        changed = True

    return changed


def main():
    ap = argparse.ArgumentParser(description="Patch idempotent de configuration.yaml (Visio Sapiens).")
    ap.add_argument("--config", required=True, help="Chemin du configuration.yaml de destination")
    ap.add_argument("--fragment", required=True, help="Chemin du config-fragment.yaml source")
    ap.add_argument("--vtoken", default="", help="Token de version (remplace __VTOKEN__)")
    ap.add_argument("--dry-run", action="store_true", help="Affiche sans écrire")
    ap.add_argument("--prune-resources", action="store_true",
                    help="Retire les resources Visio Sapiens absentes du fragment")
    args = ap.parse_args()

    if not os.path.isfile(args.config):
        sys.stderr.write(f"[ERR] Introuvable : {args.config}\n")
        sys.exit(1)
    if not os.path.isfile(args.fragment):
        sys.stderr.write(f"[ERR] Introuvable : {args.fragment}\n")
        sys.exit(1)

    y = _yaml()
    config = _load(args.config, y)
    fragment = _load(args.fragment, y)

    if not isinstance(config, CommentedMap):
        sys.stderr.write("[ERR] Le configuration.yaml cible n'est pas un mapping YAML.\n")
        sys.exit(1)

    _apply_vtoken(fragment, args.vtoken)

    changed = merge(config, fragment, prune_resources=args.prune_resources)

    if not changed:
        print("[OK] configuration.yaml déjà conforme — aucune modification.")
        return

    if args.dry_run:
        print("[i] --dry-run : résultat de la fusion (non écrit) :\n")
        y.dump(config, sys.stdout)
        return

    backup = _backup(args.config)
    print(f"[OK] Sauvegarde : {backup}")

    tmp = args.config + ".osvtmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        y.dump(config, fh)
    os.replace(tmp, args.config)
    print(f"[OK] configuration.yaml mis à jour : {args.config}")


if __name__ == "__main__":
    main()
