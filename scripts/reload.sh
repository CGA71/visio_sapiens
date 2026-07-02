#!/bin/sh

set -e

NAMESPACE="home-assistant"
POD="home-assistant-0"
CONTAINER="home-assistant"

echo "🔄 Reloading Home Assistant..."

kubectl -n $NAMESPACE exec $POD -c $CONTAINER -- ha core reload

echo "✅ Reload done"
