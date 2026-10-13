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
#
# ===========================================================================
# Visio Sapiens - vssp_icloud.py
#
# EN | MOVES AN iCLOUD PHOTO LIBRARY ONTO STORAGE YOU OWN, and only then
# EN | offers to free the copy that sits in iCloud. That order is the whole
# EN | point: nothing is ever removed from Apple's side before this program
# EN | has written the file somewhere else and read back its size.
# FR | DEPLACE UNE PHOTOTHEQUE iCLOUD VERS UN STOCKAGE QUI VOUS APPARTIENT,
# FR | et ne propose qu ensuite de liberer la copie qui dort dans iCloud. Cet
# FR | ordre est tout le propos : rien n est jamais retire du cote d Apple
# FR | avant que ce programme n ait ecrit le fichier ailleurs et relu sa
# FR | taille.
#
# ---------------------------------------------------------------------------
# EN | ONE DEPENDENCY, TWO ENGINES - and why icloudpd is the one to install
# FR | UNE DEPENDANCE, DEUX MOTEURS - et pourquoi installer icloudpd
# ---------------------------------------------------------------------------
# EN | `pip install icloudpd` delivers two things at once, and this program
# EN | uses both:
# EN |
# EN |   the icloudpd COMMAND   a download loop that has been hardened
# EN |                          against Apple for years - resumable, rate-
# EN |                          limit aware, and carrying the one option that
# EN |                          expresses this whole feature in a single
# EN |                          pass: --keep-icloud-recent-days, which
# EN |                          deletes in iCloud what it has just stored
# EN |                          locally, except the last N days.
# EN |
# EN |   the pyicloud_ipd MODULE  vendored inside that same distribution
# EN |                          (src/pyicloud_ipd), it is the library the
# EN |                          command itself talks to. Importing it gives
# EN |                          per-asset access - an id, a size, a thumbnail
# EN |                          - which the command line cannot express: no
# EN |                          icloudpd flag means "these 37 items I ticked".
# EN |
# EN | So the two paths are not two ways of doing the same thing. They are
# EN | the only two things each tool can do:
# EN |   PICK   a thumbnail grid, hand-picked items  -> the library
# EN |   BULK   everything still missing locally     -> the command
# EN | Both write into the same destination tree and the same ledger, and
# EN | both ride on ONE trusted session, in ONE cookie directory. That shared
# EN | session is the reason the library used here is pyicloud_ipd and not
# EN | plain pyicloud: the session files icloudpd reads are the ones its own
# EN | library writes.
# FR | `pip install icloudpd` livre deux choses d un coup, et ce programme se
# FR | sert des deux :
# FR |
# FR |   la COMMANDE icloudpd   une boucle de telechargement durcie contre
# FR |                          Apple depuis des annees - reprenable,
# FR |                          consciente des limites de debit, et porteuse
# FR |                          de la seule option qui exprime toute cette
# FR |                          fonction en une passe :
# FR |                          --keep-icloud-recent-days, qui supprime dans
# FR |                          iCloud ce qu elle vient de stocker en local,
# FR |                          sauf les N derniers jours.
# FR |
# FR |   le MODULE pyicloud_ipd  vendore dans cette meme distribution
# FR |                          (src/pyicloud_ipd), c est la bibliotheque a
# FR |                          laquelle la commande parle. L importer donne
# FR |                          l acces element par element - un id, une
# FR |                          taille, une miniature - que la ligne de
# FR |                          commande ne sait pas exprimer : aucun
# FR |                          drapeau icloudpd ne veut dire « ces 37
# FR |                          elements que j ai coches ».
# FR |
# FR | Les deux chemins ne sont donc pas deux facons de faire la meme chose.
# FR | Ce sont les deux seules choses que chaque outil sait faire :
# FR |   CHOISIR  une grille de miniatures, au cas par cas -> la bibliotheque
# FR |   EN MASSE tout ce qui manque encore en local       -> la commande
# FR | Les deux ecrivent dans la meme arborescence et le meme registre, et
# FR | les deux reposent sur UNE session de confiance, dans UN repertoire de
# FR | cookies. Cette session partagee est la raison pour laquelle la
# FR | bibliotheque employee ici est pyicloud_ipd et non pyicloud tout court :
# FR | les fichiers de session que lit icloudpd sont ceux qu ecrit sa propre
# FR | bibliotheque.
#
# EN | pyicloud (the upstream project) is accepted as a FALLBACK engine for
# EN | the picker, because its API is the stable, documented one. On an
# EN | instance that only has pyicloud, the grid works and the bulk button
# EN | says why it is unavailable. On an instance with icloudpd, everything
# EN | works. The screen names which engine is live.
# FR | pyicloud (le projet amont) est accepte comme moteur de REPLI pour le
# FR | selecteur, parce que son API est celle qui est stable et documentee.
# FR | Sur une instance qui n a que pyicloud, la grille marche et le bouton
# FR | de masse dit pourquoi il est indisponible. Sur une instance avec
# FR | icloudpd, tout marche. L ecran nomme le moteur actif.
#
# ---------------------------------------------------------------------------
# EN | THE ONE STEP THAT CANNOT BE AUTOMATED - the 2FA code. Apple sends it
# EN | to a trusted device and no form can read it from there, exactly as the
# EN | Google consent click cannot be signed on the owner's behalf
# EN | (vssp_google_setup.py says the same about OAuth). It is taken here by
# EN | the library rather than by `icloudpd --auth-only`, for one practical
# EN | reason: icloudpd reads the code from a console prompt or a web UI, and
# EN | has no flag to be handed one - while the library has
# EN | validate_2fa_code(). The session that comes out is the same session,
# EN | in the same directory, which the command then reuses without ever
# EN | being given a password on its command line.
# FR | LA SEULE ETAPE NON AUTOMATISABLE - le code 2FA. Apple l envoie vers un
# FR | appareil de confiance et aucun formulaire ne peut l y lire, exactement
# FR | comme le clic de consentement Google ne peut pas etre signe a la place
# FR | du proprietaire (vssp_google_setup.py dit la meme chose d OAuth). Il
# FR | est pris ici par la bibliotheque plutot que par `icloudpd --auth-only`
# FR | pour une raison pratique : icloudpd lit le code depuis une invite
# FR | console ou une interface web, et n a aucun drapeau pour s en voir
# FR | confier un - alors que la bibliotheque a validate_2fa_code(). La
# FR | session qui en sort est la meme session, dans le meme repertoire, que
# FR | la commande reutilise ensuite sans jamais recevoir de mot de passe sur
# FR | sa ligne de commande.
#
# EN | WHY AN APP-SPECIFIC PASSWORD IS THE WRONG ANSWER HERE. Apple's
# EN | app-specific passwords only open the published CalDAV/IMAP services;
# EN | the photo library is not one of them. This program therefore needs the
# EN | real Apple ID password, which is why it never travels on a command
# EN | line and is stored nowhere but a 0600 file written by
# EN | shell_command.vssp_write_icloud_password - the same convention as
# EN | vssp_ha_token, the chatbot keys and the Google client secret.
# FR | POURQUOI UN MOT DE PASSE D APPLICATION EST LA MAUVAISE REPONSE ICI.
# FR | Les mots de passe d application d Apple n ouvrent que les services
# FR | publies CalDAV/IMAP ; la photothèque n en fait pas partie. Ce
# FR | programme a donc besoin du vrai mot de passe de l identifiant Apple,
# FR | raison pour laquelle il ne voyage jamais en ligne de commande et
# FR | n est stocke que dans un fichier 0600 ecrit par
# FR | shell_command.vssp_write_icloud_password - meme convention que
# FR | vssp_ha_token, les cles du chatbot et le secret client Google.
#
# EN | PRIVACY OF THE THUMBNAILS - READ THIS BEFORE MOVING THEM. Home
# EN | Assistant serves /config/www as /local/ WITHOUT authentication: any
# EN | browser that can reach the instance can read a file there if it can
# EN | name it. The picker needs thumbnails in a browser, and an iframe has
# EN | no Bearer token to offer, so no authenticated path is available to it.
# EN | The answer is not to pretend the directory is private, but to make the
# EN | names unguessable and the stay short:
# EN |   - each thumbnail is named HMAC-SHA256(salt, photo id)[:32].jpg, the
# EN |     salt living in a 0600 file created once per instance;
# EN |   - `purge` erases them, and a transfer purges what it just moved;
# EN |   - only the page being looked at is ever materialised.
# FR | CONFIDENTIALITE DES MINIATURES - A LIRE AVANT DE LES DEPLACER. Home
# FR | Assistant sert /config/www en /local/ SANS authentification : tout
# FR | navigateur capable de joindre l instance peut y lire un fichier s il
# FR | sait le nommer. Le selecteur a besoin de miniatures dans un
# FR | navigateur, et une iframe n a aucun jeton Bearer a presenter : aucun
# FR | chemin authentifie ne lui est donc accessible. La reponse n est pas de
# FR | faire semblant que le repertoire est prive, mais de rendre les noms
# FR | impossibles a deviner et le sejour court :
# FR |   - chaque miniature se nomme HMAC-SHA256(sel, id photo)[:32].jpg, le
# FR |     sel vivant dans un fichier 0600 cree une fois par instance ;
# FR |   - `purge` les efface, et un transfert purge ce qu il vient de
# FR |     deplacer ;
# FR |   - seule la page regardee est materialisee.
#
# EN | LONG RUNS AND THE 60-SECOND WALL. A Home Assistant shell_command is
# EN | killed at 60 seconds. A library scan or a 4 GB video transfer laughs
# EN | at that, so every long action relaunches itself detached
# EN | (--background) and reports through the status file, which the console
# EN | sensors and the picker both poll. A lock file keeps two of them from
# EN | running at once.
# FR | LES EXECUTIONS LONGUES ET LE MUR DES 60 SECONDES. Un shell_command de
# FR | Home Assistant est tue a 60 secondes. Un scan de photothèque ou le
# FR | transfert d une video de 4 Go s en moquent : chaque action longue se
# FR | relance donc detachee (--background) et rend compte par le fichier
# FR | d etat, interroge a la fois par les capteurs de la console et par le
# FR | selecteur. Un fichier de verrou empeche deux d entre elles de tourner
# FR | ensemble.
#
# EN | Depends on: icloudpd (pip, optional - the screen says so when it is
# EN | absent), and for `grow` only, the Safe/Host pair of
# EN | vssp_infra_updates.py.
# FR | Depend de : icloudpd (pip, optionnel - l ecran le dit quand il
# FR | manque), et pour `grow` seulement, du couple Safe/Host de
# FR | vssp_infra_updates.py.
#
# Usage:
#   python3 vssp_icloud.py --action status
#   python3 vssp_icloud.py --action link
#   python3 vssp_icloud.py --action code --code 123456
#   python3 vssp_icloud.py --action scan --background
#   python3 vssp_icloud.py --action page --offset 0 --limit 60 --filter pending
#   python3 vssp_icloud.py --action transfer --json-b64 <base64> --background
#   python3 vssp_icloud.py --action bulk --background [--free-icloud-days 30]
#   python3 vssp_icloud.py --action release --json-b64 <base64>
#   python3 vssp_icloud.py --action storage
#   python3 vssp_icloud.py --action grow --size +50G
# ===========================================================================
import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


# ===========================================================================
# EN | LANGUAGE - same three-key contract as vssp_google_setup.py
# FR | LANGUE - meme contrat a trois cles que vssp_google_setup.py
# ===========================================================================
# EN | The status file carries, for every message:
# EN |   message_key + message_vars  - the machine form, which the wizard
# EN |                                 page re-renders in its own language;
# EN |   message + state_label       - rendered here in --locale, because a
# EN |                                 command_line sensor cannot translate.
# FR | Le fichier d etat porte, pour chaque message :
# FR |   message_key + message_vars  - la forme machine, que la page wizard
# FR |                                 rend dans sa propre langue ;
# FR |   message + state_label       - rendus ici dans --locale, parce qu un
# FR |                                 capteur command_line ne traduit rien.
BASE_LOCALE = "en"
SUPPORTED_LOCALES = ("en", "fr")

MESSAGES = {
    "no_library": {
        "en": "No iCloud engine on this instance. Press INSTALL ENGINE to "
              "add icloudpd.",
        "fr": "Aucun moteur iCloud sur cette instance. Pressez INSTALLER LE "
              "MOTEUR pour ajouter icloudpd.",
    },
    "no_credentials": {
        "en": "Apple ID and password are both required. Fill them in the "
              "iCLOUD form.",
        "fr": "L identifiant Apple et le mot de passe sont tous deux "
              "obligatoires. Renseignez-les dans le formulaire iCLOUD.",
    },
    "login_failed": {
        "en": "Apple refused the sign-in: {detail}",
        "fr": "Apple a refuse la connexion : {detail}",
    },
    "awaiting_2fa": {
        "en": "Apple sent a code to your trusted devices. Enter it to finish "
              "linking.",
        "fr": "Apple a envoye un code vers vos appareils de confiance. "
              "Saisissez-le pour terminer la liaison.",
    },
    "code_rejected": {
        "en": "Apple rejected that code. It is single-use and short-lived - "
              "press SEND A NEW CODE, then enter the one that arrives.",
        "fr": "Apple a refuse ce code. Il est a usage unique et ephemere - "
              "pressez ENVOYER UN NOUVEAU CODE, puis saisissez celui qui "
              "arrive.",
    },
    "session_forgotten": {
        "en": "Session erased ({removed} file(s)). Press CONNECT: the next "
              "sign-in is a real one, and Apple will send a code.",
        "fr": "Session effacee ({removed} fichier(s)). Pressez CONNECTER : la "
              "prochaine connexion sera une vraie, et Apple enverra un code.",
    },
    # EN | The session Apple will not use. Named apart from every other
    # EN | failure because its cure is unique and counter-intuitive: not a
    # EN | new password, not a new code - a forced forget, so the next
    # EN | sign-in is a real one and Apple is asked for a code at last.
    # FR | La session dont Apple ne veut pas. Nommee a part de tout autre
    # FR | echec parce que son remede est unique et contre-intuitif : ni un
    # FR | nouveau mot de passe, ni un nouveau code - un oubli force, pour
    # FR | que la connexion suivante soit une vraie et qu Apple soit enfin
    # FR | sollicite pour un code.
    # EN | Not a failure: Apple is rebuilding the library index for this
    # EN | session and will finish on its own. The one thing NOT to do is
    # EN | sign in again, which restarts the wait - so this message says to
    # EN | wait, and says nothing about forgetting the session.
    # FR | Pas une panne : Apple reconstruit l index de la photothèque pour
    # FR | cette session et finira tout seul. La seule chose a NE PAS faire
    # FR | est de se reconnecter, ce qui relance l attente - ce message dit
    # FR | donc d attendre, et ne dit rien d un oubli de session.
    "indexing": {
        "en": "Connected. Apple is still indexing the photo library for this "
              "session - it finishes on its own, usually within a few "
              "minutes. Wait, then press REFRESH. Do not sign in again: that "
              "restarts the indexing.",
        "fr": "Connecte. Apple indexe encore la photothèque pour cette "
              "session - cela se termine tout seul, en general en quelques "
              "minutes. Attendez, puis pressez RAFRAICHIR. Ne vous "
              "reconnectez pas : cela relance l indexation.",
    },
    "stale_session": {
        "en": "The stored session is accepted for sign-in but refused by the "
              "photo service, so nothing can be read or transferred. Press "
              "FORGET SESSION then CONNECT: the next sign-in is a real one "
              "and Apple will send a code. ({detail})",
        "fr": "La session memorisee est acceptee a la connexion mais refusee "
              "par le service photo : rien ne peut etre lu ni transfere. "
              "Pressez OUBLIER LA SESSION puis CONNECTER : la prochaine "
              "connexion sera une vraie et Apple enverra un code. ({detail})",
    },
    "already_linked": {
        "en": "{account} is already connected and Apple trusts this session, "
              "so there is no code to wait for. Nothing to do here - go to "
              "the destination and the library below.",
        "fr": "{account} est deja connecte et Apple fait confiance a cette "
              "session : il n y a aucun code a attendre. Rien a faire ici - "
              "passez a la destination et a la photothèque plus bas.",
    },
    "code_resent": {
        "en": "A new code is on its way to your trusted devices. Any earlier "
              "code is now void.",
        "fr": "Un nouveau code part vers vos appareils de confiance. Tout "
              "code precedent est desormais caduc.",
    },
    # EN | The code was right and Apple still will not trust the session. The
    # EN | user cannot tell that apart from a refused code - both end in the
    # EN | same prompt - so it gets its own sentence, naming the directory the
    # EN | session should have been written to.
    # FR | Le code etait bon et Apple refuse quand meme de faire confiance a
    # FR | la session. L utilisateur ne peut pas distinguer cela d un code
    # FR | refuse - les deux finissent sur la meme invite - d ou une phrase a
    # FR | part, qui nomme le repertoire ou la session aurait du etre ecrite.
    "code_not_trusted": {
        "en": "The code was accepted but Apple did not mark the session as "
              "trusted, so it will ask again. Check that {path} persists "
              "across restarts. ({detail})",
        "fr": "Le code a ete accepte mais Apple n a pas marque la session "
              "comme de confiance : elle redemandera. Verifiez que {path} "
              "survit aux redemarrages. ({detail})",
    },
    "session_unwritable": {
        "en": "The session directory {path} cannot be written to, so every "
              "run starts a new session and every code is already stale: "
              "{detail}",
        "fr": "Le repertoire de session {path} n est pas accessible en "
              "ecriture : chaque execution demarre donc une nouvelle session "
              "et chaque code est deja perime : {detail}",
    },
    "linked": {
        "en": "Linked to {account} through {engine}.",
        "fr": "Lie a {account} via {engine}.",
    },
    "scan_running": {
        "en": "Scanning the library: {done} items indexed.",
        "fr": "Analyse de la photothèque : {done} elements indexes.",
    },
    "scan_done": {
        "en": "{photos} photo(s) and {videos} video(s) indexed, {size} in all.",
        "fr": "{photos} photo(s) et {videos} video(s) indexees, {size} au "
              "total.",
    },
    "index_empty": {
        "en": "No index yet - run SCAN LIBRARY first.",
        "fr": "Aucun index - lancez ANALYSER LA PHOTOTHEQUE d abord.",
    },
    "transfer_running": {
        "en": "Transferring: {done}/{total} items, {size} written.",
        "fr": "Transfert : {done}/{total} elements, {size} ecrits.",
    },
    "transfer_done": {
        "en": "{done} item(s) transferred, {size} written to {dest}. "
              "{failed} failure(s).",
        "fr": "{done} element(s) transfere(s), {size} ecrits vers {dest}. "
              "{failed} echec(s).",
    },
    "transfer_failed": {
        "en": "Nothing was transferred: all {failed} item(s) failed the same "
              "way - {detail}",
        "fr": "Rien n a ete transfere : les {failed} element(s) ont tous "
              "echoue de la meme facon - {detail}",
    },
    "nothing_selected": {
        "en": "Nothing selected.",
        "fr": "Aucune selection.",
    },
    "dest_unwritable": {
        "en": "The destination {dest} cannot be written to: {detail}",
        "fr": "La destination {dest} n est pas accessible en ecriture : "
              "{detail}",
    },
    "released": {
        "en": "{done} item(s) removed from iCloud, {size} freed. {skipped} "
              "skipped because they are not verified on disk.",
        "fr": "{done} element(s) retires d iCloud, {size} liberes. {skipped} "
              "ignore(s) faute de verification sur disque.",
    },
    "release_unverified": {
        "en": "Nothing was removed: not one of the selected items is "
              "recorded in the ledger with a matching size on disk.",
        "fr": "Rien n a ete retire : aucun des elements selectionnes n est "
              "inscrit au registre avec une taille concordante sur disque.",
    },
    # EN | The bulk path, which is the icloudpd command itself.
    # FR | Le chemin de masse, c est-a-dire la commande icloudpd elle-meme.
    "bulk_unavailable": {
        "en": "The bulk transfer needs the icloudpd command, which is not "
              "installed. The thumbnail picker works without it.",
        "fr": "Le transfert en masse exige la commande icloudpd, qui n est "
              "pas installee. Le selecteur de miniatures fonctionne sans "
              "elle.",
    },
    "bulk_running": {
        "en": "icloudpd is working: {done} file(s) downloaded so far.",
        "fr": "icloudpd travaille : {done} fichier(s) telecharges jusqu ici.",
    },
    "bulk_done": {
        "en": "icloudpd finished: {done} file(s) downloaded to {dest}.",
        "fr": "icloudpd a termine : {done} fichier(s) telecharges vers "
              "{dest}.",
    },
    "bulk_done_freed": {
        "en": "icloudpd finished: {done} file(s) downloaded to {dest}, and "
              "everything older than {days} day(s) was removed from iCloud.",
        "fr": "icloudpd a termine : {done} fichier(s) telecharges vers "
              "{dest}, et tout ce qui a plus de {days} jour(s) a ete retire "
              "d iCloud.",
    },
    "bulk_failed": {
        "en": "icloudpd stopped with code {code}: {detail}",
        "fr": "icloudpd s est arrete avec le code {code} : {detail}",
    },
    "storage_local": {
        "en": "{free} free of {total} on {fstype} - {used_pct}% used.",
        "fr": "{free} libres sur {total} en {fstype} - {used_pct}% utilises.",
    },
    "storage_ephemeral": {
        "en": "{dest} is not mounted storage - it is the container's own "
              "filesystem ({fstype}), which a restart or a core update wipes. "
              "Add the partition or the NAS share in Settings > System > "
              "Storage before transferring anything.",
        "fr": "{dest} n est pas un stockage monte - c est le systeme de "
              "fichiers du conteneur ({fstype}), qu un redemarrage ou une "
              "mise a jour du coeur efface. Ajoutez la partition ou le "
              "partage NAS dans Parametres > Systeme > Stockage avant de "
              "transferer quoi que ce soit.",
    },
    "bulk_no_shared_session": {
        "en": "The icloudpd command is installed but its library "
              "(pyicloud_ipd) is not importable, so it cannot read the "
              "session this screen signed in with. The picker works; a bulk "
              "run would be refused by Apple.",
        "fr": "La commande icloudpd est installee mais sa bibliotheque "
              "(pyicloud_ipd) n est pas importable : elle ne peut donc pas "
              "lire la session avec laquelle cet ecran s est connecte. Le "
              "selecteur fonctionne ; un transfert de masse serait refuse "
              "par Apple.",
    },
    "storage_network": {
        "en": "{free} free of {total} on a network share ({fstype}) - resize "
              "it on the NAS itself.",
        "fr": "{free} libres sur {total} sur un partage reseau ({fstype}) - "
              "redimensionnez-le sur le NAS lui-meme.",
    },
    "grow_done": {
        "en": "Volume grown by {size}. {free} free now.",
        "fr": "Volume agrandi de {size}. {free} libres desormais.",
    },
    "grow_not_lvm": {
        "en": "The destination is not an LVM logical volume, so it cannot be "
              "grown from here: {detail}",
        "fr": "La destination n est pas un volume logique LVM : elle ne peut "
              "pas etre agrandie d ici : {detail}",
    },
    "grow_shrink_refused": {
        "en": "Only growing is offered. Shrinking a mounted filesystem "
              "destroys data when it goes wrong, and it is not reversible "
              "from a dashboard.",
        "fr": "Seul l agrandissement est propose. Retrecir un systeme de "
              "fichiers monte detruit des donnees en cas d erreur, et cela "
              "ne se rattrape pas depuis un dashboard.",
    },
    "grow_failed": {
        "en": "The host refused the resize: {detail}",
        "fr": "L hote a refuse le redimensionnement : {detail}",
    },
    "busy": {
        "en": "Another iCloud operation is still running ({action}).",
        "fr": "Une autre operation iCloud tourne encore ({action}).",
    },
    "failure": {
        "en": "Failure: {detail}",
        "fr": "Echec : {detail}",
    },
}

# EN | Shown by sensor.vssp_icloud_state, which would otherwise print the raw
# EN | machine token under a translated label. The token itself stays in
# EN | `state`, untranslated, because that is what the wizard branches on.
# FR | Affiche par sensor.vssp_icloud_state, qui sinon imprimerait le jeton
# FR | machine brut sous un libelle traduit. Le jeton lui-meme reste dans
# FR | `state`, non traduit, car c est sur lui que le wizard s aiguille.
STATE_LABELS = {
    "no_library": {"en": "Engine missing", "fr": "Moteur absent"},
    "not_configured": {"en": "Not configured", "fr": "Non configure"},
    "awaiting_2fa": {"en": "Code required", "fr": "Code requis"},
    # EN | Not a failure: Apple is rebuilding the library index for this
    # EN | session and will finish on its own. The one thing NOT to do is
    # EN | sign in again, which restarts the wait - so this message says to
    # EN | wait, and says nothing about forgetting the session.
    # FR | Pas une panne : Apple reconstruit l index de la photothèque pour
    # FR | cette session et finira tout seul. La seule chose a NE PAS faire
    # FR | est de se reconnecter, ce qui relance l attente - ce message dit
    # FR | donc d attendre, et ne dit rien d un oubli de session.
    "indexing": {
        "en": "Connected. Apple is still indexing the photo library for this "
              "session - it finishes on its own, usually within a few "
              "minutes. Wait, then press REFRESH. Do not sign in again: that "
              "restarts the indexing.",
        "fr": "Connecte. Apple indexe encore la photothèque pour cette "
              "session - cela se termine tout seul, en general en quelques "
              "minutes. Attendez, puis pressez RAFRAICHIR. Ne vous "
              "reconnectez pas : cela relance l indexation.",
    },
    "stale_session": {"en": "Session refused", "fr": "Session refusee"},
    "indexing": {"en": "Apple is indexing", "fr": "Indexation Apple"},
    "linked": {"en": "Linked", "fr": "Lie"},
    "scanning": {"en": "Scanning", "fr": "Analyse en cours"},
    "transferring": {"en": "Transferring", "fr": "Transfert en cours"},
    "error": {"en": "Error", "fr": "Erreur"},
}


def pick_locale(value: str) -> str:
    """EN | Normalise whatever input_select.vssp_language holds to a code.
    FR | Normalise ce que contient input_select.vssp_language en un code."""
    code = (value or "").strip().lower().replace("_", "-").split("-")[0]
    return code if code in SUPPORTED_LOCALES else BASE_LOCALE


def msg(key: str, locale: str, **fields) -> str:
    entry = MESSAGES.get(key, {})
    text = entry.get(locale) or entry.get(BASE_LOCALE) or key
    try:
        return text.format(**fields) if fields else text
    except (KeyError, IndexError):
        return text


def say(key: str, locale: str, **fields) -> dict:
    return {"message_key": key,
            "message_vars": fields,
            "message": msg(key, locale, **fields)}


def stated(state: str, locale: str) -> dict:
    label = STATE_LABELS.get(state, {})
    return {"state": state,
            "state_label": label.get(locale) or label.get(BASE_LOCALE) or state}


# ===========================================================================
# EN | THE ENGINE - pyicloud_ipd (shipped by icloudpd), else pyicloud
# FR | LE MOTEUR - pyicloud_ipd (livre par icloudpd), sinon pyicloud
# ===========================================================================
# EN | The two libraries do the same job through different doors, and the
# EN | difference is not cosmetic: pyicloud_ipd takes a password PROVIDER (a
# EN | callable) and a domain as its first arguments, pyicloud takes the
# EN | password itself. Rather than guess at call time, each engine states
# EN | its own shape here, and the rest of the file speaks only to this
# EN | interface. An engine whose internals have moved since this was written
# EN | fails inside its own adapter, with a message naming it, instead of
# EN | taking a feature down somewhere unrelated.
# FR | Les deux bibliotheques font le meme travail par des portes
# FR | differentes, et l ecart n est pas cosmetique : pyicloud_ipd prend un
# FR | FOURNISSEUR de mot de passe (un appelable) et un domaine en premiers
# FR | arguments, pyicloud prend le mot de passe lui-meme. Plutot que de
# FR | deviner au moment de l appel, chaque moteur declare ici sa propre
# FR | forme, et tout le reste du fichier ne parle qu a cette interface. Un
# FR | moteur dont les entrailles ont bouge depuis l ecriture de ces lignes
# FR | echoue dans son propre adaptateur, avec un message qui le nomme, au
# FR | lieu d emporter une fonction ailleurs.
class Engine:
    """EN | What the rest of this program needs from an iCloud library.
    FR | Ce dont le reste de ce programme a besoin d une bibliotheque
    FR | iCloud."""

    name = "none"

    def connect(self, account: str, password: str, cookie_dir: Path):
        raise NotImplementedError

    def assets(self, api, retries: int = 0, delay: float = 10.0):
        """EN | Iterate every asset of the main library.
        EN |
        EN | RETRY WHILE APPLE IS INDEXING, because Apple itself says to. The
        EN | library index is rebuilt per session and the answer flaps:
        EN | measured on a live account, one connection reported 1730 assets
        EN | ready and the next, in the same minute, answered "not finished
        EN | indexing". Giving up on the first refusal is what turned a
        EN | transient wait into an empty grid and a failed transfer - and
        EN | into an evening of looking for a fault in the sign-in.
        EN | The caller chooses how long to wait, because the budget differs:
        EN | a page request runs inside a shell_command and dies at 60
        EN | seconds, while a scan or a transfer is detached and can afford
        EN | minutes.
        FR | REESSAYER PENDANT QU APPLE INDEXE, parce qu Apple lui-meme le
        FR | demande. L index de la photothèque est reconstruit par session et
        FR | la reponse papillonne : mesure sur un compte reel, une connexion
        FR | a annonce 1730 elements prets et la suivante, dans la meme
        FR | minute, a repondu « not finished indexing ». Abandonner au
        FR | premier refus est ce qui a transforme une attente passagere en
        FR | grille vide et en transfert echoue - et en une soiree a chercher
        FR | une panne dans la connexion.
        FR | L appelant choisit la duree d attente, car le budget differe :
        FR | une demande de page tourne dans un shell_command et meurt a 60
        FR | secondes, tandis qu un scan ou un transfert est detache et peut
        FR | s offrir des minutes."""
        attempt = 0
        while True:
            try:
                return self._album(api)
            except Exception as exc:  # noqa: BLE001
                kind, _detail = photo_fault(exc)
                if kind != "indexing" or attempt >= retries:
                    raise
                attempt += 1
                time.sleep(delay)

    def _album(self, api):
        photos = api.photos
        attempts = (
            lambda: photos.all,
            lambda: photos.albums["All Photos"],
            lambda: photos.libraries["PrimarySync"].albums["All Photos"],
        )
        for attempt in attempts:
            try:
                album = attempt()
            except Exception:  # noqa: BLE001 - try the next door
                continue
            if album is not None:
                return album
        raise RuntimeError(f"{self.name} exposes no 'All Photos' album")

    def count(self, album) -> int:
        try:
            return len(album)
        except Exception:  # noqa: BLE001 - a count is a nicety, not a need
            return 0

    def download(self, asset, version: str):
        raise NotImplementedError

    def delete(self, asset) -> None:
        asset.delete()


class IpdEngine(Engine):
    """EN | The library icloudpd itself uses. Preferred, because the trusted
    EN | session it writes is the one the icloudpd command then reads.
    FR | La bibliotheque qu icloudpd emploie lui-meme. Preferee, parce que la
    FR | session de confiance qu elle ecrit est celle que la commande
    FR | icloudpd lit ensuite."""

    name = "icloudpd"

    def connect(self, account: str, password: str, cookie_dir: Path):
        from pyicloud_ipd.base import PyiCloudService  # noqa: PLC0415
        # EN | password_provider is a callable by design on this fork: the
        # EN | library calls it only if the stored session turns out to be
        # EN | stale, which is what lets a trusted run touch no secret at all.
        # FR | password_provider est un appelable par conception sur ce fork :
        # FR | la bibliotheque ne l appelle que si la session memorisee s avere
        # FR | perimee, ce qui permet a une execution de confiance de ne
        # FR | toucher aucun secret.
        return PyiCloudService(
            domain="com",
            apple_id=account,
            password_provider=lambda: password,
            cookie_directory=str(cookie_dir),
        )

    def download(self, asset, version: str):
        # EN | Recent versions of this fork key the versions by an enum
        # EN | rather than by the plain strings pyicloud uses. Both shapes are
        # EN | tried, newest first.
        # FR | Les versions recentes de ce fork indexent les tailles par une
        # FR | enumeration plutot que par les chaines de pyicloud. Les deux
        # FR | formes sont tentees, la plus recente d abord.
        try:
            from pyicloud_ipd.version_size import AssetVersionSize  # noqa: PLC0415
            sizes = {"thumb": AssetVersionSize.THUMB,
                     "medium": AssetVersionSize.MEDIUM,
                     "original": AssetVersionSize.ORIGINAL}
            return asset.download(sizes[version])
        except Exception:  # noqa: BLE001 - fall through to the string form
            return asset.download(version)


class PyiCloudEngine(Engine):
    """EN | The upstream project. Its API is the documented one, so it is the
    EN | fallback when icloudpd is not installed - the picker then works and
    EN | the bulk button explains itself.
    FR | Le projet amont. Son API est celle qui est documentee : c est donc le
    FR | repli quand icloudpd n est pas installe - le selecteur marche alors
    FR | et le bouton de masse s explique."""

    name = "pyicloud"

    def connect(self, account: str, password: str, cookie_dir: Path):
        from pyicloud import PyiCloudService  # noqa: PLC0415
        return PyiCloudService(account, password,
                               cookie_directory=str(cookie_dir))

    def download(self, asset, version: str):
        return asset.download(version)


def available_engines() -> list:
    """EN | Which engines this instance can actually import, best first.
    FR | Quels moteurs cette instance sait reellement importer, le meilleur
    FR | d abord."""
    found = []
    for engine in (IpdEngine(), PyiCloudEngine()):
        module = "pyicloud_ipd" if engine.name == "icloudpd" else "pyicloud"
        try:
            __import__(module)
            found.append(engine)
        except Exception:  # noqa: BLE001 - absent, or broken: same answer
            continue
    return found


def icloudpd_command(explicit: str = "") -> str:
    """EN | The icloudpd executable, or an empty string. An explicit path from
    EN | the caller wins, so an instance that installed it somewhere unusual
    EN | can say where without this file guessing.
    FR | L executable icloudpd, ou une chaine vide. Un chemin explicite fourni
    FR | par l appelant l emporte, pour qu une instance l ayant installe a un
    FR | endroit inhabituel puisse le dire sans que ce fichier devine."""
    if explicit:
        return explicit if Path(explicit).exists() else ""
    found = shutil.which("icloudpd")
    if found:
        return found
    # EN | pip --user and the Home Assistant image both put console scripts
    # EN | outside the PATH a shell_command inherits.
    # FR | pip --user et l image Home Assistant placent tous deux les scripts
    # FR | console hors du PATH dont herite un shell_command.
    for candidate in ("/usr/local/bin/icloudpd", "/config/.local/bin/icloudpd",
                      str(Path.home() / ".local/bin/icloudpd")):
        if Path(candidate).exists():
            return candidate
    return ""


# ===========================================================================
# EN | PATHS AND SMALL HELPERS
# FR | CHEMINS ET PETITS OUTILS
# ===========================================================================
def human(num: float) -> str:
    """EN | Bytes to a short human string. Used inside translated sentences,
    EN | so it stays unit-only (no word) and reads the same in both.
    FR | Octets vers une chaine courte. Employee dans des phrases traduites,
    FR | elle reste en unites seules (aucun mot) et se lit pareil dans les
    FR | deux."""
    step = 1024.0
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < step or unit == "TB":
            return f"{num:.0f} {unit}" if unit == "B" else f"{num:.1f} {unit}"
        num /= step
    return f"{num:.1f} TB"


def read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save_json(path: Path, payload) -> None:
    """EN | Write through a temporary file, so a reader never catches half a
    EN | document - the console polls these every few seconds.
    FR | Ecriture par fichier temporaire, pour qu un lecteur n attrape jamais
    FR | un demi-document - la console les interroge toutes les secondes."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                       encoding="utf-8")
        tmp.replace(path)
    except OSError as exc:
        print(f"[warn] {path.name} not written: {exc}", file=sys.stderr)


def thumb_salt(path: Path) -> bytes:
    """EN | One random salt per instance, created on first use, 0600. It is
    EN | what makes a thumbnail name unguessable from a photo id - see the
    EN | privacy note at the top of this file.
    FR | Un sel aleatoire par instance, cree au premier usage, en 0600. C est
    FR | lui qui rend un nom de miniature indevinable depuis un id de photo -
    FR | voir la note de confidentialite en tete de fichier."""
    existing = read_text_file(path)
    if existing:
        return existing.encode("utf-8")
    value = secrets.token_hex(32)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
        os.chmod(path, 0o600)
    except OSError as exc:
        print(f"[warn] thumbnail salt not persisted: {exc}", file=sys.stderr)
    return value.encode("utf-8")


def thumb_name(salt: bytes, photo_id: str) -> str:
    return hmac.new(salt, photo_id.encode("utf-8"),
                    hashlib.sha256).hexdigest()[:32] + ".jpg"


def safe_component(value: str, fallback: str) -> str:
    """EN | A filename from Apple, made safe for a POSIX path: no separator,
    EN | no leading dot, never empty.
    FR | Un nom de fichier venu d Apple, rendu sur pour un chemin POSIX :
    FR | aucun separateur, aucun point initial, jamais vide."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", (value or "").strip())
    cleaned = cleaned.lstrip(".")
    return cleaned[:120] or fallback


# ===========================================================================
# EN | THE LOCK - one long operation at a time
# FR | LE VERROU - une seule operation longue a la fois
# ===========================================================================
class Lock:
    """EN | A pid file. Stale locks (the process is gone) are taken over
    EN | rather than left to block the screen forever - a container restart
    EN | in the middle of a scan must not need a human with a shell.
    FR | Un fichier de pid. Les verrous morts (le processus a disparu) sont
    FR | repris plutot que de bloquer l ecran pour toujours - un redemarrage
    FR | de conteneur au milieu d un scan ne doit pas exiger un humain avec
    FR | un terminal."""

    def __init__(self, path: Path, action: str):
        self.path = path
        self.action = action
        self.held = False

    def holder(self) -> str:
        data = load_json(self.path, {})
        pid = data.get("pid")
        if not pid:
            return ""
        try:
            os.kill(int(pid), 0)
        except (OSError, ValueError):
            return ""
        return data.get("action") or "?"

    def acquire(self) -> bool:
        if self.holder():
            return False
        save_json(self.path, {"pid": os.getpid(), "action": self.action,
                              "since": datetime.now().isoformat(timespec="seconds")})
        self.held = True
        return True

    def release(self) -> None:
        if self.held:
            try:
                self.path.unlink()
            except OSError:
                pass
            self.held = False

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.release()
        return False


# ===========================================================================
# EN | iCLOUD SESSION
# FR | SESSION iCLOUD
# ===========================================================================
def photo_fault(exc) -> tuple:
    """EN | Say what really went wrong behind the photo service, by walking
    EN | the cause chain the library throws away.
    EN |
    EN | pyicloud raises PyiCloudServiceUnavailable("Photos service not
    EN | available") `from` whatever actually happened, and the outer
    EN | sentence is the same for every cause. One of those causes is not a
    EN | fault at all: Apple answers
    EN |     "iCloud Photo Library not finished indexing. Please try again in
    EN |      a few minutes."
    EN | while it rebuilds the library index for a session - a wait, not a
    EN | breakage, and it resolves on its own.
    EN | Flattening that into "service not available" is what sent a whole
    EN | evening into chasing the sign-in: the account was connected, the
    EN | password was right, the session was trusted, and the one sentence
    EN | saying "wait a few minutes" was being swallowed. Worse, the advice
    EN | the screen gave instead - forget the session and sign in again -
    EN | restarts Apple's indexing, so following it made the wait longer
    EN | every time.
    FR | Dire ce qui a reellement echoue derriere le service photo, en
    FR | remontant la chaine de causes que la bibliotheque jette.
    FR |
    FR | pyicloud leve PyiCloudServiceUnavailable(« Photos service not
    FR | available ») `from` ce qui s est vraiment produit, et la phrase
    FR | exterieure est la meme pour toutes les causes. L une d elles n est
    FR | pas une panne du tout : Apple repond
    FR |     « iCloud Photo Library not finished indexing. Please try again
    FR |      in a few minutes. »
    FR | pendant qu il reconstruit l index de la photothèque pour une
    FR | session - une attente, pas une casse, et cela se resout tout seul.
    FR | Aplatir cela en « service indisponible » est ce qui a envoye une
    FR | soiree entiere a poursuivre la connexion : le compte etait
    FR | connecte, le mot de passe bon, la session de confiance, et l unique
    FR | phrase disant « attendez quelques minutes » etait avalee. Pire, le
    FR | conseil que l ecran donnait a la place - oublier la session et se
    FR | reconnecter - relance l indexation d Apple : le suivre allongeait
    FR | donc l attente a chaque fois."""
    chain = []
    cur = exc
    for _ in range(5):
        if cur is None:
            break
        name = type(cur).__name__
        text = str(cur)
        chain.append(f"{name}: {text}")
        if ("not finished indexing" in text.lower()
                or name == "PyiCloudServiceNotActivatedException"):
            return "indexing", text[:200]
        cur = cur.__cause__ or cur.__context__
    return "unavailable", " <- ".join(chain)[:200]


def connect(args, locale: str, push_code: bool = False):
    """EN | Open a session from the stored credentials. Returns
    EN | (api, engine, state, payload-extra): state is 'linked',
    EN | 'awaiting_2fa' or an error state, and api is None unless the session
    EN | is usable.
    EN |
    EN | THIS FUNCTION NEVER ASKS APPLE FOR A CODE, and that is the whole
    EN | point of the comment. It used to call request_2fa_code() whenever it
    EN | saw requires_2fa, which read as a courtesy - push a code while the
    EN | user is looking at the field that wants one. It was in fact an
    EN | endless loop. Every action goes through connect(), including the one
    EN | that VALIDATES a code: the user typed code A, connect() asked Apple
    EN | for code B, Apple invalidated A, and the validation of A was refused.
    EN | The screen asked again, the user read the newly arrived B, typed it,
    EN | and connect() asked for C. Forever.
    EN | The call was never needed either: with HSA2, Apple sends the code on
    EN | its own when the authentication happens - requires_2fa being true
    EN | MEANS a code has just been sent. Asking again only invalidates it.
    EN | Pushing a fresh code is now a decision of the CALLER, through
    EN | push_code, and the default is not to. Only two callers pass True:
    EN | `link`, where authenticating is the whole point and a code is what
    EN | the person is waiting for, and `resend`, which exists for nothing
    EN | else. `code` - the one that validates - passes False, and that is
    EN | the whole fix.
    EN | The first attempt at this removed the push everywhere, including
    EN | from `link`, which traded the loop for the opposite failure: a
    EN | cached session answers requires_2fa without re-authenticating, so
    EN | Apple sends nothing and no code ever arrives. A person pressing
    EN | CONNECT must get a code.
    FR | Ouvre une session depuis les identifiants memorises. Renvoie
    FR | (api, moteur, etat, complement) : l etat vaut 'linked',
    FR | 'awaiting_2fa' ou un etat d erreur, et api est None sauf si la
    FR | session est utilisable.
    FR |
    FR | CETTE FONCTION NE DEMANDE JAMAIS DE CODE A APPLE, et c est tout le
    FR | propos de ce commentaire. Elle appelait request_2fa_code() des
    FR | qu elle voyait requires_2fa, ce qui passait pour une attention -
    FR | pousser un code pendant que l utilisateur regarde le champ qui en
    FR | reclame un. C etait en realite une boucle sans fin. Toute action
    FR | passe par connect(), y compris celle qui VALIDE un code :
    FR | l utilisateur tapait le code A, connect() demandait le code B a
    FR | Apple, Apple invalidait A, et la validation de A etait refusee.
    FR | L ecran redemandait, l utilisateur lisait le B qui venait
    FR | d arriver, le tapait, et connect() demandait C. Indefiniment.
    FR | L appel n a jamais ete necessaire non plus : en HSA2, Apple envoie
    FR | le code de lui-meme au moment de l authentification - requires_2fa
    FR | vrai SIGNIFIE qu un code vient d etre envoye. En redemander un ne
    FR | fait que l invalider. Pousser un nouveau code est desormais une
    FR | action explicite qu une personne choisit (--action resend), jamais
    FR | un effet de bord de la connexion."""
    engines = available_engines()
    if not engines:
        return None, None, "no_library", say("no_library", locale)
    engine = engines[0]

    account = (args.apple_id or "").strip()
    password = read_text_file(Path(args.password_file))
    if not account or not password:
        return None, engine, "not_configured", say("no_credentials", locale)

    # EN | A cookie directory that cannot be written is the OTHER way this
    # EN | ends in an endless code prompt: every run would then start a brand
    # EN | new session, so the code issued for the previous one is always
    # EN | stale. Checked and named, rather than left to look like Apple
    # EN | refusing good codes.
    # FR | Un repertoire de cookies non inscriptible est l AUTRE facon de
    # FR | finir sur une demande de code sans fin : chaque execution
    # FR | demarrerait alors une session neuve, et le code emis pour la
    # FR | precedente serait toujours perime. Verifie et nomme, plutot que
    # FR | laisse a ressembler a un Apple qui refuse de bons codes.
    cookies = Path(args.session_dir)
    try:
        cookies.mkdir(parents=True, exist_ok=True)
        os.chmod(cookies, 0o700)
        probe = cookies / ".vssp_write_test"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return None, engine, "error", say("session_unwritable", locale,
                                          path=str(cookies),
                                          detail=str(exc)[:120])

    try:
        api = engine.connect(account, password, cookies)
    except Exception as exc:  # noqa: BLE001 - the libraries raise many shapes
        return None, engine, "error", say("login_failed", locale,
                                          detail=str(exc)[:200])

    if getattr(api, "requires_2fa", False):
        if push_code:
            try:
                api.request_2fa_code()
            except Exception:  # noqa: BLE001 - a push failure is not fatal
                pass             # here; the screen still offers SEND A NEW CODE
        return api, engine, "awaiting_2fa", say("awaiting_2fa", locale)

    # EN | TRUSTED IS NOT THE SAME AS USABLE, and believing otherwise cost a
    # EN | whole evening. A stored session can come back with requires_2fa
    # EN | False and is_trusted_session True while the Photos web service
    # EN | refuses it outright - the cookie jar carries enough to skip the
    # EN | 2FA challenge and not enough to open photos, which announces
    # EN | itself as "Missing X-APPLE-WEBAUTH-HSA-LOGIN cookie" and then as
    # EN | "Photos service not available" at the first transfer.
    # EN | Reporting that session as linked is the worst possible answer: the
    # EN | screen says the account is connected, CONNECT asks Apple for
    # EN | nothing because no 2FA is required, so no code ever arrives, and
    # EN | every explanation on screen is true and useless. The person is
    # EN | told they are fine while nothing works.
    # EN | So the question asked here is the one that matters - does the
    # EN | service this feature exists for actually answer - and a session
    # EN | that fails it is named stale, with the cure, instead of being
    # EN | called linked.
    # FR | DE CONFIANCE N EST PAS LA MEME CHOSE QU UTILISABLE, et avoir cru
    # FR | le contraire a coute une soiree entiere. Une session memorisee
    # FR | peut revenir avec requires_2fa a False et is_trusted_session a
    # FR | True alors que le service web Photos la refuse net - le pot de
    # FR | cookies porte assez pour sauter le defi 2FA et pas assez pour
    # FR | ouvrir les photos, ce qui s annonce par « Missing
    # FR | X-APPLE-WEBAUTH-HSA-LOGIN cookie » puis par « Photos service not
    # FR | available » au premier transfert.
    # FR | Rapporter cette session comme liee est la pire reponse possible :
    # FR | l ecran dit que le compte est connecte, CONNECTER ne demande rien
    # FR | a Apple puisque aucun 2FA n est requis, donc aucun code n arrive
    # FR | jamais, et chaque explication a l ecran est vraie et inutile. On
    # FR | annonce a la personne que tout va bien pendant que rien ne marche.
    # FR | La question posee ici est donc celle qui compte - le service pour
    # FR | lequel cette fonction existe repond-il reellement - et une session
    # FR | qui y echoue est nommee perimee, avec le remede, au lieu d etre
    # FR | appelee liee.
    try:
        _ = api.photos
    except Exception as exc:  # noqa: BLE001 - any refusal means unusable
        kind, detail = photo_fault(exc)
        if kind == "indexing":
            return api, engine, "indexing", say("indexing", locale)
        return api, engine, "stale_session", say("stale_session", locale,
                                                 detail=detail)

    return api, engine, "linked", say("linked", locale, account=account,
                                      engine=engine.name)


def engine_facts(args, engine) -> dict:
    """EN | What the screen needs to say about its own plumbing: which engine
    EN | answered, and whether a bulk run could really work.
    EN |
    EN | `bulk_available` USED TO MEAN "the icloudpd binary is on disk", and
    EN | that was not the same question. A bulk run also needs the trusted
    EN | session, and icloudpd only finds one it recognises when the session
    EN | was written by ITS library, pyicloud_ipd. On an instance where the
    EN | command is installed but that module is not importable - which is
    EN | exactly what `pip install icloudpd` produced here - the picker runs
    EN | on plain pyicloud, the session on disk is pyicloud's, and pressing
    EN | TRANSFER EVERYTHING would meet an authentication failure rather than
    EN | a download. A button that is lit and cannot work is worse than one
    EN | that explains itself.
    FR | Ce que l ecran doit dire de sa propre plomberie : quel moteur a
    FR | repondu, et si un transfert de masse pourrait reellement aboutir.
    FR |
    FR | `bulk_available` VOULAIT DIRE « le binaire icloudpd est sur le
    FR | disque », et ce n etait pas la meme question. Un transfert de masse a
    FR | aussi besoin de la session de confiance, et icloudpd n en reconnait
    FR | une que si elle a ete ecrite par SA bibliotheque, pyicloud_ipd. Sur
    FR | une instance ou la commande est installee mais ou ce module n est pas
    FR | importable - exactement ce qu a produit `pip install icloudpd` ici -
    FR | le selecteur tourne sur pyicloud tout court, la session sur disque
    FR | est celle de pyicloud, et presser TOUT TRANSFERER rencontrerait un
    FR | echec d authentification plutot qu un telechargement. Un bouton
    FR | allume qui ne peut pas fonctionner vaut moins qu un bouton qui
    FR | s explique."""
    command = icloudpd_command(args.icloudpd)
    # EN | Callers that have no session in hand (bulk, forget) pass None; the
    # EN | engine that WOULD answer is still the honest thing to report, and
    # EN | it is what decides whether the session on disk is icloudpd's.
    # FR | Les appelants sans session en main (masse, oubli) passent None ; le
    # FR | moteur qui REPONDRAIT reste la chose honnete a rapporter, et c est
    # FR | lui qui decide si la session sur disque est celle d icloudpd.
    found = available_engines()
    if engine is None and found:
        engine = found[0]
    shares_session = bool(engine) and engine.name == "icloudpd"
    return {"engine": engine.name if engine else "",
            "engines": [e.name for e in found],
            "icloudpd": command,
            "bulk_available": bool(command) and shares_session,
            # EN | Told apart so the screen can say WHICH half is missing.
            # FR | Distingues pour que l ecran dise QUELLE moitie manque.
            "bulk_command": bool(command),
            "bulk_shares_session": shares_session}


def do_link(args, locale: str) -> dict:
    # EN | push_code=True: this is the button a person presses to sign in, and
    # EN | a code is exactly what they are waiting for. The validate path is
    # EN | the one that must never push - see connect().
    # FR | push_code=True : c est le bouton qu une personne presse pour se
    # FR | connecter, et un code est precisement ce qu elle attend. C est le
    # FR | chemin de validation qui ne doit jamais en demander - voir
    # FR | connect().
    api, engine, state, extra = connect(args, locale, push_code=True)
    payload = {**stated(state, locale), **extra,
               "account": (args.apple_id or "").strip(),
               **engine_facts(args, engine)}
    if api is not None and state == "linked":
        payload["trusted"] = bool(getattr(api, "is_trusted_session", False))
    return payload


def do_code(args, locale: str) -> dict:
    """EN | The step no form can take for you: hand Apple the code that was
    EN | sent to a trusted device, then ask for the session to be trusted so
    EN | the next runs - and every icloudpd run - need no code at all.
    FR | L etape qu aucun formulaire ne peut franchir a votre place : donner
    FR | a Apple le code envoye vers un appareil de confiance, puis demander
    FR | que la session soit de confiance pour que les executions suivantes -
    FR | et chaque execution d icloudpd - n exigent plus aucun code."""
    api, engine, state, extra = connect(args, locale)
    if api is None:
        return {**stated(state, locale), **extra, **engine_facts(args, engine)}

    # EN | The code is read from a 0600 file for the same reason the password
    # EN | is: an argv is readable by every process on the box for as long as
    # EN | this one runs. A 2FA code is short-lived and single-use, which
    # EN | makes the exposure small - not zero, and the convention costs
    # EN | nothing. --code stays accepted for a hand-run from a shell.
    # FR | Le code est lu dans un fichier 0600 pour la meme raison que le mot
    # FR | de passe : un argv est lisible par tout processus de la machine
    # FR | tant que celui-ci tourne. Un code 2FA est ephemere et a usage
    # FR | unique, ce qui rend l exposition faible - pas nulle, et la
    # FR | convention ne coute rien. --code reste accepte pour un lancement a
    # FR | la main depuis un terminal.
    # EN | Same guard as do_resend: validating a code against a session Apple
    # EN | has already trusted does not fail usefully, it just produces a
    # EN | confusing refusal on an account that is fine.
    # FR | Meme garde que do_resend : valider un code contre une session
    # FR | qu Apple a deja accordee n echoue pas utilement, cela produit juste
    # FR | un refus deroutant sur un compte qui va bien.
    if not getattr(api, "requires_2fa", False):
        return {**stated("linked", locale),
                **say("already_linked", locale,
                      account=(args.apple_id or "").strip()),
                "account": (args.apple_id or "").strip(),
                "trusted": bool(getattr(api, "is_trusted_session", False)),
                **engine_facts(args, engine)}

    code = re.sub(r"\D", "", args.code or read_text_file(Path(args.code_file)))
    if not code:
        return {**stated("awaiting_2fa", locale), **say("awaiting_2fa", locale),
                **engine_facts(args, engine)}

    try:
        ok = api.validate_2fa_code(code)
    except Exception as exc:  # noqa: BLE001
        return {**stated("error", locale),
                **say("login_failed", locale, detail=str(exc)[:200]),
                **engine_facts(args, engine)}

    if not ok:
        return {**stated("awaiting_2fa", locale),
                **say("code_rejected", locale),
                **engine_facts(args, engine)}

    # EN | TRUSTING THE SESSION IS THE POINT, not a flourish after it. A code
    # EN | that validates without the session becoming trusted leaves the next
    # EN | run facing requires_2fa again - which is the same endless prompt
    # EN | from the user's side, whatever its cause. So the outcome is read
    # EN | back and reported rather than assumed, and a failure to trust is
    # EN | said out loud instead of swallowed.
    # FR | RENDRE LA SESSION DE CONFIANCE EST LE BUT, pas une fioriture qui
    # FR | suit. Un code qui se valide sans que la session devienne de
    # FR | confiance laisse l execution suivante face a requires_2fa - c est,
    # FR | vu de l utilisateur, la meme demande sans fin, quelle qu en soit la
    # FR | cause. Le resultat est donc relu et rapporte plutot que suppose, et
    # FR | un echec a faire confiance est dit tout haut au lieu d etre avale.
    trust_error = ""
    try:
        api.trust_session()
    except Exception as exc:  # noqa: BLE001
        trust_error = str(exc)[:160]

    # EN | Spent. Leaving a used code on disk serves nothing and would be
    # EN | replayed by the next run that finds it.
    # FR | Consomme. Laisser un code use sur disque ne sert a rien et serait
    # FR | rejoue par la premiere execution qui le trouve.
    try:
        Path(args.code_file).unlink()
    except OSError:
        pass

    trusted = bool(getattr(api, "is_trusted_session", False))
    still_asking = bool(getattr(api, "requires_2fa", False))
    account = (args.apple_id or "").strip()

    if still_asking or (not trusted and trust_error):
        return {**stated("awaiting_2fa", locale),
                **say("code_not_trusted", locale,
                      path=str(Path(args.session_dir)),
                      detail=trust_error or "the session is still untrusted"),
                "account": account, "trusted": trusted,
                **engine_facts(args, engine)}

    return {**stated("linked", locale),
            **say("linked", locale, account=account, engine=engine.name),
            "account": account,
            "trusted": trusted,
            **engine_facts(args, engine)}


def do_forget(args, locale: str) -> dict:
    """EN | Erase the stored session and start over. This is the way out of
    EN | every state the two previous attempts at the 2FA flow could strand a
    EN | person in, and it needed to exist from the start.
    EN |
    EN | A cached session is not all-or-nothing. It can answer requires_2fa
    EN | while being valid enough that the library never re-authenticates -
    EN | so Apple is never asked for anything and no code is ever sent. It
    EN | can also go on reporting a linked account after the Apple ID
    EN | password has been changed underneath it. Neither state can be
    EN | argued with from the outside; both end the moment the session files
    EN | are gone and the next CONNECT is a real sign-in.
    EN |
    EN | The password file is deliberately left alone: forgetting the session
    EN | is not forgetting the account, and making a person retype their
    EN | Apple password to clear a cookie would be its own small cruelty.
    FR | Efface la session memorisee et repart de zero. C est la sortie de
    FR | chacun des etats dans lesquels les deux tentatives precedentes sur
    FR | le flux 2FA pouvaient enfermer quelqu un, et cela aurait du exister
    FR | des le depart.
    FR |
    FR | Une session en cache n est pas tout ou rien. Elle peut repondre
    FR | requires_2fa tout en etant assez valide pour que la bibliotheque ne
    FR | se reauthentifie jamais - Apple n est alors sollicite de rien et
    FR | aucun code ne part. Elle peut aussi continuer d annoncer un compte
    FR | lie apres que le mot de passe de l identifiant Apple a ete change
    FR | dessous. Ni l un ni l autre ne se discute de l exterieur ; les deux
    FR | cessent des que les fichiers de session ont disparu et que le
    FR | CONNECTER suivant est une vraie connexion.
    FR |
    FR | Le fichier du mot de passe est volontairement epargne : oublier la
    FR | session n est pas oublier le compte, et faire retaper son mot de
    FR | passe Apple a quelqu un pour vider un cookie serait une petite
    FR | cruaute gratuite."""
    removed = 0
    session = Path(args.session_dir)
    if session.is_dir():
        for item in session.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                removed += 1
            except OSError:
                pass
    return {**stated("not_configured", locale),
            **say("session_forgotten", locale, removed=removed),
            "forgotten": removed,
            **engine_facts(args, None)}


def do_resend(args, locale: str) -> dict:
    """EN | Ask Apple for a NEW verification code, on purpose. This is the
    EN | only place in this program that calls request_2fa_code(), because
    EN | each call invalidates whatever code is already in the user's hand -
    EN | see the comment on connect() for the loop that caused.
    FR | Demander a Apple un NOUVEAU code de verification, exprès. C est le
    FR | seul endroit de ce programme qui appelle request_2fa_code(), parce
    FR | que chaque appel invalide le code deja entre les mains de
    FR | l utilisateur - voir le commentaire de connect() pour la boucle que
    FR | cela a provoquee."""
    api, engine, state, extra = connect(args, locale)
    if api is None:
        return {**stated(state, locale), **extra, **engine_facts(args, engine)}

    # EN | ASK APPLE FIRST WHETHER A CODE IS EVEN WANTED. This used to push
    # EN | unconditionally and then report `awaiting_2fa` unconditionally,
    # EN | which on a session Apple has already trusted is simply false: the
    # EN | push is a no-op, no code is sent - correctly - and the screen goes
    # EN | on saying "code required, one is on its way" to somebody who is
    # EN | fully connected. They then wait for a code that has no reason to
    # EN | exist, which is indistinguishable from the feature being broken.
    # EN | The state reported here is now the one the library reports, never
    # EN | the one this function hoped for.
    # FR | DEMANDER D ABORD A APPLE SI UN CODE EST SEULEMENT SOUHAITE. Cette
    # FR | fonction poussait inconditionnellement puis annoncait
    # FR | `awaiting_2fa` inconditionnellement, ce qui, sur une session
    # FR | qu Apple a deja accordee, est simplement faux : la demande ne fait
    # FR | rien, aucun code n est envoye - a juste titre - et l ecran continue
    # FR | d annoncer « code requis, un nouveau arrive » a quelqu un de
    # FR | parfaitement connecte. Cette personne attend alors un code qui n a
    # FR | aucune raison d exister, ce qui ne se distingue pas d une fonction
    # FR | en panne. L etat rapporte ici est desormais celui que rapporte la
    # FR | bibliotheque, jamais celui que cette fonction esperait.
    if not getattr(api, "requires_2fa", False):
        return {**stated("linked", locale),
                **say("already_linked", locale,
                      account=(args.apple_id or "").strip()),
                "account": (args.apple_id or "").strip(),
                "trusted": bool(getattr(api, "is_trusted_session", False)),
                **engine_facts(args, engine)}

    try:
        api.request_2fa_code()
    except Exception as exc:  # noqa: BLE001
        return {**stated("awaiting_2fa", locale),
                **say("login_failed", locale, detail=str(exc)[:200]),
                **engine_facts(args, engine)}

    return {**stated("awaiting_2fa", locale), **say("code_resent", locale),
            **engine_facts(args, engine)}


# ===========================================================================
# EN | THE INDEX - what the library holds
# FR | L INDEX - ce que contient la photothèque
# ===========================================================================
VIDEO_EXT = {"mov", "mp4", "m4v", "avi", "mkv", "3gp", "hevc"}


def classify(filename: str, item_type: str) -> str:
    """EN | 'photo' or 'video'. item_type is Apple's own word ('image' /
    EN | 'movie'); the extension is the fallback for a record that has none,
    EN | which happens on older shared assets.
    FR | 'photo' ou 'video'. item_type est le mot d Apple (« image » /
    FR | « movie ») ; l extension sert de repli pour un enregistrement qui
    FR | n en porte pas, ce qui arrive sur d anciens elements partages."""
    kind = (item_type or "").strip().lower()
    if "movie" in kind or "video" in kind:
        return "video"
    if "image" in kind or "photo" in kind:
        return "photo"
    ext = (filename or "").rsplit(".", 1)[-1].lower()
    return "video" if ext in VIDEO_EXT else "photo"


def asset_row(photo) -> dict:
    """EN | One library item, reduced to what the picker and the ledger need.
    EN | Every field is read defensively: Apple's records are not uniform
    EN | across the decade of assets a real library spans, and the two
    EN | engines do not expose them identically either.
    FR | Un element de la photothèque, reduit a ce dont le selecteur et le
    FR | registre ont besoin. Chaque champ est lu defensivement : les
    FR | enregistrements d Apple ne sont pas uniformes sur la decennie
    FR | d elements que couvre une vraie photothèque, et les deux moteurs ne
    FR | les exposent pas identiquement non plus."""
    def attr(name, default=None):
        try:
            return getattr(photo, name)
        except Exception:  # noqa: BLE001
            return default

    filename = attr("filename") or ""
    try:
        size = int(attr("size") or 0)
    except (TypeError, ValueError):
        size = 0
    created = ""
    stamp = attr("created") or attr("asset_date")
    try:
        created = stamp.isoformat(timespec="seconds")
    except Exception:  # noqa: BLE001
        created = str(stamp or "")[:19]
    item_type = str(attr("item_type") or "")
    return {"id": photo.id,
            "filename": filename or f"{str(photo.id)[:12]}.bin",
            "kind": classify(filename, item_type),
            "size": size,
            "created": created}


def do_scan(args, locale: str, status_path: Path) -> dict:
    """EN | Walk the whole library into the index. Resumable by construction:
    EN | the index is a dict keyed by asset id, so a run interrupted halfway
    EN | leaves a usable index and the next run simply adds what is missing.
    EN | Progress is published every PROGRESS_EVERY items, because the only
    EN | thing worse than a long scan is a long scan that looks frozen.
    FR | Parcourt toute la photothèque vers l index. Reprenable par
    FR | construction : l index est un dictionnaire indexe par id d element,
    FR | donc une execution interrompue a mi-chemin laisse un index
    FR | utilisable et la suivante ajoute simplement ce qui manque. La
    FR | progression est publiee tous les PROGRESS_EVERY elements, parce que
    FR | la seule chose pire qu un long scan est un long scan qui a l air
    FR | fige."""
    PROGRESS_EVERY = 250

    api, engine, state, extra = connect(args, locale)
    if api is None or state != "linked":
        return {**stated(state, locale), **extra, **engine_facts(args, engine)}

    index_path = Path(args.index_file)
    index = load_json(index_path, {})
    seen = set()
    done = 0

    try:
        album = engine.assets(api, args.photo_retries, args.photo_retry_delay)
        total_hint = engine.count(album)
        for photo in album:
            try:
                row = asset_row(photo)
            except Exception:  # noqa: BLE001 - one bad record must not end it
                continue
            index[row["id"]] = row
            seen.add(row["id"])
            done += 1
            if done % PROGRESS_EVERY == 0:
                save_json(index_path, index)
                save_json(status_path,
                          {**stated("scanning", locale),
                           **say("scan_running", locale, done=done),
                           "indexed": done, "total_hint": total_hint,
                           **engine_facts(args, engine),
                           "generated": datetime.now().isoformat(timespec="seconds")})
    except Exception as exc:  # noqa: BLE001
        save_json(index_path, index)
        kind, detail = photo_fault(exc)
        return {**stated("indexing" if kind == "indexing" else "error", locale),
                **(say("indexing", locale) if kind == "indexing"
                   else say("failure", locale, detail=detail)),
                **engine_facts(args, engine)}

    # EN | An asset that vanished from iCloud since the last scan - deleted
    # EN | from a phone, or released by this very program - must leave the
    # EN | index, or the picker keeps offering a photo that is not there.
    # FR | Un element disparu d iCloud depuis le dernier scan - supprime
    # FR | depuis un telephone, ou libere par ce programme meme - doit
    # FR | quitter l index, sinon le selecteur continue de proposer une photo
    # FR | qui n existe plus.
    for gone in [k for k in index if k not in seen]:
        index.pop(gone, None)

    save_json(index_path, index)
    return {**index_summary(index, args, locale), "scanned": done,
            **engine_facts(args, engine)}


def index_summary(index: dict, args, locale: str) -> dict:
    photos = sum(1 for r in index.values() if r.get("kind") == "photo")
    videos = sum(1 for r in index.values() if r.get("kind") == "video")
    size = sum(int(r.get("size") or 0) for r in index.values())
    ledger = load_json(Path(args.ledger_file), {})
    stored = [k for k in index if k in ledger]
    stored_size = sum(int(index[k].get("size") or 0) for k in stored)
    return {**stated("linked", locale),
            **say("scan_done", locale, photos=photos, videos=videos,
                  size=human(size)),
            "photos": photos,
            "videos": videos,
            "items": photos + videos,
            "bytes": size,
            "size_human": human(size),
            "stored_items": len(stored),
            "stored_bytes": stored_size,
            "stored_human": human(stored_size),
            "pending_items": (photos + videos) - len(stored),
            "pending_bytes": size - stored_size,
            "pending_human": human(size - stored_size)}


# ===========================================================================
# EN | THE PICKER PAGE - thumbnails, one screenful at a time
# FR | LA PAGE DU SELECTEUR - des miniatures, un ecran a la fois
# ===========================================================================
def sorted_index(index: dict, newest_first: bool = True) -> list:
    rows = list(index.values())
    rows.sort(key=lambda r: (r.get("created") or "", r.get("filename") or ""),
              reverse=newest_first)
    return rows


def do_page(args, locale: str) -> dict:
    """EN | Materialise the thumbnails for ONE page and describe it in a JSON
    EN | the browser reads. Nothing outside the page being looked at is ever
    EN | written to /config/www - see the privacy note at the top.
    FR | Materialise les miniatures d UNE page et la decrit dans un JSON lu
    FR | par le navigateur. Rien d autre que la page regardee n est jamais
    FR | ecrit dans /config/www - voir la note de confidentialite en tete."""
    index = load_json(Path(args.index_file), {})
    if not index:
        return {**stated("linked", locale), **say("index_empty", locale),
                "items": [], "offset": 0, "limit": args.limit, "matching": 0}

    ledger = load_json(Path(args.ledger_file), {})
    rows = sorted_index(index)

    wanted = (args.filter or "all").lower()
    if wanted == "photo":
        rows = [r for r in rows if r.get("kind") == "photo"]
    elif wanted == "video":
        rows = [r for r in rows if r.get("kind") == "video"]
    elif wanted == "pending":
        rows = [r for r in rows if r["id"] not in ledger]
    elif wanted == "stored":
        rows = [r for r in rows if r["id"] in ledger]

    matching = len(rows)
    offset = max(0, int(args.offset or 0))
    limit = max(1, min(int(args.limit or 60), 200))
    window = rows[offset:offset + limit]

    thumbs_dir = Path(args.thumbs_dir)
    salt = thumb_salt(Path(args.salt_file))

    # EN | Only the ids of THIS page are fetched, and only those not already
    # EN | on disk from a previous visit. Paging back and forth therefore
    # EN | costs nothing after the first pass.
    # FR | Seuls les ids de CETTE page sont charges, et seulement ceux qui ne
    # FR | sont pas deja sur disque depuis une visite precedente. Feuilleter
    # FR | d avant en arriere ne coute donc rien apres le premier passage.
    needed = {r["id"]: thumbs_dir / thumb_name(salt, r["id"]) for r in window}
    missing = {pid: dest for pid, dest in needed.items() if not dest.exists()}

    fetched = 0
    if missing:
        api, engine, state, extra = connect(args, locale)
        if api is None or state != "linked":
            return {**stated(state, locale), **extra,
                    "items": [], "offset": offset, "limit": limit,
                    "matching": matching}
        try:
            thumbs_dir.mkdir(parents=True, exist_ok=True)
            for photo in engine.assets(api, args.photo_retries, args.photo_retry_delay):
                if photo.id not in missing:
                    continue
                dest = missing[photo.id]
                try:
                    response = engine.download(photo, "thumb")
                    with open(dest, "wb") as handle:
                        shutil.copyfileobj(response.raw, handle)
                    fetched += 1
                except Exception:  # noqa: BLE001 - a missing thumb is a hole
                    try:                                  # in the grid, not a
                        dest.unlink()                     # failed page
                    except OSError:
                        pass
                    fetched += 1
                if fetched >= len(missing):
                    break
        except Exception as exc:  # noqa: BLE001
            return {**stated("error", locale),
                    **say("failure", locale, detail=str(exc)[:200]),
                    "items": [], "offset": offset, "limit": limit,
                    "matching": matching}

    items = []
    for row in window:
        name = thumb_name(salt, row["id"])
        items.append({"id": row["id"],
                      "filename": row.get("filename"),
                      "kind": row.get("kind"),
                      "size": row.get("size"),
                      "size_human": human(int(row.get("size") or 0)),
                      "created": row.get("created"),
                      "stored": row["id"] in ledger,
                      "thumb": f"{args.thumbs_url}/{name}"
                               if (thumbs_dir / name).exists() else ""})

    return {**stated("linked", locale),
            "items": items,
            "offset": offset,
            "limit": limit,
            "matching": matching,
            "filter": wanted,
            "fetched": fetched}


def do_purge(args, locale: str) -> dict:
    """EN | Erase every materialised thumbnail. Offered as a button because
    EN | the directory is served without authentication.
    FR | Efface toutes les miniatures materialisees. Propose en bouton parce
    FR | que le repertoire est servi sans authentification."""
    removed = 0
    thumbs = Path(args.thumbs_dir)
    if thumbs.is_dir():
        for item in thumbs.glob("*.jpg"):
            try:
                item.unlink()
                removed += 1
            except OSError:
                pass
    return {"purged": removed}


# ===========================================================================
# EN | TRANSFER - the hand-picked path
# FR | TRANSFERT - le chemin au cas par cas
# ===========================================================================
def selection(args) -> list:
    """EN | The chosen ids. They arrive base64-encoded for the same reason
    EN | vssp_assign_apply.py takes its payload that way: a list of asset ids
    EN | is far longer than the 255 characters an input_text holds, and the
    EN | filenames beside them carry apostrophes and accents.
    FR | Les ids choisis. Ils arrivent encodes en base64 pour la meme raison
    FR | que vssp_assign_apply.py recoit le sien ainsi : une liste d ids
    FR | depasse de loin les 255 caracteres d un input_text, et les noms de
    FR | fichiers a cote portent apostrophes et accents."""
    if not args.json_b64:
        return []
    try:
        raw = base64.b64decode(args.json_b64).decode("utf-8")
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return []
    if isinstance(data, list):
        return [str(x) for x in data if x]
    if isinstance(data, dict):
        return [str(x) for x in (data.get("ids") or []) if x]
    return []


def destination_path(dest_root: Path, row: dict) -> Path:
    """EN | <dest>/<YYYY>/<MM>/<filename> - the same shape icloudpd writes
    EN | with --folder-structure {:%Y/%m}, so the two paths fill one tree
    EN | rather than two. The asset id is appended when a name is already
    EN | taken: Apple reuses IMG_0001.HEIC across years and devices, and
    EN | collapsing two different photos onto one path would lose one of them
    EN | silently, which is the one failure this program must never have.
    FR | <dest>/<AAAA>/<MM>/<nom> - exactement la forme qu ecrit icloudpd avec
    FR | --folder-structure {:%Y/%m}, pour que les deux chemins remplissent un
    FR | seul arbre et non deux. L id de l element est ajoute quand un nom est
    FR | deja pris : Apple reutilise IMG_0001.HEIC d une annee et d un
    FR | appareil a l autre, et faire tomber deux photos differentes sur un
    FR | meme chemin en perdrait une en silence, le seul echec que ce
    FR | programme ne doit jamais avoir."""
    created = (row.get("created") or "")[:7]
    year, _, month = created.partition("-")
    # EN | Through safe_component as well: these two come from a date string
    # EN | in a record Apple supplied, and a path segment built from remote
    # EN | data is never pasted into a filesystem path unchecked, however
    # EN | unlikely a hostile value is.
    # FR | Par safe_component egalement : ces deux-la viennent d une chaine de
    # FR | date dans un enregistrement fourni par Apple, et un segment de
    # FR | chemin construit depuis une donnee distante n est jamais colle
    # FR | dans un chemin de fichiers sans controle, aussi improbable soit une
    # FR | valeur hostile.
    folder = (dest_root / safe_component(year, "undated")
              / safe_component(month, "00"))
    name = safe_component(row.get("filename"), f"{str(row['id'])[:12]}.bin")
    candidate = folder / name
    if candidate.exists():
        stem, dot, ext = name.rpartition(".")
        marker = re.sub(r"[^A-Za-z0-9]", "", str(row["id"]))[:8]
        name = f"{stem or name}-{marker}{dot}{ext}" if dot else f"{name}-{marker}"
        candidate = folder / name
    return candidate


def writable(dest_root: Path, locale: str, args=None):
    """EN | True, or the payload that says why not.
    EN |
    EN | Writable is not the same as SAFE, and both transfer paths ask for
    EN | both. The container's own filesystem is writable, roomy and
    EN | disposable: a library transferred there vanishes with the next pod
    EN | restart while the ledger goes on claiming it is stored - and the
    EN | ledger is what authorises deleting the originals from iCloud. That
    EN | is the one failure this whole feature exists to prevent, so an
    EN | unmounted destination is refused here rather than reported later.
    FR | Inscriptible n est pas la meme chose que SUR, et les deux chemins de
    FR | transfert exigent les deux. Le systeme de fichiers du conteneur est
    FR | inscriptible, vaste et jetable : une photothèque qu on y transfere
    FR | disparait au redemarrage suivant du pod tandis que le registre
    FR | continue d affirmer qu elle est stockee - et c est le registre qui
    FR | autorise la suppression des originaux dans iCloud. C est l unique
    FR | echec que toute cette fonction existe pour empecher : une
    FR | destination non montee est donc refusee ici, pas signalee apres."""
    try:
        dest_root.mkdir(parents=True, exist_ok=True)
        probe = dest_root / ".vssp_write_test"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return False, {**stated("error", locale),
                       **say("dest_unwritable", locale, dest=str(dest_root),
                             detail=str(exc)[:120])}

    if args is not None:
        storage = do_storage(args, locale)
        if storage.get("ephemeral"):
            return False, {**stated("error", locale),
                           **{k: v for k, v in storage.items()
                              if k in ("message", "message_key",
                                       "message_vars")},
                           "storage": storage}
    return True, None


def do_transfer(args, locale: str, status_path: Path) -> dict:
    """EN | Download the chosen originals and record each one in the ledger.
    EN | The ledger is written after EVERY item, not at the end: a transfer
    EN | interrupted by a restart must leave behind the truth about what is
    EN | already on disk, because that record is what later authorises a
    EN | deletion from iCloud.
    FR | Telecharge les originaux choisis et inscrit chacun au registre. Le
    FR | registre est ecrit apres CHAQUE element, pas a la fin : un transfert
    FR | interrompu par un redemarrage doit laisser derriere lui la verite
    FR | sur ce qui est deja sur disque, parce que c est cet enregistrement
    FR | qui autorisera plus tard une suppression dans iCloud."""
    wanted = set(selection(args))
    if not wanted:
        return {**stated("linked", locale), **say("nothing_selected", locale)}

    dest_root = Path(args.dest)
    ok, refusal = writable(dest_root, locale, args)
    if not ok:
        return refusal

    index = load_json(Path(args.index_file), {})
    ledger_path = Path(args.ledger_file)
    ledger = load_json(ledger_path, {})

    api, engine, state, extra = connect(args, locale)
    if api is None or state != "linked":
        return {**stated(state, locale), **extra, **engine_facts(args, engine)}

    done = 0
    failed = 0
    written = 0
    first_fault = None
    total = len(wanted)
    salt = thumb_salt(Path(args.salt_file))
    thumbs_dir = Path(args.thumbs_dir)

    try:
        for photo in engine.assets(api, args.photo_retries, args.photo_retry_delay):
            if photo.id not in wanted:
                continue
            row = index.get(photo.id) or asset_row(photo)
            target = destination_path(dest_root, row)
            partial = target.with_suffix(target.suffix + ".part")
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                # EN | Written to a .part first and renamed once complete, so
                # EN | an interrupted download can never be mistaken for a
                # EN | stored file by the release step.
                # FR | Ecrit d abord en .part puis renomme une fois complet,
                # FR | pour qu un telechargement interrompu ne puisse jamais
                # FR | passer pour un fichier stocke aupres de l etape de
                # FR | liberation.
                response = engine.download(photo, "original")
                with open(partial, "wb") as handle:
                    shutil.copyfileobj(response.raw, handle)
                partial.replace(target)
                on_disk = target.stat().st_size
                written += on_disk
                done += 1
                ledger[photo.id] = {
                    "path": str(target),
                    "size": on_disk,
                    "expected": int(row.get("size") or 0),
                    "filename": row.get("filename"),
                    "kind": row.get("kind"),
                    "created": row.get("created"),
                    "at": datetime.now().isoformat(timespec="seconds"),
                    "released": False,
                }
                save_json(ledger_path, ledger)
                # EN | The thumbnail has done its job: the item is now on
                # EN | disk, so the unauthenticated copy can go.
                # FR | La miniature a fait son travail : l element est sur
                # FR | disque, la copie non authentifiee peut partir.
                try:
                    (thumbs_dir / thumb_name(salt, photo.id)).unlink()
                except OSError:
                    pass
            except Exception as exc:  # noqa: BLE001 - one item, not the batch
                failed += 1
                # EN | KEEP THE FIRST REASON. A counter that says "3
                # EN | failure(s)" and nothing else is not a report: it was
                # EN | what hid, for an evening, that every single item was
                # EN | failing on the same sentence from Apple. One item may
                # EN | fail for its own reason without ending the batch, but
                # EN | the batch must carry at least one of them back.
                # FR | GARDER LA PREMIERE RAISON. Un compteur qui annonce
                # FR | « 3 echec(s) » et rien d autre n est pas un rapport :
                # FR | c est lui qui a masque, une soiree durant, que chaque
                # FR | element echouait sur la meme phrase d Apple. Un
                # FR | element peut echouer pour sa propre raison sans
                # FR | interrompre le lot, mais le lot doit en rapporter au
                # FR | moins une.
                if not first_fault:
                    first_fault = photo_fault(exc)
                try:
                    partial.unlink()
                except OSError:
                    pass

            if (done + failed) % 5 == 0:
                save_json(status_path,
                          {**stated("transferring", locale),
                           **say("transfer_running", locale, done=done,
                                 total=total, size=human(written)),
                           "transferred": done, "failed": failed,
                           "generated": datetime.now().isoformat(timespec="seconds")})
            if done + failed >= total:
                break
    except Exception as exc:  # noqa: BLE001
        save_json(ledger_path, ledger)
        return {**stated("error", locale),
                **say("failure", locale, detail=str(exc)[:200])}

    save_json(ledger_path, ledger)
    summary = index_summary(index, args, locale)
    # EN | Nothing moved and every item failed the same way: report THAT,
    # EN | not a tally. An all-failed batch during Apple's indexing is a
    # EN | wait, and saying so is the difference between "try again in a few
    # EN | minutes" and an evening spent re-authenticating.
    # FR | Rien n a bouge et tous les elements ont echoue pareil : rapporter
    # FR | CELA, pas un decompte. Un lot entierement en echec pendant
    # FR | l indexation d Apple est une attente, et le dire fait la
    # FR | difference entre « reessayez dans quelques minutes » et une
    # FR | soiree passee a se reconnecter.
    if done == 0 and first_fault:
        kind, detail = first_fault
        summary.update(**stated("indexing" if kind == "indexing" else "error",
                                locale),
                       **(say("indexing", locale) if kind == "indexing"
                          else say("transfer_failed", locale, failed=failed,
                                   detail=detail)),
                       transferred=0, failed=failed, written=0,
                       **engine_facts(args, engine))
        return summary

    summary.update(**say("transfer_done", locale, done=done,
                         size=human(written), dest=str(dest_root),
                         failed=failed),
                   transferred=done, failed=failed, written=written,
                   fault=(first_fault[1] if first_fault else ""),
                   **engine_facts(args, engine))
    return summary


# ===========================================================================
# EN | BULK - the icloudpd command, for everything still missing
# FR | EN MASSE - la commande icloudpd, pour tout ce qui manque encore
# ===========================================================================
def do_bulk(args, locale: str, status_path: Path) -> dict:
    """EN | Hand the whole job to icloudpd. This is the path to take when the
    EN | answer to "which ones?" is "all of them": it resumes, it skips what
    EN | is already on disk, and with --keep-icloud-recent-days it frees
    EN | iCloud in the same pass instead of needing a second trip.
    EN |
    EN | NO PASSWORD ON THIS COMMAND LINE. The session written by the link
    EN | step is already in --cookie-directory, and icloudpd reads it from
    EN | there. If it has expired, icloudpd exits rather than prompting (its
    EN | stdin is closed), and the message says to link again - which is the
    EN | correct outcome, not a failure to work around.
    EN |
    EN | WHY THE OUTPUT IS READ LINE BY LINE. icloudpd has no machine-readable
    EN | output, so progress is counted from the lines it prints with
    EN | --only-print-filenames off and the progress bar suppressed. That is a
    EN | count for a human watching a screen, not an accounting record: the
    EN | ledger below is rebuilt from the files that actually landed.
    FR | Confie tout le travail a icloudpd. C est le chemin a prendre quand la
    FR | reponse a « lesquels ? » est « tous » : il reprend, il saute ce qui
    FR | est deja sur disque, et avec --keep-icloud-recent-days il libere
    FR | iCloud dans la meme passe au lieu d exiger un second voyage.
    FR |
    FR | AUCUN MOT DE PASSE SUR CETTE LIGNE DE COMMANDE. La session ecrite par
    FR | l etape de liaison est deja dans --cookie-directory, et icloudpd l y
    FR | lit. Si elle a expire, icloudpd sort au lieu d interroger (son stdin
    FR | est ferme), et le message dit de relier - ce qui est le bon
    FR | resultat, pas un echec a contourner.
    FR |
    FR | POURQUOI LA SORTIE EST LUE LIGNE A LIGNE. icloudpd n a aucune sortie
    FR | lisible par machine : la progression est donc comptee depuis les
    FR | lignes qu il imprime, barre de progression supprimee. C est un
    FR | compteur pour un humain qui regarde un ecran, pas une comptabilite :
    FR | le registre ci-dessous est reconstruit depuis les fichiers reellement
    FR | arrives."""
    facts = engine_facts(args, None)
    if not facts["bulk_command"]:
        return {**stated("error", locale), **say("bulk_unavailable", locale),
                **facts}
    # EN | The command is there but the session on disk is not one it can
    # EN | read - see engine_facts(). Refused here with the reason, rather
    # EN | than handed to icloudpd to fail against Apple.
    # FR | La commande est la mais la session sur disque n est pas une qu elle
    # FR | sait lire - voir engine_facts(). Refuse ici avec la raison, plutot
    # FR | que confie a icloudpd pour echouer contre Apple.
    if not facts["bulk_shares_session"]:
        return {**stated("error", locale),
                **say("bulk_no_shared_session", locale), **facts}
    command = facts["icloudpd"]

    account = (args.apple_id or "").strip()
    if not account:
        return {**stated("not_configured", locale),
                **say("no_credentials", locale)}

    dest_root = Path(args.dest)
    ok, refusal = writable(dest_root, locale, args)
    if not ok:
        return refusal

    argv = [command,
            "--username", account,
            "--directory", str(dest_root),
            "--cookie-directory", str(Path(args.session_dir)),
            # EN | The same tree the hand-picked path writes into, so one
            # EN | library does not end up in two shapes.
            # FR | Le meme arbre que celui ou ecrit le chemin au cas par cas,
            # FR | pour qu une photothèque ne finisse pas en deux formes.
            "--folder-structure", "{:%Y/%m}",
            "--no-progress-bar"]
    # EN | NO --password AND NO --password-provider. The trusted session in
    # EN | --cookie-directory is what authorises this run, and a valid session
    # EN | means no provider is consulted at all. Pinning
    # EN | `--password-provider parameter` without a --password would hand
    # EN | icloudpd a provider with nothing in it, which can fail a run that
    # EN | the session alone would have carried. Leaving the default order
    # EN | (parameter, keyring, console) costs nothing here because stdin is
    # EN | /dev/null: the console provider reads EOF and the run stops with a
    # EN | message, rather than hanging on a prompt nobody can see.
    # FR | PAS DE --password NI DE --password-provider. C est la session de
    # FR | confiance dans --cookie-directory qui autorise cette execution, et
    # FR | une session valide veut dire qu aucun fournisseur n est consulte.
    # FR | Figer `--password-provider parameter` sans --password confierait a
    # FR | icloudpd un fournisseur vide, ce qui peut faire echouer une
    # FR | execution que la session seule aurait portee. Laisser l ordre par
    # FR | defaut (parameter, keyring, console) ne coute rien ici puisque
    # FR | stdin est /dev/null : le fournisseur console lit EOF et
    # FR | l execution s arrete avec un message, au lieu de se bloquer sur une
    # FR | invite que personne ne voit.
    if args.skip_videos:
        argv.append("--skip-videos")
    if args.skip_photos:
        argv.append("--skip-photos")
    if args.until_found > 0:
        argv += ["--until-found", str(args.until_found)]
    # EN | THE ONE IRREVERSIBLE FLAG. It tells icloudpd to delete in iCloud
    # EN | what it has just stored, keeping the last N days. It is only ever
    # EN | added when the console explicitly asked for it, never by default.
    # FR | LE SEUL DRAPEAU IRREVERSIBLE. Il dit a icloudpd de supprimer dans
    # FR | iCloud ce qu il vient de stocker, en gardant les N derniers jours.
    # FR | Il n est ajoute que si la console l a explicitement demande, jamais
    # FR | par defaut.
    if args.free_icloud_days >= 0:
        argv += ["--keep-icloud-recent-days", str(args.free_icloud_days)]

    downloaded = 0
    tail = []
    try:
        process = subprocess.Popen(argv, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   stdin=subprocess.DEVNULL,
                                   text=True, bufsize=1)
    except OSError as exc:
        return {**stated("error", locale),
                **say("bulk_failed", locale, code="-", detail=str(exc)[:200])}

    for line in process.stdout:
        line = line.strip()
        if not line:
            continue
        tail = (tail + [line])[-8:]
        if "Download" in line or "Downloaded" in line:
            downloaded += 1
            if downloaded % 10 == 0:
                save_json(status_path,
                          {**stated("transferring", locale),
                           **say("bulk_running", locale, done=downloaded),
                           "downloaded": downloaded,
                           "generated": datetime.now().isoformat(timespec="seconds")})
    code = process.wait()

    if code != 0:
        return {**stated("error", locale),
                **say("bulk_failed", locale, code=code,
                      detail=" | ".join(tail)[:200])}

    # EN | icloudpd wrote files this program did not place, so the ledger is
    # EN | reconciled against the tree rather than trusted from the run.
    # FR | icloudpd a ecrit des fichiers que ce programme n a pas poses : le
    # FR | registre est donc reconcilie avec l arbre plutot que cru sur
    # FR | parole.
    matched = reconcile_ledger(args)

    index = load_json(Path(args.index_file), {})
    summary = index_summary(index, args, locale)
    key = "bulk_done_freed" if args.free_icloud_days >= 0 else "bulk_done"
    summary.update(**say(key, locale, done=downloaded, dest=str(dest_root),
                         days=args.free_icloud_days),
                   downloaded=downloaded, reconciled=matched,
                   **engine_facts(args, None))
    return summary


def reconcile_ledger(args) -> int:
    """EN | Walk the destination tree and record, for every indexed asset, the
    EN | file that bears its name. This is what makes a bulk run count as
    EN | "stored" in the picker, and what lets RELEASE later verify an item
    EN | icloudpd downloaded rather than only the ones picked by hand.
    EN | Matching is by filename and size, which is the only common ground
    EN | between an index entry and a file icloudpd named on its own.
    FR | Parcourt l arbre de destination et inscrit, pour chaque element
    FR | indexe, le fichier qui porte son nom. C est ce qui fait compter une
    FR | execution de masse comme « stocke » dans le selecteur, et ce qui
    FR | permet plus tard a LIBERER de verifier un element telecharge par
    FR | icloudpd et pas seulement ceux choisis a la main. La correspondance
    FR | se fait par nom de fichier et taille, le seul terrain commun entre
    FR | une entree d index et un fichier nomme par icloudpd."""
    index = load_json(Path(args.index_file), {})
    if not index:
        return 0
    ledger_path = Path(args.ledger_file)
    ledger = load_json(ledger_path, {})

    on_disk = {}
    dest_root = Path(args.dest)
    if dest_root.is_dir():
        for path in dest_root.rglob("*"):
            if path.is_file() and not path.name.endswith(".part"):
                on_disk.setdefault(path.name, []).append(path)

    matched = 0
    for pid, row in index.items():
        if pid in ledger and not ledger[pid].get("released"):
            continue
        name = row.get("filename") or ""
        for candidate in on_disk.get(name, []):
            try:
                size = candidate.stat().st_size
            except OSError:
                continue
            expected = int(row.get("size") or 0)
            # EN | icloudpd may convert or add EXIF, so an exact size match is
            # EN | not required - a 5% window keeps a converted HEIC matched
            # EN | while still refusing a different photo of the same name.
            # FR | icloudpd peut convertir ou ajouter de l EXIF : une taille
            # FR | exacte n est donc pas exigee - une fenetre de 5 % garde un
            # FR | HEIC converti apparie tout en refusant une autre photo
            # FR | portant le meme nom.
            if expected and abs(size - expected) > max(expected * 0.05, 1024):
                continue
            ledger[pid] = {"path": str(candidate), "size": size,
                           "expected": expected,
                           "filename": name, "kind": row.get("kind"),
                           "created": row.get("created"),
                           "at": datetime.now().isoformat(timespec="seconds"),
                           "by": "icloudpd", "released": False}
            matched += 1
            break

    save_json(ledger_path, ledger)
    return matched


# ===========================================================================
# EN | RELEASE - the only irreversible step, and the narrowest
# FR | LIBERER - la seule etape irreversible, et la plus etroite
# ===========================================================================
def do_release(args, locale: str) -> dict:
    """EN | Delete from iCloud, and ONLY what can be proven to exist here.
    EN | The proof is deliberately narrow: the ledger names a path, that path
    EN | exists, and its size on disk equals the size recorded at transfer.
    EN | An item that fails any of the three is skipped and counted, never
    EN | deleted.
    FR | Supprime dans iCloud, et UNIQUEMENT ce dont l existence ici peut
    FR | etre prouvee. La preuve est volontairement etroite : le registre
    FR | nomme un chemin, ce chemin existe, et sa taille sur disque egale la
    FR | taille enregistree au transfert. Un element qui echoue a l un des
    FR | trois est ignore et compte, jamais supprime."""
    wanted = set(selection(args))
    if not wanted:
        return {**stated("linked", locale), **say("nothing_selected", locale)}

    ledger_path = Path(args.ledger_file)
    ledger = load_json(ledger_path, {})

    verified = {}
    for pid in wanted:
        entry = ledger.get(pid)
        if not entry or entry.get("released"):
            continue
        try:
            stored = Path(entry["path"])
            if stored.is_file() and stored.stat().st_size == int(entry.get("size") or -1):
                verified[pid] = entry
        except (OSError, KeyError, ValueError, TypeError):
            continue

    skipped = len(wanted) - len(verified)
    if not verified:
        return {**stated("linked", locale),
                **say("release_unverified", locale),
                "released": 0, "skipped": skipped}

    api, engine, state, extra = connect(args, locale)
    if api is None or state != "linked":
        return {**stated(state, locale), **extra, **engine_facts(args, engine)}

    done = 0
    freed = 0
    try:
        for photo in engine.assets(api, args.photo_retries, args.photo_retry_delay):
            if photo.id not in verified:
                continue
            try:
                engine.delete(photo)
            except Exception:  # noqa: BLE001 - one refusal is not the batch
                skipped += 1
                continue
            entry = verified[photo.id]
            entry["released"] = True
            entry["released_at"] = datetime.now().isoformat(timespec="seconds")
            ledger[photo.id] = entry
            freed += int(entry.get("size") or 0)
            done += 1
            save_json(ledger_path, ledger)
            if done >= len(verified):
                break
    except Exception as exc:  # noqa: BLE001
        save_json(ledger_path, ledger)
        return {**stated("error", locale),
                **say("failure", locale, detail=str(exc)[:200])}

    save_json(ledger_path, ledger)
    index = load_json(Path(args.index_file), {})
    for pid, entry in verified.items():
        if entry.get("released"):
            index.pop(pid, None)
    save_json(Path(args.index_file), index)

    summary = index_summary(index, args, locale)
    summary.update(**say("released", locale, done=done, size=human(freed),
                         skipped=skipped),
                   released=done, skipped=skipped, freed=freed,
                   **engine_facts(args, engine))
    return summary


# ===========================================================================
# EN | STORAGE - where the files land, and how to make room
# FR | STOCKAGE - ou atterrissent les fichiers, et comment faire de la place
# ===========================================================================
NETWORK_FS = {"nfs", "nfs4", "cifs", "smb3", "smbfs", "fuse.sshfs", "afs",
              "9p", "glusterfs", "ceph"}


def mount_of(path: Path) -> tuple:
    """EN | (mount point, fstype, source) for the filesystem holding `path`,
    EN | read from /proc/mounts. Longest matching mount point wins, which is
    EN | what makes a nested mount report itself rather than its parent.
    FR | (point de montage, type, source) du systeme de fichiers qui porte
    FR | `path`, lu dans /proc/mounts. Le point de montage correspondant le
    FR | plus long gagne, ce qui fait qu un montage imbrique se decrit
    FR | lui-meme plutot que son parent."""
    best = ("", "", "")
    try:
        target = str(path.resolve())
    except OSError:
        target = str(path)
    try:
        for line in Path("/proc/mounts").read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            source, point, fstype = parts[0], parts[1].replace("\\040", " "), parts[2]
            if (target == point or target.startswith(point.rstrip("/") + "/")) \
                    and len(point) >= len(best[0]):
                best = (point, fstype, source)
    except OSError:
        pass
    return best


def do_storage(args, locale: str) -> dict:
    """EN | Describe the destination: total, free, used, and whether this is
    EN | something that can be grown from here at all.
    FR | Decrit la destination : total, libre, utilise, et si c est quelque
    FR | chose qui peut etre agrandi d ici."""
    dest = Path(args.dest)
    payload = {"dest": str(dest)}

    try:
        dest.mkdir(parents=True, exist_ok=True)
        stat = os.statvfs(str(dest))
    except OSError as exc:
        return {**payload, **stated("error", locale),
                **say("dest_unwritable", locale, dest=str(dest),
                      detail=str(exc)[:120]),
                "exists": False}

    total = stat.f_blocks * stat.f_frsize
    free = stat.f_bavail * stat.f_frsize
    used = total - (stat.f_bfree * stat.f_frsize)
    point, fstype, source = mount_of(dest)
    network = fstype in NETWORK_FS
    used_pct = round(100.0 * used / total, 1) if total else 0.0

    payload.update(exists=True,
                   total=total, free=free, used=used,
                   total_human=human(total), free_human=human(free),
                   used_human=human(used), used_pct=used_pct,
                   mount=point, fstype=fstype, source=source,
                   network=network,
                   # EN | Growing needs a host that can be reached AND a
                   # EN | local filesystem. A NAS is grown on the NAS.
                   # FR | Agrandir exige un hote joignable ET un systeme de
                   # FR | fichiers local. Un NAS s agrandit sur le NAS.
                   growable=bool(args.host_path) and not network)

    # EN | THE DESTINATION IS NOT REAL STORAGE UNTIL SOMETHING IS MOUNTED ON
    # EN | IT. A path that resolves to the container's own root filesystem is
    # EN | not a partition and not a NAS: it is the writable layer of the
    # EN | image, which a pod restart or a core update throws away. It reports
    # EN | hundreds of free gigabytes and accepts every write, which is
    # EN | precisely what makes it dangerous - a 10 GB library would transfer
    # EN | perfectly and then be gone, with the ledger still claiming it is
    # EN | stored, and RELEASE would then have been authorised to free iCloud.
    # EN | Named here, loudly, rather than discovered afterwards.
    # FR | LA DESTINATION N EST PAS UN VRAI STOCKAGE TANT QUE RIEN N Y EST
    # FR | MONTE. Un chemin qui aboutit au systeme de fichiers racine du
    # FR | conteneur n est ni une partition ni un NAS : c est la couche
    # FR | inscriptible de l image, que le redemarrage d un pod ou une mise a
    # FR | jour du coeur jette. Elle annonce des centaines de gigaoctets
    # FR | libres et accepte toutes les ecritures, ce qui est precisement ce
    # FR | qui la rend dangereuse - une photothèque de 10 Go s y transfererait
    # FR | parfaitement puis disparaitrait, le registre continuant d affirmer
    # FR | qu elle est stockee, et LIBERER aurait alors ete autorise a vider
    # FR | iCloud. Nomme ici, fort, plutot que decouvert apres coup.
    ephemeral = (not network) and (point in ("", "/")
                                   or fstype in ("overlay", "overlayfs", "tmpfs"))
    payload["ephemeral"] = ephemeral

    if ephemeral:
        key = "storage_ephemeral"
    elif network:
        key = "storage_network"
    else:
        key = "storage_local"
    payload.update(**say(key, locale, free=human(free), total=human(total),
                         fstype=fstype or "?", used_pct=used_pct,
                         dest=str(dest)))
    # EN | Growing a filesystem that is not a volume makes no sense either.
    # FR | Agrandir un systeme de fichiers qui n est pas un volume n a pas de
    # FR | sens non plus.
    if ephemeral:
        payload["growable"] = False
    return payload


# EN | A logical volume path as LVM writes it, and nothing else. This value
# EN | reaches a root shell on the host, so it is matched against a strict
# EN | shape rather than quoted and hoped for.
# FR | Un chemin de volume logique tel que LVM l ecrit, et rien d autre.
# FR | Cette valeur atteint un shell root sur l hote : elle est donc
# FR | confrontee a une forme stricte plutot que quotee en esperant.
LV_PATH = re.compile(r"^/dev/[A-Za-z0-9+_.-]+/[A-Za-z0-9+_.-]+$")
GROW_SIZE = re.compile(r"^\+\d{1,5}(\.\d{1,2})?[MGT]$")
HOST_PATH = re.compile(r"^/[A-Za-z0-9/._-]{0,200}$")


def host_session(args):
    """EN | The host shell, borrowed from vssp_infra_updates.py rather than
    EN | reimplemented: it already carries the ssh-binary/paramiko fallback,
    EN | the 0600 temporary key, the CRLF guard and the sudo-over-stdin
    EN | convention, and its credentials already live in the safe as
    EN | `host_ssh`. A second copy of all that would be a second thing to
    EN | keep right.
    FR | Le shell de l hote, emprunte a vssp_infra_updates.py plutot que
    FR | reimplemente : il porte deja le repli binaire ssh/paramiko, la cle
    FR | temporaire en 0600, la garde CRLF et la convention sudo par stdin,
    FR | et ses identifiants vivent deja dans le coffre sous `host_ssh`. Une
    FR | seconde copie de tout cela serait une seconde chose a maintenir
    FR | juste."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from vssp_infra_updates import Safe, open_host  # noqa: PLC0415
    safe = Safe.open(args.vault_addr, Path(args.vault_token_file))
    return open_host(safe)


def do_grow(args, locale: str) -> dict:
    """EN | Grow the logical volume behind the destination, filesystem
    EN | included, on the Ubuntu host.
    EN |
    EN | WHAT THIS DELIBERATELY DOES NOT DO - shrink, and touch a partition
    EN | table. `lvextend -r` on a mounted volume is an online, journalled,
    EN | reversible-by-growing-again operation that LVM and ext4/xfs both
    EN | support while the data is in use. Shrinking is none of those things:
    EN | xfs cannot shrink at all, ext4 must be unmounted, and a mistake
    EN | takes the photo library with it. Repartitioning is further still
    EN | from anything a dashboard button should reach. Both are refused by
    EN | name, with the reason, rather than silently missing.
    FR | Agrandit le volume logique derriere la destination, systeme de
    FR | fichiers compris, sur l hote Ubuntu.
    FR |
    FR | CE QU IL NE FAIT VOLONTAIREMENT PAS - retrecir, et toucher a une
    FR | table de partitions. `lvextend -r` sur un volume monte est une
    FR | operation en ligne, journalisee, rattrapable en agrandissant encore,
    FR | que LVM et ext4/xfs supportent tous deux pendant que les donnees
    FR | servent. Retrecir n est rien de tout cela : xfs ne sait pas
    FR | retrecir, ext4 exige un demontage, et une erreur emporte la
    FR | photothèque. Repartitionner est encore plus loin de ce qu un bouton
    FR | de dashboard devrait atteindre. Les deux sont refuses nommement,
    FR | avec la raison, plutot qu absents en silence."""
    size = (args.size or "").strip()
    if size.startswith("-"):
        return {**stated("error", locale), **say("grow_shrink_refused", locale)}
    if not GROW_SIZE.match(size):
        return {**stated("error", locale),
                **say("grow_failed", locale,
                      detail=f"size must look like +50G, got {size!r}")}

    host_path = (args.host_path or "").strip()
    if not HOST_PATH.match(host_path):
        return {**stated("error", locale),
                **say("grow_not_lvm", locale,
                      detail="no usable host path declared for the destination")}

    try:
        host = host_session(args)
    except Exception as exc:  # noqa: BLE001 - a sealed safe lands here
        return {**stated("error", locale),
                **say("grow_failed", locale, detail=str(exc)[:200])}

    canonical = ""
    with host:
        # EN | findmnt answers with the device behind the path, which for an
        # EN | LVM volume is the /dev/<vg>/<lv> symlink lvextend expects.
        # FR | findmnt repond par le peripherique derriere le chemin, qui
        # FR | pour un volume LVM est le lien /dev/<vg>/<lv> attendu par
        # FR | lvextend.
        code, out, err = host.run(
            f"findmnt -no SOURCE,FSTYPE --target {host_path}")
        if code != 0 or not out.strip():
            return {**stated("error", locale),
                    **say("grow_not_lvm", locale,
                          detail=(err or out or "findmnt said nothing")[:160])}
        fields = out.split()
        device = fields[0] if fields else ""
        if not HOST_PATH.match(device):
            return {**stated("error", locale),
                    **say("grow_not_lvm", locale,
                          detail=f"unexpected device {device!r}")}

        # EN | A mapper name (/dev/mapper/vg-lv) is the same volume by
        # EN | another spelling; lvs resolves it to the canonical path.
        # FR | Un nom mapper (/dev/mapper/vg-lv) est le meme volume ecrit
        # FR | autrement ; lvs le resout vers le chemin canonique.
        code, out, err = host.run(
            f"lvs --noheadings -o lv_path {device}", sudo=True)
        lines = [ln.strip() for ln in (out or "").splitlines() if ln.strip()]
        canonical = lines[0] if lines else ""
        if code != 0 or not LV_PATH.match(canonical):
            return {**stated("error", locale),
                    **say("grow_not_lvm", locale,
                          detail=(err or device or "not an LVM volume")[:160])}

        code, out, err = host.run(f"lvextend -r -L {size} {canonical}",
                                  sudo=True)
        if code != 0:
            return {**stated("error", locale),
                    **say("grow_failed", locale,
                          detail=(err or out or f"exit {code}")[:200])}

    after = do_storage(args, locale)
    return {**after,
            **say("grow_done", locale, size=size.lstrip("+"),
                  free=after.get("free_human", "?")),
            "grown": size, "volume": canonical}


# ===========================================================================
# EN | STATUS - the one file everything else reads
# FR | ETAT - l unique fichier que tout le reste lit
# ===========================================================================
def do_status(args, locale: str, lock: Lock) -> dict:
    """EN | Cheap by design: it reads files, it does not call Apple. The
    EN | console polls this every 30 seconds and a round trip to iCloud on
    EN | every poll would rate-limit the account for nothing.
    FR | Volontairement bon marche : il lit des fichiers, il n appelle pas
    FR | Apple. La console l interroge toutes les 30 secondes, et un
    FR | aller-retour vers iCloud a chaque interrogation ferait limiter le
    FR | compte pour rien."""
    index = load_json(Path(args.index_file), {})
    engines = available_engines()
    payload = {"account": (args.apple_id or "").strip(),
               **engine_facts(args, engines[0] if engines else None)}

    busy = lock.holder()
    if busy:
        state = "scanning" if busy == "scan" else "transferring"
        payload.update(**stated(state, locale),
                       **say("busy", locale, action=busy), busy=busy)
    elif not engines:
        payload.update(**stated("no_library", locale),
                       **say("no_library", locale))
    elif not payload["account"] or not read_text_file(Path(args.password_file)):
        payload.update(**stated("not_configured", locale),
                       **say("no_credentials", locale))
    elif not index:
        payload.update(**stated("linked", locale), **say("index_empty", locale))
    else:
        payload.update(**index_summary(index, args, locale))

    # EN | The counters are published even while an operation holds the lock,
    # EN | so the console keeps showing the library it knows about instead of
    # EN | blanking out for the duration of a scan.
    # FR | Les compteurs sont publies meme pendant qu une operation tient le
    # FR | verrou, pour que la console continue d afficher la photothèque
    # FR | qu elle connait au lieu de se vider le temps d un scan.
    if index:
        payload.update({k: v for k, v in index_summary(index, args, locale).items()
                        if k not in ("state", "state_label", "message",
                                     "message_key", "message_vars")})
    payload["storage"] = do_storage(args, locale)
    return payload


# ===========================================================================
# EN | RUN
# FR | EXECUTION
# ===========================================================================
LONG_ACTIONS = ("scan", "transfer", "bulk", "release", "page")
LOCKED_ACTIONS = ("scan", "transfer", "bulk", "release")


def relaunch_detached(args) -> dict:
    """EN | Re-run this same command without --background, in a session of
    EN | its own, and return immediately. This is what gets a 40-minute scan
    EN | past the 60-second ceiling Home Assistant puts on a shell_command.
    FR | Relance cette meme commande sans --background, dans une session a
    FR | elle, et rend la main tout de suite. C est ce qui fait passer un
    FR | scan de 40 minutes au-dessus du plafond de 60 secondes que Home
    FR | Assistant impose a un shell_command."""
    argv = [sys.executable, os.path.abspath(__file__)]
    argv += [a for a in sys.argv[1:] if a != "--background"]
    log = Path(args.log_file)
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        handle = open(log, "ab")  # noqa: SIM115 - handed to the child process
    except OSError:
        handle = subprocess.DEVNULL
    subprocess.Popen(argv, stdout=handle, stderr=handle,
                     stdin=subprocess.DEVNULL, start_new_session=True,
                     close_fds=True)
    return {"started": args.action,
            "at": datetime.now().isoformat(timespec="seconds")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--action", required=True,
                    choices=("status", "link", "code", "scan", "page",
                             "transfer", "bulk", "release", "reconcile",
                             "purge", "storage", "grow", "resend", "forget"))
    ap.add_argument("--apple-id", default="")
    ap.add_argument("--password-file", default="/config/vssp/.icloud_password")
    # EN | The session directory is shared with the icloudpd command on
    # EN | purpose - see the header. Changing it here without changing the
    # EN | --cookie-directory passed to icloudpd would mean two logins.
    # FR | Le repertoire de session est partage avec la commande icloudpd a
    # FR | dessein - voir l en-tete. Le changer ici sans changer le
    # FR | --cookie-directory passe a icloudpd signifierait deux connexions.
    ap.add_argument("--session-dir", default="/config/vssp/.icloud_session")
    ap.add_argument("--code", default="")
    ap.add_argument("--code-file", default="/config/vssp/.icloud_code")
    ap.add_argument("--index-file", default="/config/vssp/icloud_index.json")
    ap.add_argument("--ledger-file", default="/config/vssp/icloud_ledger.json")
    ap.add_argument("--salt-file", default="/config/vssp/.icloud_thumb_salt")
    ap.add_argument("--lock-file", default="/config/vssp/.icloud_lock")
    ap.add_argument("--log-file", default="/config/vssp/icloud.log")
    ap.add_argument("--status-file",
                    default="/config/www/vssp/icloud_status.json")
    ap.add_argument("--page-file", default="/config/www/vssp/icloud_page.json")
    ap.add_argument("--thumbs-dir", default="/config/www/vssp/icloud/thumbs")
    ap.add_argument("--thumbs-url", default="/local/vssp/icloud/thumbs")
    ap.add_argument("--icloudpd", default="",
                    help="EN | explicit path to the icloudpd executable")
    # EN | The destination as THIS container sees it. /media is Home
    # EN | Assistant's own mount point for added storage, so a partition or a
    # EN | NAS share added in Settings > System > Storage lands under it and
    # EN | needs no further plumbing here.
    # FR | La destination telle que CE conteneur la voit. /media est le point
    # FR | de montage propre a Home Assistant pour le stockage ajoute : une
    # FR | partition ou un partage NAS ajoute dans Parametres > Systeme >
    # FR | Stockage atterrit dessous et n exige aucune autre plomberie ici.
    ap.add_argument("--dest", default="/media/icloud")
    # EN | The same place as the host sees it, which is what `grow` needs and
    # EN | this container cannot deduce: a bind mount hides its own origin.
    # FR | Le meme endroit vu par l hote, dont `grow` a besoin et que ce
    # FR | conteneur ne peut pas deduire : un bind mount masque son origine.
    ap.add_argument("--host-path", default="")
    ap.add_argument("--size", default="")
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--filter", default="all")
    # EN | How long to keep asking while Apple reports the library as still
    # EN | indexing. A page request lives inside a shell_command and is killed
    # EN | at 60 seconds, so its budget is deliberately small; scan, transfer
    # EN | and release run detached and are given minutes by their callers.
    # FR | Combien de temps continuer a demander pendant qu Apple annonce la
    # FR | photothèque en cours d indexation. Une demande de page vit dans un
    # FR | shell_command tue a 60 secondes : son budget est donc volontairement
    # FR | petit ; scan, transfert et liberation tournent detaches et leurs
    # FR | appelants leur accordent des minutes.
    ap.add_argument("--photo-retries", type=int, default=3)
    ap.add_argument("--photo-retry-delay", type=float, default=10.0)
    ap.add_argument("--json-b64", default="")
    ap.add_argument("--skip-videos", action="store_true")
    ap.add_argument("--skip-photos", action="store_true")
    ap.add_argument("--until-found", type=int, default=0)
    # EN | -1 means "do not free iCloud at all", which is the default. 0 and
    # EN | above are handed straight to --keep-icloud-recent-days.
    # FR | -1 veut dire « ne liberer iCloud en rien », et c est le defaut. 0
    # FR | et au-dela sont passes tels quels a --keep-icloud-recent-days.
    ap.add_argument("--free-icloud-days", type=int, default=-1)
    ap.add_argument("--background", action="store_true")
    ap.add_argument("--vault-addr", default=os.environ.get(
        "VSSP_VAULT_ADDR", "http://192.168.1.11:8200"))
    ap.add_argument("--vault-token-file",
                    default="/config/vssp/.vault_maint_token")
    ap.add_argument("--locale", default=BASE_LOCALE)
    args = ap.parse_args()

    locale = pick_locale(args.locale)
    status_path = Path(args.status_file)
    lock = Lock(Path(args.lock_file), args.action)

    # EN | `page` writes its own file, so the picker can read a page without
    # EN | the status file flickering under the console's sensors.
    # FR | `page` ecrit son propre fichier, pour que le selecteur lise une
    # FR | page sans faire clignoter le fichier d etat sous les capteurs de
    # FR | la console.
    out_path = Path(args.page_file) if args.action == "page" else status_path

    if args.background and args.action in LONG_ACTIONS:
        save_json(status_path,
                  {**stated("scanning" if args.action == "scan"
                            else "transferring", locale),
                   **say("busy", locale, action=args.action),
                   "generated": datetime.now().isoformat(timespec="seconds")})
        print(json.dumps(relaunch_detached(args)))
        return 0

    if args.action in LOCKED_ACTIONS and not lock.acquire():
        payload = {**stated("error", locale),
                   **say("busy", locale, action=lock.holder())}
        save_json(status_path, {**payload, "generated":
                                datetime.now().isoformat(timespec="seconds")})
        print(json.dumps(payload, ensure_ascii=False))
        return 1

    try:
        if args.action == "status":
            payload = do_status(args, locale, lock)
        elif args.action == "link":
            payload = do_link(args, locale)
        elif args.action == "code":
            payload = do_code(args, locale)
        elif args.action == "resend":
            payload = do_resend(args, locale)
        elif args.action == "forget":
            payload = do_forget(args, locale)
        elif args.action == "scan":
            payload = do_scan(args, locale, status_path)
        elif args.action == "page":
            payload = do_page(args, locale)
        elif args.action == "transfer":
            payload = do_transfer(args, locale, status_path)
        elif args.action == "bulk":
            payload = do_bulk(args, locale, status_path)
        elif args.action == "release":
            payload = do_release(args, locale)
        elif args.action == "reconcile":
            payload = {"reconciled": reconcile_ledger(args)}
        elif args.action == "purge":
            payload = do_purge(args, locale)
        elif args.action == "storage":
            payload = do_storage(args, locale)
        else:
            payload = do_grow(args, locale)
    except Exception as exc:  # noqa: BLE001 - never leave the screen blank
        payload = {**stated("error", locale),
                   **say("failure", locale, detail=str(exc)[:200])}
    finally:
        lock.release()

    payload["generated"] = datetime.now().isoformat(timespec="seconds")

    def as_status(body: dict) -> dict:
        """EN | Everything the console and the form read lives in ONE file, so
        EN | whatever action wrote it last must leave the whole picture - not
        EN | just its own result. A transfer used to write a summary with no
        EN | `storage` and no `account` in it, and the form then showed an
        EN | empty destination and a blank free-space tile until some other
        EN | action happened to put them back. The fields are filled in here,
        EN | at the one place that writes that file, rather than remembered
        EN | separately by each of the nine actions.
        FR | Tout ce que lisent la console et le formulaire vit dans UN
        FR | fichier : l action qui l ecrit en dernier doit donc y laisser
        FR | l image complete, pas seulement son propre resultat. Un transfert
        FR | y ecrivait un resume sans `storage` ni `account`, et le
        FR | formulaire affichait alors une destination vide et une tuile
        FR | d espace libre blanche jusqu a ce qu une autre action les y
        FR | remette. Les champs sont completes ici, a l unique endroit qui
        FR | ecrit ce fichier, plutot que retenus separement par chacune des
        FR | neuf actions."""
        filled = dict(body)
        filled.setdefault("account", (args.apple_id or "").strip())
        if "storage" not in filled:
            try:
                filled["storage"] = do_storage(args, locale)
            except Exception:  # noqa: BLE001 - a status file beats none
                pass
        return filled

    save_json(out_path, payload if args.action == "page" else as_status(payload))
    # EN | A page refresh must also leave the summary current, or the console
    # EN | counters freeze while the user browses thumbnails.
    # FR | Un rafraichissement de page doit aussi laisser le resume a jour,
    # FR | sinon les compteurs de la console gelent pendant que
    # FR | l utilisateur feuillette les miniatures.
    if args.action in ("transfer", "bulk", "release", "scan", "grow"):
        save_json(status_path, as_status(payload))
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get("state") != "error" else 1


if __name__ == "__main__":
    sys.exit(main())
