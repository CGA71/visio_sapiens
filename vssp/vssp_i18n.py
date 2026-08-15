#!/usr/bin/env python3
# ============================================================================
# Visio Sapiens — i18n Engine
# ----------------------------------------------------------------------------
# EN | Single translation layer for the whole project. English is the source of
# EN | truth: every key exists in en.yaml, and any other locale is an OVERLAY
# EN | merged on top of it. A missing French key therefore falls back to
# EN | English instead of rendering an empty label in production.
# FR | Couche de traduction unique pour tout le projet. L'anglais est la source
# FR | de verite : chaque cle existe dans en.yaml, et toute autre langue est une
# FR | SURCOUCHE fusionnee par-dessus. Une cle francaise manquante retombe donc
# FR | sur l'anglais au lieu d'afficher un libelle vide en production.
#
# EN | Three consumers, one catalogue:
# EN |   1. generate_dashboards.py — Jinja2 templates call t('energy.tab.day')
# EN |   2. config-fragment.yaml   — plain files use __T:dashboard.core.title__
# EN |   3. the admin wizard       — reads the catalogue as JSON
# FR | Trois consommateurs, un seul catalogue :
# FR |   1. generate_dashboards.py — les templates Jinja2 appellent t('...')
# FR |   2. config-fragment.yaml   — les fichiers simples utilisent __T:...__
# FR |   3. le wizard admin        — lit le catalogue en JSON
#
# EN | USAGE
# FR | UTILISATION
#   python3 vssp/vssp_i18n.py check
#   python3 vssp/vssp_i18n.py render --locale fr --in a.yaml --out b.yaml
#   python3 vssp/vssp_i18n.py dump --locale fr > catalog.json
#
# EN | Dependencies: PyYAML only (available in the CI image and inside HA).
# FR | Dependances : PyYAML uniquement (present dans l'image CI et dans HA).
# ============================================================================

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required — pip install pyyaml")

# EN | Reference locale. Never remove a key from this file: it is the contract.
# FR | Langue de reference. Ne jamais retirer une cle de ce fichier : c'est le
# FR | contrat que toutes les autres langues doivent honorer.
BASE_LOCALE = "en"

# EN | Default catalogue location, relative to the repository root.
# FR | Emplacement par defaut des catalogues, relatif a la racine du depot.
DEFAULT_LOCALES_DIR = Path("home-assistant/dashboards/locales")

# EN | Placeholder syntax used in non-Jinja files: __T:some.dotted.key__
# FR | Syntaxe de substitution dans les fichiers non-Jinja : __T:cle.pointee__
PLACEHOLDER = re.compile(r"__T:([A-Za-z0-9_.]+)__")


# ----------------------------------------------------------------------------
# EN | Loading and merging
# FR | Chargement et fusion
# ----------------------------------------------------------------------------
def _read_yaml(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Locale file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Locale file must be a mapping: {path}")
    return data


def _deep_merge(base: dict, overlay: dict) -> dict:
    """
    EN | Returns base updated with overlay; nested dicts merge key by key.
    FR | Renvoie base mis a jour par overlay ; les dicts imbriques fusionnent
    FR | cle par cle.
    """
    out = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_catalog(locale: str, locales_dir: Path = DEFAULT_LOCALES_DIR) -> dict:
    """
    EN | Loads en.yaml, then merges <locale>.yaml over it. Requesting 'en'
    EN | simply returns the reference catalogue.
    FR | Charge en.yaml, puis fusionne <locale>.yaml par-dessus. Demander 'en'
    FR | renvoie simplement le catalogue de reference.
    """
    locales_dir = Path(locales_dir)
    catalog = _read_yaml(locales_dir / f"{BASE_LOCALE}.yaml")
    if locale and locale != BASE_LOCALE:
        catalog = _deep_merge(catalog, _read_yaml(locales_dir / f"{locale}.yaml"))
    return catalog


def flatten(catalog: dict, prefix: str = "") -> dict:
    """
    EN | Turns a nested catalogue into {'energy.tab.day': 'Day', ...}.
    EN | Lists are kept whole — weekday arrays must stay ordered.
    FR | Aplatit un catalogue imbrique en {'energy.tab.day': 'Day', ...}.
    FR | Les listes sont conservees telles quelles — les tableaux de jours
    FR | doivent rester ordonnes.
    """
    flat = {}
    for key, value in catalog.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(flatten(value, f"{path}."))
        else:
            flat[path] = value
    return flat


def lookup(catalog: dict, dotted_key: str):
    """
    EN | Resolves 'energy.tab.day' against the catalogue. Raises KeyError so a
    EN | typo fails the build instead of silently printing an empty label.
    FR | Resout 'energy.tab.day' dans le catalogue. Leve KeyError pour qu'une
    FR | faute de frappe casse le build plutot que d'afficher un libelle vide.
    """
    node = catalog
    for part in dotted_key.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(dotted_key)
        node = node[part]
    return node


# ----------------------------------------------------------------------------
# EN | Consumer 1 — Jinja2 (generate_dashboards.py)
# FR | Consommateur 1 — Jinja2 (generate_dashboards.py)
# ----------------------------------------------------------------------------
def jinja_context(locale: str, locales_dir: Path = DEFAULT_LOCALES_DIR) -> dict:
    """
    EN | Context to inject into the Jinja2 environment. Templates then write:
    EN |     name: "{{ t('energy.tab.day') }}"
    EN |     const LOCALE = '{{ locale_tag }}';
    FR | Contexte a injecter dans l'environnement Jinja2. Les templates ecrivent :
    FR |     name: "{{ t('energy.tab.day') }}"
    FR |     const LOCALE = '{{ locale_tag }}';
    """
    catalog = load_catalog(locale, locales_dir)
    meta = catalog.get("meta", {})
    return {
        "t": lambda key: lookup(catalog, key),
        "tr": catalog,
        "locale": meta.get("code", locale),
        "locale_tag": meta.get("locale_tag", "en-US"),
        "locale_name": meta.get("name", locale),
    }


# ----------------------------------------------------------------------------
# EN | Consumer 2 — plain files (config-fragment.yaml, CSS, JS, HTML)
# FR | Consommateur 2 — fichiers simples (config-fragment.yaml, CSS, JS, HTML)
# ----------------------------------------------------------------------------
def render_text(text: str, catalog: dict, strict: bool = True) -> tuple[str, list]:
    """
    EN | Replaces every __T:key__ placeholder. Returns (text, unknown_keys).
    FR | Remplace chaque substitution __T:cle__. Renvoie (texte, cles_inconnues).
    """
    unknown = []

    def _sub(match):
        key = match.group(1)
        try:
            value = lookup(catalog, key)
        except KeyError:
            unknown.append(key)
            return match.group(0)
        if isinstance(value, (dict, list)):
            unknown.append(f"{key} (not a scalar)")
            return match.group(0)
        return str(value)

    rendered = PLACEHOLDER.sub(_sub, text)
    if unknown and strict:
        raise KeyError("Unknown translation key(s): " + ", ".join(sorted(set(unknown))))
    return rendered, unknown


# ----------------------------------------------------------------------------
# EN | CI guard — every locale must cover every reference key
# FR | Garde-fou CI — chaque langue doit couvrir toutes les cles de reference
# ----------------------------------------------------------------------------
def check(locales_dir: Path = DEFAULT_LOCALES_DIR) -> int:
    locales_dir = Path(locales_dir)
    base = flatten(_read_yaml(locales_dir / f"{BASE_LOCALE}.yaml"))
    status = 0

    print(f"[i] Reference locale '{BASE_LOCALE}': {len(base)} key(s)")

    for path in sorted(locales_dir.glob("*.yaml")):
        code = path.stem
        if code == BASE_LOCALE:
            continue
        overlay = flatten(_read_yaml(path))
        missing = sorted(set(base) - set(overlay))
        extra = sorted(set(overlay) - set(base))

        # EN | Missing keys are tolerated (English fallback) but reported.
        # FR | Les cles manquantes sont tolerees (repli anglais) mais signalees.
        if missing:
            print(f"[warn] '{code}' falls back to English for {len(missing)} key(s):")
            for key in missing[:15]:
                print(f"         - {key}")
            if len(missing) > 15:
                print(f"         ... and {len(missing) - 15} more")

        # EN | Extra keys are an error: a typo that will never be displayed.
        # FR | Les cles en trop sont une erreur : une faute jamais affichee.
        if extra:
            status = 1
            print(f"[ERR] '{code}' declares {len(extra)} key(s) absent from '{BASE_LOCALE}':")
            for key in extra:
                print(f"         - {key}")

        if not missing and not extra:
            print(f"[OK] '{code}' fully covers the reference catalogue")

    return status


# ----------------------------------------------------------------------------
# EN | Command line
# FR | Ligne de commande
# ----------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Visio Sapiens i18n engine")
    parser.add_argument("--locales-dir", default=str(DEFAULT_LOCALES_DIR))
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="Validate every locale against the reference")

    p_render = sub.add_parser("render", help="Substitute __T:key__ placeholders in a file")
    p_render.add_argument("--locale", default=BASE_LOCALE)
    p_render.add_argument("--in", dest="src", required=True)
    p_render.add_argument("--out", dest="dst", required=True)
    p_render.add_argument("--lenient", action="store_true",
                          help="Leave unknown placeholders in place instead of failing")

    p_dump = sub.add_parser("dump", help="Print the merged catalogue as JSON")
    p_dump.add_argument("--locale", default=BASE_LOCALE)

    args = parser.parse_args()
    locales_dir = Path(args.locales_dir)

    if args.command == "check":
        return check(locales_dir)

    if args.command == "render":
        catalog = load_catalog(args.locale, locales_dir)
        src, dst = Path(args.src), Path(args.dst)
        try:
            rendered, unknown = render_text(
                src.read_text(encoding="utf-8"), catalog, strict=not args.lenient
            )
        except KeyError as exc:
            print(f"[ERR] {src}: {exc}")
            return 1
        # EN | A translated value containing ':', '#', a leading quote or a
        # EN | leading '-' can turn a valid scalar into broken YAML. We refuse
        # EN | to write a file that no longer parses rather than let the CI
        # EN | discover it three jobs later.
        # FR | Une valeur traduite contenant ':', '#', un guillemet ou un '-'
        # FR | en tete peut transformer un scalaire valide en YAML casse. On
        # FR | refuse d'ecrire un fichier qui ne parse plus, plutot que de
        # FR | laisser la CI le decouvrir trois jobs plus loin.
        if dst.suffix.lower() in {".yaml", ".yml"}:
            probe = yaml.SafeLoader
            probe.add_multi_constructor("!", lambda loader, suffix, node: None)
            try:
                yaml.load(rendered, Loader=probe)
            except yaml.YAMLError as exc:
                print(f"[ERR] Rendering '{args.locale}' produced invalid YAML: {exc}")
                print("      Quote the offending value in the locale catalogue.")
                return 1

        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(rendered, encoding="utf-8")
        note = f" ({len(unknown)} placeholder(s) left untouched)" if unknown else ""
        print(f"[OK] {src} -> {dst} rendered in '{args.locale}'{note}")
        return 0

    if args.command == "dump":
        print(json.dumps(load_catalog(args.locale, locales_dir),
                         ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
