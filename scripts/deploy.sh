#!/bin/sh

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
