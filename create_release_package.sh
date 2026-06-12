#!/bin/bash
# Create installation package for manual HassOS deployment
set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

# Version comes from the integration manifest (single source of truth)
VERSION=$(sed -n 's/.*"version": *"v\{0,1\}\([^"]*\)".*/\1/p' \
    "$REPO_ROOT/custom_components/lunatone_dali2_iot4/manifest.json")

echo "Creating release package for version ${VERSION}..."

WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT
cd "$WORK_DIR"

cp -r "$REPO_ROOT/custom_components/lunatone_dali2_iot4" .

# Remove Python cache files
find lunatone_dali2_iot4 -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find lunatone_dali2_iot4 -type f -name "*.pyc" -delete 2>/dev/null || true

tar -czf "lunatone_dali2_iot4_v${VERSION}.tar.gz" lunatone_dali2_iot4/
mv "lunatone_dali2_iot4_v${VERSION}.tar.gz" "$REPO_ROOT/"

echo "✅ Package created: $REPO_ROOT/lunatone_dali2_iot4_v${VERSION}.tar.gz"
echo ""
echo "To install on Home Assistant:"
echo "1. Copy the tar.gz file to your Home Assistant device"
echo "2. Extract to /config/custom_components/"
echo "   tar -xzf lunatone_dali2_iot4_v${VERSION}.tar.gz -C /config/custom_components/"
echo "3. Restart Home Assistant"
echo ""
echo "See INSTALL.md for detailed instructions"
