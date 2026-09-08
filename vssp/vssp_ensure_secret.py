#!/usr/bin/env python3
# ============================================================================
# Visio Sapiens — vssp_ensure_secret.py
#
# EN | Guarantees that a key exists in /config/secrets.yaml, adding it with
# EN | an empty value if it does not.
# FR | Garantit qu une cle existe dans /config/secrets.yaml, en l ajoutant
# FR | avec une valeur vide si elle manque.
#
# EN | WHY THIS IS NOT OPTIONAL
# EN | A package that says `!secret vault_ha_token` and a secrets.yaml that
# EN | does not define it do not produce a broken sensor: they produce a
# EN | Home Assistant that REFUSES TO START. The whole configuration fails
# EN | to load, every dashboard with it, over one missing line — and the
# EN | package ships through CI, so the breakage would arrive on an
# EN | instance whose owner never asked for the safe yet.
# EN | Seeding the key empty makes the failure proportionate: Vault
# EN | answers 403 to an empty token, the three branch sensors go
# EN | unavailable, the ADMIN screen says the safe is unreachable, and
# EN | everything else works exactly as before. Pasting the real token
# EN | then turns it on.
# FR | POURQUOI CE N EST PAS OPTIONNEL
# FR | Un package qui dit `!secret vault_ha_token` et un secrets.yaml qui
# FR | ne le definit pas ne produisent pas un capteur casse : ils
# FR | produisent un Home Assistant qui REFUSE DE DEMARRER. Toute la
# FR | configuration echoue au chargement, chaque dashboard avec elle,
# FR | pour une ligne manquante — et le package est livre par le CI, donc
# FR | la panne arriverait sur une instance dont le proprietaire n a pas
# FR | encore demande le coffre.
# FR | Amorcer la cle a vide rend la defaillance proportionnee : Vault
# FR | repond 403 a un token vide, les trois capteurs de branche passent
# FR | indisponibles, l ecran ADMIN annonce le coffre injoignable, et tout
# FR | le reste fonctionne comme avant. Coller le vrai token l allume.
#
# EN | NEVER OVERWRITES. If the key is present with any value at all —
# EN | including empty — the file is left byte for byte as it was. This
# EN | script must be incapable of destroying a credential.
# FR | N ECRASE JAMAIS. Si la cle est presente avec quelque valeur que ce
# FR | soit — vide comprise — le fichier est laisse octet pour octet tel
# FR | quel. Ce script doit etre incapable de detruire un identifiant.
#
# EN | Zero dependencies (stdlib only): surgical TEXT editing, so
# EN | comments, quoting and line endings elsewhere in the file survive
# EN | untouched. Loading and re-dumping secrets.yaml with a YAML library
# EN | would rewrite a file full of credentials to fix one line.
# FR | Zero dependance (stdlib seule) : edition TEXTUELLE chirurgicale,
# FR | donc les commentaires, les guillemets et les fins de ligne ailleurs
# FR | dans le fichier survivent intacts. Charger et re-serialiser
# FR | secrets.yaml avec une bibliotheque YAML reecrirait un fichier plein
# FR | d identifiants pour corriger une ligne.
#
# Usage :
#     python3 vssp_ensure_secret.py --config /config/secrets.yaml \
#             --key vault_ha_token
# ============================================================================
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def has_key(text: str, key: str) -> bool:
    """
    EN | True when `key` is defined at the TOP level of the document.
    EN | Anchored at column zero on purpose: secrets.yaml is a flat
    EN | mapping, and a match indented under something else — or inside a
    EN | commented-out block — is not a definition Home Assistant will
    EN | resolve.
    FR | Vrai quand `key` est definie au niveau RACINE du document.
    FR | Ancre en colonne zero a dessein : secrets.yaml est un mapping
    FR | plat, et une correspondance indentee sous autre chose — ou dans
    FR | un bloc commente — n est pas une definition que Home Assistant
    FR | resoudra.
    """
    pattern = re.compile(r"^" + re.escape(key) + r"\s*:", re.MULTILINE)
    return bool(pattern.search(text))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Idempotently seed a key in secrets.yaml (Visio Sapiens).")
    ap.add_argument("--config", required=True,
                    help="path to secrets.yaml (e.g. /config/secrets.yaml)")
    ap.add_argument("--key", required=True,
                    help="the key to guarantee, e.g. vault_ha_token")
    ap.add_argument("--comment", default=None,
                    help="one-line comment written above the key when it is "
                         "created. Ignored when the key already exists.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    path = Path(args.config)

    # EN | An absent secrets.yaml is ordinary on a fresh instance: Home
    # EN | Assistant only creates it when something needs it. Creating it
    # EN | here is the same act as adding a line to it.
    # FR | Un secrets.yaml absent est ordinaire sur une instance neuve :
    # FR | Home Assistant ne le cree que lorsque quelque chose en a besoin.
    # FR | Le creer ici est le meme geste que d y ajouter une ligne.
    text = path.read_text(encoding="utf-8") if path.is_file() else ""

    if has_key(text, args.key):
        print(f"[OK] {path}: '{args.key}' already defined — untouched")
        return 0

    block = ""
    if text and not text.endswith("\n"):
        block += "\n"
    if args.comment:
        block += f"# {args.comment}\n"
    block += f'{args.key}: ""\n'

    if args.dry_run:
        print(f"[dry-run] would append to {path}:\n{block}", end="")
        return 0

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(block)

    # EN | secrets.yaml holds credentials; it has no business being
    # EN | world-readable. Best effort — a filesystem that does not carry
    # EN | POSIX modes is not a reason to fail the deploy.
    # FR | secrets.yaml porte des identifiants ; il n a rien a faire
    # FR | lisible par tous. Au mieux — un systeme de fichiers sans modes
    # FR | POSIX n est pas une raison de faire echouer le deploiement.
    try:
        path.chmod(0o600)
    except OSError:
        pass

    print(f"[OK] {path}: '{args.key}' added, empty. "
          f"Paste the real value to activate it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
