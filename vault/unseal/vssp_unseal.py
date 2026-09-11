#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EN | VSSP UNSEAL — one password, from one of your own devices.
EN |
EN | WHAT THIS IS, AND WHAT IT COSTS. Vault reseals on every restart, by
EN | design: no auto-unseal is configured, and three of the five Shamir shares
EN | have to be typed by hand before the safe answers anything. That is the
EN | strongest arrangement available here, because the machine never holds
EN | enough to open itself. This tool trades some of that away, deliberately
EN | and at the operator's explicit request, for a ceremony that takes one
EN | password instead of three keys.
EN |
EN | BE CLEAR ABOUT THE TRADE. After this, the three shares live on the
EN | machine, encrypted with a key derived from a passphrase that only the
EN | operator knows. What is gained: a stolen disk, a stolen backup or a
EN | snapshot yields ciphertext. What is lost: an attacker who already has
EN | root on the RUNNING host can wait for the passphrase to be typed and take
EN | the shares as they are decrypted. A 3-of-5 split whose three shares sleep
EN | in one file is a 1-of-1 secret. This file exists because that trade was
EN | made knowingly, not because it is free.
EN |
EN | WHAT ACTUALLY AUTHENTICATES. Two factors, both real:
EN |   - something the device holds: a client certificate, verified by mutual
EN |     TLS against a private CA this tool creates. No certificate, no TLS
EN |     handshake at all — an unauthorised client is not served an error page,
EN |     it is not served anything.
EN |   - something the operator knows: the passphrase, which is the only thing
EN |     that can derive the key the shares are encrypted with.
EN | MAC addresses are NOT in that list, and were asked for. They are not
EN | authentication: `ip link set dev X address ...` changes one in a single
EN | command, and a MAC is invisible the moment a router sits between the
EN | client and this host — what arrives is the router's. This tool records
EN | the MAC it can see for the audit line and lets it decide nothing.
EN |
EN | WHAT IT CANNOT DO. It unseals. It cannot seal, cannot read a secret,
EN | cannot write one, cannot reach anything but sys/seal-status and
EN | sys/unseal on the local Vault. A compromise of this service is a
EN | compromise of the unseal step, not of the safe's contents.
EN |
FR | VSSP UNSEAL — un mot de passe, depuis un de vos propres appareils.
FR |
FR | CE QUE C EST, ET CE QUE CA COUTE. Vault se rescelle a chaque
FR | redemarrage, par conception : aucun descellement automatique n est
FR | configure, et trois des cinq parts de Shamir doivent etre saisies a la
FR | main avant que le coffre reponde. C est l arrangement le plus solide
FR | disponible ici, parce que la machine ne detient jamais de quoi s ouvrir
FR | elle-meme. Cet outil en abandonne une partie, deliberement et a la
FR | demande explicite de l operateur, pour une ceremonie a un mot de passe
FR | plutot qu a trois cles.
FR |
FR | QUE LE MARCHE SOIT CLAIR. Apres cela, les trois parts vivent sur la
FR | machine, chiffrees par une cle derivee d une phrase secrete que seul
FR | l operateur connait. Ce qu on gagne : un disque vole, une sauvegarde
FR | volee ou un instantane ne donnent que du chiffre. Ce qu on perd : un
FR | attaquant deja root sur l hote EN MARCHE peut attendre que la phrase soit
FR | tapee et prendre les parts au moment ou elles sont dechiffrees. Un
FR | partage 3-sur-5 dont les trois parts dorment dans un seul fichier est un
FR | secret 1-sur-1. Ce fichier existe parce que ce marche a ete fait en
FR | connaissance de cause, pas parce qu il serait gratuit.
FR |
FR | CE QUI AUTHENTIFIE REELLEMENT. Deux facteurs, tous deux reels :
FR |   - ce que l appareil possede : un certificat client, verifie en TLS
FR |     mutuel contre une autorite privee que cet outil cree. Pas de
FR |     certificat, pas de poignee de main TLS du tout — un client non
FR |     autorise ne recoit pas une page d erreur, il ne recoit rien.
FR |   - ce que l operateur sait : la phrase secrete, seule chose capable de
FR |     deriver la cle qui chiffre les parts.
FR | Les adresses MAC ne sont PAS dans cette liste, et avaient ete demandees.
FR | Ce n est pas de l authentification : `ip link set dev X address ...` en
FR | change une en une commande, et une MAC est invisible des qu un routeur
FR | separe le client de cet hote — ce qui arrive est celle du routeur. Cet
FR | outil consigne la MAC qu il peut voir pour la ligne d audit, et ne lui
FR | laisse decider de rien.
FR |
FR | CE QU IL NE PEUT PAS FAIRE. Il descelle. Il ne peut pas sceller, ni lire
FR | un secret, ni en ecrire un, ni joindre autre chose que sys/seal-status et
FR | sys/unseal sur le Vault local. Compromettre ce service, c est
FR | compromettre l etape de descellement, pas le contenu du coffre."""

from __future__ import annotations

import argparse
import base64
import datetime as _dt
import getpass
import hashlib
import hmac
import http.server
import json
import os
import re
import secrets
import ssl
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.x509.oid import NameOID

# ═══════════════════════════════════════════════════════════════════════════
# EN | Where things live / FR | Ou vivent les choses
# ═══════════════════════════════════════════════════════════════════════════
ETC = Path(os.environ.get("VSSP_UNSEAL_DIR", "/etc/vssp-unseal"))
SHARES = ETC / "shares.enc"
CA_CRT = ETC / "ca.crt"
CA_KEY = ETC / "ca.key"
SRV_CRT = ETC / "server.crt"
SRV_KEY = ETC / "server.key"
STATE = ETC / "state.json"

VAULT_ADDR = os.environ.get("VSSP_VAULT_ADDR", "http://127.0.0.1:8200")
BIND_PORT = int(os.environ.get("VSSP_UNSEAL_PORT", "8443"))
HTTP_TIMEOUT = 10

# EN | scrypt, from the standard library. N=2^17 with r=8 asks for about
# EN | 128 MB and a noticeable fraction of a second per attempt on this host —
# EN | invisible to someone typing a password once after a reboot, and ruinous
# EN | to someone trying a dictionary against a stolen file. The parameters are
# EN | STORED IN THE FILE rather than hard-coded here, so they can be raised
# EN | later without orphaning a blob encrypted under the old ones.
# FR | scrypt, depuis la bibliotheque standard. N=2^17 avec r=8 demande environ
# FR | 128 Mo et une fraction de seconde perceptible par tentative sur cet
# FR | hote — invisible pour qui tape un mot de passe une fois apres un
# FR | redemarrage, ruineux pour qui essaie un dictionnaire contre un fichier
# FR | vole. Les parametres sont STOCKES DANS LE FICHIER plutot qu ecrits en
# FR | dur ici, pour qu on puisse les augmenter plus tard sans rendre
# FR | illisible un blob chiffre sous les anciens.
KDF_N = 1 << 17
KDF_R = 8
KDF_P = 1
KDF_LEN = 32

# EN | Five wrong passphrases and the door stays shut for fifteen minutes. The
# EN | counter is PERSISTED: restarting the service is not a way around it, and
# EN | on this host only root can restart it anyway. Counted per certificate,
# EN | because that is the identity that got through the TLS layer.
# FR | Cinq phrases fausses et la porte reste fermee un quart d heure. Le
# FR | compteur est PERSISTE : redemarrer le service n est pas un moyen de le
# FR | contourner, et sur cet hote seul root peut le redemarrer de toute
# FR | facon. Compte par certificat, puisque c est l identite qui a franchi la
# FR | couche TLS.
MAX_FAILURES = 5
LOCK_SECONDS = 15 * 60

_LOCK = threading.Lock()


def log(msg: str) -> None:
    """EN | To the journal, never a file of our own, and NEVER a secret.
    FR | Vers le journal, jamais un fichier a nous, et JAMAIS un secret."""
    stamp = _dt.datetime.now().isoformat(timespec="seconds")
    print(f"[vssp-unseal] {stamp} {msg}", flush=True)


# ═══════════════════════════════════════════════════════════════════════════
# EN | THE BLOB — scrypt then AES-256-GCM
# FR | LE BLOB — scrypt puis AES-256-GCM
# ═══════════════════════════════════════════════════════════════════════════
def derive(passphrase: str, salt: bytes, n: int, r: int, p: int,
           dklen: int) -> bytes:
    """EN | maxmem is COMPUTED, not left at the default, and that default is a
    EN | trap: `maxmem=0` reads as "no limit" and means "OpenSSL's own limit",
    EN | which is 32 MB. scrypt at N=2^17, r=8 needs 128 MB — so the honest
    EN | parameters chosen above fail outright with "memory limit exceeded"
    EN | unless the ceiling is raised to match them. Deriving it from n and r
    EN | means raising the cost later cannot reintroduce the failure.
    FR | maxmem est CALCULE, pas laisse par defaut, et ce defaut est un piege :
    FR | `maxmem=0` se lit « pas de limite » et signifie « la limite propre
    FR | d OpenSSL », soit 32 Mo. scrypt en N=2^17, r=8 demande 128 Mo — les
    FR | parametres honnetes choisis plus haut echouent donc franchement sur
    FR | « memory limit exceeded » tant que le plafond ne les suit pas. Le
    FR | deriver de n et r fait qu augmenter le cout plus tard ne peut pas
    FR | ramener la panne."""
    need = 128 * n * r * p
    return hashlib.scrypt(passphrase.encode("utf-8"), salt=salt, n=n, r=r,
                          p=p, dklen=dklen, maxmem=need * 2)


def seal_blob(shares: list[str], passphrase: str) -> dict:
    """EN | GCM, not CBC or CTR: the tag makes a wrong passphrase fail as a
    EN | DECRYPTION ERROR rather than as plausible-looking garbage that would
    EN | then be posted to Vault as if it were a key. The version and the KDF
    EN | parameters are authenticated as additional data, so nobody can talk
    EN | this tool into re-reading the blob with weaker settings.
    FR | GCM, pas CBC ni CTR : le tag fait echouer une phrase fausse comme une
    FR | ERREUR DE DECHIFFREMENT plutot que comme un charabia vraisemblable qui
    FR | serait ensuite envoye a Vault comme s il s agissait d une cle. La
    FR | version et les parametres du KDF sont authentifies en donnees
    FR | additionnelles : personne ne peut convaincre cet outil de relire le
    FR | blob avec des reglages plus faibles."""
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    meta = {"v": 1, "kdf": "scrypt", "n": KDF_N, "r": KDF_R, "p": KDF_P,
            "len": KDF_LEN}
    aad = json.dumps(meta, sort_keys=True, separators=(",", ":")).encode()
    key = derive(passphrase, salt, KDF_N, KDF_R, KDF_P, KDF_LEN)
    payload = json.dumps({"shares": shares}, separators=(",", ":")).encode()
    box = AESGCM(key).encrypt(nonce, payload, aad)
    return dict(meta,
                salt=base64.b64encode(salt).decode(),
                nonce=base64.b64encode(nonce).decode(),
                blob=base64.b64encode(box).decode())


def open_blob(doc: dict, passphrase: str) -> list[str]:
    meta = {k: doc[k] for k in ("v", "kdf", "n", "r", "p", "len")}
    if meta["kdf"] != "scrypt" or meta["v"] != 1:
        raise ValueError("unsupported blob format")
    aad = json.dumps(meta, sort_keys=True, separators=(",", ":")).encode()
    key = derive(passphrase, base64.b64decode(doc["salt"]), meta["n"],
                 meta["r"], meta["p"], meta["len"])
    clear = AESGCM(key).decrypt(base64.b64decode(doc["nonce"]),
                                base64.b64decode(doc["blob"]), aad)
    return json.loads(clear)["shares"]


def write_private(path: Path, data: bytes) -> None:
    """EN | 0600 BEFORE the bytes land, not after. Creating the file readable
    EN | and tightening it afterwards leaves a window in which anyone on the
    EN | host can read it, and the whole value of this file is that they
    EN | cannot.
    FR | 0600 AVANT que les octets arrivent, pas apres. Creer le fichier
    FR | lisible puis le restreindre laisse une fenetre pendant laquelle
    FR | n importe qui sur l hote peut le lire, et toute la valeur de ce
    FR | fichier est qu il ne le peut pas."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)
    os.replace(tmp, path)


# ═══════════════════════════════════════════════════════════════════════════
# EN | THE SAFE — only the two routes this tool is allowed to touch
# FR | LE COFFRE — seulement les deux routes que cet outil a le droit de toucher
# ═══════════════════════════════════════════════════════════════════════════
def vault_call(path: str, payload: dict | None = None) -> dict:
    url = f"{VAULT_ADDR.rstrip('/')}/v1/{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method="PUT" if data else "GET",
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:200]
        raise RuntimeError(f"vault {exc.code}: {body}") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise RuntimeError(f"vault unreachable: {exc}") from exc


def seal_status() -> dict:
    return vault_call("sys/seal-status")


def submit(share: str) -> dict:
    return vault_call("sys/unseal", {"key": share})


def unseal_reset() -> dict:
    """EN | Throws away a half-finished unseal attempt. Used after VERIFYING
    EN | shares at enrolment, so that checking the keys are right does not
    EN | leave the safe open as a side effect.
    FR | Jette une tentative de descellement a moitie faite. Utilise apres
    FR | VERIFICATION des parts a l enrolement, pour que controler la justesse
    FR | des cles ne laisse pas le coffre ouvert par effet de bord."""
    return vault_call("sys/unseal", {"reset": True})


def do_unseal(shares: list[str]) -> dict:
    """EN | Feed shares until the safe opens or they run out. Stops the moment
    EN | it is open: handing Vault a share it no longer needs is pointless, and
    EN | every share that stays unused is one that never left the process.
    FR | Donner des parts jusqu a ce que le coffre s ouvre ou qu il n y en ait
    FR | plus. S arrete des qu il est ouvert : donner a Vault une part dont il
    FR | n a plus besoin ne sert a rien, et chaque part inutilisee est une part
    FR | qui n a jamais quitte le processus."""
    state = seal_status()
    for share in shares:
        if not state.get("sealed", True):
            break
        state = submit(share)
    return state


# ═══════════════════════════════════════════════════════════════════════════
# EN | CERTIFICATES — a private CA, a server cert, one cert per device
# FR | CERTIFICATS — une autorite privee, un cert serveur, un cert par appareil
# ═══════════════════════════════════════════════════════════════════════════
def _name(cn: str) -> x509.Name:
    return x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Visio Sapiens"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "vssp-unseal"),
        x509.NameAttribute(NameOID.COMMON_NAME, cn)])


def ensure_ca() -> tuple[x509.Certificate, ec.EllipticCurvePrivateKey]:
    """EN | P-256 and ten years. This CA signs nothing but the handful of
    EN | devices allowed to ask for an unseal, and it is trusted by nothing but
    EN | this one service — so its only job is to be unforgeable, and its
    EN | private key never leaves this directory.
    FR | P-256 et dix ans. Cette autorite ne signe rien d autre que la poignee
    FR | d appareils autorises a demander un descellement, et rien d autre que
    FR | ce service ne lui fait confiance — son seul travail est donc d etre
    FR | infalsifiable, et sa cle privee ne quitte jamais ce repertoire."""
    if CA_CRT.exists() and CA_KEY.exists():
        return (x509.load_pem_x509_certificate(CA_CRT.read_bytes()),
                serialization.load_pem_private_key(CA_KEY.read_bytes(),
                                                   password=None))
    key = ec.generate_private_key(ec.SECP256R1())
    now = _dt.datetime.now(_dt.timezone.utc)
    cert = (x509.CertificateBuilder()
            .subject_name(_name("VSSP Unseal CA"))
            .issuer_name(_name("VSSP Unseal CA"))
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - _dt.timedelta(minutes=5))
            .not_valid_after(now + _dt.timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0),
                           critical=True)
            .add_extension(x509.KeyUsage(
                digital_signature=False, content_commitment=False,
                key_encipherment=False, data_encipherment=False,
                key_agreement=False, key_cert_sign=True, crl_sign=True,
                encipher_only=False, decipher_only=False), critical=True)
            .sign(key, hashes.SHA256()))
    write_private(CA_KEY, key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()))
    write_private(CA_CRT, cert.public_bytes(serialization.Encoding.PEM))
    log("created the unseal CA")
    return cert, key


def issue(cn: str, days: int, server: bool,
          hosts: list[str] | None = None) -> tuple[bytes, bytes]:
    ca_cert, ca_key = ensure_ca()
    key = ec.generate_private_key(ec.SECP256R1())
    now = _dt.datetime.now(_dt.timezone.utc)
    usage = (x509.ExtendedKeyUsage([x509.ExtendedKeyUsageOID.SERVER_AUTH])
             if server else
             x509.ExtendedKeyUsage([x509.ExtendedKeyUsageOID.CLIENT_AUTH]))
    builder = (x509.CertificateBuilder()
               .subject_name(_name(cn))
               .issuer_name(ca_cert.subject)
               .public_key(key.public_key())
               .serial_number(x509.random_serial_number())
               .not_valid_before(now - _dt.timedelta(minutes=5))
               .not_valid_after(now + _dt.timedelta(days=days))
               .add_extension(x509.BasicConstraints(ca=False, path_length=None),
                              critical=True)
               .add_extension(usage, critical=False))
    if server and hosts:
        alts: list[x509.GeneralName] = []
        for h in hosts:
            try:
                import ipaddress
                alts.append(x509.IPAddress(ipaddress.ip_address(h)))
            except ValueError:
                alts.append(x509.DNSName(h))
        builder = builder.add_extension(x509.SubjectAlternativeName(alts),
                                        critical=False)
    cert = builder.sign(ca_key, hashes.SHA256())
    return (cert.public_bytes(serialization.Encoding.PEM),
            key.private_bytes(serialization.Encoding.PEM,
                              serialization.PrivateFormat.PKCS8,
                              serialization.NoEncryption()))


# ═══════════════════════════════════════════════════════════════════════════
# EN | LOCKOUT
# ═══════════════════════════════════════════════════════════════════════════
def read_state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state: dict) -> None:
    write_private(STATE, json.dumps(state).encode())


def locked_for(who: str) -> int:
    entry = read_state().get(who) or {}
    left = int(entry.get("until", 0) - _dt.datetime.now().timestamp())
    return max(0, left)


def note_failure(who: str) -> int:
    with _LOCK:
        state = read_state()
        entry = state.get(who) or {"fails": 0, "until": 0}
        entry["fails"] = int(entry.get("fails", 0)) + 1
        if entry["fails"] >= MAX_FAILURES:
            entry["until"] = _dt.datetime.now().timestamp() + LOCK_SECONDS
            entry["fails"] = 0
        state[who] = entry
        save_state(state)
        return int(entry.get("until", 0) and LOCK_SECONDS)


def note_success(who: str) -> None:
    with _LOCK:
        state = read_state()
        state.pop(who, None)
        save_state(state)


def mac_of(ip: str) -> str:
    """EN | Best effort, for the audit line only — see the module docstring on
    EN | why this decides nothing. Off-LAN it returns the router's, or nothing.
    FR | Au mieux, pour la seule ligne d audit — voir l en-tete du module sur
    FR | la raison pour laquelle cela ne decide de rien. Hors du LAN, renvoie
    FR | celle du routeur, ou rien."""
    try:
        out = subprocess.run(["ip", "neigh", "show", ip], capture_output=True,
                             text=True, timeout=3).stdout
    except (OSError, subprocess.SubprocessError):
        return ""
    m = re.search(r"lladdr ([0-9a-f:]{17})", out)
    return m.group(1) if m else ""


# ═══════════════════════════════════════════════════════════════════════════
# EN | THE SERVICE
# ═══════════════════════════════════════════════════════════════════════════
class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "vssp-unseal"
    sys_version = ""

    def log_message(self, fmt, *args):  # noqa: A003
        """EN | Silenced: the default access log prints the request line, and
        EN | this tool must never risk a body or a query string reaching a log.
        EN | Every event worth keeping is logged deliberately below.
        FR | Muet : le journal d acces par defaut imprime la ligne de requete,
        FR | et cet outil ne doit jamais risquer qu un corps ou une chaine de
        FR | requete atteigne un journal. Tout evenement qui merite d etre
        FR | garde est journalise deliberement plus bas."""

    # -- helpers ------------------------------------------------------------
    def who(self) -> str:
        cert = self.connection.getpeercert() or {}
        for rdn in cert.get("subject", ()):
            for key, value in rdn:
                if key == "commonName":
                    return value
        return "unknown"

    def reply(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    # -- routes -------------------------------------------------------------
    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET")
        self.end_headers()

    def do_GET(self):  # noqa: N802
        if self.path.split("?")[0] != "/status":
            return self.reply(404, {"error": "not found"})
        try:
            st = seal_status()
        except RuntimeError as exc:
            return self.reply(502, {"error": str(exc)})
        self.reply(200, {"sealed": st.get("sealed", True),
                         "progress": st.get("progress", 0),
                         "threshold": st.get("t", 0),
                         "version": st.get("version", ""),
                         "locked": locked_for(self.who())})

    def do_POST(self):  # noqa: N802
        if self.path.split("?")[0] != "/unseal":
            return self.reply(404, {"error": "not found"})
        who = self.who()
        ip = self.client_address[0]

        left = locked_for(who)
        if left:
            log(f"REFUSED {who} from {ip} mac={mac_of(ip)}: locked {left}s")
            return self.reply(429, {"error": "locked", "retry_after": left})

        try:
            size = int(self.headers.get("Content-Length") or 0)
            if size <= 0 or size > 4096:
                raise ValueError
            passphrase = json.loads(self.rfile.read(size)).get("passphrase")
            if not isinstance(passphrase, str) or not passphrase:
                raise ValueError
        except (ValueError, TypeError, json.JSONDecodeError):
            return self.reply(400, {"error": "bad request"})

        try:
            doc = json.loads(SHARES.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            log("no share file: run `vssp_unseal.py enroll-keys` first")
            return self.reply(503, {"error": "not enrolled"})

        try:
            shares = open_blob(doc, passphrase)
        except Exception:  # noqa: BLE001
            # EN | Wrong passphrase, or a tampered file. The two are NOT
            # EN | distinguished in the answer: telling a caller which one they
            # EN | hit is telling them whether the file is intact, and that is
            # EN | free information for an attacker.
            # FR | Phrase fausse, ou fichier altere. Les deux ne sont PAS
            # FR | distingues dans la reponse : dire a un appelant lequel il a
            # FR | touche, c est lui dire si le fichier est intact, et c est un
            # FR | renseignement gratuit pour un attaquant.
            lock = note_failure(who)
            log(f"DENIED {who} from {ip} mac={mac_of(ip)}: bad passphrase"
                + (f" — locked {lock}s" if lock else ""))
            return self.reply(403, {"error": "denied"})

        try:
            state = do_unseal(shares)
        except RuntimeError as exc:
            log(f"ERROR {who} from {ip}: {exc}")
            return self.reply(502, {"error": str(exc)})
        finally:
            # EN | Best effort, and said plainly: Python strings are immutable
            # EN | and the interpreter may well have left copies behind. This
            # EN | drops the only references WE hold, which is all a program in
            # EN | this language can honestly promise.
            # FR | Au mieux, et dit franchement : les chaines Python sont
            # FR | immuables et l interprete a tres bien pu laisser des copies
            # FR | derriere lui. Ceci lache les seules references que NOUS
            # FR | tenons, ce qui est tout ce qu un programme dans ce langage
            # FR | peut honnetement promettre.
            shares = None
            passphrase = None

        note_success(who)
        opened = not state.get("sealed", True)
        log(f"{'UNSEALED' if opened else 'PARTIAL'} by {who} from {ip} "
            f"mac={mac_of(ip)} progress={state.get('progress', 0)}")
        self.reply(200, {"sealed": state.get("sealed", True),
                         "progress": state.get("progress", 0),
                         "threshold": state.get("t", 0)})


def serve() -> int:
    for path in (SHARES, CA_CRT, SRV_CRT, SRV_KEY):
        if not path.exists():
            print(f"[ERR] {path} is missing — run the enrolment steps first",
                  file=sys.stderr)
            return 1
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    # EN | CERT_REQUIRED is the whole gate. With no client certificate the
    # EN | handshake fails and nothing is served — not a login page, not a 401,
    # EN | nothing that says a service is here at all.
    # FR | CERT_REQUIRED est tout le portail. Sans certificat client la
    # FR | poignee de main echoue et rien n est servi — pas de page de
    # FR | connexion, pas de 401, rien qui dise meme qu un service est la.
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.load_verify_locations(cafile=str(CA_CRT))
    ctx.load_cert_chain(certfile=str(SRV_CRT), keyfile=str(SRV_KEY))
    httpd = http.server.ThreadingHTTPServer(("0.0.0.0", BIND_PORT), Handler)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    log(f"listening on :{BIND_PORT} (mutual TLS), vault at {VAULT_ADDR}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


# ═══════════════════════════════════════════════════════════════════════════
# EN | ENROLMENT
# ═══════════════════════════════════════════════════════════════════════════
def enroll_keys(verify: bool) -> int:
    """EN | THE KEYS ARE READ HERE AND NOWHERE ELSE. getpass, so they are not
    EN | echoed, not in the shell history, and not in this process's argv where
    EN | every user on the host could read them out of /proc.
    FR | LES CLES SONT LUES ICI ET NULLE PART AILLEURS. getpass, pour qu elles
    FR | ne soient pas affichees, pas dans l historique du shell, et pas dans
    FR | l argv de ce processus ou chaque utilisateur de l hote pourrait les
    FR | lire dans /proc."""
    try:
        status = seal_status()
    except RuntimeError as exc:
        print(f"[ERR] {exc}", file=sys.stderr)
        return 1
    threshold = int(status.get("t", 3))
    print(f"[i] Vault {status.get('version', '?')} — threshold {threshold} of "
          f"{status.get('n', '?')}, currently "
          f"{'SEALED' if status.get('sealed') else 'open'}")

    shares: list[str] = []
    for i in range(threshold):
        while True:
            got = getpass.getpass(f"    unseal key {i + 1}/{threshold} "
                                  "(not echoed): ").strip()
            if got:
                shares.append(got)
                break
            print("    empty — try again")

    if verify:
        if status.get("sealed"):
            print("[i] verifying each key against the sealed safe...")
            try:
                unseal_reset()
                progress = 0
                for i, share in enumerate(shares, 1):
                    st = submit(share)
                    if not st.get("sealed", True):
                        print(f"    key {i}: accepted (and the safe is now "
                              "OPEN — that was the last one)")
                        progress = threshold
                        break
                    if st.get("progress", 0) <= progress:
                        print(f"[ERR] key {i} was REJECTED by Vault. Nothing "
                              "has been written.", file=sys.stderr)
                        unseal_reset()
                        return 1
                    progress = st["progress"]
                    print(f"    key {i}: accepted ({progress}/{threshold})")
                if progress < threshold:
                    unseal_reset()
            except RuntimeError as exc:
                print(f"[ERR] verification failed: {exc}", file=sys.stderr)
                return 1
        else:
            # EN | An open safe cannot check a share: sys/unseal answers
            # EN | "already unsealed" whatever you hand it. Saying so is better
            # EN | than implying the keys were checked when they were not — a
            # EN | typo found now is a typo not found at two in the morning.
            # FR | Un coffre ouvert ne peut pas verifier une part : sys/unseal
            # FR | repond « deja descelle » quoi qu on lui donne. Le dire vaut
            # FR | mieux que laisser croire que les cles ont ete verifiees — une
            # FR | faute de frappe trouvee maintenant est une faute de frappe
            # FR | qu on ne trouvera pas a deux heures du matin.
            print("[!] The safe is OPEN, so the keys CANNOT be verified now.")
            print("    Re-run this with --verify while it is sealed to be "
                  "sure they work.")

    while True:
        p1 = getpass.getpass("    passphrase (not echoed): ")
        if len(p1) < 12:
            print("    too short — 12 characters minimum, and longer is the "
                  "whole point")
            continue
        p2 = getpass.getpass("    passphrase again: ")
        if not hmac.compare_digest(p1, p2):
            print("    they do not match")
            continue
        break

    write_private(SHARES, json.dumps(seal_blob(shares, p1), indent=2).encode())
    print(f"[OK] {threshold} shares encrypted into {SHARES} (mode 0600)")
    print("     The passphrase is not stored anywhere. Lose it and this file "
          "is scrap;")
    print("     your five original unseal keys remain the way in.")
    return 0


def enroll_device(name: str, days: int, out_dir: Path) -> int:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    crt, key = issue(name, days, server=False)
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle = out_dir / f"{safe}.p12"
    # EN | PKCS#12 because that is the one format both iOS and Android will
    # EN | import from a file, and it is what a desktop browser's certificate
    # EN | store expects too. It is protected by an export password of its own,
    # EN | asked for here: the file has to travel to the phone somehow, and it
    # EN | should not be a usable identity while it is in transit.
    # FR | PKCS#12 parce que c est le seul format qu iOS comme Android
    # FR | importent depuis un fichier, et c est aussi ce qu attend le magasin
    # FR | de certificats d un navigateur de bureau. Il est protege par un mot
    # FR | de passe d export qui lui est propre, demande ici : le fichier doit
    # FR | bien voyager jusqu au telephone, et il ne doit pas etre une identite
    # FR | utilisable pendant le trajet.
    while True:
        e1 = getpass.getpass("    export password for the .p12 (not echoed): ")
        if len(e1) < 6:
            print("    too short — 6 characters minimum")
            continue
        e2 = getpass.getpass("    export password again: ")
        if hmac.compare_digest(e1, e2):
            break
        print("    they do not match")

    from cryptography.hazmat.primitives.serialization import pkcs12
    blob = pkcs12.serialize_key_and_certificates(
        name=safe.encode(),
        key=serialization.load_pem_private_key(key, password=None),
        cert=x509.load_pem_x509_certificate(crt),
        cas=[ensure_ca()[0]],
        encryption_algorithm=serialization.BestAvailableEncryption(
            e1.encode()))
    write_private(bundle, blob)
    os.chmod(bundle, 0o600)
    fp = x509.load_pem_x509_certificate(crt).fingerprint(hashes.SHA256())
    print(f"[OK] {bundle}")
    print(f"     SHA-256 {fp.hex(':')}")
    print(f"     valid {days} days — import it on the device, then copy "
          f"{CA_CRT} there too and trust it.")
    return 0


def issue_cert(cn: str, hosts: list[str], days: int, out: Path) -> int:
    """EN | A server certificate for SOMETHING ELSE on this network, signed by
    EN | the same authority. Home Assistant behind Traefik is the reason this
    EN | exists: the alternative is a second private CA, and a second CA means
    EN | a second thing to install and trust on every phone. One authority for
    EN | the house, several certificates under it, is both less work and
    EN | easier to reason about — trusting it is one decision, made once.
    EN | The CA's private key never leaves /etc/vssp-unseal. This writes only
    EN | the leaf certificate and its key, and the key is written 0600 before a
    EN | byte of it exists on disk.
    FR | Un certificat serveur pour AUTRE CHOSE sur ce reseau, signe par la
    FR | meme autorite. Home Assistant derriere Traefik est la raison d etre de
    FR | cette commande : l alternative est une seconde autorite privee, et une
    FR | seconde autorite veut dire une chose de plus a installer et approuver
    FR | sur chaque telephone. Une autorite pour la maison, plusieurs
    FR | certificats dessous, c est moins de travail et plus simple a tenir —
    FR | lui faire confiance est une decision unique, prise une fois.
    FR | La cle privee de l autorite ne quitte jamais /etc/vssp-unseal. Ceci
    FR | n ecrit que le certificat feuille et sa cle, et la cle est ecrite en
    FR | 0600 avant qu un seul de ses octets existe sur le disque."""
    crt, key = issue(cn, days, server=True, hosts=hosts)
    out.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", cn)
    crt_path, key_path = out / f"{safe}.crt", out / f"{safe}.key"
    write_private(crt_path, crt)
    write_private(key_path, key)
    os.chmod(crt_path, 0o644)
    print(f"[OK] {crt_path}")
    print(f"[OK] {key_path}  (0600)")
    print(f"     for {', '.join(hosts)}, {days} days, signed by {CA_CRT}")
    return 0


def enroll_server(hosts: list[str], days: int) -> int:
    crt, key = issue(hosts[0], days, server=True, hosts=hosts)
    write_private(SRV_CRT, crt)
    write_private(SRV_KEY, key)
    print(f"[OK] server certificate for {', '.join(hosts)} "
          f"({days} days) -> {SRV_CRT}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Visio Sapiens — unseal Vault with one passphrase from an "
                    "enrolled device")
    sub = ap.add_subparsers(dest="cmd", required=True)

    k = sub.add_parser("enroll-keys", help="encrypt the unseal keys")
    k.add_argument("--no-verify", action="store_true",
                   help="skip checking each key against the sealed safe")

    d = sub.add_parser("enroll-device", help="issue a client certificate")
    d.add_argument("name")
    d.add_argument("--days", type=int, default=825)
    # EN | NOT the home directory. This is normally run as `sudo -u
    # EN | vssp-unseal`, and that account is a system user with no usable home
    # EN | — Path.home() would resolve to /nonexistent and the .p12 would have
    # EN | nowhere to land. The installer creates this directory, owned by the
    # EN | service account, mode 0700.
    # FR | PAS le repertoire personnel. Ceci s execute normalement en
    # FR | `sudo -u vssp-unseal`, et ce compte est un utilisateur systeme sans
    # FR | vrai repertoire personnel — Path.home() donnerait /nonexistent et le
    # FR | .p12 n aurait nulle part ou atterrir. L installateur cree ce
    # FR | repertoire, possede par le compte de service, en 0700.
    d.add_argument("--out", default="/var/lib/vssp-unseal/devices")

    s = sub.add_parser("enroll-server", help="issue this host's certificate")
    s.add_argument("hosts", nargs="+", help="IPs and names clients will use")
    s.add_argument("--days", type=int, default=3650)

    c = sub.add_parser("issue-cert",
                       help="server certificate for another service, same CA")
    c.add_argument("cn", help="common name, e.g. homeassistant")
    c.add_argument("--host", action="append", required=True, dest="hosts",
                   help="IP or DNS name clients will use (repeatable)")
    c.add_argument("--days", type=int, default=825)
    c.add_argument("--out", default="/var/lib/vssp-unseal/certs")

    sub.add_parser("serve", help="run the service")
    sub.add_parser("status", help="print the safe's seal status")

    args = ap.parse_args()
    if args.cmd == "enroll-keys":
        return enroll_keys(verify=not args.no_verify)
    if args.cmd == "enroll-device":
        return enroll_device(args.name, args.days, Path(args.out))
    if args.cmd == "issue-cert":
        return issue_cert(args.cn, args.hosts, args.days, Path(args.out))
    if args.cmd == "enroll-server":
        return enroll_server(args.hosts, args.days)
    if args.cmd == "status":
        print(json.dumps(seal_status(), indent=2))
        return 0
    return serve()


if __name__ == "__main__":
    sys.exit(main())
