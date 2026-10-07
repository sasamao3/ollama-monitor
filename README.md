# Ollama Monitor + GPU

A native macOS app for monitoring models loaded in Ollama and LM Studio, plus Apple Silicon GPU utilization.

## Features

- Lists loaded Ollama and LM Studio models with model name, identifier, size, and type.
- Reads GPU utilization and Apple GPU-driver memory counters from `ioreg` on Apple Silicon Macs.
- Sends an unload request for a selected Ollama model.
- Stops a selected Bionic model by unloading it from memory.
- Supports an always-on-top window and adjustable window opacity.
- Reads the existing `~/.ollama_monitor_config.json` settings and restores the saved window geometry.

## Requirements

- macOS 26 or later
- Xcode 27 or the matching Command Line Tools with Swift 6.4 or later
- Ollama running locally at `http://localhost:11434`
- Bionic's Local Model API server enabled in `Settings → Local Model API`

## Build

```bash
./scripts/build_app.sh
open dist/OllamaMonitor.app
```

The script builds a native SwiftUI executable and places it in `dist/OllamaMonitor.app`. You can also open `Package.swift` in Xcode to edit and run the app.

## Configuration

The app keeps the existing `~/.ollama_monitor_config.json` location for the always-on-top and opacity preferences. It imports the previous Tk window geometry on first launch; subsequent window placement is saved by macOS under the app's native window autosave name.

Ollama and Bionic are queried once per second. Bionic models are filtered to loaded instances from the LM Studio runtime's [`GET /api/v1/models`](https://lmstudio.ai/docs/developer/rest/list) endpoint. The app reads the configured port from `lms server status`; if the CLI is unavailable, it checks ports `1234` and `8000`. Turn on Bionic's Local Model API in `Settings → Local Model API` for model monitoring.

The GPU memory meter shows `In use system memory` relative to `Alloc system memory` from `IOAccelerator`. On Apple silicon this is shared system memory, not dedicated VRAM.

## Legacy Python app

`ollama_monitor.py` and `setup.py` are retained as the previous Tkinter implementation. The native app is built from `Sources/OllamaMonitor`.

## License

MIT
