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

"""Visio Sapiens — visuels produits des modules du dashboard ENERGY.

Quand un nouvel appareil est branché, le scan le découvre et l'ajoute à la
liste des interrupteurs. Ce module va chercher la PHOTO du produit et la
dépose à côté, pour que la ligne montre le boîtier au lieu de seulement le
nommer.

La source est le catalogue Shopify public de Shelly, qui donne pour chaque
produit son titre et l'URL de son visuel. C'est la seule source utilisée :
elle est structurée, stable, et c'est le fabricant lui-même. Un modèle
d'une autre marque ne trouve rien, et la ligne garde son icône — un
dashboard sans photo reste un dashboard, une génération qui échoue parce
qu'un site est inaccessible n'en est plus un.

Trois règles qui font que ça ne casse jamais une génération :
  · rien n'est retéléchargé : un fichier déjà présent suffit ;
  · tout est borné dans le temps (timeouts courts) et sans relance ;
  · toute erreur réseau est journalisée puis avalée — le scan continue.

Usage :
    python3 vssp/vssp_module_images.py --devices … --images-dir …
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

# EN | Shelly's public storefront catalogue. Paged, 250 products a page.
# FR | Catalogue public de la boutique Shelly. Pagine, 250 produits par page.
CATALOGUE = "https://www.shelly.com/collections/all/products.json"
CATALOGUE_PAGES = 4
TIMEOUT = 20

# EN | Shopify resizes on the fly. 240px wide is what the dashboard draws at
# EN | most (a rail header), and it turns a 1 MB press photo into ~30 KB.
# FR | Shopify redimensionne a la volee. 240px de large est ce que le
# FR | dashboard affiche au maximum (un en-tete de rail), et cela ramene une
# FR | photo de presse de 1 Mo a ~30 Ko.
IMAGE_WIDTH = 240

UA = {"User-Agent": "Mozilla/5.0 (Visio Sapiens dashboard generator)"}


def slug(text: str) -> str:
    """« Shelly Power Strip 4 Gen4 » → « shelly-power-strip-4-gen4 »."""
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower())
    return s.strip("-")


def normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def fetch_catalogue(url: str = CATALOGUE, pages: int = CATALOGUE_PAGES) -> list[dict]:
    """→ [{title, image}] — vide si le catalogue est injoignable."""
    out: list[dict] = []
    for page in range(1, pages + 1):
        req = urllib.request.Request(f"{url}?limit=250&page={page}", headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                doc = json.load(resp)
        except (urllib.error.URLError, urllib.error.HTTPError,
                json.JSONDecodeError, TimeoutError) as exc:
            print(f"  ⚠ catalogue produits injoignable ({exc}) — "
                  f"les visuels manquants restent des icones.")
            break
        products = doc.get("products") or []
        if not products:
            break
        for prod in products:
            images = prod.get("images") or []
            if images and images[0].get("src"):
                out.append({"title": prod.get("title", ""),
                            "image": images[0]["src"]})
    return out


def best_match(model: str, catalogue: list[dict]) -> str | None:
    """L'URL du visuel du produit qui correspond le mieux au modèle.

    EN | Exact title wins. Otherwise the shortest title that CONTAINS the
    EN | model, which is what keeps "Shelly Plug M Gen3" off the
    EN | "Shelly Plug M Gen3 Black 4-pack" photo — a picture of four boxes
    EN | is not a picture of the one on the wall.
    FR | Le titre exact gagne. Sinon le titre le plus COURT qui contient le
    FR | modele, ce qui evite d'attribuer a « Shelly Plug M Gen3 » la photo
    FR | de « Shelly Plug M Gen3 Black 4-pack » — une image de quatre
    FR | boitiers n'est pas l'image de celui qui est au mur.
    """
    want = normalise(model)
    if not want:
        return None
    contains = []
    for prod in catalogue:
        title = normalise(prod["title"])
        if title == want:
            return prod["image"]
        if want and want in title:
            contains.append(prod)
    if contains:
        return min(contains, key=lambda p: len(p["title"]))["image"]

    # EN | Last stage: every word of the model present in the title, in any
    # EN | order. Home Assistant reports "Shelly Pro Dual Cover PM" while the
    # EN | shop sells "Shelly Pro Dual Cover / Shutter PM" — the same object,
    # EN | which no substring test will ever pair up. Two words minimum, so a
    # EN | model reduced to one generic token cannot drag in a whole shelf.
    # FR | Dernier etage : tous les mots du modele presents dans le titre,
    # FR | dans n'importe quel ordre. Home Assistant annonce « Shelly Pro Dual
    # FR | Cover PM » la ou la boutique vend « Shelly Pro Dual Cover / Shutter
    # FR | PM » — le meme objet, qu'aucun test de sous-chaine n'appariera
    # FR | jamais. Deux mots minimum, pour qu'un modele reduit a un seul terme
    # FR | generique ne ramene pas un rayon entier.
    words = [w for w in re.split(r"[^a-z0-9]+", (model or "").lower()) if w]
    if len(words) < 2:
        return None
    every = [p for p in catalogue
             if all(w in normalise(p["title"]) for w in words)]
    if not every:
        return None
    return min(every, key=lambda p: len(p["title"]))["image"]


def download(url: str, dest: Path) -> bool:
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(f"{url}{sep}width={IMAGE_WIDTH}", headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        print(f"  ⚠ telechargement echoue ({exc})")
        return False
    if not data.startswith(b"\x89PNG") and not data.startswith(b"\xff\xd8"):
        print(f"  ⚠ {dest.name} : ce n'est ni un PNG ni un JPEG, ignore")
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return True


def resolve(models: list[str], images_dir: Path,
            known: dict | None = None) -> dict[str, str]:
    """modele → nom de fichier, en téléchargeant ce qui manque.

    `known` est la table déjà établie : elle est respectée telle quelle, et
    un modèle qu'elle couvre n'est jamais rejoué.
    """
    table = dict(known or {})
    wanted = [m for m in sorted({m for m in models if m})
              if not (table.get(m) and (images_dir / table[m]).exists())]

    # EN | A model whose file is already on disk under its own slug needs no
    # EN | network at all — that is the shipped baseline, and the usual case.
    # FR | Un modele dont le fichier est deja sur le disque sous son propre
    # FR | slug ne demande aucun reseau — c'est la base livree, et le cas
    # FR | courant.
    still: list[str] = []
    for model in wanted:
        local = f"{slug(model)}.png"
        if (images_dir / local).exists():
            table[model] = local
        else:
            still.append(model)

    if not still:
        return table

    print(f"  {len(still)} visuel(s) produit a chercher : {', '.join(still)}")
    catalogue = fetch_catalogue()
    if not catalogue:
        return table
    print(f"  catalogue : {len(catalogue)} produits")
    for model in still:
        url = best_match(model, catalogue)
        if not url:
            print(f"  · {model} : aucun produit correspondant")
            continue
        name = f"{slug(model)}.png"
        if download(url, images_dir / name):
            size = (images_dir / name).stat().st_size // 1024
            table[model] = name
            print(f"  + {model} → {name} ({size} Ko)")
    return table


def models_in(doc: dict) -> list[str]:
    """Tous les modèles cités par le parc : appareils, circuits, modules."""
    out = []
    for key in ("devices", "circuits", "modules"):
        for item in doc.get(key) or []:
            if item.get("model"):
                out.append(item["model"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--devices",
                    default="home-assistant/dashboards/model/energy_devices.yaml")
    ap.add_argument("--images-dir",
                    default="home-assistant/www/vssp/modules",
                    help="Ou deposer les visuels (cote pod : "
                         "/config/www/vssp/modules)")
    args = ap.parse_args()

    path = Path(args.devices)
    if not path.exists():
        print(f"✗ {path} est absent — lancez d'abord vssp_energy_sync.py")
        return 1
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    table = resolve(models_in(doc), Path(args.images_dir), doc.get("images"))
    if table != (doc.get("images") or {}):
        doc["images"] = table
        # EN | Keep the file's header: it explains what the file is and who
        # EN | maintains it, and safe_dump would drop every comment.
        # FR | On garde l'en-tete du fichier : il explique ce qu'est ce
        # FR | fichier et qui le maintient, et safe_dump effacerait tout
        # FR | commentaire.
        text = path.read_text(encoding="utf-8")
        header = ""
        for line in text.splitlines(keepends=True):
            if not line.startswith("#"):
                break
            header += line
        path.write_text(
            header + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False,
                                    default_flow_style=False),
            encoding="utf-8")
        print(f"✓ {path} : table des visuels mise a jour")
    else:
        print("= Aucun nouveau visuel.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
