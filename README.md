# Ollama Monitor + GPU

Ollama Monitor is a macOS desktop application designed to provide real-time monitoring of your locally running [Ollama](https://ollama.com/) models and Apple Silicon GPU utilization. Additionally, it leverages an Ollama AI model itself to periodically generate and display insights summarizing the current state of your running models.

## ✨ Features

- **Live Models Monitoring**
  Displays real-time information about actively running/loaded Ollama models, including their names, IDs, sizes, and operational status.
- **GPU Meter**
  Visually tracks your Apple Silicon GPU utilization with a progress bar and percentage value, retrieved via the `ioreg` command.
- **AI Insights**
  Automatically sends the current system status (e.g., list of running models) to an AI model (default: `gemma4:latest`) and displays an AI-generated summary of your environment.
- **Customizable Window**
  - **Always on Top**: A toggle to pin the monitor window above other applications.
  - **Transparency**: An adjustable slider to set the window's alpha (transparency) level.
- **Persistent State**
  Automatically saves your window layout preferences (geometry, 'Always on Top' status, and transparency) to `~/.ollama_monitor_config.json` and restores them on your next launch.

## 💻 Requirements

- **OS**: macOS (Apple Silicon highly recommended, as the application uses `ioreg` to fetch GPU data).
- **Environment**: Python 3.x
- **Dependencies**: [Ollama](https://ollama.com) must be installed and running in the background (`http://localhost:11434`).
- **Models**: You need an active model for the AI Insights feature. The default is `gemma4:latest`, but this can be changed in the source code via `self.model_name`.

## 🚀 Installation & Usage

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/ollama-monitor.git
cd ollama-monitor

# 2. Run the application
python3 ollama_monitor.py
```

*Note: The script relies strictly on Python standard libraries (`tkinter`, `urllib`, `json`, `threading`, `subprocess`, etc.), so no additional `pip install` commands are typically required.*

## 📦 Packaging (Creating a macOS .app)

You can bundle this script into a standalone macOS `.app` using [PyInstaller](https://pyinstaller.org/) and the provided `OllamaMonitor.spec` file.

```bash
# Install PyInstaller
pip install pyinstaller

# Build the application
pyinstaller OllamaMonitor.spec
```
Once the build is complete, you will find `OllamaMonitor.app` inside the `dist/` directory.

## ⚙️ Configuration & Customization

Feel free to tweak the following variables located in `ollama_monitor.py` to match your preferences:

- `self.model_name = "gemma4:latest"` : The model used for AI Insights generation.
- `self.update_interval = 1000` : The UI update frequency in milliseconds.
- `self.ai_interval = 15000` : The frequency of generating new AI Insights in milliseconds.

## 📄 Logs
For debugging and troubleshooting purposes, run logs are automatically saved to `/tmp/ollama_monitor_log.txt`.

## 📝 License
This project is licensed under the MIT License.
