#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
Visio Sapiens — sonde LAN du local technique.

Interroge la Livebox V7 Pro en local (API sysbus, http://<box>/ws) et
imprime du JSON sur stdout, consomme par les capteurs `command_line`
declares dans technical_room_config_snippets.yaml.

    python3 vssp_lan_probe.py wan       # IP publique, lien, debits
    python3 vssp_lan_probe.py dhcp      # plage DHCP + baux actifs
    python3 vssp_lan_probe.py nat       # redirections de ports
    python3 vssp_lan_probe.py clients   # table IP / hostname / MAC

Aucune dependance externe (urllib uniquement) : le script tourne tel
quel dans le conteneur Home Assistant. Rien ne sort du LAN.

Configuration en CASCADE, du moins au plus prioritaire :

  1. livebox.env   — reglages NON SECRETS, VERSIONNES dans le repo
                     (vssp/livebox.env : hote, utilisateur, mode d'IP,
                      nombre de ports du commutateur).
  2. .livebox.env  — le SEUL secret : LIVEBOX_PASSWORD. Ecrit par le job
                     de deploiement depuis la variable CI/CD masquee,
                     jamais commite (chmod 600).
  3. variables d'environnement du conteneur — priorite maximale, utile
                     pour un test ponctuel sans toucher aux fichiers.

Aucune de ces trois etapes n'est manuelle en fonctionnement normal :
la CI ecrit .livebox.env a chaque deploiement.

Code retour non nul en cas d'echec : Home Assistant marque alors le
capteur "unavailable" plutot que de publier des donnees fausses.
"""

import json
import os
import sys
import http.cookiejar
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
# Reglages versionnes (repo) puis secret depose par la CI. L'ordre compte :
# le second ecrase le premier, l'environnement ecrase les deux.
CONF_FILES = (os.path.join(HERE, "livebox.env"),
              os.path.join(HERE, ".livebox.env"))

CT = "application/x-sah-ws-4-call+json"


# ─────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────
def _read_conf(path, cfg):
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            if v:                      # une valeur vide ne doit rien ecraser
                cfg[k.strip()] = v


def load_env():
    cfg = {
        "LIVEBOX_HOST": "192.168.1.1",
        "LIVEBOX_USER": "admin",
        "LIVEBOX_PASSWORD": "",
        "LIVEBOX_IP_MODE": "static",
        "NETGEAR_PORTS": "10",
    }
    for path in CONF_FILES:
        _read_conf(path, cfg)
    for k in list(cfg):
        if os.environ.get(k):
            cfg[k] = os.environ[k]
    return cfg


CFG = load_env()
BASE = "http://%s/ws" % CFG["LIVEBOX_HOST"]

_jar = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_jar))
_context_id = None


# ─────────────────────────────────────────────────────────────────────
# Transport sysbus
# ─────────────────────────────────────────────────────────────────────
def _post(payload, auth):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BASE, data=body, method="POST")
    req.add_header("Content-Type", CT)
    req.add_header("Authorization", auth)
    if _context_id:
        req.add_header("X-Context", _context_id)
    with _opener.open(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def login():
    """Ouvre un contexte sysbus et memorise le contextID + les cookies."""
    global _context_id
    if not CFG["LIVEBOX_PASSWORD"]:
        raise RuntimeError(
            "LIVEBOX_PASSWORD absent. Il est ecrit dans "
            "/config/vssp/.livebox.env par le job de deploiement, depuis la "
            "variable CI/CD masquee LIVEBOX_PASSWORD. Verifier qu'elle existe "
            "dans GitLab (Settings > CI/CD > Variables)."
        )
    out = _post({
        "service": "sah.Device.Information",
        "method": "createContext",
        "parameters": {
            "applicationName": "so_sdkut",
            "username": CFG["LIVEBOX_USER"],
            "password": CFG["LIVEBOX_PASSWORD"],
        },
    }, "X-Sah-Login")
    ctx = (out.get("data") or {}).get("contextID")
    if not ctx:
        raise RuntimeError("authentification Livebox refusee: %s" % out)
    _context_id = ctx
    return ctx


def call(service, method, parameters=None):
    out = _post({
        "service": service,
        "method": method,
        "parameters": parameters or {},
    }, "X-Sah %s" % _context_id)
    if out.get("errors"):
        raise RuntimeError("%s.%s: %s" % (service, method, out["errors"]))
    return out.get("data") or out.get("status")


# ─────────────────────────────────────────────────────────────────────
# Utilitaires
# ─────────────────────────────────────────────────────────────────────
def kbps_to_mbps(v):
    try:
        return round(float(v) / 1000.0, 1)
    except (TypeError, ValueError):
        return 0.0


def humanize_lease(seconds):
    try:
        s = int(seconds)
    except (TypeError, ValueError):
        return "—"
    if s >= 86400 and s % 86400 == 0:
        return "%d j" % (s // 86400)
    if s >= 3600:
        return "%d h" % round(s / 3600.0)
    return "%d min" % round(s / 60.0)


def proto_name(p):
    """La Livebox renvoie les numeros de protocole IANA (6 = TCP, 17 = UDP)."""
    table = {"6": "TCP", "17": "UDP", "1": "ICMP"}
    parts = [table.get(x.strip(), x.strip().upper())
             for x in str(p).split(",") if x.strip()]
    return "/".join(parts) or "TCP"


def ip_key(ip):
    try:
        return tuple(int(x) for x in str(ip).split("."))
    except ValueError:
        return (999, 999, 999, 999)


def lan_devices():
    """Equipements vus par la box sur le LAN (nom, IP, MAC, actif)."""
    data = call("Devices", "get", {"expression": "lan and not self"})
    out = []
    for d in data or []:
        ip = d.get("IPAddress") or ""
        mac = d.get("PhysAddress") or d.get("MACAddress") or ""
        if not ip or not mac:
            continue
        out.append({
            "ip": ip,
            "hostname": d.get("Name") or d.get("Hostname") or "inconnu",
            "mac": mac.upper(),
            "active": bool(d.get("Active")),
            "layer2": d.get("Layer2Interface") or "",
        })
    return out


# ─────────────────────────────────────────────────────────────────────
# Modes
# ─────────────────────────────────────────────────────────────────────
def mode_wan():
    d = call("NMC", "getWANStatus") or {}
    link = str(d.get("LinkState", "")).lower()
    conn = str(d.get("ConnectionState", "")).lower()
    up = link in ("up", "connected") or conn in ("connected", "bound")
    return {
        "status": "up" if up else "down",
        "ip": d.get("IPAddress") or "—",
        "assignment": CFG["LIVEBOX_IP_MODE"],
        "downstream": kbps_to_mbps(d.get("DownstreamCurrRate")),
        "upstream": kbps_to_mbps(d.get("UpstreamCurrRate")),
    }


def mode_dhcp():
    lan = call("NMC", "getLANIP") or {}
    devices = {x["mac"]: x for x in lan_devices()}

    leases = []
    try:
        raw = call("DHCPv4.Server.Pool.default", "getLeases") or []
    except RuntimeError:
        raw = []
    for l in raw:
        mac = str(l.get("MACAddress") or "").upper()
        ip = l.get("IPAddress") or ""
        if not ip:
            continue
        leases.append({
            "ip": ip,
            "mac": mac,
            "hostname": (devices.get(mac) or {}).get("hostname", "inconnu"),
        })

    # Repli : si getLeases n'est pas expose, on derive les baux de la
    # liste des equipements actifs (hors adresses statiques hors plage).
    if not leases:
        leases = [{"ip": d["ip"], "mac": d["mac"], "hostname": d["hostname"]}
                  for d in devices.values() if d["active"]]

    leases.sort(key=lambda x: ip_key(x["ip"]))
    return {
        "count": len(leases),
        "pool_start": lan.get("DHCPMinAddress") or "192.168.1.100",
        "pool_end": lan.get("DHCPMaxAddress") or "192.168.1.200",
        "gateway": lan.get("Address") or CFG["LIVEBOX_HOST"],
        "netmask": lan.get("Netmask") or "255.255.255.0",
        "lease_time": humanize_lease(lan.get("LeaseTime")),
        "leases": leases,
    }


def mode_nat():
    data = call("Firewall", "getPortForwarding") or {}
    items = data.values() if isinstance(data, dict) else data
    rules = []
    for r in items:
        if not isinstance(r, dict):
            continue
        rules.append({
            "name": r.get("Description") or r.get("Id") or "Règle",
            "protocol": proto_name(r.get("Protocol")),
            "external_port": str(r.get("ExternalPort") or ""),
            "internal_ip": r.get("DestinationIPAddress") or "",
            "internal_port": str(r.get("InternalPort")
                                 or r.get("ExternalPort") or ""),
            "enabled": bool(r.get("Enable", True)),
        })
    rules.sort(key=lambda x: (not x["enabled"], x["name"].lower()))
    return {"count": len(rules), "rules": rules}


def mode_clients():
    """Table du commutateur : colonne 1 = IP, 2 = hostname, 3 = MAC.

    La MS510TX est un modele « Plus » : elle n'expose pas de table
    MAC-par-port exploitable en HTTP. La liste est donc reconstruite
    depuis les equipements vus par la Livebox, ce qui couvre tous les
    hotes branches derriere le commutateur.
    """
    devices = [d for d in lan_devices() if d["active"]]
    devices.sort(key=lambda x: ip_key(x["ip"]))
    clients = [{"ip": d["ip"], "hostname": d["hostname"], "mac": d["mac"]}
               for d in devices]
    wired = sum(1 for d in devices
                if "eth" in str(d["layer2"]).lower()
                or "lan" in str(d["layer2"]).lower())
    ports = int(CFG["NETGEAR_PORTS"] or 10)
    return {
        "count": len(clients),
        "clients": clients,
        "ports_up": min(wired, ports),
    }


MODES = {
    "wan": mode_wan,
    "dhcp": mode_dhcp,
    "nat": mode_nat,
    "clients": mode_clients,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in MODES:
        sys.stderr.write("usage: vssp_lan_probe.py {%s}\n"
                         % "|".join(MODES))
        return 2
    try:
        login()
        payload = MODES[sys.argv[1]]()
    except (urllib.error.URLError, RuntimeError, ValueError, OSError) as exc:
        sys.stderr.write("vssp_lan_probe: %s\n" % exc)
        return 1
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
