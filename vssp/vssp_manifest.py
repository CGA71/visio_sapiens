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
# Visio Sapiens - vssp_manifest.py
#
# EN | One reader for requirements.yaml, so the three programs that care
# EN | about prerequisites cannot drift apart: vssp_preflight.py refuses a
# EN | deployment, vssp_prepare.py repairs what can be repaired, and
# EN | vssp_dependencies.py reports from the ADMIN console. Before this file
# EN | they each carried their own list, and the console announced "18 of 18
# EN | in place" on an instance whose header band was empty.
# FR | Un seul lecteur de requirements.yaml, pour que les trois programmes
# FR | qui s occupent des prerequis ne puissent pas diverger :
# FR | vssp_preflight.py refuse un deploiement, vssp_prepare.py repare ce qui
# FR | peut l etre, et vssp_dependencies.py rapporte depuis la console ADMIN.
# FR | Avant ce fichier, chacun portait sa propre liste, et la console
# FR | annoncait « 18 sur 18 en place » sur une instance au bandeau vide.
#
# EN | The manifest travels with the code: it sits next to these scripts and
# EN | is copied onto the instance with them, so a checkout and a deployed
# EN | instance always answer the same question the same way.
# FR | Le manifeste voyage avec le code : il est a cote de ces scripts et est
# FR | copie sur l instance avec eux, pour qu un depot et une instance
# FR | deployee repondent toujours pareil a la meme question.
# ============================================================================
from __future__ import annotations

from pathlib import Path

DEFAULT = Path(__file__).resolve().parent / "requirements.yaml"


def load(path: str | None = None) -> dict:
    """EN | The manifest as a dict, or {} when it cannot be read - a caller
    EN | that gets {} must say so rather than conclude that nothing is
    EN | required.
    FR | Le manifeste en dictionnaire, ou {} s il n est pas lisible - un
    FR | appelant qui recoit {} doit le dire plutot que de conclure que rien
    FR | n est requis."""
    import yaml  # EN | imported here: a caller may only need the path

    target = Path(path) if path else DEFAULT
    try:
        data = yaml.safe_load(target.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def cards(man: dict) -> list:
    """EN | [(owner/name, blocking, why_en, why_fr)]
    FR | [(proprietaire/nom, bloquant, pourquoi_en, pourquoi_fr)]"""
    out = []
    for row in man.get("cards") or []:
        if isinstance(row, dict) and row.get("repo"):
            out.append((str(row["repo"]), bool(row.get("blocking")),
                        str(row.get("why_en") or ""),
                        str(row.get("why_fr") or "")))
    return out


def integrations(man: dict) -> list:
    out = []
    for row in man.get("integrations") or []:
        if isinstance(row, dict) and row.get("domain"):
            out.append((str(row["domain"]), bool(row.get("blocking")),
                        str(row.get("why_en") or ""),
                        str(row.get("why_fr") or "")))
    return out


def core_integrations(man: dict) -> list:
    """EN | [(domain, display name, why_en, why_fr)] - never blocking: each
    EN | feeds one tile, and a house that has not added them still gets a
    EN | control centre that works.
    FR | [(domaine, nom affiche, pourquoi_en, pourquoi_fr)] - jamais
    FR | bloquantes : chacune alimente une tuile, et une maison qui ne les a
    FR | pas ajoutees obtient quand meme un centre de controle qui marche."""
    out = []
    for row in man.get("core_integrations") or []:
        if isinstance(row, dict) and row.get("domain"):
            out.append((str(row["domain"]),
                        str(row.get("name") or row["domain"]),
                        str(row.get("why_en") or ""),
                        str(row.get("why_fr") or "")))
    return out
