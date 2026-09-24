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
# Visio Sapiens — vssp_ws.py
#
# EN | THE WEBSOCKET, IN ONE PLACE. Home Assistant exposes part of itself
# EN | only on its websocket API: application credentials, config flows and
# EN | — the reason this file now exists — the Lovelace RESOURCE registry.
# EN | None of those have a REST endpoint, and a storage-mode instance keeps
# EN | its resource list nowhere else.
# EN | The client below was written for vssp_google_setup.py and lived
# EN | inside it. A second caller (vssp_dependencies.py) would have meant a
# EN | second copy, and two copies of a hand-rolled protocol drift in the
# EN | worst possible way: quietly, and only on the instance you are not
# EN | looking at. So it moved here unchanged, and both scripts import it.
# FR | LE WEBSOCKET, A UN SEUL ENDROIT. Home Assistant n'expose une partie
# FR | de lui-meme que sur son API websocket : credentials applicatifs,
# FR | config flows et — la raison de l'existence de ce fichier — le
# FR | registre des RESSOURCES Lovelace. Aucun n'a de point d'acces REST, et
# FR | une instance en mode storage ne garde sa liste de ressources nulle
# FR | part ailleurs.
# FR | Le client ci-dessous a ete ecrit pour vssp_google_setup.py et vivait
# FR | dedans. Un second appelant (vssp_dependencies.py) aurait signifie une
# FR | seconde copie, et deux copies d'un protocole ecrit a la main divergent
# FR | de la pire maniere : en silence, et seulement sur l'instance qu'on ne
# FR | regarde pas. Il a donc demenage ici tel quel, et les deux scripts
# FR | l'importent.
#
# EN | WHY HAND-ROLLED — every script in this project is stdlib + pyyaml, so
# EN | that a Home Assistant OS box, where `pip install` is not a thing you
# EN | ask of a user, runs them exactly like the development pod does. This
# EN | speaks the few frames of RFC 6455 it needs: masked client text
# EN | frames, unmasked server frames, ping/pong. About 90 lines, and no new
# EN | dependency.
# FR | POURQUOI ECRIT A LA MAIN — chaque script de ce projet est stdlib +
# FR | pyyaml, pour qu'une machine Home Assistant OS, ou `pip install` n'est
# FR | pas une chose qu'on demande a un utilisateur, les execute exactement
# FR | comme le pod de developpement. Celui-ci parle les quelques trames de
# FR | la RFC 6455 dont il a besoin : trames texte client masquees, trames
# FR | serveur non masquees, ping/pong. Environ 90 lignes, zero dependance.
# ============================================================================
from __future__ import annotations

import base64
import json
import os
import socket
import ssl
import struct
import urllib.parse
from pathlib import Path

# ── EN | Minimal RFC 6455 client / FR | Client RFC 6455 minimal ──────────
class WSError(RuntimeError):
    pass


class MiniWS:
    """EN | Just enough WebSocket to talk to Home Assistant: connect, auth,
    EN | send a command, read its result. Text frames only.
    FR | Juste ce qu'il faut de WebSocket pour parler a Home Assistant :
    FR | connexion, auth, envoi d'une commande, lecture du resultat. Trames
    FR | texte uniquement."""

    def __init__(self, base_url: str, timeout: float = 20.0,
                 path: str = "/api/websocket",
                 bearer: str | None = None):
        parsed = urllib.parse.urlsplit(base_url)
        self.secure = parsed.scheme == "https"
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port or (443 if self.secure else 80)
        # EN | HA serves its websocket at /api/websocket regardless of any
        # EN | path prefix in the base url (the pod is always the root).
        # FR | HA sert son websocket sur /api/websocket quel que soit le
        # FR | prefixe de chemin de l'url de base (le pod est toujours la
        # FR | racine).
        # EN | Almost always /api/websocket. The exception is the
        # EN | Supervisor's proxy, which serves Home Assistant's own
        # EN | websocket at /core/websocket and lets a container inside the
        # EN | appliance authenticate with SUPERVISOR_TOKEN instead of a
        # EN | long-lived token somebody had to create by hand.
        # FR | Presque toujours /api/websocket. L exception est le proxy du
        # FR | Superviseur, qui sert le websocket de Home Assistant sur
        # FR | /core/websocket et permet a un conteneur de l appareil de
        # FR | s authentifier avec SUPERVISOR_TOKEN plutot qu avec un jeton
        # FR | longue duree que quelqu un a du creer a la main.
        self.path = path or "/api/websocket"
        # EN | THE PROXY'S OWN GATE, SEPARATE FROM HOME ASSISTANT'S.
        # EN | Wrong the first time this was written: SUPERVISOR_TOKEN was
        # EN | sent only inside the post-handshake `auth` message, the same
        # EN | way a long-lived token is. Home Assistant Core's own auth
        # EN | handler does not recognise it there and answered "Invalid
        # EN | access" - confirmed live, on the production box. The
        # EN | Supervisor's documentation says plainly that every endpoint
        # EN | it marks locked, GET /core/websocket included, wants its
        # EN | token "with an authorization header with a Bearer token" -
        # EN | an HTTP header on the upgrade request itself, a layer below
        # EN | anything Home Assistant's own websocket protocol carries.
        # EN | Once the Supervisor's proxy has let the request through on
        # EN | that header, Home Assistant's own `auth_required` /
        # EN | `auth` exchange still happens exactly as before - this
        # EN | header adds a gate, it does not replace one.
        # FR | LA PORTE DU PROXY, SEPAREE DE CELLE DE HOME ASSISTANT.
        # FR | Faux la premiere fois que ceci a ete ecrit : SUPERVISOR_TOKEN
        # FR | n etait envoye que dans le message `auth` d apres la
        # FR | poignee de main, comme un jeton longue duree. Le gestionnaire
        # FR | d authentification de Home Assistant Core ne le reconnait
        # FR | pas la et a repondu « Invalid access » - confirme en direct,
        # FR | sur la machine de production. La documentation du
        # FR | Superviseur dit clairement que chaque point d acces qu il
        # FR | marque verrouille, GET /core/websocket compris, veut son
        # FR | jeton « avec un en-tete d autorisation Bearer » - un en-tete
        # FR | HTTP sur la requete de mise a niveau elle-meme, une couche en
        # FR | dessous de tout ce que porte le protocole websocket de Home
        # FR | Assistant. Une fois le proxy du Superviseur franchi grace a
        # FR | cet en-tete, l echange `auth_required` / `auth` de Home
        # FR | Assistant a lieu exactement comme avant - cet en-tete ajoute
        # FR | une porte, il n en remplace aucune.
        self.bearer = bearer
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
        if self.bearer:
            handshake = handshake[:-2] + f"Authorization: Bearer {self.bearer}\r\n\r\n"
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




# ── EN | Token resolution / FR | Resolution du jeton ─────────────────────
# EN | --token > $HA_TOKEN > --token-file, the order every script in this
# EN | project follows. The placeholders are not accidents: an input_text
# EN | that has never been filled renders as "unknown", and a shell_command
# EN | happily passes that string along as if it were a credential.
# FR | --token > $HA_TOKEN > --token-file, l'ordre suivi par chaque script
# FR | de ce projet. Les valeurs sentinelles ne sont pas des accidents : un
# FR | input_text jamais rempli vaut « unknown », et un shell_command
# FR | transmet joyeusement cette chaine comme si c'etait un identifiant.
PLACEHOLDERS = ("", "unknown", "unavailable", "none", "None")


def resolve_token(token: str | None = None,
                  token_file: str = "/config/vssp/.ha_token") -> str | None:
    if token and token.strip() not in PLACEHOLDERS:
        return token.strip()
    env = os.environ.get("HA_TOKEN")
    if env and env.strip() not in PLACEHOLDERS:
        return env.strip()
    try:
        text = Path(token_file).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text if text and text not in PLACEHOLDERS else None


def connected(url: str, token: str, timeout: float = 20.0,
              path: str = "/api/websocket",
              bearer: str | None = None) -> MiniWS:
    """EN | Open and authenticate in one call — the caller closes it.
    EN | `bearer` is the Supervisor proxy's own HTTP-level gate; omit it
    EN | for a direct connection to Home Assistant's own /api/websocket,
    EN | which has no such gate.
    FR | Ouvre et authentifie en un appel — l'appelant referme.
    FR | `bearer` est la porte HTTP propre au proxy du Superviseur ; on
    FR | l'omet pour une connexion directe a /api/websocket de Home
    FR | Assistant, qui n'a pas cette porte."""
    ws = MiniWS(url, timeout=timeout, path=path, bearer=bearer)
    ws.connect()
    ws.authenticate(token)
    return ws
