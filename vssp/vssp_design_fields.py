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
# Visio Sapiens — Design token vocabulary (shared, dependency-free)
#
# EN | Single source of truth for the flat token names the THEME editor's
# EN | form, the webhook payload and the status file all use, and how each
# EN | one maps onto the nested `design:` structure of design_system.yaml.
# EN | Deliberately stdlib-only: generate_dashboards.py imports it to write
# EN | design_system_status.json, and its only other dependencies are jinja2
# EN | + pyyaml (see docs/dashboards/Dashboard_Generator.md) — it must never gain a hard
# EN | dependency on ruamel.yaml, which vssp_theme_apply.py needs only to
# EN | rewrite design_system.yaml with its comments intact. Splitting this
# EN | table out of vssp_theme_apply.py is what keeps that boundary real.
# FR | Source unique de verite pour les noms plats de tokens qu utilisent le
# FR | formulaire de l editeur THEME, le payload du webhook et le fichier de
# FR | statut, et pour la correspondance de chacun vers la structure imbriquee
# FR | `design:` de design_system.yaml.
# FR | Deliberement stdlib uniquement : generate_dashboards.py l importe pour
# FR | ecrire design_system_status.json, et ses seules autres dependances sont
# FR | jinja2 + pyyaml (voir docs/dashboards/Dashboard_Generator.md) — il ne doit jamais
# FR | acquerir de dependance dure a ruamel.yaml, dont vssp_theme_apply.py a
# FR | seul besoin pour reecrire design_system.yaml sans perdre ses
# FR | commentaires. Extraire cette table de vssp_theme_apply.py est ce qui
# FR | rend cette frontiere reelle.
# ============================================================================
from __future__ import annotations

import re

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
_RGBA_RE = re.compile(
    r"^rgba\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(0|1|0?\.\d+)\s*\)$")
_LENGTH_RE = re.compile(r"^\d{1,3}px$")

# EN | payload/form key -> (path inside `design:`, kind, max px for lengths)
# FR | cle du payload/formulaire -> (chemin sous `design:`, nature, max px)
FIELDS: dict[str, tuple[tuple[str, ...], str, int]] = {
    "primary":                     (("palette", "primary"), "color", 0),
    "accent":                      (("palette", "accent"), "color", 0),
    "background":                  (("palette", "background"), "color", 0),
    "background_secondary":        (("palette", "background_secondary"), "color", 0),
    "card_background":             (("palette", "card_background"), "color", 0),
    "selector_background":         (("palette", "selector_background"), "color", 0),
    "input_background":            (("palette", "input_background"), "color", 0),
    "input_ink":                   (("palette", "input_ink"), "color", 0),
    "input_label":                 (("palette", "input_label"), "color", 0),
    "text_primary":                (("palette", "text_primary"), "color", 0),
    "text_secondary":              (("palette", "text_secondary"), "color", 0),
    "header_background":           (("header", "background"), "color", 0),
    "header_text":                 (("header", "text"), "color", 0),
    "divider":                     (("divider",), "color", 0),
    "icon_default":                (("icons", "default"), "color", 0),
    "icon_active":                 (("icons", "active"), "color", 0),
    "card_radius":                 (("shape", "card_radius"), "length", 60),
    "card_border_width":           (("shape", "card_border_width"), "length", 10),
    "dialog_radius":               (("shape", "dialog_radius"), "length", 60),
    "dialog_scrim":                (("dialog", "scrim"), "color", 0),
    "sidebar_background":          (("sidebar", "background"), "color", 0),
    "sidebar_text":                (("sidebar", "text"), "color", 0),
    "sidebar_icon":                (("sidebar", "icon"), "color", 0),
    "sidebar_selected_background": (("sidebar", "selected_background"), "color", 0),
    "sidebar_selected_text":       (("sidebar", "selected_text"), "color", 0),
    "sidebar_selected_icon":       (("sidebar", "selected_icon"), "color", 0),
    # EN | The one token allowed to be literally "transparent" as well as a color.
    # FR | Le seul token autorise a valoir litteralement "transparent", en plus d'une couleur.
    "bubble_backdrop":             (("bubble_backdrop",), "color_or_transparent", 0),
}


def is_color(value: str) -> bool:
    return bool(_HEX_RE.match(value) or _RGBA_RE.match(value))


def validate(payload: dict) -> tuple[dict, list]:
    """
    EN | Checks every submitted token against FIELDS. Returns
    EN | ({payload_key: value}, errors) — only tokens that passed validation
    EN | are in the first dict, so a single bad field never blocks the rest.
    FR | Verifie chaque token soumis face a FIELDS. Renvoie
    FR | ({cle_payload: valeur}, erreurs) — seuls les tokens valides figurent
    FR | dans le premier dict, un seul champ invalide ne bloque donc jamais
    FR | les autres.
    """
    errors: list = []
    accepted: dict = {}

    tokens = payload.get("tokens")
    if not isinstance(tokens, dict) or not tokens:
        errors.append("payload has no non-empty `tokens` object")
        return accepted, errors

    for key, raw_value in tokens.items():
        if key not in FIELDS:
            errors.append(f"unknown token `{key}` — ignored")
            continue
        _, kind, max_px = FIELDS[key]
        value = str(raw_value).strip()

        if kind == "color":
            if not is_color(value):
                errors.append(f"`{key}`: not a color (#RRGGBB or rgba(...)) — got `{value}`")
                continue
        elif kind == "color_or_transparent":
            if value != "transparent" and not is_color(value):
                errors.append(f"`{key}`: not a color nor `transparent` — got `{value}`")
                continue
        elif kind == "length":
            if not _LENGTH_RE.match(value):
                errors.append(f"`{key}`: not a pixel length (e.g. `18px`) — got `{value}`")
                continue
            if not (0 <= int(value[:-2]) <= max_px):
                errors.append(f"`{key}`: {value} out of range (0-{max_px}px)")
                continue

        accepted[key] = value

    return accepted, errors


def flatten(design) -> dict:
    """
    EN | Reads the current value of every known token straight out of
    EN | `design:` (nested) into the flat shape the editor's form and the
    EN | webhook payload both use. Used by generate_dashboards.py to write
    EN | design_system_status.json — the editor's form reads this file on
    EN | load, so the flat keys it sees are guaranteed to match what APPLY
    EN | (vssp_theme_apply.py, same FIELDS table) will accept back.
    FR | Lit la valeur courante de chaque token connu directement depuis
    FR | `design:` (imbrique) vers la forme plate qu utilisent aussi bien le
    FR | formulaire de l editeur que le payload du webhook. Utilise par
    FR | generate_dashboards.py pour ecrire design_system_status.json — le
    FR | formulaire de l editeur lit ce fichier au chargement, les cles
    FR | plates qu il voit correspondent donc forcement a ce qu APPLY
    FR | (vssp_theme_apply.py, meme table FIELDS) acceptera en retour.
    """
    flat = {}
    for key, (path, _, _) in FIELDS.items():
        node = design
        try:
            for segment in path:
                node = node[segment]
        except (KeyError, TypeError):
            continue
        flat[key] = node
    return flat
