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
# Visio Sapiens - vssp_verify.py
#
# EN | WHAT THIS IS FOR. A deployment can succeed on every step it knows
# EN | about and still leave an instance where nothing is drawn. That is not
# EN | a hypothesis: on a freshly deployed Home Assistant OS the pipeline was
# EN | green, the smoke test was green, and the screen was blank - the theme
# EN | had never been selected, HACS was absent so no custom card existed,
# EN | and two rooms had a navigation entry with no dashboard behind them.
# EN | Everything the pipeline verified was true. It verified the wrong
# EN | things: that the API answered and that two files were served.
# EN | This script verifies what a person would look at.
# FR | A QUOI CECI SERT. Un deploiement peut reussir chacune des etapes qu il
# FR | connait et laisser malgre tout une instance ou rien ne s affiche. Ce
# FR | n est pas une hypothese : sur un Home Assistant OS fraichement
# FR | deploye, le pipeline etait vert, le test de fumee etait vert, et
# FR | l ecran etait blanc - le theme n avait jamais ete selectionne, HACS
# FR | etait absent donc aucune carte personnalisee n existait, et deux
# FR | pieces avaient une entree de navigation sans dashboard derriere.
# FR | Tout ce que le pipeline verifiait etait vrai. Il verifiait les
# FR | mauvaises choses : que l API repond et que deux fichiers sont servis.
# FR | Ce script verifie ce qu une personne regarderait.
#
# EN | WHAT IT CHECKS, in the order a screen fails:
# EN |   1. dashboards  - every declared dashboard serves a config. A
# EN |                    declaration whose file is missing, or a room whose
# EN |                    fragment was never merged, is caught here: Home
# EN |                    Assistant answers such a url_path with the default
# EN |                    panel, which is why a room "opens HOME".
# EN |   2. entities    - the Visio Sapiens entities the served configs
# EN |                    name all exist. A missing one means a package did
# EN |                    not load. Entities belonging to the HOUSE -
# EN |                    cameras, a vacuum, plugs - are counted and listed
# EN |                    but never fail: a house without a camera is not a
# EN |                    broken deployment, and iso-environment means the
# EN |                    control centre works, not that two houses own the
# EN |                    same hardware.
# EN |   3. resources   - every registered Lovelace resource answers 200. A
# EN |                    stale stamp or a file renamed upstream shows up
# EN |                    here, and it is the difference between a styled
# EN |                    interface and a blank one.
# EN |   4. theme       - the theme is loaded AND selected. Generating it is
# EN |                    not enough: the selection is a preference, and an
# EN |                    instance nobody set it on renders unstyled.
# EN |   5. dependencies- nothing blocking is missing, read from the probe's
# EN |                    own report rather than guessed again.
# EN |   6. version     - the instance runs the reference it was given, when
# EN |                    one is passed.
# FR | CE QU IL VERIFIE, dans l ordre ou un ecran tombe :
# FR |   1. dashboards  - chaque dashboard declare sert une configuration.
# FR |                    Une declaration dont le fichier manque, ou une
# FR |                    piece dont le fragment n a jamais ete fusionne, est
# FR |                    attrapee ici : Home Assistant repond a un tel
# FR |                    url_path par le panneau par defaut, et c est
# FR |                    pourquoi une piece « ouvre HOME ».
# FR |   2. entites     - les entites Visio Sapiens nommees par les
# FR |                    configurations servies existent toutes. Une
# FR |                    absence signifie qu un package n a pas charge. Les
# FR |                    entites de la MAISON - cameras, aspirateur, prises
# FR |                    - sont comptees et listees mais n echouent jamais :
# FR |                    une maison sans camera n est pas un deploiement
# FR |                    casse, et iso-environnement veut dire que le centre
# FR |                    de controle fonctionne, pas que deux maisons
# FR |                    possedent le meme materiel.
# FR |   3. ressources  - chaque ressource Lovelace enregistree repond 200.
# FR |                    Un tampon perime ou un fichier renomme en amont
# FR |                    apparait ici, et c est la difference entre une
# FR |                    interface habillee et une page blanche.
# FR |   4. theme       - le theme est charge ET selectionne. Le generer ne
# FR |                    suffit pas : la selection est une preference, et
# FR |                    une instance ou personne ne l a posee s affiche
# FR |                    sans style.
# FR |   5. dependances - rien de bloquant ne manque, lu dans le rapport de
# FR |                    la sonde plutot que devine une seconde fois.
# FR |   6. version     - l instance fait tourner la reference qu on lui a
# FR |                    donnee, quand on en passe une.
#
# EN | WHERE IT RUNS. Over the network only, so the same command works from
# EN | the CI runner against any instance and from the instance itself. The
# EN | token is read from an environment variable or a file, never from an
# EN | argument: an argument is visible in the process list of the machine
# EN | it runs on.
# FR | OU IL TOURNE. Par le reseau uniquement : la meme commande fonctionne
# FR | depuis le runner CI contre n importe quelle instance et depuis
# FR | l instance elle-meme. Le jeton est lu dans une variable d
# FR | environnement ou un fichier, jamais dans un argument : un argument est
# FR | visible dans la liste des processus de la machine qui l execute.
#
# EN | USAGE / FR | UTILISATION
#   HA_TOKEN=... python3 vssp_verify.py --url http://192.168.1.11:8123
#   python3 vssp_verify.py --token-file /config/vssp/.ha_token
#   python3 vssp_verify.py --url ... --expect-version dev-abc1234 --json out.json
#
# EN | Exit codes: 0 = everything a screen needs is in place, 1 = something
# EN | a person would see is broken. Tolerated placeholders never fail it.
# FR | Codes de sortie : 0 = tout ce dont un ecran a besoin est en place,
# FR | 1 = quelque chose qu une personne verrait est casse. Les emplacements
# FR | toleres ne le font jamais echouer.
# ============================================================================
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vssp_ws import WSError, connected, resolve_token  # noqa: E402

# EN | The domains an entity id can start with. Anything else matching
# EN | "word.word" in a dashboard is a file name, a CSS class or a Jinja
# EN | attribute, and must not be mistaken for an entity.
# FR | Les domaines par lesquels un identifiant d entite peut commencer.
# FR | Tout autre « mot.mot » dans un dashboard est un nom de fichier, une
# FR | classe CSS ou un attribut Jinja, et ne doit pas etre pris pour une
# FR | entite.
DOMAINS = (
    "alarm_control_panel", "binary_sensor", "button", "calendar", "camera",
    "climate", "cover", "device_tracker", "fan", "humidifier", "input_boolean",
    "input_button", "input_datetime", "input_number", "input_select",
    "input_text", "light", "lock", "media_player", "number", "person",
    "remote", "scene", "script", "select", "sensor", "siren", "switch",
    "text", "todo", "update", "vacuum", "water_heater", "weather", "zone",
)
ENTITY_RE = re.compile(r"\b(?:%s)\.[a-z0-9_]+\b" % "|".join(DOMAINS))

GREEN, RED, YELLOW, DIM, RESET = (
    "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[0m")


class Report:
    """EN | Collects one line per check and decides the exit code.
    FR | Rassemble une ligne par verification et decide du code de sortie."""

    def __init__(self) -> None:
        self.sections: list[dict] = []
        self.failed = 0

    def add(self, section: str, ok: bool, label: str,
            detail: str = "", fix: str = "", fatal: bool = True) -> None:
        self.sections.append({"section": section, "ok": ok, "label": label,
                              "detail": detail, "fix": fix, "fatal": fatal})
        if not ok and fatal:
            self.failed += 1

    def print(self) -> None:
        current = ""
        for row in self.sections:
            if row["section"] != current:
                current = row["section"]
                print(f"\n=== {current} ===")
            if row["ok"]:
                mark = f"{GREEN}OK{RESET}  "
            elif row["fatal"]:
                mark = f"{RED}FAIL{RESET}"
            else:
                mark = f"{YELLOW}warn{RESET}"
            print(f"  {mark} {row['label']}"
                  + (f"  {DIM}{row['detail']}{RESET}" if row["detail"] else ""))
            if not row["ok"] and row["fix"]:
                print(f"       -> {row['fix']}")


# EN | Keys whose value is a SERVICE, not an entity. "input_select.select_option"
# EN | and "script.turn_on" match the entity pattern exactly, and a report
# EN | that invents missing entities is worse than no report: it trains
# EN | everyone to ignore it.
# FR | Cles dont la valeur est un SERVICE, pas une entite.
# FR | « input_select.select_option » et « script.turn_on » correspondent
# FR | exactement au motif d une entite, et un rapport qui invente des
# FR | entites manquantes est pire que pas de rapport : il apprend a tout le
# FR | monde a l ignorer.
SERVICE_KEYS = {"service", "action", "perform_action"}


def entities_in(node, key: str = "") -> set:
    """EN | Every entity id a dashboard configuration names, service calls
    EN | excluded. Walks the structure rather than the rendered text, so a
    EN | value is judged by the key that carries it.
    FR | Chaque identifiant d entite que nomme une configuration de
    FR | dashboard, appels de service exclus. Parcourt la structure plutot
    FR | que le texte rendu, pour juger une valeur d apres la cle qui la
    FR | porte."""
    found: set = set()
    if isinstance(node, dict):
        for k, v in node.items():
            if str(k) in SERVICE_KEYS and isinstance(v, str):
                continue
            found |= entities_in(v, str(k))
    elif isinstance(node, list):
        for v in node:
            found |= entities_in(v, key)
    elif isinstance(node, str):
        found |= set(ENTITY_RE.findall(node))
    return found


def rest(url: str, token: str, path: str):
    req = urllib.request.Request(
        url.rstrip("/") + path,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def head(url: str, token: str, path: str) -> int:
    """EN | The status of one served file. A Lovelace resource is fetched by
    EN | the browser without a token, so no header is sent here either - a
    EN | resource that only answers to an authenticated caller would still be
    EN | a broken resource.
    FR | Le statut d un fichier servi. Une ressource Lovelace est chargee par
    FR | le navigateur sans jeton : on n en envoie donc pas non plus ici - une
    FR | ressource qui ne repondrait qu a un appelant authentifie resterait
    FR | une ressource cassee."""
    try:
        req = urllib.request.Request(url.rstrip("/") + path, method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return int(resp.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except OSError:
        return 0


# EN | The dashboards the PRODUCT declares, read from the static fragment.
# EN | config-fragment.yaml is written by this project and holds HOME, CORE,
# EN | ENERGY, their mobile variants, the preview and the ADMIN console:
# EN | those are structure, and one of them without a file is a defect of the
# EN | control centre. config-fragment-rooms.yaml is written from the house
# EN | model and holds the rooms: those are CONTENT. A house declares a
# EN | kitchen and later removes it; a stale room entry is untidy, it is not
# EN | a broken product, and a release must never be blocked by it.
# FR | Les dashboards que le PRODUIT declare, lus dans le fragment statique.
# FR | config-fragment.yaml est ecrit par ce projet et contient HOME, CORE,
# FR | ENERGY, leurs variantes mobiles, l apercu et la console ADMIN : c est
# FR | de la structure, et l un d eux sans fichier est un defaut du centre de
# FR | controle. config-fragment-rooms.yaml est ecrit depuis le modele de la
# FR | maison et contient les pieces : c est du CONTENU. Une maison declare
# FR | une cuisine puis la retire ; une entree de piece perimee est un
# FR | desordre, pas un produit casse, et une livraison ne doit jamais etre
# FR | bloquee par cela.
FALLBACK_SYSTEM = {
    "visio-sapiens", "visio-sapiens-m", "visio-sapiens-core",
    "visio-sapiens-core-m", "visio-sapiens-energy", "visio-sapiens-energy-m",
    "visio-sapiens-energy-preview", "visio-sapiens-admin",
}


def load_system(path: str) -> set:
    """EN | The url_paths the static fragment declares, or the fallback set
    EN | when it cannot be read - never an empty set, which would turn every
    EN | dashboard into content and the check into decoration.
    FR | Les url_path que declare le fragment statique, ou l ensemble de
    FR | repli s il n est pas lisible - jamais un ensemble vide, qui ferait
    FR | de chaque dashboard du contenu et de la verification une decoration."""
    try:
        import yaml

        class Loader(yaml.SafeLoader):
            pass

        Loader.add_multi_constructor("!", lambda l, s, n: None)
        data = yaml.load(Path(path).read_text(encoding="utf-8"), Loader=Loader)
        boards = ((data or {}).get("lovelace") or {}).get("dashboards") or {}
        keys = {str(k) for k in boards}
        return keys or FALLBACK_SYSTEM
    except Exception:                                    # noqa: BLE001
        return FALLBACK_SYSTEM


def load_tolerated(path: str) -> set:
    """EN | Entity ids known to be absent on every instance - placeholders a
    EN | dashboard keeps for an installation that does not exist yet, such as
    EN | the photovoltaic tiles. Listed in a file so the list is reviewed
    EN | like anything else, rather than hidden in this script.
    FR | Identifiants d entites connus pour etre absents sur toutes les
    FR | instances - des emplacements qu un dashboard garde pour une
    FR | installation qui n existe pas encore, comme les tuiles
    FR | photovoltaiques. Listes dans un fichier pour que la liste soit
    FR | relue comme le reste, plutot que cachee dans ce script."""
    out: set = set()
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip().lstrip("- ").strip()
        if line and ENTITY_RE.fullmatch(line):
            out.add(line)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Visio Sapiens - verify that a deployed instance can "
                    "actually draw its interface")
    ap.add_argument("--url", default="http://localhost:8123")
    ap.add_argument("--token-file", default="/config/vssp/.ha_token",
                    help="EN | read when HA_TOKEN is not set / "
                         "FR | lu quand HA_TOKEN n'est pas definie")
    ap.add_argument("--tolerated",
                    default="/config/dashboards/model/tolerated_entities.txt")
    ap.add_argument("--fragment", default="/config/config-fragment.yaml",
                    help="EN | the static fragment, which says which "
                         "dashboards belong to the product rather than to "
                         "the house")
    ap.add_argument("--templates-dir", default="",
                    help="EN | the template set this release ships: each "
                         "dashboard says which set generated it, and HOME is "
                         "protected from regeneration, so drift is silent")
    ap.add_argument("--expect-version", default="",
                    help="EN | fail when sensor.vssp_deployed_version differs")
    ap.add_argument("--theme", default="Visio Sapiens")
    ap.add_argument("--json", default="",
                    help="EN | write the whole report here as well")
    args = ap.parse_args()

    token = resolve_token(os.environ.get("HA_TOKEN"), args.token_file)
    if not token:
        print("[ERR] no token: set HA_TOKEN or pass --token-file",
              file=sys.stderr)
        return 2

    rep = Report()
    try:
        ws = connected(args.url, token)
    except (WSError, OSError) as exc:
        print(f"[ERR] websocket: {exc}", file=sys.stderr)
        return 2

    try:
        states = rest(args.url, token, "/api/states")
        existing = {e["entity_id"] for e in states}

        # ── 1. EN | dashboards / FR | tableaux de bord ─────────────────
        boards = ws.command({"type": "lovelace/dashboards/list"}) or []
        mine = [b for b in boards
                if str(b.get("url_path") or "").startswith("visio-sapiens")]
        rep.add("1. DASHBOARDS", bool(mine),
                f"{len(mine)} Visio Sapiens dashboard(s) declared",
                fix="config-fragment.yaml was never merged into "
                    "configuration.yaml - run vssp_apply_config.py")
        system = load_system(args.fragment)
        cited: set = set()
        for b in mine:
            url_path = str(b.get("url_path") or "")
            structural = url_path in system
            try:
                cfg = ws.command({"type": "lovelace/config",
                                  "url_path": url_path}) or {}
            except (WSError, OSError) as exc:
                rep.add("1. DASHBOARDS", False, url_path, detail=str(exc),
                        fix=("declared with no file behind it - the control "
                             "centre is incomplete"
                             if structural else
                             "a room declared in configuration.yaml that the "
                             "house model no longer has: tidy it with "
                             "--prune-dashboards, it blocks nothing"),
                        fatal=structural)
                continue
            views = cfg.get("views") or []
            rep.add("1. DASHBOARDS", bool(views), url_path,
                    detail=f"{len(views)} view(s)",
                    fix="serves an empty configuration", fatal=structural)
            cited |= entities_in(cfg)

        # ── 2. EN | entities / FR | entites ────────────────────────────
        # EN | TWO KINDS, AND ONLY ONE IS A DEFECT. An entity whose id
        # EN | carries the vssp_ prefix belongs to the control centre: it
        # EN | comes from a package this project deploys, and its absence
        # EN | means a package did not load - the same release, the same
        # EN | files, a broken instance. That fails.
        # EN | Every other entity belongs to the house: cameras, a vacuum,
        # EN | plugs, a doorbell. Deploy this project in a house that has no
        # EN | camera and those ids will be missing forever, and nothing is
        # EN | wrong. Iso-environment means the control centre works, not
        # EN | that two houses own the same hardware. They are counted and
        # EN | listed, never fatal.
        # FR | DEUX ESPECES, UNE SEULE EST UN DEFAUT. Une entite dont
        # FR | l identifiant porte le prefixe vssp_ appartient au centre de
        # FR | controle : elle vient d un package que ce projet deploie, et
        # FR | son absence signifie qu un package n a pas charge - meme
        # FR | livraison, memes fichiers, instance cassee. Cela echoue.
        # FR | Toute autre entite appartient a la maison : cameras,
        # FR | aspirateur, prises, sonnette. Deployez ce projet dans une
        # FR | maison sans camera et ces identifiants manqueront pour
        # FR | toujours, sans que rien ne soit anormal. Iso-environnement
        # FR | veut dire que le centre de controle fonctionne, pas que deux
        # FR | maisons possedent le meme materiel. Elles sont comptees et
        # FR | listees, jamais fatales.
        tolerated = load_tolerated(args.tolerated)
        absent = cited - existing - tolerated
        product = sorted(e for e in absent if ".vssp_" in e)
        house = sorted(e for e in absent if ".vssp_" not in e)
        skipped = sorted((cited - existing) & tolerated)
        rep.add("2. ENTITIES", not product,
                f"control centre: {len(cited)} cited, {len(product)} missing",
                detail=", ".join(product[:6]) + (" ..." if len(product) > 6
                                                 else ""),
                fix="a Visio Sapiens entity the dashboards name does not "
                    "exist: a package did not load. Check the error log")
        if house:
            rep.add("2. ENTITIES", True,
                    f"house and platform: {len(house)} not present here",
                    detail=", ".join(house[:5]) + (" ..." if len(house) > 5
                                                   else ""),
                    fix="a device this house does not own, or a core "
                        "integration not added yet - CHECK DEPENDENCIES "
                        "lists the second kind",
                    fatal=False)
        if skipped:
            rep.add("2. ENTITIES", True,
                    f"{len(skipped)} tolerated placeholder(s)",
                    detail=", ".join(skipped[:4]) + (" ..." if len(skipped) > 4
                                                     else ""),
                    fatal=False)

        # ── 3. EN | resources / FR | ressources ────────────────────────
        resources = ws.command({"type": "lovelace/resources"}) or []
        bad = []
        for r in resources:
            url = str(r.get("url") or "")
            if not url.startswith("/"):
                continue
            code = head(args.url, token, url)
            if code != 200:
                bad.append(f"{url} -> {code}")
        rep.add("3. RESOURCES", not bad,
                f"{len(resources)} registered, {len(bad)} not served",
                detail=" | ".join(bad[:3]),
                fix="a resource that does not answer is a card that never "
                    "registers - run INSTALL DEPENDENCIES")

        # ── 4. EN | theme / FR | theme ─────────────────────────────────
        themes = ws.command({"type": "frontend/get_themes"}) or {}
        known = args.theme in (themes.get("themes") or {})
        selected = themes.get("default_theme") == args.theme
        rep.add("4. THEME", known, f"{args.theme} loaded",
                fix="themes/visio_sapiens.yaml is missing or frontend.themes "
                    "does not include that directory")
        rep.add("4. THEME", selected, f"{args.theme} selected",
                detail=f"default_theme={themes.get('default_theme')}",
                fix="generated but never selected: every dashboard renders "
                    "unstyled. frontend.set_theme fixes it")

        # ── 5. EN | dependencies / FR | dependances ────────────────────
        # EN | Read from the probe's own report, so the two never disagree.
        # FR | Lu dans le rapport de la sonde, pour que les deux ne se
        # FR | contredisent jamais.
        dep = next((e for e in states
                    if e["entity_id"] == "sensor.vssp_dependencies"), None)
        items = ((dep or {}).get("attributes") or {}).get("items") or []
        if not items:
            rep.add("5. DEPENDENCIES", True, "never checked on this instance",
                    fix="press CHECK DEPENDENCIES in the ADMIN console",
                    fatal=False)
        else:
            blocking = [i for i in items if i.get("required")
                        and i.get("state") not in ("ok", "added")]
            rep.add("5. DEPENDENCIES", not blocking,
                    f"{len(items)} known, {len(blocking)} blocking missing",
                    detail=", ".join(i.get("name", "?") for i in blocking[:4]),
                    fix="without these nothing can be drawn - run INSTALL "
                        "DEPENDENCIES")

        # ── 6. EN | template drift / FR | derive des gabarits ──────────
        # EN | HOME is protected from regeneration so a deployment never
        # EN | erases what someone changed there. The cost is that a template
        # EN | fix never reaches an instance that already has a HOME, and
        # EN | nothing said so: three instances were measured running three
        # EN | different HOME files from the same release, one drawing a
        # EN | "Configuration error" box where the event log should be.
        # EN | This reports, it does not fail: an old dashboard is a screen
        # EN | to refresh with REGENERATE, not a broken release.
        # FR | HOME est protege contre la regeneration pour qu un
        # FR | deploiement n efface jamais ce que quelqu un y a change. Le
        # FR | cout, c est qu une correction de gabarit n atteint jamais une
        # FR | instance qui a deja un HOME, et rien ne le disait : trois
        # FR | instances ont ete mesurees avec trois HOME differents issus de
        # FR | la meme livraison, dont un dessinait un encadre « Erreur de
        # FR | configuration » la ou doit etre le journal d evenements.
        # FR | Ceci signale, sans echouer : un dashboard ancien est un ecran
        # FR | a rafraichir avec REGENERER, pas une livraison cassee.
        if args.templates_dir:
            import vssp_manifest

            expected = vssp_manifest.templates_digest(args.templates_dir)
            stamps = {}
            try:
                req = urllib.request.Request(
                    args.url.rstrip("/") + "/local/vssp/generated_stamps.json")
                with urllib.request.urlopen(req, timeout=30) as resp:
                    stamps = json.loads(resp.read().decode("utf-8"))
            except (OSError, ValueError):
                stamps = {}
            boards = (stamps or {}).get("dashboards") or {}
            if not expected:
                rep.add("6. TEMPLATES", True, "template set unreadable",
                        fatal=False)
            elif not boards:
                rep.add("6. TEMPLATES", True,
                        "no dashboard is stamped yet",
                        detail="generated before this release",
                        fix="REGENERATE from the ADMIN console stamps them",
                        fatal=False)
            else:
                stale = sorted(name for name, row in boards.items()
                               if (row or {}).get("templates") != expected)
                rep.add("6. TEMPLATES", not stale,
                        f"{len(boards)} stamped, {len(stale)} from an older "
                        f"template set",
                        detail=", ".join(stale[:5]) + (" ..." if len(stale) > 5
                                                       else ""),
                        fix="REGENERATE them from the ADMIN console - HOME is "
                            "protected, so a deploy will never do it for you",
                        fatal=False)

        # ── 7. EN | version / FR | version ─────────────────────────────
        if args.expect_version:
            live = next((e["state"] for e in states
                         if e["entity_id"] == "sensor.vssp_deployed_version"),
                        "")
            rep.add("7. VERSION", live == args.expect_version,
                    f"expected {args.expect_version}", detail=f"live {live}",
                    fix="the instance is not running what was just deployed")
    finally:
        ws.close()

    rep.print()
    print()
    if rep.failed:
        print(f"{RED}[FAIL]{RESET} {rep.failed} check(s) a person would see "
              f"as broken")
    else:
        print(f"{GREEN}[OK]{RESET} the interface has everything it needs")
    if args.json:
        Path(args.json).write_text(
            json.dumps({"failed": rep.failed, "checks": rep.sections},
                       indent=2, ensure_ascii=False), encoding="utf-8")
    return 1 if rep.failed else 0


if __name__ == "__main__":
    sys.exit(main())
