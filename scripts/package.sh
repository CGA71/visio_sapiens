#!/bin/sh

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
