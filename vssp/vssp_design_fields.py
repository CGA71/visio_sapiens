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
_PERCENT_RE = re.compile(r"^\d{2,3}%$")
# EN | Bounds of a size scale. Below half, a 9px label drops under 5px; above
# EN | double, the 24px header clock overflows its band.
# FR | Bornes d'une echelle de taille. Sous la moitie, un libelle de 9px passe
# FR | sous 5px ; au-dela du double, l'horloge de 24px deborde de son bandeau.
SCALE_MIN, SCALE_MAX = 50, 200

# EN | TYPEFACES — a closed list, never free text. A font token is a family
# EN | NAME the editor picks from this list; the theme gets the full CSS stack
# EN | beside it (font_stack). Closed because a family name is only half a
# EN | font: the file has to be served too. Every name here except Roboto and
# EN | System has its woff2 under www/vssp/fonts/, declared in vssp_fonts.css;
# EN | Roboto ships with the Home Assistant frontend, System is the device's
# EN | own. A free-text "Comic Neue" would validate, render into the theme,
# EN | and quietly fall back to sans-serif on every screen — the far-from-
# EN | its-cause failure the validation below exists to prevent.
# FR | POLICES — une liste fermee, jamais du texte libre. Un token de police
# FR | est un NOM de famille choisi dans cette liste ; le theme recoit la
# FR | pile CSS complete a cote (font_stack). Fermee parce qu'un nom de
# FR | famille n'est que la moitie d'une police : il faut aussi servir le
# FR | fichier. Chaque nom ici sauf Roboto et System a son woff2 sous
# FR | www/vssp/fonts/, declare dans vssp_fonts.css ; Roboto est livre avec
# FR | le frontend Home Assistant, System est celle de l'appareil. Un
# FR | « Comic Neue » en texte libre passerait la validation, se rendrait dans
# FR | le theme, et retomberait en silence sur sans-serif sur chaque ecran —
# FR | la panne loin de sa cause que la validation ci-dessous doit empecher.
FONTS: dict[str, str] = {
    "Orbitron":        "'Orbitron', 'Segoe UI', system-ui, sans-serif",
    "Rajdhani":        "'Rajdhani', 'Segoe UI', system-ui, sans-serif",
    "Exo 2":           "'Exo 2', 'Segoe UI', system-ui, sans-serif",
    "Oxanium":         "'Oxanium', 'Segoe UI', system-ui, sans-serif",
    "Chakra Petch":    "'Chakra Petch', 'Segoe UI', system-ui, sans-serif",
    "Share Tech Mono": "'Share Tech Mono', ui-monospace, monospace",
    "Roboto":          "Roboto, Noto, sans-serif",
    "System":          "system-ui, -apple-system, 'Segoe UI', sans-serif",
}

# EN | What each font token falls back to when design_system.yaml predates
# EN | `typography:` — the pod keeps its own copy across deploys, so the
# EN | section is missing there until the THEME editor first writes it. The
# EN | values are the look before fonts were configurable: Orbitron for every
# EN | HUD label, Home Assistant's own Roboto for the rest.
# FR | Ce vers quoi chaque token de police se replie quand design_system.yaml
# FR | est anterieur a `typography:` — le pod garde sa propre copie d'un
# FR | deploiement a l'autre, la section y manque donc jusqu'a ce que
# FR | l'editeur THEME l'ecrive une premiere fois. Les valeurs sont l'aspect
# FR | d'avant les polices configurables : Orbitron pour chaque libelle HUD,
# FR | le Roboto de Home Assistant pour le reste.
FONT_DEFAULTS: dict[str, str] = {
    "font_display": "Orbitron",
    "font_body":    "Roboto",
}

# EN | TEXT SIZES BY USAGE — one scale per role rather than one size per
# EN | role, because a role spans several sizes on purpose: a "title" is 20px
# EN | in the header, 15px on a section, 11px on a subsection, and 17px on
# EN | mobile. One pixel value per role would flatten that hierarchy; a
# EN | percentage multiplies it. Every literal font-size in the templates is
# EN | written calc(<px> * var(--vssp-scale-<role>, 1)), classified by what
# EN | the text IS:
# EN |   clock  the header clock digits
# EN |   title  header title, sidebar logo, page/section/card headings
# EN |   value  a reading: power, energy, temperature, amps, a device state
# EN |   text   names — nav entries, devices, rows — and HA's own text
# EN |   label  captions, units, hints, column headers, legends, badges
# EN | Missing from an older pod-side design_system.yaml = 100%, the look
# EN | before sizes were configurable.
# FR | TAILLES DE TEXTE PAR USAGE — une echelle par role plutot qu'une taille
# FR | par role, car un role couvre volontairement plusieurs tailles : un
# FR | « titre » fait 20px dans le header, 15px sur une section, 11px sur une
# FR | sous-section, 17px en mobile. Une valeur en pixels par role ecraserait
# FR | cette hierarchie ; un pourcentage la multiplie. Chaque font-size
# FR | litteral des templates s'ecrit calc(<px> * var(--vssp-scale-<role>, 1)),
# FR | classe selon ce qu'EST le texte :
# FR |   clock  les chiffres de l'horloge du header
# FR |   title  titre du header, logo de la sidebar, titres de page/section/carte
# FR |   value  une mesure : puissance, energie, temperature, amperes, un etat
# FR |   text   les noms — entrees de nav, appareils, lignes — et le texte de HA
# FR |   label  legendes, unites, aides, en-tetes de colonne, badges
# FR | Absent d'un design_system.yaml ancien cote pod = 100 %, l'aspect
# FR | d'avant les tailles configurables.
SCALE_DEFAULT = "100%"

# EN | NAV LOGO — the image under the navigation rail. Three states:
# EN |   "default"   house.logo from house.yaml, as before
# EN |   "none"      nothing: the square collapses, the rail gets the room
# EN |   "custom:nav_logo.<webp|png|jpg>?v=<YYYYmmddHHMMSS>"
# EN |               an image sent from the THEME screen. Only
# EN |               vssp_theme_apply.py writes this form, after checking
# EN |               the file; ?v= is the cache key, since /local is served
# EN |               with a one-month max-age.
# EN | The file lives in www/vssp_user/, NOT www/vssp/: each deploy replaces
# EN | www/vssp wholesale, and an uploaded logo would vanish with it.
# FR | LOGO DE NAV — l'image sous le bandeau de navigation. Trois etats :
# FR |   "default"   house.logo de house.yaml, comme avant
# FR |   "none"      rien : le carre disparait, le bandeau recupere la place
# FR |   "custom:nav_logo.<webp|png|jpg>?v=<AAAAmmjjHHMMSS>"
# FR |               une image envoyee depuis l'ecran THEME. Seul
# FR |               vssp_theme_apply.py ecrit cette forme, apres avoir
# FR |               verifie le fichier ; ?v= est la cle de cache, /local
# FR |               etant servi avec un max-age d'un mois.
# FR | Le fichier vit dans www/vssp_user/, PAS www/vssp/ : chaque deploiement
# FR | remplace www/vssp en bloc, et un logo envoye disparaitrait avec lui.
_LOGO_CUSTOM_RE = re.compile(r"^custom:(nav_logo\.(?:webp|png|jpg))\?v=\d{14}$")
LOGO_URL_DIR = "/local/vssp_user"

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
    # EN | display = the HUD face (nav rail, header clock, titles, values);
    # EN | body = every other piece of text on the generated dashboards.
    # FR | display = la police HUD (bandeau de nav, horloge du header, titres,
    # FR | valeurs) ; body = tout le reste du texte des dashboards generes.
    "font_display":                (("typography", "display"), "font", 0),
    "font_body":                   (("typography", "body"), "font", 0),
    # EN | Size scales by usage (see SCALE_DEFAULT) — "NNN%".
    # FR | Echelles de taille par usage (voir SCALE_DEFAULT) — "NNN%".
    "size_clock":                  (("typography", "size", "clock"), "scale", 0),
    "size_title":                  (("typography", "size", "title"), "scale", 0),
    "size_value":                  (("typography", "size", "value"), "scale", 0),
    "size_text":                   (("typography", "size", "text"), "scale", 0),
    "size_label":                  (("typography", "size", "label"), "scale", 0),
    # EN | See _LOGO_CUSTOM_RE for the three accepted forms.
    # FR | Voir _LOGO_CUSTOM_RE pour les trois formes acceptees.
    "nav_logo":                    (("nav_logo",), "logo", 0),
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
        elif kind == "font":
            if value not in FONTS:
                errors.append(f"`{key}`: unknown font `{value}` — "
                              f"one of: {', '.join(FONTS)}")
                continue
        elif kind == "scale":
            if not _PERCENT_RE.match(value):
                errors.append(f"`{key}`: not a percentage (e.g. `100%`) — got `{value}`")
                continue
            if not (SCALE_MIN <= int(value[:-1]) <= SCALE_MAX):
                errors.append(f"`{key}`: {value} out of range ({SCALE_MIN}-{SCALE_MAX}%)")
                continue
        elif kind == "logo":
            if value not in ("default", "none") and not _LOGO_CUSTOM_RE.match(value):
                errors.append(f"`{key}`: expected `default`, `none` or an "
                              f"uploaded logo — got `{value}`")
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


def font_stack(design, key: str) -> str:
    """
    EN | The CSS font-family stack theme.yaml.j2 writes for one font token,
    EN | read out of `design:`. A missing `typography:` section or a name that
    EN | left the list since it was saved both resolve to FONT_DEFAULTS, so
    EN | the theme always renders — see FONT_DEFAULTS for why it can be absent.
    FR | La pile CSS font-family que theme.yaml.j2 ecrit pour un token de
    FR | police, lue depuis `design:`. Une section `typography:` absente ou un
    FR | nom sorti de la liste depuis son enregistrement se replient tous deux
    FR | sur FONT_DEFAULTS, pour que le theme se rende toujours — voir
    FR | FONT_DEFAULTS pour la raison de cette absence.
    """
    path, _, _ = FIELDS[key]
    node = design
    try:
        for segment in path:
            node = node[segment]
    except (KeyError, TypeError):
        node = None
    if not isinstance(node, str) or node not in FONTS:
        node = FONT_DEFAULTS[key]
    return FONTS[node]


def size_scale(design, key: str) -> str:
    """
    EN | The unitless multiplier theme.yaml.j2 writes for one size token
    EN | ("120%" -> "1.2"), for calc(<px> * var(--vssp-scale-<role>, 1)).
    EN | Missing or out of bounds resolves to SCALE_DEFAULT, like font_stack.
    FR | Le multiplicateur sans unite que theme.yaml.j2 ecrit pour un token de
    FR | taille ("120%" -> "1.2"), pour calc(<px> * var(--vssp-scale-<role>, 1)).
    FR | Absent ou hors bornes, il vaut SCALE_DEFAULT, comme font_stack.
    """
    path, _, _ = FIELDS[key]
    node = design
    try:
        for segment in path:
            node = node[segment]
    except (KeyError, TypeError):
        node = None
    value = str(node).strip() if node is not None else ""
    if not _PERCENT_RE.match(value) or not (
            SCALE_MIN <= int(value[:-1]) <= SCALE_MAX):
        value = SCALE_DEFAULT
    return f"{int(value[:-1]) / 100:g}"


def logo_filename(value: str):
    """
    EN | The file name inside www/vssp_user/ a custom nav_logo value points
    EN | at ("custom:nav_logo.webp?v=..." -> "nav_logo.webp"), else None.
    FR | Le nom de fichier sous www/vssp_user/ que vise une valeur nav_logo
    FR | personnalisee ("custom:nav_logo.webp?v=..." -> "nav_logo.webp"),
    FR | sinon None.
    """
    m = _LOGO_CUSTOM_RE.match(str(value or ""))
    return m.group(1) if m else None


def nav_logo(design, house) -> dict:
    """
    EN | What theme.yaml.j2 writes for the nav logo: the CSS `image` for
    EN | --vssp-nav-logo and the `display` for --vssp-nav-logo-display.
    EN | Anything unreadable resolves to the default logo, never to a broken
    EN | url().
    FR | Ce que theme.yaml.j2 ecrit pour le logo de nav : l'`image` CSS pour
    FR | --vssp-nav-logo et le `display` pour --vssp-nav-logo-display. Toute
    FR | valeur illisible se replie sur le logo par defaut, jamais sur un
    FR | url() casse.
    """
    value = design.get("nav_logo", "default") if isinstance(design, dict) else "default"
    if value == "none":
        return {"image": "none", "display": "none"}
    custom = _LOGO_CUSTOM_RE.match(str(value))
    if custom:
        url = f"{LOGO_URL_DIR}/{str(value)[len('custom:'):]}"
    else:
        url = (house or {}).get("logo") or ""
    if not url:
        return {"image": "none", "display": "none"}
    return {"image": f"url('{url}')", "display": "block"}
