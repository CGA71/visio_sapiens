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

echo "📦 OSVision V2 - Packaging..."

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build"
OUTPUT="$ROOT_DIR/osvision-v2.tar.gz"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo "📁 Copying Home Assistant files..."
cp -r "$ROOT_DIR/home-assistant" "$BUILD_DIR/"

echo "🗜️ Creating archive..."
tar -czf "$OUTPUT" -C "$BUILD_DIR" .

echo "✅ Package created: $OUTPUT"
