#!/usr/bin/env python3
"""Visio Sapiens — auto-diagnostic de la chaîne de génération ENERGY.

À lancer SUR LE POD. Ne modifie rien, n'écrit aucun fichier.

    python3 /config/vssp/vssp_selftest.py
    python3 /config/vssp/vssp_selftest.py --token "eyJ..."   # test complet

Teste les cinq maillons, dans l'ordre où ils cassent en pratique, et
s'arrête au premier bloquant en disant quoi faire.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

VSSP = Path("/config/vssp")
DASH = Path("/config/dashboards")
PKG = Path("/config/packages")
WWW = Path("/config/www/vssp")

GREEN, RED, YELLOW, DIM, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[0m"
OK, KO, WARN = f"{GREEN}✓{RESET}", f"{RED}✗{RESET}", f"{YELLOW}⚠{RESET}"

problems: list[str] = []


def check(label: str, ok: bool, fix: str = "", detail: str = "") -> bool:
    print(f"  {OK if ok else KO} {label}" + (f"  {DIM}{detail}{RESET}" if detail else ""))
    if not ok and fix:
        print(f"      → {fix}")
        problems.append(label)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", default=None,
                    help="Jeton longue durée HA (active les tests 4 et 5)")
    ap.add_argument("--url", default="http://localhost:8123")
    args = ap.parse_args()

    print("\n═══ 1. FICHIERS EN PLACE ═══")
    gen = VSSP / "generate_dashboards.py"
    sync = VSSP / "vssp_energy_sync.py"
    tpl = DASH / "templates_j2" / "energy.yaml.j2"
    model = DASH / "model" / "house.yaml"
    devices = DASH / "model" / "energy_devices.yaml"

    check("generate_dashboards.py", gen.exists(),
          "le job build du CI ne le copie pas : cp vssp/generate_dashboards.py dist/vssp/")
    check("vssp_energy_sync.py", sync.exists(),
          "idem : cp vssp/vssp_energy_sync.py dist/vssp/")
    check("templates_j2/energy.yaml.j2", tpl.exists(),
          "commiter le template dans home-assistant/dashboards/templates_j2/")
    check("model/house.yaml", model.exists(),
          "commiter le modèle dans home-assistant/dashboards/model/")
    check("packages/vssp_admin.yaml", (PKG / "vssp_admin.yaml").exists(),
          "commiter le package dans home-assistant/packages/")
    print(f"  {OK if devices.exists() else WARN} model/energy_devices.yaml"
          + ("" if devices.exists() else
             f"  {DIM}(absent — normal tant que le sync n'a pas tourné){RESET}"))

    print("\n═══ 2. DÉPENDANCES PYTHON ═══")
    check("jinja2", importlib.util.find_spec("jinja2") is not None,
          "pip install jinja2 --break-system-packages")
    check("yaml (PyYAML)", importlib.util.find_spec("yaml") is not None,
          "pip install pyyaml --break-system-packages")

    print("\n═══ 3. LE DASHBOARD ACTUEL VIENT-IL DU TEMPLATE ? ═══")
    target = DASH / "views" / "energy.yaml"
    if not target.exists():
        check("views/energy.yaml", False,
              "absent — utilisez le bouton CRÉER ENERGY du panneau ADMIN")
    else:
        content = target.read_text(encoding="utf-8", errors="replace")
        generated = "FICHIER GÉNÉRÉ" in content
        n_rows = content.count("template: vssp_energy_device_row")
        n_circ = content.count("template: vssp_circuit_switch")
        check("views/energy.yaml issu du template", generated,
              "c'est ENCORE le fichier écrit à la main : le dashboard "
              "affichera ses données d'origine tant qu'il n'est pas "
              "régénéré (bouton RÉGÉNÉRER ENERGY)",
              f"{n_rows} appareils, {n_circ} circuits affichés")
        if generated:
            print(f"      {DIM}dernière génération : "
                  f"{__import__('datetime').datetime.fromtimestamp(target.stat().st_mtime):%d/%m %H:%M}{RESET}")

    print("\n═══ 4. LE GÉNÉRATEUR TOURNE-T-IL ? ═══")
    if gen.exists():
        r = subprocess.run(
            [sys.executable, str(gen), "--dry-run",
             "--model", str(model), "--devices", str(devices),
             "--templates", str(DASH / "templates_j2"),
             "--out", str(DASH / "views")],
            capture_output=True, text=True)
        ok = r.returncode == 0
        check("generate_dashboards.py --dry-run", ok,
              "voir la sortie ci-dessous")
        for line in (r.stdout + r.stderr).strip().splitlines():
            print(f"      {DIM}{line}{RESET}")
    else:
        print(f"  {WARN} ignoré (script absent)")

    print("\n═══ 5. LE SCAN VOIT-IL VOS APPAREILS ? ═══")
    if not args.token:
        print(f"  {WARN} ignoré — relancez avec --token \"votre_jeton\"")
        print(f"      {DIM}Profil → Jetons d'accès longue durée{RESET}")
    elif not sync.exists():
        print(f"  {WARN} ignoré (script absent)")
    else:
        r = subprocess.run(
            [sys.executable, str(sync), "--token", args.token,
             "--url", args.url, "--devices", str(devices), "--dry-run"],
            capture_output=True, text=True)
        ok = r.returncode == 0
        check("vssp_energy_sync.py --dry-run", ok, "voir la sortie ci-dessous")
        for line in (r.stdout + r.stderr).strip().splitlines():
            print(f"      {DIM}{line}{RESET}")

    print("\n═══ VERDICT ═══")
    if not problems:
        print(f"  {OK} Chaîne complète. Si le dashboard affiche encore les "
              f"anciennes données,\n      lancez RÉGÉNÉRER ENERGY puis "
              f"rafraîchissez l'onglet (Ctrl+Maj+R).")
        return 0
    print(f"  {KO} {len(problems)} maillon(s) à corriger :")
    for p in problems:
        print(f"      - {p}")
    print(f"\n  {DIM}Corrigez dans l'ordre affiché : chaque maillon dépend "
          f"des précédents.{RESET}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
