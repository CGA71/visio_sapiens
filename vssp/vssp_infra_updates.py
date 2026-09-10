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
# Visio Sapiens — INFRASTRUCTURE updates probe and installer
#
# EN | WHY THIS FILE EXISTS
# EN | packages/vssp_updates.yaml opens by saying it adds no data source: it
# EN | reads the `update.*` entities Home Assistant already holds and only
# EN | splits them into families. That is true, and it is exactly why the
# EN | UPDATES screen could never see the layer underneath itself. Home
# EN | Assistant knows it has a Core update pending. It does not know the
# EN | Ubuntu host it runs on has six packages waiting and wants a reboot,
# EN | that k3s is two minor versions behind, or that the GitLab that
# EN | deploys it has shipped a security release. Those facts live on the
# EN | other side of the container boundary, and no entity carries them.
# EN | This script is that missing data source, and the ONLY one in the
# EN | project that reaches outside Home Assistant to get it.
# FR | POURQUOI CE FICHIER EXISTE
# FR | packages/vssp_updates.yaml s ouvre en disant qu il n ajoute aucune
# FR | source de donnees : il lit les entites `update.*` que Home Assistant
# FR | detient deja et se contente de les repartir en familles. C est vrai,
# FR | et c est precisement pourquoi l ecran MISES A JOUR ne pouvait pas
# FR | voir la couche sous lui-meme. Home Assistant sait qu une mise a jour
# FR | de Core l attend. Il ignore que l hote Ubuntu sur lequel il tourne a
# FR | six paquets en attente et reclame un redemarrage, que k3s a deux
# FR | versions mineures de retard, ou que le GitLab qui le deploie a publie
# FR | un correctif de securite. Ces faits vivent de l autre cote de la
# FR | frontiere du conteneur, et aucune entite ne les porte.
# FR | Ce script est cette source manquante, et la SEULE du projet qui sorte
# FR | de Home Assistant pour aller la chercher.
#
# ---------------------------------------------------------------------------
# EN | THE PRIVILEGE PROBLEM, AND WHY THE SAFE ANSWERS IT
# EN | Reading `apt list --upgradable` needs an account on the host.
# EN | Installing anything there needs sudo. Asking GitLab its version needs
# EN | a token. Home Assistant must never hold any of the three: everything
# EN | it reads becomes an entity state, written in clear text to
# EN | home-assistant_v2.db by the recorder and shown in Developer Tools to
# EN | any administrator. That is the same reasoning that gave the SAFE its
# EN | shape (see vault/policies/vssp-ha.hcl), applied to maintenance.
# EN | So the credentials live in the safe, under secret/vssp/infra/, and
# EN | THIS PROCESS reads them — not Home Assistant. They exist in the
# EN | memory of a python process for the length of one run, travel to ssh
# EN | or to an HTTPS call, and are never returned to the caller. Home
# EN | Assistant only ever sees what this script writes back: counts,
# EN | version strings and a status message. A shell_command that triggers
# EN | a run learns nothing a `ps` could not already tell it.
# EN | The token this script carries is a THIRD policy, vssp-maint, which
# EN | grants read on secret/data/vssp/infra/* and nothing else. It cannot
# EN | list the safe, cannot see accounts/ or apps/, and cannot write.
# FR | LE PROBLEME DES PRIVILEGES, ET POURQUOI LE COFFRE Y REPOND
# FR | Lire `apt list --upgradable` demande un compte sur l hote. Y
# FR | installer quoi que ce soit demande sudo. Demander sa version a
# FR | GitLab demande un jeton. Home Assistant ne doit jamais detenir aucun
# FR | des trois : tout ce qu il lit devient un etat d entite, ecrit en
# FR | clair dans home-assistant_v2.db par le recorder et montre dans les
# FR | Outils de developpement a n importe quel administrateur. C est le
# FR | raisonnement qui a donne sa forme au COFFRE (voir
# FR | vault/policies/vssp-ha.hcl), applique a la maintenance.
# FR | Les identifiants vivent donc dans le coffre, sous secret/vssp/infra/,
# FR | et c est CE PROCESSUS qui les lit — pas Home Assistant. Ils existent
# FR | dans la memoire d un processus python le temps d une execution, vont
# FR | vers ssh ou vers un appel HTTPS, et ne sont jamais rendus a
# FR | l appelant. Home Assistant ne voit que ce que ce script reecrit :
# FR | des decomptes, des versions et un message de statut. Un
# FR | shell_command qui declenche une execution n apprend rien qu un `ps`
# FR | ne lui dirait deja.
# FR | Le jeton que porte ce script est une TROISIEME policy, vssp-maint,
# FR | qui accorde la lecture sur secret/data/vssp/infra/* et rien d autre.
# FR | Elle ne peut pas lister le coffre, ne voit ni accounts/ ni apps/, et
# FR | n ecrit pas.
#
# ---------------------------------------------------------------------------
# EN | THE THREE TIERS — the same philosophy the other families already
# EN | follow, applied to things that can take the house offline.
# EN |   auto     may be installed unattended by the nightly pass. Reversible,
# EN |            or cheap enough that a bad one is a nuisance rather than an
# EN |            outage: host packages, the GitLab runner.
# EN |   manual   never installed unattended, whatever the switch says. One
# EN |            row, one button, one confirmation: GitLab, k3s, Vault,
# EN |            the host reboot.
# EN |   locked   reported and never installable from here at all.
# EN | The tier is a property of the COMPONENT, declared in the table below,
# EN | not a decision the dashboard makes. A card cannot promote a component
# EN | to auto by rendering it differently, and the nightly pass filters on
# EN | this field rather than on anything the UI sent it.
# FR | LES TROIS PALIERS — la philosophie que suivent deja les autres
# FR | familles, appliquee a des choses capables de mettre la maison a
# FR | l arret.
# FR |   auto     installable sans surveillance par la passe nocturne.
# FR |            Reversible, ou assez peu couteux pour qu un echec soit une
# FR |            genes plutot qu une panne : paquets de l hote, runner.
# FR |   manual   jamais installe sans surveillance, quoi que dise
# FR |            l interrupteur. Une ligne, un bouton, une confirmation :
# FR |            GitLab, k3s, Vault, le redemarrage de l hote.
# FR |   locked   remonte, et jamais installable d ici.
# FR | Le palier est une propriete du COMPOSANT, declaree dans la table plus
# FR | bas, pas une decision du dashboard. Une carte ne peut pas promouvoir
# FR | un composant en auto en l affichant autrement, et la passe nocturne
# FR | filtre sur ce champ plutot que sur quoi que ce soit envoye par l IHM.
#
# ---------------------------------------------------------------------------
# EN | USAGE
# FR | UTILISATION
#     python3 vssp_infra_updates.py --probe \
#         --out /config/www/vssp/infra_updates.json \
#         --status /config/www/vssp/infra_updates_status.json
#     python3 vssp_infra_updates.py --install os_packages --out ... --status ...
#     python3 vssp_infra_updates.py --install-auto --out ... --status ...
#     python3 vssp_infra_updates.py --probe --dry-run   # no safe, no ssh
#
# EN | Exit code is 0 when the run did what it was asked, 1 otherwise. The
# EN | status file always gets written, including on failure — a screen that
# EN | shows nothing is indistinguishable from a screen that was never asked.
# FR | Le code de sortie vaut 0 quand l execution a fait ce qu on lui a
# FR | demande, 1 sinon. Le fichier de statut est toujours ecrit, echec
# FR | compris — un ecran qui n affiche rien est indistinguable d un ecran a
# FR | qui l on n a jamais rien demande.
# ---------------------------------------------------------------------------
"""Visio Sapiens — infrastructure updates: probe and installer."""
import argparse
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE_LOCALE = "en"

# EN | Where the safe lives, and which entries this script may read. Both are
# EN | overridable on the command line so a second instance is a flag rather
# EN | than a fork of this file.
# FR | Ou vit le coffre, et quelles entrees ce script peut lire. Les deux sont
# FR | surchargeables en ligne de commande pour qu une seconde instance soit
# FR | une option plutot qu une copie de ce fichier.
DEFAULT_VAULT_ADDR = "http://192.168.1.11:8200"
VAULT_PREFIX = "secret/data/vssp/infra"

# EN | Entry names in the safe. Creating them is the SAFE screen's job — this
# EN | script only ever reads, and says which one is missing when it is.
# FR | Noms des entrees dans le coffre. Les creer est le travail de l ecran
# FR | COFFRE-FORT — ce script ne fait que lire, et dit laquelle manque le cas
# FR | echeant.
SECRET_HOST = "host_ssh"       # host, user, port, private_key
SECRET_SUDO = "host_sudo"      # password
SECRET_GITLAB = "gitlab"       # url, token

HTTP_TIMEOUT = 15
SSH_TIMEOUT = 120


# ═══════════════════════════════════════════════════════════════════════════
# EN | STATUS FILE — the machine form travels, the rendered form is a fallback
# FR | FICHIER DE STATUT — la forme machine voyage, le rendu est un repli
# ═══════════════════════════════════════════════════════════════════════════
#
# EN | Same contract as every other status file in the project: the page gets
# EN | `message_key` plus its variables and translates it in whatever language
# EN | its ?lang= says, and `message` is what to show if it cannot. A machine
# EN | token is never translated here.
# FR | Meme contrat que tout autre fichier de statut du projet : la page recoit
# FR | `message_key` et ses variables et le traduit dans la langue que dit son
# FR | ?lang=, et `message` est ce qu il faut afficher si elle ne peut pas. Un
# FR | jeton machine n est jamais traduit ici.
MESSAGES = {
    "probe.ok": "{total} update(s) pending on the infrastructure.",
    "probe.none": "Infrastructure up to date.",
    "probe.partial": "{total} update(s) pending; {failed} component(s) could not be probed.",
    "install.ok": "{name}: installed.",
    "install.none": "{name}: nothing to install.",
    "install.auto_ok": "{count} component(s) installed by the automatic pass.",
    "install.auto_none": "Automatic pass: nothing to install.",
    "error.secret_missing": "Safe entry vssp/infra/{name} is missing or unreadable.",
    "error.vault": "The safe answered {code} — check the vssp-maint token.",
    "error.no_token": "No maintenance token: /config/vssp/.vault_maint_token is missing.",
    "error.ssh": "The host refused the connection: {detail}",
    "error.no_transport": "No SSH transport available in this container (neither the ssh binary nor paramiko).",
    "error.tier": "{name} is a {tier} component: it is never installed unattended.",
    "error.unknown": "Unknown component: {name}.",
}


def status(key: str, **vars_) -> dict:
    template = MESSAGES.get(key, key)
    try:
        rendered = template.format(**vars_)
    except (KeyError, IndexError):
        rendered = template
    return {"message_key": key, "message_vars": vars_, "message": rendered}


def write_json(path: Path, payload: dict) -> None:
    """EN | Atomic write — a half-written JSON read by the console mid-run is
    EN | a parse error on screen, and the console polls this file every few
    EN | seconds by design.
    FR | Ecriture atomique — un JSON a moitie ecrit lu par la console en cours
    FR | d execution est une erreur d analyse a l ecran, et la console
    FR | interroge ce fichier toutes les quelques secondes, a dessein."""
    payload.setdefault("generated", _dt.datetime.now().isoformat(timespec="seconds"))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        os.replace(tmp, path)
    except OSError as exc:
        print(f"[warn] {path.name} not written: {exc}", file=sys.stderr)


# ═══════════════════════════════════════════════════════════════════════════
# EN | THE SAFE — read only, and only under secret/vssp/infra/
# FR | LE COFFRE — lecture seule, et seulement sous secret/vssp/infra/
# ═══════════════════════════════════════════════════════════════════════════
class VaultError(Exception):
    """EN | Carries the status dict to publish. FR | Porte le statut a publier."""

    def __init__(self, payload: dict):
        super().__init__(payload.get("message", "vault error"))
        self.payload = payload


class Safe:
    """EN | The maintenance half of the safe. Reads entries, caches them for
    EN | the length of one run, and never writes any of it to disk.
    FR | La moitie maintenance du coffre. Lit les entrees, les garde en cache
    FR | le temps d une execution, et n en ecrit jamais rien sur disque."""

    def __init__(self, addr: str, token: str):
        self.addr = addr.rstrip("/")
        self.token = token
        self._cache: dict[str, dict] = {}

    @classmethod
    def open(cls, addr: str, token_file: Path):
        # EN | The token file is deployed like .livebox.env — written by the
        # EN | pipeline with umask 077, never versioned. Its absence is a
        # EN | configuration state, not a crash.
        # FR | Le fichier de jeton est deploye comme .livebox.env — ecrit par
        # FR | le pipeline avec umask 077, jamais versionne. Son absence est un
        # FR | etat de configuration, pas un plantage.
        token = ""
        if token_file.is_file():
            token = token_file.read_text(encoding="utf-8").strip()
        if not token:
            raise VaultError(status("error.no_token"))
        return cls(addr, token)

    def read(self, name: str) -> dict:
        if name in self._cache:
            return self._cache[name]
        url = f"{self.addr}/v1/{VAULT_PREFIX}/{name}"
        req = urllib.request.Request(url, headers={"X-Vault-Token": self.token})
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # EN | 403 means the token is wrong or carries the wrong policy;
            # EN | 404 means the entry was never created. Both are things the
            # EN | operator fixes in the SAFE screen, so name which.
            # FR | 403 : jeton faux ou mauvaise policy ; 404 : entree jamais
            # FR | creee. Les deux se corrigent dans l ecran COFFRE-FORT, donc
            # FR | dire laquelle.
            if exc.code == 404:
                raise VaultError(status("error.secret_missing", name=name)) from exc
            raise VaultError(status("error.vault", code=exc.code)) from exc
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise VaultError(status("error.vault", code=str(exc))) from exc
        data = (body.get("data") or {}).get("data") or {}
        if not data:
            raise VaultError(status("error.secret_missing", name=name))
        self._cache[name] = data
        return data


# ═══════════════════════════════════════════════════════════════════════════
# EN | SSH TRANSPORT — the ssh binary if the image has one, paramiko if not
# FR | TRANSPORT SSH — le binaire ssh si l image en a un, paramiko sinon
# ═══════════════════════════════════════════════════════════════════════════
#
# EN | The Home Assistant container is not guaranteed to ship an ssh client,
# EN | and this script must not be the reason a deployment fails. So it tries
# EN | the binary, falls back to paramiko (pure python, pip-installable the
# EN | same way the deploy job already installs ruamel.yaml), and if neither
# EN | is there says exactly that instead of a traceback about FileNotFound.
# FR | Le conteneur Home Assistant n embarque pas forcement de client ssh, et
# FR | ce script ne doit pas etre la raison d un deploiement en echec. Il
# FR | essaie donc le binaire, se rabat sur paramiko (python pur,
# FR | pip-installable comme le job de deploiement installe deja
# FR | ruamel.yaml), et si aucun des deux n est la, le dit exactement au lieu
# FR | d une trace sur FileNotFound.
class Host:
    """EN | One authenticated shell on the host, for the length of one run.
    FR | Un shell authentifie sur l hote, le temps d une execution."""

    def __init__(self, creds: dict, sudo_password: str = ""):
        self.host = creds.get("host") or "127.0.0.1"
        self.user = creds.get("user") or "root"
        self.port = int(creds.get("port") or 22)
        self.key = creds.get("private_key") or ""
        self.sudo_password = sudo_password
        self._key_path: Path | None = None
        self._client = None

    # ── EN | Lifecycle / FR | Cycle de vie ──────────────────────────────
    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()
        return False

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
        # EN | The key never outlives the run. It is written 0600 into the
        # EN | private tmp of this process only because the ssh binary cannot
        # EN | read a key from memory; paramiko can, and skips this entirely.
        # FR | La cle ne survit pas a l execution. Elle n est ecrite en 0600
        # FR | dans le tmp privé de ce processus que parce que le binaire ssh
        # FR | ne sait pas lire une cle en memoire ; paramiko, si, et saute
        # FR | entierement cette etape.
        if self._key_path and self._key_path.exists():
            try:
                self._key_path.unlink()
            except OSError:
                pass
            self._key_path = None

    # ── EN | Running a command / FR | Executer une commande ─────────────
    def run(self, command: str, sudo: bool = False) -> tuple[int, str, str]:
        if sudo:
            # EN | -S reads the password from stdin, -p '' keeps the prompt out
            # EN | of stderr so a caller parsing stderr does not see it.
            # FR | -S lit le mot de passe sur stdin, -p '' garde l invite hors
            # FR | de stderr pour qu un appelant qui analyse stderr ne la voie
            # FR | pas.
            command = f"sudo -S -p '' {command}"
        if shutil.which("ssh"):
            return self._run_binary(command, sudo)
        return self._run_paramiko(command, sudo)

    def _ensure_key_file(self) -> Path:
        if self._key_path is not None:
            return self._key_path
        import tempfile
        fd, name = tempfile.mkstemp(prefix="vssp_maint_", suffix=".key")
        os.close(fd)
        path = Path(name)
        path.chmod(0o600)
        key = self.key if self.key.endswith("\n") else self.key + "\n"
        # EN | newline="" so the bytes written are exactly the bytes read from
        # EN | the safe. Python's default text mode rewrites \n to the
        # EN | platform separator, and OpenSSH rejects a CRLF private key with
        # EN | "error in libcrypto" — a message that names the crypto library
        # EN | rather than the line endings that actually broke it.
        # FR | newline="" pour que les octets ecrits soient exactement ceux lus
        # FR | dans le coffre. Le mode texte de Python reecrit \n vers le
        # FR | separateur de la plateforme, et OpenSSH rejette une cle privee
        # FR | en CRLF sur « error in libcrypto » — un message qui nomme la
        # FR | bibliotheque de chiffrement plutot que les fins de ligne qui ont
        # FR | reellement casse la lecture.
        path.write_text(key, encoding="utf-8", newline="")
        self._key_path = path
        return path

    def _run_binary(self, command: str, sudo: bool) -> tuple[int, str, str]:
        key_path = self._ensure_key_file()
        argv = [
            "ssh", "-i", str(key_path),
            "-p", str(self.port),
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", f"ConnectTimeout={HTTP_TIMEOUT}",
            f"{self.user}@{self.host}", command,
        ]
        try:
            proc = subprocess.run(
                argv, input=(self.sudo_password + "\n") if sudo else "",
                capture_output=True, text=True, timeout=SSH_TIMEOUT)
        except (OSError, subprocess.SubprocessError) as exc:
            raise VaultError(status("error.ssh", detail=str(exc))) from exc
        return proc.returncode, proc.stdout, proc.stderr

    def _run_paramiko(self, command: str, sudo: bool) -> tuple[int, str, str]:
        try:
            import paramiko  # noqa: F401
        except ImportError as exc:
            raise VaultError(status("error.no_transport")) from exc
        import io
        import paramiko
        if self._client is None:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            pkey = None
            for loader in (paramiko.Ed25519Key, paramiko.RSAKey,
                           paramiko.ECDSAKey):
                try:
                    pkey = loader.from_private_key(io.StringIO(self.key))
                    break
                except Exception:
                    continue
            if pkey is None:
                raise VaultError(status("error.ssh",
                                        detail="unsupported private key format"))
            try:
                client.connect(self.host, port=self.port, username=self.user,
                               pkey=pkey, timeout=HTTP_TIMEOUT,
                               allow_agent=False, look_for_keys=False)
            except Exception as exc:
                raise VaultError(status("error.ssh", detail=str(exc))) from exc
            self._client = client
        stdin, stdout, stderr = self._client.exec_command(command,
                                                          timeout=SSH_TIMEOUT)
        if sudo:
            stdin.write(self.sudo_password + "\n")
            stdin.flush()
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        return stdout.channel.recv_exit_status(), out, err


# ═══════════════════════════════════════════════════════════════════════════
# EN | UPSTREAM VERSIONS — what the latest release actually is
# FR | VERSIONS AMONT — quelle est reellement la derniere version
# ═══════════════════════════════════════════════════════════════════════════
#
# EN | Every call here is anonymous and read-only, and every one of them is
# EN | allowed to fail: an instance with no outbound network still gets a
# EN | complete INSTALLED column, and the component simply reports "unknown"
# EN | upstream rather than disappearing from the screen.
# FR | Chaque appel ici est anonyme et en lecture seule, et chacun a le droit
# FR | d echouer : une instance sans reseau sortant garde une colonne INSTALLE
# FR | complete, et le composant remonte un amont « inconnu » plutot que de
# FR | disparaitre de l ecran.
def http_json(url: str, headers: dict | None = None) -> dict | list | None:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def github_latest(repo: str) -> str:
    data = http_json(f"https://api.github.com/repos/{repo}/releases/latest",
                     {"Accept": "application/vnd.github+json",
                      "User-Agent": "visio-sapiens"})
    if isinstance(data, dict):
        return (data.get("tag_name") or "").lstrip("v")
    return ""


def apt_policy(host: "Host", package: str) -> tuple[str, str]:
    """EN | (installed, candidate) for one apt package, or ('','') when the
    EN | host does not know it.
    EN | LC_ALL=C IS LOAD-BEARING. apt-cache translates its own field labels:
    EN | the same command prints "Installed:/Candidate:" on an English host and
    EN | "Installé :/Candidat :" on this one. Parsing the labels without
    EN | pinning the locale gives a probe that works on the machine it was
    EN | written on and reports every package as unknown everywhere else.
    FR | (installe, candidat) pour un paquet apt, ou ('','') quand l hote ne le
    FR | connait pas.
    FR | LC_ALL=C EST PORTEUR. apt-cache traduit ses propres libelles de
    FR | champs : la meme commande affiche « Installed:/Candidate: » sur un
    FR | hote anglais et « Installé :/Candidat : » sur celui-ci. Analyser les
    FR | libelles sans figer la langue donne une sonde qui marche sur la
    FR | machine ou elle a ete ecrite et remonte partout ailleurs un paquet
    FR | inconnu."""
    code, out, _ = host.run(f"LC_ALL=C apt-cache policy {package} 2>/dev/null")
    if code != 0 or not out.strip():
        return "", ""
    installed = candidate = ""
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("Installed:"):
            installed = line.split(":", 1)[1].strip()
        elif line.startswith("Candidate:"):
            candidate = line.split(":", 1)[1].strip()
    # EN | apt says "(none)" for a package it knows but has not installed.
    # FR | apt dit « (none) » pour un paquet qu il connait sans l avoir
    # FR | installe.
    if installed in ("(none)", ""):
        return "", candidate if candidate != "(none)" else ""
    return installed, ("" if candidate == "(none)" else candidate)


def dockerhub_latest(repo: str, pattern: str = r"^\d+\.\d+\.\d+$") -> str:
    """EN | Highest semver tag on Docker Hub. Tags are strings and sort like
    EN | strings, so 1.20.0 would beat 1.9.0 — compare as tuples of ints.
    FR | Plus haut tag semver sur Docker Hub. Les tags sont des chaines et se
    FR | trient comme telles, donc 1.20.0 battrait 1.9.0 — comparer en
    FR | tuples d entiers."""
    data = http_json(
        f"https://hub.docker.com/v2/repositories/{repo}/tags"
        "?page_size=100&ordering=last_updated")
    if not isinstance(data, dict):
        return ""
    rx = re.compile(pattern)
    best: tuple = ()
    best_name = ""
    for item in data.get("results") or []:
        name = str(item.get("name") or "")
        if not rx.match(name):
            continue
        try:
            parts = tuple(int(p) for p in name.split("."))
        except ValueError:
            continue
        if parts > best:
            best, best_name = parts, name
    return best_name


def version_tuple(value: str) -> tuple:
    return tuple(int(p) for p in re.findall(r"\d+", value or "")) or (0,)


def is_behind(installed: str, latest: str) -> bool:
    """EN | Only ever answers True on a confident comparison. An empty or
    EN | unparsable upstream is not evidence of being up to date, but it is
    EN | not evidence of being behind either — and a false "update pending"
    EN | on a k3s row is how someone reboots a cluster for nothing.
    FR | Ne repond True que sur une comparaison sure. Un amont vide ou
    FR | illisible ne prouve pas qu on est a jour, mais ne prouve pas non plus
    FR | qu on est en retard — et un faux « mise a jour en attente » sur une
    FR | ligne k3s, c est quelqu un qui redemarre un cluster pour rien."""
    if not installed or not latest:
        return False
    return version_tuple(latest) > version_tuple(installed)


# ═══════════════════════════════════════════════════════════════════════════
# EN | THE COMPONENTS
# FR | LES COMPOSANTS
# ═══════════════════════════════════════════════════════════════════════════
#
# EN | One entry per thing the screen reports. `tier` decides what the nightly
# EN | pass is allowed to touch; `name_key` is a locale key, never a label —
# EN | this file ships no user-facing English.
# FR | Une entree par chose que l ecran remonte. `tier` decide de ce que la
# FR | passe nocturne a le droit de toucher ; `name_key` est une cle de
# FR | langue, jamais un libelle — ce fichier ne livre aucun anglais destine a
# FR | l utilisateur.
COMPONENTS = [
    {"key": "os_packages",   "name_key": "admin.updates_infra_os_packages",
     "tier": "auto",   "icon": "mdi:ubuntu"},
    {"key": "os_reboot",     "name_key": "admin.updates_infra_os_reboot",
     "tier": "manual", "icon": "mdi:restart-alert"},
    {"key": "k3s",           "name_key": "admin.updates_infra_k3s",
     "tier": "locked", "icon": "mdi:kubernetes"},
    {"key": "gitlab_runner", "name_key": "admin.updates_infra_gitlab_runner",
     "tier": "auto",   "icon": "mdi:rocket-launch-outline"},
    {"key": "gitlab",        "name_key": "admin.updates_infra_gitlab",
     "tier": "manual", "icon": "mdi:gitlab"},
    {"key": "vault",         "name_key": "admin.updates_infra_vault",
     "tier": "locked", "icon": "mdi:safe"},
    {"key": "docker_images", "name_key": "admin.updates_infra_docker_images",
     "tier": "locked", "icon": "mdi:docker"},
]
BY_KEY = {c["key"]: c for c in COMPONENTS}

# EN | apt packages that have a component row of their own. They are excluded
# EN | from the host-packages row so nothing is counted twice, and from the
# EN | host-packages upgrade so a manual-tier component is never installed by
# EN | the auto tier through the side door.
# FR | Paquets apt qui ont leur propre ligne de composant. Ils sont exclus de
# FR | la ligne des paquets de l hote pour que rien ne soit compte deux fois,
# FR | et de sa mise a jour pour qu un composant de palier manuel ne soit
# FR | jamais installe par le palier auto en passant par la porte de service.
OWNED_PACKAGES = {"gitlab-ce", "gitlab-ee", "gitlab-runner"}


def blank(component: dict, **over) -> dict:
    row = {
        "key": component["key"],
        "name_key": component["name_key"],
        "tier": component["tier"],
        "icon": component["icon"],
        "installed": "",
        "latest": "",
        "pending": False,
        "count": 0,
        "detail": [],
        "probed": True,
    }
    row.update(over)
    return row


# ── EN | Probes, one per component / FR | Sondes, une par composant ──────
def probe_os_packages(host: Host, comp: dict) -> dict:
    # EN | `apt list --upgradable` writes its "Listing..." header to stderr
    # EN | and the packages to stdout, which is why stdout alone is parsed.
    # EN | -qq keeps even that header away on most releases; both are handled.
    # FR | `apt list --upgradable` ecrit son en-tete « Listing... » sur stderr
    # FR | et les paquets sur stdout, d ou l analyse de stdout seul. -qq
    # FR | supprime meme cet en-tete sur la plupart des versions ; les deux cas
    # FR | sont traites.
    code, out, err = host.run("apt list --upgradable -qq 2>/dev/null")
    if code != 0:
        return blank(comp, probed=False, detail=[err.strip()[:200]])
    lines = [ln.strip() for ln in out.splitlines()
             if ln.strip() and "/" in ln and not ln.startswith("Listing")]
    # EN | A security package is one whose POCKET ends in -security
    # EN | (noble-security, bookworm-security...), which is a different field
    # EN | from the package name. Testing the whole line for the substring
    # EN | would count libapache2-mod-security as a security update on any
    # EN | host that has it, and that number is the one the HOME upgrade
    # EN | button turns orange on.
    # FR | Un paquet de securite est celui dont la POCHE finit en -security
    # FR | (noble-security, bookworm-security...), ce qui est un champ
    # FR | different du nom du paquet. Tester la ligne entiere sur la
    # FR | sous-chaine compterait libapache2-mod-security comme une mise a
    # FR | jour de securite sur tout hote qui l a, et ce nombre est celui sur
    # FR | lequel le bouton UPGRADE de HOME passe a l orange.
    def _pocket(line: str) -> str:
        after = line.split("/", 1)[1] if "/" in line else ""
        return after.split(" ", 1)[0] if after else ""

    security = [ln for ln in lines if _pocket(ln).endswith("-security")]
    names = [ln.split("/", 1)[0] for ln in lines]
    # EN | GitLab and the runner are apt packages too, and each already has a
    # EN | row of its own further down. Left in here they would be counted
    # EN | twice, and the family total — the one number the ADMIN menu shows —
    # EN | would overstate the work waiting. They are removed from this row,
    # EN | not from the upgrade: `apt-get upgrade` still installs them, which
    # EN | is exactly why gitlab-ce must not be reachable from the auto tier
    # EN | by that back door. See install_os_packages.
    # FR | GitLab et le runner sont aussi des paquets apt, et chacun a deja sa
    # FR | ligne plus bas. Laisses ici, ils seraient comptes deux fois, et le
    # FR | total de la famille — le seul nombre qu affiche le menu ADMIN —
    # FR | exagererait le travail en attente. Ils sont retires de cette ligne,
    # FR | pas de la mise a jour : `apt-get upgrade` les installe toujours,
    # FR | et c est precisement pourquoi gitlab-ce ne doit pas devenir
    # FR | joignable depuis le palier auto par cette porte derobee. Voir
    # FR | install_os_packages.
    names = [n for n in names if n not in OWNED_PACKAGES]
    lines = [ln for ln in lines if ln.split("/", 1)[0] not in OWNED_PACKAGES]
    security = [ln for ln in security if ln.split("/", 1)[0] not in OWNED_PACKAGES]
    return blank(
        comp,
        installed=str(len(lines)),
        latest="",
        pending=bool(lines),
        count=len(lines),
        # EN | The security subset is the number that decides whether tonight
        # EN | is soon enough. It rides in the row rather than in a component
        # EN | of its own, because it is the same apt transaction.
        # FR | Le sous-ensemble securite est le nombre qui decide si cette nuit
        # FR | suffit. Il voyage dans la ligne plutot que dans un composant a
        # FR | lui, parce que c est la meme transaction apt.
        security=len(security),
        detail=names[:40],
    )


def probe_os_reboot(host: Host, comp: dict) -> dict:
    code, out, _ = host.run(
        "test -f /var/run/reboot-required && echo yes || echo no")
    if code != 0:
        return blank(comp, probed=False)
    needed = out.strip().endswith("yes")
    pkgs: list[str] = []
    if needed:
        _c, po, _e = host.run("cat /var/run/reboot-required.pkgs 2>/dev/null")
        pkgs = [p.strip() for p in po.splitlines() if p.strip()]
    return blank(comp, installed="", latest="", pending=needed,
                 count=1 if needed else 0, detail=pkgs[:40])


def probe_k3s(host: Host, comp: dict) -> dict:
    code, out, _ = host.run("k3s --version 2>/dev/null | head -1")
    if code != 0 or not out.strip():
        return blank(comp, probed=False)
    m = re.search(r"v?(\d+\.\d+\.\d+)", out)
    installed = m.group(1) if m else ""
    latest = github_latest("k3s-io/k3s")
    # EN | k3s tags read v1.36.2+k3s1 — the +k3s suffix is a build of the same
    # EN | Kubernetes version and must not be compared as a fourth number.
    # FR | Les tags k3s se lisent v1.36.2+k3s1 — le suffixe +k3s est une
    # FR | compilation de la meme version de Kubernetes et ne doit pas etre
    # FR | compare comme un quatrieme nombre.
    latest = latest.split("+")[0]
    return blank(comp, installed=installed, latest=latest,
                 pending=is_behind(installed, latest),
                 count=1 if is_behind(installed, latest) else 0)


def probe_apt_package(host: Host, comp: dict, packages: tuple[str, ...],
                      fallback_cmd: str = "",
                      fallback_rx: str = "") -> dict:
    """EN | An apt-installed component. The upstream version is the apt
    EN | CANDIDATE, not a release feed: the host is already subscribed to the
    EN | vendor's repository, so the candidate is by definition the version
    EN | this machine would actually get — and it stays right on a pinned or
    EN | held package, which an upstream API cannot know about.
    FR | Un composant installe par apt. La version amont est le CANDIDAT apt,
    FR | pas un flux de releases : l hote est deja abonne au depot de
    FR | l editeur, le candidat est donc par definition la version que cette
    FR | machine obtiendrait reellement — et il reste juste sur un paquet
    FR | epingle ou gele, ce qu une API amont ne peut pas savoir."""
    for package in packages:
        installed, candidate = apt_policy(host, package)
        if installed:
            behind = is_behind(installed, candidate)
            return blank(comp, installed=installed, latest=candidate,
                         pending=behind, count=1 if behind else 0,
                         detail=[package], package=package)
    # EN | Not an apt package here — a containerised or hand-installed
    # EN | instance. Fall back to asking the binary, which at least fills the
    # EN | INSTALLED column instead of dropping the row.
    # FR | Pas un paquet apt ici — instance conteneurisee ou installee a la
    # FR | main. Se rabattre sur le binaire, ce qui remplit au moins la colonne
    # FR | INSTALLE au lieu de faire disparaitre la ligne.
    if fallback_cmd:
        code, out, _ = host.run(fallback_cmd)
        if code == 0 and out.strip():
            m = re.search(fallback_rx, out)
            if m:
                return blank(comp, installed=m.group(1), latest="",
                             pending=False, count=0)
    return blank(comp, probed=False)


def probe_gitlab_runner(host: Host, comp: dict) -> dict:
    return probe_apt_package(
        host, comp, ("gitlab-runner",),
        fallback_cmd="gitlab-runner --version 2>/dev/null",
        fallback_rx=r"Version:\s*([0-9][^\s]*)")


def probe_gitlab(host: Host, safe: Safe | None, comp: dict) -> dict:
    # EN | Community edition first, then enterprise — an instance runs one or
    # EN | the other, never both.
    # FR | Edition communautaire d abord, puis entreprise — une instance fait
    # FR | tourner l une ou l autre, jamais les deux.
    row = probe_apt_package(host, comp, ("gitlab-ce", "gitlab-ee"))
    if row["probed"]:
        return row
    # EN | Not installed by apt: ask the instance itself. This is the only
    # EN | path that needs a token, and it exists for a containerised GitLab —
    # EN | on a host where GitLab is a package, no secret is involved at all.
    # FR | Pas installe par apt : demander a l instance elle-meme. C est le
    # FR | seul chemin qui reclame un jeton, et il existe pour un GitLab
    # FR | conteneurise — sur un hote ou GitLab est un paquet, aucun secret
    # FR | n entre en jeu.
    if safe is None:
        return blank(comp, probed=False)
    try:
        creds = safe.read(SECRET_GITLAB)
    except VaultError:
        # EN | No GitLab entry in the safe is a normal state on an instance
        # EN | that has no GitLab. The row stays, unprobed, and says so.
        # FR | Pas d entree GitLab dans le coffre est un etat normal sur une
        # FR | instance sans GitLab. La ligne reste, non sondee, et le dit.
        return blank(comp, probed=False)
    url = (creds.get("url") or "").rstrip("/")
    token = creds.get("token") or ""
    if not url or not token:
        return blank(comp, probed=False)
    data = http_json(f"{url}/api/v4/version", {"PRIVATE-TOKEN": token})
    if not isinstance(data, dict):
        return blank(comp, probed=False)
    installed = str(data.get("version") or "")
    return blank(comp, installed=installed, latest="",
                 pending=False, count=0)


def probe_vault(host: Host, comp: dict) -> dict:
    # EN | Vault runs as a docker container here, so its version is the image
    # EN | tag rather than anything a package manager knows.
    # FR | Vault tourne en conteneur docker ici, sa version est donc le tag de
    # FR | l image plutot que quelque chose que connaitrait un gestionnaire de
    # FR | paquets.
    code, out, _ = host.run(
        "docker ps --filter name=vault --format '{{.Image}}' 2>/dev/null | head -1")
    if code != 0 or not out.strip():
        return blank(comp, probed=False)
    image = out.strip()
    installed = image.split(":", 1)[1] if ":" in image else ""
    latest = dockerhub_latest("hashicorp/vault")
    return blank(comp, installed=installed, latest=latest,
                 pending=is_behind(installed, latest),
                 count=1 if is_behind(installed, latest) else 0,
                 detail=[image])


def probe_docker_images(host: Host, comp: dict) -> dict:
    """EN | Every other running container, reported as a list rather than as a
    EN | comparison: an image pinned to `latest` has no version to be behind,
    EN | and one pinned to a digest is deliberately frozen. The row says what
    EN | is running; deciding is the operator's.
    FR | Tout autre conteneur en marche, remonte comme une liste plutot que
    FR | comme une comparaison : une image epinglee sur `latest` n a pas de
    FR | version a avoir en retard, et une image epinglee sur une empreinte est
    FR | figee volontairement. La ligne dit ce qui tourne ; decider revient a
    FR | l operateur."""
    code, out, _ = host.run(
        "docker ps --format '{{.Names}} {{.Image}}' 2>/dev/null")
    if code != 0:
        return blank(comp, probed=False)
    rows = [ln.strip() for ln in out.splitlines() if ln.strip()]
    floating = [r for r in rows if r.endswith(":latest") or ":" not in r.split(" ", 1)[-1]]
    return blank(comp, installed=str(len(rows)), latest="",
                 pending=False, count=0, detail=rows[:40],
                 floating=len(floating))


# ── EN | Installers / FR | Installateurs ────────────────────────────────
#
# EN | Each returns (ok, detail). None of them is reachable for a component
# EN | whose tier forbids it — that check happens in install_one, once, rather
# EN | than being repeated and eventually forgotten in one of these.
# FR | Chacun renvoie (ok, detail). Aucun n est joignable pour un composant
# FR | dont le palier l interdit — ce controle a lieu dans install_one, une
# FR | fois, plutot que d etre repete puis oublie dans l un d eux.
def install_os_packages(host: Host) -> tuple[bool, str]:
    """EN | Upgrade the host packages — NAMING EACH ONE, rather than running a
    EN | bare `apt-get upgrade`.
    EN | The bare form is the obvious version and it is wrong here: it would
    EN | also upgrade gitlab-ce, a manual-tier component, in the middle of an
    EN | unattended three-in-the-morning pass. The tier would be enforced
    EN | everywhere in this file except in the one command that actually
    EN | installs things. Listing the packages keeps the promise the tier
    EN | makes.
    FR | Mettre a jour les paquets de l hote — EN LES NOMMANT UN A UN, plutot
    FR | qu un `apt-get upgrade` nu.
    FR | La forme nue est la version evidente et elle est fausse ici : elle
    FR | mettrait aussi a jour gitlab-ce, composant de palier manuel, au milieu
    FR | d une passe sans surveillance a trois heures du matin. Le palier
    FR | serait respecte partout dans ce fichier sauf dans la seule commande
    FR | qui installe reellement. Nommer les paquets tient la promesse que fait
    FR | le palier."""
    code, out, err = host.run("apt list --upgradable -qq 2>/dev/null")
    if code != 0:
        return False, (err or out).strip()[-400:]
    names = [ln.strip().split("/", 1)[0] for ln in out.splitlines()
             if ln.strip() and "/" in ln and not ln.startswith("Listing")]
    names = [n for n in names if n and n not in OWNED_PACKAGES]
    if not names:
        return True, "nothing to upgrade"
    # EN | DEBIAN_FRONTEND keeps a package that wants to ask a question from
    # EN | hanging the run for ever; the confdef/confold pair keeps a modified
    # EN | config file rather than replacing it behind the operator's back.
    # FR | DEBIAN_FRONTEND empeche un paquet qui veut poser une question de
    # FR | bloquer l execution indefiniment ; le couple confdef/confold
    # FR | conserve un fichier de configuration modifie plutot que de le
    # FR | remplacer dans le dos de l operateur.
    cmd = ("DEBIAN_FRONTEND=noninteractive apt-get -y "
           "-o Dpkg::Options::=--force-confdef "
           "-o Dpkg::Options::=--force-confold install --only-upgrade "
           + " ".join(names))
    code, out, err = host.run(cmd, sudo=True)
    return code == 0, (err or out).strip()[-400:]


def install_gitlab_runner(host: Host) -> tuple[bool, str]:
    cmd = ("DEBIAN_FRONTEND=noninteractive apt-get -y "
           "install --only-upgrade gitlab-runner")
    code, out, err = host.run(cmd, sudo=True)
    return code == 0, (err or out).strip()[-400:]


def install_os_reboot(host: Host) -> tuple[bool, str]:
    # EN | Fire and forget, on purpose. `shutdown -r +1` returns immediately
    # EN | and the host goes down a minute later, which is the only way this
    # EN | can report success: a reboot that took the ssh session with it looks
    # EN | exactly like a failed command.
    # FR | On lance et on oublie, a dessein. `shutdown -r +1` rend la main
    # FR | immediatement et l hote tombe une minute plus tard, seule facon pour
    # FR | ceci de rapporter un succes : un redemarrage qui emporte la session
    # FR | ssh ressemble exactement a une commande en echec.
    code, out, err = host.run("shutdown -r +1 'Visio Sapiens maintenance'",
                              sudo=True)
    return code == 0, (err or out).strip()[-400:]


def install_gitlab(host: Host) -> tuple[bool, str]:
    # EN | GitLab upgrades itself through its own package: apt runs the
    # EN | reconfigure and the migrations. It is a manual-tier component
    # EN | because that takes minutes, restarts every GitLab service, and
    # EN | wants a backup taken first — not because apt cannot do it.
    # FR | GitLab se met a jour par son propre paquet : apt enchaine la
    # FR | reconfiguration et les migrations. C est un composant de palier
    # FR | manuel parce que cela prend des minutes, redemarre tous les
    # FR | services GitLab et reclame une sauvegarde prealable — pas parce
    # FR | qu apt ne saurait pas le faire.
    for package in ("gitlab-ce", "gitlab-ee"):
        installed, _cand = apt_policy(host, package)
        if installed:
            cmd = ("DEBIAN_FRONTEND=noninteractive apt-get -y "
                   f"install --only-upgrade {package}")
            code, out, err = host.run(cmd, sudo=True)
            return code == 0, (err or out).strip()[-400:]
    return False, "gitlab-ce/gitlab-ee is not an apt package on this host"


# EN | Which key does what, in one table. A component with no entry here is
# EN | reported and never installed — the `locked` tier — and that is derived
# EN | from this mapping plus the tier field rather than from a second list
# EN | that would drift out of step with it.
# FR | Quelle cle fait quoi, en une table. Un composant sans entree ici est
# FR | remonte et jamais installe — le palier `locked` — et cela se deduit de
# FR | cette table plus du champ tier, plutot que d une seconde liste qui
# FR | finirait par diverger.
INSTALLERS = {
    "os_packages": install_os_packages,
    "gitlab_runner": install_gitlab_runner,
    "gitlab": install_gitlab,
    "os_reboot": install_os_reboot,
}


# ═══════════════════════════════════════════════════════════════════════════
# EN | RUNS
# FR | EXECUTIONS
# ═══════════════════════════════════════════════════════════════════════════
def open_host(safe: Safe) -> Host:
    creds = safe.read(SECRET_HOST)
    sudo = ""
    try:
        sudo = (safe.read(SECRET_SUDO) or {}).get("password") or ""
    except VaultError:
        # EN | A host whose account is NOPASSWD needs no sudo entry, and the
        # EN | probe needs no sudo at all. Only an install will notice.
        # FR | Un hote dont le compte est NOPASSWD n a pas besoin d entree
        # FR | sudo, et la sonde n a besoin d aucun sudo. Seule une
        # FR | installation le remarquera.
        pass
    return Host(creds, sudo)


def run_probe(safe: Safe | None, out_path: Path) -> dict:
    rows: list[dict] = []
    host: Host | None = None
    try:
        if safe is not None:
            host = open_host(safe)
        if host is not None:
            with host:
                rows.append(probe_os_packages(host, BY_KEY["os_packages"]))
                rows.append(probe_os_reboot(host, BY_KEY["os_reboot"]))
                rows.append(probe_k3s(host, BY_KEY["k3s"]))
                rows.append(probe_gitlab_runner(host, BY_KEY["gitlab_runner"]))
                rows.append(probe_gitlab(host, safe, BY_KEY["gitlab"]))
                rows.append(probe_vault(host, BY_KEY["vault"]))
                rows.append(probe_docker_images(host, BY_KEY["docker_images"]))
        else:
            for comp in COMPONENTS:
                rows.append(blank(comp, probed=False))
    finally:
        if host is not None:
            host.close()

    # EN | Order the rows the way the table declares them rather than the way
    # EN | they finished, so the screen does not reshuffle between runs.
    # FR | Ordonner les lignes comme la table les declare plutot que comme
    # FR | elles se sont terminees, pour que l ecran ne se reordonne pas d une
    # FR | execution a l autre.
    order = {c["key"]: i for i, c in enumerate(COMPONENTS)}
    rows.sort(key=lambda r: order.get(r["key"], 99))

    total = sum(r["count"] for r in rows)
    payload = {
        "ok": True,
        "components": rows,
        "counts": {
            "total": total,
            "auto": sum(r["count"] for r in rows if r["tier"] == "auto"),
            "manual": sum(r["count"] for r in rows if r["tier"] == "manual"),
            "locked": sum(r["count"] for r in rows if r["tier"] == "locked"),
            "failed": sum(1 for r in rows if not r["probed"]),
        },
    }
    write_json(out_path, payload)
    return payload


def install_one(safe: Safe, key: str, unattended: bool) -> dict:
    comp = BY_KEY.get(key)
    if comp is None:
        return status("error.unknown", name=key)
    if comp["tier"] == "locked" or key not in INSTALLERS:
        return status("error.tier", name=key, tier="locked")
    # EN | The unattended gate is here and only here. A manual component is
    # EN | installable by a human pressing its button and never by the pass,
    # EN | whatever the switch says.
    # FR | Le verrou « sans surveillance » est ici, et seulement ici. Un
    # FR | composant manuel est installable par un humain qui presse son
    # FR | bouton, jamais par la passe, quoi que dise l interrupteur.
    if unattended and comp["tier"] != "auto":
        return status("error.tier", name=key, tier=comp["tier"])
    host = open_host(safe)
    with host:
        ok, detail = INSTALLERS[key](host)
    payload = status("install.ok" if ok else "error.ssh",
                     name=key, detail=detail)
    payload["ok"] = ok
    payload["detail"] = detail
    return payload


def run_install_auto(safe: Safe, out_path: Path) -> dict:
    """EN | The nightly pass over the infrastructure. It probes first — a list
    EN | computed before dinner is not a safe thing to apt-upgrade at three in
    EN | the morning — then installs only the auto tier.
    FR | La passe nocturne sur l infrastructure. Elle sonde d abord — une
    FR | liste calculee avant le diner n est pas une chose sure a
    FR | apt-upgrader a trois heures du matin — puis n installe que le palier
    FR | auto."""
    probed = run_probe(safe, out_path)
    targets = [r["key"] for r in probed["components"]
               if r["pending"] and r["tier"] == "auto" and r["key"] in INSTALLERS]
    if not targets:
        return status("install.auto_none")
    done = 0
    failures: list[str] = []
    for key in targets:
        result = install_one(safe, key, unattended=True)
        if result.get("ok"):
            done += 1
        else:
            failures.append(key)
    # EN | Re-probe so the screen reflects the world after the pass rather
    # EN | than the one that justified it.
    # FR | Resonder pour que l ecran reflete le monde apres la passe plutot que
    # FR | celui qui l a justifiee.
    run_probe(safe, out_path)
    payload = status("install.auto_ok", count=done)
    payload["ok"] = not failures
    payload["failed"] = failures
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Visio Sapiens — infrastructure updates probe/installer")
    ap.add_argument("--probe", action="store_true",
                    help="EN | probe every component / FR | sonder chaque composant")
    ap.add_argument("--install", default="",
                    help="EN | install one component by key / FR | installer un composant par cle")
    ap.add_argument("--install-auto", action="store_true",
                    help="EN | install the auto tier / FR | installer le palier auto")
    ap.add_argument("--out", default="/config/www/vssp/infra_updates.json",
                    help="EN | component report / FR | rapport des composants")
    ap.add_argument("--status", default="/config/www/vssp/infra_updates_status.json",
                    help="EN | status file / FR | fichier de statut")
    ap.add_argument("--vault-addr", default=os.environ.get(
        "VSSP_VAULT_ADDR", DEFAULT_VAULT_ADDR))
    ap.add_argument("--token-file", default="/config/vssp/.vault_maint_token",
                    help="EN | vssp-maint token / FR | jeton vssp-maint")
    ap.add_argument("--dry-run", action="store_true",
                    help="EN | no safe, no ssh — writes an unprobed report "
                         "/ FR | sans coffre ni ssh — ecrit un rapport non sonde")
    args = ap.parse_args()

    out_path = Path(args.out)
    status_path = Path(args.status)

    if not (args.probe or args.install or args.install_auto):
        args.probe = True

    safe: Safe | None = None
    if not args.dry_run:
        try:
            safe = Safe.open(args.vault_addr, Path(args.token_file))
        except VaultError as exc:
            # EN | Publish, then stop. A screen that says "no maintenance
            # EN | token" sends someone to the right file; a screen that says
            # EN | nothing sends them into the logs.
            # FR | Publier, puis s arreter. Un ecran qui dit « pas de jeton de
            # FR | maintenance » envoie quelqu un vers le bon fichier ; un
            # FR | ecran muet l envoie dans les journaux.
            payload = dict(exc.payload)
            payload["ok"] = False
            write_json(status_path, payload)
            print(payload["message"], file=sys.stderr)
            return 1

    try:
        if args.install:
            result = install_one(safe, args.install, unattended=False)
            run_probe(safe, out_path)
        elif args.install_auto:
            result = run_install_auto(safe, out_path)
        else:
            report = run_probe(safe, out_path)
            counts = report["counts"]
            if counts["failed"]:
                result = status("probe.partial", total=counts["total"],
                                failed=counts["failed"])
            elif counts["total"]:
                result = status("probe.ok", total=counts["total"])
            else:
                result = status("probe.none")
            result["ok"] = True
    except VaultError as exc:
        payload = dict(exc.payload)
        payload["ok"] = False
        write_json(status_path, payload)
        print(payload["message"], file=sys.stderr)
        return 1

    result.setdefault("ok", True)
    write_json(status_path, result)
    print(result.get("message", ""))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
