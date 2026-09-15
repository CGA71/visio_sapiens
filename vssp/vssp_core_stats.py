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
# Visio Sapiens — CORE screen: host partitions and k3s cluster state
#
# EN | WHY THIS FILE EXISTS
# EN | core.html reads CPU, RAM, load and temperatures from the Glances
# EN | integration, through Home Assistant. Two things never reach it that
# EN | way. The partitions: Glances in Home Assistant reports "/" once and
# EN | then every kubelet volume bind-mounted from it, dozens of lookalike
# EN | rows, none of them /boot/efi. And the cluster: its panel was fed by
# EN | /opt/osvision/k3s_stats.sh, a root timer installed on the host by
# EN | hand, outside this repository, writing into the old osvision_v2
# EN | folder — no version (it asks `kubectl version --short`, which no
# EN | longer exists), event messages cut to their last word, and nothing
# EN | about failing pods, node pressure or load.
# EN | This script is that collector, in the repository, through the same
# EN | door as vssp_infra_updates.py: the host credentials come from the
# EN | safe (vssp-maint), one run, and Home Assistant only ever sees the
# EN | JSON written back. Every command is a READ: df, nproc, os-release,
# EN | `k3s kubectl get/top`, `openssl x509 -enddate`. Nothing is written
# EN | on the host.
# FR | POURQUOI CE FICHIER EXISTE
# FR | core.html lit CPU, RAM, charge et temperatures dans l integration
# FR | Glances, via Home Assistant. Deux choses n y arrivent jamais par ce
# FR | chemin. Les partitions : Glances dans Home Assistant remonte « / » une
# FR | fois puis chaque volume kubelet monte depuis lui, des dizaines de
# FR | lignes identiques, et jamais /boot/efi. Et le cluster : son panneau
# FR | etait nourri par /opt/osvision/k3s_stats.sh, un minuteur root pose a
# FR | la main sur l hote, hors de ce depot, qui ecrit dans l ancien dossier
# FR | osvision_v2 — sans version (il demande `kubectl version --short`, qui
# FR | n existe plus), messages d evenements coupes a leur dernier mot, et
# FR | rien sur les pods en echec, la pression des noeuds ou la charge.
# FR | Ce script est ce collecteur, dans le depot, par la meme porte que
# FR | vssp_infra_updates.py : les identifiants de l hote viennent du coffre
# FR | (vssp-maint), le temps d une execution, et Home Assistant ne voit que
# FR | le JSON ecrit en retour. Chaque commande est une LECTURE : df, nproc,
# FR | os-release, `k3s kubectl get/top`, `openssl x509 -enddate`. Rien
# FR | n est ecrit sur l hote.
#
# EN | The advice itself is NOT computed here: core.html turns these facts
# EN | into recommendations, next to the numbers they are about, in the
# EN | language of its ?lang=. This file only measures.
# FR | Les preconisations ne sont PAS calculees ici : core.html transforme
# FR | ces faits en recommandations, a cote des chiffres qu elles concernent,
# FR | dans la langue de son ?lang=. Ce fichier ne fait que mesurer.
#
# Usage:
#     python3 vssp_core_stats.py --out /config/www/vssp/core_stats.json
#     python3 vssp_core_stats.py --dry-run          # no safe, no ssh
# ---------------------------------------------------------------------------
"""Visio Sapiens — CORE screen collector: partitions and k3s state."""
import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vssp_infra_updates as infra  # noqa: E402

MESSAGES = {
    "stats.ok": "Host and cluster read.",
    "stats.k3s_down": "Host read; the cluster did not answer: {detail}",
    "stats.dry_run": "Dry run: nothing probed.",
}

# EN | df sees every bind mount the kubelet and containerd make from "/":
# EN | same device, same numbers, one row per pod volume. They are the disk
# EN | "/" again, not partitions. Filesystem types are filtered by df itself.
# FR | df voit chaque montage lie que font le kubelet et containerd depuis
# FR | « / » : meme peripherique, memes chiffres, une ligne par volume de pod.
# FR | C est encore le disque « / », pas des partitions. Les types de
# FR | systemes de fichiers sont filtres par df lui-meme.
DF_EXCLUDE_TYPES = ("tmpfs", "devtmpfs", "squashfs", "overlay", "efivarfs",
                    "fuse.snapfuse", "nsfs", "ramfs")
MOUNT_SKIP = ("/var/lib/kubelet", "/run", "/snap", "/var/lib/docker",
              "/var/lib/rancher/k3s/agent/containerd", "/var/snap")

# EN | Container states that mean "this will not fix itself". Everything a
# EN | pod goes through on a normal start (ContainerCreating, PodInitializing)
# EN | is left out, or every deploy would light the panel orange.
# FR | Etats de conteneur qui veulent dire « cela ne se reparera pas seul ».
# FR | Ce que traverse un pod a un demarrage normal (ContainerCreating,
# FR | PodInitializing) est laisse de cote, sinon chaque deploiement
# FR | allumerait le panneau en orange.
BAD_WAITING = {"CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull",
               "CreateContainerConfigError", "CreateContainerError",
               "InvalidImageName", "RunContainerError"}

APISERVER_CERT = "/var/lib/rancher/k3s/server/tls/serving-kube-apiserver.crt"


def status(key: str, **vars_) -> dict:
    template = MESSAGES.get(key, key)
    try:
        rendered = template.format(**vars_)
    except (KeyError, IndexError):
        rendered = template
    return {"message_key": key, "message_vars": vars_, "message": rendered}


# ═══════════════════════════════════════════════════════════════════════════
# EN | HOST / FR | HOTE
# ═══════════════════════════════════════════════════════════════════════════
def df_command(inodes: bool) -> str:
    # EN | LC_ALL=C: the host answers in French otherwise, and the header
    # EN | line is the only thing skipped by position.
    # FR | LC_ALL=C : sinon l hote repond en francais, et la ligne d en-tete
    # FR | est la seule chose sautee par position.
    excl = " ".join(f"-x {t}" for t in DF_EXCLUDE_TYPES)
    return f"LC_ALL=C df -P {'-i' if inodes else '-T -B1'} {excl} 2>/dev/null"


def parse_partitions(space: str, inodes: str) -> list[dict]:
    inode_pct: dict[str, int | None] = {}
    for line in inodes.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 6:
            pct = parts[4].rstrip("%")
            inode_pct[parts[5]] = int(pct) if pct.isdigit() else None
    out = []
    for line in space.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 7:
            continue
        device, fstype, size, used, avail, pct, mount = parts[:7]
        if any(mount == p or mount.startswith(p + "/") for p in MOUNT_SKIP):
            continue
        try:
            size_b, used_b, avail_b = int(size), int(used), int(avail)
        except ValueError:
            continue
        out.append({
            "mount": mount, "device": device, "fs": fstype,
            "size": size_b, "used": used_b, "avail": avail_b,
            "pct": int(pct.rstrip("%")) if pct.rstrip("%").isdigit() else None,
            "inodes_pct": inode_pct.get(mount),
        })
    return out


def read_host(host: "infra.Host") -> dict:
    _c, space, _e = host.run(df_command(inodes=False))
    _c, inodes, _e = host.run(df_command(inodes=True))
    _c, facts, _e = host.run(
        "nproc; (. /etc/os-release 2>/dev/null && echo \"$PRETTY_NAME\"); uname -r")
    lines = [l.strip() for l in facts.splitlines()]
    cpus = int(lines[0]) if lines and lines[0].isdigit() else None
    return {
        "cpus": cpus,
        "os": lines[1] if len(lines) > 1 else "",
        "kernel": lines[2] if len(lines) > 2 else "",
        "partitions": parse_partitions(space, inodes),
    }


# ═══════════════════════════════════════════════════════════════════════════
# EN | CLUSTER / FR | CLUSTER
# ═══════════════════════════════════════════════════════════════════════════
def kubectl_json(host: "infra.Host", args: str) -> dict:
    # EN | run_maybe_sudo: k3s.yaml is 0600 root unless k3s was started with
    # EN | --write-kubeconfig-mode, and both setups are normal.
    # FR | run_maybe_sudo : k3s.yaml est en 0600 root sauf si k3s a ete
    # FR | demarre avec --write-kubeconfig-mode, et les deux cas sont normaux.
    code, out, err = host.run_maybe_sudo(f"k3s kubectl {args} -o json 2>/dev/null")
    if code != 0 or not out.strip():
        raise RuntimeError((err or out or f"exit {code}").strip()[:200])
    return json.loads(out)


def iso(ts: str | None) -> str:
    return ts or ""


def node_summary(item: dict, top: dict) -> dict:
    meta, st = item.get("metadata", {}), item.get("status", {})
    conds = {c.get("type"): c.get("status") for c in st.get("conditions", [])}
    labels = meta.get("labels", {}) or {}
    roles = sorted(l.split("/", 1)[1] for l in labels if l.startswith("node-role.kubernetes.io/"))
    name = meta.get("name", "")
    return {
        "name": name,
        "ready": conds.get("Ready") == "True",
        "roles": ",".join(roles) or "worker",
        "kubelet": (st.get("nodeInfo") or {}).get("kubeletVersion", ""),
        "cpu": (st.get("capacity") or {}).get("cpu", ""),
        "memory": (st.get("capacity") or {}).get("memory", ""),
        "pods_capacity": int((st.get("allocatable") or {}).get("pods", "0") or 0),
        "pressure": [t for t in ("MemoryPressure", "DiskPressure", "PIDPressure",
                                 "NetworkUnavailable") if conds.get(t) == "True"],
        "cpu_pct": top.get(name, {}).get("cpu_pct"),
        "mem_pct": top.get(name, {}).get("mem_pct"),
    }


def pod_problems(pods: list[dict]) -> tuple[dict, list[dict]]:
    counts = {"total": 0, "running": 0, "pending": 0, "failed": 0,
              "succeeded": 0, "not_ready": 0, "restarts": 0}
    problems = []
    for p in pods:
        meta, st = p.get("metadata", {}), p.get("status", {})
        phase = st.get("phase", "Unknown")
        counts["total"] += 1
        key = phase.lower()
        if key in counts:
            counts[key] += 1
        restarts, reason, ready = 0, "", True
        for cs in (st.get("initContainerStatuses") or []) + (st.get("containerStatuses") or []):
            restarts += int(cs.get("restartCount", 0) or 0)
            waiting = (cs.get("state") or {}).get("waiting") or {}
            last = (cs.get("lastState") or {}).get("terminated") or {}
            if waiting.get("reason") in BAD_WAITING:
                reason = waiting["reason"]
            elif last.get("reason") == "OOMKilled" and not reason:
                reason = "OOMKilled"
            if not cs.get("ready", False) and cs in (st.get("containerStatuses") or []):
                ready = False
        counts["restarts"] += restarts
        if phase == "Running" and not ready:
            counts["not_ready"] += 1
        if phase == "Failed":
            reason = reason or st.get("reason", "") or "Failed"
        elif phase == "Pending" and not reason:
            # EN | Pending for more than five minutes is a scheduling or
            # EN | volume problem; less is an ordinary start.
            # FR | En attente depuis plus de cinq minutes : un probleme de
            # FR | placement ou de volume ; moins, un demarrage ordinaire.
            created = meta.get("creationTimestamp", "")
            try:
                age = _dt.datetime.now(_dt.timezone.utc) - _dt.datetime.fromisoformat(
                    created.replace("Z", "+00:00"))
                if age.total_seconds() > 300:
                    reason = "Pending"
            except ValueError:
                pass
        if reason or restarts >= 10:
            problems.append({"ns": meta.get("namespace", ""), "name": meta.get("name", ""),
                             "phase": phase, "reason": reason, "restarts": restarts})
    problems.sort(key=lambda x: (x["reason"] == "", -x["restarts"]))
    return counts, problems[:12]


def workload_summary(items: list[dict]) -> dict:
    out = {"deployments": 0, "statefulsets": 0, "daemonsets": 0, "unavailable": [],
           "top": []}
    for it in items:
        kind, meta = it.get("kind", ""), it.get("metadata", {})
        spec, st = it.get("spec", {}) or {}, it.get("status", {}) or {}
        if kind == "Deployment":
            out["deployments"] += 1
            want, have = int(spec.get("replicas", 1) or 0), int(st.get("availableReplicas", 0) or 0)
        elif kind == "StatefulSet":
            out["statefulsets"] += 1
            want, have = int(spec.get("replicas", 1) or 0), int(st.get("readyReplicas", 0) or 0)
        elif kind == "DaemonSet":
            out["daemonsets"] += 1
            want, have = int(st.get("desiredNumberScheduled", 0) or 0), int(st.get("numberAvailable", 0) or 0)
        else:
            continue
        row = {"kind": kind, "ns": meta.get("namespace", ""), "name": meta.get("name", ""),
               "ready": f"{have}/{want}"}
        out["top"].append(row)
        if have < want:
            out["unavailable"].append(row)
    out["top"] = out["top"][:10]
    return out


def warning_events(items: list[dict]) -> list[dict]:
    rows = []
    for ev in items:
        when = ev.get("lastTimestamp") or ev.get("eventTime") or \
            (ev.get("metadata") or {}).get("creationTimestamp") or ""
        obj = ev.get("involvedObject") or {}
        rows.append({
            "time": iso(when), "reason": ev.get("reason", ""),
            "ns": obj.get("namespace", ""),
            "object": f"{obj.get('kind', '').lower()}/{obj.get('name', '')}",
            "message": re.sub(r"\s+", " ", ev.get("message", "")).strip()[:240],
            "count": int(ev.get("count", 1) or 1),
        })
    rows.sort(key=lambda r: r["time"], reverse=True)
    return rows[:8]


def read_k3s(host: "infra.Host") -> dict:
    _c, active, _e = host.run("systemctl is-active k3s 2>/dev/null")
    _c, version, _e = host.run("k3s --version 2>/dev/null | head -1")
    m = re.search(r"v\d+\.\d+\.\d+\+k3s\d+", version)
    k3s = {"service": active.strip() or "unknown", "version": m.group(0) if m else ""}

    everything = kubectl_json(
        host, "get nodes,pods,deployments,statefulsets,daemonsets,pvc,services,namespaces -A")
    by_kind: dict[str, list] = {}
    for it in everything.get("items", []):
        by_kind.setdefault(it.get("kind", ""), []).append(it)

    # EN | metrics-server ships with k3s, but `top` is allowed to be missing:
    # EN | the panel simply shows no load then.
    # FR | metrics-server est livre avec k3s, mais `top` a le droit de
    # FR | manquer : le panneau n affiche alors simplement pas de charge.
    top: dict[str, dict] = {}
    code, out, _e = host.run_maybe_sudo("k3s kubectl top nodes --no-headers 2>/dev/null")
    if code == 0:
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 5:
                cpu, mem = parts[2].rstrip("%"), parts[4].rstrip("%")
                top[parts[0]] = {"cpu_pct": int(cpu) if cpu.isdigit() else None,
                                 "mem_pct": int(mem) if mem.isdigit() else None}

    try:
        events = warning_events(kubectl_json(
            host, "get events -A --field-selector type=Warning").get("items", []))
    except (RuntimeError, ValueError):
        events = []

    cert_days = None
    code, out, _e = host.run_maybe_sudo(
        f"openssl x509 -enddate -noout -in {APISERVER_CERT} 2>/dev/null")
    m = re.search(r"notAfter=(.+)", out or "")
    if code == 0 and m:
        try:
            end = _dt.datetime.strptime(m.group(1).strip(), "%b %d %H:%M:%S %Y %Z")
            cert_days = (end - _dt.datetime.utcnow()).days
        except ValueError:
            pass

    counts, problems = pod_problems(by_kind.get("Pod", []))
    namespaces: dict[str, int] = {}
    for p in by_kind.get("Pod", []):
        ns = (p.get("metadata") or {}).get("namespace", "")
        namespaces[ns] = namespaces.get(ns, 0) + 1
    pvcs = by_kind.get("PersistentVolumeClaim", [])
    k3s.update({
        "reachable": True,
        "nodes": [node_summary(n, top) for n in by_kind.get("Node", [])],
        "pods": counts,
        "problem_pods": problems,
        "workloads": workload_summary(by_kind.get("Deployment", []) +
                                      by_kind.get("StatefulSet", []) +
                                      by_kind.get("DaemonSet", [])),
        "services": len(by_kind.get("Service", [])),
        "namespaces": len(by_kind.get("Namespace", [])),
        "top_namespaces": [{"ns": k, "count": v} for k, v in
                           sorted(namespaces.items(), key=lambda kv: -kv[1])[:8]],
        "pvc": {"total": len(pvcs), "not_bound": [
            {"ns": (p.get("metadata") or {}).get("namespace", ""),
             "name": (p.get("metadata") or {}).get("name", ""),
             "phase": (p.get("status") or {}).get("phase", "")}
            for p in pvcs if (p.get("status") or {}).get("phase") != "Bound"]},
        "events": events,
        "cert_days": cert_days,
    })
    return k3s


# ═══════════════════════════════════════════════════════════════════════════
def carry_forward(out_path: Path, payload: dict) -> dict:
    """EN | The last measurement, marked stale — see the same function in
    EN | vssp_infra_updates.py: numbers remembered and said so beat numbers
    EN | that silently look current.
    FR | La derniere mesure, marquee perimee — voir la meme fonction dans
    FR | vssp_infra_updates.py : des chiffres souvenus et presentes comme tels
    FR | valent mieux que des chiffres qui paraissent actuels en silence."""
    try:
        previous = json.loads(out_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    for key in ("host", "k3s", "measured"):
        if key in previous:
            payload[key] = previous[key]
    payload["stale"] = bool(previous)
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description="Visio Sapiens — CORE collector")
    ap.add_argument("--out", default="/config/www/vssp/core_stats.json")
    ap.add_argument("--vault-addr", default=infra.DEFAULT_VAULT_ADDR)
    ap.add_argument("--token-file", default="/config/vssp/.vault_maint_token")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    out_path = Path(args.out)

    if args.dry_run:
        infra.write_json(out_path, dict(status("stats.dry_run"), ok=True))
        return 0
    try:
        safe = infra.Safe.open(args.vault_addr, Path(args.token_file))
        host = infra.open_host(safe)
    except infra.VaultError as exc:
        # EN | Most often a sealed safe after a host reboot: the page says so
        # EN | and falls back to what it can still read.
        # FR | Le plus souvent un coffre scelle apres un redemarrage d hote :
        # FR | la page le dit et se rabat sur ce qu elle peut encore lire.
        payload = carry_forward(out_path, dict(exc.payload, ok=False))
        infra.write_json(out_path, payload)
        print(payload["message"], file=sys.stderr)
        return 1

    now = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        with host:
            data = {"host": read_host(host), "measured": now}
            try:
                data["k3s"] = read_k3s(host)
                result = status("stats.ok")
            except (RuntimeError, ValueError) as exc:
                data["k3s"] = {"reachable": False, "detail": str(exc)[:200]}
                result = status("stats.k3s_down", detail=str(exc)[:200])
    except infra.VaultError as exc:
        payload = carry_forward(out_path, dict(exc.payload, ok=False))
        infra.write_json(out_path, payload)
        print(payload["message"], file=sys.stderr)
        return 1

    payload = dict(result, ok=True, stale=False, **data)
    infra.write_json(out_path, payload)
    print(payload["message"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
