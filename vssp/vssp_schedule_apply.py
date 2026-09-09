#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================================
# Visio Sapiens — vssp_schedule_apply.py
#
# EN | Keeps the schedule store: the list of rules the SWITCHES popup writes
# EN | and the Home Assistant engine reads. One file, one writer, one reader.
# EN |
# EN | WHY THIS SCRIPT EXISTS AT ALL, rather than the popup creating real
# EN | Home Assistant automations: a real automation has to be written through
# EN | the authenticated API, and this popup opens from a room dashboard on a
# EN | wall tablet. Making someone paste a long-lived token to say "turn the
# EN | lamp off at ten" is the wrong trade. So the popup posts to a webhook
# EN | (no token, LAN only) and this script owns the file.
# EN |
# EN | THE ONE IDEA WORTH KNOWING: every rule is reduced HERE to absolute
# EN | moments — a wall-clock time plus weekdays, or a dated timestamp. The
# EN | engine on the Home Assistant side then does nothing but compare
# EN | strings against the clock. No date arithmetic in Jinja, no timers to
# EN | lose across a restart, no state that can drift out of step with the
# EN | file. A restart mid-pause is a non-event: the resume moment was
# EN | computed when the rule was saved and is still sitting there.
# EN |
# EN | Operations (payload arrives base64 encoded on the command line):
# EN |   {"op": "save",   "rule": {...}}       create or replace
# EN |   {"op": "delete", "id": "sch_xxx"}     remove
# EN |   {"op": "toggle", "id": "sch_xxx", "enabled": bool}
# EN |   {"op": "prune"}                       drop what is long past
# EN |
# FR | Tient le magasin de planifications : la liste de regles qu'ecrit le
# FR | popup du tableau INTERRUPTEURS et que lit le moteur Home Assistant.
# FR | Un fichier, un ecrivain, un lecteur.
# FR |
# FR | POURQUOI CE SCRIPT EXISTE, plutot qu'un popup qui creerait de vraies
# FR | automatisations Home Assistant : une vraie automatisation s'ecrit par
# FR | l'API authentifiee, et ce popup s'ouvre depuis le dashboard d'une piece
# FR | sur une tablette murale. Demander a quelqu'un de coller un jeton longue
# FR | duree pour dire « eteins la lampe a vingt-deux heures » est le mauvais
# FR | compromis. Le popup poste donc vers un webhook (sans jeton, LAN
# FR | seulement) et ce script est proprietaire du fichier.
# FR |
# FR | LA SEULE IDEE QUI COMPTE : chaque regle est reduite ICI a des moments
# FR | absolus — une heure murale plus des jours de semaine, ou un horodatage
# FR | date. Le moteur cote Home Assistant ne fait alors que comparer des
# FR | chaines a l'horloge. Aucun calcul de date en Jinja, aucune minuterie a
# FR | perdre au redemarrage, aucun etat qui puisse se desaccorder du fichier.
# FR | Un redemarrage au milieu d'une pause est un non-evenement : le moment
# FR | de reprise a ete calcule a l'enregistrement et il est toujours la.
# FR |
# FR | Operations (payload en base64 sur la ligne de commande) :
# FR |   {"op": "save",   "rule": {...}}       creer ou remplacer
# FR |   {"op": "delete", "id": "sch_xxx"}     supprimer
# FR |   {"op": "toggle", "id": "sch_xxx", "enabled": bool}
# FR |   {"op": "prune"}                       jeter ce qui est loin derriere
#
# EN | Zero dependencies: standard library only, same rule as every other
# EN | vssp_*.py that runs on the pod.
# FR | Zero dependance : bibliotheque standard uniquement, meme regle que tout
# FR | autre vssp_*.py tournant sur le pod.
#
# EN | NO DEFAULT PATHS. --store and --status are required. A default pointing
# EN | at a repository path resolves to nothing on the pod, fails quietly, and
# EN | costs an afternoon to find.
# FR | AUCUN CHEMIN PAR DEFAUT. --store et --status sont obligatoires. Un
# FR | defaut pointant vers un chemin du depot ne resout rien sur le pod,
# FR | echoue en silence, et coute un apres-midi a trouver.
# ============================================================================
import argparse
import base64
import binascii
import datetime as _dt
import json
import os
import re
import secrets
import sys
from pathlib import Path

BASE_LOCALE = "en"
SUPPORTED_LOCALES = ("en", "fr")

KINDS = ("recurring", "once", "timer")
ACTIONS = ("on", "off", "pause")

# EN | Domains the SWITCHES slot can hold. homeassistant.turn_on/turn_off
# EN | covers all three — on a cover they mean open and close — which is why
# EN | the engine needs no per-domain branch.
# FR | Domaines que peut contenir le tableau INTERRUPTEURS.
# FR | homeassistant.turn_on/turn_off les couvre tous les trois — sur un volet
# FR | ils signifient ouvrir et fermer — d'ou l'absence de branche par domaine
# FR | dans le moteur.
ALLOWED_DOMAINS = ("light", "switch", "cover", "fan", "media_player",
                   "input_boolean", "climate", "humidifier", "siren")

ENTITY_RE = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")
TIME_RE = re.compile(r"^([01][0-9]|2[0-3]):([0-5][0-9])$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

MAX_RULES = 200
KEEP_EXPIRED_HOURS = 24

# ── EN | Messages / FR | Messages ────────────────────────────────────────
# EN | Same contract as vssp_google_setup.py: the status file carries the
# EN | machine form (message_key + message_vars) for the page, which
# EN | translates on its own, AND the sentence rendered in --locale for
# EN | anything that cannot translate.
# FR | Meme contrat que vssp_google_setup.py : le fichier d'etat porte la
# FR | forme machine (message_key + message_vars) pour la page, qui traduit
# FR | elle-meme, ET la phrase rendue dans --locale pour ce qui ne sait pas
# FR | traduire.
MESSAGES = {
    "saved": {
        "en": "Rule saved.",
        "fr": "Règle enregistrée.",
    },
    "deleted": {
        "en": "Rule deleted.",
        "fr": "Règle supprimée.",
    },
    "toggled": {
        "en": "Rule updated.",
        "fr": "Règle mise à jour.",
    },
    "pruned": {
        "en": "{n} expired rule(s) removed.",
        "fr": "{n} règle(s) expirée(s) supprimée(s).",
    },
    "bad_payload": {
        "en": "The payload could not be read.",
        "fr": "Le contenu reçu n'a pas pu être lu.",
    },
    "bad_op": {
        "en": "Unknown operation: {op}.",
        "fr": "Opération inconnue : {op}.",
    },
    "not_found": {
        "en": "No rule with that id.",
        "fr": "Aucune règle avec cet identifiant.",
    },
    "invalid": {
        "en": "Rule refused: {why}",
        "fr": "Règle refusée : {why}",
    },
    "too_many": {
        "en": "Refused: the store already holds {n} rules.",
        "fr": "Refusé : le magasin contient déjà {n} règles.",
    },
}

# EN | Validation reasons are messages too — they are the sentence a person
# EN | reads under the form, not a developer log line.
# FR | Les motifs de refus sont aussi des messages — ce sont la phrase que
# FR | lit une personne sous le formulaire, pas une ligne de log.
WHY = {
    "entity": {"en": "no valid entity", "fr": "aucune entité valide"},
    "domain": {"en": "this kind of device cannot be scheduled",
               "fr": "ce type d'appareil ne peut pas être planifié"},
    "kind": {"en": "unknown schedule type", "fr": "type de planification inconnu"},
    "action": {"en": "unknown action", "fr": "action inconnue"},
    "time": {"en": "the time must read HH:MM",
             "fr": "l'heure doit s'écrire HH:MM"},
    "days": {"en": "pick at least one day", "fr": "choisissez au moins un jour"},
    "date": {"en": "the date must read YYYY-MM-DD",
             "fr": "la date doit s'écrire AAAA-MM-JJ"},
    "past": {"en": "that moment is already behind us",
             "fr": "ce moment est déjà derrière nous"},
    "minutes": {"en": "the countdown must be between 1 minute and 7 days",
                "fr": "le compte à rebours doit tenir entre 1 minute et 7 jours"},
    "duration": {"en": "the pause must be between 1 minute and 24 hours",
                 "fr": "la pause doit tenir entre 1 minute et 24 heures"},
}


def _pick(table: dict, key: str, locale: str, **fields) -> str:
    entry = table.get(key, {})
    text = entry.get(locale) or entry.get(BASE_LOCALE) or key
    try:
        return text.format(**fields)
    except (KeyError, IndexError):
        return text


def say(key: str, locale: str, **fields) -> dict:
    return {"message_key": key,
            "message_vars": fields,
            "message": _pick(MESSAGES, key, locale, **fields)}


def why(key: str, locale: str) -> str:
    return _pick(WHY, key, locale)


# ── EN | Store / FR | Magasin ────────────────────────────────────────────
def load_store(path: Path) -> dict:
    """EN | A missing or corrupt store is an EMPTY store, never a crash. This
    EN | file sits under /config/www and is served to the popup; the day it is
    EN | half-written or hand-edited, the popup must still open.
    FR | Un magasin absent ou corrompu est un magasin VIDE, jamais un plantage.
    FR | Ce fichier vit sous /config/www et est servi au popup ; le jour ou il
    FR | est a moitie ecrit ou edite a la main, le popup doit quand meme
    FR | s'ouvrir."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"rules": []}
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        return {"rules": []}
    return data


def save_store(path: Path, rules: list) -> None:
    """EN | Write to a neighbour then rename. The popup polls this file and the
    EN | command_line sensor cats it; a reader landing between two writes must
    EN | never see half a document. rename() on the same filesystem is atomic.
    FR | Ecrire a cote puis renommer. Le popup interroge ce fichier et le
    FR | capteur command_line le cat ; un lecteur qui tombe entre deux
    FR | ecritures ne doit jamais voir un demi-document. rename() sur le meme
    FR | systeme de fichiers est atomique."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "rules": rules,
        "count": len(rules),
        "updated": _dt.datetime.now().isoformat(timespec="seconds"),
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    os.replace(tmp, path)


def write_status(path: Path, payload: dict) -> None:
    payload["generated"] = _dt.datetime.now().isoformat(timespec="seconds")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        os.replace(tmp, path)
    except OSError as exc:
        print(f"[warn] status file not written: {exc}")


# ── EN | Rule normalisation / FR | Normalisation des regles ──────────────
def last_moment(rule: dict) -> _dt.datetime | None:
    """EN | The instant after which a dated rule has nothing left to do —
    EN | its resume for a pause, its fire otherwise. Recurring rules have no
    EN | such instant and return None: they never expire.
    FR | L'instant apres lequel une regle datee n'a plus rien a faire — sa
    FR | reprise pour une pause, son declenchement sinon. Les regles
    FR | recurrentes n'ont pas cet instant et renvoient None : elles
    FR | n'expirent jamais."""
    if rule.get("kind") == "recurring":
        return None
    stamp = rule.get("resume_at") or rule.get("fire_at")
    if not stamp:
        return None
    try:
        return _dt.datetime.fromisoformat(stamp)
    except ValueError:
        return None


def normalise(raw: dict, locale: str, now: _dt.datetime) -> tuple:
    """EN | Turn what the form sent into a rule the engine can execute by
    EN | string comparison alone. Returns (rule, None) or (None, reason).
    FR | Transformer ce qu'a envoye le formulaire en une regle que le moteur
    FR | peut executer par simple comparaison de chaines. Renvoie
    FR | (regle, None) ou (None, motif)."""
    entity = str(raw.get("entity_id") or "").strip()
    if not ENTITY_RE.match(entity):
        return None, why("entity", locale)
    if entity.split(".", 1)[0] not in ALLOWED_DOMAINS:
        return None, why("domain", locale)

    kind = str(raw.get("kind") or "").strip()
    if kind not in KINDS:
        return None, why("kind", locale)

    action = str(raw.get("action") or "").strip()
    if action not in ACTIONS:
        return None, why("action", locale)

    rule = {
        "id": str(raw.get("id") or "").strip() or "sch_" + secrets.token_hex(4),
        "entity_id": entity,
        "kind": kind,
        "action": action,
        "enabled": bool(raw.get("enabled", True)),
    }

    # EN | The pause duration is what separates the off from the on that
    # EN | follows it. Bounded at a day: past that, "pause" is a word for
    # EN | something else and the user wants two rules.
    # FR | La duree de pause est ce qui separe l'extinction du rallumage qui
    # FR | la suit. Bornee a une journee : au-dela, « pause » designe autre
    # FR | chose et l'utilisateur veut deux regles.
    duration = 0
    if action == "pause":
        try:
            duration = int(raw.get("duration"))
        except (TypeError, ValueError):
            return None, why("duration", locale)
        if not 1 <= duration <= 1440:
            return None, why("duration", locale)
        rule["duration"] = duration

    if kind == "recurring":
        hhmm = str(raw.get("time") or "").strip()
        if not TIME_RE.match(hhmm):
            return None, why("time", locale)
        try:
            days = sorted({int(d) for d in (raw.get("days") or [])})
        except (TypeError, ValueError):
            return None, why("days", locale)
        if not days or any(d < 0 or d > 6 for d in days):
            return None, why("days", locale)

        rule["fire_time"] = hhmm
        rule["fire_days"] = days

        if action == "pause":
            # EN | Midnight rollover, and the whole reason this is computed
            # EN | here rather than in a template. A pause starting 23:50 for
            # EN | 30 minutes resumes at 00:20 the NEXT day, so the resume
            # EN | weekdays are the start weekdays shifted by one. Get this
            # EN | wrong and a device stays off until someone notices.
            # FR | Passage de minuit, et toute la raison pour laquelle ceci se
            # FR | calcule ici et non dans un template. Une pause commencee a
            # FR | 23h50 pour 30 minutes reprend a 00h20 le jour SUIVANT, donc
            # FR | les jours de reprise sont les jours de depart decales d'un.
            # FR | Se tromper ici, c'est un appareil qui reste eteint jusqu'a
            # FR | ce que quelqu'un s'en apercoive.
            h, m = (int(x) for x in hhmm.split(":"))
            total = h * 60 + m + duration
            rule["resume_time"] = "%02d:%02d" % ((total // 60) % 24, total % 60)
            shift = total // (24 * 60)
            rule["resume_days"] = sorted({(d + shift) % 7 for d in days})

    else:
        if kind == "once":
            date = str(raw.get("date") or "").strip()
            hhmm = str(raw.get("time") or "").strip()
            if not DATE_RE.match(date):
                return None, why("date", locale)
            if not TIME_RE.match(hhmm):
                return None, why("time", locale)
            try:
                when = _dt.datetime.fromisoformat(date + "T" + hhmm)
            except ValueError:
                return None, why("date", locale)
        else:  # timer
            try:
                minutes = int(raw.get("minutes"))
            except (TypeError, ValueError):
                return None, why("minutes", locale)
            if not 1 <= minutes <= 7 * 24 * 60:
                return None, why("minutes", locale)
            rule["minutes"] = minutes
            when = now + _dt.timedelta(minutes=minutes)

        # EN | Truncated to the minute because that is the engine's
        # EN | resolution: it wakes once a minute and compares to the minute.
        # EN | Storing seconds would store a promise nothing can keep.
        # FR | Tronque a la minute parce que c'est la resolution du moteur :
        # FR | il se reveille une fois par minute et compare a la minute. Y
        # FR | stocker des secondes reviendrait a stocker une promesse que
        # FR | rien ne peut tenir.
        when = when.replace(second=0, microsecond=0)
        if when <= now.replace(second=0, microsecond=0):
            return None, why("past", locale)
        rule["fire_at"] = when.strftime("%Y-%m-%dT%H:%M")
        if action == "pause":
            resume = when + _dt.timedelta(minutes=duration)
            rule["resume_at"] = resume.strftime("%Y-%m-%dT%H:%M")

    rule["created"] = now.isoformat(timespec="seconds")
    return rule, None


def prune(rules: list, now: _dt.datetime) -> tuple:
    """EN | Drop dated rules whose last moment is well behind us. Well, not
    EN | just, because a rule that fired five minutes ago is the one the user
    EN | is looking for when they reopen the popup to check it ran. It stays
    EN | visible for a day, then goes.
    FR | Jeter les regles datees dont le dernier moment est loin derriere.
    FR | Loin, et pas seulement derriere : une regle declenchee il y a cinq
    FR | minutes est justement celle que l'utilisateur cherche en rouvrant le
    FR | popup pour verifier qu'elle est passee. Elle reste visible un jour,
    FR | puis s'en va."""
    cutoff = now - _dt.timedelta(hours=KEEP_EXPIRED_HOURS)
    kept = []
    dropped = 0
    for rule in rules:
        end = last_moment(rule)
        if end is not None and end < cutoff:
            dropped += 1
            continue
        kept.append(rule)
    return kept, dropped


# ── EN | Operations / FR | Operations ────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Maintains the Visio Sapiens schedule store")
    ap.add_argument("--store", required=True,
                    help="Path of schedules.json (under /config/www/vssp)")
    ap.add_argument("--status", required=True,
                    help="Path of the status file the popup polls")
    ap.add_argument("--json-b64", default="",
                    help="Base64 of the JSON command; empty means prune")
    ap.add_argument("--locale", default=BASE_LOCALE,
                    choices=SUPPORTED_LOCALES,
                    help="Language of the rendered sentence")
    args = ap.parse_args()

    locale = args.locale
    store_path = Path(args.store)
    status_path = Path(args.status)
    now = _dt.datetime.now()

    # EN | Base64 because a rule carries no shell-safe guarantee and this
    # EN | argument crosses a shell_command template. Same reasoning, and the
    # EN | same encoding, as vssp_assign_apply.py.
    # FR | Base64 parce qu'une regle n'offre aucune garantie de surete shell et
    # FR | que cet argument traverse un template de shell_command. Meme
    # FR | raisonnement, et meme encodage, que vssp_assign_apply.py.
    if args.json_b64:
        try:
            payload = json.loads(
                base64.b64decode(args.json_b64).decode("utf-8"))
        except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
            print(f"[ERR] payload unreadable: {exc}")
            write_status(status_path, dict(ok=False, **say("bad_payload", locale)))
            return 1
    else:
        payload = {"op": "prune"}

    op = str(payload.get("op") or "").strip()
    store = load_store(store_path)
    rules = [r for r in store["rules"] if isinstance(r, dict)]

    if op == "save":
        rule, reason = normalise(payload.get("rule") or {}, locale, now)
        if reason:
            print(f"[ERR] rule refused: {reason}")
            write_status(status_path,
                         dict(ok=False, **say("invalid", locale, why=reason)))
            return 1
        others = [r for r in rules if r.get("id") != rule["id"]]
        if len(others) >= MAX_RULES:
            print(f"[ERR] store full ({len(others)} rules)")
            write_status(status_path,
                         dict(ok=False, **say("too_many", locale, n=len(others))))
            return 1
        rules = others + [rule]
        rules, _ = prune(rules, now)
        save_store(store_path, rules)
        print(f"[OK] rule {rule['id']} saved ({rule['kind']}/{rule['action']} "
              f"on {rule['entity_id']}) — {len(rules)} rule(s) in store")
        write_status(status_path,
                     dict(ok=True, rule_id=rule["id"], count=len(rules),
                          **say("saved", locale)))
        return 0

    if op == "delete":
        target = str(payload.get("id") or "").strip()
        kept = [r for r in rules if r.get("id") != target]
        if len(kept) == len(rules):
            print(f"[ERR] no rule with id {target}")
            write_status(status_path, dict(ok=False, **say("not_found", locale)))
            return 1
        kept, _ = prune(kept, now)
        save_store(store_path, kept)
        print(f"[OK] rule {target} deleted — {len(kept)} rule(s) in store")
        write_status(status_path,
                     dict(ok=True, count=len(kept), **say("deleted", locale)))
        return 0

    if op == "toggle":
        target = str(payload.get("id") or "").strip()
        found = False
        for rule in rules:
            if rule.get("id") == target:
                rule["enabled"] = bool(payload.get("enabled", True))
                found = True
        if not found:
            print(f"[ERR] no rule with id {target}")
            write_status(status_path, dict(ok=False, **say("not_found", locale)))
            return 1
        rules, _ = prune(rules, now)
        save_store(store_path, rules)
        print(f"[OK] rule {target} toggled")
        write_status(status_path,
                     dict(ok=True, count=len(rules), **say("toggled", locale)))
        return 0

    if op == "prune":
        rules, dropped = prune(rules, now)
        save_store(store_path, rules)
        print(f"[OK] {dropped} expired rule(s) removed — "
              f"{len(rules)} rule(s) in store")
        write_status(status_path,
                     dict(ok=True, count=len(rules),
                          **say("pruned", locale, n=dropped)))
        return 0

    print(f"[ERR] unknown operation: {op!r}")
    write_status(status_path, dict(ok=False, **say("bad_op", locale, op=op)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
