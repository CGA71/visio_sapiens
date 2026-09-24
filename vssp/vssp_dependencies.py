#!/usr/bin/env python3
# Visio Sapiens - Neural Home Interface for Home Assistant
# Copyright (C) 2026 Expanse IT <expanse-it@outlook.fr>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301 USA.


# ============================================================================
# Visio Sapiens — vssp_dependencies.py
#
# EN | WHAT THIS IS FOR. A Visio Sapiens dashboard is not made of Home
# EN | Assistant's built-in cards. It is drawn with a dozen community cards
# EN | installed through HACS, and it is driven by five files of its own
# EN | (vssp.css, vssp.js and three web components) that Home Assistant will
# EN | only load if they are REGISTERED as Lovelace resources.
# EN | A deployment copies those five files onto the instance. Nothing
# EN | registered them, and nothing installed the cards.
# EN | On the development pod it never showed: the resources had been added
# EN | by hand years ago and every card was already installed. On a freshly
# EN | deployed Home Assistant OS box — and on any HACS user's first
# EN | install — the same release produced an ADMIN console with error
# EN | cards reading "Custom element doesn't exist" and no styling at all,
# EN | because the stylesheet and the engine were sitting in /config/www
# EN | unread. Same files, same dashboards, completely different screen.
# FR | A QUOI CECI SERT. Un dashboard Visio Sapiens n'est pas fait des
# FR | cartes natives de Home Assistant. Il est dessine avec une douzaine de
# FR | cartes communautaires installees via HACS, et il est anime par cinq
# FR | fichiers qui lui appartiennent (vssp.css, vssp.js et trois composants
# FR | web) que Home Assistant ne chargera que s'ils sont ENREGISTRES comme
# FR | ressources Lovelace.
# FR | Un deploiement copie ces cinq fichiers sur l'instance. Rien ne les
# FR | enregistrait, et rien n'installait les cartes.
# FR | Sur le pod de developpement cela ne se voyait pas : les ressources y
# FR | avaient ete ajoutees a la main il y a longtemps et chaque carte etait
# FR | deja installee. Sur une machine Home Assistant OS fraichement
# FR | deployee — et chez n'importe quel utilisateur HACS a sa premiere
# FR | installation — la meme version produisait une console ADMIN avec des
# FR | cartes d'erreur « Custom element doesn't exist » et aucun style, la
# FR | feuille de style et le moteur restant dans /config/www sans etre lus.
# FR | Memes fichiers, memes dashboards, ecran completement different.
#
# EN | WHY A BUTTON RATHER THAN THE PIPELINE. Installing these belongs to
# EN | the instance, not to the release: the pipeline cannot reach the HACS
# EN | of someone who installed Visio Sapiens from the HACS store, and a
# EN | deployment that silently downloads a dozen third-party repositories
# EN | is not something an owner asked for. So it is a press, in the UPDATE
# EN | screen, next to the other things that install: you see what is
# EN | missing, why it is needed, and then you decide.
# FR | POURQUOI UN BOUTON PLUTOT QUE LE PIPELINE. Installer tout cela
# FR | appartient a l'instance, pas a la livraison : le pipeline ne peut pas
# FR | atteindre le HACS de quelqu'un qui a installe Visio Sapiens depuis le
# FR | magasin HACS, et un deploiement qui telecharge en silence une
# FR | douzaine de depots tiers n'est pas une chose qu'un proprietaire a
# FR | demandee. C'est donc une pression, dans l'ecran MISES A JOUR, a cote
# FR | des autres choses qui installent : on voit ce qui manque, pourquoi
# FR | c'est necessaire, et on decide.
#
# EN | WHAT IT DOES
# EN |   --action check    reports, changes nothing.
# EN |   --action install  downloads the missing HACS repositories through
# EN |                     HACS's own websocket API, then registers (or
# EN |                     re-stamps) the Visio Sapiens resources.
# FR | CE QU'IL FAIT
# FR |   --action check    rapporte, ne change rien.
# FR |   --action install  telecharge les depots HACS manquants via l'API
# FR |                     websocket de HACS, puis enregistre (ou re-tamponne)
# FR |                     les ressources Visio Sapiens.
#
# EN | STORAGE MODE VS YAML MODE. Lovelace keeps its resource list in one of
# EN | two places and they are not interchangeable. In YAML mode the list is
# EN | the `lovelace: resources:` block of configuration.yaml — the block
# EN | this project already writes — and the websocket registry refuses to
# EN | be written at all. In storage mode, which is the default and what
# EN | every ordinary install runs, that block is ignored entirely and only
# EN | the registry counts. This script writes the registry and says so when
# EN | there is nothing for it to do.
# FR | MODE STORAGE CONTRE MODE YAML. Lovelace garde sa liste de ressources
# FR | dans l'un de deux endroits, et ils ne sont pas interchangeables. En
# FR | mode YAML la liste est le bloc `lovelace: resources:` de
# FR | configuration.yaml — le bloc que ce projet ecrit deja — et le registre
# FR | websocket refuse d'etre ecrit. En mode storage, qui est le defaut et
# FR | ce que fait tourner toute installation ordinaire, ce bloc est ignore
# FR | et seul le registre compte. Ce script ecrit le registre, et le dit
# FR | quand il n'a rien a y faire.
#
# EN | THE CACHE STAMP. `/local` is cached by browsers for 31 days, so a
# EN | file replaced by a deployment keeps rendering as its old self until
# EN | the resource URL changes. Each Visio Sapiens resource is therefore
# EN | registered as `?v=<sha1 of its content>`: a build that changed
# EN | nothing keeps the same stamp and nothing reloads, a build that
# EN | changed the file gets a new one and every browser fetches it.
# FR | LE TAMPON DE CACHE. `/local` est mis en cache 31 jours par les
# FR | navigateurs, donc un fichier remplace par un deploiement continue de
# FR | s'afficher tel qu'il etait jusqu'a ce que l'URL de la ressource
# FR | change. Chaque ressource Visio Sapiens est donc enregistree en
# FR | `?v=<sha1 de son contenu>` : un build qui n'a rien change garde le
# FR | meme tampon et rien ne se recharge, un build qui a change le fichier
# FR | en recoit un nouveau et chaque navigateur le retelecharge.
#
# EN | USAGE / FR | UTILISATION
#   python3 vssp_dependencies.py --action check
#   python3 vssp_dependencies.py --action install
#
# EN | Exit codes: 0 = nothing missing / everything installed, 1 = something
# EN | is still missing or could not be done. The report and the status file
# EN | are always written, so the screen can explain a failure instead of
# EN | going quiet.
# FR | Codes de sortie : 0 = rien ne manque / tout est installe, 1 = quelque
# FR | chose manque encore ou n'a pas pu etre fait. Le rapport et le fichier
# FR | d'etat sont toujours ecrits, pour que l'ecran puisse expliquer un
# FR | echec au lieu de rester muet.
# ============================================================================
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from vssp_ws import WSError, connected, resolve_token

BASE_LOCALE = "en"
SUPPORTED_LOCALES = ("en", "fr")


# ── EN | The dependency list / FR | La liste des dependances ─────────────
# EN | One entry per thing a Visio Sapiens dashboard cannot be drawn
# EN | without, and each one says WHAT NEEDS IT. That sentence is the whole
# EN | point of the screen: a list of twelve repository names asks you to
# EN | trust it, a list that says "the energy graphs" beside apexcharts-card
# EN | lets you check it.
# EN | `folder` is the directory HACS creates, which is also the middle
# EN | segment of the /hacsfiles/<folder>/<file> URL — and, for every
# EN | repository here, the last segment of its GitHub full name. Matching
# EN | on that rather than hard-coding "owner/repo" means an owner who
# EN | renames their account, or a repository that moved, does not turn into
# EN | a wrong download from this file.
# FR | Une entree par chose sans laquelle un dashboard Visio Sapiens ne peut
# FR | pas etre dessine, et chacune dit CE QUI EN A BESOIN. Cette phrase est
# FR | tout l'interet de l'ecran : une liste de douze noms de depots demande
# FR | qu'on lui fasse confiance, une liste qui dit « les graphiques
# FR | d'energie » a cote d'apexcharts-card permet de verifier.
# FR | `folder` est le repertoire que cree HACS, qui est aussi le segment du
# FR | milieu de l'URL /hacsfiles/<folder>/<fichier> — et, pour chaque depot
# FR | present ici, le dernier segment de son nom complet GitHub. Faire la
# FR | correspondance la-dessus plutot que de coder « owner/repo » en dur
# FR | evite qu'un proprietaire qui renomme son compte, ou un depot qui
# FR | demenage, ne se transforme en mauvais telechargement depuis ce
# FR | fichier.
PLUGINS = [
    ("button-card",
     "Every tile, button and panel of the interface.",
     "Chaque tuile, bouton et panneau de l'interface."),
    ("lovelace-card-mod",
     "The styling of the navigation rail and of the cards.",
     "L'habillage du bandeau de navigation et des cartes."),
    ("lovelace-layout-card",
     "The page layouts (grid-layout, vertical-layout).",
     "Les mises en page (grid-layout, vertical-layout)."),
    ("vertical-stack-in-card",
     "Panels stacked inside a single frame.",
     "Les panneaux empiles dans un meme cadre."),
    ("apexcharts-card",
     "The energy and history graphs.",
     "Les graphiques d'energie et d'historique."),
    ("mini-graph-card",
     "The compact curves of the room pages.",
     "Les courbes compactes des pages de piece."),
    ("config-template-card",
     "Cards whose configuration depends on a state.",
     "Les cartes dont la configuration depend d'un etat."),
    ("decluttering-card",
     "The shared card templates.",
     "Les gabarits de cartes partages."),
    ("lovelace-mushroom",
     "The vacuum panel of the entrance hall.",
     "Le panneau du robot aspirateur de l'entree."),
    ("simple-weather-card",
     "The weather cell of the header band.",
     "La case meteo du bandeau d'en-tete."),
    ("dynamic-weather-card",
     "The weather panel of the HOME dashboard.",
     "Le panneau meteo du dashboard HOME."),
    ("calendar-card-pro",
     "The agenda panel.",
     "Le panneau agenda."),
]

# EN | Integrations are a different kind of dependency: HACS puts files in
# EN | custom_components/, and Home Assistant only loads them at the next
# EN | restart. The screen has to say that, or the press looks like it did
# EN | nothing.
# FR | Les integrations sont une dependance d'une autre nature : HACS depose
# FR | des fichiers dans custom_components/, et Home Assistant ne les charge
# FR | qu'au redemarrage suivant. L'ecran doit le dire, sinon la pression a
# FR | l'air de n'avoir rien fait.
INTEGRATIONS = [
    ("browser_mod",
     "The pop-ups of the ADMIN console (AI setup, confirmations).",
     "Les fenetres de la console ADMIN (configuration IA, confirmations)."),
]

# EN | The fallback list, used only when config-fragment.yaml cannot be read
# EN | on the instance. The fragment is the real source: an asset added
# EN | there is picked up here without touching this file.
# FR | La liste de secours, utilisee seulement si config-fragment.yaml n'est
# FR | pas lisible sur l'instance. Le fragment est la vraie source : un actif
# FR | ajoute la-bas est repris ici sans toucher a ce fichier.
FALLBACK_RESOURCES = [
    ("/local/vssp/css/vssp.css", "css"),
    ("/local/vssp/js/vssp.js", "module"),
    ("/local/vssp/components/vssp-core.js", "module"),
    ("/local/vssp/components/vssp-card.js", "module"),
    ("/local/vssp/components/vssp-datetime-card.js", "module"),
]

MESSAGES = {
    "no_token": {
        "en": "Home Assistant token missing - fill input_text.vssp_ha_token "
              "in the ADMIN console, then press SAVE TOKEN.",
        "fr": "Jeton Home Assistant absent - renseignez "
              "input_text.vssp_ha_token dans la console ADMIN puis lancez "
              "ENREGISTRER LE JETON.",
    },
    "ws_down": {
        "en": "Home Assistant did not answer on its websocket API: {err}",
        "fr": "Home Assistant n'a pas repondu sur son API websocket : {err}",
    },
    "no_hacs": {
        "en": "HACS is not installed on this instance. Install it first "
              "(hacs.xyz), then press this button again: the cards below "
              "cannot be downloaded without it.",
        "fr": "HACS n'est pas installe sur cette instance. Installez-le "
              "d'abord (hacs.xyz) puis repressez ce bouton : les cartes "
              "ci-dessous ne peuvent pas etre telechargees sans lui.",
    },
    "all_ok": {
        "en": "Every dependency is in place.",
        "fr": "Chaque dependance est en place.",
    },
    "missing": {
        "en": "{n} dependency(ies) missing. Press INSTALL DEPENDENCIES.",
        "fr": "{n} dependance(s) manquante(s). Pressez INSTALLER LES "
              "DEPENDANCES.",
    },
    "installed": {
        "en": "{n} dependency(ies) installed. Reload the page with "
              "Ctrl+Shift+R.",
        "fr": "{n} dependance(s) installee(s). Rechargez la page avec "
              "Ctrl+Maj+R.",
    },
    "installed_restart": {
        "en": "{n} dependency(ies) installed, {i} of them integration(s): "
              "restart Home Assistant, then reload the page with "
              "Ctrl+Shift+R.",
        "fr": "{n} dependance(s) installee(s), dont {i} integration(s) : "
              "redemarrez Home Assistant puis rechargez la page avec "
              "Ctrl+Maj+R.",
    },
    "partial": {
        "en": "{n} dependency(ies) could not be installed - see the rows "
              "below.",
        "fr": "{n} dependance(s) n'ont pas pu etre installees - voir les "
              "lignes ci-dessous.",
    },
    "yaml_mode": {
        "en": "Lovelace runs in YAML mode: its resources come from "
              "configuration.yaml, which the deployment already writes. "
              "Nothing to register here.",
        "fr": "Lovelace tourne en mode YAML : ses ressources viennent de "
              "configuration.yaml, que le deploiement ecrit deja. Rien a "
              "enregistrer ici.",
    },
    "running": {
        "en": "Installation in progress...",
        "fr": "Installation en cours...",
    },
}

STATE_LABELS = {
    "ok":      {"en": "installed",      "fr": "installee"},
    "added":   {"en": "installed",      "fr": "installee"},
    "missing": {"en": "missing",        "fr": "manquante"},
    "failed":  {"en": "failed",         "fr": "echec"},
    "no_file": {"en": "file absent",    "fr": "fichier absent"},
    "unknown": {"en": "not in HACS",    "fr": "absente de HACS"},
    "restart": {"en": "restart needed", "fr": "redemarrage requis"},
    "stale":   {"en": "cache stamp outdated",
               "fr": "tampon de cache perime"},
    "legacy":  {"en": "obsolete",       "fr": "obsolete"},
    "skipped": {"en": "not applicable", "fr": "sans objet"},
}


# EN | The /local prefixes this project has shipped under. A resource
# EN | pointing inside one of them, whose file is not on disk, is our own
# EN | leftover and nobody else's - the osvision_v2 names date from before
# EN | the project was called Visio Sapiens. Anything else under /local
# EN | belongs to the owner and is never touched, however broken it looks.
# FR | Les prefixes /local sous lesquels ce projet a livre. Une ressource
# FR | pointant dans l'un d'eux, dont le fichier n'est pas sur le disque,
# FR | est notre propre reste et celui de personne d'autre - les noms
# FR | osvision_v2 datent d'avant que le projet s'appelle Visio Sapiens.
# FR | Tout le reste sous /local appartient au proprietaire et n'est jamais
# FR | touche, aussi casse que cela paraisse.
OUR_NAMESPACES = ("/local/vssp/", "/local/osvision_v2/", "/local/osvision/")


# ── EN | Language / FR | Langue ──────────────────────────────────────────
def pick_locale(value: str) -> str:
    code = (value or "").strip().lower().replace("_", "-").split("-")[0]
    return code if code in SUPPORTED_LOCALES else BASE_LOCALE


def msg(key: str, locale: str, **fields) -> str:
    entry = MESSAGES.get(key, {})
    text = entry.get(locale) or entry.get(BASE_LOCALE) or key
    return text.format(**fields) if fields else text


def say(key: str, locale: str, **fields) -> dict:
    return {"message_key": key,
            "message_vars": fields,
            "message": msg(key, locale, **fields)}


def label_of(state: str, locale: str) -> str:
    entry = STATE_LABELS.get(state, {})
    return entry.get(locale) or entry.get(BASE_LOCALE) or state


# ── EN | Files the screen reads / FR | Fichiers lus par l'ecran ──────────
def write_json(path: str, payload: dict) -> None:
    """EN | Written after every step, not once at the end: an install that
    EN | is killed halfway - a shell_command hitting its timeout, a box
    EN | rebooting - must still leave the screen saying how far it got.
    FR | Ecrit apres chaque etape, pas une fois a la fin : une installation
    FR | interrompue en cours de route - un shell_command qui atteint son
    FR | delai, une machine qui redemarre - doit tout de meme laisser
    FR | l'ecran capable de dire jusqu'ou elle est allee."""
    payload["generated"] = datetime.now().isoformat(timespec="seconds")
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                       encoding="utf-8")
        tmp.replace(p)
    except OSError as exc:
        print(f"[warn] {path} not written: {exc}", file=sys.stderr)


def rest_get(url: str, token: str, path: str):
    req = urllib.request.Request(
        url.rstrip("/") + path,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None


def detect_locale(explicit: str, url: str, token: str) -> str:
    """EN | The selector first, because it is what the console shows; then
    EN | the file the deployment leaves behind, because a fresh instance may
    EN | not have the selector yet; then English.
    FR | Le selecteur d'abord, parce que c'est ce qu'affiche la console ;
    FR | puis le fichier laisse par le deploiement, parce qu'une instance
    FR | neuve peut ne pas encore avoir le selecteur ; puis l'anglais."""
    if explicit and explicit.strip().lower() not in ("", "auto", "unknown"):
        return pick_locale(explicit)
    state = rest_get(url, token, "/api/states/input_select.vssp_language")
    if isinstance(state, dict) and state.get("state"):
        return pick_locale(state["state"])
    try:
        return pick_locale(Path("/config/VSSP_LOCALE").read_text(
            encoding="utf-8"))
    except OSError:
        return BASE_LOCALE


# ── EN | The Visio Sapiens resources / FR | Les ressources Visio Sapiens ──
def stamp(file_path: Path) -> str:
    """EN | The cache stamp is a hash of the CONTENT, not a build number: a
    EN | release that did not change vssp.css must not make every browser in
    EN | the house re-download it, and a hand-edit that the pipeline never
    EN | saw must not be served from a month-old cache.
    FR | Le tampon de cache est une empreinte du CONTENU, pas un numero de
    FR | build : une livraison qui n'a pas change vssp.css ne doit pas faire
    FR | retelecharger le fichier a tous les navigateurs de la maison, et
    FR | une retouche a la main que le pipeline n'a jamais vue ne doit pas
    FR | etre servie depuis un cache vieux d'un mois."""
    h = hashlib.sha1()
    h.update(file_path.read_bytes())
    return h.hexdigest()[:8]


def declared_resources(fragment: str) -> list:
    """EN | The list of Visio Sapiens resources, read from the config
    EN | fragment the project already maintains rather than repeated here.
    EN | Only the /local entries: the /hacsfiles ones are HACS's business
    EN | and HACS registers them itself on a storage-mode instance.
    FR | La liste des ressources Visio Sapiens, lue dans le fragment de
    FR | configuration que le projet maintient deja plutot que repetee ici.
    FR | Seules les entrees /local : celles en /hacsfiles regardent HACS,
    FR | qui les enregistre lui-meme sur une instance en mode storage."""
    try:
        import yaml  # noqa: PLC0415  (optional, and only needed here)

        # EN | The fragment is Home Assistant YAML, not plain YAML: it
        # EN | carries !include_dir_named and friends, and a safe loader
        # EN | stops dead on the first one - which would silently send this
        # EN | function to its fallback list and make the claim above
        # EN | ("the fragment is the real source") false. Unknown ! tags are
        # EN | therefore read as None: nothing here needs their value, only
        # EN | the resources list beside them.
        # FR | Le fragment est du YAML Home Assistant, pas du YAML ordinaire:
        # FR | il porte !include_dir_named et consorts, et un chargeur sur
        # FR | lequel on s'appuie s'arrete net au premier - ce qui enverrait
        # FR | en silence cette fonction vers sa liste de secours et rendrait
        # FR | fausse l'affirmation ci-dessus (« le fragment est la vraie
        # FR | source »). Les tags ! inconnus sont donc lus comme None : rien
        # FR | ici n'a besoin de leur valeur, seulement de la liste de
        # FR | ressources a cote d'eux.
        class _HALoader(yaml.SafeLoader):
            pass

        _HALoader.add_multi_constructor(
            "!", lambda loader, suffix, node: None)
        data = yaml.load(Path(fragment).read_text(encoding="utf-8"),
                         Loader=_HALoader)
        entries = ((data or {}).get("lovelace") or {}).get("resources") or []
    except Exception:                                    # noqa: BLE001
        entries = []
    out = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        url = str(e.get("url") or "")
        if not url.startswith("/local/"):
            continue
        out.append((url.split("?", 1)[0], str(e.get("type") or "module")))
    return out or list(FALLBACK_RESOURCES)


def local_file(url_base: str, www_root: str) -> Path:
    return Path(www_root) / url_base[len("/local/"):]


# ── EN | HACS / FR | HACS ────────────────────────────────────────────────
def find_repo(repos: list, category: str, needle: str) -> dict | None:
    """EN | A plugin is found by its FOLDER - the name HACS gives the
    EN | directory, which is the last segment of the repository's full name
    EN | and the middle segment of its /hacsfiles URL. An integration is
    EN | found by its DOMAIN, because there the folder and the repository
    EN | name differ (hass-browser_mod installs browser_mod) and the domain
    EN | is the only stable identity.
    FR | Un plugin se trouve par son DOSSIER - le nom que HACS donne au
    FR | repertoire, qui est le dernier segment du nom complet du depot et
    FR | le segment du milieu de son URL /hacsfiles. Une integration se
    FR | trouve par son DOMAINE, car la le dossier et le nom du depot
    FR | different (hass-browser_mod installe browser_mod) et le domaine est
    FR | la seule identite stable."""
    needle = needle.lower()
    for r in repos:
        if not isinstance(r, dict) or r.get("category") != category:
            continue
        if category == "integration":
            if str(r.get("domain") or "").lower() == needle:
                return r
            continue
        full = str(r.get("full_name") or "").rstrip("/").split("/")[-1].lower()
        local = str(r.get("local_path") or "").rstrip("/").split("/")[-1].lower()
        if needle in (full, local):
            return r
    return None


def download(ws, repo: dict) -> str:
    """EN | Returns "" on success, the error sentence otherwise.
    FR | Renvoie "" en cas de succes, la phrase d'erreur sinon."""
    try:
        ws.command({"type": "hacs/repository/download",
                    "repository": str(repo.get("id"))})
        return ""
    except (WSError, OSError) as exc:
        return str(exc) or exc.__class__.__name__


# ── EN | The run / FR | L'execution ──────────────────────────────────────
def run(args) -> int:
    install = args.action == "install"
    token = resolve_token(args.token, args.token_file)
    locale = detect_locale(args.locale, args.url, token or "")

    report = {"action": args.action, "running": install, "items": [],
              "counts": {"total": 0, "ok": 0, "missing": 0, "failed": 0,
                         "installed": 0},
              "hacs": {"available": False, "error": ""},
              "resources_mode": "unknown",
              "restart_required": False, "reload_required": False}

    def row(kind, key, name, state, why="", detail=""):
        report["items"].append({"kind": kind, "key": key, "name": name,
                                "state": state,
                                "state_label": label_of(state, locale),
                                "why": why, "detail": detail})

    def publish(ok: bool, key: str, **fields) -> None:
        c = report["counts"]
        c["total"] = len(report["items"])
        c["ok"] = sum(1 for i in report["items"] if i["state"] == "ok")
        c["installed"] = sum(1 for i in report["items"]
                             if i["state"] in ("added", "restart"))
        c["missing"] = sum(1 for i in report["items"]
                           if i["state"] in ("missing", "unknown", "stale"))
        c["failed"] = sum(1 for i in report["items"]
                          if i["state"] in ("failed", "no_file"))
        report["ok"] = ok
        write_json(args.out, report)
        write_json(args.status, {"ok": ok, **say(key, locale, **fields)})

    if not token:
        publish(False, "no_token")
        print("[ERR] no Home Assistant token", file=sys.stderr)
        return 1

    if install:
        publish(True, "running")

    try:
        ws = connected(args.url, token, timeout=args.timeout)
    except (WSError, OSError) as exc:
        publish(False, "ws_down", err=str(exc) or exc.__class__.__name__)
        print(f"[ERR] websocket: {exc}", file=sys.stderr)
        return 1

    try:
        # ── EN | HACS cards and integrations ────────────────────────────
        # FR | Cartes et integrations HACS
        try:
            repos = ws.command({"type": "hacs/repositories/list"}) or []
            report["hacs"]["available"] = True
        except (WSError, OSError) as exc:
            repos = []
            report["hacs"]["error"] = str(exc) or exc.__class__.__name__

        wanted = ([("plugin", f, en, fr) for f, en, fr in PLUGINS]
                  + [("integration", d, en, fr) for d, en, fr in INTEGRATIONS])

        for category, key, why_en, why_fr in wanted:
            why = why_fr if locale == "fr" else why_en
            kind = "card" if category == "plugin" else "integration"
            if not report["hacs"]["available"]:
                row(kind, key, key, "unknown", why, report["hacs"]["error"])
                continue
            repo = find_repo(repos, category, key)
            if repo is None:
                row(kind, key, key, "unknown", why)
                continue
            name = str(repo.get("name") or key)
            if repo.get("installed"):
                row(kind, key, name, "ok", why,
                    str(repo.get("installed_version") or ""))
                continue
            if not install:
                row(kind, key, name, "missing", why)
                continue
            err = download(ws, repo)
            if err:
                row(kind, key, name, "failed", why, err)
            elif category == "integration":
                # EN | The files are down; Home Assistant loads a custom
                # EN | component only at startup, so this one is not usable
                # EN | until a restart and the screen must not pretend
                # EN | otherwise.
                # FR | Les fichiers sont la ; Home Assistant ne charge un
                # FR | composant personnalise qu'au demarrage, donc
                # FR | celle-ci n'est pas utilisable avant un redemarrage et
                # FR | l'ecran ne doit pas pretendre le contraire.
                report["restart_required"] = True
                row(kind, key, name, "restart", why,
                    str(repo.get("available_version") or ""))
            else:
                report["reload_required"] = True
                row(kind, key, name, "added", why,
                    str(repo.get("available_version") or ""))
            if install:
                publish(True, "running")

        # ── EN | The Visio Sapiens resources ────────────────────────────
        # FR | Les ressources Visio Sapiens
        try:
            registry = ws.command({"type": "lovelace/resources"}) or []
            report["resources_mode"] = "storage"
        except (WSError, OSError) as exc:
            registry = []
            report["resources_mode"] = "unknown"
            print(f"[warn] resource registry unreadable: {exc}",
                  file=sys.stderr)

        by_base = {}
        for r in registry:
            if isinstance(r, dict) and r.get("url"):
                by_base[str(r["url"]).split("?", 1)[0]] = r

        yaml_mode = False
        declared = declared_resources(args.fragment)
        declared_bases = {u for u, _ in declared}
        for url_base, res_type in declared:
            name = url_base.rsplit("/", 1)[-1]
            why = ("Le moteur et le style de Visio Sapiens."
                   if locale == "fr" else
                   "The Visio Sapiens engine and styling.")
            f = local_file(url_base, args.www)
            if not f.is_file():
                # EN | The file is not on the instance at all: that is a
                # EN | deployment that did not finish, and registering a URL
                # EN | for it would only add a 404 to the browser console.
                # FR | Le fichier n'est pas sur l'instance : c'est un
                # FR | deploiement qui n'est pas alle au bout, et enregistrer
                # FR | une URL pour lui n'ajouterait qu'un 404 dans la
                # FR | console du navigateur.
                row("resource", url_base, name, "no_file", why, str(f))
                continue
            want = f"{url_base}?v={stamp(f)}"
            have = by_base.get(url_base)
            if have and str(have.get("url")) == want:
                row("resource", url_base, name, "ok", why, want)
                continue
            state = "stale" if have else "missing"
            if not install:
                row("resource", url_base, name, state, why, want)
                continue
            try:
                if have:
                    ws.command({"type": "lovelace/resources/update",
                                "resource_id": have.get("id"),
                                "res_type": res_type, "url": want})
                else:
                    ws.command({"type": "lovelace/resources/create",
                                "res_type": res_type, "url": want})
                report["reload_required"] = True
                row("resource", url_base, name, "added", why, want)
            except (WSError, OSError) as exc:
                text = str(exc)
                if "yaml" in text.lower() or "not supported" in text.lower():
                    yaml_mode = True
                    report["resources_mode"] = "yaml"
                    row("resource", url_base, name, "skipped", why, text)
                else:
                    row("resource", url_base, name, "failed", why, text)
            if install:
                publish(True, "running")

        # ── EN | Our own leftovers / FR | Nos propres restes ────────────
        for base, r in sorted(by_base.items()):
            if not base.startswith(OUR_NAMESPACES):
                continue
            if base in declared_bases:
                continue
            if local_file(base, args.www).is_file():
                continue
            name = base.rsplit("/", 1)[-1]
            why = ("Enregistree par une version precedente ; le fichier "
                   "n'existe plus." if locale == "fr" else
                   "Registered by an earlier version; the file is gone.")
            if install and args.prune and not yaml_mode:
                try:
                    ws.command({"type": "lovelace/resources/delete",
                                "resource_id": r.get("id")})
                    report["reload_required"] = True
                    row("resource", base, name, "added", why, "removed")
                    continue
                except (WSError, OSError) as exc:
                    row("resource", base, name, "failed", why, str(exc))
                    continue
            row("resource", base, name, "legacy", why, base)
    except Exception as exc:                             # noqa: BLE001
        # EN | Whatever happened, the screen gets a sentence rather than a
        # EN | button that did nothing. The traceback still goes to the log.
        # FR | Quoi qu'il soit arrive, l'ecran recoit une phrase plutot
        # FR | qu'un bouton qui n'a rien fait. La trace reste dans le
        # FR | journal.
        report["running"] = False
        publish(False, "ws_down", err=str(exc) or exc.__class__.__name__)
        print(f"[ERR] {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        ws.close()

    report["running"] = False
    c = report["counts"]
    c["total"] = len(report["items"])
    missing = sum(1 for i in report["items"]
                  if i["state"] in ("missing", "unknown", "stale"))
    failed = sum(1 for i in report["items"]
                 if i["state"] in ("failed", "no_file"))
    done = sum(1 for i in report["items"] if i["state"] in ("added", "restart"))
    integrations = sum(1 for i in report["items"] if i["state"] == "restart")
    ok = not missing and not failed

    if yaml_mode:
        publish(ok, "yaml_mode")
    elif not report["hacs"]["available"]:
        publish(False, "no_hacs")
    elif failed:
        publish(False, "partial", n=failed)
    elif install and done and integrations:
        publish(True, "installed_restart", n=done, i=integrations)
    elif install and done:
        publish(True, "installed", n=done)
    elif missing:
        publish(False, "missing", n=missing)
    else:
        publish(True, "all_ok")

    print(f"[{'OK' if ok else 'i'}] {c['total']} dependency(ies): "
          f"{c['ok']} in place, {done} installed, {missing} missing, "
          f"{failed} failed")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Visio Sapiens - check or install the dependencies "
                    "a dashboard cannot be drawn without")
    ap.add_argument("--action", default="check", choices=["check", "install"])
    ap.add_argument("--url", default="http://localhost:8123")
    ap.add_argument("--token", default=None)
    ap.add_argument("--token-file", default="/config/vssp/.ha_token")
    ap.add_argument("--out", default="/config/www/vssp/dependencies.json")
    ap.add_argument("--status",
                    default="/config/www/vssp/dependencies_status.json")
    ap.add_argument("--fragment", default="/config/config-fragment.yaml",
                    help="where the declared resource list is read from")
    ap.add_argument("--www", default="/config/www",
                    help="what /local/ resolves to on this instance")
    ap.add_argument("--locale", default="auto")
    # EN | A HACS download is a GitHub round trip per repository; twelve of
    # EN | them on a slow link is minutes, not seconds.
    # FR | Un telechargement HACS est un aller-retour GitHub par depot ;
    # FR | douze sur une liaison lente, cela fait des minutes, pas des
    # FR | secondes.
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--prune", dest="prune", action="store_true", default=True,
                    help="remove resources this project registered whose file "
                         "no longer exists (default)")
    ap.add_argument("--no-prune", dest="prune", action="store_false")
    return run(ap.parse_args())


if __name__ == "__main__":
    sys.exit(main())
