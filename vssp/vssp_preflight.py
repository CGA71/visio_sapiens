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
# Visio Sapiens - vssp_preflight.py
#
# EN | WHAT THIS IS FOR. It answers one question before a deployment starts:
# EN | can this instance host the control centre at all? If it cannot, the
# EN | deployment does not run. A release that lands on an instance without
# EN | HACS or without button-card produces a blank screen and a green
# EN | pipeline, and the person in front of it concludes the version is
# EN | broken. It is not: the ground was not prepared.
# FR | A QUOI CECI SERT. Il repond a une seule question avant qu un
# FR | deploiement commence : cette instance peut-elle heberger le centre de
# FR | controle ? Si non, le deploiement n a pas lieu. Une livraison qui
# FR | atterrit sur une instance sans HACS ou sans button-card produit un
# FR | ecran blanc et un pipeline vert, et la personne devant conclut que la
# FR | version est cassee. Elle ne l est pas : le terrain n etait pas pret.
#
# EN | WHAT IS A PREREQUISITE, AND WHAT IS NOT. A prerequisite is what the
# EN | CONTROL CENTRE needs to be drawn. It is never a connected device: a
# EN | house with no camera, no plug and no room declared must still receive
# EN | a working Visio Sapiens, and does. Cameras and thermostats are
# EN | configured afterwards, from the ADMIN console, and their absence is
# EN | reported by vssp_verify.py without ever failing anything.
# FR | CE QU EST UN PREREQUIS, ET CE QU IL N EST PAS. Un prerequis est ce
# FR | dont le CENTRE DE CONTROLE a besoin pour etre dessine. Ce n est jamais
# FR | un appareil connecte : une maison sans camera, sans prise et sans
# FR | piece declaree doit quand meme recevoir un Visio Sapiens qui marche,
# FR | et le recoit. Cameras et thermostats se configurent ensuite, depuis la
# FR | console ADMIN, et leur absence est signalee par vssp_verify.py sans
# FR | jamais rien faire echouer.
#
# EN | WHAT IT CHECKS, all of it read from requirements.yaml:
# EN |   - the instance answers and the token is accepted
# EN |   - Home Assistant is at least the minimum this release is built for
# EN |   - HACS is present and answering. Without it no card can ever be
# EN |     installed, and its GitHub authorization cannot be automated - so
# EN |     this one is a human step, once, and the message says so
# EN |   - every blocking card and integration is installed
# EN | Everything else - the optional cards, the core integrations - is
# EN | listed and does not stop the deployment.
# FR | CE QU IL VERIFIE, le tout lu dans requirements.yaml :
# FR |   - l instance repond et le jeton est accepte
# FR |   - Home Assistant est au moins au minimum pour lequel cette livraison
# FR |     est construite
# FR |   - HACS est present et repond. Sans lui aucune carte ne pourra jamais
# FR |     etre installee, et son autorisation GitHub ne s automatise pas -
# FR |     c est donc une etape humaine, une fois, et le message le dit
# FR |   - chaque carte et integration bloquante est installee
# FR | Tout le reste - cartes optionnelles, integrations natives - est liste
# FR | et n arrete pas le deploiement.
#
# EN | WHEN IT FAILS. Run vssp_prepare.py (the prepare job of the pipeline):
# EN | it installs what can be installed from here, and names what only a
# EN | person can do. Then run this again.
# FR | QUAND IL ECHOUE. Lancer vssp_prepare.py (le job prepare du pipeline) :
# FR | il installe ce qui peut l etre d ici, et nomme ce que seule une
# FR | personne peut faire. Puis relancer ceci.
#
# EN | USAGE / FR | UTILISATION
#   HA_TOKEN=... python3 vssp_preflight.py --url http://192.168.1.11:8123
#
# EN | Exit codes: 0 = the instance can host the release, 1 = it cannot and
# EN | the reasons are printed, 2 = it could not be reached or read.
# FR | Codes de sortie : 0 = l instance peut heberger la livraison, 1 = elle
# FR | ne le peut pas et les raisons sont affichees, 2 = elle n a pas pu etre
# FR | jointe ou lue.
# ============================================================================
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import vssp_manifest  # noqa: E402
from vssp_ws import WSError, connected, resolve_token  # noqa: E402

GREEN, RED, YELLOW, DIM, RESET = (
    "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[0m")


def version_tuple(text: str) -> tuple:
    out = []
    for part in str(text).split(".")[:3]:
        digits = "".join(c for c in part if c.isdigit())
        out.append(int(digits) if digits else 0)
    while len(out) < 3:
        out.append(0)
    return tuple(out)


def rest(url: str, token: str, path: str):
    req = urllib.request.Request(
        url.rstrip("/") + path,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Visio Sapiens - refuse to deploy into an instance that "
                    "cannot host the control centre")
    ap.add_argument("--url", default="http://localhost:8123")
    ap.add_argument("--token-file", default="/config/vssp/.ha_token")
    ap.add_argument("--manifest", default="")
    args = ap.parse_args()

    man = vssp_manifest.load(args.manifest or None)
    if not man:
        print("[ERR] requirements.yaml unreadable - refusing to guess",
              file=sys.stderr)
        return 2

    token = resolve_token(os.environ.get("HA_TOKEN"), args.token_file)
    if not token:
        print("[ERR] no token: set HA_TOKEN or pass --token-file",
              file=sys.stderr)
        return 2

    print(f"[i] preflight -> {args.url}")
    blocking: list[str] = []
    notes: list[str] = []

    try:
        config = rest(args.url, token, "/api/config")
    except OSError as exc:
        print(f"[ERR] {args.url} unreachable or token rejected: {exc}",
              file=sys.stderr)
        return 2

    core = str(config.get("version") or "0")
    minimum = str(man.get("minimum_core") or "0")
    if version_tuple(core) < version_tuple(minimum):
        blocking.append(f"Home Assistant {core} < {minimum} required")
        print(f"  {RED}FAIL{RESET} core {core}  {DIM}minimum {minimum}{RESET}")
    else:
        print(f"  {GREEN}OK{RESET}   core {core}")

    try:
        ws = connected(args.url, token)
    except (WSError, OSError) as exc:
        print(f"[ERR] websocket: {exc}", file=sys.stderr)
        return 2

    try:
        hacs_rule = man.get("hacs") or {}
        repos: list = []
        try:
            repos = ws.command({"type": "hacs/repositories/list"}) or []
            print(f"  {GREEN}OK{RESET}   HACS answering  "
                  f"{DIM}{len(repos)} repositories known{RESET}")
        except (WSError, OSError) as exc:
            if hacs_rule.get("required", True):
                blocking.append("HACS absent: " + str(hacs_rule.get("how_en")
                                                      or exc))
                print(f"  {RED}FAIL{RESET} HACS absent  {DIM}{exc}{RESET}")
                print(f"       -> {hacs_rule.get('how_en')}")
                print(f"       -> {hacs_rule.get('how_fr')}")

        # EN | Cards, matched on the full owner/name: two repositories can
        # EN | share a folder name and a fresh instance once got the wrong
        # EN | one of the two simple-weather-card.
        # FR | Cartes, comparees sur le proprietaire/nom complet : deux
        # FR | depots peuvent partager un nom de dossier et une instance
        # FR | neuve a recu un jour la mauvaise des deux simple-weather-card.
        installed = {str(r.get("full_name") or "").lower()
                     for r in repos if r.get("installed")}
        for repo, is_blocking, why_en, _why_fr in vssp_manifest.cards(man):
            ok = repo.lower() in installed
            if ok:
                print(f"  {GREEN}OK{RESET}   {repo}")
            elif is_blocking:
                blocking.append(f"{repo} missing - {why_en}")
                print(f"  {RED}FAIL{RESET} {repo}  {DIM}{why_en}{RESET}")
            else:
                notes.append(f"{repo} - {why_en}")
                print(f"  {YELLOW}warn{RESET} {repo}  {DIM}{why_en}{RESET}")

        domains = {str(r.get("domain") or "").lower()
                   for r in repos if r.get("installed")}
        for domain, is_blocking, why_en, _why_fr in \
                vssp_manifest.integrations(man):
            ok = domain.lower() in domains
            if ok:
                print(f"  {GREEN}OK{RESET}   {domain}")
            elif is_blocking:
                blocking.append(f"{domain} missing - {why_en}")
                print(f"  {RED}FAIL{RESET} {domain}  {DIM}{why_en}{RESET}")
            else:
                notes.append(f"{domain} - {why_en}")

        # EN | Core integrations never block: each feeds one tile.
        # FR | Les integrations natives ne bloquent jamais : chacune alimente
        # FR | une tuile.
        try:
            entries = ws.command({"type": "config_entries/get"}) or []
            have = {e.get("domain") for e in entries if isinstance(e, dict)}
            for domain, name, why_en, _why_fr in \
                    vssp_manifest.core_integrations(man):
                if domain not in have:
                    notes.append(f"{name} - {why_en}")
                    print(f"  {YELLOW}warn{RESET} {name}  {DIM}{why_en}{RESET}")
        except (WSError, OSError) as exc:
            print(f"  {YELLOW}warn{RESET} config entries unreadable: {exc}")
    finally:
        ws.close()

    print()
    if blocking:
        print(f"{RED}[STOP]{RESET} this instance cannot host the release:")
        for row in blocking:
            print(f"   - {row}")
        print("\n   Run the prepare job of the pipeline, or INSTALL "
              "DEPENDENCIES in the ADMIN console, then start again.")
        return 1
    if notes:
        print(f"{YELLOW}[i]{RESET} {len(notes)} optional piece(s) missing - "
              f"one tile each, the control centre is unaffected:")
        for row in notes:
            print(f"   - {row}")
    print(f"{GREEN}[OK]{RESET} the instance can host the control centre")
    return 0


if __name__ == "__main__":
    sys.exit(main())
