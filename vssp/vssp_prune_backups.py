#!/usr/bin/env python3
# ============================================================================
# Visio Sapiens — Backup rotation
#
# EN | Every REGENERATE button (HOME/ENERGY/CORE) and every THEME/ASSIGN/ROOMS
# EN | apply writes a timestamped backup before overwriting anything —
# EN | vssp_backup_dashboard, vssp_backup_energy, vssp_backup_theme
# EN | (home-assistant/packages/*.yaml) and the backup step inside
# EN | vssp_assign_apply.py / vssp_rooms_apply.py / vssp_theme_apply.py. None
# EN | of them ever delete an old one: left alone, the directory grows
# EN | forever (found 62 files going back three weeks on the first real
# EN | instance this ran against, most of them from the same few minutes of
# EN | testing).
# EN | This script is the other half: keep the N most recent backups PER
# EN | PREFIX (home, energy, core, theme, house, design_system, ...) in a
# EN | directory, delete the rest. Run daily by vssp_maintenance.yaml — see
# EN | docs/platform/Backup_Retention.md.
# FR | Chaque bouton REGENERER (HOME/ENERGY/CORE) et chaque application
# FR | THEME/ASSIGN/ROOMS ecrit une sauvegarde horodatee avant d'ecraser quoi
# FR | que ce soit — vssp_backup_dashboard, vssp_backup_energy,
# FR | vssp_backup_theme (home-assistant/packages/*.yaml) et l'etape de
# FR | sauvegarde a l'interieur de vssp_assign_apply.py / vssp_rooms_apply.py
# FR | / vssp_theme_apply.py. Aucun d'eux ne supprime jamais une ancienne
# FR | sauvegarde : laisse tel quel, le repertoire grossit indefiniment (62
# FR | fichiers remontant a trois semaines trouves sur la premiere instance
# FR | reelle contre laquelle ceci a tourne, la plupart issus de quelques
# FR | minutes de tests).
# FR | Ce script est l'autre moitie : garder les N sauvegardes les plus
# FR | recentes PAR PREFIXE (home, energy, core, theme, house, design_system,
# FR | ...) dans un repertoire, supprimer le reste. Lance quotidiennement par
# FR | vssp_maintenance.yaml — voir docs/platform/Backup_Retention.md.
#
# EN | USAGE / FR | UTILISATION
#   python3 vssp_prune_backups.py --dir /config/vssp/backups --keep 5
#   python3 vssp_prune_backups.py --dir DIR1 --dir DIR2 --keep 5 --dry-run
#
# EN | Matches `<prefix>_<YYYYMMDD>_<HHMMSS>.yaml` — exactly what
# EN | datetime.now().strftime("%Y%m%d_%H%M%S") produces, the format every
# EN | backup step in this project already uses. A file that does not match
# EN | is left alone and reported, never guessed at.
# FR | Reconnait `<prefixe>_<AAAAMMJJ>_<HHMMSS>.yaml` — exactement ce que
# FR | produit datetime.now().strftime("%Y%m%d_%H%M%S"), le format que
# FR | chaque etape de sauvegarde de ce projet utilise deja. Un fichier qui
# FR | ne correspond pas est laisse tel quel et signale, jamais devine.
# ============================================================================
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

TIMESTAMPED_RE = re.compile(r"^(?P<prefix>.+)_(?P<stamp>\d{8}_\d{6})\.ya?ml$")


def group_by_prefix(directory: Path) -> tuple[dict[str, list[Path]], list[Path]]:
    """
    EN | Splits a directory's files into {prefix: [files sorted oldest-first]}
    EN | plus a separate list of files that do not match the naming
    EN | convention at all (never touched).
    FR | Repartit les fichiers d'un repertoire en {prefixe: [fichiers tries du
    FR | plus ancien au plus recent]}, plus une liste separee des fichiers qui
    FR | ne correspondent pas du tout a la convention de nommage (jamais
    FR | touches).
    """
    groups: dict[str, list[Path]] = {}
    unmatched: list[Path] = []
    for f in sorted(directory.iterdir()):
        if not f.is_file():
            continue
        m = TIMESTAMPED_RE.match(f.name)
        if not m:
            unmatched.append(f)
            continue
        groups.setdefault(m.group("prefix"), []).append(f)
    # EN | The timestamp format sorts correctly as plain text, but sorting by
    # EN | mtime instead of by filename survives a backup restored from
    # EN | elsewhere with a different mtime than its name implies.
    # FR | Le format d'horodatage se trie correctement en texte brut, mais
    # FR | trier par mtime plutot que par nom de fichier survit a une
    # FR | sauvegarde restauree d'ailleurs avec une mtime differente de ce que
    # FR | son nom suggere.
    for files in groups.values():
        files.sort(key=lambda p: p.stat().st_mtime)
    return groups, unmatched


def prune_directory(directory: Path, keep: int, dry_run: bool) -> dict:
    """
    EN | Prunes one directory. Returns a per-prefix report; never raises on a
    EN | missing directory (nothing to prune yet is not an error).
    FR | Purge un repertoire. Renvoie un rapport par prefixe ; ne leve jamais
    FR | si le repertoire est absent (rien a purger n'est pas une erreur).
    """
    report: dict = {"directory": str(directory), "kept": {}, "deleted": {}, "unmatched": []}
    if not directory.is_dir():
        report["skipped"] = "directory does not exist"
        return report

    groups, unmatched = group_by_prefix(directory)
    report["unmatched"] = [f.name for f in unmatched]

    for prefix, files in sorted(groups.items()):
        to_keep = files[-keep:] if keep > 0 else files
        to_delete = files[:-keep] if keep > 0 else []
        report["kept"][prefix] = [f.name for f in to_keep]
        report["deleted"][prefix] = [f.name for f in to_delete]
        for f in to_delete:
            if not dry_run:
                f.unlink()
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", dest="dirs", action="append", required=True,
                     help="Directory to prune. Repeatable.")
    ap.add_argument("--keep", type=int, default=5,
                     help="Backups to keep per prefix (default: 5)")
    ap.add_argument("--dry-run", action="store_true",
                     help="Report what would be deleted, delete nothing")
    ap.add_argument("--status-file", default=None)
    args = ap.parse_args()

    status = {
        "ok": True,
        "dry_run": args.dry_run,
        "keep": args.keep,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "directories": [],
    }

    total_deleted = 0
    for raw_dir in args.dirs:
        report = prune_directory(Path(raw_dir), args.keep, args.dry_run)
        status["directories"].append(report)

        if report.get("skipped"):
            print(f"[i] {report['directory']}: {report['skipped']}")
            continue

        n_deleted = sum(len(v) for v in report["deleted"].values())
        total_deleted += n_deleted
        verb = "would delete" if args.dry_run else "deleted"
        print(f"[i] {report['directory']}: {len(report['kept'])} prefix(es), "
              f"{verb} {n_deleted} file(s)")
        for prefix, deleted in sorted(report["deleted"].items()):
            if deleted:
                print(f"      {prefix}: kept {len(report['kept'][prefix])}, "
                      f"{verb} {len(deleted)}")
        if report["unmatched"]:
            print(f"      {len(report['unmatched'])} file(s) do not match "
                  f"<prefix>_<YYYYMMDD>_<HHMMSS>.yaml — left untouched: "
                  f"{', '.join(report['unmatched'][:5])}"
                  f"{' ...' if len(report['unmatched']) > 5 else ''}")

    tag = "[dry-run]" if args.dry_run else "[OK]"
    verb_total = "would be pruned" if args.dry_run else "pruned"
    print(f"{tag} {total_deleted} file(s) {verb_total} in total")

    if args.status_file:
        try:
            sp = Path(args.status_file)
            sp.parent.mkdir(parents=True, exist_ok=True)
            sp.write_text(json.dumps(status, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        except OSError as exc:
            print(f"[warn] status file not written: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
