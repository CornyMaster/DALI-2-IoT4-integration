#!/bin/bash
# Installation script for Lunatone DALI-2 IoT4 Home Assistant Integration

set -e

echo "============================================================"
echo "Lunatone DALI-2 IoT4 Integration Installer"
echo "============================================================"
echo

# Check if Home Assistant config directory is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <home_assistant_config_directory>"
    echo "Example: $0 /path/to/homeassistant/config"
    echo
    echo "Or set the HA_CONFIG environment variable:"
    echo "  export HA_CONFIG=/path/to/homeassistant/config"
    echo "  $0"
    exit 1
fi

HA_CONFIG="$1"

# Validate Home Assistant config directory
if [ ! -d "$HA_CONFIG" ]; then
    echo "✗ Home Assistant config directory not found: $HA_CONFIG"
    exit 1
fi

echo "✓ Home Assistant config directory: $HA_CONFIG"
echo

# Check if configuration.yaml exists
if [ ! -f "$HA_CONFIG/configuration.yaml" ]; then
    echo "✗ configuration.yaml not found in $HA_CONFIG"
    exit 1
fi

echo "✓ Found configuration.yaml"
echo

# Create custom_components directory if it doesn't exist
CUSTOM_DIR="$HA_CONFIG/custom_components"
if [ ! -d "$CUSTOM_DIR" ]; then
    echo "Creating custom_components directory..."
    mkdir -p "$CUSTOM_DIR"
fi

echo "✓ custom_components directory ready"
echo

# Copy integration files
echo "Installing Lunatone DALI-2 IoT4 integration..."
INTEGRATION_DIR="$CUSTOM_DIR/lunatone_dali2_iot4"

if [ -d "$INTEGRATION_DIR" ]; then
    echo "⚠ Integration already exists at $INTEGRATION_DIR"
    read -p "Do you want to overwrite it? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
    rm -rf "$INTEGRATION_DIR"
fi

# Copy files
cp -r "$(dirname "$0")/custom_components/lunatone_dali2_iot4" "$INTEGRATION_DIR"

echo "✓ Integration files copied to $INTEGRATION_DIR"
echo

# Validate installation
echo "Validating installation..."
if [ ! -f "$INTEGRATION_DIR/manifest.json" ]; then
    echo "✗ Installation failed: manifest.json not found"
    exit 1
fi

echo "✓ Installation validated"
echo

# Success message
echo "============================================================"
echo "✓ Installation Complete!"
echo "============================================================"
echo
echo "Next steps:"
echo "  1. Restart Home Assistant"
echo "  2. Go to Settings → Devices & Services"
echo "  3. Click '+ Add Integration'"
echo "  4. Search for 'Lunatone DALI-2 IoT4'"
echo "  5. Enter your device details:"
echo "     - IP Address: <gateway-ip>"
echo "     - Port: 80"
echo
echo "For debug logging, add to configuration.yaml:"
echo "  logger:"
echo "    logs:"
echo "      custom_components.lunatone_dali2_iot4: debug"
echo
echo "Integration installed at: $INTEGRATION_DIR"
echo
