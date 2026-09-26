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
# Visio Sapiens - vssp_prepare.py
#
# EN | WHAT THIS IS FOR. vssp_preflight.py refuses to deploy into an instance
# EN | that cannot host the control centre. This is what you run next: it
# EN | prepares the ground, from the same manifest, and then says plainly
# EN | what only a person can do.
# EN | It is written to be run without a pipeline as well - a house that
# EN | installed Visio Sapiens by hand has no runner, and the same command
# EN | works from that instance's own terminal.
# FR | A QUOI CECI SERT. vssp_preflight.py refuse de deployer dans une
# FR | instance incapable d heberger le centre de controle. Voici ce qu on
# FR | lance ensuite : il prepare le terrain, a partir du meme manifeste,
# FR | puis dit clairement ce que seule une personne peut faire.
# FR | Il est ecrit pour tourner aussi sans pipeline - une maison qui a
# FR | installe Visio Sapiens a la main n a pas de runner, et la meme
# FR | commande fonctionne depuis le terminal de cette instance.
#
# EN | WHAT IT DOES
# EN |   1. the cards and HACS integrations, by handing the work to
# EN |      vssp_dependencies.py --action install, which also registers the
# EN |      Visio Sapiens resources and re-stamps them;
# EN |   2. the core integrations whose setup needs no human answer:
# EN |      Open-Meteo on the home zone, Time & Date, System Monitor, a local
# EN |      calendar. Meteo-France needs a city, so it is only created when
# EN |      one is passed;
# EN |   3. the theme, selected - generating it is not enough, and an
# EN |      instance nobody selected it on renders every dashboard unstyled.
# FR | CE QU IL FAIT
# FR |   1. les cartes et integrations HACS, en confiant le travail a
# FR |      vssp_dependencies.py --action install, qui enregistre aussi les
# FR |      ressources Visio Sapiens et les re-tamponne ;
# FR |   2. les integrations natives dont l installation ne demande aucune
# FR |      reponse humaine : Open-Meteo sur la zone du domicile, Date &
# FR |      heure, Moniteur systeme, un calendrier local. Meteo-France
# FR |      reclame une ville : elle n est creee que si on en passe une ;
# FR |   3. le theme, selectionne - le generer ne suffit pas, et une instance
# FR |      ou personne ne l a choisi affiche tous ses dashboards sans style.
#
# EN | WHAT IT WILL NEVER DO. Install HACS (its GitHub authorization is a
# EN | human step), mint a long-lived token, pair a device, or unseal the
# EN | vault. Those are listed at the end, in the language of the instance.
# FR | CE QU IL NE FERA JAMAIS. Installer HACS (son autorisation GitHub est
# FR | une etape humaine), fabriquer un jeton longue duree, appairer un
# FR | appareil, ou desceller le coffre. Ces points sont listes a la fin.
#
# EN | USAGE / FR | UTILISATION
#   HA_TOKEN=... python3 vssp_prepare.py --url http://192.168.1.11:8123
#   python3 vssp_prepare.py --city 13960        # EN | adds Meteo-France too
#
# EN | Exit codes: 0 = everything it could do is done, 1 = something it tried
# EN | failed. What only a person can do never changes the code.
# FR | Codes de sortie : 0 = tout ce qu il pouvait faire est fait, 1 = une
# FR | action a echoue. Ce que seule une personne peut faire ne change jamais
# FR | le code de sortie.
# ============================================================================
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import vssp_manifest  # noqa: E402
from vssp_ws import WSError, connected, resolve_token  # noqa: E402

GREEN, RED, YELLOW, DIM, RESET = (
    "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[0m")

# EN | The answer each config flow needs, when it needs one that is the same
# EN | on every instance. A flow whose answer belongs to the house - a city,
# EN | a password, a pairing code - is not here: guessing it would be worse
# EN | than leaving it to the person.
# FR | La reponse dont chaque assistant a besoin, quand elle est la meme sur
# FR | toutes les instances. Un assistant dont la reponse appartient a la
# FR | maison - une ville, un mot de passe, un code d appairage - n y figure
# FR | pas : la deviner serait pire que de la laisser a la personne.
FLOW_ANSWERS = {
    "open_meteo": {"zone": "zone.home"},
    "time_date": {"display_options": "time"},
    "systemmonitor": {},
    "local_calendar": {"calendar_name": "Visio Sapiens"},
}


def post(url: str, token: str, path: str, payload: dict | None = None):
    data = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(
        url.rstrip("/") + path, data=data, method="POST",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body) if body.strip() else {}


def create_entry(url: str, token: str, handler: str, answer: dict) -> str:
    """EN | "" when the entry now exists, the reason otherwise.
    FR | "" quand l entree existe desormais, la raison sinon."""
    try:
        flow = post(url, token, "/api/config/config_entries/flow",
                    {"handler": handler})
        flow_id = flow.get("flow_id")
        if not flow_id:
            return str(flow.get("reason") or "flow refused")
        res = post(url, token,
                   f"/api/config/config_entries/flow/{flow_id}", answer)
        if res.get("type") == "create_entry":
            return ""
        if res.get("reason") == "already_configured":
            return ""
        return str(res.get("errors") or res.get("reason") or res.get("type"))
    except OSError as exc:
        return str(exc)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Visio Sapiens - prepare an instance to host the "
                    "control centre")
    ap.add_argument("--url", default="http://localhost:8123")
    ap.add_argument("--token-file", default="/config/vssp/.ha_token")
    ap.add_argument("--manifest", default="")
    ap.add_argument("--theme", default="Visio Sapiens")
    ap.add_argument("--city", default="",
                    help="EN | city or postcode for Meteo-France, which has "
                         "no instance-independent answer")
    ap.add_argument("--calendar", default="Visio Sapiens")
    args = ap.parse_args()

    man = vssp_manifest.load(args.manifest or None)
    if not man:
        print("[ERR] requirements.yaml unreadable", file=sys.stderr)
        return 1
    token = resolve_token(os.environ.get("HA_TOKEN"), args.token_file)
    if not token:
        print("[ERR] no token: set HA_TOKEN or pass --token-file",
              file=sys.stderr)
        return 1

    failures = 0
    manual: list[str] = []

    # ── 1. EN | cards and HACS integrations / FR | cartes et integrations ──
    print("=== 1. CARDS AND RESOURCES ===")
    env = dict(os.environ, HA_TOKEN=token)
    dep = HERE / "vssp_dependencies.py"
    proc = subprocess.run(
        [sys.executable, str(dep), "--action", "install", "--url", args.url],
        env=env, capture_output=True, text=True)
    for line in (proc.stdout + proc.stderr).strip().splitlines()[-6:]:
        print(f"  {DIM}{line}{RESET}")
    if proc.returncode == 0:
        print(f"  {GREEN}OK{RESET}   dependencies installed")
    else:
        # EN | A non-zero code here can also mean "HACS is absent", which is
        # EN | not something this program can repair.
        # FR | Un code non nul ici peut aussi vouloir dire « HACS est
        # FR | absent », ce que ce programme ne peut pas reparer.
        print(f"  {YELLOW}warn{RESET} dependencies not fully installed")
        manual.append("HACS itself, if it is missing: install the integration "
                      "and authorize it with a GitHub account")

    # ── 2. EN | core integrations / FR | integrations natives ─────────────
    print("\n=== 2. CORE INTEGRATIONS ===")
    try:
        ws = connected(args.url, token)
        entries = ws.command({"type": "config_entries/get"}) or []
        have = {e.get("domain") for e in entries if isinstance(e, dict)}
        ws.close()
    except (WSError, OSError) as exc:
        print(f"[ERR] websocket: {exc}", file=sys.stderr)
        return 1

    answers = dict(FLOW_ANSWERS)
    answers["local_calendar"] = {"calendar_name": args.calendar}
    if args.city:
        answers["meteo_france"] = {"city": args.city}

    for domain, name, why_en, _why_fr in vssp_manifest.core_integrations(man):
        if domain in have:
            print(f"  {GREEN}OK{RESET}   {name}")
            continue
        if domain not in answers:
            manual.append(f"{name}: its setup needs an answer only you have "
                          f"({why_en})")
            print(f"  {YELLOW}warn{RESET} {name}  {DIM}needs an answer{RESET}")
            continue
        err = create_entry(args.url, token, domain, answers[domain])
        if err:
            failures += 1
            print(f"  {RED}FAIL{RESET} {name}  {DIM}{err}{RESET}")
        else:
            print(f"  {GREEN}OK{RESET}   {name}  {DIM}created{RESET}")

    # ── 3. EN | the theme / FR | le theme ─────────────────────────────────
    print("\n=== 3. THEME ===")
    try:
        post(args.url, token, "/api/services/frontend/set_theme",
             {"name": args.theme})
        print(f"  {GREEN}OK{RESET}   {args.theme} selected")
    except OSError as exc:
        failures += 1
        print(f"  {RED}FAIL{RESET} set_theme  {DIM}{exc}{RESET}")

    # ── EN | what is left for a person / FR | ce qui reste a une personne ──
    manual.append("a restart of Home Assistant, once, if packages were "
                  "deployed for the first time")
    print("\n=== WHAT ONLY YOU CAN DO ===")
    for row in manual:
        print(f"  - {row}")

    print()
    if failures:
        print(f"{RED}[FAIL]{RESET} {failures} action(s) did not go through")
        return 1
    print(f"{GREEN}[OK]{RESET} the ground is prepared - run the preflight "
          f"again")
    return 0


if __name__ == "__main__":
    sys.exit(main())
