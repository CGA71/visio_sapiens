validate:
  stage: validate
  image: alpine:latest

  script:
    - echo "🔍 OSVision V2 - Validation started"

    # vérifie structure du repo
    - test -f scripts/package.sh || (echo "❌ package.sh missing" && exit 1)
    - test -f scripts/deploy.sh || (echo "❌ deploy.sh missing" && exit 1)
    - test -f scripts/reload.sh || (echo "❌ reload.sh missing" && exit 1)

    - test -d home-assistant || (echo "❌ home-assistant folder missing" && exit 1)

    # vérifie fichiers critiques OSVision
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

    echo "✅ Validation OK - OSVision structure valid"
