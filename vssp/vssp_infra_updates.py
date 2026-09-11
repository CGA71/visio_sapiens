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
# EN | THE TWO THINGS A ROW HAS TO SAY, AND DID NOT
# EN | A row used to carry a name, a version pair and a button. Two questions
# EN | anyone actually asks of an infrastructure update had no answer on it.
# EN | WHERE DOES THIS LIVE. The Ubuntu host, a Docker container beside the
# EN | cluster, and a workload inside the cluster are three different blast
# EN | radiuses, and they sat in one flat list of seven rows that never named
# EN | the difference. Restarting Vault costs a reseal; restarting k3s takes
# EN | Home Assistant with it. Every component now declares its layer and the
# EN | screen groups on it — and the cluster, which used to appear only as a
# EN | version number, now lists what is running inside it.
# EN | HOW FAR IS ONE PRESS. "Latest upstream" is an instruction on an apt
# EN | package and a trap on a component that may not skip a minor version.
# EN | See the UPGRADE POLICIES section for the whole argument; the short form
# EN | is that a row now publishes the NEXT supported version, the path after
# EN | it, and how many steps that is — so a safe on 1.20.4 is offered 1.21.4
# EN | and told there are two more stops, instead of being offered 2.1.0 and a
# EN | button that would skip two storage migrations.
# FR | LES DEUX CHOSES QU UNE LIGNE DOIT DIRE, ET NE DISAIT PAS
# FR | Une ligne portait un nom, un couple de versions et un bouton. Deux
# FR | questions que l on se pose reellement devant une mise a jour
# FR | d infrastructure n y trouvaient aucune reponse.
# FR | OU CECI VIT-IL. L hote Ubuntu, un conteneur Docker a cote du cluster et
# FR | une charge dans le cluster sont trois rayons d explosion differents, et
# FR | ils tenaient dans une seule liste plate de sept lignes qui ne nommait
# FR | jamais la difference. Redemarrer Vault coute un rescellement ;
# FR | redemarrer k3s emporte Home Assistant. Chaque composant declare
# FR | desormais sa couche et l ecran regroupe dessus — et le cluster, qui
# FR | n apparaissait que comme un numero de version, liste maintenant ce qui
# FR | tourne dedans.
# FR | JUSQU OU VA UNE PRESSION. « Le dernier amont » est une consigne sur un
# FR | paquet apt et un piege sur un composant qui ne peut pas sauter une
# FR | version mineure. Voir la section POLITIQUES DE MISE A NIVEAU pour tout
# FR | l argument ; en bref, une ligne publie desormais la PROCHAINE version
# FR | supportee, le chemin qui la suit, et combien d etapes cela represente —
# FR | pour qu un coffre en 1.20.4 se voie proposer 1.21.4 avec deux escales
# FR | annoncees, au lieu de se voir proposer 2.1.0 et un bouton qui sauterait
# FR | deux migrations de stockage.
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
# EN |   locked   reported and never installable from here at all, and each
# EN |            locked component now says WHY in its own words — a generic
# EN |            note under a chip explained nothing about the row it sat on.
# EN | The tier is a property of the COMPONENT, declared in the table below,
# EN | not a decision the dashboard makes. A card cannot promote a component
# EN | to auto by rendering it differently, and the nightly pass filters on
# EN | this field rather than on anything the UI sent it.
# EN | k3s and Vault were `locked` and both were wrongly so, for different
# EN | reasons. Vault is a plain Docker container beside the cluster, not in
# EN | it, so recreating it costs a reseal and nothing else. k3s really does
# EN | take Home Assistant down with it — but so does the host reboot, which
# EN | has been a button all along, and the fix for "this kills the session
# EN | that pressed it" is to detach the command, not to refuse the operation.
# EN | What was actually dangerous about both was aiming them at the newest
# EN | release, and that is what the upgrade policies below fix.
# FR |   manual   jamais installe sans surveillance, quoi que dise
# FR |            l interrupteur. Une ligne, un bouton, une confirmation.
# FR |   locked   remonte, jamais installable d ici, et chaque composant
# FR |            verrouille dit desormais POURQUOI avec ses propres mots — une
# FR |            note generique sous une pastille n expliquait rien sur la
# FR |            ligne ou elle se trouvait.
# FR | k3s et Vault etaient `locked` et tous deux a tort, pour des raisons
# FR | differentes. Vault est un simple conteneur Docker a cote du cluster, pas
# FR | dedans : le recreer coute un rescellement et rien d autre. k3s emporte
# FR | reellement Home Assistant avec lui — mais le redemarrage de l hote aussi,
# FR | et il est un bouton depuis toujours ; la reponse a « ceci tue la session
# FR | qui l a presse » est de detacher la commande, pas de refuser
# FR | l operation. Ce qui etait reellement dangereux sur les deux, c etait de
# FR | les viser sur la release la plus recente, et c est ce que corrigent les
# FR | politiques de mise a niveau plus bas.
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

# EN | Where the upstream ladder of each versioned component is published.
# EN | Named here rather than inline in the probes so a component that moves
# EN | registry is one edit, and so the installers can ask the same source the
# EN | probes did — the version a button installs must be a version the screen
# EN | actually offered.
# FR | Ou est publiee l echelle amont de chaque composant versionne. Nommees
# FR | ici plutot qu en dur dans les sondes pour qu un composant qui change de
# FR | registre soit une seule modification, et pour que les installateurs
# FR | interrogent la meme source que les sondes — la version qu installe un
# FR | bouton doit etre une version que l ecran a reellement proposee.
K3S_REPO = "k3s-io/k3s"
VAULT_IMAGE_REPO = "hashicorp/vault"


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
    "error.vault_sealed": "The safe is sealed: enter three of the five unseal keys, then probe again.",
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
            # EN | 503 is a SEALED safe, and it is far and away the most likely
            # EN | failure here: Vault reseals on every restart by design and no
            # EN | auto-unseal is configured (vault/config/vault.hcl says why).
            # EN | Answering it with "check the vssp-maint token" sends the
            # EN | operator to the one file that is certainly not the problem,
            # EN | and it sends them there on the ordinary morning after a host
            # EN | reboot. The whole INFRASTRUCTURE half goes unprobed when the
            # EN | safe is shut — the host SSH credentials are the first thing
            # EN | read — so this message is the only clue on screen.
            # FR | 503 est un coffre SCELLE, et c est de loin l echec le plus
            # FR | probable ici : Vault se rescelle a chaque redemarrage par
            # FR | conception et aucun descellement automatique n est configure
            # FR | (vault/config/vault.hcl dit pourquoi). Y repondre par
            # FR | « verifier le jeton vssp-maint » envoie l operateur vers le
            # FR | seul fichier qui n est certainement pas en cause, et l y
            # FR | envoie le matin ordinaire qui suit un redemarrage d hote.
            # FR | Toute la moitie INFRASTRUCTURE reste non sondee quand le
            # FR | coffre est ferme — les identifiants SSH de l hote sont la
            # FR | premiere chose lue — donc ce message est le seul indice a
            # FR | l ecran.
            if exc.code == 503:
                raise VaultError(status("error.vault_sealed")) from exc
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

    def put_script(self, script: str, path: str) -> tuple[int, str, str]:
        """EN | Write a shell script to the host and make it executable.
        EN | Sending a multi-line script as a FILE is the only sane way to run
        EN | anything with quotes in it over ssh: a command string here travels
        EN | through the local argv, the remote login shell and sometimes sudo
        EN | as well, and a sed expression with a brace or a pipe in it does not
        EN | survive all three intact. The heredoc is quoted, so the remote
        EN | shell expands nothing at all while writing the file.
        FR | Ecrire un script shell sur l hote et le rendre executable.
        FR | Envoyer un script multi-lignes comme FICHIER est la seule facon
        FR | saine d executer quoi que ce soit contenant des guillemets par
        FR | ssh : une chaine de commande traverse ici l argv local, le shell de
        FR | connexion distant et parfois sudo en plus, et une expression sed
        FR | avec une accolade ou un tube n y survit pas intacte. Le heredoc est
        FR | quote, donc le shell distant n expanse rien du tout en ecrivant le
        FR | fichier."""
        body = script if script.endswith("\n") else script + "\n"
        return self.run(
            f"cat > {path} <<'VSSP_EOF'\n{body}VSSP_EOF\nchmod 700 {path}")

    def run_detached(self, path: str) -> tuple[int, str, str]:
        """EN | Start a script and return without waiting for it, stdin closed
        EN | and the session left behind.
        EN | For an operation that takes down the thing running this process.
        EN | install_os_reboot gets away with staying attached because
        EN | `shutdown -r +1` schedules the work and returns; a k3s upgrade has
        EN | no such courtesy, and without setsid it dies with the ssh session
        EN | the restarting cluster kills. Attached, that is indistinguishable
        EN | from a failed upgrade — the same trap the reboot installer already
        EN | documents.
        EN | The log stays on the host: there is no process left on this side to
        EN | read it into.
        FR | Lancer un script et rendre la main sans l attendre, entree standard
        FR | fermee et session laissee derriere.
        FR | Pour une operation qui emporte ce qui execute ce processus.
        FR | install_os_reboot peut rester attache parce que `shutdown -r +1`
        FR | programme le travail et rend la main ; une mise a niveau k3s n a pas
        FR | cette courtoisie, et sans setsid elle meurt avec la session ssh que
        FR | tue le cluster qui redemarre. Attachee, c est indiscernable d une
        FR | mise a niveau en echec — le meme piege que documente deja
        FR | l installateur de redemarrage.
        FR | Le journal reste sur l hote : il n y a plus de processus de ce cote
        FR | pour le lire."""
        return self.run(
            f"sh -c 'setsid {path} >{path}.log 2>&1 </dev/null &'", sudo=True)

    def run_maybe_sudo(self, command: str) -> tuple[int, str, str]:
        """EN | Run a command that MAY need root, without demanding it.
        EN | Whether `docker ps` or `k3s kubectl` answers unprivileged depends
        EN | on how the host was set up — whether the account is in the docker
        EN | group, whether k3s was started with --write-kubeconfig-mode — and
        EN | both answers are normal. Trying plain first means a
        EN | correctly-configured host never needs the sudo password out of the
        EN | safe to be PROBED, and a locked-down one still gets probed rather
        EN | than reporting its whole Docker and cluster layer as unknown.
        FR | Executer une commande qui PEUT avoir besoin de root, sans
        FR | l exiger. Que `docker ps` ou `k3s kubectl` reponde sans privilege
        FR | depend de la facon dont l hote a ete installe — compte dans le
        FR | groupe docker ou non, k3s demarre avec --write-kubeconfig-mode ou
        FR | non — et les deux reponses sont normales. Essayer d abord sans
        FR | privilege fait qu un hote correctement configure n a jamais besoin
        FR | du mot de passe sudo du coffre pour etre SONDE, et qu un hote
        FR | verrouille est sonde quand meme au lieu de remonter toute sa couche
        FR | Docker et cluster comme inconnue."""
        code, out, err = self.run(command)
        if code == 0:
            return code, out, err
        return self.run(command, sudo=True)

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
# EN | Answers are cached for the length of one run, failures included. The
# EN | k3s probe reads the release list and install_k3s reads it again to
# EN | recover the exact +k3s tag; a second round trip for an answer already
# EN | in memory is one more thing that can fail BETWEEN the version the
# EN | screen offered and the version that gets installed. Caching the
# EN | failures too bounds a run on an instance with no outbound network to
# EN | one timeout per URL instead of one per caller.
# FR | Les reponses sont mises en cache le temps d une execution, echecs
# FR | compris. La sonde k3s lit la liste des releases et install_k3s la relit
# FR | pour retrouver le tag +k3s exact ; un second aller-retour pour une
# FR | reponse deja en memoire, c est une chose de plus qui peut echouer ENTRE
# FR | la version proposee par l ecran et celle qui s installe. Mettre aussi
# FR | les echecs en cache borne une execution sans reseau sortant a un
# FR | timeout par URL au lieu d un par appelant.
_HTTP_CACHE: dict = {}


def http_json(url: str, headers: dict | None = None) -> dict | list | None:
    if url in _HTTP_CACHE:
        return _HTTP_CACHE[url]
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        data = None
    _HTTP_CACHE[url] = data
    return data


def github_releases(repo: str, pages: int = 3) -> list[str]:
    """EN | EVERY published release tag, not just the newest one.
    EN | `releases/latest` answers a single version, which is all the old probe
    EN | asked for — enough to say "you are behind", never enough to say what
    EN | the next hop is. A component that may not skip a minor version needs
    EN | the whole ladder, not its top rung. Pre-releases are dropped: an rc is
    EN | not a stop on anybody's upgrade path.
    FR | TOUS les tags de release publies, pas seulement le plus recent.
    FR | `releases/latest` repond une seule version, tout ce que demandait
    FR | l ancienne sonde — assez pour dire « vous etes en retard », jamais
    FR | assez pour dire quelle est l etape suivante. Un composant qui ne peut
    FR | pas sauter une version mineure a besoin de toute l echelle, pas de son
    FR | dernier barreau. Les pre-versions sont ecartees : une rc n est une
    FR | escale sur le chemin de personne."""
    out: list[str] = []
    for page in range(1, pages + 1):
        data = http_json(
            f"https://api.github.com/repos/{repo}/releases"
            f"?per_page=100&page={page}",
            {"Accept": "application/vnd.github+json",
             "User-Agent": "visio-sapiens"})
        if not isinstance(data, list) or not data:
            break
        for item in data:
            if not isinstance(item, dict):
                continue
            if item.get("draft") or item.get("prerelease"):
                continue
            tag = (item.get("tag_name") or "").lstrip("v")
            if tag and not re.search(r"(?i)(rc|alpha|beta|dev)\d*(\+|$)", tag):
                out.append(tag)
    return out


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


def apt_versions(host: "Host", package: str) -> list[str]:
    """EN | Every version of a package the host's repositories offer.
    EN | apt-cache policy names the CANDIDATE and nothing else, which is enough
    EN | to say "behind" and not enough to say "one minor at a time": the rungs
    EN | between here and there are what madison lists. LC_ALL=C for the same
    EN | reason as in apt_policy — this parses apt's own output.
    FR | Toutes les versions d un paquet que proposent les depots de l hote.
    FR | apt-cache policy nomme le CANDIDAT et rien d autre, ce qui suffit pour
    FR | dire « en retard » et pas pour dire « une mineure a la fois » : les
    FR | barreaux entre ici et la-bas, c est madison qui les liste. LC_ALL=C
    FR | pour la meme raison que dans apt_policy — on analyse la sortie
    FR | d apt."""
    code, out, _ = host.run(f"LC_ALL=C apt-cache madison {package} 2>/dev/null")
    if code != 0:
        return []
    versions: list[str] = []
    for line in out.splitlines():
        parts = [p.strip() for p in line.split("|")]
        # EN | madison prints "pkg | version | source". A Sources line has the
        # EN | same shape and is not an installable binary version.
        # FR | madison affiche « paquet | version | source ». Une ligne Sources
        # FR | a la meme forme et n est pas une version binaire installable.
        if len(parts) >= 3 and parts[0] == package and "Sources" not in parts[2]:
            versions.append(parts[1])
    return versions


def dockerhub_versions(repo: str, pattern: str = r"^\d+\.\d+\.\d+$",
                       pages: int = 3) -> list[str]:
    """EN | Every semver tag Docker Hub still publishes for an image, in
    EN | whatever order it returns them — the caller sorts, because tags are
    EN | strings and sort like strings: 1.9.0 would beat 1.20.0 unless they are
    EN | compared as tuples of ints, which version_tuple does.
    EN | The pattern deliberately rejects a two-part tag like `1.20`: that is a
    EN | floating alias for whatever patch is newest in the series, so it is
    EN | not a rung on a ladder.
    FR | Tous les tags semver que Docker Hub publie encore pour une image, dans
    FR | l ordre ou il les rend — c est l appelant qui trie, parce que les tags
    FR | sont des chaines et se trient comme telles : 1.9.0 battrait 1.20.0 a
    FR | moins de les comparer en tuples d entiers, ce que fait version_tuple.
    FR | Le motif rejette volontairement un tag en deux parties comme `1.20` :
    FR | c est un alias flottant vers le correctif le plus recent de la serie,
    FR | donc pas un barreau d echelle."""
    out: list[str] = []
    rx = re.compile(pattern)
    for page in range(1, pages + 1):
        data = http_json(f"https://hub.docker.com/v2/repositories/{repo}/tags"
                         f"?page_size=100&page={page}")
        if not isinstance(data, dict):
            break
        results = data.get("results") or []
        if not results:
            break
        for item in results:
            name = str(item.get("name") or "")
            if rx.match(name):
                out.append(name)
        if not data.get("next"):
            break
    return out


def vault_api_version(addr: str) -> str:
    """EN | The safe's own version, from the one endpoint that answers without
    EN | a token AND without a shell on the host.
    EN | This matters far more than it sounds. Reading the version over ssh
    EN | means reading host_ssh out of the safe first — so a SEALED Vault could
    EN | not report its own version, and a sealed Vault is the NORMAL state
    EN | after any host reboot, because no auto-unseal is configured on purpose.
    EN | The row that tells you a Vault upgrade is waiting went blank precisely
    EN | when you came to look at it.
    EN | sys/seal-status is unauthenticated, answers 200 even when sealed — the
    EN | healthcheck in vault/docker-compose.yml leans on exactly that — and
    EN | carries a `version` field. Home Assistant already polls this endpoint
    EN | for the seal state on the SAFE screen, so this adds no new exposure,
    EN | no new secret and no new dependency.
    FR | La version du coffre lui-meme, par le seul point d entree qui repond
    FR | sans jeton ET sans shell sur l hote.
    FR | Cela compte bien plus qu il n y parait. Lire la version par ssh veut
    FR | dire lire d abord host_ssh dans le coffre — donc un Vault SCELLE ne
    FR | pouvait pas rapporter sa propre version, et un Vault scelle est l etat
    FR | NORMAL apres tout redemarrage d hote, puisqu aucun descellement
    FR | automatique n est configure, volontairement. La ligne qui vous dit
    FR | qu une mise a niveau de Vault attend se vidait precisement au moment ou
    FR | vous veniez la regarder.
    FR | sys/seal-status est non authentifie, repond 200 meme scelle — le
    FR | healthcheck de vault/docker-compose.yml s appuie exactement sur cela —
    FR | et porte un champ `version`. Home Assistant interroge deja ce point
    FR | d entree pour l etat de scellement sur l ecran COFFRE-FORT : ceci
    FR | n ajoute donc aucune exposition, aucun secret et aucune dependance."""
    data = http_json(f"{addr.rstrip('/')}/v1/sys/seal-status")
    if isinstance(data, dict):
        return str(data.get("version") or "")
    return ""


def image_tag(image: str) -> str:
    """EN | The tag of an image reference, or '' when it carries none. The last
    EN | slash comes first: a registry with a port (`host:5000/img`) puts a
    EN | colon before it and that colon is not a tag. A digest pin has no tag
    EN | at all, by design — it is frozen on purpose.
    FR | Le tag d une reference d image, ou '' quand elle n en porte pas. Le
    FR | dernier slash d abord : un registre avec un port (`hote:5000/img`)
    FR | place un deux-points avant lui, et ce deux-points n est pas un tag.
    FR | Une image epinglee sur une empreinte n a pas de tag du tout, et c est
    FR | voulu — elle est figee a dessein."""
    last = (image or "").rsplit("/", 1)[-1]
    if "@" in last:
        return ""
    return last.split(":", 1)[1] if ":" in last else ""


def version_tuple(value: str) -> tuple:
    return tuple(int(p) for p in re.findall(r"\d+", value or "")) or (0,)


# ═══════════════════════════════════════════════════════════════════════════
# EN | UPGRADE POLICIES — "the latest version" is not always "the next one"
# FR | POLITIQUES DE MISE A NIVEAU — « la derniere version » n est pas
# FR | toujours « la suivante »
# ═══════════════════════════════════════════════════════════════════════════
#
# EN | WHY THIS EXISTS
# EN | The probe used to publish one pair per row: what is installed, and the
# EN | highest version upstream. On an apt package that pair is also the
# EN | instruction — apt goes from one to the other in a single step. On Vault
# EN | it is a LIE. HashiCorp supports one minor series at a time, so a host on
# EN | 1.20.4 reaches 2.1.0 through 1.21.x, then 2.0.x, then 2.1.0: three
# EN | upgrades, each with its own storage and seal migration. A row that
# EN | printed "1.20.4 → 2.1.0" beside a button was offering to skip two of
# EN | them. The same holds for k3s, where Kubernetes forbids skipping a minor
# EN | outright, and for GitLab, whose database migrations run per minor.
# EN | So the ladder is a property of the COMPONENT, declared beside its tier,
# EN | and the probe publishes the WHOLE path instead of its endpoint:
# EN |   next    the one version a press installs — always a version the
# EN |           vendor supports arriving at from where this host stands.
# EN |   latest  the top of the ladder. It stays on the row because how far
# EN |           behind you are is worth knowing; it is no longer a target.
# EN |   path    every stop from next to latest, so the screen can say "three
# EN |           steps" and mean it.
# FR | POURQUOI CECI EXISTE
# FR | La sonde publiait un couple par ligne : ce qui est installe, et la plus
# FR | haute version amont. Sur un paquet apt, ce couple est aussi la consigne
# FR | — apt passe de l un a l autre en une seule etape. Sur Vault c est un
# FR | MENSONGE. HashiCorp ne supporte qu une serie mineure a la fois : un hote
# FR | en 1.20.4 atteint 2.1.0 en passant par 1.21.x, puis 2.0.x, puis 2.1.0 —
# FR | trois mises a niveau, chacune avec sa migration de stockage et de
# FR | scellement. Une ligne qui affichait « 1.20.4 → 2.1.0 » a cote d un
# FR | bouton proposait d en sauter deux. Idem pour k3s, ou Kubernetes interdit
# FR | purement et simplement de sauter une mineure, et pour GitLab, dont les
# FR | migrations de base tournent par mineure.
# FR | L echelle est donc une propriete du COMPOSANT, declaree a cote de son
# FR | palier, et la sonde publie tout le CHEMIN au lieu de son extremite :
# FR |   next    la seule version qu installe une pression — toujours une
# FR |           version ou l editeur supporte d arriver depuis ici.
# FR |   latest  le sommet de l echelle. Il reste sur la ligne parce que savoir
# FR |           de combien on est en retard a de la valeur ; ce n est plus une
# FR |           cible.
# FR |   path    chaque escale de next jusqu a latest, pour que l ecran puisse
# FR |           dire « trois etapes » et le vouloir dire.

# EN | Any version to any version in one move: apt resolves its own
# EN | dependencies and the vendor supports the jump.
# FR | N importe quelle version vers n importe quelle autre en un mouvement :
# FR | apt resout ses dependances et l editeur supporte le saut.
POLICY_DIRECT = "direct"

# EN | One major.minor series at a time, landing on the highest patch that
# EN | series ever published.
# FR | Une serie majeure.mineure a la fois, en atterrissant sur le plus haut
# FR | correctif que cette serie ait publie.
POLICY_SERIES = "series"


def series_of(value: str) -> tuple:
    """EN | (major, minor) — the pair that names an upgrade series.
    FR | (majeure, mineure) — le couple qui nomme une serie de mise a
    FR | niveau."""
    return (version_tuple(value) + (0, 0))[:2]


def plan_upgrade(installed: str, available: list[str], policy: str) -> dict:
    """EN | The road from `installed` to the top of `available`, as the vendor
    EN | allows it to be travelled.
    EN | Every field comes back empty when nothing waits ahead, and an empty or
    EN | unreadable upstream is one of those cases: it is not evidence of being
    EN | up to date, but it is not evidence of being behind either. Only a
    EN | confident comparison ever produces a `next`, because a false "update
    EN | pending" on the k3s row is somebody rebooting a cluster for nothing.
    FR | La route de `installed` jusqu au sommet de `available`, telle que
    FR | l editeur autorise a la parcourir.
    FR | Tous les champs reviennent vides quand rien n attend, et un amont vide
    FR | ou illisible est l un de ces cas : cela ne prouve pas qu on est a jour,
    FR | mais ne prouve pas non plus qu on est en retard. Seule une comparaison
    FR | sure produit un `next`, parce qu un faux « mise a jour en attente » sur
    FR | la ligne k3s, c est quelqu un qui redemarre un cluster pour rien."""
    empty = {"next": "", "path": [], "steps": 0, "latest": ""}
    if not installed:
        return empty
    known = sorted({v for v in available if version_tuple(v) != (0,)},
                   key=version_tuple)
    here = version_tuple(installed)
    ahead = [v for v in known if version_tuple(v) > here]
    if not ahead:
        return empty
    latest = ahead[-1]
    if policy != POLICY_SERIES:
        return {"next": latest, "path": [latest], "steps": 1, "latest": latest}
    # EN | One stop per series waiting ahead, each the highest patch known in
    # EN | that series. A host behind within its OWN series gets that patch as
    # EN | its first stop: both the smallest possible move and the one every
    # EN | vendor asks for before crossing into the next minor.
    # FR | Une escale par serie en attente, chacune au plus haut correctif
    # FR | connu de cette serie. Un hote en retard au sein de SA serie recoit ce
    # FR | correctif comme premiere escale : a la fois le plus petit mouvement
    # FR | possible et celui que tout editeur reclame avant de franchir la
    # FR | mineure suivante.
    stops: list[str] = []
    for one in sorted({series_of(v) for v in ahead}):
        top = max((v for v in known if series_of(v) == one), key=version_tuple)
        if version_tuple(top) > here:
            stops.append(top)
    if not stops:
        return empty
    return {"next": stops[0], "path": stops, "steps": len(stops),
            "latest": latest}


# ═══════════════════════════════════════════════════════════════════════════
# EN | THE COMPONENTS
# FR | LES COMPOSANTS
# ═══════════════════════════════════════════════════════════════════════════
#
# EN | One entry per thing the screen reports.
# EN |   tier         what the nightly pass may touch: auto / manual / locked.
# EN |   where        WHICH LAYER it lives in. `host` is the Ubuntu install
# EN |                itself — apt packages and systemd units. `docker` is a
# EN |                container the host's own Docker daemon runs. `k3s` is
# EN |                inside the cluster. Three layers sat in one flat list
# EN |                before, which left the screen unable to answer the first
# EN |                question anyone asks of an upgrade: what does restarting
# EN |                this take down with it. The screen groups on this field.
# EN |   policy       how far one press may move it — see the policies above.
# EN |   reason_key   why a locked component is locked, IN ITS OWN WORDS. One
# EN |                sentence used to cover all of them, which meant the chip
# EN |                on a row explained nothing about that row.
# EN |   confirm_key  an extra warning for a button whose cost is not obvious
# EN |                from its label. Absent means the plain confirmation.
# EN | `name_key` is a locale key, never a label — this file ships no
# EN | user-facing English.
# FR | Une entree par chose que l ecran remonte.
# FR |   tier         ce que la passe nocturne peut toucher : auto / manual /
# FR |                locked.
# FR |   where        QUELLE COUCHE l heberge. `host` est l installation Ubuntu
# FR |                elle-meme — paquets apt et unites systemd. `docker` est
# FR |                un conteneur que fait tourner le demon Docker de l hote.
# FR |                `k3s` est dans le cluster. Trois couches tenaient dans
# FR |                une seule liste plate, ce qui laissait l ecran incapable
# FR |                de repondre a la premiere question que pose toute mise a
# FR |                niveau : qu est-ce que son redemarrage emporte avec lui.
# FR |                L ecran regroupe sur ce champ.
# FR |   policy       jusqu ou une pression peut la deplacer — voir les
# FR |                politiques ci-dessus.
# FR |   reason_key   pourquoi un composant verrouille l est, AVEC SES PROPRES
# FR |                MOTS. Une seule phrase les couvrait tous, donc la
# FR |                pastille d une ligne n expliquait rien sur cette ligne.
# FR |   confirm_key  un avertissement supplementaire pour un bouton dont le
# FR |                cout ne saute pas aux yeux depuis son libelle. Absent
# FR |                veut dire la confirmation ordinaire.
# FR | `name_key` est une cle de langue, jamais un libelle — ce fichier ne
# FR | livre aucun anglais destine a l utilisateur.
COMPONENTS = [
    # ── EN | The Ubuntu host itself / FR | L hote Ubuntu lui-meme ──────
    {"key": "os_packages",   "name_key": "admin.updates_infra_os_packages",
     "tier": "auto",   "icon": "mdi:ubuntu", "where": "host",
     "policy": POLICY_DIRECT},
    {"key": "os_reboot",     "name_key": "admin.updates_infra_os_reboot",
     "tier": "manual", "icon": "mdi:restart-alert", "where": "host",
     "policy": POLICY_DIRECT,
     "confirm_key": "admin.updates_infra_confirm_reboot"},
    {"key": "gitlab",        "name_key": "admin.updates_infra_gitlab",
     "tier": "manual", "icon": "mdi:gitlab", "where": "host",
     "policy": POLICY_SERIES,
     "confirm_key": "admin.updates_infra_confirm_gitlab"},
    {"key": "gitlab_runner", "name_key": "admin.updates_infra_gitlab_runner",
     "tier": "auto",   "icon": "mdi:rocket-launch-outline", "where": "host",
     "policy": POLICY_DIRECT},
    {"key": "k3s",           "name_key": "admin.updates_infra_k3s",
     "tier": "manual", "icon": "mdi:kubernetes", "where": "host",
     "policy": POLICY_SERIES,
     "confirm_key": "admin.updates_infra_confirm_k3s"},

    # ── EN | Containers the host's own Docker daemon runs
    # ── FR | Conteneurs que fait tourner le demon Docker de l hote ─────
    {"key": "vault",         "name_key": "admin.updates_infra_vault",
     "tier": "manual", "icon": "mdi:safe", "where": "docker",
     "policy": POLICY_SERIES,
     "confirm_key": "admin.updates_infra_confirm_vault"},
    {"key": "docker_images", "name_key": "admin.updates_infra_docker_images",
     "tier": "locked", "icon": "mdi:docker", "where": "docker",
     "policy": POLICY_DIRECT,
     "reason_key": "admin.updates_infra_why_docker_images"},

    # ── EN | Inside the cluster / FR | Dans le cluster ────────────
    {"key": "k3s_workloads", "name_key": "admin.updates_infra_k3s_workloads",
     "tier": "locked", "icon": "mdi:layers-triple-outline", "where": "k3s",
     "policy": POLICY_DIRECT,
     "reason_key": "admin.updates_infra_why_k3s_workloads"},
]
BY_KEY = {c["key"]: c for c in COMPONENTS}

# EN | The order the layers are shown in, declared here rather than in the
# EN | card so the markdown summary and the button card cannot disagree about
# EN | it. Every row carries its layer, so a consumer that ignores this still
# EN | renders correctly — just ungrouped.
# FR | L ordre d affichage des couches, declare ici plutot que dans la carte
# FR | pour que le resume markdown et la carte a boutons ne puissent pas s y
# FR | contredire. Chaque ligne porte sa couche, donc un consommateur qui
# FR | ignore ceci s affiche quand meme — simplement sans regroupement.
WHERE_ORDER = ["host", "docker", "k3s"]

# EN | apt packages that have a component row of their own. They are excluded
# EN | from the host-packages row so nothing is counted twice, and from the
# EN | host-packages upgrade so a manual-tier component is never installed by
# EN | the auto tier through the side door.
# FR | Paquets apt qui ont leur propre ligne de composant. Ils sont exclus de
# FR | la ligne des paquets de l hote pour que rien ne soit compte deux fois,
# FR | et de sa mise a jour pour qu un composant de palier manuel ne soit
# FR | jamais installe par le palier auto en passant par la porte de service.
OWNED_PACKAGES = {"gitlab-ce", "gitlab-ee", "gitlab-runner"}

# EN | The same rule for containers: a container with a component row of its
# EN | own is not counted again in the generic Docker row, so the safe is not
# EN | listed twice under two different verdicts.
# FR | La meme regle pour les conteneurs : un conteneur qui a sa propre ligne
# FR | de composant n est pas recompte dans la ligne Docker generique, pour que
# FR | le coffre ne soit pas liste deux fois sous deux verdicts differents.
OWNED_CONTAINERS = {"vssp-vault"}


def needs_host(probe):
    """EN | Wrap a probe that cannot say anything without a shell on the host,
    EN | so `host is None` becomes an unprobed row rather than an AttributeError.
    EN | Wrapping beats an `if host is None` line inside each probe: it is one
    EN | rule, applied where the table is declared, and a probe written later
    EN | cannot forget it. And `host is None` is no longer the rare case — a
    EN | sealed safe means no ssh at all, and the report still has to be
    EN | written.
    FR | Envelopper une sonde incapable de dire quoi que ce soit sans shell sur
    FR | l hote, pour que `host is None` devienne une ligne non sondee plutot
    FR | qu une AttributeError.
    FR | L enveloppe vaut mieux qu une ligne `if host is None` dans chaque
    FR | sonde : c est une seule regle, appliquee la ou la table est declaree, et
    FR | une sonde ecrite plus tard ne peut pas l oublier. Et `host is None`
    FR | n est plus le cas rare — un coffre scelle veut dire aucun ssh, et le
    FR | rapport doit quand meme etre ecrit."""
    def wrapped(host, safe, comp):
        if host is None:
            return blank(comp, probed=False)
        return probe(host, safe, comp)
    wrapped.__name__ = getattr(probe, "__name__", "probe")
    return wrapped


def blank(component: dict, **over) -> dict:
    row = {
        "key": component["key"],
        "name_key": component["name_key"],
        "tier": component["tier"],
        "icon": component["icon"],
        "where": component["where"],
        "policy": component["policy"],
        "reason_key": component.get("reason_key", ""),
        "confirm_key": component.get("confirm_key", ""),
        "installed": "",
        # EN | `latest` is how far behind the row is; `next` is what a press
        # EN | installs. They are the same string only where the policy allows
        # EN | the whole jump at once, and telling them apart is the entire
        # EN | point of the plan.
        # FR | `latest` dit de combien la ligne est en retard ; `next` dit ce
        # FR | qu installe une pression. Ce sont la meme chaine seulement la ou
        # FR | la politique autorise tout le saut d un coup, et les distinguer
        # FR | est tout l interet du plan.
        "latest": "",
        "next": "",
        "path": [],
        "steps": 0,
        "pending": False,
        "count": 0,
        "detail": [],
        "probed": True,
        # EN | `probed` says whether THIS RUN measured the row. `stale` says
        # EN | the values above came from an EARLIER run that did, and
        # EN | `measured` says when. The three are separate because a screen
        # EN | needs all three answers: what is installed, whether anyone has
        # EN | checked lately, and how lately.
        # FR | `probed` dit si CETTE EXECUTION a mesure la ligne. `stale` dit
        # FR | que les valeurs ci-dessus viennent d une execution ANTERIEURE
        # FR | qui l a fait, et `measured` dit quand. Les trois sont distincts
        # FR | parce qu un ecran a besoin des trois reponses : ce qui est
        # FR | installe, si quelqu un a verifie recemment, et a quel point.
        "stale": False,
        "measured": "",
    }
    row.update(over)
    return row


def planned(component: dict, installed: str, available: list[str],
            **over) -> dict:
    """EN | A row whose pending state IS its upgrade plan, so the two can never
    EN | disagree: nothing reachable means nothing pending, and a row that says
    EN | it is waiting always has a version to name.
    FR | Une ligne dont l etat « en attente » EST son plan de mise a niveau,
    FR | pour que les deux ne puissent jamais se contredire : rien
    FR | d atteignable veut dire rien en attente, et une ligne qui se dit en
    FR | attente a toujours une version a nommer."""
    plan = plan_upgrade(installed, available, component["policy"])
    return blank(component, installed=installed, latest=plan["latest"],
                 next=plan["next"], path=plan["path"], steps=plan["steps"],
                 pending=bool(plan["next"]),
                 count=1 if plan["next"] else 0, **over)


# ── EN | Probes, one per component / FR | Sondes, une par composant ──────
def probe_os_packages(host: Host, safe: "Safe | None", comp: dict) -> dict:
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


def probe_os_reboot(host: Host, safe: "Safe | None", comp: dict) -> dict:
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


def k3s_release_tag(version: str) -> str:
    """EN | The exact release tag for a plain Kubernetes version — `1.37.1`
    EN | becomes `v1.37.1+k3s1`. The suffix counts the k3s build of that same
    EN | Kubernetes version, so the highest one is the right one, and the k3s
    EN | installer accepts nothing else.
    EN | It is resolved HERE rather than carried on the row so the row stays a
    EN | list of versions: the +k3s suffix is k3s trivia, and it belongs next to
    EN | the only code that needs it.
    FR | Le tag de release exact pour une version Kubernetes nue — `1.37.1`
    FR | devient `v1.37.1+k3s1`. Le suffixe numerote la compilation k3s de cette
    FR | meme version de Kubernetes, donc la plus haute est la bonne, et
    FR | l installateur k3s n accepte rien d autre.
    FR | Resolu ICI plutot que porte par la ligne, pour que la ligne reste une
    FR | liste de versions : le suffixe +k3s est une particularite de k3s, sa
    FR | place est a cote du seul code qui en a besoin."""
    if not version:
        return ""
    builds = [t for t in github_releases(K3S_REPO)
              if t.split("+")[0] == version and "+" in t]
    if not builds:
        return ""
    return "v" + max(builds, key=lambda t: version_tuple(t.split("+", 1)[1]))


def probe_k3s(host: Host, safe: "Safe | None", comp: dict) -> dict:
    code, out, _ = host.run("k3s --version 2>/dev/null | head -1")
    if code != 0 or not out.strip():
        return blank(comp, probed=False)
    m = re.search(r"v?(\d+\.\d+\.\d+)", out)
    installed = m.group(1) if m else ""
    # EN | k3s tags read v1.36.2+k3s1 — the +k3s suffix is a build of the same
    # EN | Kubernetes version and must not be compared as a fourth number, so
    # EN | the ladder is built from the part before the plus. Kubernetes itself
    # EN | forbids skipping a minor version, which is why this row carries
    # EN | POLICY_SERIES: a cluster on 1.36 goes to 1.37 and not to 1.39,
    # EN | whatever the newest release happens to be.
    # FR | Les tags k3s se lisent v1.36.2+k3s1 — le suffixe +k3s est une
    # FR | compilation de la meme version de Kubernetes et ne doit pas etre
    # FR | compare comme un quatrieme nombre, l echelle est donc construite sur
    # FR | la partie avant le plus. Kubernetes lui-meme interdit de sauter une
    # FR | version mineure, d ou POLICY_SERIES sur cette ligne : un cluster en
    # FR | 1.36 passe en 1.37 et pas en 1.39, quelle que soit la release la plus
    # FR | recente.
    versions = [t.split("+")[0] for t in github_releases(K3S_REPO)]
    return planned(comp, installed, versions)


def probe_k3s_workloads(host: Host, safe: "Safe | None", comp: dict) -> dict:
    """EN | What is actually running INSIDE the cluster, workload by workload.
    EN | The k3s row above reports the cluster's own version and says nothing
    EN | whatever about its contents — which is how Home Assistant, the thing
    EN | serving this very screen, never appeared on the screen at all. This row
    EN | lists every deployment, statefulset and daemonset with the image it
    EN | pulls, at the level where that image is actually declared: pods come
    EN | and go, their controllers are what an upgrade edits.
    EN | Reported, never installed — see the reason on its row. Changing an
    EN | image here means editing a manifest, and the manifests are not in this
    EN | repository.
    FR | Ce qui tourne reellement DANS le cluster, charge par charge.
    FR | La ligne k3s ci-dessus remonte la version du cluster lui-meme et ne dit
    FR | absolument rien de son contenu — c est ainsi que Home Assistant, ce
    FR | qui sert cet ecran meme, n apparaissait pas du tout a l ecran. Cette
    FR | ligne liste chaque deployment, statefulset et daemonset avec l image
    FR | qu il tire, au niveau ou cette image est reellement declaree : les pods
    FR | vont et viennent, ce sont leurs controleurs qu une mise a niveau
    FR | modifie.
    FR | Remontee, jamais installee — voir la raison sur sa ligne. Changer une
    FR | image ici veut dire modifier un manifeste, et les manifestes ne sont
    FR | pas dans ce depot."""
    code, out, _ = host.run_maybe_sudo(
        "k3s kubectl get deploy,sts,ds -A --no-headers -o "
        "custom-columns=NS:.metadata.namespace,NAME:.metadata.name,"
        "IMG:.spec.template.spec.containers[*].image 2>/dev/null")
    if code != 0 or not out.strip():
        return blank(comp, probed=False)
    rows: list[str] = []
    floating = 0
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        namespace, name = parts[0], parts[1]
        # EN | custom-columns joins a multi-container template with commas, and
        # EN | each image is its own version to know about.
        # FR | custom-columns joint un modele multi-conteneurs par des virgules,
        # FR | et chaque image est sa propre version a connaitre.
        for image in ",".join(parts[2:]).split(","):
            image = image.strip()
            if not image:
                continue
            rows.append(f"{namespace}/{name} {image}")
            if image_tag(image) in ("", "latest"):
                floating += 1
    return blank(comp, installed=str(len(rows)), latest="", pending=False,
                 count=0, detail=rows[:40], floating=floating)


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
            # EN | madison lists the whole ladder; the candidate is the highest
            # EN | rung this machine may actually climb to. A version madison
            # EN | knows but apt would not offer — held, pinned, from a
            # EN | repository that outranks it — is not a stop on the path.
            # FR | madison liste toute l echelle ; le candidat est le plus haut
            # FR | barreau que cette machine puisse reellement atteindre. Une
            # FR | version connue de madison mais que apt ne proposerait pas —
            # FR | gelee, epinglee, issue d un depot moins prioritaire — n est
            # FR | pas une escale du chemin.
            ladder = apt_versions(host, package) or [candidate]
            if candidate:
                ceiling = version_tuple(candidate)
                ladder = [v for v in ladder if version_tuple(v) <= ceiling]
            return planned(comp, installed, ladder,
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


def probe_gitlab_runner(host: Host, safe: "Safe | None", comp: dict) -> dict:
    return probe_apt_package(
        host, comp, ("gitlab-runner",),
        fallback_cmd="gitlab-runner --version 2>/dev/null",
        fallback_rx=r"Version:\s*([0-9][^\s]*)")


def probe_gitlab(host: Host, safe: "Safe | None", comp: dict) -> dict:
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


def vault_container(host: Host) -> tuple[str, str]:
    """EN | (name, image) of the running safe, or ('','') when none runs here.
    FR | (nom, image) du coffre en marche, ou ('','') si aucun ne tourne
    FR | ici."""
    code, out, _ = host.run_maybe_sudo(
        "docker ps --filter name=vault --format '{{.Names}} {{.Image}}' "
        "2>/dev/null | head -1")
    if code != 0 or not out.strip():
        return "", ""
    parts = out.strip().split()
    return (parts[0], parts[1]) if len(parts) >= 2 else (parts[0], "")


def probe_vault(host: "Host | None", safe: "Safe | None", comp: dict) -> dict:
    """EN | Vault runs as a docker container here, so no package manager knows
    EN | its version. Three ways to ask, in this order, and the order is the
    EN | whole design of this probe.
    EN | 1. THE SAFE'S OWN API. Needs neither a token nor a shell, so it is the
    EN |    only one that still answers when the safe is sealed — which is the
    EN |    normal state after a host reboot, and exactly when you want to see
    EN |    this row. This probe is therefore NOT wrapped in needs_host().
    EN | 2. THE BINARY, over ssh. Cannot be wrong about itself, and stands in if
    EN |    the API is unreachable while the host is.
    EN | 3. THE IMAGE TAG, last and reluctantly. It is the obvious place to read
    EN |    a version and the wrong one: this deployment pins
    EN |    `hashicorp/vault:1.20`, a floating alias for the newest patch in the
    EN |    series, so the tag says 1.20 while the binary is 1.20.4 — and a plan
    EN |    built on 1.20 offers 1.20.4 as its first step, an upgrade to the
    EN |    version already running.
    FR | Vault tourne en conteneur docker ici, aucun gestionnaire de paquets ne
    FR | connait donc sa version. Trois facons de demander, dans cet ordre, et
    FR | l ordre est toute la conception de cette sonde.
    FR | 1. L API DU COFFRE LUI-MEME. Ne demande ni jeton ni shell, c est donc
    FR |    la seule qui reponde encore quand le coffre est scelle — etat normal
    FR |    apres un redemarrage d hote, et precisement le moment ou l on veut
    FR |    voir cette ligne. Cette sonde n est donc PAS enveloppee dans
    FR |    needs_host().
    FR | 2. LE BINAIRE, par ssh. Ne peut pas se tromper sur lui-meme, et prend
    FR |    le relais si l API est injoignable alors que l hote l est.
    FR | 3. LE TAG DE L IMAGE, en dernier et a contrecoeur. C est l endroit
    FR |    evident pour lire une version et le mauvais : ce deploiement epingle
    FR |    `hashicorp/vault:1.20`, un alias flottant vers le correctif le plus
    FR |    recent de la serie, donc le tag dit 1.20 quand le binaire est en
    FR |    1.20.4 — et un plan construit sur 1.20 propose 1.20.4 en premiere
    FR |    etape, une mise a niveau vers la version deja en marche."""
    installed = ""
    detail: list[str] = []
    if safe is not None:
        installed = vault_api_version(safe.addr)
        if installed:
            detail.append(safe.addr)
    if host is not None:
        name, image = vault_container(host)
        if name:
            detail.append(f"{name} {image}".strip())
            if not installed:
                code, out, _ = host.run_maybe_sudo(
                    f"docker exec {name} vault version 2>/dev/null")
                if code == 0:
                    m = re.search(r"v?(\d+\.\d+\.\d+)", out)
                    installed = m.group(1) if m else ""
            if not installed:
                installed = image_tag(image)
    if not installed:
        return blank(comp, probed=False)
    # EN | POLICY_SERIES, and this is the component the policy was written for:
    # EN | HashiCorp supports one minor series at a time because each carries a
    # EN | storage and seal migration.
    # FR | POLICY_SERIES, et c est le composant pour lequel la politique a ete
    # FR | ecrite : HashiCorp ne supporte qu une serie mineure a la fois parce
    # FR | que chacune porte une migration de stockage et de scellement.
    return planned(comp, installed, dockerhub_versions(VAULT_IMAGE_REPO),
                   detail=detail)


def probe_docker_images(host: Host, safe: "Safe | None", comp: dict) -> dict:
    """EN | Every other running container, reported as a list rather than as a
    EN | comparison: an image pinned to `latest` has no version to be behind,
    EN | and one pinned to a digest is deliberately frozen. The row says what
    EN | is running; deciding is the operator's.
    FR | Tout autre conteneur en marche, remonte comme une liste plutot que
    FR | comme une comparaison : une image epinglee sur `latest` n a pas de
    FR | version a avoir en retard, et une image epinglee sur une empreinte est
    FR | figee volontairement. La ligne dit ce qui tourne ; decider revient a
    FR | l operateur."""
    code, out, _ = host.run_maybe_sudo(
        "docker ps --format '{{.Names}} {{.Image}}' 2>/dev/null")
    if code != 0:
        return blank(comp, probed=False)
    rows: list[str] = []
    floating = 0
    for line in out.splitlines():
        parts = line.split()
        if not parts or parts[0] in OWNED_CONTAINERS:
            continue
        rows.append(line.strip())
        if image_tag(parts[1] if len(parts) > 1 else "") in ("", "latest"):
            floating += 1
    return blank(comp, installed=str(len(rows)), latest="",
                 pending=False, count=0, detail=rows[:40],
                 floating=floating)


# ── EN | Installers / FR | Installateurs ────────────────────────────────
#
# EN | Each returns (ok, detail). None of them is reachable for a component
# EN | whose tier forbids it — that check happens in install_one, once, rather
# EN | than being repeated and eventually forgotten in one of these.
# FR | Chacun renvoie (ok, detail). Aucun n est joignable pour un composant
# FR | dont le palier l interdit — ce controle a lieu dans install_one, une
# FR | fois, plutot que d etre repete puis oublie dans l un d eux.
def install_os_packages(host: Host, row: dict) -> tuple[bool, str]:
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


def install_apt_pinned(host: Host, row: dict) -> tuple[bool, str]:
    """EN | Install ONE NAMED VERSION of an apt package — the version the row
    EN | published as its next step — rather than `--only-upgrade`.
    EN | `--only-upgrade` installs the candidate, which is the TOP of the
    EN | ladder. On a component whose policy allows the whole jump those are the
    EN | same version and nothing changes. On GitLab they are not: the candidate
    EN | can be several minors up, and every minor in between carries database
    EN | migrations that GitLab runs on the way past. `--only-upgrade` is
    EN | precisely the skipped-migration upgrade the plan exists to prevent.
    EN | Naming the version also makes the button install what the screen
    EN | offered, which is the only circumstance under which a confirmation
    EN | dialog means anything.
    FR | Installer UNE VERSION NOMMEE d un paquet apt — celle que la ligne a
    FR | publiee comme etape suivante — plutot que `--only-upgrade`.
    FR | `--only-upgrade` installe le candidat, c est-a-dire le SOMMET de
    FR | l echelle. Sur un composant dont la politique autorise tout le saut,
    FR | c est la meme version et rien ne change. Sur GitLab, non : le candidat
    FR | peut etre plusieurs mineures plus haut, et chaque mineure intermediaire
    FR | porte des migrations de base que GitLab execute au passage.
    FR | `--only-upgrade` est exactement la mise a niveau a migrations sautees
    FR | que le plan existe pour empecher.
    FR | Nommer la version fait aussi que le bouton installe ce que l ecran a
    FR | propose, seule circonstance ou une demande de confirmation veut dire
    FR | quelque chose."""
    package = row.get("package") or ""
    target = row.get("next") or ""
    if not package:
        return False, f"{row.get('key')} is not an apt package on this host"
    if not target:
        return True, "nothing to upgrade"
    cmd = ("DEBIAN_FRONTEND=noninteractive apt-get -y "
           "-o Dpkg::Options::=--force-confdef "
           "-o Dpkg::Options::=--force-confold "
           f"install {package}={target}")
    code, out, err = host.run(cmd, sudo=True)
    return code == 0, (err or out).strip()[-400:]


def install_os_reboot(host: Host, row: dict) -> tuple[bool, str]:
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


def vault_retag(host: Host, project: str, repo: str, tag: str) -> tuple[int, str]:
    """EN | Point the compose file at one image tag and bring the container up
    EN | on it. Returns (code, output) — saying whether the RIGHT Vault came up
    EN | is the caller's job, because `docker compose up -d` succeeds when it
    EN | has nothing to do and succeeds again when what it started immediately
    EN | died.
    FR | Pointer le fichier compose sur un tag d image et lever le conteneur
    FR | dessus. Renvoie (code, sortie) — dire si le BON Vault s est leve est
    FR | le travail de l appelant, parce que `docker compose up -d` reussit
    FR | quand il n a rien a faire et reussit encore quand ce qu il a demarre
    FR | est mort dans la seconde."""
    path = "/tmp/vssp_vault_retag.sh"
    script = (
        "set -e\n"
        f"cd {project}\n"
        "f=docker-compose.yml\n"
        '[ -f "$f" ] || f=docker-compose.yaml\n'
        f'sed -i "s|{repo}:[A-Za-z0-9._-]*|{repo}:{tag}|g" "$f"\n'
        "docker compose pull\n"
        "docker compose up -d\n"
        # EN | The container needs a moment before `docker exec` will answer,
        # EN | and a container that is going to crash needs a moment to crash.
        # EN | Asking too early reads a starting container as a broken one and a
        # EN | broken one as a starting one.
        # FR | Le conteneur a besoin d un instant avant que `docker exec` ne
        # FR | reponde, et un conteneur qui va planter a besoin d un instant
        # FR | pour planter. Demander trop tot lit un conteneur qui demarre
        # FR | comme casse, et un conteneur casse comme en train de demarrer.
        "sleep 8\n")
    code, out, err = host.put_script(script, path)
    if code != 0:
        return code, (err or out).strip()[-300:]
    code, out, err = host.run_maybe_sudo(f"sh {path}")
    return code, (err or out).strip()[-300:]


def vault_running_version(host: Host, name: str) -> str:
    """EN | The version the container actually answers with, or '' when it is
    EN | not answering at all — which is the same thing as far as an upgrade is
    EN | concerned.
    FR | La version que le conteneur repond reellement, ou '' quand il ne
    FR | repond pas du tout — ce qui revient au meme du point de vue d une mise
    FR | a niveau."""
    code, out, _ = host.run_maybe_sudo(
        f"docker exec {name} vault version 2>/dev/null")
    if code != 0:
        return ""
    m = re.search(r"v?(\d+\.\d+\.\d+)", out)
    return m.group(1) if m else ""


def install_vault(host: Host, row: dict) -> tuple[bool, str]:
    """EN | Move the safe ONE SERIES forward, and PUT IT BACK if the new one
    EN | will not start.
    EN | Vault was a `locked` component and the lock was doing two jobs. One was
    EN | real — nothing should skip two storage migrations — and the upgrade
    EN | plan handles that now. The other was a mistake: the safe is a plain
    EN | Docker container on the host, NOT in k3s (vault/config/vault.hcl says
    EN | why), so recreating it touches neither Home Assistant nor the cluster.
    EN | The compose project directory comes from the container's own labels
    EN | rather than being assumed to be /opt/vssp-vault: that path is a
    EN | convention from the install doc, and docker knows the truth.
    EN |
    EN | THE ROLLBACK IS THE POINT, and it was learned the hard way. An upgrade
    EN | to 2.0.4 pulled, recreated and started cleanly — `docker compose up -d`
    EN | reported nothing but success — and the container then crash-looped on
    EN | an mlock limit. The check below caught it and reported honestly, which
    EN | is worth something, but "honestly reported" still left the safe DOWN:
    EN | no SAFE screen, no infrastructure probe, no installs, until a human
    EN | noticed and edited a compose file by hand.
    EN | So a failed upgrade now undoes itself. The previous tag is read before
    EN | anything changes, and if the new version does not answer, the compose
    EN | file goes back to it and the container comes up on the version that was
    EN | working ten seconds earlier. The operator is told what happened either
    EN | way, and told separately if the rollback ALSO failed, because that is
    EN | the one case that needs hands.
    EN | THE SAFE RESEALS on any of these paths. It answers 503 until three of
    EN | the five unseal keys are entered by hand, because no auto-unseal is
    EN | configured, on purpose. That is what this component's confirm_key warns
    EN | about before the press.
    FR | Avancer le coffre D UNE SERIE, et LE REMETTRE EN PLACE si la nouvelle
    FR | ne demarre pas.
    FR | Vault etait un composant `locked` et ce verrou faisait deux choses.
    FR | L une etait reelle — rien ne doit sauter deux migrations de stockage —
    FR | et le plan de mise a niveau s en charge desormais. L autre etait une
    FR | erreur : le coffre est un simple conteneur Docker sur l hote, PAS dans
    FR | k3s (vault/config/vault.hcl dit pourquoi), le recreer ne touche donc ni
    FR | Home Assistant ni le cluster.
    FR | Le repertoire de projet compose vient des labels du conteneur lui-meme
    FR | plutot que d etre suppose etre /opt/vssp-vault : ce chemin est une
    FR | convention de la doc d installation, et docker connait la verite.
    FR |
    FR | LE RETOUR ARRIERE EST L ESSENTIEL, et il a ete appris a la dure. Une
    FR | mise a niveau vers 2.0.4 a tire, recree et demarre proprement —
    FR | `docker compose up -d` n a rapporte que des succes — puis le conteneur
    FR | est entre en boucle de plantage sur une limite mlock. La verification
    FR | ci-dessous l a attrape et l a dit honnetement, ce qui vaut quelque
    FR | chose, mais « dit honnetement » laissait quand meme le coffre A TERRE :
    FR | plus d ecran COFFRE-FORT, plus de sonde infrastructure, plus
    FR | d installation, jusqu a ce qu un humain le remarque et modifie un
    FR | fichier compose a la main.
    FR | Une mise a niveau en echec se defait donc elle-meme. Le tag precedent
    FR | est lu avant toute modification, et si la nouvelle version ne repond
    FR | pas, le fichier compose y retourne et le conteneur se leve sur la
    FR | version qui marchait dix secondes plus tot. L operateur est informe
    FR | dans les deux cas, et separement si le retour arriere a AUSSI echoue,
    FR | parce que c est le seul cas qui reclame des mains.
    FR | LE COFFRE SE RESCELLE sur tous ces chemins. Il repond 503 tant que
    FR | trois des cinq cles de descellement ne sont pas saisies a la main,
    FR | parce qu aucun descellement automatique n est configure,
    FR | volontairement. C est ce dont le confirm_key de ce composant avertit
    FR | avant la pression."""
    target = row.get("next") or ""
    if not target:
        return True, "nothing to upgrade"
    name, image = vault_container(host)
    if not name:
        return False, "no vault container is running on this host"
    label = '{{index .Config.Labels "com.docker.compose.project.working_dir"}}'
    code, out, _ = host.run_maybe_sudo(
        f"docker inspect --format '{label}' {name} 2>/dev/null")
    project = out.strip()
    if code != 0 or not project or project == "<no value>":
        return False, (f"{name} was not started by docker compose on this "
                       "host: its image tag is not ours to rewrite")
    previous = image_tag(image)
    repo = image[:-(len(previous) + 1)] if previous else image
    if not repo:
        return False, f"cannot read the image reference of {name}"

    _code, ran = vault_retag(host, project, repo, target)
    if vault_running_version(host, name) == target:
        return True, (f"Vault {target} is running and SEALED: it needs three "
                      "of the five unseal keys before the SAFE screen works "
                      "again.")

    # EN | It did not come up. Put back what was there.
    # FR | Elle ne s est pas levee. Remettre ce qui etait la.
    if not previous or previous == target:
        return False, (f"{target} did not come up and there is no previous "
                       f"tag to return to. {ran}")
    vault_retag(host, project, repo, previous)
    if vault_running_version(host, name) == previous:
        return False, (f"{target} would not start, so the safe was rolled back "
                       f"to {previous} and is running again, SEALED. Check "
                       f"`docker logs {name}` before retrying. {ran}")
    return False, (f"{target} would not start AND the rollback to {previous} "
                   f"did not come up either — the safe is down and needs "
                   f"hands: `docker logs {name}` on the host. {ran}")


def install_k3s(host: Host, row: dict) -> tuple[bool, str]:
    """EN | One Kubernetes minor version forward, and this installer could not
    EN | have existed before the plan did. The newest k3s release is routinely
    EN | several minors ahead, Kubernetes forbids skipping any of them, so a
    EN | button aimed at `latest` would have been a button that breaks the
    EN | cluster. Aimed at `next` it is an ordinary upgrade, and that is the
    EN | whole reason this row stopped being `locked`.
    EN | Detached, for the reason install_os_reboot is fire-and-forget: k3s
    EN | restarts, every pod on this node restarts with it, and Home Assistant
    EN | — which is running this very script — is one of them. The ssh session
    EN | dies mid-command, which attached is indistinguishable from a failed
    EN | upgrade. Detached, the upgrade finishes on its own and the next probe
    EN | reports the result.
    FR | Une version mineure de Kubernetes en avant, et cet installateur
    FR | n aurait pas pu exister avant le plan. La release k3s la plus recente
    FR | est couramment plusieurs mineures en avance, Kubernetes interdit d en
    FR | sauter une seule, donc un bouton visant `latest` aurait ete un bouton
    FR | qui casse le cluster. Visant `next`, c est une mise a niveau ordinaire,
    FR | et c est toute la raison pour laquelle cette ligne a cesse d etre
    FR | `locked`.
    FR | Detachee, pour la raison qui fait install_os_reboot « on lance et on
    FR | oublie » : k3s redemarre, chaque pod de ce noeud redemarre avec lui, et
    FR | Home Assistant — qui execute ce script meme — en fait partie. La
    FR | session ssh meurt en pleine commande, ce qui, attache, est indiscernable
    FR | d une mise a niveau en echec. Detachee, la mise a niveau se termine
    FR | seule et la sonde suivante en rapporte le resultat."""
    target = row.get("next") or ""
    if not target:
        return True, "nothing to upgrade"
    tag = k3s_release_tag(target)
    if not tag:
        return False, f"no k3s release tag was published for {target}"
    path = "/tmp/vssp_k3s_upgrade.sh"
    script = ("set -e\n"
              "curl -sfL https://get.k3s.io | "
              f"INSTALL_K3S_VERSION={tag} sh -\n")
    code, out, err = host.put_script(script, path)
    if code != 0:
        return False, (err or out).strip()[-400:]
    code, out, err = host.run_detached(path)
    if code != 0:
        return False, (err or out).strip()[-400:]
    return True, (f"k3s {tag} is installing in the background. The cluster and "
                  f"Home Assistant restart with it; the log is {path}.log on "
                  "the host.")


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
    "os_reboot": install_os_reboot,
    "gitlab": install_apt_pinned,
    "gitlab_runner": install_apt_pinned,
    "k3s": install_k3s,
    "vault": install_vault,
}

# EN | Which key is probed by what, in the same shape. run_probe used to name
# EN | its seven probes by hand in a fixed order, which meant adding a component
# EN | to the table above published a row that nothing ever looked at — the
# EN | quietest possible bug. Now the table is the list.
# EN | Every probe takes (host, safe, comp) whether or not it needs the safe.
# EN | Only GitLab does, and only for a containerised instance; a uniform
# EN | signature is what lets this be a table at all.
# FR | Quelle cle est sondee par quoi, dans la meme forme. run_probe nommait ses
# FR | sept sondes a la main dans un ordre fixe, ce qui faisait qu ajouter un
# FR | composant a la table ci-dessus publiait une ligne que rien ne regardait
# FR | jamais — le bug le plus silencieux possible. Desormais la table EST la
# FR | liste.
# FR | Chaque sonde prend (host, safe, comp) qu elle ait besoin du coffre ou
# FR | non. Seul GitLab en a besoin, et seulement pour une instance
# FR | conteneurisee ; c est une signature uniforme qui permet d en faire une
# FR | table.
PROBES = {
    "os_packages": needs_host(probe_os_packages),
    "os_reboot": needs_host(probe_os_reboot),
    "gitlab": needs_host(probe_gitlab),
    "gitlab_runner": needs_host(probe_gitlab_runner),
    "k3s": needs_host(probe_k3s),
    # EN | The ONE probe not wrapped: the safe answers its own version over an
    # EN | unauthenticated endpoint, so this row survives a sealed safe and a
    # EN | host that cannot be reached at all. See probe_vault.
    # FR | La SEULE sonde non enveloppee : le coffre repond sa propre version
    # FR | sur un point d entree non authentifie, cette ligne survit donc a un
    # FR | coffre scelle et a un hote totalement injoignable. Voir probe_vault.
    "vault": probe_vault,
    "docker_images": needs_host(probe_docker_images),
    "k3s_workloads": needs_host(probe_k3s_workloads),
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


# EN | The fields that are a MEASUREMENT of the machine rather than a
# EN | DESCRIPTION of the component. Everything not in this list - the name,
# EN | the tier, the icon, the layer, the policy, the warning text - comes from
# EN | COMPONENTS in this file and must keep coming from there, so that editing
# EN | the table still changes every row on the next run. Only these travel
# EN | forward from an older report.
# FR | Les champs qui sont une MESURE de la machine plutot qu une DESCRIPTION
# FR | du composant. Tout ce qui n est pas dans cette liste - le nom, le
# FR | palier, l icone, la couche, la politique, le texte d avertissement -
# FR | vient de COMPONENTS dans ce fichier et doit continuer d en venir, pour
# FR | qu editer la table change encore chaque ligne a l execution suivante.
# FR | Seuls ceux-ci voyagent depuis un rapport plus ancien.
CARRIED = ("installed", "latest", "next", "path", "steps", "pending",
           "count", "detail", "security")


def read_report(path: Path) -> dict:
    """EN | The report as it currently stands on disk, or {} when there is
    EN | none, when it is unreadable, or when it is not what we left there.
    EN | Never raises: this runs to make a failing probe less bad, and it has
    EN | no business making it worse.
    FR | Le rapport tel qu il est sur disque, ou {} quand il n y en a pas,
    FR | qu il est illisible, ou que ce n est pas ce qu on y a laisse. Ne leve
    FR | jamais : ceci s execute pour rendre une sonde en echec moins mauvaise,
    FR | et n a aucune raison de la rendre pire."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def carry_forward(rows: list[dict], previous: dict) -> list[dict]:
    """EN | WHAT WE SAW LAST TIME, for the rows we could not see this time.
    EN | A sealed safe takes the host SSH credentials down with it, so seven of
    EN | the eight rows cannot be measured - and the report written in that
    EN | state used to say installed "", pending false, count 0 for every one
    EN | of them. The screen rendered that faithfully: the host, GitLab and k3s
    EN | updates that had been listed an hour earlier simply vanished, and the
    EN | counts went to zero. Vault reseals on every restart by design, so this
    EN | was not a corner case; it was every reboot.
    EN | "I could not measure this" and "there is nothing here" are different
    EN | facts, and the report was publishing the second one for the first. Now
    EN | an unmeasured row keeps the last real measurement, `stale` marks it as
    EN | remembered rather than seen, and `measured` carries the timestamp of
    EN | the run that actually looked, so the screen can dim it and date it.
    EN | The alternative - leaving the previous report untouched on disk - is
    EN | what this file used to do and is strictly worse: old versions are then
    EN | shown as current with nothing anywhere to say they are old. The
    EN | difference between the two is not the data, it is the label on it.
    EN | `measured` is taken from the OLD row when the old row was itself
    EN | carried, so a week of sealed reboots keeps pointing at the last run
    EN | that saw the machine instead of walking the date forward one probe at
    EN | a time.
    FR | CE QU ON A VU LA DERNIERE FOIS, pour les lignes qu on n a pas pu voir
    FR | cette fois. Un coffre scelle emporte avec lui l acces SSH a l hote :
    FR | sept des huit lignes sont donc immesurables - et le rapport ecrit dans
    FR | cet etat disait installed "", pending false, count 0 pour chacune.
    FR | L ecran l affichait fidelement : les mises a jour hote, GitLab et k3s
    FR | listees une heure plus tot disparaissaient purement et simplement, et
    FR | les compteurs tombaient a zero. Vault se rescelle a chaque
    FR | redemarrage par conception : ce n etait donc pas un cas limite,
    FR | c etait chaque redemarrage.
    FR | « Je n ai pas pu mesurer ceci » et « il n y a rien ici » sont deux
    FR | faits differents, et le rapport publiait le second a la place du
    FR | premier. Desormais une ligne non mesuree garde la derniere mesure
    FR | reelle, `stale` la marque comme souvenue plutot que vue, et `measured`
    FR | porte l horodatage de l execution qui a reellement regarde, pour que
    FR | l ecran puisse l attenuer et la dater.
    FR | L alternative - laisser le rapport precedent intact sur disque - est
    FR | ce que ce fichier faisait avant, et est strictement pire : de vieilles
    FR | versions sont alors montrees comme actuelles sans que rien nulle part
    FR | ne dise qu elles sont vieilles. La difference entre les deux n est pas
    FR | la donnee, c est l etiquette dessus.
    FR | `measured` est repris de l ANCIENNE ligne quand celle-ci etait
    FR | elle-meme reportee : une semaine de redemarrages scelles continue donc
    FR | de pointer sur la derniere execution qui a vu la machine, au lieu de
    FR | faire avancer la date d une sonde a l autre."""
    was = {r.get("key"): r for r in (previous.get("components") or [])
           if isinstance(r, dict)}
    stamp = previous.get("generated", "")
    kept = []
    for row in rows:
        old = was.get(row["key"])
        if row.get("probed") or not old:
            kept.append(row)
            continue
        # EN | Nothing to remember: the previous run could not see it either.
        # FR | Rien a retenir : l execution precedente ne la voyait pas non plus.
        if not (old.get("probed") or old.get("stale")):
            kept.append(row)
            continue
        merged = dict(row)
        for field in CARRIED:
            if field in old:
                merged[field] = old[field]
        merged["stale"] = True
        merged["measured"] = old.get("measured") or stamp
        kept.append(merged)
    return kept


def run_probe(safe: Safe | None, out_path: Path) -> dict:
    rows: list[dict] = []
    host: Host | None = None
    failure: VaultError | None = None
    try:
        if safe is not None:
            # EN | A SHUT SAFE STILL PUBLISHES A REPORT, and catching this here
            # EN | rather than letting it fly to main() is the whole point.
            # EN | open_host() reads host_ssh out of the safe, so a sealed Vault
            # EN | fails before a single component has been looked at. The old
            # EN | code let the exception leave without writing anything — which
            # EN | LEFT THE PREVIOUS REPORT ON DISK, and the screen renders
            # EN | whatever is on disk. Versions from days ago were shown as
            # EN | current with no mark anywhere to say otherwise: the worst
            # EN | possible failure for a screen whose one job is telling you
            # EN | what is installed, and the reason a whole redesign of these
            # EN | rows could ship and stay invisible.
            # EN | Now every row that needs the host says "not probed", the rows
            # EN | that do not need it still report, and the exception is
            # EN | re-raised at the end so the status file still names the cause.
            # FR | UN COFFRE FERME PUBLIE QUAND MEME UN RAPPORT, et attraper ceci
            # FR | ici plutot que de le laisser voler jusqu a main() est tout
            # FR | l interet. open_host() lit host_ssh dans le coffre, donc un
            # FR | Vault scelle echoue avant qu un seul composant ait ete
            # FR | regarde. L ancien code laissait l exception partir sans rien
            # FR | ecrire — ce qui LAISSAIT LE RAPPORT PRECEDENT SUR DISQUE, et
            # FR | l ecran affiche ce qui est sur disque. Des versions vieilles
            # FR | de plusieurs jours etaient montrees comme actuelles, sans
            # FR | aucune marque nulle part pour le dire : le pire echec possible
            # FR | pour un ecran dont le seul travail est de dire ce qui est
            # FR | installe, et la raison pour laquelle toute une refonte de ces
            # FR | lignes a pu etre livree et rester invisible.
            # FR | Desormais chaque ligne qui a besoin de l hote dit « non
            # FR | sondee », celles qui n en ont pas besoin remontent quand meme,
            # FR | et l exception est relancee a la fin pour que le fichier de
            # FR | statut en nomme la cause.
            try:
                host = open_host(safe)
            except VaultError as exc:
                failure = exc
        # EN | ONE loop over the table, host or no host. Declaration order IS
        # EN | display order, and the table declares the layers in the order the
        # EN | screen groups them, so a component added above is probed here
        # EN | without anyone remembering to come and say so.
        # EN | A probe that cannot work without a shell is wrapped in
        # EN | needs_host() where PROBES is declared, so `host is None` is an
        # EN | unprobed row rather than a special case here — which is what
        # EN | lets a report be written at all when the safe is shut.
        # FR | UNE boucle sur la table, avec hote ou sans. L ordre de
        # FR | declaration EST l ordre d affichage, et la table declare les
        # FR | couches dans l ordre ou l ecran les regroupe : un composant ajoute
        # FR | plus haut est donc sonde ici sans que personne ait a penser a
        # FR | venir le dire.
        # FR | Une sonde incapable de travailler sans shell est enveloppee dans
        # FR | needs_host() la ou PROBES est declaree, donc `host is None` est
        # FR | une ligne non sondee plutot qu un cas particulier ici — c est ce
        # FR | qui permet d ecrire un rapport du tout quand le coffre est ferme.
        for comp in COMPONENTS:
            probe = PROBES.get(comp["key"])
            rows.append(probe(host, safe, comp) if probe
                        else blank(comp, probed=False))
    finally:
        if host is not None:
            host.close()

    # EN | Read the report we are about to replace, and inherit from it every
    # EN | row this run could not measure. Reading AFTER the loop rather than
    # EN | before is deliberate: the probes take real time, and the file on
    # EN | disk is the freshest thing available at the moment we overwrite it.
    # FR | Lire le rapport qu on s apprete a remplacer, et en heriter chaque
    # FR | ligne que cette execution n a pas pu mesurer. Lire APRES la boucle
    # FR | plutot qu avant est delibere : les sondes prennent du temps reel, et
    # FR | le fichier sur disque est ce qu il y a de plus frais au moment ou on
    # FR | l ecrase.
    rows = carry_forward(rows, read_report(out_path))

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
            # EN | Of the failed rows, how many still have something to show
            # EN | from an earlier run. `failed` alone cannot answer "is the
            # EN | screen empty, or merely out of date", and those two call for
            # EN | different reactions from whoever is looking at it.
            # FR | Parmi les lignes en echec, combien ont encore quelque chose
            # FR | a montrer d une execution anterieure. `failed` seul ne peut
            # FR | pas repondre a « l ecran est-il vide ou seulement perime »,
            # FR | et ces deux cas appellent deux reactions differentes de qui
            # FR | le regarde.
            "stale": sum(1 for r in rows if r.get("stale")),
            # EN | Per layer, so the screen can say which of the three has
            # EN | something waiting without walking the rows in three cards.
            # FR | Par couche, pour que l ecran puisse dire laquelle des trois a
            # FR | quelque chose en attente sans parcourir les lignes dans trois
            # FR | cartes.
            "layers": {w: sum(r["count"] for r in rows if r["where"] == w)
                       for w in WHERE_ORDER},
            # EN | Every hop still to take, across every component. "4 updates
            # EN | pending" and "7 upgrades to perform" are different numbers
            # EN | once a component may not skip a version, and the second one
            # EN | is the one that describes an evening.
            # FR | Chaque saut restant, tous composants confondus. « 4 mises a
            # FR | jour en attente » et « 7 mises a niveau a faire » sont deux
            # FR | nombres differents des lors qu un composant ne peut pas
            # FR | sauter une version, et le second est celui qui decrit une
            # FR | soiree.
            "steps": sum(r["steps"] for r in rows),
        },
    }
    write_json(out_path, payload)
    # EN | Report first, then fail. main() turns this into the status file, so
    # EN | the screen gets both halves: rows that say "not probed", and a message
    # EN | that says why they do.
    # FR | Le rapport d abord, l echec ensuite. main() en fait le fichier de
    # FR | statut, l ecran recoit donc les deux moities : des lignes qui disent
    # FR | « non sondee », et un message qui dit pourquoi elles le disent.
    if failure is not None:
        raise failure
    return payload


def install_one(safe: Safe, key: str, unattended: bool) -> dict:
    # EN | A REFUSAL IS NOT A SUCCESS. These three returns used to leave `ok`
    # EN | unset, main() defaulted it to True, and the status sensor stayed
    # EN | green — so a press the script deliberately refused looked exactly
    # EN | like a press that worked, which is the same silence the browser
    # EN | dialog used to produce.
    # FR | UN REFUS N EST PAS UNE REUSSITE. Ces trois retours laissaient `ok`
    # FR | non defini, main() le mettait a True par defaut, et le capteur de
    # FR | statut restait vert — une pression que le script refusait
    # FR | deliberement ressemblait donc exactement a une pression qui avait
    # FR | marche, le meme silence que produisait le dialogue du navigateur.
    comp = BY_KEY.get(key)
    if comp is None:
        return dict(status("error.unknown", name=key), ok=False)
    if comp["tier"] == "locked" or key not in INSTALLERS:
        return dict(status("error.tier", name=key, tier="locked"), ok=False)
    # EN | The unattended gate is here and only here. A manual component is
    # EN | installable by a human pressing its button and never by the pass,
    # EN | whatever the switch says.
    # FR | Le verrou « sans surveillance » est ici, et seulement ici. Un
    # FR | composant manuel est installable par un humain qui presse son
    # FR | bouton, jamais par la passe, quoi que dise l interrupteur.
    if unattended and comp["tier"] != "auto":
        return dict(status("error.tier", name=key, tier=comp["tier"]), ok=False)
    host = open_host(safe)
    with host:
        # EN | PROBE FIRST, then install what that probe found.
        # EN | The installer is handed a row it did not choose, and installs the
        # EN | single version that row names as its next step. That is what
        # EN | keeps a stepped upgrade honest: the button on screen said
        # EN | 1.20.4 → 1.21.4, and no path through this code can turn the press
        # EN | into a jump to 2.1.0 — not a stale sensor, not a card rendered
        # EN | before the last probe, not a second operator pressing a different
        # EN | row. It also means an already-installed update is a no-op with a
        # EN | message rather than a command run for nothing.
        # FR | SONDER D ABORD, puis installer ce que cette sonde a trouve.
        # FR | L installateur recoit une ligne qu il n a pas choisie, et installe
        # FR | la seule version que cette ligne nomme comme etape suivante. C est
        # FR | ce qui garde honnete une mise a niveau par etapes : le bouton a
        # FR | l ecran disait 1.20.4 → 1.21.4, et aucun chemin dans ce code ne
        # FR | peut transformer la pression en un saut vers 2.1.0 — ni un
        # FR | capteur perime, ni une carte rendue avant la derniere sonde, ni un
        # FR | second operateur qui presse une autre ligne. Cela fait aussi
        # FR | qu une mise a jour deja installee est une non-operation avec un
        # FR | message plutot qu une commande lancee pour rien.
        probe = PROBES.get(key)
        row = probe(host, safe, comp) if probe else blank(comp, probed=False)
        if not row["pending"]:
            payload = status("install.none", name=key)
            payload["ok"] = True
            payload["detail"] = ""
            return payload
        ok, detail = INSTALLERS[key](host, row)
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
            # EN | AND REPUBLISH THE REPORT, which this path used to skip.
            # EN | Returning here left the previous report untouched on disk,
            # EN | and the screen renders what is on disk: every row appeared
            # EN | current, dated now, measured never. A probe with no safe at
            # EN | all is exactly the case carry_forward() exists for - it
            # EN | writes the same rows back with `stale` on them, so the
            # EN | numbers survive and the screen says they are remembered.
            # EN | Guarded, because this is the error path: a second failure
            # EN | while reporting the first must not replace the message the
            # EN | operator needs with a traceback about the report.
            # FR | ET REPUBLIER LE RAPPORT, ce que ce chemin sautait. Revenir
            # FR | ici laissait le rapport precedent intact sur disque, et
            # FR | l ecran affiche ce qui est sur disque : chaque ligne
            # FR | paraissait actuelle, datee de maintenant, mesuree jamais.
            # FR | Une sonde sans coffre du tout est precisement le cas pour
            # FR | lequel carry_forward() existe - elle reecrit les memes
            # FR | lignes avec `stale` dessus, les nombres survivent donc et
            # FR | l ecran dit qu ils sont souvenus.
            # FR | Sous garde, parce que c est le chemin d erreur : un second
            # FR | echec pendant qu on rapporte le premier ne doit pas
            # FR | remplacer le message dont l operateur a besoin par une
            # FR | trace d appels a propos du rapport.
            try:
                run_probe(None, out_path)
            except Exception as report_exc:  # noqa: BLE001
                print(f"[warn] report not refreshed: {report_exc}",
                      file=sys.stderr)
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
