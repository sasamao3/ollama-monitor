import tkinter as tk
from tkinter import scrolledtext
import urllib.request
import json
import threading
import time
import sys
import os
import traceback
import subprocess
import re
from datetime import datetime

# --- STABLE LOGGING TO /tmp/ ---
class Logger:
    def __init__(self, filename="ollama_monitor_log.txt"):
        self.terminal = sys.stdout
        self.log_path = os.path.join("/tmp", filename)
        try:
            self.log = open(self.log_path, "a", encoding="utf-8")
            self.log.write(f"\n--- App Started: {datetime.now()} ---\n")
            self.terminal.write(f"Logging to {self.log_path}\n")
        except:
            pass

    def write(self, message):
        self.terminal.write(message)
        try:
            self.log.write(message)
            self.log.flush()
        except:
            pass

    def flush(self):
        self.terminal.flush()

if getattr(sys, 'frozen', False):
    logger = Logger()
    sys.stdout = logger
    sys.stderr = logger

class OllamaMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ollama Monitor + GPU")
        
        # Persistence: Default geometry or load from config
        self.config_path = os.path.expanduser("~/.ollama_monitor_config.json")
        self.initial_config = self.load_config()
        self.root.geometry(self.initial_config.get("geometry", "900x700"))
        
        self.root.configure(bg="#121212")

        # Configuration
        self.update_interval = 1000 
        self.ai_interval = 15000    
        self.last_ai_time = 0
        self.model_name = "gemma4:latest"
        self.api_base = "http://localhost:11434/api"
        self.running = True

        try:
            self.create_widgets()
            
            # Apply initial settings to widgets
            self.topmost_var.set(self.initial_config.get("topmost", False))
            self.alpha_var.set(self.initial_config.get("alpha", 1.0))
            self.toggle_topmost()
            self.set_alpha(self.alpha_var.get())

            self.root.update_idletasks()
            self.root.update()
        except Exception as e:
            print(f"UI Error: {e}")
            traceback.print_exc()

    def create_widgets(self):
        # Header
        header_frame = tk.Frame(self.root, bg="#121212")
        header_frame.pack(fill="x", padx=30, pady=(30, 10))
        
        self.title_label = tk.Label(header_frame, text="OLLAMA MONITOR", 
                                    fg="#BB86FC", bg="#121212", font=("Helvetica", 18, "bold"))
        self.title_label.pack(side="left")
        
        # Window Settings Section
        settings_frame = tk.Frame(header_frame, bg="#121212")
        settings_frame.pack(side="right", padx=(0, 20))
        
        self.topmost_var = tk.BooleanVar(value=False)
        self.topmost_check = tk.Checkbutton(
            settings_frame, text="Always on Top", variable=self.topmost_var,
            command=self.toggle_topmost, bg="#121212", fg="#BB86FC", 
            selectcolor="#333333"
        )
        self.topmost_check.pack(side="top", anchor="e")

        self.alpha_var = tk.DoubleVar(value=1.0)
        self.alpha_scale = tk.Scale(
            settings_frame, from_=0.2, to=1.0, resolution=0.05, orient="horizontal",
            variable=self.alpha_var, command=self.set_alpha,
            bg="#121212", fg="#03DAC6", highlightthickness=0, length=100, showvalue=0
        )
        self.alpha_scale.pack(side="top", anchor="e")

        # GPU Meter Section (Right of Title)
        gpu_frame = tk.Frame(header_frame, bg="#121212")
        gpu_frame.pack(side="right")

        self.gpu_label = tk.Label(gpu_frame, text="GPU: 0%", fg="#03DAC6", bg="#121212", font=("Helvetica", 10, "bold"))
        self.gpu_label.pack(side="top", anchor="e")

        self.gpu_canvas = tk.Canvas(gpu_frame, width=150, height=8, bg="#333333", highlightthickness=0)
        self.gpu_canvas.pack(side="top", pady=2)
        self.gpu_bar = self.gpu_canvas.create_rectangle(0, 0, 0, 8, fill="#03DAC6", outline="")

        self.time_label = tk.Label(self.root, text="Initializing...", 
                                   fg="#888888", bg="#121212", font=("Helvetica", 9))
        self.time_label.place(x=30, y=70) # Fixed position for sync time

        # Main Container
        main_container = tk.Frame(self.root, bg="#121212")
        main_container.pack(fill="both", expand=True, padx=30, pady=(20, 10))

        # Left Panel
        left_panel = tk.Frame(main_container, bg="#121212")
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 15))
        
        tk.Label(left_panel, text="LIVE MODELS", fg="#03DAC6", bg="#121212", 
                 font=("Helvetica", 12, "bold")).pack(anchor="w", pady=(0, 10))
        
        self.ps_output = scrolledtext.ScrolledText(
            left_panel, bg="#1A1A1A", fg="#E0E0E0", insertbackground="white",
            font=("Courier New", 12), borderwidth=0, highlightthickness=1, highlightbackground="#333333"
        )
        self.ps_output.pack(fill="both", expand=True)

        # Right Panel
        right_panel = tk.Frame(main_container, bg="#121212")
        right_panel.pack(side="right", fill="both", expand=True, padx=(15, 0))
        
        tk.Label(right_panel, text="AI INSIGHTS", fg="#03DAC6", bg="#121212", 
                 font=("Helvetica", 12, "bold")).pack(anchor="w", pady=(0, 10))
        
        self.ai_output = scrolledtext.ScrolledText(
            right_panel, bg="#1A1A1A", fg="#BB86FC", insertbackground="white",
            font=("Helvetica", 12, "italic"), borderwidth=0, highlightthickness=1, highlightbackground="#333333", wrap="word"
        )
        self.ai_output.pack(fill="both", expand=True)

        self.status_bar = tk.Label(self.root, text="System: Ready", 
                                   fg="#888888", bg="#121212", font=("Helvetica", 10))
        self.status_bar.pack(side="bottom", fill="x", padx=30, pady=20)

    def toggle_topmost(self):
        self.root.attributes("-topmost", self.topmost_var.get())

    def set_alpha(self, value):
        self.root.attributes("-alpha", float(value))

    def get_gpu_usage(self):
        try:
            # Use ioreg to get Apple Silicon GPU utilization
            cmd = "ioreg -rw0 -c IOAccelerator | grep -i PerformanceStatistics"
            output = subprocess.check_output(cmd, shell=True).decode()
            
            # Find "Device Utilization %" = 20
            match = re.search(r'"Device Utilization %"=(\d+)', output)
            if match:
                return int(match.group(1))
            return 0
        except:
            return 0

    def get_ps_data(self):
        try:
            req = urllib.request.Request(f"{self.api_base}/ps")
            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode())
                models = data.get("models", [])
                if not models: return "No models currently running."
                
                output = f"{'NAME':<25} {'ID':<15} {'SIZE':<10} {'STATUS':<15}\n"
                output += "=" * 70 + "\n"
                for m in models:
                    name = m.get('name', 'N/A')
                    mid = m.get('digest', 'N/A')[:12]
                    size = f"{m.get('size', 0) / (1024**3):.1f} GB"
                    output += f"{name:<25} {mid:<15} {size:<10} Running\n"
                return output
        except Exception as e:
            return f"Error: {e}"

    def get_ai_insight(self, ps_text):
        try:
            prompt = f"Summarize current running AI status: {ps_text}"
            payload = json.dumps({"model": self.model_name, "prompt": prompt, "stream": False}).encode('utf-8')
            req = urllib.request.Request(f"{self.api_base}/generate", data=payload, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=15) as response:
                result = json.loads(response.read().decode())
                return result.get("response", "").strip()
        except:
            return "Ollama offline or model missing."

    def update_loop(self):
        while self.running:
            try:
                if not self.root.winfo_exists(): break
                now = datetime.now().strftime("%H:%M:%S")
                self.root.after(0, lambda t=now: self.time_label.config(text=f"Last Sync: {t}"))

                # Update GPU Meter
                gpu_load = self.get_gpu_usage()
                self.root.after(0, self.refresh_gpu, gpu_load)

                # Update Process List
                ps_text = self.get_ps_data()
                self.root.after(0, self.refresh_ps, ps_text)

                # Update AI Insight (less frequent)
                current_time = time.time() * 1000
                if current_time - self.last_ai_time > self.ai_interval:
                    insight = self.get_ai_insight(ps_text)
                    self.root.after(0, self.refresh_ai, insight)
                    self.last_ai_time = current_time

                time.sleep(self.update_interval / 1000)
            except Exception as e:
                print(f"Loop error: {e}")
                time.sleep(2)

    def refresh_gpu(self, load):
        if not self.root.winfo_exists(): return
        
        # Update Text
        self.gpu_label.config(text=f"GPU: {load}%")
        
        # Update Bar Width
        width = (load / 100.0) * 150
        self.gpu_canvas.coords(self.gpu_bar, 0, 0, width, 8)
        
        # Update Bar Color (Green -> Yellow -> Red)
        if load < 30: color = "#03DAC6" # Teal
        elif load < 70: color = "#FFB300" # Amber
        else: color = "#CF6679" # Pinkish Red
        self.gpu_canvas.itemconfig(self.gpu_bar, fill=color)

    def refresh_ps(self, text):
        if self.root.winfo_exists():
            self.ps_output.delete("1.0", tk.END)
            self.ps_output.insert(tk.END, text)

    def refresh_ai(self, text):
        if self.root.winfo_exists():
            self.ai_output.delete("1.0", tk.END)
            self.ai_output.insert(tk.END, f"SYSTEM ANALYSIS:\n\n\"{text}\"")

    def load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as f:
                    return json.load(f)
        except:
            pass
        return {}

    def save_config(self):
        try:
            self.root.update_idletasks() # Ensure geometry is current
            current_geometry = self.root.geometry()
            config = {
                "geometry": current_geometry,
                "topmost": self.topmost_var.get(),
                "alpha": self.alpha_var.get()
            }
            with open(self.config_path, "w") as f:
                json.dump(config, f)
            print(f"Config saved: {config}")
        except Exception as e:
            print(f"Failed to save config: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = OllamaMonitorApp(root)
    
    def on_closing():
        print("Closing application...")
        app.save_config()
        app.running = False
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Mac specific: Handle Command+Q and Quit menu
    try:
        root.createcommand('tk::mac::Quit', on_closing)
    except:
        pass
    
    update_thread = threading.Thread(target=app.update_loop, daemon=True)
    update_thread.start()
    
    root.mainloop()
