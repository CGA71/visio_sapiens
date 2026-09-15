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

# ---------------------------------------------------------------------------
# Visio Sapiens — CORE screen: SCAN, recommendations looked up on the web
#
# EN | The two recommendation boxes of core.html are computed in the page,
# EN | from thresholds: they say WHAT is wrong. The SCAN button asks the
# EN | chat assistant already configured in the console (packages/
# EN | vssp_chatbot.yaml, same key files) to look each finding up on the
# EN | internet — the provider's own web search — and bring back what to do,
# EN | with the pages it read.
# EN | What leaves the house: the findings as the page wrote them (a disk at
# EN | 91 %, a pod in CrashLoopBackOff, a k3s version), the OS and k3s
# EN | versions, and nothing else. No hostname, no address — the page never
# EN | puts them in, and anything shaped like an IPv4 address is masked here
# EN | anyway before the request is built.
# EN | TIME: a web search takes longer than the 60 s Home Assistant gives a
# EN | shell_command before killing it. So --detach writes "running", forks,
# EN | and returns at once; the child does the work and writes the result
# EN | into the same file, which the page polls.
# FR | Les deux encadres de preconisations de core.html sont calcules dans la
# FR | page, a partir de seuils : ils disent CE QUI ne va pas. Le bouton SCAN
# FR | demande a l assistant deja configure dans la console (packages/
# FR | vssp_chatbot.yaml, memes fichiers de cle) de chercher chaque constat
# FR | sur Internet — la recherche web du fournisseur lui-meme — et de
# FR | rapporter quoi faire, avec les pages lues.
# FR | Ce qui sort de la maison : les constats tels que la page les a ecrits
# FR | (un disque a 91 %, un pod en CrashLoopBackOff, une version de k3s),
# FR | les versions de l OS et de k3s, et rien d autre. Ni nom d hote, ni
# FR | adresse — la page n en met jamais, et tout ce qui ressemble a une
# FR | adresse IPv4 est de toute facon masque ici avant la requete.
# FR | DUREE : une recherche web prend plus que les 60 s que Home Assistant
# FR | laisse a un shell_command avant de le tuer. --detach ecrit donc
# FR | « en cours », se detache, et rend la main aussitot ; l enfant fait le
# FR | travail et ecrit le resultat dans le meme fichier, que la page
# FR | interroge.
#
# Usage:
#     python3 vssp_core_scan.py --provider claude --payload-b64 "..." \
#         --status-dir /config/www/vssp --detach
#     python3 vssp_core_scan.py --provider claude --payload-b64 "..." --dry-run
# ---------------------------------------------------------------------------
"""Visio Sapiens — CORE SCAN: web-searched recommendations for the findings."""
import argparse
import base64
import binascii
import datetime as _dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vssp_chatbot_send import DEFAULT_MODELS, KEY_FILES, ha_get_state  # noqa: E402

# EN | The scan is a research task, not a chat turn: Claude runs on its
# EN | current model with the web search tool that filters results itself,
# EN | whatever older model the chat bubble is set to. Gemini and ChatGPT
# EN | keep the model the console chose for them.
# FR | Le scan est une recherche, pas un tour de conversation : Claude tourne
# FR | sur son modele actuel avec l outil de recherche web qui filtre lui-meme
# FR | ses resultats, quel que soit l ancien modele choisi pour la bulle de
# FR | chat. Gemini et ChatGPT gardent le modele choisi pour eux par la
# FR | console.
CLAUDE_MODEL = "claude-opus-5"
CLAUDE_SEARCH_TOOL = "web_search_20260209"
MAX_SEARCHES = 5
MAX_CONTINUATIONS = 3
TIMEOUT_SECONDS = 240

SCOPES = ("system", "k3s")
LANGS = {"en": "English", "fr": "French"}
MAX_FINDINGS = 12

MESSAGES = {
    "scan.running": "Searching the web…",
    "scan.ok": "{count} recommendation(s) from {provider}.",
    "error.payload": "The request from the page was malformed: {detail}",
    "error.no_key": "No API key for {provider}: enter it in the assistant settings of the console.",
    "error.no_web": "The custom provider has no web search: choose Claude, Gemini or ChatGPT for SCAN.",
    "error.provider": "{provider} answered {code}: {detail}",
    "error.refusal": "{provider} declined the request.",
    "error.parse": "{provider} answered, but not in the expected form.",
}


class ScanError(Exception):
    def __init__(self, key: str, **vars_):
        super().__init__(key)
        self.key, self.vars = key, vars_


def status(key: str, **vars_) -> dict:
    template = MESSAGES.get(key, key)
    try:
        rendered = template.format(**vars_)
    except (KeyError, IndexError):
        rendered = template
    return {"message_key": key, "message_vars": vars_, "message": rendered}


def now() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


# ═══════════════════════════════════════════════════════════════════════════
# EN | THE REQUEST FROM THE PAGE / FR | LA DEMANDE DE LA PAGE
# ═══════════════════════════════════════════════════════════════════════════
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def clean(text, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return IPV4.sub("<ip>", text)[:limit]


def decode_payload(b64: str) -> dict:
    try:
        raw = json.loads(base64.b64decode(b64, validate=True).decode("utf-8"))
    except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
        raise ScanError("error.payload", detail=str(exc)[:120]) from exc
    if not isinstance(raw, dict):
        raise ScanError("error.payload", detail="not an object")
    rid = str(raw.get("request_id", ""))
    if not re.fullmatch(r"[A-Za-z0-9-]{8,40}", rid):
        raise ScanError("error.payload", detail="request_id")
    scope = raw.get("scope")
    if scope not in SCOPES:
        raise ScanError("error.payload", detail="scope")
    lang = raw.get("lang") if raw.get("lang") in LANGS else "en"
    ctx = raw.get("context") if isinstance(raw.get("context"), dict) else {}
    findings = []
    for f in (raw.get("findings") or [])[:MAX_FINDINGS]:
        if isinstance(f, dict):
            findings.append({"severity": clean(f.get("sev"), 8),
                             "title": clean(f.get("title"), 200),
                             "detail": clean(f.get("detail"), 600)})
    return {"request_id": rid, "scope": scope, "lang": lang, "findings": findings,
            "context": {k: clean(ctx.get(k), 80) for k in ("os", "kernel", "k3s", "cpus", "ram")
                        if ctx.get(k) not in (None, "")}}


def build_prompt(req: dict) -> tuple[str, str]:
    what = ("a Linux home server (Ubuntu) running Home Assistant inside a single-node k3s cluster"
            if req["scope"] == "system" else
            "a single-node k3s cluster on a Linux home server that runs Home Assistant")
    system = (
        f"You are a site-reliability engineer helping the owner of {what}. "
        "For each finding, search the web for current, authoritative guidance — prefer official "
        "documentation (docs.k3s.io, kubernetes.io, ubuntu.com, home-assistant.io, the Glances docs) "
        "and upstream GitHub issues over forums — and turn it into concrete advice for this machine. "
        "Diagnose before changing: give read-only commands first, then the fix. Never suggest "
        "disabling security features, exposing ports, or deleting data without a backup. "
        f"Write in {LANGS[req['lang']]}. "
        "Answer with ONE JSON object and nothing else, of the form "
        '{"summary": string, "items": [{"finding": string, "severity": "crit"|"warn"|"info", '
        '"advice": string, "steps": [string], "sources": [{"title": string, "url": string}]}]}. '
        "At most 6 items, advice under 400 characters, at most 4 steps each (shell commands or "
        "short actions), and only sources you actually read."
    )
    if req["findings"]:
        body = "Findings on screen right now:\n" + json.dumps(req["findings"], ensure_ascii=False, indent=1)
    else:
        body = ("Nothing is flagged on screen right now. Give preventive maintenance advice and "
                "any known issues for exactly these versions.")
    body += "\n\nContext:\n" + json.dumps(req["context"], ensure_ascii=False)
    return system, body


# ═══════════════════════════════════════════════════════════════════════════
# EN | PROVIDERS — each with its own web search / FR | FOURNISSEURS
# ═══════════════════════════════════════════════════════════════════════════
def post(url: str, headers: dict, body: dict, provider: str) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers=dict(headers, **{"Content-Type": "application/json"}))
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        try:
            detail = json.loads(detail).get("error", {}).get("message", detail)
        except (ValueError, AttributeError):
            pass
        raise ScanError("error.provider", provider=provider, code=exc.code,
                        detail=str(detail)[:200]) from exc
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise ScanError("error.provider", provider=provider, code="—",
                        detail=str(exc)[:200]) from exc


def ask_claude(key: str, system: str, prompt: str) -> tuple[str, list, int]:
    # EN | fallbacks "default": if Claude declines, Anthropic re-runs the
    # EN | request on the model it recommends for that case, server side.
    # FR | fallbacks "default" : si Claude refuse, Anthropic relance la
    # FR | requete, cote serveur, sur le modele qu il recommande pour ce cas.
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01",
               "anthropic-beta": "server-side-fallback-2026-07-01"}
    messages = [{"role": "user", "content": prompt}]
    body = {"model": CLAUDE_MODEL, "max_tokens": 16000, "system": system,
            "fallbacks": "default", "output_config": {"effort": "medium"},
            "tools": [{"type": CLAUDE_SEARCH_TOOL, "name": "web_search", "max_uses": MAX_SEARCHES}],
            "messages": messages}
    for _ in range(MAX_CONTINUATIONS + 1):
        resp = post("https://api.anthropic.com/v1/messages", headers, body, "Claude")
        if resp.get("stop_reason") == "refusal":
            raise ScanError("error.refusal", provider="Claude")
        # EN | pause_turn: the server-side search loop hit its own limit;
        # EN | sending the turn back as is lets it resume where it stopped.
        # FR | pause_turn : la boucle de recherche cote serveur a atteint sa
        # FR | propre limite ; renvoyer le tour tel quel la fait reprendre.
        if resp.get("stop_reason") == "pause_turn":
            messages = [{"role": "user", "content": prompt},
                        {"role": "assistant", "content": resp.get("content", [])}]
            body["messages"] = messages
            continue
        break
    text, sources, searches = [], [], 0
    for block in resp.get("content", []):
        kind = block.get("type")
        if kind == "text":
            text.append(block.get("text", ""))
            for c in block.get("citations") or []:
                if c.get("url"):
                    sources.append({"title": c.get("title", ""), "url": c["url"]})
        elif kind == "server_tool_use":
            searches += 1
    return "".join(text), sources, searches


def ask_gemini(key: str, model: str, system: str, prompt: str) -> tuple[str, list, int]:
    body = {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}]}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    resp = post(url, {"X-goog-api-key": key}, body, "Gemini")
    cand = (resp.get("candidates") or [{}])[0]
    text = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts", []))
    meta = cand.get("groundingMetadata") or {}
    sources = [{"title": (c.get("web") or {}).get("title", ""), "url": (c.get("web") or {}).get("uri", "")}
               for c in meta.get("groundingChunks") or [] if (c.get("web") or {}).get("uri")]
    return text, sources, len(meta.get("webSearchQueries") or [])


def ask_chatgpt(key: str, model: str, system: str, prompt: str) -> tuple[str, list, int]:
    body = {"model": model, "instructions": system, "input": prompt,
            "tools": [{"type": "web_search"}]}
    resp = post("https://api.openai.com/v1/responses", {"Authorization": f"Bearer {key}"},
                body, "ChatGPT")
    text, sources, searches = [], [], 0
    for item in resp.get("output") or []:
        if item.get("type") == "web_search_call":
            searches += 1
        for part in item.get("content") or []:
            if part.get("type") == "output_text":
                text.append(part.get("text", ""))
                for a in part.get("annotations") or []:
                    if a.get("type") == "url_citation" and a.get("url"):
                        sources.append({"title": a.get("title", ""), "url": a["url"]})
    return "".join(text), sources, searches


# ═══════════════════════════════════════════════════════════════════════════
def parse_answer(text: str, provider: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ScanError("error.parse", provider=provider)
    try:
        data = json.loads(text[start:end + 1])
    except ValueError as exc:
        raise ScanError("error.parse", provider=provider) from exc
    items = []
    for it in (data.get("items") or [])[:6]:
        if not isinstance(it, dict):
            continue
        items.append({
            "finding": clean(it.get("finding"), 200),
            "severity": it.get("severity") if it.get("severity") in ("crit", "warn", "info") else "info",
            "advice": str(it.get("advice") or "").strip()[:600],
            "steps": [str(s).strip()[:300] for s in (it.get("steps") or [])[:4] if str(s).strip()],
            "sources": [{"title": clean(s.get("title"), 120), "url": s["url"]}
                        for s in (it.get("sources") or [])[:4]
                        if isinstance(s, dict) and str(s.get("url", "")).startswith(("https://", "http://"))],
        })
    return {"summary": str(data.get("summary") or "").strip()[:600], "items": items}


def run(req: dict, provider: str, args) -> dict:
    if provider == "custom":
        raise ScanError("error.no_web")
    key_path = Path(KEY_FILES.get(provider, ""))
    key = key_path.read_text(encoding="utf-8").strip() if key_path.is_file() else ""
    if not key:
        raise ScanError("error.no_key", provider=provider)
    system, prompt = build_prompt(req)
    if provider == "claude":
        model = CLAUDE_MODEL
        text, cites, searches = ask_claude(key, system, prompt)
    else:
        model = DEFAULT_MODELS[provider]
        try:
            token = Path(args.ha_token_file).read_text(encoding="utf-8").strip()
            model = ha_get_state(args.url, token, f"input_text.vssp_{provider}_model") or model
        except (OSError, urllib.error.URLError, ValueError):
            pass
        ask = ask_gemini if provider == "gemini" else ask_chatgpt
        text, cites, searches = ask(key, model, system, prompt)
    answer = parse_answer(text, provider.capitalize())
    seen, citations = set(), []
    for s in cites:
        if s["url"] not in seen:
            seen.add(s["url"])
            citations.append({"title": clean(s.get("title"), 120), "url": s["url"]})
    return dict(answer, model=model, searches=searches, citations=citations[:12])


def main() -> int:
    ap = argparse.ArgumentParser(description="Visio Sapiens — CORE SCAN")
    ap.add_argument("--provider", required=True, choices=["gemini", "claude", "chatgpt", "custom"])
    ap.add_argument("--payload-b64", required=True)
    ap.add_argument("--status-dir", default="/config/www/vssp")
    ap.add_argument("--url", default="http://localhost:8123")
    ap.add_argument("--ha-token-file", default="/config/vssp/.ha_token")
    ap.add_argument("--detach", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    try:
        req = decode_payload(args.payload_b64)
    except ScanError as exc:
        # EN | No valid scope means no file to answer in: say it on stderr,
        # EN | the automation turns a nonzero exit into a notification.
        # FR | Sans portee valide, pas de fichier ou repondre : le dire sur
        # FR | stderr, l automatisation transforme un code non nul en
        # FR | notification.
        print(status(exc.key, **exc.vars)["message"], file=sys.stderr)
        return 1
    out = Path(args.status_dir) / f"core_scan_{req['scope']}.json"
    base = {"request_id": req["request_id"], "scope": req["scope"], "provider": args.provider,
            "started": now()}
    write_json(out, dict(base, state="running", ok=True, **status("scan.running")))
    if args.dry_run:
        print(json.dumps(build_prompt(req), ensure_ascii=False, indent=1))
        return 0

    if args.detach:
        if os.fork():
            return 0
        os.setsid()
        # EN | Home Assistant waits for the pipes it handed over to close, not
        # EN | just for the parent: the child lets go of them.
        # FR | Home Assistant attend la fermeture des tubes qu il a transmis,
        # FR | pas seulement le parent : l enfant les lache.
        devnull = os.open(os.devnull, os.O_RDWR)
        for fd in (0, 1, 2):
            os.dup2(devnull, fd)

    try:
        result = run(req, args.provider, args)
        payload = dict(base, state="done", ok=True, generated=now(), **result,
                       **status("scan.ok", count=len(result["items"]),
                                provider=args.provider.capitalize()))
    except ScanError as exc:
        payload = dict(base, state="done", ok=False, generated=now(), **status(exc.key, **exc.vars))
    write_json(out, payload)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
