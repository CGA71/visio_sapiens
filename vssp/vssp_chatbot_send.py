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

"""Visio Sapiens — envoi d'un message au chatbot IA (Gemini/Claude/ChatGPT/Custom).

Appele par shell_command.vssp_chatbot_send (packages/vssp_chatbot.yaml),
lui-meme declenche par le webhook vssp_chatbot_send que l'iframe de chat
(www/vssp/wizard/vssp_chatbot.html) soumet a chaque envoi de message.

Ce que fait ce script a chaque appel :
  1. decode le message (et l'historique recent) depuis le base64 recu ;
  2. lit la cle API du fournisseur dans son fichier protege
     (/config/vssp/.<provider>_key, ecrit par
     shell_command.vssp_write_<provider>_key) ;
  3. lit le modele a utiliser (et, pour "custom", l'URL du point d'acces
     et le prompt systeme) via l'API REST Home Assistant — PAS en argument
     de ligne de commande : ce sont des champs texte libre tapes par
     l'utilisateur, et shell_command.vssp_chatbot_send passe par un vrai
     shell (asyncio.create_subprocess_shell), donc un guillemet ou un
     `$(...)` dans un prompt systeme ne doit jamais atteindre cette ligne
     de commande ;
  4. appelle l'API reelle du fournisseur (stdlib urllib uniquement — ce
     depot n'utilise pas `requests`, voir vssp_energy_sync.py) ;
  5. ecrit systematiquement un JSON de statut (succes OU echec) : c'est ce
     fichier que l'iframe interroge en boucle apres avoir envoye un
     message, donc un abandon silencieux le laisserait attendre pour rien.

HYPOTHESE POUR LE FOURNISSEUR "custom" : l'URL configuree doit repondre a
un contrat compatible OpenAI (POST {"model", "messages":[...]} ->
{"choices":[{"message":{"content": "..."}}]}), le contrat le plus courant
chez les serveurs auto-heberges (Ollama, LM Studio, text-generation-webui
en mode API OpenAI...). Un serveur qui parle un protocole different n'est
pas pris en charge sans adapter build_custom_request()/parse_custom_response()
ci-dessous.

CHEMIN INTEGRATION (--agent) : quand le fournisseur a son integration Home
Assistant (Anthropic, Google Gemini, OpenAI, Ollama), l'automatisation
appelle elle-meme conversation.process et ce script ne fait que classer la
reponse (--answer-b64) dans le meme fichier de statut, avec le
conversation_id que la page renverra au message suivant. Tout ce qui suit
(cles, API des fournisseurs) n'est alors pas utilise.

Usage :
    python3 vssp_chatbot_send.py --provider claude --message-b64 "..." \
        --status-file /config/www/vssp/chatbot_status.json
    python3 vssp_chatbot_send.py --provider claude --message-b64 "..." \
        --agent conversation.claude_conversation --answer-b64 "..."
    python3 vssp_chatbot_send.py --provider gemini --message-b64 "..." --dry-run
"""
from __future__ import annotations

import argparse
import base64
import binascii
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

KEY_FILES = {
    "gemini": "/config/vssp/.gemini_key",
    "claude": "/config/vssp/.claude_key",
    "chatgpt": "/config/vssp/.chatgpt_key",
    "custom": "/config/vssp/.custom_key",
}

DEFAULT_MODELS = {
    "gemini": "gemini-2.0-flash",
    "claude": "claude-sonnet-4-5",
    "chatgpt": "gpt-4o-mini",
}

MAX_TOKENS = 1024
TIMEOUT_SECONDS = 30


class ChatbotError(Exception):
    """Erreur attendue (config manquante, reponse inattendue...) — jamais
    une trace Python brute, toujours un message ecrit dans le statut."""


# ── Home Assistant — lecture de la configuration ─────────────────────
def ha_get_state(url: str, token: str, entity_id: str) -> str:
    """Lit l'etat courant d'une entite via l'API REST HA.

    Utilise pour le modele et (pour "custom") l'URL/le prompt systeme :
    des champs texte libre qui ne doivent jamais transiter par la ligne
    de commande d'un shell_command — voir la note en tete de fichier.
    """
    req = urllib.request.Request(
        f"{url.rstrip('/')}/api/states/{entity_id}",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.load(resp)
    state = (data.get("state") or "").strip()
    return "" if state in ("unknown", "unavailable") else state


# ── Construction des requetes, une par fournisseur ────────────────────
def _history_as_pairs(history: list) -> list[dict]:
    """Normalise l'historique recu : liste de {"role": "user"|"assistant", "content": str}."""
    out = []
    for turn in history or []:
        role = turn.get("role")
        content = turn.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content:
            out.append({"role": role, "content": content})
    return out


def build_gemini_request(model: str, api_key: str, message: str,
                          history: list) -> urllib.request.Request:
    # EN | Gemini uses "model" (not "assistant") for the bot's own turns.
    # FR | Gemini utilise "model" (pas "assistant") pour les tours du bot.
    contents = [
        {"role": ("model" if t["role"] == "assistant" else "user"),
         "parts": [{"text": t["content"]}]}
        for t in _history_as_pairs(history)
    ]
    contents.append({"role": "user", "parts": [{"text": message}]})
    body = json.dumps({"contents": contents}).encode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    return urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "X-goog-api-key": api_key},
    )


def parse_gemini_response(raw: dict) -> str:
    return raw["candidates"][0]["content"]["parts"][0]["text"]


def build_claude_request(model: str, api_key: str, message: str,
                          history: list) -> urllib.request.Request:
    messages = _history_as_pairs(history) + [{"role": "user", "content": message}]
    body = json.dumps({
        "model": model, "max_tokens": MAX_TOKENS, "messages": messages,
    }).encode("utf-8")
    return urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body, method="POST",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )


def parse_claude_response(raw: dict) -> str:
    return raw["content"][0]["text"]


def build_chatgpt_request(model: str, api_key: str, message: str,
                           history: list) -> urllib.request.Request:
    messages = _history_as_pairs(history) + [{"role": "user", "content": message}]
    body = json.dumps({"model": model, "messages": messages}).encode("utf-8")
    return urllib.request.Request(
        "https://api.openai.com/v1/chat/completions", data=body, method="POST",
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
    )


def parse_chatgpt_response(raw: dict) -> str:
    return raw["choices"][0]["message"]["content"]


def build_custom_request(endpoint: str, model: str, system_prompt: str,
                          api_key: str, message: str,
                          history: list) -> urllib.request.Request:
    # EN | OpenAI-compatible shape — see the module docstring's assumption.
    # FR | Forme compatible OpenAI — voir l'hypothese du docstring de module.
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages += _history_as_pairs(history) + [{"role": "user", "content": message}]
    body = json.dumps({"model": model or "default", "messages": messages}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return urllib.request.Request(endpoint, data=body, method="POST", headers=headers)


def parse_custom_response(raw: dict) -> str:
    return raw["choices"][0]["message"]["content"]


BUILDERS = {
    "gemini": build_gemini_request,
    "claude": build_claude_request,
    "chatgpt": build_chatgpt_request,
}
PARSERS = {
    "gemini": parse_gemini_response,
    "claude": parse_claude_response,
    "chatgpt": parse_chatgpt_response,
    "custom": parse_custom_response,
}


def write_status(status_file: str, **fields) -> None:
    Path(status_file).parent.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": datetime.now().isoformat(timespec="seconds"), **fields}
    Path(status_file).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


AGENT_RE = re.compile(r"^conversation\.[a-z0-9_]+$")
CONVERSATION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def file_agent_answer(args, message: str) -> int:
    """Chemin integration : l'automatisation a deja appele
    conversation.process (agent de l'integration Home Assistant du
    fournisseur) et passe sa reponse en base64 — ce script ne fait que la
    classer dans le fichier de statut que la page interroge.

    Une erreur de l'agent (cle refusee, compte sans credit...) sort en 0 :
    elle est dans le statut, la page l'affiche. Le code non nul reste
    reserve a ce qui empeche d'ecrire un statut utile, pour que
    l'automatisation ne notifie pas a chaque message."""
    agent = args.agent if AGENT_RE.match(args.agent or "") else ""
    base = {"provider": args.provider, "agent": agent, "request_message": message}
    if not agent:
        write_status(args.status_file, ok=False, reply=None,
                     error=f"Agent invalide : {args.agent!r}.", **base)
        return 1
    answer = {}
    if args.answer_b64:
        try:
            answer = json.loads(base64.b64decode(args.answer_b64).decode("utf-8"))
        except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
            print(f"[ERR] answer_b64 illisible : {exc}")
            answer = {}
    if not isinstance(answer, dict) or not answer:
        err = (f"{agent} n'a pas repondu. Verifiez l'integration (cle, credit "
               "du compte) dans Parametres > Appareils et services, et le "
               "journal de Home Assistant.")
        write_status(args.status_file, ok=False, reply=None, error=err, **base)
        return 0
    speech = answer.get("speech") if isinstance(answer.get("speech"), str) else ""
    cid = answer.get("conversation_id") if isinstance(answer.get("conversation_id"), str) else ""
    cid = cid if CONVERSATION_ID_RE.match(cid) else ""
    if answer.get("type") == "error":
        write_status(args.status_file, ok=False, reply=None, conversation_id=cid,
                     error=f"{agent} : {speech or 'erreur sans message'}", **base)
        return 0
    write_status(args.status_file, ok=True, reply=speech, error=None,
                 conversation_id=cid, **base)
    print(f"[OK] reponse de {agent} ecrite dans {args.status_file}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8123")
    ap.add_argument("--ha-token-file", default="/config/vssp/.ha_token",
                     help="Jeton HA (voir input_text.vssp_ha_token / "
                          "script.vssp_save_token) — utilise pour lire le "
                          "modele configure et, pour 'custom', l'URL/le "
                          "prompt systeme.")
    ap.add_argument("--provider", required=True,
                     choices=["gemini", "claude", "chatgpt", "custom"])
    ap.add_argument("--message-b64", required=True,
                     help="Message utilisateur, encode en base64 (UTF-8).")
    ap.add_argument("--history-b64", default="",
                     help="JSON [{role, content}, ...] encode en base64 — "
                          "quelques tours recents seulement.")
    ap.add_argument("--status-file", default="/config/www/vssp/chatbot_status.json")
    ap.add_argument("--dry-run", action="store_true",
                     help="Construit la requete et l'affiche, sans appeler le fournisseur.")
    ap.add_argument("--agent", default="",
                     help="Chemin integration : l'agent conversation.* qui a "
                          "deja repondu (shell_command.vssp_chatbot_reply).")
    ap.add_argument("--answer-b64", default="",
                     help="Avec --agent : {type, speech, conversation_id} en "
                          "JSON base64, tire de la reponse de conversation.process.")
    args = ap.parse_args()

    try:
        message = base64.b64decode(args.message_b64).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as exc:
        print(f"[ERR] message_b64 illisible : {exc}")
        write_status(args.status_file, ok=False, provider=args.provider,
                     reply=None, request_message=None,
                     error=f"message_b64 illisible : {exc}")
        return 1
    if not message.strip():
        write_status(args.status_file, ok=False, provider=args.provider,
                     reply=None, request_message=message,
                     error="Message vide.")
        return 1

    if args.agent:
        return file_agent_answer(args, message)

    history: list = []
    if args.history_b64:
        try:
            history = json.loads(base64.b64decode(args.history_b64).decode("utf-8"))
        except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
            print(f"[WARN] history_b64 illisible, historique ignore : {exc}")
            history = []

    api_key = ""
    key_path = Path(KEY_FILES[args.provider])
    if key_path.exists():
        api_key = key_path.read_text(encoding="utf-8").strip()
    if args.provider != "custom" and not api_key:
        err = (f"{args.provider} n'est pas configure : ADMIN > DASHBOARDS > "
               f"CONFIGURER L'IA / SET UP THE AI installe son integration Home Assistant "
               f"(ou, sans integration, collez une cle dans "
               f"input_text.vssp_{args.provider}_api_key puis lancez "
               f"script.vssp_save_{args.provider}_key).")
        print(f"[ERR] {err}")
        write_status(args.status_file, ok=False, provider=args.provider,
                     reply=None, request_message=message, error=err)
        return 1

    ha_token = ""
    token_path = Path(args.ha_token_file)
    if token_path.exists():
        ha_token = token_path.read_text(encoding="utf-8").strip()
    if not ha_token:
        err = ("Jeton API Home Assistant absent "
               f"({args.ha_token_file}). Voir input_text.vssp_ha_token "
               "et script.vssp_save_token.")
        print(f"[ERR] {err}")
        write_status(args.status_file, ok=False, provider=args.provider,
                     reply=None, request_message=message, error=err)
        return 1

    try:
        if args.provider == "custom":
            endpoint = ha_get_state(args.url, ha_token,
                                     "input_text.vssp_chatbot_custom_endpoint")
            if not endpoint:
                raise ChatbotError(
                    "Aucun chatbot custom configure — ouvrez le popup "
                    "depuis l'ecran GENERATION de l'ADMIN pour renseigner "
                    "au moins l'URL du point d'acces.")
            model = ha_get_state(args.url, ha_token,
                                  "input_text.vssp_chatbot_custom_model")
            system_prompt = ha_get_state(
                args.url, ha_token, "input_text.vssp_chatbot_custom_system_prompt")
            request = build_custom_request(
                endpoint, model, system_prompt, api_key, message, history)
        else:
            model = ha_get_state(
                args.url, ha_token, f"input_text.vssp_{args.provider}_model"
            ) or DEFAULT_MODELS[args.provider]
            request = BUILDERS[args.provider](model, api_key, message, history)
    except ChatbotError as exc:
        print(f"[ERR] {exc}")
        write_status(args.status_file, ok=False, provider=args.provider,
                     reply=None, request_message=message, error=str(exc))
        return 1
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        err = f"Home Assistant injoignable pour lire la configuration : {exc}"
        print(f"[ERR] {err}")
        write_status(args.status_file, ok=False, provider=args.provider,
                     reply=None, request_message=message, error=err)
        return 1

    if args.dry_run:
        print(f"[DRY-RUN] {request.full_url}")
        print(f"  headers: { {k: v for k, v in request.header_items()} }")
        print(f"  body: {request.data.decode('utf-8') if request.data else None}")
        return 0

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as resp:
            raw = json.load(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:500]
        err = f"HTTP {exc.code} depuis {args.provider} : {body}"
        print(f"[ERR] {err}")
        write_status(args.status_file, ok=False, provider=args.provider,
                     reply=None, request_message=message, error=err)
        return 1
    except urllib.error.URLError as exc:
        err = f"{args.provider} injoignable : {exc.reason}"
        print(f"[ERR] {err}")
        write_status(args.status_file, ok=False, provider=args.provider,
                     reply=None, request_message=message, error=err)
        return 1

    try:
        reply = PARSERS[args.provider](raw)
    except (KeyError, IndexError, TypeError) as exc:
        err = f"Reponse inattendue de {args.provider} (forme imprevue) : {exc}"
        print(f"[ERR] {err}")
        write_status(args.status_file, ok=False, provider=args.provider,
                     reply=None, request_message=message, error=err)
        return 1

    write_status(args.status_file, ok=True, provider=args.provider,
                 reply=reply, request_message=message, error=None)
    print(f"[OK] reponse recue de {args.provider}, ecrite dans {args.status_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
