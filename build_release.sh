#!/bin/bash
# Build script for Time Tracker Companion release
# Creates a self-contained .dmg with bundled Flask server

set -e

echo "=== Time Tracker Companion Release Build ==="

# Configuration
APP_NAME="TimeTrackerCompanion"
DMG_NAME="TimeTrackerCompanion"
BUILD_DIR="./release_build"
DIST_DIR="./dist"

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf "$BUILD_DIR"
rm -rf "$DIST_DIR"
mkdir -p "$BUILD_DIR"

# Step 1: Build the Flask server with PyInstaller
echo ""
echo "=== Step 1: Building Flask server with PyInstaller ==="
pixi run pyinstaller --clean --noconfirm time_tracker_server.spec

# Verify server was built
if [ ! -f "dist/TimeTrackerServer" ]; then
    echo "ERROR: PyInstaller failed to create TimeTrackerServer"
    exit 1
fi
echo "Flask server built successfully: dist/TimeTrackerServer"

# Step 2: Build the macOS app
echo ""
echo "=== Step 2: Building macOS app ==="
xcodebuild -project TimeTrackerCompanion/TimeTrackerCompanion.xcodeproj \
    -scheme TimeTrackerCompanion \
    -configuration Release \
    -derivedDataPath "$BUILD_DIR/xcode" \
    build

# Find the built app
APP_PATH=$(find "$BUILD_DIR/xcode" -name "*.app" -type d | head -1)
if [ -z "$APP_PATH" ]; then
    echo "ERROR: Could not find built app"
    exit 1
fi
echo "macOS app built: $APP_PATH"

# Step 3: Copy the bundled server into the app
echo ""
echo "=== Step 3: Bundling Flask server into app ==="
RESOURCES_DIR="$APP_PATH/Contents/Resources"
mkdir -p "$RESOURCES_DIR"
cp "dist/TimeTrackerServer" "$RESOURCES_DIR/"
chmod +x "$RESOURCES_DIR/TimeTrackerServer"
echo "Server bundled into: $RESOURCES_DIR/TimeTrackerServer"

# Step 4: Copy app to build directory
echo ""
echo "=== Step 4: Preparing for DMG ==="
mkdir -p "$DIST_DIR"
cp -R "$APP_PATH" "$DIST_DIR/"

# Step 5: Create DMG
echo ""
echo "=== Step 5: Creating DMG ==="
DMG_PATH="$DIST_DIR/${DMG_NAME}.dmg"

# Remove old DMG if exists
rm -f "$DMG_PATH"

# Create DMG directly from the app folder
hdiutil create -volname "$DMG_NAME" -srcfolder "$DIST_DIR/$APP_NAME.app" -ov -format UDZO "$DMG_PATH"

echo ""
echo "=== Build Complete ==="
echo "DMG created: $DMG_PATH"
echo ""
echo "To install:"
echo "1. Open $DMG_PATH"
echo "2. Drag TimeTrackerCompanion to Applications"
echo "3. Launch from Applications"

# Show file sizes
echo ""
echo "=== File Sizes ==="
ls -lh "dist/TimeTrackerServer"
ls -lh "$DMG_PATH"
