#!/usr/bin/env python3
# ============================================================================
# Visio Sapiens — Idempotent configuration.yaml patcher
#
# EN | Merges home-assistant/config-fragment.yaml (the desired state of the
# EN | keys Visio Sapiens owns) into the destination configuration.yaml, while
# EN | PRESERVING:
# EN |   - everything else in the file (non-Visio-Sapiens keys, order,
# EN |     comments, style),
# EN |   - Home Assistant tags (!include, !secret, !include_dir_merge_named...).
# FR | Fusionne home-assistant/config-fragment.yaml (etat desire des cles gerees
# FR | par Visio Sapiens) dans le configuration.yaml de destination, en
# FR | PRESERVANT :
# FR |   - tout le reste du fichier (cles non-Visio Sapiens, ordre, commentaires,
# FR |     style),
# FR |   - les tags Home Assistant (!include, !secret, !include_dir_merge_named...).
#
# EN | Strategy: DECLARATIVE, TARGETED merge. We never append lines blindly; we
# EN | impose the desired state key by key, which makes it idempotent by
# EN | construction.
# FR | Strategie : merge DECLARATIF et CIBLE. On n'ajoute pas des lignes a
# FR | l'aveugle, on impose l'etat desire cle par cle -> idempotent par
# FR | construction.
#
# EN | Backup before any write:
# FR | Sauvegarde AVANT toute ecriture :
#   <config>/backups/configuration_YYYYMMDD_HHMMSS.bak
#
# EN | USAGE / FR | UTILISATION
#   python3 vssp_apply_config.py \
#       --config   /config/configuration.yaml \
#       --fragment /config/.osv_stage/config-fragment.yaml \
#       [--vtoken  v1.2.3]      # replaces __VTOKEN__ in the resource urls
#       [--dry-run]             # print the merge result, write nothing
#       [--prune-resources]     # drop old Visio Sapiens resources absent from the fragment
#       [--allow-placeholders]  # ESCAPE HATCH, see the guard below
#
# EN | Exit codes: 0 = OK (changed or already compliant), 1 = error.
# FR | Codes de sortie : 0 = OK (modifie ou deja conforme), 1 = erreur.
#
# EN | Dependency: ruamel.yaml (pip install ruamel.yaml)
# FR | Dependance : ruamel.yaml (pip install ruamel.yaml)
# ============================================================================
import argparse
import datetime as _dt
import os
import re
import shutil
import sys

try:
    from ruamel.yaml import YAML
    from ruamel.yaml.comments import CommentedMap, CommentedSeq
except ImportError:
    sys.stderr.write(
        "[ERR] ruamel.yaml is missing. Install it: pip install ruamel.yaml\n"
    )
    sys.exit(1)

# EN | Prefix identifying entries "owned by Visio Sapiens" (dashboards, helpers).
# FR | Prefixe identifiant les entrees « propriete de Visio Sapiens »
# FR | (dashboards, helpers).
OSV_PREFIX = "visio-sapiens"
# EN | Marker for Visio Sapiens resources: any url containing this segment is ours.
# FR | Marqueur des ressources Visio Sapiens : toute url contenant ce segment
# FR | est « a nous ».
OSV_RESOURCE_MARK = "/local/vssp/"

# EN | Top-level keys the fragment is allowed to merge. Any other fragment key
# EN | is ignored (safety rail: the patcher only ever touches this perimeter).
# FR | Cles de premier niveau que le fragment peut fusionner. Toute autre cle du
# FR | fragment est ignoree (garde-fou : le patcher ne touche que ce perimetre).
MERGEABLE_TOP_KEYS = ("lovelace", "input_text", "shell_command", "template")

# EN | Translation placeholder, substituted upstream by vssp_i18n.py. Reaching
# EN | this script means the rendering step never ran.
# FR | Substitution de traduction, remplacee en amont par vssp_i18n.py. Arriver
# FR | jusqu'ici signifie que l'etape de rendu n'a jamais tourne.
T_PLACEHOLDER = re.compile(r"__T:[A-Za-z0-9_.]+__")


def _yaml():
    y = YAML()
    y.preserve_quotes = True
    # EN | Avoid unwanted line wrapping / FR | Evite les replis de lignes intempestifs
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)
    # EN | HA tags (!include...) are preserved automatically by ruamel because
    # EN | they appear as tagged scalars; nothing to register as long as we do
    # EN | not try to interpret them.
    # FR | Les tags HA (!include...) sont preserves automatiquement par ruamel
    # FR | car ils apparaissent comme des scalaires taggues ; on n'a rien a
    # FR | enregistrer tant qu'on ne cherche pas a les interpreter.
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


# ----------------------------------------------------------------------------
# EN | GUARD — refuse an unrendered fragment
# FR | GARDE-FOU — refuser un fragment non rendu
# ----------------------------------------------------------------------------
def check_placeholders(fragment_path, allow=False):
    """
    EN | The fragment carries __T:key__ markers that vssp_i18n.py replaces with
    EN | the chosen language. If that step is skipped, the raw marker ends up in
    EN | configuration.yaml and Home Assistant displays it as a dashboard title
    EN | in the sidebar — visible to the user, and only fixable by a restart.
    EN | This patcher is the single point every path goes through (pipeline,
    EN | ADMIN panel, manual run), so the guard belongs here.
    FR | Le fragment porte des marqueurs __T:cle__ que vssp_i18n.py remplace par
    FR | la langue choisie. Si cette etape est sautee, le marqueur brut se
    FR | retrouve dans configuration.yaml et Home Assistant l'affiche comme
    FR | titre de dashboard dans la sidebar — visible par l'utilisateur, et
    FR | corrigible seulement par un redemarrage. Ce patcher est le point de
    FR | passage unique de tous les chemins (pipeline, panneau ADMIN, execution
    FR | manuelle) : le garde-fou a donc sa place ici.
    """
    with open(fragment_path, encoding="utf-8") as fh:
        raw = fh.read()
    found = sorted(set(T_PLACEHOLDER.findall(raw)))
    if not found:
        return
    head = "[WARN]" if allow else "[ERR]"
    sys.stderr.write(
        f"{head} {fragment_path} holds {len(found)} unrendered "
        f"translation placeholder(s):\n"
    )
    for item in found[:10]:
        sys.stderr.write(f"         {item}\n")
    if len(found) > 10:
        sys.stderr.write(f"         ... and {len(found) - 10} more\n")
    if allow:
        sys.stderr.write(
            "       --allow-placeholders was passed: merging them AS IS. They "
            "will show up verbatim in the Home Assistant sidebar.\n"
        )
        return
    sys.stderr.write(
        "       Render the fragment first:\n"
        "         python3 vssp/vssp_i18n.py render --locale <code> \\\n"
        "             --in <fragment> --out <rendered>\n"
        "       then pass the RENDERED file to --fragment.\n"
    )
    sys.exit(1)


def _apply_vtoken(fragment, vtoken):
    """
    EN | Replaces the __VTOKEN__ placeholder in the resource urls (cache-busting).
    FR | Remplace le placeholder __VTOKEN__ dans les url resources (cache-busting).
    """
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
    EN | Merges src_map into dst_map key by key. When only_prefix is given, only
    EN | keys starting with that prefix are written (other src keys are ignored,
    EN | dst keys preserved). Returns True if dst changed.
    FR | Fusionne src_map dans dst_map par cle. Si only_prefix est fourni, seules
    FR | les cles commencant par ce prefixe sont ecrites (les autres cles de src
    FR | sont ignorees, celles de dst preservees). Renvoie True si dst a change.
    """
    changed = False
    for key, val in src_map.items():
        if only_prefix is not None and not str(key).startswith(only_prefix):
            continue
        if key not in dst_map or dst_map[key] != val:
            dst_map[key] = val
            changed = True
    return changed


def report_skipped_keys(src_map, only_prefix, label):
    """
    EN | Names the fragment keys the prefix filter silently drops. A dashboard
    EN | declared in the fragment but never written to configuration.yaml is
    EN | invisible: it simply never appears, with no error anywhere. Saying so
    EN | out loud costs one line and saves an hour of puzzlement.
    FR | Nomme les cles du fragment que le filtre de prefixe ecarte en silence.
    FR | Un dashboard declare dans le fragment mais jamais ecrit dans
    FR | configuration.yaml est invisible : il n'apparait tout simplement pas,
    FR | sans erreur nulle part. Le dire coute une ligne et evite une heure
    FR | d'incomprehension.
    """
    if not isinstance(src_map, (dict, CommentedMap)):
        return
    skipped = [k for k in src_map if not str(k).startswith(only_prefix)]
    if skipped:
        print(f"[WARN] {label}: {len(skipped)} key(s) ignored — they do not "
              f"start with '{only_prefix}':")
        for key in skipped:
            print(f"         - {key}")
        print(f"       Rename them, or adjust OSV_PREFIX in this script.")


def _merge_resources(dst_lovelace, src_resources, prune=False):
    """
    EN | Merges the resource list by 'url' (deduplicated).
    EN |   - updates/adds the entries present in the fragment,
    EN |   - preserves the user's non-Visio-Sapiens resources,
    EN |   - with prune=True, drops Visio Sapiens resources (marked
    EN |     OSV_RESOURCE_MARK) that are NO LONGER in the fragment.
    EN | Returns True on change.
    FR | Fusionne la liste des resources par 'url' (dedoublonne).
    FR |   - met a jour/ajoute les entrees presentes dans le fragment,
    FR |   - preserve les resources non-Visio Sapiens de l'utilisateur,
    FR |   - si prune=True, retire les resources Visio Sapiens (marquees
    FR |     OSV_RESOURCE_MARK) qui ne sont PLUS dans le fragment.
    FR | Renvoie True si changement.
    """
    changed = False
    existing = dst_lovelace.get("resources")
    if not isinstance(existing, (list, CommentedSeq)):
        existing = CommentedSeq()
        dst_lovelace["resources"] = existing

    # EN | url -> position index / FR | Index url -> position
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
                # EN | drop this stale Visio Sapiens resource
                # FR | on retire cette ancienne resource Visio Sapiens
                changed = True
                continue
            keep.append(it)
        if changed:
            dst_lovelace["resources"] = keep

    return changed


def merge(config, fragment, prune_resources=False):
    """
    EN | Applies the targeted merge. Returns True if config was modified.
    FR | Applique la fusion ciblee. Renvoie True si config a ete modifie.
    """
    changed = False

    for top in MERGEABLE_TOP_KEYS:
        if top not in fragment:
            continue
        src = fragment[top]

        if top == "lovelace":
            dst = config.setdefault("lovelace", CommentedMap())
            if not isinstance(dst, CommentedMap):
                sys.stderr.write("[ERR] target 'lovelace' is not a mapping.\n")
                sys.exit(1)

            # EN | dashboards: merge per sub-key, only the visio-sapiens-* ones
            # FR | dashboards : merge par sous-cle, uniquement les visio-sapiens-*
            if "dashboards" in src:
                report_skipped_keys(src["dashboards"], OSV_PREFIX,
                                    "lovelace.dashboards")
                dboards = dst.setdefault("dashboards", CommentedMap())
                if _merge_named(dboards, src["dashboards"], only_prefix=OSV_PREFIX):
                    changed = True

            # EN | resources: merge by url / FR | resources : merge par url
            if "resources" in src:
                if _merge_resources(dst, src["resources"], prune=prune_resources):
                    changed = True

            # EN | any other lovelace sub-key (mode...): direct merge
            # FR | autres sous-cles de lovelace eventuelles (mode...) : merge direct
            for k, v in src.items():
                if k in ("dashboards", "resources"):
                    continue
                if dst.get(k) != v:
                    dst[k] = v
                    changed = True

        else:
            # EN | input_text / shell_command / template: merge per vssp_* key
            # FR | input_text / shell_command / template : merge par cle vssp_*
            dst = config.setdefault(top, CommentedMap())
            if top == "template":
                # EN | 'template' may be a list; we only merge when it is a
                # EN | mapping of prefixed helpers (rare case). Otherwise we
                # EN | leave it alone so the user's structure is not broken.
                # FR | 'template' peut etre une liste ; on ne fusionne que si
                # FR | c'est un mapping de helpers prefixes (cas rare). Sinon on
                # FR | laisse tel quel pour ne pas casser la structure de
                # FR | l'utilisateur.
                if isinstance(dst, CommentedMap) and isinstance(src, CommentedMap):
                    if _merge_named(dst, src, only_prefix=OSV_PREFIX):
                        changed = True
            else:
                if isinstance(dst, CommentedMap) and isinstance(src, CommentedMap):
                    if _merge_named(dst, src, only_prefix=OSV_PREFIX):
                        changed = True

    return changed


def main():
    ap = argparse.ArgumentParser(
        description="Idempotent configuration.yaml patcher (Visio Sapiens).")
    ap.add_argument("--config", required=True,
                    help="Path to the destination configuration.yaml")
    ap.add_argument("--fragment", required=True,
                    help="Path to the source config-fragment.yaml")
    ap.add_argument("--vtoken", default="",
                    help="Version token (replaces __VTOKEN__)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print without writing")
    ap.add_argument("--prune-resources", action="store_true",
                    help="Drop Visio Sapiens resources absent from the fragment")
    ap.add_argument("--allow-placeholders", action="store_true",
                    help="Merge a fragment that still holds __T: markers. "
                         "They will appear verbatim in the HA sidebar — only "
                         "for debugging.")
    args = ap.parse_args()

    if not os.path.isfile(args.config):
        sys.stderr.write(f"[ERR] Not found: {args.config}\n")
        sys.exit(1)
    if not os.path.isfile(args.fragment):
        sys.stderr.write(f"[ERR] Not found: {args.fragment}\n")
        sys.exit(1)

    # EN | Before anything else: a fragment that was never rendered must not
    # EN | reach configuration.yaml.
    # FR | Avant toute chose : un fragment jamais rendu ne doit pas atteindre
    # FR | configuration.yaml.
    check_placeholders(args.fragment, allow=args.allow_placeholders)

    y = _yaml()
    config = _load(args.config, y)
    fragment = _load(args.fragment, y)

    if not isinstance(config, CommentedMap):
        sys.stderr.write(
            "[ERR] The target configuration.yaml is not a YAML mapping.\n")
        sys.exit(1)

    _apply_vtoken(fragment, args.vtoken)

    changed = merge(config, fragment, prune_resources=args.prune_resources)

    if not changed:
        print("[OK] configuration.yaml already compliant — no change.")
        return

    if args.dry_run:
        print("[i] --dry-run: merge result (not written):\n")
        y.dump(config, sys.stdout)
        return

    backup = _backup(args.config)
    print(f"[OK] Backup: {backup}")

    tmp = args.config + ".osvtmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        y.dump(config, fh)
    os.replace(tmp, args.config)
    print(f"[OK] configuration.yaml updated: {args.config}")


if __name__ == "__main__":
    main()
