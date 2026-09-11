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

"""
Visio Sapiens dashboard generator.

EN | USAGE
FR | UTILISATION
    # EN | from the repo root (defaults match the tree)
    # FR | depuis la racine du repo (defauts alignes sur l'arborescence)
    python3 vssp/generate_dashboards.py                    # publish
    python3 vssp/generate_dashboards.py --locale fr        # French deliverable
    python3 vssp/generate_dashboards.py --format both      # tablet + mobile
    python3 vssp/generate_dashboards.py --preview          # isolated TEST dashboard
    python3 vssp/generate_dashboards.py --dry-run          # validation only
    python3 vssp/generate_dashboards.py --only theme       # theme file only, from design_system.yaml
    # EN | or on the HA pod (see vssp/vssp_admin_config.yaml):
    # FR | ou sur le pod HA (voir vssp/vssp_admin_config.yaml) :
    python3 /config/vssp/generate_dashboards.py --model ... --templates ... --out ...

EN | PIPELINE (step 5 of the admin process)
FR | CHAINE (etape 5 du processus admin)
    house.yaml (home model) + locales/<code>.yaml + *.yaml.j2
        -> dashboards/views/*.yaml

EN | The render is validated (parsable YAML, !include tags tolerated) BEFORE
EN | the target file is overwritten: a broken dashboard is never deployed.
EN | Designed to be called by a Home Assistant shell_command at the end of the
EN | scan/assignment process.
FR | Le rendu est valide (YAML parsable, tags !include toleres) AVANT
FR | d'ecraser le fichier cible : jamais de dashboard casse deploye.
FR | Pense pour etre appele par un shell_command Home Assistant a la fin du
FR | processus scan/assignation.
"""
import argparse
import json
import re
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound

# EN | The i18n engine lives next to this script, whether the repo root or
# EN | /config/vssp/ is the working directory.
# FR | Le moteur i18n vit a cote de ce script, que le repertoire courant soit la
# FR | racine du repo ou /config/vssp/.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vssp_i18n  # noqa: E402
import vssp_design_fields  # noqa: E402

# ----------------------------------------------------------------------------
# EN | SYSTEM DASHBOARDS — the four mandatory ones. They depend on no room and
# EN | therefore never go through the room create/modify/delete form. They are
# EN | generated from the ADMIN console.
# FR | DASHBOARDS SYSTEME — les quatre obligatoires. Ils ne dependent d'aucune
# FR | piece et ne passent donc jamais par le formulaire de creation/
# FR | modification/suppression des pieces. Ils se generent depuis la console
# FR | ADMIN.
# ----------------------------------------------------------------------------
SYSTEM_DASHBOARDS = [
    ("home",   "home.yaml.j2",   "home.yaml",   {"active_nav": "home"}),
    ("core",   "core.yaml.j2",   "core.yaml",   {"active_nav": "core"}),
    ("energy", "energy.yaml.j2", "energy.yaml", {"active_nav": "energy"}),
    ("admin",  "admin.yaml.j2",  "admin.yaml",  {"active_nav": "admin"}),
]

# EN | These three are created on demand from the ADMIN console (CREER
# EN | HOME/ENERGY/CORE), not always present — so their nav entry must be
# EN | conditional on the file actually existing, or the rail lies about
# EN | what a fresh (or emptied) instance actually offers. `admin` is
# EN | deliberately NOT in this set: it is the only way back into the
# EN | console, so it must never be able to disappear from the rail.
# FR | Ces trois sont crees a la demande depuis la console ADMIN (CREER
# FR | HOME/ENERGY/CORE), pas toujours presents — leur entree de bandeau
# FR | doit donc dependre de l existence reelle du fichier, sinon le bandeau
# FR | ment sur ce qu une instance neuve (ou videe) offre vraiment. `admin`
# FR | est deliberement EXCLU de cet ensemble : c est le seul chemin de
# FR | retour vers la console, il ne doit jamais pouvoir disparaitre du
# FR | bandeau.
OPTIONAL_SYSTEM_NAV_IDS = {"home", "core", "energy"}

# EN | HOME is the one system dashboard meant for manual Lovelace editing
# EN | after creation — it must never be silently overwritten by a caller
# EN | that has no reason to know that, unlike energy/core/admin/rooms
# EN | which are always regenerated fresh from the model. This is the
# EN | DEFAULT for --protect-existing (see argparse below): every routine
# EN | caller (the ROOMS-sync / ASSIGN-save webhook automations, the CI
# EN | build, the CI pod-side regeneration) gets it for free by not passing
# EN | the flag at all. The one caller that must be allowed to overwrite —
# EN | the explicit "REGENERATE HOME" admin button — passes
# EN | --protect-existing "" to opt out for that one run.
# FR | HOME est le seul dashboard systeme destine a une edition Lovelace
# FR | manuelle apres creation — il ne doit jamais etre ecrase en silence
# FR | par un appelant qui n a aucune raison de le savoir, contrairement a
# FR | energy/core/admin/rooms toujours regeneres a neuf depuis le modele.
# FR | C est la valeur PAR DEFAUT de --protect-existing (voir argparse plus
# FR | bas) : chaque appelant routinier (les automations webhook sync ROOMS
# FR | / enregistrement ASSIGN, le build CI, la regeneration cote pod du
# FR | CI) l obtient gratuitement en ne passant pas l option du tout. Le
# FR | seul appelant qui doit pouvoir ecraser — le bouton admin explicite
# FR | « REGENERER HOME » — passe --protect-existing "" pour s en exempter
# FR | le temps de ce run.
DEFAULT_PROTECTED_DASHBOARD_IDS = "home"

# EN | One shared template renders every room OF A GIVEN FORMAT. The
# EN | differences between rooms live in the data (slot set, device lists),
# EN | never in a second template.
# EN | Formats are a different matter: a phone is not a narrow tablet. The
# EN | navigation rail becomes a scrolling chip bar, the grid collapses to a
# EN | single column with one slot per row, and the type scale shrinks. Trying
# EN | to express that with `{% if format == 'mobile' %}` inside one file
# EN | produces a template that is hard to read and, worse, silently renders a
# EN | tablet layout under a mobile filename when a branch is missing.
# EN | So: one template per format, and the generator refuses to substitute
# EN | one for the other.
# FR | Un unique template partage rend toutes les pieces D'UN FORMAT DONNE.
# FR | Les differences entre pieces vivent dans la donnee (jeu de tableaux,
# FR | listes d'appareils), jamais dans un second template.
# FR | Les formats sont un autre sujet : un telephone n'est pas une tablette
# FR | etroite. Le bandeau de navigation devient une barre de chips
# FR | defilante, la grille s'effondre en une colonne avec un tableau par
# FR | ligne, et l'echelle typographique diminue. Exprimer cela avec des
# FR | `{% if format == 'mobile' %}` dans un seul fichier produit un template
# FR | illisible et, pire, rend en silence une disposition tablette sous un
# FR | nom de fichier mobile quand une branche manque.
# FR | Donc : un template par format, et le generateur refuse de substituer
# FR | l'un a l'autre.
ROOM_TEMPLATE = "room.yaml.j2"

# EN | Dashboards that exist in the tablet format ONLY, by design.
# EN | The admin console is desk work — declaring rooms, assigning eighty
# EN | devices, importing a stylesheet — and a phone is the wrong place for
# EN | all of it. There is therefore no admin_mobile.yaml.j2 and there is not
# EN | meant to be one.
# EN | Listing it here rather than letting the template simply be missing is
# EN | the difference between a decision and an oversight: without this, every
# EN | build printed `[skip] admin_mobile.yaml.j2 not found`, a warning about
# EN | something nobody intends to fix. A guard that cries wolf on purpose is
# EN | a guard people learn to ignore.
# FR | Dashboards qui n existent qu au format tablette, par conception.
# FR | La console d administration est un travail de bureau — declarer des
# FR | pieces, assigner quatre-vingts appareils, importer une feuille de style
# FR | — et un telephone est le mauvais endroit pour tout cela. Il n existe
# FR | donc pas d admin_mobile.yaml.j2, et il n est pas prevu d en avoir un.
# FR | Le lister ici plutot que de laisser le template simplement absent fait
# FR | la difference entre une decision et un oubli : sans cela, chaque build
# FR | affichait `[skip] admin_mobile.yaml.j2 not found`, un avertissement sur
# FR | quelque chose que personne ne compte corriger. Un garde-fou qui crie au
# FR | loup volontairement est un garde-fou qu on apprend a ignorer.
TABLET_ONLY = {"admin"}


def template_for(tpl_name: str, target_format: str) -> str:
    """
    EN | `room.yaml.j2` -> `room_mobile.yaml.j2` for the mobile format.
    FR | `room.yaml.j2` -> `room_mobile.yaml.j2` pour le format mobile.
    """
    if target_format != "mobile":
        return tpl_name
    return tpl_name.replace(".yaml.j2", "_mobile.yaml.j2")

# EN | Canonical slot order. The identifier is used as the key in house.yaml,
# EN | as the CSS grid-area and as the section name in the template — the three
# EN | must be the same string. Never translated; only slot.<id> labels are.
# FR | Ordre canonique des tableaux. L'identifiant sert de cle dans house.yaml,
# FR | de grid-area CSS et de nom de section dans le template — les trois
# FR | doivent etre la meme chaine. Jamais traduit ; seuls les libelles
# FR | slot.<id> le sont.
SLOTS = ["sensors", "switches", "appliances", "security", "infrastructure"]

# EN | Slot sets. `default` applies unless the room says otherwise.
# FR | Jeux de tableaux. `default` s'applique sauf mention contraire.
DEFAULT_SLOT_SETS = {
    "default":       ["sensors", "switches", "appliances", "security"],
    "toilet":        ["sensors", "switches"],
    "garden":        ["sensors", "switches", "appliances", "security"],
    "utility":       ["sensors", "switches", "appliances", "security"],
    # EN | No sensors slot: an entrance has no thermostat of its own.
    # FR | Pas de tableau sensors : l'entree n'a pas son propre thermostat.
    "entrance":      ["switches", "security"],
    "minimal":       ["switches", "security"],
    # EN | Named after the room TYPE (room_icons/locales `computer`), not
    # EN | after any one room's own id — a slot set is a reusable preset,
    # EN | the same way `toilet`/`garden`/`entrance` are, not something tied
    # EN | to a specific room instance.
    # EN | Server, network switch, ISP box, firewall — no HA domain or
    # EN | device_class reliably tells this apart from an ordinary sensor or
    # EN | switch, so this is the one slot with no automatic suggestion
    # EN | (see DEVICE_CLASS_HINT/DOMAIN_HINT in vssp_assign_prepare.py): the
    # EN | admin picks it by hand in the assignment form.
    # FR | Nomme d'apres le TYPE de piece (room_icons/locales `computer`),
    # FR | pas d'apres l'id d'une piece en particulier — un jeu de tableaux
    # FR | est un preset reutilisable, au meme titre que `toilet`/`garden`/
    # FR | `entrance`, pas quelque chose de lie a une instance de piece
    # FR | precise.
    # FR | Serveur, switch reseau, box FAI, firewall — aucun domaine ni
    # FR | device_class Home Assistant ne distingue fiablement cela d'un
    # FR | capteur ou interrupteur ordinaire, donc c'est le seul tableau sans
    # FR | suggestion automatique (voir DEVICE_CLASS_HINT/DOMAIN_HINT dans
    # FR | vssp_assign_prepare.py) : l'administrateur le choisit a la main
    # FR | dans le formulaire d'assignation.
    "computer": ["sensors", "switches", "infrastructure", "security"],
}

# ----------------------------------------------------------------------------
# EN | GRID LAYOUT — computed per room by compute_room_layout(), not a fixed
# EN | preset per slot_set. See docs/dashboards/Dashboard_Generator.md, "Room dashboard
# EN | grid — dynamic slot layout" for the full design. Replaced the old
# EN | hand-drawn DEFAULT_LAYOUTS (one grid per slot_set, same proportions for
# EN | every room sharing a set regardless of how many devices each slot
# EN | actually held, and an empty slot still rendered a "no device" card).
# FR | GABARIT DE GRILLE — calcule par piece par compute_room_layout(), plus
# FR | un preset fixe par slot_set. Voir docs/dashboards/Dashboard_Generator.md,
# FR | « Room dashboard grid — dynamic slot layout » pour la conception
# FR | complete. Remplace l'ancien DEFAULT_LAYOUTS ecrit a la main (une grille
# FR | par slot_set, memes proportions pour toute piece partageant ce jeu quel
# FR | que soit le nombre d'appareils par tableau, et un tableau vide affichait
# FR | quand meme une carte "aucun appareil").
# ----------------------------------------------------------------------------

# EN | At most one Visio Sapiens filler animation per dashboard, on the first
# EN | slot of this list that is in the room's set and holds no device.
# EN | Empty on purpose. `switches` was tried here after the five-slot rework
# EN | (FILLER_PRIORITY previously read ["shutters", "audio"]), but the
# EN | filler card's markup — a full-bleed <img ... object-fit:cover> — was
# EN | designed for a roughly card-shaped panel, and switches is now ALWAYS
# EN | a full-width horizontal strip: the same image renders as a thin,
# EN | stretched sliver instead of the intended hero visual. On top of that,
# EN | the default asset (house.filler_animation, /local/vssp/images/
# EN | vssp_loop.gif) does not actually exist on this deployment — only
# EN | desk.png, floorplan.png, logo_VS-Sapiens.png and radar.gif are in
# EN | www/vssp/images/ — so the filler card rendered a broken image on top
# EN | of the aspect-ratio problem. No slot here currently has a shape this
# EN | card was designed for; re-enable by picking a real (tall-ish) slot
# EN | AND supplying/confirming a real asset for house.filler_animation.
# FR | Au plus une animation Visio Sapiens de remplissage par dashboard, sur
# FR | le premier tableau de cette liste appartenant au jeu de la piece et ne
# FR | contenant aucun appareil.
# FR | Vide volontairement. `switches` avait ete essaye ici apres la refonte
# FR | a cinq tableaux (FILLER_PRIORITY valait avant ["shutters", "audio"]),
# FR | mais le balisage de la carte de remplissage — un <img ...
# FR | object-fit:cover> pleine carte — a ete concu pour un panneau a peu
# FR | pres carre, et switches est desormais TOUJOURS un bandeau horizontal
# FR | pleine largeur : la meme image se rend en fine lamelle etiree au lieu
# FR | du visuel vedette prevu. En plus de cela, l'actif par defaut
# FR | (house.filler_animation, /local/vssp/images/vssp_loop.gif) n'existe
# FR | pas reellement sur ce deploiement — seuls desk.png, floorplan.png,
# FR | logo_VS-Sapiens.png et radar.gif sont dans www/vssp/images/ — donc la
# FR | carte de remplissage rendait une image cassee en plus du probleme de
# FR | proportions. Aucun tableau ici n'a actuellement la forme prevue pour
# FR | cette carte ; la reactiver suppose de choisir un vrai tableau (plutot
# FR | haut) ET de fournir/confirmer un vrai actif pour house.filler_animation.
FILLER_PRIORITY = []

T_PLACEHOLDER = re.compile(r"__T:[A-Za-z0-9_.]+__")


def slug(value: str) -> str:
    """
    EN | Turns a room id into a Home Assistant dashboard url_path.
    EN | HA requires the url_path to contain a hyphen and rejects some
    EN | characters; underscores in particular are a known source of silently
    EN | unreachable dashboards. `living_room` therefore becomes
    EN | `visio-sapiens-living-room`, while the VIEW path keeps the raw id —
    EN | view paths have no such restriction, and the id stays the single
    EN | identifier used everywhere else.
    FR | Transforme un id de piece en url_path de dashboard Home Assistant.
    FR | HA exige que l'url_path contienne un tiret et rejette certains
    FR | caracteres ; les underscores en particulier sont une source connue de
    FR | dashboards silencieusement inatteignables. `living_room` devient donc
    FR | `visio-sapiens-living-room`, tandis que le chemin de VUE garde l'id
    FR | brut — les chemins de vue n'ont pas cette restriction, et l'id reste
    FR | l'identifiant unique utilise partout ailleurs.
    """
    return str(value).replace("_", "-").lower()


class HaLoader(yaml.SafeLoader):
    """
    EN | SafeLoader tolerating Home Assistant tags (!include, etc.).
    FR | SafeLoader qui tolere les tags Home Assistant (!include, etc.).
    """


for _tag in ("!include", "!include_dir_list", "!include_dir_named",
             "!include_dir_merge_list", "!include_dir_merge_named",
             "!secret", "!env_var", "!input"):
    HaLoader.add_constructor(_tag, lambda loader, node: node.value)


# ----------------------------------------------------------------------------
# EN | Model validation
# FR | Validation du modele
# ----------------------------------------------------------------------------
def validate_model(model: dict) -> tuple[list, list]:
    """
    EN | Business checks — returns (blocking errors, warnings).
    FR | Controles metier — renvoie (erreurs bloquantes, avertissements).
    """
    errors: list = []
    warnings: list = []
    seen_entities = {}

    for d in model.get("energy_devices", []):
        # EN | Blocking: without these fields the card cannot render.
        # FR | Bloquant : sans ces champs, la carte ne peut pas s'afficher.
        for field in ("name", "icon", "power_entity", "energy_entity"):
            if not d.get(field):
                errors.append(f"Device \u00ab {d.get('name', '?')} \u00bb: "
                              f"missing field `{field}`")
        # EN | Informative: the model comes from the HA registry when available,
        # EN | otherwise it stays to be filled in — not a reason to refuse the
        # EN | whole dashboard.
        # FR | Informatif : le modele vient du registre HA quand il est
        # FR | disponible, sinon il reste a completer — ce n'est pas une raison
        # FR | de refuser tout le dashboard.
        if not d.get("model"):
            warnings.append(f"Device \u00ab {d.get('name', '?')} \u00bb: "
                            f"unknown model")
        ent = d.get("power_entity")
        if ent in seen_entities:
            errors.append(f"Entity {ent} listed twice "
                          f"(\u00ab {seen_entities[ent]} \u00bb and "
                          f"\u00ab {d.get('name')} \u00bb)")
        seen_entities[ent] = d.get("name")

    for c in model.get("circuits", []):
        for field in ("name", "icon", "entity"):
            if not c.get(field):
                errors.append(f"Circuit \u00ab {c.get('name', '?')} \u00bb: "
                              f"missing field `{field}`")
        # EN | The rating is never auto-discoverable: it is read off the
        # EN | breaker. Reported, never blocking.
        # FR | Le calibre n'est jamais decouvrable automatiquement : il se lit
        # FR | sur le disjoncteur. Signale, jamais bloquant.
        if not c.get("amp"):
            warnings.append(f"Circuit \u00ab {c.get('name', '?')} \u00bb: "
                            f"rating (amp) to fill in")

    # EN | Modules of the virtual breaker panel. A module with no channel
    # EN | would draw an empty rail: worth saying, never worth blocking.
    # FR | Modules du tableau electrique virtuel. Un module sans voie
    # FR | dessinerait un rail vide : a signaler, jamais a bloquer.
    for m in model.get("modules") or []:
        if not m.get("id"):
            errors.append("Module \u00ab %s \u00bb: missing field `id`"
                          % m.get("name", "?"))
        if not (m.get("channels") or []):
            warnings.append(f"Module \u00ab {m.get('name', '?')} \u00bb: "
                            f"no channel")
        for chan in m.get("channels") or []:
            if not chan.get("entity") and not chan.get("power_entity"):
                errors.append(f"Module \u00ab {m.get('name', '?')} \u00bb: "
                              f"a channel has neither `entity` nor "
                              f"`power_entity`")

    # EN | Rooms: an unknown slot would silently never be rendered.
    # FR | Pieces : un tableau inconnu ne serait jamais rendu, en silence.
    slot_sets = {**DEFAULT_SLOT_SETS, **(model.get("slot_sets") or {})}
    seen_ids = set()
    for room in model.get("rooms", []) or []:
        rid = room.get("id")
        if not rid:
            errors.append("A room has no `id`")
            continue
        if rid in seen_ids:
            errors.append(f"Room id `{rid}` declared twice")
        seen_ids.add(rid)
        set_name = room.get("slot_set", "default")
        if set_name not in slot_sets:
            errors.append(f"Room `{rid}`: unknown slot set `{set_name}` "
                          f"(known: {', '.join(sorted(slot_sets))})")
        for slot_id in (room.get("slots") or {}):
            if slot_id not in SLOTS:
                errors.append(f"Room `{rid}`: unknown slot `{slot_id}` "
                              f"(known: {', '.join(SLOTS)})")
        # EN | default_slot is optional (build_rooms() falls back to the
        # EN | heaviest candidate when missing/invalid), so this is a warning,
        # EN | not an error — a bad value degrades gracefully rather than
        # EN | blocking the whole build over one room.
        # FR | default_slot est optionnel (build_rooms() se replie sur le
        # FR | candidat le plus charge si absent/invalide), donc c'est un
        # FR | avertissement, pas une erreur — une valeur invalide degrade
        # FR | proprement plutot que de bloquer tout le build pour une piece.
        default_slot = room.get("default_slot")
        if default_slot and default_slot not in SLOTS:
            warnings.append(f"Room `{rid}`: unknown default_slot `{default_slot}` "
                            f"(known: {', '.join(SLOTS)}) — falling back to the "
                            f"heaviest candidate")
        elif default_slot and set_name in slot_sets and default_slot not in slot_sets[set_name]:
            warnings.append(f"Room `{rid}`: default_slot `{default_slot}` is not "
                            f"in its own slot_set `{set_name}` — falling back to "
                            f"the heaviest candidate")

    return errors, warnings


# ----------------------------------------------------------------------------
# EN | Room and navigation composition
# FR | Composition des pieces et de la navigation
# ----------------------------------------------------------------------------
def normalise_slots(room: dict, slot_sets: dict) -> dict:
    """
    EN | Turns a room's raw slots into what the template consumes. Every slot in
    EN | the room's set is present in the output, with an explicit `state`:
    EN |   filled    — holds at least one device
    EN |   empty     — belongs to the set but holds nothing yet -> slot.empty
    EN |   filler    — empty, and carries the Visio Sapiens animation
    EN | Slots outside the set are absent entirely: the template collapses them
    EN | and lets neighbours expand.
    FR | Transforme les tableaux bruts d'une piece en ce que le template
    FR | consomme. Chaque tableau du jeu de la piece est present en sortie, avec
    FR | un `state` explicite :
    FR |   filled    — contient au moins un appareil
    FR |   empty     — appartient au jeu mais ne contient encore rien -> slot.empty
    FR |   filler    — vide, et porte l'animation Visio Sapiens
    FR | Les tableaux hors du jeu sont totalement absents : le template les
    FR | effondre et laisse les voisins s'etendre.
    """
    set_name = room.get("slot_set", "default")
    candidates = slot_sets.get(set_name, SLOTS)
    raw = room.get("slots") or {}

    out = {}
    for slot_id in SLOTS:
        if slot_id not in candidates:
            continue
        value = raw.get(slot_id)
        entities = list(value or [])
        entry = {"id": slot_id, "entities": entities,
                 "state": "filled" if entities else "empty"}

        # EN | Entities grouped by Home Assistant domain, order preserved.
        # EN | The `security` slot needs this: an alarm state, an intercom
        # EN | video feed and a camera mosaic are three different visual
        # EN | natures that cannot share one card. `switches` needs it too,
        # EN | now that it holds lights, outlets and shutters together: the
        # EN | template lists them as three separate groups, not one mixed
        # EN | pile. Classifying here rather than in the template keeps the
        # EN | template about presentation — and Jinja has no regex test, so
        # EN | doing it there would mean an awkward workaround anyway.
        # FR | Entites groupees par domaine Home Assistant, ordre preserve.
        # FR | Le tableau `security` en a besoin : un etat d'alarme, un flux
        # FR | video d'interphone et une mosaique de cameras sont trois
        # FR | natures visuelles differentes qui ne peuvent pas partager une
        # FR | seule carte. `switches` aussi, maintenant qu'il porte lumieres,
        # FR | prises et volets ensemble : le template les liste en trois
        # FR | groupes separes, pas un tas melange. Classer ici plutot que
        # FR | dans le template garde le template sur la presentation — et
        # FR | Jinja n'a pas de test regex, donc le faire la-bas imposerait un
        # FR | contournement de toute facon.
        by_domain = {}
        for ent in entry["entities"]:
            domain = str(ent).split(".", 1)[0]
            by_domain.setdefault(domain, []).append(ent)
        entry["by_domain"] = by_domain

        out[slot_id] = entry

    # EN | One filler at most, first eligible slot wins.
    # FR | Un seul remplisseur au maximum, le premier tableau eligible gagne.
    for slot_id in FILLER_PRIORITY:
        entry = out.get(slot_id)
        if entry and entry["state"] == "empty":
            entry["state"] = "filler"
            break

    return out


def resolve_default_slot(requested: str | None, rendered: dict) -> str | None:
    """
    EN | Picks the slot that gets the privileged (1fr) band: the room's
    EN | requested `default_slot` if it actually renders (see
    EN | rendered_slots()), otherwise the rendered slot with the most devices
    EN | (ties broken by SLOTS order), or None if the room renders nothing.
    FR | Choisit le tableau qui recoit la bande privilegiee (1fr) : le
    FR | `default_slot` demande par la piece s'il se rend reellement (voir
    FR | rendered_slots()), sinon le tableau rendu avec le plus d'appareils
    FR | (egalite tranchee par l'ordre de SLOTS), ou None si la piece ne rend
    FR | rien.
    """
    if requested and requested in rendered:
        return requested
    if not rendered:
        return None
    ordered = sorted(rendered.values(), key=lambda s: (-len(s["entities"]), SLOTS.index(s["id"])))
    return ordered[0]["id"]


def rendered_slots(slots: dict, slot_set: str) -> dict:
    """
    EN | The subset of a room's `slots` that actually renders a panel: every
    EN | filled slot, plus — for slot_set == 'entrance' — `switches` and
    EN | `security` even when empty, because their content is hardcoded per
    EN | the physical room (camera mosaic, intercom feed — see room.yaml.j2's
    EN | `and room.slot_set == 'entrance'`-gated branches) rather than driven
    EN | by assigned devices, so device count says nothing about whether they
    EN | should render.
    EN | Single source of truth for "does this slot get a grid area": every
    EN | function below, and room.yaml.j2's/room_mobile.yaml.j2's rendering
    EN | loop (via room.rendered_slot_ids), all consume this instead of each
    EN | re-deriving the exemption — a slot present in one but missing from
    EN | another is exactly the "grid-area that doesn't exist, panel silently
    EN | not displayed" failure the old validate_layouts() existed to catch.
    FR | Le sous-ensemble des `slots` d'une piece qui rend reellement un
    FR | panneau : tout tableau rempli, plus — pour slot_set == 'entrance' —
    FR | `switches` et `security` meme vides, car leur contenu est code en
    FR | dur pour la piece physique (mosaique de cameras, flux d'interphone —
    FR | voir les branches de room.yaml.j2 conditionnees par
    FR | `and room.slot_set == 'entrance'`) plutot que pilote par des
    FR | appareils assignes, donc le nombre d'appareils ne dit rien sur si
    FR | ils doivent se rendre.
    FR | Source unique de verite pour « ce tableau a-t-il une zone de
    FR | grille » : chaque fonction ci-dessous, et la boucle de rendu de
    FR | room.yaml.j2/room_mobile.yaml.j2 (via room.rendered_slot_ids),
    FR | consomment tous ceci plutot que de redecoder chacun l'exception —
    FR | un tableau present dans l'un mais absent d'un autre est exactement
    FR | la panne « zone de grille inexistante, panneau silencieusement non
    FR | affiche » que l'ancien validate_layouts() existait pour attraper.
    """
    exempt = slot_set == "entrance"
    return {
        sid: s for sid, s in slots.items()
        if s["state"] != "empty" or (exempt and sid in ("switches", "security"))
    }


def compute_room_layout(rendered: dict, default_slot: str | None) -> dict:
    """
    EN | Computes a room's CSS grid from what it actually renders (see
    EN | rendered_slots()). Replaces the old DEFAULT_LAYOUTS per-slot_set
    EN | presets — see docs/dashboards/Dashboard_Generator.md, "Room dashboard grid —
    EN | dynamic slot layout" for the full design this implements.
    EN | Every rendered, non-default slot ("secondary") is ordered by device
    EN | count descending (ties by SLOTS order) and split into at most two
    EN | tiers: tier A (top 2, a tall row) and tier B (next 2, a short row,
    EN | only when 3-4 secondaries are present). A lone tier member always
    EN | takes the full row — the weight split only matters between two
    EN | members sharing one. default_slot always renders last, full width,
    EN | sized 1fr so it takes whatever space is left.
    FR | Calcule la grille CSS d'une piece a partir de ce qu'elle rend
    FR | reellement (voir rendered_slots()). Remplace les anciens gabarits
    FR | DEFAULT_LAYOUTS par slot_set — voir docs/dashboards/Dashboard_Generator.md,
    FR | « Room dashboard grid — dynamic slot layout » pour la conception
    FR | complete que ceci met en oeuvre.
    FR | Chaque tableau rendu et non-defaut (« secondaire ») est ordonne par
    FR | nombre d'appareils decroissant (egalite par l'ordre de SLOTS) et
    FR | reparti sur au plus deux paliers : palier A (les 2 premiers, ligne
    FR | haute) et palier B (les 2 suivants, ligne basse, seulement quand 3-4
    FR | secondaires sont presents). Un palier a un seul membre prend
    FR | toujours toute la ligne — le partage par poids ne compte qu'a deux.
    FR | default_slot est toujours rendu en dernier, pleine largeur, en 1fr
    FR | pour prendre l'espace restant.
    """
    secondaries = sorted(
        (s for s in rendered.values() if s["id"] != default_slot),
        key=lambda s: (-len(s["entities"]), SLOTS.index(s["id"])),
    )
    tier_a, tier_b = secondaries[:2], secondaries[2:4]

    def area_row(tier: list) -> str:
        if len(tier) == 1:
            return "nav " + " ".join([tier[0]["id"]] * 5)
        total = sum(len(s["entities"]) for s in tier) or 1
        spans = [max(1, min(4, round(5 * len(s["entities"]) / total))) for s in tier]
        # EN | Force a clean 2-5 split when rounding leaves the pair short of
        # EN | (or over) the 5 columns available — happens at ties (e.g. 1/1).
        # FR | Force un partage propre a 5 colonnes quand l'arrondi laisse la
        # FR | paire en-deca (ou au-dela) des 5 colonnes disponibles — arrive
        # FR | en cas d'egalite (ex. 1/1).
        if sum(spans) != 5:
            spans[1] = max(1, min(4, 5 - spans[0]))
            spans[0] = 5 - spans[1]
        cells: list = []
        for slot, span in zip(tier, spans):
            cells += [slot["id"]] * span
        return "nav " + " ".join(cells[:5])

    rows = ["130px"]
    areas = ["nav header header header header header"]

    if tier_a:
        rows.append("260px")
        areas.append(area_row(tier_a))
    if tier_b:
        rows.append("140px")
        areas.append(area_row(tier_b))
    if default_slot:
        rows.append("1fr")
        areas.append(f"nav {default_slot} {default_slot} {default_slot} "
                      f"{default_slot} {default_slot}")

    return {"rows": " ".join(rows), "areas": areas}


def compute_mobile_order(rendered: dict, default_slot: str | None) -> list:
    """
    EN | Single-column reading order for room_mobile.yaml.j2: secondaries by
    EN | device count descending (same tie-break as compute_room_layout),
    EN | then default_slot last — mirroring its "biggest, at the bottom"
    EN | desktop position without needing 2-D tiering. Operates on
    EN | rendered_slots()'s output, so the entrance switches/security
    EN | exemption is already applied — nothing left to filter here.
    FR | Ordre de lecture mono-colonne pour room_mobile.yaml.j2 : secondaires
    FR | par nombre d'appareils decroissant (meme egalite que
    FR | compute_room_layout), puis default_slot en dernier — reprend sa
    FR | position desktop « le plus grand, en bas » sans repartition 2D.
    FR | Opere sur la sortie de rendered_slots(), donc l'exception
    FR | switches/security d'entrance est deja appliquee — rien a filtrer ici.
    """
    secondaries = sorted(
        (s for s in rendered.values() if s["id"] != default_slot),
        key=lambda s: (-len(s["entities"]), SLOTS.index(s["id"])),
    )
    order = [s["id"] for s in secondaries]
    if default_slot and default_slot in rendered:
        order.append(default_slot)
    return order


def build_rooms(model: dict, ctx_t) -> list:
    """
    EN | Expands the model's rooms into what the template needs: display name,
    EN | path, icon and normalised slots. The identifier stays in English; only
    EN | the label goes through the catalogue.
    FR | Developpe les pieces du modele en ce dont le template a besoin : nom
    FR | affiche, chemin, icone et tableaux normalises. L'identifiant reste en
    FR | anglais ; seul le libelle passe par le catalogue.
    """
    slot_sets = {**DEFAULT_SLOT_SETS, **(model.get("slot_sets") or {})}
    icons = model.get("room_icons") or {}
    rooms = []

    for room in model.get("rooms", []) or []:
        rid = room["id"]
        rtype = room.get("type", rid)
        index = room.get("index")

        # EN | Label from the catalogue, with the index appended for (n) rooms.
        # FR | Libelle depuis le catalogue, index ajoute pour les pieces (n).
        try:
            label = ctx_t(f"room.{rtype}")
        except KeyError:
            label = room.get("label") or rid
        if index:
            label = f"{label} {index}"

        # EN | url_path and the nav target must be derived from the SAME
        # EN | slug, otherwise the rail links to a dashboard that does not
        # EN | exist and the click silently does nothing.
        # FR | L'url_path et la cible de navigation doivent venir du MEME
        # FR | slug, sinon le bandeau pointe vers un dashboard inexistant et
        # FR | le clic ne fait rien, en silence.
        url_path = room.get("url_path") or f"visio-sapiens-{slug(rid)}"
        url_path_mobile = room.get("url_path_mobile") or f"{url_path}-m"

        slot_set = room.get("slot_set", "default")
        slots = normalise_slots(room, slot_sets)
        rendered = rendered_slots(slots, slot_set)
        default_slot = resolve_default_slot(room.get("default_slot"), rendered)

        rooms.append({
            "id": rid,
            "type": rtype,
            "index": index,
            "label": label,
            "name": room.get("name") or label.upper(),
            "icon": room.get("icon") or icons.get(rtype, "mdi:home-outline"),
            "slot_set": slot_set,
            "slots": slots,
            # EN | Slot ids room.yaml.j2's tablet loop renders, in SLOTS
            # EN | order — the same `rendered` set compute_room_layout() and
            # EN | compute_mobile_order() below are built from, so the loop
            # EN | can never diverge from what the grid actually has areas
            # EN | for (see rendered_slots()'s docstring).
            # FR | Ids de tableaux que la boucle tablette de room.yaml.j2
            # FR | rend, dans l'ordre de SLOTS — le meme jeu `rendered` dont
            # FR | sont batis compute_room_layout() et compute_mobile_order()
            # FR | ci-dessous, donc la boucle ne peut pas diverger de ce pour
            # FR | quoi la grille a reellement des zones (voir la docstring
            # FR | de rendered_slots()).
            "rendered_slot_ids": [s for s in SLOTS if s in rendered],
            "default_slot": default_slot,
            "layout": compute_room_layout(rendered, default_slot),
            "slot_order_mobile": compute_mobile_order(rendered, default_slot),
            # EN | Home Assistant area id, used by anything that targets an
            # EN | area (the HOME logbook, area-scoped automations). Defaults
            # EN | to the room id; override in house.yaml when the HA area is
            # EN | named differently — they drift apart easily.
            # FR | Identifiant de zone Home Assistant, utilise par tout ce qui
            # FR | cible une zone (le journal de HOME, les automatisations par
            # FR | zone). Vaut l'id de la piece par defaut ; a surcharger dans
            # FR | house.yaml quand la zone HA porte un autre nom — les deux
            # FR | divergent facilement.
            "area_id": room.get("area_id") or rid,
            "url_path": url_path,
            "url_path_mobile": url_path_mobile,
            "path": room.get("path") or f"/{url_path}/{rid}",
            "path_mobile": room.get("path_mobile") or f"/{url_path_mobile}/{rid}",
        })
    return rooms


def build_nav(model: dict, rooms: list, out_dir: Path) -> list:
    """
    EN | Composes the navigation rail: the fixed system entries, with the
    EN | declared rooms inserted between them. This is what makes the rail
    EN | dynamic — its length is always (present system entries) + the
    EN | number of rooms, and no navigation block is maintained by hand
    EN | anywhere.
    EN | A system entry whose id is in OPTIONAL_SYSTEM_NAV_IDS is included
    EN | only if `out_dir/<id>.yaml` actually exists — an on-demand
    EN | dashboard (home/core/energy) that was never created, or was
    EN | deleted, must not leave a dead tile in the rail. Every other
    EN | entry (admin) is unconditional.
    FR | Compose le bandeau de navigation : les entrees systeme fixes, avec les
    FR | pieces declarees inserees entre elles. C'est ce qui rend le bandeau
    FR | dynamique — sa longueur vaut toujours (entrees systeme presentes) +
    FR | le nombre de pieces, et aucun bloc de navigation n'est maintenu a la
    FR | main nulle part.
    FR | Une entree systeme dont l id figure dans OPTIONAL_SYSTEM_NAV_IDS
    FR | n est incluse que si `out_dir/<id>.yaml` existe reellement — un
    FR | dashboard a la demande (home/core/energy) jamais cree, ou supprime,
    FR | ne doit pas laisser une tuile morte dans le bandeau. Toute autre
    FR | entree (admin) est inconditionnelle.
    """
    nav_system = model.get("nav_system") or {}

    def present(entries):
        return [e for e in entries
                if e.get("id") not in OPTIONAL_SYSTEM_NAV_IDS
                or (out_dir / f"{e['id']}.yaml").is_file()]

    before = present(nav_system.get("before_rooms") or [])
    after = present(nav_system.get("after_rooms") or [])

    room_entries = [{
        "id": r["id"],
        "name": r["name"],
        "label": r["label"],
        "icon": r["icon"],
        "path": r["path"],
        "path_mobile": r["path_mobile"],
    } for r in rooms]

    return before + room_entries + after


# ----------------------------------------------------------------------------
# EN | Legacy helpers, unchanged behaviour
# FR | Aides historiques, comportement inchange
# ----------------------------------------------------------------------------
def flatten_rooms(rooms: list) -> list:
    """
    EN | rooms -> flat device list, keeping the room as a label.
    FR | rooms -> liste plate d'appareils, en gardant la piece comme libelle.
    """
    flat = []
    for room in rooms:
        for d in room.get("devices", []) or []:
            item = dict(d)
            item.setdefault("room", room.get("name", ""))
            flat.append(item)
    return flat


def preview_context(context: dict) -> dict:
    """
    EN | Isolates the render into a TEST dashboard. The preview has its own
    EN | url_path, hence its own Lovelace entry: it coexists with the staging
    EN | dashboard without ever overwriting it. The title is marked to avoid
    EN | any visual confusion.
    FR | Isole le rendu dans un dashboard de TEST. L'apercu a sa propre
    FR | url_path, donc sa propre entree Lovelace : il coexiste avec le
    FR | dashboard de staging sans jamais l'ecraser. Le titre est marque pour
    FR | eviter toute confusion visuelle.
    """
    ctx = deepcopy(context)
    energy = ctx.get("energy", {})
    energy["url_path"] = energy.get("url_path", "vssp-energy") + "-preview"
    energy["title"] = energy.get("title", "ENERGY") + " \u29d7 PREVIEW"
    energy["subtitle"] = "PREVIEW — not deployed"
    ctx["energy"] = energy
    return ctx


def existing_rooms_fragment(path) -> dict:
    """
    EN | The room dashboards the fragment declares RIGHT NOW, before this run
    EN | rewrites it. Only used to refuse a rewrite that would delete all of
    EN | them — see the guard in write_rooms_fragment.
    EN | An unreadable or absent file reads as "declares nothing", which is
    EN | the safe answer: it lets a first run write the fragment normally.
    FR | Les dashboards de piece que le fragment declare MAINTENANT, avant
    FR | que ce lancement ne le reecrive. Sert uniquement a refuser une
    FR | reecriture qui les supprimerait tous — voir le garde-fou dans
    FR | write_rooms_fragment.
    FR | Un fichier absent ou illisible vaut « ne declare rien », ce qui est
    FR | la reponse sure : un premier lancement ecrit le fragment normalement.
    """
    p = Path(path) if path else None
    if not p or not p.is_file():
        return {}
    try:
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError) as exc:
        print(f"[warn] {p} unreadable ({exc}) — treated as declaring nothing")
        return {}
    return ((doc.get("lovelace") or {}).get("dashboards") or {})


def write_rooms_fragment(path, rooms: list, formats: list, out_dir: Path,
                         locale: str, allow_empty: bool = False) -> dict:
    """
    EN | Writes the `lovelace.dashboards` entries for the generated room
    EN | dashboards. Without this, every room dashboard exists on disk and is
    EN | linked from the navigation rail, but Home Assistant knows none of
    EN | those URLs — clicking a room does nothing at all.
    FR | Ecrit les entrees `lovelace.dashboards` des dashboards de piece
    FR | generes. Sans cela, chaque dashboard de piece existe sur le disque et
    FR | est lie depuis le bandeau de navigation, mais Home Assistant ne
    FR | connait aucune de ces URL — cliquer sur une piece ne fait rien.
    #
    EN | Three deliberate choices:
    EN |   - the key is prefixed `visio-sapiens-`, because vssp_apply_config.py
    EN |     only merges keys matching VSSP_PREFIX and silently skips the rest;
    EN |   - `filename` is relative to /config, like every other entry;
    EN |   - the title is written already translated. This fragment is
    EN |     generated in a known locale, so it carries no __T: marker and
    EN |     needs no rendering step.
    FR | Trois choix volontaires :
    FR |   - la cle est prefixee `visio-sapiens-`, car vssp_apply_config.py ne
    FR |     fusionne que les cles correspondant a VSSP_PREFIX et ignore le
    FR |     reste en silence ;
    FR |   - `filename` est relatif a /config, comme toutes les autres entrees ;
    FR |   - le titre est ecrit deja traduit. Ce fragment est genere dans une
    FR |     langue connue, il ne porte donc aucun marqueur __T: et n'a besoin
    FR |     d'aucune etape de rendu.
    """
    dashboards = {}
    for room in rooms:
        for target_format in formats:
            mobile = target_format == "mobile"
            key = room["url_path_mobile"] if mobile else room["url_path"]
            name = f"{room['id']}_mobile.yaml" if mobile else f"{room['id']}.yaml"
            # EN | Only declare a dashboard whose file actually exists.
            # FR | Ne declarer qu'un dashboard dont le fichier existe vraiment.
            if not (out_dir / name).is_file():
                continue
            dashboards[key] = {
                "mode": "yaml",
                "title": room["label"],
                "icon": room["icon"],
                # EN | Hidden from the Home Assistant sidebar: navigation goes
                # EN | through the Visio Sapiens rail, and 15 extra entries
                # EN | would drown the native sidebar.
                # FR | Masque de la barre laterale Home Assistant : la
                # FR | navigation passe par le bandeau Visio Sapiens, et 15
                # FR | entrees de plus noieraient la sidebar native.
                "show_in_sidebar": False,
                "filename": f"dashboards/views/{name}",
            }

    header = (
        "########################################################################\n"
        "# Visio Sapiens — Room dashboards fragment\n"
        "#\n"
        "# *** GENERATED FILE — DO NOT EDIT BY HAND ***\n"
        "# *** FICHIER GENERE — NE PAS EDITER A LA MAIN ***\n"
        "#\n"
        "# EN | Written by generate_dashboards.py. Merged into\n"
        "# EN | configuration.yaml by vssp_apply_config.py, alongside the\n"
        "# EN | static config-fragment.yaml which declares the system\n"
        "# EN | dashboards.\n"
        "# FR | Ecrit par generate_dashboards.py. Fusionne dans\n"
        "# FR | configuration.yaml par vssp_apply_config.py, a cote du\n"
        "# FR | config-fragment.yaml statique qui declare les dashboards\n"
        "# FR | systeme.\n"
        "#\n"
        f"# EN | Locale: {locale} — regenerate after changing the language.\n"
        f"# FR | Langue : {locale} — regenerer apres un changement de langue.\n"
        "#\n"
        "# EN | Removing a room from house.yaml removes it here, but NOT from\n"
        "# EN | configuration.yaml: the patcher never deletes on its own. Use\n"
        "# EN | vssp_apply_config.py --prune-dashboards to clear stale entries.\n"
        "# FR | Retirer une piece de house.yaml la retire d'ici, mais PAS de\n"
        "# FR | configuration.yaml : le patcher ne supprime jamais de lui-meme.\n"
        "# FR | Utiliser vssp_apply_config.py --prune-dashboards pour nettoyer\n"
        "# FR | les entrees obsoletes.\n"
        "########################################################################\n\n"
    )

    # EN | GUARD — never let one run delete EVERY room declaration.
    # EN | This fragment is what tells Home Assistant that the room
    # EN | dashboards exist at all; emptying it unlinks every room in the
    # EN | interface at once, and nothing on screen explains why. It happened:
    # EN | six ADMIN buttons passed --rooms-fragment WITHOUT --rooms, so they
    # EN | rebuilt this file from a rooms list that was empty, and one click
    # EN | on REGENERATE HOME took every room dashboard out of the console.
    # EN | Going from "some rooms" to "no rooms" is almost always a missing
    # EN | source (no --rooms, an empty model, a half-finished deploy) rather
    # EN | than an intent, so it now needs to be stated: --allow-empty-rooms.
    # EN | Everything else still writes normally — including removing SOME
    # EN | rooms, which is an ordinary edit.
    # FR | GARDE-FOU — ne jamais laisser un lancement supprimer TOUTES les
    # FR | declarations de pieces.
    # FR | Ce fragment est ce qui apprend a Home Assistant que les dashboards
    # FR | de piece existent ; le vider delie toutes les pieces de l'interface
    # FR | d'un coup, et rien a l'ecran n'explique pourquoi. C'est arrive :
    # FR | six boutons de l'ADMIN passaient --rooms-fragment SANS --rooms, ils
    # FR | reconstruisaient donc ce fichier depuis une liste de pieces vide,
    # FR | et un clic sur REGENERER HOME a sorti tous les dashboards de piece
    # FR | de la console.
    # FR | Passer de « quelques pieces » a « aucune piece » vient presque
    # FR | toujours d'une source manquante (pas de --rooms, un modele vide, un
    # FR | deploiement a moitie fait) plutot que d'une intention : cela doit
    # FR | desormais etre declare, avec --allow-empty-rooms. Tout le reste
    # FR | s'ecrit normalement — y compris retirer CERTAINES pieces, qui est
    # FR | une modification ordinaire.
    if not dashboards and not allow_empty:
        already = existing_rooms_fragment(path)
        if already:
            print(f"[REFUSED] {path}: this run declares no room dashboard, "
                  f"but the file currently declares {len(already)} "
                  f"({', '.join(sorted(already))}).")
            print("          Refusing to unlink every room. Likely cause: no "
                  "--rooms given, or the model's rooms: list is empty.")
            print("          Re-run with --rooms <house_rooms.yaml>, or pass "
                  "--allow-empty-rooms if the rooms really are all gone.")
            return already

    body = yaml.safe_dump({"lovelace": {"dashboards": dashboards}},
                          sort_keys=False, allow_unicode=True, default_flow_style=False)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(header + body, encoding="utf-8")
    return dashboards


def static_dashboards(static_fragment) -> set:
    """
    EN | Dashboard keys declared by the static fragment (the system ones).
    FR | Cles de dashboards declarees par le fragment statique (les systeme).
    """
    path = Path(static_fragment) if static_fragment else None
    if not path or not path.is_file():
        return set()
    try:
        loader = yaml.SafeLoader
        loader.add_multi_constructor("!", lambda l, s_, n: None)
        doc = yaml.load(path.read_text(encoding="utf-8"), Loader=loader) or {}
    except (yaml.YAMLError, OSError) as exc:
        print(f"[warn] {path} unreadable: {exc}")
        return set()
    return set(((doc.get("lovelace") or {}).get("dashboards") or {}))


def check_fragment_collisions(room_keys: set, static_keys: set) -> list:
    """
    EN | A key declared by BOTH fragments is merged twice, and the rooms
    EN | fragment wins because it is applied second. The static declaration is
    EN | silently replaced — a hand-written dashboard can be swapped for a
    EN | generated one with no warning anywhere. Same failure shape as the
    EN | grid-area and navigation checks: a reference that quietly resolves to
    EN | something other than what was intended.
    FR | Une cle declaree par les DEUX fragments est fusionnee deux fois, et
    FR | le fragment des pieces gagne car il est applique en second. La
    FR | declaration statique est remplacee en silence — un dashboard ecrit a
    FR | la main peut etre echange contre un dashboard genere sans le moindre
    FR | avertissement. Meme forme de defaillance que les controles des
    FR | grid-area et de la navigation : une reference qui resout
    FR | discretement vers autre chose que ce qui etait voulu.
    """
    return sorted(room_keys & static_keys)


def check_declared_files(static_fragment, out_dir: Path, repo_root: Path) -> list:
    """
    EN | Every dashboard the static fragment declares must have a file. A
    EN | declaration pointing at a file nothing generates gives Home Assistant
    EN | a dashboard it cannot open: the sidebar entry exists, the URL exists,
    EN | and clicking it produces an error page. Nothing in the pipeline
    EN | notices, because the declaration is valid YAML and the file is simply
    EN | absent.
    EN | This is the third check of the same family — grid areas, navigation
    EN | targets, dashboard keys — and it closes the last gap: a reference
    EN | that resolves to no file at all.
    FR | Chaque dashboard declare par le fragment statique doit avoir un
    FR | fichier. Une declaration pointant vers un fichier que rien ne genere
    FR | donne a Home Assistant un dashboard qu'il ne peut pas ouvrir :
    FR | l'entree existe, l'URL existe, et cliquer produit une page d'erreur.
    FR | Rien dans le pipeline ne le remarque, car la declaration est du YAML
    FR | valide et le fichier est simplement absent.
    FR | C'est le troisieme controle de la meme famille — zones de grille,
    FR | cibles de navigation, cles de dashboards — et il ferme le dernier
    FR | trou : une reference qui ne resout vers aucun fichier.
    """
    path = Path(static_fragment) if static_fragment else None
    if not path or not path.is_file():
        return []
    try:
        loader = yaml.SafeLoader
        loader.add_multi_constructor("!", lambda l, s_, n: None)
        doc = yaml.load(path.read_text(encoding="utf-8"), Loader=loader) or {}
    except (yaml.YAMLError, OSError):
        return []

    missing = []
    for key, entry in (((doc.get("lovelace") or {}).get("dashboards") or {})).items():
        filename = (entry or {}).get("filename")
        if not filename:
            continue
        # EN | `filename` is relative to /config; out_dir is where this run
        # EN | writes. Compare on the basename, which is what actually has to
        # EN | exist next to the other generated dashboards.
        # FR | `filename` est relatif a /config ; out_dir est l'endroit ou ce
        # FR | run ecrit. On compare sur le nom de fichier, qui est ce qui doit
        # FR | reellement exister a cote des autres dashboards generes.
        name = Path(filename).name
        # EN | Preview dashboards are produced ONLY by --preview, on demand.
        # EN | Their declaration is permanent so the url_path stays reserved
        # EN | and the preview can appear the moment it is generated, but the
        # EN | file is absent the rest of the time — by design, not by
        # EN | accident. Reporting it would print the same warning on every
        # EN | single build about something nobody intends to fix, and a
        # EN | warning that always fires is a warning that stops being read.
        # FR | Les dashboards d apercu ne sont produits QUE par --preview, a la
        # FR | demande. Leur declaration est permanente pour que l url_path
        # FR | reste reserve et que l apercu apparaisse des sa generation, mais
        # FR | le fichier est absent le reste du temps — par conception, pas
        # FR | par accident. Le signaler afficherait le meme avertissement a
        # FR | chaque build sur quelque chose que personne ne compte corriger,
        # FR | et un avertissement qui se declenche toujours est un
        # FR | avertissement qu on cesse de lire.
        if "_preview" in name:
            continue
        if not (out_dir / name).is_file():
            missing.append((key, filename))
    return missing


def check_nav_targets(nav: list, declared: set, static_fragment,
                      formats: list) -> list:
    """
    EN | Every navigation target must correspond to a declared dashboard.
    EN | A rail entry pointing at an undeclared url_path is a link that does
    EN | nothing when clicked — no error, no log, the page simply never opens.
    EN | This is the navigation counterpart of the grid-area check: both catch
    EN | a reference that resolves to nothing.
    FR | Chaque cible de navigation doit correspondre a un dashboard declare.
    FR | Une entree de bandeau pointant vers un url_path non declare est un
    FR | lien qui ne fait rien au clic — aucune erreur, aucun log, la page ne
    FR | s'ouvre simplement jamais. C'est le pendant navigation du controle
    FR | des grid-area : tous deux attrapent une reference qui ne resout rien.
    """
    known = set(declared)
    path = Path(static_fragment) if static_fragment else None
    if path and path.is_file():
        try:
            loader = yaml.SafeLoader
            loader.add_multi_constructor("!", lambda l, s_, n: None)
            doc = yaml.load(path.read_text(encoding="utf-8"), Loader=loader) or {}
            known |= set(((doc.get("lovelace") or {}).get("dashboards") or {}))
        except (yaml.YAMLError, OSError) as exc:
            print(f"[warn] {path} unreadable, nav check partial: {exc}")

    wanted = []
    for item in nav:
        wanted.append(item.get("path"))
        if "mobile" in formats:
            wanted.append(item.get("path_mobile"))

    missing = []
    for target in wanted:
        if not target:
            continue
        url = str(target).lstrip("/").split("/", 1)[0]
        if url and url not in known:
            missing.append(url)

    return sorted(set(missing))


def render_theme(model: dict, env: Environment, template_name: str,
                  out_path: Path, design_status_path, dry_run: bool,
                  status: dict) -> bool:
    """
    EN | Renders model["design"] (design_system.yaml) into the Home Assistant
    EN | theme file, with the same guarantees as a dashboard render: YAML
    EN | validated before writing, so a broken template never overwrites a
    EN | working theme. Returns False on a fatal error (the caller writes the
    EN | status and exits 1), mirroring the dashboard job loop below.
    EN | Also writes design_status_path (design_system_status.json): the flat
    EN | token values the THEME editor reads on load, via the same FIELDS
    EN | table vssp_theme_apply.py validates a submission against — so the
    EN | editor can never show a token under a name APPLY would reject.
    FR | Rend model["design"] (design_system.yaml) dans le fichier de theme
    FR | Home Assistant, avec les memes garanties qu'un rendu de dashboard :
    FR | YAML valide avant ecriture, pour qu'un template casse n'ecrase jamais
    FR | un theme fonctionnel. Renvoie False en cas d'erreur fatale (l'appelant
    FR | ecrit le statut et sort en 1), comme la boucle des dashboards plus bas.
    FR | Ecrit aussi design_status_path (design_system_status.json) : les
    FR | valeurs plates de tokens que l'editeur THEME lit au chargement, via
    FR | la meme table FIELDS que vssp_theme_apply.py utilise pour valider une
    FR | soumission — l'editeur ne peut donc jamais afficher un token sous un
    FR | nom qu'APPLY rejetterait.
    """
    try:
        template = env.get_template(template_name)
    except TemplateNotFound:
        msg = f"{template_name} not found — theme not generated"
        print(f"[skip] {msg}")
        status["skipped"].append(msg)
        return True

    rendered = template.render(**model)

    try:
        doc = yaml.load(rendered, Loader=HaLoader)
    except yaml.YAMLError as exc:
        msg = f"{out_path.name}: invalid YAML after render — not written"
        print(f"[ERR] {msg}\n{exc}")
        status["errors"].append(f"{msg} — {exc}")
        return False

    if not isinstance(doc, dict) or not doc:
        msg = f"{out_path.name}: rendered theme is empty — not written"
        print(f"[ERR] {msg}")
        status["errors"].append(msg)
        return False

    if dry_run:
        print(f"[dry-run] {out_path} — render valid "
              f"({len(rendered.splitlines())} lines) — NOT written")
    else:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
        print(f"[OK] {out_path} generated")

        if design_status_path:
            flat = vssp_design_fields.flatten(model.get("design") or {})
            write_status(design_status_path, flat)
            print(f"[OK] {design_status_path} written "
                  f"({len(flat)} token(s), for the THEME editor)")

    status["generated"].append({
        "file": str(out_path), "id": "theme", "lines": len(rendered.splitlines())})
    return True


def write_status(path, status: dict) -> None:
    """
    EN | JSON report read by the admin console (served under /local/vssp/...).
    FR | Rapport JSON lu par la console admin (servi en /local/vssp/...).
    """
    if not path:
        return
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(status, indent=2, ensure_ascii=False),
                     encoding="utf-8")
    except OSError as exc:
        print(f"[warn] status file not written: {exc}")


# ----------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model",
                    default="home-assistant/dashboards/model/house.yaml")
    ap.add_argument("--rooms",
                    default="home-assistant/dashboards/model/house_rooms.yaml",
                    help="Rooms fragment produced by the discovery wizard; if "
                         "present, its rooms: key replaces the model's")
    ap.add_argument("--devices",
                    default="home-assistant/dashboards/model/energy_devices.yaml",
                    help="Flat device list for the ENERGY dashboard "
                         "(maintained by vssp_energy_sync.py). Takes "
                         "precedence over flattening the rooms.")
    ap.add_argument("--design-model",
                    default="home-assistant/dashboards/model/design_system.yaml",
                    help="Design tokens (theme screen of the ADMIN console). "
                         "If present, rendered by --theme-template into "
                         "--themes-out/visio_sapiens.yaml (id 'theme' for --only)")
    ap.add_argument("--theme-template", default="theme.yaml.j2")
    ap.add_argument("--themes-out", default="themes")
    ap.add_argument("--design-status-file", default=None,
                    help="Flat token values for the THEME editor's initial "
                         "load (see vssp_design_fields.flatten), e.g. "
                         "/config/www/vssp/design_system_status.json. Same "
                         "opt-in-only default as --status-file: unset locally "
                         "so a local --only theme run never writes outside "
                         "--themes-out.")
    ap.add_argument("--templates",
                    default="home-assistant/dashboards/templates_j2")
    ap.add_argument("--out", default="home-assistant/dashboards/views")
    ap.add_argument("--locales-dir",
                    default="home-assistant/dashboards/locales")
    ap.add_argument("--locale", default=None,
                    help="Interface language. Overrides house.locale. English "
                         "is the reference: any key missing from another "
                         "catalogue falls back to it.")
    ap.add_argument("--calendar-entity", default=None,
                    help="calendar.* entity shown in every dashboard header. "
                         "Overrides house.calendar_entity; set by the ADMIN "
                         "console's Google Calendar screen. An empty or "
                         "'unknown' value falls back to the model.")
    ap.add_argument("--format", default=None,
                    choices=["tablet", "mobile", "both"],
                    help="Target layout. Overrides house.format.")
    ap.add_argument("--preview", action="store_true",
                    help="Generates an isolated TEST dashboard "
                         "(energy_preview.yaml / url vssp-energy-preview) "
                         "without ever touching the staging dashboards")
    ap.add_argument("--only", default=None,
                    help="Generate only these dashboards (comma-separated "
                         "ids, e.g. energy,home, or a room id). Default: all.")
    ap.add_argument("--if-missing", action="store_true",
                    help="Generate only when the output file does not exist "
                         "yet. An existing dashboard is NEVER overwritten "
                         "(CREATE button of the ADMIN console).")
    ap.add_argument("--protect-existing", default=DEFAULT_PROTECTED_DASHBOARD_IDS,
                    help="Comma-separated dashboard ids treated as --if-missing "
                         "regardless of the --if-missing flag (default: "
                         f"'{DEFAULT_PROTECTED_DASHBOARD_IDS}'). Pass an empty "
                         "string to allow overwriting them for this run — "
                         "used by the explicit REGENERATE HOME button.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Validates the model and the render, writes nothing")
    ap.add_argument("--static-fragment",
                    default="home-assistant/config-fragment.yaml",
                    help="Static fragment declaring the system dashboards. "
                         "Read only, to check that every navigation target "
                         "resolves.")
    ap.add_argument("--rooms-fragment",
                    default="home-assistant/config-fragment-rooms.yaml",
                    help="Where to write the lovelace.dashboards entries of "
                         "the generated room dashboards. Pass an empty string "
                         "to skip.")
    # EN | Opt out of the guard above: says the rooms really are all gone
    # EN | and the fragment should be emptied. Only the room wizard's own
    # EN | "delete everything" path has any business passing this.
    # FR | Renonce au garde-fou ci-dessus : affirme que les pieces ont bien
    # FR | toutes disparu et que le fragment doit etre vide. Seul le parcours
    # FR | « tout supprimer » de l'assistant pieces a une raison de le passer.
    ap.add_argument("--allow-empty-rooms", action="store_true",
                    help="Allow the rooms fragment to be emptied. Without it, "
                         "a run that declares no room refuses to delete "
                         "existing room declarations.")
    ap.add_argument("--status-file", default=None,
                    help="Writes a JSON report (readable by the console at "
                         "/local/vssp/preview_status.json)")
    args = ap.parse_args()

    status = {"ok": False, "preview": args.preview, "dry_run": args.dry_run,
              "generated": [], "skipped": [], "errors": [], "warnings": [],
              "timestamp": datetime.now().isoformat(timespec="seconds")}

    model = yaml.safe_load(Path(args.model).read_text(encoding="utf-8"))

    # --- EN | Language / FR | Langue -------------------------------------
    # EN | Precedence: --locale (console selector) > house.locale > 'en'.
    # EN | Passing it as an argument means the ADMIN console never has to
    # EN | rewrite house.yaml just to switch language.
    # FR | Priorite : --locale (selecteur de la console) > house.locale > 'en'.
    # FR | Le passer en argument evite que la console ADMIN doive reecrire
    # FR | house.yaml juste pour changer de langue.
    house = model.get("house") or {}
    locale = args.locale or house.get("locale") or vssp_i18n.BASE_LOCALE
    try:
        i18n = vssp_i18n.jinja_context(locale, Path(args.locales_dir))
    except FileNotFoundError as exc:
        print(f"[ERR] locale '{locale}': {exc}")
        status["errors"].append(str(exc))
        write_status(args.status_file, status)
        return 1
    print(f"[i] locale: {locale} ({i18n['locale_tag']})")

    # --- EN | Format / FR | Format ---------------------------------------
    fmt = args.format or house.get("format") or "tablet"
    formats = ["tablet", "mobile"] if fmt == "both" else [fmt]
    print(f"[i] format: {', '.join(formats)}")

    # --- EN | Header calendar / FR | Calendrier du bandeau ---------------
    # EN | Same precedence trick as --locale: the ADMIN console's Google
    # EN | Calendar screen stores the chosen entity in
    # EN | input_text.vssp_google_calendar_entity, and the shell_command
    # EN | passes it here — so switching calendars never means rewriting
    # EN | house.yaml. house.calendar_entity remains the default for a
    # EN | command-line run, and the header partial keeps its own fallback
    # EN | for a model that predates this key.
    # EN | An empty/unknown/unavailable value (an input_text that was never
    # EN | filled renders as "unknown") must NOT win over the model — that is
    # EN | what the guard below is for.
    # FR | Meme mecanique de priorite que --locale : l'ecran Google Calendar
    # FR | de la console ADMIN memorise l'entite choisie dans
    # FR | input_text.vssp_google_calendar_entity, et le shell_command la
    # FR | passe ici — changer de calendrier n'impose donc jamais de reecrire
    # FR | house.yaml. house.calendar_entity reste le defaut pour un lancement
    # FR | en ligne de commande, et le partial d'en-tete garde son propre
    # FR | repli pour un modele anterieur a cette cle.
    # FR | Une valeur vide/unknown/unavailable (un input_text jamais rempli
    # FR | vaut « unknown ») ne doit PAS l'emporter sur le modele — c'est le
    # FR | role du garde-fou ci-dessous.
    cal_arg = (args.calendar_entity or "").strip()
    if cal_arg in ("", "unknown", "unavailable", "None"):
        cal_arg = ""
    calendar_entity = cal_arg or house.get("calendar_entity") or ""
    if calendar_entity:
        house["calendar_entity"] = calendar_entity
        print(f"[i] header calendar: {calendar_entity}")

    # --- EN | Rooms fragment from the discovery wizard (steps 2-4) -------
    # --- FR | Fragment rooms du Discovery Wizard (etapes 2-4) ------------
    todo_count = 0
    rooms_path = Path(args.rooms)
    if rooms_path.exists():
        text = rooms_path.read_text(encoding="utf-8")
        fragment = yaml.safe_load(text)
        todo_count = text.count("# TODO ")
        if fragment and fragment.get("rooms"):
            model["rooms"] = fragment["rooms"]
            print(f"[i] rooms: taken from {rooms_path} "
                  f"({len(fragment['rooms'])} room(s))")

    # --- EN | FLAT device list for the ENERGY dashboard ------------------
    # --- FR | Liste PLATE des appareils du dashboard ENERGY --------------
    # EN | ENERGY depends on no room: it shows every measured device in the
    # EN | home. Two possible sources, in this order:
    # EN |   1. model/energy_devices.yaml — maintained by vssp_energy_sync.py
    # EN |   2. otherwise, flattening the model's / wizard's rooms
    # FR | ENERGY ne depend d'aucune piece : il affiche tous les appareils
    # FR | mesures de la maison. Deux sources possibles, dans cet ordre :
    # FR |   1. model/energy_devices.yaml — maintenu par vssp_energy_sync.py
    # FR |   2. sinon, aplatissement des rooms du modele / du wizard
    devices_path = Path(args.devices)
    if devices_path.exists():
        dev_doc = yaml.safe_load(devices_path.read_text(encoding="utf-8")) or {}
        model["energy_devices"] = dev_doc.get("devices", [])
        if dev_doc.get("circuits") is not None:
            model["circuits"] = dev_doc["circuits"]
        if dev_doc.get("modules") is not None:
            model["modules"] = dev_doc["modules"]
        # EN | The rating is typed once, on the circuit. The virtual panel
        # EN | reads it from there instead of asking for it a second time:
        # EN | one entity, one rating, whichever side of the panel shows it.
        # FR | Le calibre se saisit une fois, sur le circuit. Le tableau
        # FR | virtuel le lit la plutot que de le redemander : une entite, un
        # FR | calibre, quel que soit le cote du panneau qui l'affiche.
        amps = {c.get("entity"): c.get("amp")
                for c in model.get("circuits") or [] if c.get("amp")}
        # EN | Picture and master switch are DERIVED, never stored: the
        # EN | picture from the model name (so N identical boxes share one
        # EN | file), the master switch from the channels that can actually be
        # EN | switched — covers and metering channels are not toggled.
        # FR | Image et interrupteur maitre sont DERIVES, jamais stockes :
        # FR | l'image depuis le nom de modele (pour que N boitiers
        # FR | identiques partagent un fichier), l'interrupteur maitre depuis
        # FR | les voies reellement commandables — un volet ou une voie de
        # FR | mesure ne se bascule pas.
        pictures = model.get("module_images") or []
        base = (model.get("module_image_base") or "").rstrip("/")

        # EN | Two sources, in this order: the table the scan filled in
        # EN | when it discovered the box — exact, model by model — then the
        # EN | curated rules of house.yaml, which cover the shipped pictures
        # EN | and any instance with no internet access.
        # FR | Deux sources, dans cet ordre : la table remplie par le scan au
        # FR | moment ou il a decouvert le boitier — exacte, modele par
        # FR | modele — puis les regles curatees de house.yaml, qui couvrent
        # FR | les visuels livres et toute instance sans acces internet.
        fetched = dev_doc.get("images") or {}

        def picture_for(model_name: str) -> str:
            if fetched.get(model_name):
                return f"{base}/{fetched[model_name]}"
            for rule in pictures:
                if re.search(rule.get("match", ""), model_name or "",
                             re.IGNORECASE):
                    return f"{base}/{rule.get('image', '')}"
            return ""

        # EN | The switch list shows the same product pictures: a row names
        # EN | its model already, and the picture is what makes it recognised
        # EN | at a glance rather than read.
        # FR | La liste des interrupteurs montre les memes visuels : une ligne
        # FR | nomme deja son modele, et l'image est ce qui le fait
        # FR | reconnaitre d'un coup d'oeil au lieu de le lire.
        for cir in model.get("circuits") or []:
            cir["image"] = picture_for(cir.get("model") or "")
        for mod in model.get("modules") or []:
            for chan in mod.get("channels") or []:
                if not chan.get("amp") and amps.get(chan.get("entity")):
                    chan["amp"] = amps[chan["entity"]]
            mod["switches"] = [c["entity"] for c in mod.get("channels") or []
                               if (c.get("entity") or "").startswith("switch.")]
            mod["image"] = picture_for(mod.get("model") or "")
            # EN | `panel` says whether the module is mounted in the
            # EN | enclosure, and the rail renders on it. A model written
            # EN | before that key existed has no opinion, and the honest
            # EN | default is "not on the rail" — the scan decides on its next
            # EN | run. Without this default the template would hit an
            # EN | undefined attribute and the whole render would fail.
            # FR | `panel` dit si le module est monte dans le coffret, et le
            # FR | rail se rend la-dessus. Un modele ecrit avant l'existence
            # FR | de cette cle n'a pas d'avis, et le defaut honnete est
            # FR | « pas sur le rail » — le scan tranchera a son prochain
            # FR | passage. Sans ce defaut le template tomberait sur un
            # FR | attribut indefini et tout le rendu echouerait.
            mod.setdefault("panel", False)
        print(f"[i] ENERGY devices: {devices_path} "
              f"({len(model['energy_devices'])} device(s), "
              f"{len(model.get('circuits', []))} circuit(s), "
              f"{len(model.get('modules', []))} module(s))")
    else:
        model["energy_devices"] = flatten_rooms(model.get("rooms", []))

    # --- EN | Design tokens for the THEME screen -------------------------
    # --- FR | Tokens de design pour l'ecran THEME -------------------------
    design_path = Path(args.design_model)
    if design_path.exists():
        design_doc = yaml.safe_load(design_path.read_text(encoding="utf-8")) or {}
        model["design"] = design_doc.get("design", {})
    else:
        model["design"] = {}

    errors, warns = validate_model(model)
    status["warnings"] = warns
    if warns:
        print(f"[warn] {len(warns)} point(s) to review:")
        for w in warns[:5]:
            print(f"  - {w}")
        if len(warns) > 5:
            print(f"  ... and {len(warns) - 5} more")
    if errors:
        print("[ERR] invalid model — generation cancelled:")
        for e in errors:
            print(f"  - {e}")
        status["errors"] = errors
        write_status(args.status_file, status)
        return 1

    # --- EN | Rooms and dynamic navigation rail --------------------------
    # --- FR | Pieces et bandeau de navigation dynamique ------------------
    # EN | out_dir computed here (ahead of its later mkdir/write use below)
    # EN | because build_nav() needs it to check which on-demand system
    # EN | dashboards actually exist on disk right now.
    # FR | out_dir calcule ici (avant son mkdir/ecriture plus bas) car
    # FR | build_nav() en a besoin pour verifier quels dashboards systeme a
    # FR | la demande existent reellement sur le disque en ce moment.
    out_dir = Path(args.out)
    rooms = build_rooms(model, i18n["t"])
    model["rooms_rendered"] = rooms
    model["nav"] = build_nav(model, rooms, out_dir)
    model["slots"] = SLOTS
    # EN | Cache-busting query param for the ADMIN console's wizard iframes
    # EN | (assign.html, vssp_rooms_floors.html, vssp_theme_editor.html — see
    # EN | admin.yaml.j2). Those were all served at a literal `?v=0`: once a
    # EN | browser cached that exact URL, it kept the iframe's *first-ever*
    # EN | content forever, no matter how many times the underlying HTML file
    # EN | changed on a later deploy — confirmed live: a THEME editor fix
    # EN | shipped, deployed, and confirmed running on the pod by commit SHA,
    # EN | yet the iframe kept showing the pre-fix page. A fresh value here on
    # EN | every generation (any REGENERATE, ROOMS/ASSIGN apply, or CI deploy)
    # EN | forces the browser to fetch the iframe content again.
    # FR | Parametre anti-cache pour les iframes wizard de la console ADMIN
    # FR | (assign.html, vssp_rooms_floors.html, vssp_theme_editor.html — voir
    # FR | admin.yaml.j2). Elles etaient toutes servies avec un `?v=0` litteral :
    # FR | une fois cette URL exacte mise en cache par le navigateur, l'iframe
    # FR | gardait son contenu de la toute premiere fois pour toujours, peu
    # FR | importe combien de fois le fichier HTML sous-jacent changeait a un
    # FR | deploiement suivant — constate en direct : un correctif de l'editeur
    # FR | THEME livre, deploye et confirme actif sur le pod par son SHA de
    # FR | commit, alors que l'iframe continuait d'afficher la page d'avant le
    # FR | correctif. Une valeur fraiche ici a chaque generation (n'importe
    # FR | quel REGENERER, application ROOMS/ASSIGN, ou deploiement CI) force
    # FR | le navigateur a re-telecharger le contenu de l'iframe.
    model["build_stamp"] = datetime.now().strftime("%Y%m%d%H%M%S")
    print(f"[i] navigation: {len(model['nav'])} entries "
          f"({len(model['nav']) - len(rooms)} system + {len(rooms)} room(s))")

    env = Environment(
        loader=FileSystemLoader(args.templates),
        # EN | missing variable = error, never a silent hole
        # FR | variable manquante = erreur, jamais de trou silencieux
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    # EN | Escapes a translated string for safe embedding inside a JS
    # EN | single-quoted literal in a button-card [[[ ]]] template. Without
    # EN | it, any locale value containing an apostrophe (e.g. fr "À l'arrêt")
    # EN | breaks the generated JS and button-card raises ButtonCardJSTemplateError.
    # FR | Echappe une chaine traduite pour une insertion sure dans un
    # FR | litteral JS entre guillemets simples au sein d'un template
    # FR | button-card [[[ ]]]. Sans cela, toute valeur de locale contenant
    # FR | une apostrophe (ex. fr "À l'arrêt") casse le JS genere et
    # FR | button-card leve ButtonCardJSTemplateError.
    env.filters["js"] = lambda s: str(s).replace("\\", "\\\\").replace("'", "\\'")

    out_dir.mkdir(parents=True, exist_ok=True)
    n_dev = len(model.get("energy_devices", []))

    # --- EN | Build the job list: system dashboards + one per room -------
    # --- FR | Constitution des jobs : dashboards systeme + un par piece --
    jobs = list(SYSTEM_DASHBOARDS)
    for room in rooms:
        jobs.append((room["id"], ROOM_TEMPLATE, f"{room['id']}.yaml",
                     {"active_nav": room["id"], "room": room,
                      "room_id": room["id"]}))

    protected_ids = {s.strip() for s in args.protect_existing.split(",") if s.strip()}

    wanted = ({s.strip() for s in args.only.split(",") if s.strip()}
              if args.only else None)
    if wanted:
        # EN | 'theme' is a recognised --only id but not a Lovelace dashboard
        # EN | job (see render_theme() below) — exclude it from the
        # EN | "unknown dashboard" check instead of adding a fake job for it.
        # FR | 'theme' est un id --only reconnu mais pas un job de dashboard
        # FR | Lovelace (voir render_theme() plus bas) — on l'exclut du
        # FR | controle "dashboard inconnu" plutot que d'ajouter un faux job.
        unknown = (wanted - {"theme"}) - {j[0] for j in jobs}
        if unknown:
            msg = f"unknown dashboard(s): {', '.join(sorted(unknown))}"
            print(f"[ERR] {msg}")
            status["errors"].append(msg)
            write_status(args.status_file, status)
            return 1

    # --- EN | THEME — independent of the Lovelace dashboard jobs ---------
    # --- FR | THEME — independant des jobs de dashboards Lovelace ---------
    # EN | Opt-in only (--only theme / --only theme,energy,...), never part
    # EN | of a plain full run: the CI build already copies themes/ into
    # EN | dist/themes BEFORE calling this script without --only (see
    # EN | .gitlab-ci.yml), so a default-on render here would silently modify
    # EN | the source tree's themes/visio_sapiens.yaml after that copy ran,
    # EN | with no effect on the artefact actually shipped — confusing, for
    # EN | no benefit. The ADMIN console's THEME screen always passes
    # EN | --only theme explicitly.
    # FR | Seulement a la demande (--only theme / --only theme,energy,...),
    # FR | jamais lors d'un run complet ordinaire : le build CI copie deja
    # FR | themes/ vers dist/themes AVANT d'appeler ce script sans --only
    # FR | (voir .gitlab-ci.yml), donc un rendu actif par defaut ici
    # FR | modifierait en silence le themes/visio_sapiens.yaml de l'arbre
    # FR | source apres cette copie, sans effet sur le livrable reellement
    # FR | expedie — source de confusion, pour aucun benefice. L'ecran THEME
    # FR | de la console ADMIN passe toujours --only theme explicitement.
    if wanted is not None and "theme" in wanted and not args.preview:
        theme_out = Path(args.themes_out) / "visio_sapiens.yaml"
        if not render_theme(model, env, args.theme_template, theme_out,
                            args.design_status_file,
                            args.dry_run, status):
            write_status(args.status_file, status)
            return 1

    for dash_id, tpl_name, out_name, extra in jobs:
        if wanted and dash_id not in wanted:
            continue

        for target_format in formats:
            # EN | Silent by design: see TABLET_ONLY. This is not a missing
            # EN | template, it is a dashboard that has no mobile form.
            # FR | Silencieux par conception : voir TABLET_ONLY. Ce n est pas
            # FR | un template manquant, c est un dashboard qui n a pas de
            # FR | forme mobile.
            if target_format == "mobile" and dash_id in TABLET_ONLY:
                continue
            context = {**model, **i18n, **extra, "format": target_format}
            name = out_name
            if target_format == "mobile":
                name = name.replace(".yaml", "_mobile.yaml")

            if args.preview:
                context = preview_context(context)
                name = name.replace(".yaml", "_preview.yaml")

            # EN | --if-missing: never overwrite an existing dashboard. The
            # EN | check uses the FINAL output name (including the _preview
            # EN | suffix), so a preview does not block creating the real one.
            # EN | --protect-existing (home by default) gets this same
            # EN | protection from EVERY caller that does not opt out — the
            # EN | routine regeneration fired after every ROOMS sync / ASSIGN
            # EN | save has no reason to know this dashboard is meant for
            # EN | manual editing, so the script enforces it in their place.
            # EN | Exempted in --preview: a preview file is disposable by
            # EN | design and never what the user actually sees as home.yaml.
            # FR | --if-missing : ne jamais ecraser un dashboard existant. Le
            # FR | controle porte sur le nom de sortie FINAL (suffixe _preview
            # FR | compris), pour qu'un apercu ne bloque pas la creation du vrai.
            # FR | --protect-existing (home par defaut) recoit cette meme
            # FR | protection de la part de TOUT appelant qui ne s en
            # FR | exempte pas — la regeneration routiniere declenchee apres
            # FR | chaque sync ROOMS / enregistrement ASSIGN n a aucune
            # FR | raison de savoir que ce dashboard est destine a une
            # FR | edition manuelle, donc le script l impose a sa place.
            # FR | Exempte en --preview : un fichier d apercu est jetable par
            # FR | conception et n est jamais ce que l utilisateur voit
            # FR | reellement comme home.yaml.
            force_if_missing = dash_id in protected_ids and not args.preview
            if (args.if_missing or force_if_missing) and (out_dir / name).exists():
                print(f"= {out_dir / name} already exists — left intact "
                      f"(--if-missing)")
                status["skipped"].append(str(out_dir / name))
                continue

            # EN | A template that does not exist yet is not an error: the
            # EN | project ships them one at a time. Reported, then skipped.
            # FR | Un template pas encore ecrit n'est pas une erreur : le projet
            # FR | les livre un par un. Signale, puis saute.
            wanted_tpl = template_for(tpl_name, target_format)
            try:
                template = env.get_template(wanted_tpl)
            except TemplateNotFound:
                # EN | No fallback to the tablet template. Rendering a tablet
                # EN | layout into a *_mobile.yaml file would produce a
                # EN | dashboard that loads, looks broken on a phone, and
                # EN | reports nothing. Skipping says what is missing.
                # FR | Aucun repli sur le template tablette. Rendre une
                # FR | disposition tablette dans un fichier *_mobile.yaml
                # FR | produirait un dashboard qui se charge, s'affiche mal
                # FR | sur telephone, et ne signale rien. Sauter dit ce qui
                # FR | manque.
                print(f"[skip] {wanted_tpl} not found — {dash_id} "
                      f"({target_format}) not generated")
                status["skipped"].append(
                    f"{dash_id}/{target_format} ({wanted_tpl} missing)")
                continue

            rendered = template.render(**context)

            # EN | A __T: marker surviving the render means a template used the
            # EN | placeholder syntax instead of calling t(). It would reach the
            # EN | screen verbatim.
            # FR | Un marqueur __T: survivant au rendu signifie qu'un template a
            # FR | utilise la syntaxe de substitution au lieu d'appeler t(). Il
            # FR | arriverait tel quel a l'ecran.
            leftover = sorted(set(T_PLACEHOLDER.findall(rendered)))
            if leftover:
                msg = (f"{name}: {len(leftover)} unresolved placeholder(s) "
                       f"after render — {', '.join(leftover[:5])}")
                print(f"[ERR] {msg}")
                print("      Templates must call t('key'), not __T:key__.")
                status["errors"].append(msg)
                write_status(args.status_file, status)
                return 1

            # EN | YAML validation BEFORE writing
            # FR | Validation YAML AVANT ecriture
            try:
                doc = yaml.load(rendered, Loader=HaLoader)
            except yaml.YAMLError as exc:
                msg = f"{name}: invalid YAML after render — not written"
                print(f"[ERR] {msg}\n{exc}")
                status["errors"].append(f"{msg} — {exc}")
                write_status(args.status_file, status)
                return 1

            # EN | STRUCTURAL CHECK — parsing is not enough. A whitespace
            # EN | mishap in a template can glue a key onto the previous line
            # EN | and turn it into a comment: the result still parses, and the
            # EN | key is simply gone. That is exactly how twenty dashboards
            # EN | lost their `title` without a single error. A Lovelace
            # EN | dashboard is a mapping with `title` and `views`; anything
            # EN | else means the render was damaged.
            # FR | CONTROLE STRUCTUREL — parser ne suffit pas. Un accident
            # FR | d'espacement dans un template peut coller une cle sur la
            # FR | ligne precedente et la transformer en commentaire : le
            # FR | resultat parse toujours, et la cle a simplement disparu.
            # FR | C'est exactement ainsi que vingt dashboards ont perdu leur
            # FR | `title` sans la moindre erreur. Un dashboard Lovelace est
            # FR | un mapping avec `title` et `views` ; toute autre forme
            # FR | signifie que le rendu est abime.
            required = [k for k in ("title", "views") if not isinstance(doc, dict)
                        or k not in doc]
            if required:
                msg = (f"{name}: rendered YAML is missing "
                       f"{', '.join(required)} — not written")
                print(f"[ERR] {msg}")
                print("      A key was probably absorbed into a comment. Check "
                      "for {%- or -%} whitespace stripping in the template.")
                status["errors"].append(msg)
                write_status(args.status_file, status)
                return 1

            target = out_dir / name
            if args.dry_run:
                print(f"[dry-run] {target} — render valid "
                      f"({len(rendered.splitlines())} lines) — NOT written")
            else:
                target.write_text(rendered, encoding="utf-8")
                print(f"[OK] {target} generated ({target_format}, {locale})")

            status["generated"].append({
                "file": str(target),
                "id": dash_id,
                "format": target_format,
                "locale": locale,
                "lines": len(rendered.splitlines()),
            })

    # --- EN | Declare the generated room dashboards to Home Assistant ----
    # --- FR | Declarer les dashboards de piece generes a Home Assistant --
    # EN | Skipped in preview and dry-run: neither should touch what
    # EN | production actually serves.
    # FR | Saute en apercu et en dry-run : ni l'un ni l'autre ne doit toucher
    # FR | a ce que la production sert reellement.
    fragment_entries = {}
    if args.rooms_fragment and not args.preview and not args.dry_run:
        fragment_entries = write_rooms_fragment(
            args.rooms_fragment, rooms, formats, out_dir, locale,
            allow_empty=args.allow_empty_rooms)
        print(f"[OK] {args.rooms_fragment}: "
              f"{len(fragment_entries)} room dashboard(s) declared")
        if rooms and not fragment_entries:
            print("[warn] no room dashboard declared — room.yaml.j2 is "
                  "probably missing, so no room file was generated")

        clashes = check_fragment_collisions(
            set(fragment_entries), static_dashboards(args.static_fragment))
        if clashes:
            print(f"[ERR] {len(clashes)} dashboard key(s) declared by BOTH the "
                  f"static fragment and the generated one:")
            for key in clashes:
                print(f"         - {key}")
            print("       The generated declaration would silently replace the "
                  "static one.")
            print("       Either remove the entry from config-fragment.yaml, "
                  "or rename the room id in house.yaml.")
            status["errors"].append(
                f"fragment key collision: {', '.join(clashes)}")
            write_status(args.status_file, status)
            return 1

        no_file = check_declared_files(args.static_fragment, out_dir,
                                       Path(args.model).parent)
        if no_file:
            print(f"[warn] {len(no_file)} declared dashboard(s) have no file — "
                  f"opening them in Home Assistant will show an error page:")
            for key, filename in no_file:
                print(f"         - {key} -> {filename}")
            print("       Either write the missing template, or remove the "
                  "entry from config-fragment.yaml.")
            status["warnings"].append(
                f"declared but not generated: {', '.join(k for k, _ in no_file)}")
        else:
            print("[OK] every declared dashboard has a generated file")

        orphans = check_nav_targets(model["nav"], set(fragment_entries),
                                    args.static_fragment, formats)
        if orphans:
            print(f"[warn] {len(orphans)} navigation target(s) declared in no "
                  f"fragment — clicking them will do nothing:")
            for url in orphans:
                print(f"         - {url}")
            print("       Declare them in config-fragment.yaml, or remove the "
                  "entry from nav_system in house.yaml.")
            status["warnings"].append(
                f"navigation targets not declared: {', '.join(orphans)}")
        else:
            print("[OK] every navigation target resolves to a declared dashboard")

    status["ok"] = True
    status["rooms_fragment"] = sorted(fragment_entries)
    status["locale"] = locale
    status["formats"] = formats
    status["rooms"] = len(rooms)
    status["nav_entries"] = len(model["nav"])
    status["energy_devices"] = n_dev
    status["devices"] = n_dev
    status["circuits"] = len(model.get("circuits", []))
    status["modules"] = len(model.get("modules", []))
    status["channels"] = sum(len(m.get("channels") or [])
                             for m in model.get("modules") or [])
    status["todo_devices"] = todo_count
    if args.preview:
        print("\n-> Preview available at /vssp-energy-preview/energy "
              "— your staging dashboards were not modified.")
    write_status(args.status_file, status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
