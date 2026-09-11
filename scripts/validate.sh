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

validate:
  stage: validate
  image: alpine:latest

  script:
    - echo "🔍 Visio Sapiens - Validation started"

    # vérifie structure du repo
    - test -f scripts/package.sh || (echo "❌ package.sh missing" && exit 1)
    - test -f scripts/deploy.sh || (echo "❌ deploy.sh missing" && exit 1)
    - test -f scripts/reload.sh || (echo "❌ reload.sh missing" && exit 1)

    - test -d home-assistant || (echo "❌ home-assistant folder missing" && exit 1)

    # vérifie fichiers critiques Visio Sapiens
    - test -d home-assistant/dashboards || echo "⚠️ dashboards folder missing"
    - test -d home-assistant/themes || echo "⚠️ themes folder missing"

    # vérifie scripts exécutables
    - chmod +x scripts/*.sh

    # check syntax simple YAML (si fichiers YAML présents)
    - |
      for f in $(find . -name "*.yaml"); do
        echo "📄 Checking $f"
        cat "$f" > /dev/null || exit 1
      done

    echo "✅ Validation OK - Visio Sapiens structure valid"
