#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_PATH="$ROOT_DIR/dist/OllamaMonitor.app"
APP_BINARY="${OLLAMA_MONITOR_BINARY:-}"

if [ -z "$APP_BINARY" ]; then
	mkdir -p "$ROOT_DIR/.build/swiftpm-module-cache"
	export SWIFTPM_MODULECACHE_OVERRIDE="$ROOT_DIR/.build/swiftpm-module-cache"
	swift build --package-path "$ROOT_DIR" --configuration release
	BIN_DIR="$(swift build --package-path "$ROOT_DIR" --configuration release --show-bin-path)"
	APP_BINARY="$BIN_DIR/OllamaMonitor"
fi

mkdir -p "$APP_PATH/Contents/MacOS" "$APP_PATH/Contents/Resources"
install -m 755 "$APP_BINARY" "$APP_PATH/Contents/MacOS/OllamaMonitor"
install -m 644 "$ROOT_DIR/icon.icns" "$APP_PATH/Contents/Resources/icon.icns"

cat > "$APP_PATH/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleName</key>
	<string>Ollama Monitor</string>
	<key>CFBundleDisplayName</key>
	<string>Ollama Monitor + GPU</string>
	<key>CFBundleIdentifier</key>
	<string>com.mao.ollamamonitor</string>
	<key>CFBundleExecutable</key>
	<string>OllamaMonitor</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleIconFile</key>
	<string>icon.icns</string>
	<key>CFBundleVersion</key>
	<string>1</string>
	<key>CFBundleShortVersionString</key>
	<string>1.0.0</string>
	<key>LSMinimumSystemVersion</key>
	<string>26.0</string>
	<key>LSApplicationCategoryType</key>
	<string>public.app-category.utilities</string>
	<key>NSHighResolutionCapable</key>
	<true/>
	<key>NSAppTransportSecurity</key>
	<dict>
		<key>NSAllowsLocalNetworking</key>
		<true/>
	</dict>
</dict>
</plist>
PLIST

plutil -lint "$APP_PATH/Contents/Info.plist"
echo "Built $APP_PATH"
