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


"""Narration, subtitles and timing table of the YouTube pilot, from its script.

EN | The script (docs/project/episode-01-vision-architecture{,.fr}.md) is the
EN | only source. This rebuilds, per language:
EN |   episode-01-narration.<lang>.txt  spoken text only, one section per audio file
EN |   episode-01.<lang>.srt            subtitles, 42 chars a line, never 3 lines
EN |   the table between the TIMING-TABLE markers inside the script itself
EN | Voice-over = a blockquote whose first line opens with a double quote; the
EN | on-screen text boxes are skipped. Timing: 140 words a minute from the start
EN | of each section's slot, compressed only when the section overruns its slot
EN | -- one section is one audio file placed at its slot, so subtitles follow
EN | the voice rather than being stretched over silence.
FR | Le script est l'unique source. Ceci reconstruit, par langue, la narration,
FR | les sous-titres et le tableau de minutage. Voix off = une citation dont la
FR | premiere ligne s'ouvre sur un guillemet ; les encadres a l'ecran sont
FR | ignores. Minutage : 140 mots/minute depuis le debut du creneau, compresse
FR | seulement quand la section deborde.

Usage: python3 scripts/build_episode_media.py [docs/project]
"""
import math
import re
import sys
from pathlib import Path

WPM = 140
MAX_LINE = 42
NBSP = " "

L10N = {
    "fr": dict(
        head=["# VISIO SAPIENS - EPISODE PILOTE - Vision & Architecture",
              "# Narration seule. Une section = un fichier audio, pose au debut de son creneau.",
              "# Debit de reference : 140 mots/minute.",
              "# GENERE depuis episode-01-vision-architecture.fr.md — ne pas editer a la main."],
        meta="##      narration | creneau {a}-{b} ({s}s) | {w} mots | vise {t}s",
        total="# TOTAL : {w} mots, {m} min {s:02d} s",
        th="| # | Section | Créneau | Narration | Écart |",
        tot="| | **Total** | **{slot}** | **{nar}** | **{d}** |",
        short="Sections volontairement courtes, où l'image porte le temps : {lst}. Partout ailleurs, la narration remplit son créneau.",
        none="La narration remplit chaque créneau.",
        names=["Cold open", "Mon approche", "La complexité de HA", "Ce qu'est Visio Sapiens",
               "Pourquoi pas les cartes natives", "Diagramme d'architecture", "Visite de HOME",
               "La console", "La sécurité par défaut", "Une note sur les noms", "Montage — ce qui a été livré", "La carte de la série",
               "Conclusion"],
    ),
    "en": dict(
        head=["# VISIO SAPIENS - PILOT EPISODE - Vision & Architecture",
              "# Narration only. One section = one audio file, placed at the start of its slot.",
              "# Reference pace: 140 words per minute.",
              "# GENERATED from episode-01-vision-architecture.md — do not edit by hand."],
        meta="##      narration | slot {a}-{b} ({s}s) | {w} words | target {t}s",
        total="# TOTAL: {w} words, {m} min {s:02d} s",
        th="| # | Section | Slot | Narration | Delta |",
        tot="| | **Total** | **{slot}** | **{nar}** | **{d}** |",
        short="Sections deliberately short, where the picture carries the time: {lst}. Everywhere else the narration fills its slot.",
        none="The narration fills every slot.",
        names=["Cold open", "My approach", "HA's complexity", "What Visio Sapiens is",
               "Why not native cards", "Architecture diagram", "HOME tour",
               "The console", "Secure by default", "A note on names", "Montage — what has shipped", "The map of the series",
               "Close"],
    ),
}

SEC_RE = re.compile(r"^## (\d+)\. (.+?) \((\d+):(\d\d) - (\d+):(\d\d)\)\s*$")


def parse(md: str):
    sections, cur, group = [], None, None

    def flush():
        nonlocal group
        if cur is not None and group:
            text = "\n".join(group).strip()
            if text.startswith('"'):
                paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
                paras[0] = paras[0].lstrip('"')
                paras[-1] = paras[-1].rstrip('"')
                cur["paras"].extend(clean(p) for p in paras)
        group = None

    for line in md.splitlines():
        m = SEC_RE.match(line)
        if m:
            flush()
            n, title = int(m.group(1)), m.group(2)
            a = int(m.group(3)) * 60 + int(m.group(4))
            b = int(m.group(5)) * 60 + int(m.group(6))
            cur = dict(n=n, title=title, a=a, b=b, paras=[])
            sections.append(cur)
            continue
        if line.startswith("## ") or line.startswith("---"):
            flush()
            if line.startswith("## "):
                cur = None
            continue
        if line.startswith(">"):
            if group is None:
                group = []
            group.append(line[1:].lstrip(" ") if len(line) > 1 else "")
        else:
            flush()
    flush()
    return sections


def clean(p: str) -> str:
    p = p.replace("**", "").replace("`", "")
    p = re.sub(r"\s+", " ", p).strip()
    return p


def words(s: str) -> int:
    return sum(1 for t in s.split() if re.search(r"\w", t))


def mmss(sec: float) -> str:
    sec = int(round(sec))
    return f"{sec // 60}:{sec % 60:02d}"


def ts(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def glue(s: str) -> str:
    # Keep French spaced punctuation and em dashes on the word before them.
    s = re.sub(r" ([:;?!»—])", NBSP + r"\1", s)
    s = s.replace("« ", "«" + NBSP)
    return s


def wrap(chunk_words):
    text = " ".join(chunk_words)
    if len(text) <= MAX_LINE:
        return [text]
    best = None
    for i in range(1, len(chunk_words)):
        l1, l2 = " ".join(chunk_words[:i]), " ".join(chunk_words[i:])
        if len(l1) <= MAX_LINE and len(l2) <= MAX_LINE:
            score = max(len(l1), len(l2))
            if best is None or score < best[0]:
                best = (score, [l1, l2])
    return best[1] if best else None


def split_sentence(sentence: str):
    toks = glue(sentence).split(" ")
    n = max(1, math.ceil(len(sentence) / (2 * MAX_LINE - 4)))
    while True:
        total = sum(len(t) + 1 for t in toks)
        target = total / n
        chunks, cur, acc = [], [], 0
        for t in toks:
            if cur and acc + len(t) + 1 > target * (len(chunks) + 1) + 6 and len(chunks) < n - 1:
                chunks.append(cur)
                cur = []
            cur.append(t)
            acc += len(t) + 1
        chunks.append(cur)
        # no orphan: a 1-2 word chunk is merged into its neighbour when it fits
        merged = []
        for c in chunks:
            if merged and words(" ".join(c)) <= 2 and wrap(merged[-1] + c):
                merged[-1] = merged[-1] + c
            else:
                merged.append(c)
        lines = [wrap(c) for c in merged]
        if all(lines):
            return [(c, l) for c, l in zip(merged, lines)]
        n += 1


def cues_for(section):
    sentences = []
    for p in section["paras"]:
        sentences += [s for s in re.split(r"(?<=[.!?…])\s+", p) if s]
    chunks = []
    for s in sentences:
        chunks += split_sentence(s)
    total_w = sum(words(" ".join(c)) for c, _ in chunks)
    slot = section["b"] - section["a"]
    spw = min(60 / WPM, slot / total_w) if total_w else 0
    t = section["a"]
    out = []
    for c, lines in chunks:
        d = words(" ".join(c)) * spw
        out.append((t, t + d, lines))
        t += d
    return out


def build(md_path: Path, lang: str, txt_path: Path, srt_path: Path):
    L = L10N[lang]
    md = md_path.read_text(encoding="utf-8")
    secs = parse(md)

    # narration
    out = L["head"] + ["#" + "-" * 68, ""]
    total_w = 0
    rows = []
    for s in secs:
        w = sum(words(p) for p in s["paras"])
        total_w += w
        tgt = round(w / WPM * 60)
        slot = s["b"] - s["a"]
        rows.append((s, slot, tgt))
        out.append(f"## [{s['n']:02d}] {s['title']}")
        out.append(L["meta"].format(a=mmss(s["a"]), b=mmss(s["b"]), s=slot, w=w, t=tgt))
        out.append("")
        for p in s["paras"]:
            out.append(p)
            out.append("")
    secs_total = round(total_w / WPM * 60)
    out.append("#" + "-" * 68)
    out.append(L["total"].format(w=total_w, m=secs_total // 60, s=secs_total % 60))
    txt_path.write_text("\n".join(out) + "\n", encoding="utf-8")

    # srt
    srt, i = [], 1
    for s in secs:
        for a, b, lines in cues_for(s):
            srt += [str(i), f"{ts(a)} --> {ts(b)}", *lines, ""]
            i += 1
    srt_path.write_text("\n".join(srt), encoding="utf-8")

    # timing table
    tab = [L["th"], "|---|---|---|---|---|"]
    short = []
    for s, slot, tgt in rows:
        d = tgt - slot
        sign = "+" if d > 0 else ("−" if d < 0 else "±")
        tab.append(f"| {s['n']} | {L['names'][s['n']]} | {slot} s | {tgt} s | {sign}{abs(d)} s |")
        if d <= -15:
            short.append(str(s["n"]))
    slot_total = secs[-1]["b"] - secs[0]["a"]
    d = secs_total - slot_total
    sign = "+" if d > 0 else ("−" if d < 0 else "±")
    tab.append(L["tot"].format(slot=mmss(slot_total), nar=mmss(secs_total), d=f"{sign}{abs(d)} s"))
    tab.append("")
    tab.append(L["short"].format(lst=", ".join(short)) if short else L["none"])
    block = "<!-- TIMING-TABLE -->\n" + "\n".join(tab) + "\n<!-- /TIMING-TABLE -->"
    if "<!-- /TIMING-TABLE -->" in md:
        md = re.sub(r"<!-- TIMING-TABLE -->.*?<!-- /TIMING-TABLE -->", lambda _: block, md, flags=re.S)
    else:
        md = md.replace("<!-- TIMING-TABLE -->", block)
    md_path.write_text(md, encoding="utf-8")

    print(f"{md_path.name}: {len(secs)} sections, {total_w} words, {mmss(secs_total)} narration "
          f"for {mmss(slot_total)} of slots, {i - 1} cues")
    for s, slot, tgt in rows:
        flag = "  OVER" if tgt > slot + 5 else ""
        print(f"   [{s['n']:02d}] {slot:4d}s slot  {tgt:4d}s narration{flag}")


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "docs" / "project"
    build(root / "episode-01-vision-architecture.fr.md", "fr",
          root / "episode-01-narration.fr.txt", root / "episode-01.fr.srt")
    build(root / "episode-01-vision-architecture.md", "en",
          root / "episode-01-narration.en.txt", root / "episode-01.en.srt")
