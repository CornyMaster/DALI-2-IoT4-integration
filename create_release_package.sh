#!/bin/bash
# Create installation package for HassOS deployment

VERSION="0.1.4-beta-3"

echo "Creating release package for version ${VERSION}..."

# Create temporary directory
mkdir -p /tmp/dali_lunatone_release
cd /tmp/dali_lunatone_release

# Copy integration files
cp -r ~/development/dali-lunatone-integration/custom_components/dali_lunatone .

# Remove Python cache files
find dali_lunatone -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find dali_lunatone -type f -name "*.pyc" -delete 2>/dev/null || true

# Create tar.gz file (preferred for HACS and manual installation)
tar -czf dali_lunatone_v${VERSION}.tar.gz dali_lunatone/

# Move to development directory
mv dali_lunatone_v${VERSION}.tar.gz ~/development/dali-lunatone-integration/

# Cleanup
cd ~
rm -rf /tmp/dali_lunatone_release

echo "✅ Package created: ~/development/dali-lunatone-integration/dali_lunatone_v${VERSION}.tar.gz"
echo ""
echo "To install on Home Assistant:"
echo "1. Copy tar.gz file to your Home Assistant device"
echo "2. Extract to /config/custom_components/"
echo "   tar -xzf dali_lunatone_v${VERSION}.tar.gz -C /config/custom_components/"
echo "3. Restart Home Assistant"
echo ""
echo "See INSTALL.md for detailed instructions"

