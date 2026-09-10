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
# Visio Sapiens — Google Calendar setup automation
#
# EN | Does, from the ADMIN console, everything Home Assistant's Google
# EN | Calendar integration normally asks you to do by hand in
# EN | Settings > Devices & services:
# EN |   1. register the OAuth client (client_id / client_secret) as an
# EN |      "application credential" for domain `google`,
# EN |   2. start the `google` config flow and hand back the Google consent
# EN |      URL,
# EN |   3. report which calendar.* entities exist once the account is linked.
# EN | The ONE step this cannot remove is the Google consent click itself:
# EN | OAuth is designed so the account owner approves in Google's own UI.
# EN | Everything before and after it is automated here.
# FR | Fait, depuis la console ADMIN, tout ce que l'integration Google
# FR | Calendar de Home Assistant demande normalement a la main dans
# FR | Parametres > Appareils et services :
# FR |   1. enregistrer le client OAuth (client_id / client_secret) comme
# FR |      « application credential » du domaine `google`,
# FR |   2. demarrer le config flow `google` et renvoyer l'URL de
# FR |      consentement Google,
# FR |   3. rapporter les entites calendar.* une fois le compte lie.
# FR | La SEULE etape non supprimable est le clic de consentement Google :
# FR | OAuth est concu pour que le proprietaire du compte approuve dans
# FR | l'interface de Google. Tout ce qui l'entoure est automatise ici.
#
# EN | WHY A HAND-ROLLED WEBSOCKET CLIENT — application_credentials has NO
# EN | REST endpoint; `application_credentials/create` exists only on Home
# EN | Assistant's websocket API. Rather than add a websockets dependency to
# EN | the pod (every other script here is stdlib + pyyaml), this speaks the
# EN | few frames of RFC 6455 it needs: masked client text frames, unmasked
# EN | server frames, ping/pong. That is ~90 lines and no new dependency.
# FR | POURQUOI UN CLIENT WEBSOCKET ECRIT A LA MAIN — application_credentials
# FR | n'a AUCUN point d'acces REST ; `application_credentials/create`
# FR | n'existe que sur l'API websocket de Home Assistant. Plutot que
# FR | d'ajouter une dependance websockets au pod (tous les autres scripts
# FR | ici sont stdlib + pyyaml), celui-ci parle les quelques trames de la
# FR | RFC 6455 dont il a besoin : trames texte client masquees, trames
# FR | serveur non masquees, ping/pong. Environ 90 lignes, zero dependance.
#
# EN | SECRETS — the client_secret is NEVER a command-line argument (it would
# EN | show up in `ps` and in the shell history of the pod). Same convention
# EN | as vssp_ha_token and the chatbot API keys: a shell_command writes it to
# EN | a 0600 file, this script reads the file. The client_id is public by
# EN | OAuth design (it travels in the consent URL) so it stays a plain flag.
# FR | SECRETS — le client_secret n'est JAMAIS un argument de ligne de
# FR | commande (il apparaitrait dans `ps` et dans l'historique shell du
# FR | pod). Meme convention que vssp_ha_token et les cles API du chatbot :
# FR | un shell_command l'ecrit dans un fichier 0600, ce script lit le
# FR | fichier. Le client_id est public par conception OAuth (il voyage dans
# FR | l'URL de consentement), il reste donc un simple flag.
#
# EN | LANGUAGE — every sentence written to the status file is read by a
# EN | human in the ADMIN console, under labels the dashboard generator has
# EN | already translated. `--locale` (fed by input_select.vssp_language, the
# EN | same selector the generator reads) therefore renders `message` and
# EN | `state_label` in that language, and `message_key` + `message_vars` are
# EN | published alongside so the wizard page can re-translate on its own.
# FR | LANGUE — chaque phrase ecrite dans le fichier d'etat est lue par un
# FR | humain dans la console ADMIN, sous des libelles que le generateur de
# FR | dashboards a deja traduits. `--locale` (alimente par
# FR | input_select.vssp_language, le meme selecteur que lit le generateur)
# FR | rend donc `message` et `state_label` dans cette langue, et
# FR | `message_key` + `message_vars` sont publies a cote pour que la page
# FR | wizard puisse retraduire elle-meme.
#
# EN | USAGE / FR | UTILISATION
#   python3 vssp_google_setup.py --action connect  --client-id "…apps.googleusercontent.com" --locale fr
#   python3 vssp_google_setup.py --action status   --locale en
#   python3 vssp_google_setup.py --action calendars
#
# EN | Exit codes: 0 = OK, 1 = error (the status file always gets written, so
# EN | the ADMIN screen can explain the failure instead of just going quiet).
# FR | Codes de sortie : 0 = OK, 1 = erreur (le fichier d'etat est toujours
# FR | ecrit, pour que l'ecran ADMIN puisse expliquer l'echec au lieu de
# FR | rester muet).
# ============================================================================
from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import ssl
import struct
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

# EN | The domain Home Assistant registers the Google Calendar integration
# EN | under. Both the application credential and the config flow use it.
# FR | Le domaine sous lequel Home Assistant enregistre l'integration Google
# FR | Calendar. Le credential applicatif et le config flow l'utilisent tous
# FR | les deux.
GOOGLE_DOMAIN = "google"

# EN | Exact redirect URI Google must be configured with, per the integration
# EN | documentation. Surfaced in the status file so the ADMIN form can show
# EN | the value to paste into Google Cloud rather than hardcoding it twice.
# FR | URI de redirection exacte a configurer chez Google, selon la
# FR | documentation de l'integration. Exposee dans le fichier d'etat pour
# FR | que le formulaire ADMIN affiche la valeur a coller dans Google Cloud
# FR | plutot que de la coder en dur a deux endroits.
REDIRECT_URI = "https://my.home-assistant.io/redirect/oauth"


# ── EN | Interface language / FR | Langue de l'interface ─────────────────
# EN | Every sentence this script publishes is read by a HUMAN in the ADMIN
# EN | console, next to labels that the dashboard generator has already
# EN | translated. English-only messages under French labels is exactly the
# EN | mismatch this table exists to remove, so the status file carries BOTH:
# EN |   message_key + message_vars  — machine form, re-translated by the
# EN |                                 wizard page in ITS own language;
# EN |   message + state_label       — rendered here in --locale, because a
# EN |                                 command_line sensor cannot translate.
# EN | English is the reference: a locale missing a key falls back to it, so
# EN | adding a language never breaks the flow.
# FR | Chaque phrase publiee par ce script est lue par un HUMAIN dans la
# FR | console ADMIN, a cote de libelles que le generateur de dashboards a
# FR | deja traduits. Des messages en anglais sous des libelles francais,
# FR | c'est exactement le melange que cette table sert a supprimer : le
# FR | fichier d'etat porte donc LES DEUX :
# FR |   message_key + message_vars  — forme machine, retraduite par la page
# FR |                                 wizard dans SA propre langue ;
# FR |   message + state_label       — rendus ici dans --locale, parce qu'un
# FR |                                 capteur command_line ne sait pas
# FR |                                 traduire.
# FR | L'anglais est la reference : une locale sans la cle y retombe, donc
# FR | ajouter une langue ne casse jamais le flux.
BASE_LOCALE = "en"
SUPPORTED_LOCALES = ("en", "fr")

MESSAGES = {
    "no_token": {
        "en": "Home Assistant token missing — fill input_text.vssp_ha_token "
              "and run SAVE TOKEN first.",
        "fr": "Jeton Home Assistant absent — renseignez "
              "input_text.vssp_ha_token puis lancez ENREGISTRER LE JETON.",
    },
    "calendars_found": {
        "en": "{n} calendar entity(ies) found.",
        "fr": "{n} entite(s) calendrier trouvee(s).",
    },
    "no_calendar_yet": {
        "en": "No calendar entity yet — finish the Google consent step.",
        "fr": "Aucune entite calendrier — terminez l'etape de consentement "
              "Google.",
    },
    "credentials_required": {
        "en": "Client ID and client secret are both required. Fill them in "
              "the ADMIN Google Calendar form.",
        "fr": "L'ID client et le secret client sont tous deux obligatoires. "
              "Renseignez-les dans le formulaire Google Calendar de l'ADMIN.",
    },
    "credentials_ok": {
        "en": "OAuth client registered in Home Assistant. Start the "
              "connection to get the Google consent link.",
        "fr": "Client OAuth enregistre dans Home Assistant. Lancez la "
              "connexion pour obtenir le lien de consentement Google.",
    },
    "awaiting_consent": {
        "en": "Open the Google consent link to finish linking the account.",
        "fr": "Ouvrez le lien de consentement Google pour terminer la "
              "liaison du compte.",
    },
    "already_linked": {
        "en": "Google Calendar is already linked to Home Assistant — nothing "
              "to do.",
        "fr": "Google Calendar est deja lie a Home Assistant — rien a faire.",
    },
    "flow_aborted": {
        "en": "Config flow aborted: {reason}",
        "fr": "Config flow interrompu : {reason}",
    },
    "unexpected_step": {
        "en": "Unexpected config-flow step '{step}' ({type}) — finish this "
              "one in Settings > Devices & services.",
        "fr": "Etape de config flow inattendue « {step} » ({type}) — "
              "terminez celle-ci dans Parametres > Appareils et services.",
    },
    # EN | Technical failure text (HTTP body, socket error). Not translatable
    # EN | — it comes from Home Assistant or the OS — so the key only frames
    # EN | it, and the raw string travels in message_vars.
    # FR | Texte d'echec technique (corps HTTP, erreur socket). Non
    # FR | traduisible — il vient de Home Assistant ou de l'OS — donc la cle
    # FR | ne fait que l'encadrer, la chaine brute voyage dans message_vars.
    "failure": {
        "en": "Failure: {detail}",
        "fr": "Echec : {detail}",
    },
}

# EN | Shown by sensor.vssp_google_state, which would otherwise display the
# EN | raw machine token ("awaiting_consent") under a translated label. The
# EN | token itself stays in `state`, untranslated, because that is what the
# EN | wizard page branches on.
# FR | Affiche par sensor.vssp_google_state, qui sinon montrerait le jeton
# FR | machine brut (« awaiting_consent ») sous un libelle traduit. Le jeton
# FR | lui-meme reste dans `state`, non traduit, car c'est sur lui que la
# FR | page wizard s'aiguille.
STATE_LABELS = {
    "not_configured": {"en": "Not configured", "fr": "Non configure"},
    "idle": {"en": "Waiting", "fr": "En attente"},
    "credentials_ok": {"en": "Client registered", "fr": "Client enregistre"},
    "awaiting_consent": {"en": "Consent required", "fr": "Consentement requis"},
    "connected": {"en": "Connected", "fr": "Connecte"},
    "error": {"en": "Error", "fr": "Erreur"},
}


def pick_locale(value: str) -> str:
    """EN | Normalise whatever input_select.vssp_language holds ('fr', 'en',
    EN | 'unknown' before the selector is set) to a supported code.
    FR | Normalise ce que contient input_select.vssp_language ('fr', 'en',
    FR | 'unknown' tant que le selecteur n'est pas pose) vers un code
    FR | supporte."""
    code = (value or "").strip().lower().replace("_", "-").split("-")[0]
    return code if code in SUPPORTED_LOCALES else BASE_LOCALE


def msg(key: str, locale: str, **fields) -> str:
    entry = MESSAGES.get(key, {})
    text = entry.get(locale) or entry.get(BASE_LOCALE) or key
    return text.format(**fields) if fields else text


def say(key: str, locale: str, **fields) -> dict:
    """EN | The three status keys that describe one message: the key and its
    EN | variables for consumers that translate on their own, plus the
    EN | rendered sentence for the ones that cannot.
    FR | Les trois cles d'etat qui decrivent un message : la cle et ses
    FR | variables pour les consommateurs qui traduisent eux-memes, plus la
    FR | phrase rendue pour ceux qui ne savent pas."""
    return {"message_key": key,
            "message_vars": fields,
            "message": msg(key, locale, **fields)}


def stated(state: str, locale: str) -> dict:
    label = STATE_LABELS.get(state, {})
    return {"state": state,
            "state_label": label.get(locale) or label.get(BASE_LOCALE) or state}


# ── EN | Status file / FR | Fichier d'etat ───────────────────────────────
def write_status(path: str, payload: dict) -> None:
    """EN | Atomic-ish write of the JSON the ADMIN screen and the wizard poll.
    FR | Ecriture (quasi atomique) du JSON interroge par l'ecran ADMIN et le
    FR | wizard."""
    payload["generated"] = datetime.now().isoformat(timespec="seconds")
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                       encoding="utf-8")
        tmp.replace(p)
    except OSError as exc:
        print(f"[warn] status file not written: {exc}", file=sys.stderr)


# ── EN | Token resolution / FR | Resolution du jeton ─────────────────────
def resolve_token(args) -> str | None:
    """EN | --token > $HA_TOKEN > --token-file. Same order as
    FR | vssp_energy_sync.py, so one convention across the project."""
    if args.token and args.token.strip() not in ("", "unknown", "unavailable",
                                                 "None"):
        return args.token.strip()
    env = os.environ.get("HA_TOKEN")
    if env and env.strip():
        return env.strip()
    try:
        text = Path(args.token_file).read_text(encoding="utf-8").strip()
        return text or None
    except OSError:
        return None


def read_secret(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


# ── EN | Minimal RFC 6455 client / FR | Client RFC 6455 minimal ──────────
class WSError(RuntimeError):
    pass


class MiniWS:
    """EN | Just enough WebSocket to talk to Home Assistant: connect, auth,
    EN | send a command, read its result. Text frames only.
    FR | Juste ce qu'il faut de WebSocket pour parler a Home Assistant :
    FR | connexion, auth, envoi d'une commande, lecture du resultat. Trames
    FR | texte uniquement."""

    def __init__(self, base_url: str, timeout: float = 20.0):
        parsed = urllib.parse.urlsplit(base_url)
        self.secure = parsed.scheme == "https"
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port or (443 if self.secure else 80)
        # EN | HA serves its websocket at /api/websocket regardless of any
        # EN | path prefix in the base url (the pod is always the root).
        # FR | HA sert son websocket sur /api/websocket quel que soit le
        # FR | prefixe de chemin de l'url de base (le pod est toujours la
        # FR | racine).
        self.path = "/api/websocket"
        self.timeout = timeout
        self.sock: socket.socket | None = None
        self._buf = b""
        self._msg_id = 0

    # -- connection ------------------------------------------------------
    def connect(self) -> None:
        raw = socket.create_connection((self.host, self.port), self.timeout)
        if self.secure:
            ctx = ssl.create_default_context()
            raw = ctx.wrap_socket(raw, server_hostname=self.host)
        raw.settimeout(self.timeout)
        self.sock = raw
        key = base64.b64encode(os.urandom(16)).decode()
        handshake = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        raw.sendall(handshake.encode())
        # EN | Read response headers only; anything after the blank line is
        # EN | already frame data and must stay in the buffer.
        # FR | Ne lire que les en-tetes ; tout ce qui suit la ligne vide est
        # FR | deja de la trame et doit rester dans le tampon.
        while b"\r\n\r\n" not in self._buf:
            chunk = raw.recv(4096)
            if not chunk:
                raise WSError("connection closed during handshake")
            self._buf += chunk
        head, _, rest = self._buf.partition(b"\r\n\r\n")
        self._buf = rest
        status = head.split(b"\r\n", 1)[0].decode("latin-1")
        if "101" not in status:
            raise WSError(f"websocket upgrade refused: {status}")

    def close(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

    # -- framing ---------------------------------------------------------
    def _recv_exact(self, n: int) -> bytes:
        while len(self._buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise WSError("connection closed by Home Assistant")
            self._buf += chunk
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def _send_frame(self, payload: bytes, opcode: int = 0x1) -> None:
        header = bytearray([0x80 | opcode])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < (1 << 16):
            header.append(0x80 | 126)
            header += struct.pack(">H", length)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", length)
        mask = os.urandom(4)
        header += mask
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(bytes(header) + masked)

    def _read_frame(self) -> tuple[int, bytes]:
        b0, b1 = self._recv_exact(2)
        opcode = b0 & 0x0F
        length = b1 & 0x7F
        if length == 126:
            length = struct.unpack(">H", self._recv_exact(2))[0]
        elif length == 127:
            length = struct.unpack(">Q", self._recv_exact(8))[0]
        # EN | A server frame is never masked (RFC 6455 §5.1).
        # FR | Une trame serveur n'est jamais masquee (RFC 6455 §5.1).
        payload = self._recv_exact(length) if length else b""
        return opcode, payload

    def recv_json(self) -> dict:
        """EN | Next application message, reassembling continuations and
        FR | repondant aux ping, jusqu'a obtenir un message texte complet."""
        buf = b""
        opcode_first = None
        while True:
            opcode, payload = self._read_frame()
            if opcode == 0x9:                      # ping -> pong
                self._send_frame(payload, opcode=0xA)
                continue
            if opcode == 0xA:                      # pong, ignore
                continue
            if opcode == 0x8:                      # close
                raise WSError("Home Assistant closed the websocket")
            if opcode in (0x1, 0x2):
                opcode_first = opcode
                buf = payload
            elif opcode == 0x0:
                buf += payload
            # EN | FIN bit lives in the byte we already consumed; simplest
            # EN | reliable test for HA (which never fragments its small JSON)
            # EN | is to try to parse and keep reading if it is incomplete.
            # FR | Le bit FIN est dans l'octet deja consomme ; le test fiable
            # FR | le plus simple pour HA (qui ne fragmente jamais son petit
            # FR | JSON) est de tenter le parse et de continuer si incomplet.
            if opcode_first == 0x1:
                try:
                    return json.loads(buf.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue

    def send_json(self, obj: dict) -> None:
        self._send_frame(json.dumps(obj).encode("utf-8"))

    # -- protocol --------------------------------------------------------
    def authenticate(self, token: str) -> None:
        hello = self.recv_json()
        if hello.get("type") != "auth_required":
            raise WSError(f"unexpected greeting: {hello.get('type')}")
        self.send_json({"type": "auth", "access_token": token})
        reply = self.recv_json()
        if reply.get("type") != "auth_ok":
            raise WSError(reply.get("message") or "authentication refused "
                                                  "(check the long-lived token)")

    def command(self, payload: dict) -> dict:
        """EN | Send one command, return its result message.
        FR | Envoie une commande, renvoie son message de resultat."""
        self._msg_id += 1
        msg_id = self._msg_id
        self.send_json({"id": msg_id, **payload})
        while True:
            msg = self.recv_json()
            if msg.get("id") == msg_id and msg.get("type") == "result":
                if not msg.get("success", False):
                    err = (msg.get("error") or {}).get("message", "unknown error")
                    raise WSError(err)
                return msg.get("result")


# ── EN | REST helpers / FR | Aides REST ──────────────────────────────────
def rest(url: str, token: str, path: str, body: dict | None = None,
         method: str | None = None) -> dict | list:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{url.rstrip('/')}{path}", data=data,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        method=method or ("POST" if data else "GET"),
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw) if raw else {}


def list_calendars(url: str, token: str) -> list[dict]:
    """EN | The user-visible proof the link worked: calendar.* entities.
    FR | La preuve visible que la liaison a marche : les entites calendar.*"""
    try:
        states = rest(url, token, "/api/states")
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError):
        return []
    out = []
    for st in states or []:
        eid = st.get("entity_id", "")
        if eid.startswith("calendar."):
            out.append({
                "entity_id": eid,
                "name": (st.get("attributes") or {}).get("friendly_name", eid),
            })
    return sorted(out, key=lambda c: c["entity_id"])


# ── EN | Actions / FR | Actions ──────────────────────────────────────────
def ensure_credentials(url: str, token: str, client_id: str,
                       client_secret: str, name: str) -> tuple[str, str]:
    """EN | Create the application credential unless an identical one exists,
    EN | and return (credential_id, message).
    EN |
    EN | The id matters: Home Assistant's application_credentials collection
    EN | declares UPDATE_FIELDS = {} — credentials CANNOT be edited. Fixing a
    EN | mistyped client id therefore leaves the old credential in place and
    EN | adds a second one, at which point the config flow stops going
    EN | straight to Google and asks which implementation to use. Returning
    EN | the id of OUR credential is what lets start_flow() answer that
    EN | question with the right one instead of whichever happens to be
    EN | listed first (which would be the stale one).
    EN | Requires an ADMIN token: the collection is registered with
    EN | admin_only=True.
    FR | Cree le credential applicatif sauf s'il en existe deja un identique,
    FR | et renvoie (credential_id, message).
    FR |
    FR | L'id compte : la collection application_credentials de Home
    FR | Assistant declare UPDATE_FIELDS = {} — un credential NE PEUT PAS
    FR | etre modifie. Corriger un id client mal saisi laisse donc l'ancien
    FR | en place et en ajoute un second, et des lors le config flow ne va
    FR | plus directement chez Google : il demande quelle implementation
    FR | utiliser. Renvoyer l'id du NOTRE est ce qui permet a start_flow() de
    FR | repondre correctement plutot que de prendre le premier de la liste
    FR | (qui serait le perime).
    FR | Exige un jeton ADMIN : la collection est enregistree avec
    FR | admin_only=True."""
    ws = MiniWS(url)
    try:
        ws.connect()
        ws.authenticate(token)
        existing = ws.command({"type": "application_credentials/list"}) or []
        for cred in existing:
            if (cred.get("domain") == GOOGLE_DOMAIN
                    and cred.get("client_id") == client_id):
                return cred.get("id", ""), "credential already registered"
        created = ws.command({
            "type": "application_credentials/create",
            "domain": GOOGLE_DOMAIN,
            "client_id": client_id,
            "client_secret": client_secret,
            "name": name or "Visio Sapiens — Google Calendar",
        }) or {}
        return created.get("id", ""), "credential registered"
    finally:
        ws.close()


def _option_value(option) -> str:
    """EN | Normalise one select option to its VALUE.
    EN | `vol.In({key: label})` serialises to JSON as [value, label] pairs,
    EN | so an option is usually a two-item list — passing the pair straight
    EN | back as the answer is rejected by the flow. Dicts and bare strings
    EN | are accepted too, since the exact shape is a serialisation detail
    EN | that has changed before.
    FR | Normalise une option de select vers sa VALEUR.
    FR | `vol.In({cle: libelle})` se serialise en JSON en paires
    FR | [valeur, libelle] : une option est donc le plus souvent une liste de
    FR | deux elements, et renvoyer la paire telle quelle est refuse par le
    FR | flow. Les dictionnaires et les chaines nues sont acceptes aussi, la
    FR | forme exacte etant un detail de serialisation qui a deja change."""
    if isinstance(option, dict):
        return str(option.get("value", ""))
    if isinstance(option, (list, tuple)) and option:
        return str(option[0])
    return str(option)


def start_flow(url: str, token: str, prefer_implementation: str = "") -> dict:
    """EN | Start the `google` config flow and dig out the consent URL.
    EN | Answers the pick_implementation step — which only appears when more
    EN | than one credential is registered for the domain — with OUR
    EN | credential rather than whichever is listed first, because an
    EN | un-editable stale credential (see ensure_credentials) is exactly
    EN | what puts a second option in that list.
    FR | Demarre le config flow `google` et extrait l'URL de consentement.
    FR | Repond a l'etape pick_implementation — qui n'apparait que si
    FR | plusieurs credentials existent pour le domaine — avec le NOTRE
    FR | plutot qu'avec le premier de la liste, car c'est justement un
    FR | credential perime non modifiable (voir ensure_credentials) qui
    FR | ajoute une seconde option."""
    res = rest(url, token, "/api/config/config_entries/flow",
               {"handler": GOOGLE_DOMAIN, "show_advanced_options": False})
    if res.get("type") == "form" and res.get("step_id") == "pick_implementation":
        flow_id = res.get("flow_id")
        options = []
        for field in (res.get("data_schema") or []):
            if field.get("name") == "implementation":
                options = [_option_value(o) for o in (field.get("options") or [])]
        chosen = (prefer_implementation
                  if prefer_implementation in options
                  else (options[0] if options else ""))
        payload = {"implementation": chosen} if chosen else {}
        res = rest(url, token,
                   f"/api/config/config_entries/flow/{flow_id}", payload)
    return res


def build_status(url: str, token: str, client_id: str, secret_set: bool,
                 extra: dict | None = None) -> dict:
    calendars = list_calendars(url, token) if token else []
    status = {
        "redirect_uri": REDIRECT_URI,
        "client_id_set": bool(client_id),
        # EN | Never the value itself — just enough to recognise it in the UI.
        # FR | Jamais la valeur elle-meme — juste de quoi la reconnaitre.
        "client_id_tail": client_id[-12:] if client_id else "",
        "secret_set": secret_set,
        "connected": bool(calendars),
        "calendars": calendars,
    }
    status.update(extra or {})
    return status


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--action", required=True,
                    choices=["connect", "credentials", "flow", "status",
                             "calendars"])
    ap.add_argument("--url", default="http://localhost:8123")
    ap.add_argument("--token", default=None)
    ap.add_argument("--token-file", default="/config/vssp/.ha_token")
    ap.add_argument("--client-id", default="",
                    help="OAuth client id (public by design, unlike the secret)")
    ap.add_argument("--secret-file", default="/config/vssp/.google_client_secret",
                    help="0600 file written by shell_command.vssp_write_google_secret")
    ap.add_argument("--name", default="Visio Sapiens — Google Calendar")
    ap.add_argument("--status-file",
                    default="/config/www/vssp/google_status.json")
    # EN | Interface language, fed by input_select.vssp_language (the same
    # EN | selector the dashboard generator reads through its own --locale).
    # EN | Anything unknown falls back to English rather than failing: a
    # EN | selector that has never been set reads as "unknown", and that must
    # EN | not stop a setup run.
    # FR | Langue de l'interface, alimentee par input_select.vssp_language (le
    # FR | selecteur que le generateur de dashboards lit deja via son propre
    # FR | --locale). Toute valeur inconnue retombe sur l'anglais plutot que
    # FR | d'echouer : un selecteur jamais pose vaut « unknown », et cela ne
    # FR | doit pas interrompre une configuration.
    ap.add_argument("--locale", default=BASE_LOCALE,
                    help="Interface language for the published messages "
                         "(en/fr). Unknown values fall back to English.")
    args = ap.parse_args()

    locale = pick_locale(args.locale)
    client_id = (args.client_id or "").strip()
    secret = read_secret(args.secret_file)
    token = resolve_token(args)

    if not token:
        write_status(args.status_file, build_status(
            args.url, "", client_id, bool(secret),
            {**stated("error", locale), **say("no_token", locale)}))
        print("[ERR] no Home Assistant token", file=sys.stderr)
        return 1

    # EN | Read-only actions first: they never touch the config flow.
    # FR | Actions en lecture seule d'abord : elles ne touchent jamais au flow.
    if args.action in ("status", "calendars"):
        status = build_status(args.url, token, client_id, bool(secret))
        status.update(stated("connected" if status["connected"] else "idle",
                             locale))
        status.update(
            say("calendars_found", locale, n=len(status["calendars"]))
            if status["connected"]
            else say("no_calendar_yet", locale))
        write_status(args.status_file, status)
        print(json.dumps(status, indent=2, ensure_ascii=False))
        return 0

    if not client_id or not secret:
        write_status(args.status_file, build_status(
            args.url, token, client_id, bool(secret),
            {**stated("error", locale),
             **say("credentials_required", locale)}))
        print("[ERR] client id and/or secret missing", file=sys.stderr)
        return 1

    credential_id = ""
    registered = False
    try:
        if args.action in ("connect", "credentials"):
            credential_id, cred_msg = ensure_credentials(
                args.url, token, client_id, secret, args.name)
            registered = True
            print(f"[i] {cred_msg}")
        if args.action == "credentials":
            status = build_status(args.url, token, client_id, True, {
                "credentials_registered": registered,
                **stated("credentials_ok", locale),
                **say("credentials_ok", locale),
            })
            write_status(args.status_file, status)
            return 0

        res = start_flow(args.url, token, credential_id)
        flow_type = res.get("type")
        if flow_type in ("external", "external_step"):
            status = build_status(args.url, token, client_id, True, {
                "credentials_registered": True,
                **stated("awaiting_consent", locale),
                "flow_id": res.get("flow_id", ""),
                "auth_url": res.get("url", ""),
                **say("awaiting_consent", locale),
            })
            write_status(args.status_file, status)
            print(f"[i] consent url: {res.get('url', '')}")
            return 0
        if flow_type == "abort":
            reason = res.get("reason", "unknown")
            already = reason in ("already_configured", "single_instance_allowed")
            status = build_status(args.url, token, client_id, True, {
                "credentials_registered": True,
                **stated("connected" if already else "error", locale),
                **(say("already_linked", locale) if already
                   else say("flow_aborted", locale, reason=reason)),
            })
            write_status(args.status_file, status)
            return 0 if already else 1
        # EN | A plain form here means HA is asking something this script does
        # EN | not know how to answer — report it rather than guessing.
        # FR | Un formulaire simple ici signifie que HA demande quelque chose
        # FR | que ce script ne sait pas remplir — le signaler plutot que de
        # FR | deviner.
        status = build_status(args.url, token, client_id, True, {
            "credentials_registered": registered,
            **stated("error", locale),
            **say("unexpected_step", locale,
                  step=res.get("step_id"), type=flow_type),
        })
        write_status(args.status_file, status)
        return 1

    except (WSError, urllib.error.HTTPError, urllib.error.URLError,
            OSError, ValueError) as exc:
        detail = str(exc)
        if isinstance(exc, urllib.error.HTTPError):
            try:
                detail = f"HTTP {exc.code}: {exc.read().decode('utf-8')[:200]}"
            except OSError:
                detail = f"HTTP {exc.code}"
        write_status(args.status_file, build_status(
            args.url, token, client_id, bool(secret),
            {"credentials_registered": registered,
             **stated("error", locale),
             **say("failure", locale, detail=detail)}))
        print(f"[ERR] {detail}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
