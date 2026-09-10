#!/bin/sh
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


set -e

NAMESPACE="home-assistant"
POD="home-assistant-0"
CONTAINER="home-assistant"
PACKAGE="osvision-v2.tar.gz"

echo "🚀 Deploying OSVision V2 to Home Assistant..."

if [ ! -f "$PACKAGE" ]; then
  echo "❌ Package not found: $PACKAGE"
  exit 1
fi

echo "📤 Copying package to pod..."
kubectl -n $NAMESPACE cp $PACKAGE $POD:/config/$PACKAGE -c $CONTAINER

echo "📂 Extracting package inside Home Assistant..."
kubectl -n $NAMESPACE exec $POD -c $CONTAINER -- \
  tar -xzf /config/$PACKAGE -C /config/

echo "🔄 Reloading Home Assistant..."
kubectl -n $NAMESPACE exec $POD -c $CONTAINER -- \
  ha core reload || echo "⚠️ reload command failed (maybe HA CLI not available)"

echo "✅ Deployment completed"
