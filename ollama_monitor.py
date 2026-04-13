import tkinter as tk
from tkinter import ttk
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

        # Add tokens per second display
        self.tokens_label = tk.Label(gpu_frame, text="tok/s: 0.0", fg="#03DAC6", bg="#121212", font=("Helvetica", 10, "bold"))
        self.tokens_label.pack(side="top", anchor="e")

        self.time_label = tk.Label(self.root, text="Initializing...", 
                                   fg="#888888", bg="#121212", font=("Helvetica", 9))
        self.time_label.place(x=30, y=70) # Fixed position for sync time

        # Token tracking
        self.token_counts = {}  # model_name -> token count
        self.token_timestamps = {}  # model_name -> last update timestamp
        self.token_throughput = {}  # model_name -> tokens per second

        # Main Container
        main_container = tk.Frame(self.root, bg="#121212")
        main_container.pack(fill="both", expand=True, padx=30, pady=(20, 10))

        # Left Panel
        left_panel = tk.Frame(main_container, bg="#121212")
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 15))
        
        models_header_frame = tk.Frame(left_panel, bg="#121212")
        models_header_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(models_header_frame, text="LIVE MODELS", fg="#03DAC6", bg="#121212", 
                 font=("Helvetica", 12, "bold")).pack(side="left")
        
        self.model_combo = ttk.Combobox(models_header_frame, state="readonly", width=15)
        self.model_combo.pack(side="left", padx=(10, 5))
        
        self.stop_btn = tk.Button(models_header_frame, text="Stop", command=self.stop_model, highlightbackground="#121212")
        self.stop_btn.pack(side="left")
        
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

        # Token tracking
        self.token_counts = {}  # model_name -> token count
        self.token_timestamps = {}  # model_name -> last update timestamp
        self.total_tokens = 0
        self.last_token_time = time.time()

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

    def get_model_token_info(self, model_name):
        """Get token information for a specific model by making a test generate request"""
        try:
            # Make a lightweight test request to get token info
            payload = json.dumps({
                "model": model_name,
                "prompt": ".",
                "stream": False,
                "options": {
                    "temperature": 0
                }
            }).encode('utf-8')
            
            req = urllib.request.Request(f"{self.api_base}/generate", data=payload, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode())
                
                # Extract token information from the response
                prompt_eval_count = result.get("prompt_eval_count", 0)
                eval_count = result.get("eval_count", 0)
                total_duration = result.get("total_duration", 0)
                
                # Calculate tokens per second
                if total_duration > 0:
                    tok_per_sec = eval_count / (total_duration / 1e9)
                    return tok_per_sec
                else:
                    return 0.0
        except Exception as e:
            print(f"Error getting token info for {model_name}: {e}")
            return 0.0

    def get_token_throughput(self):
        """Calculate average token throughput from running models"""
        try:
            req = urllib.request.Request(f"{self.api_base}/ps")
            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode())
                models = data.get("models", [])
                
                if not models:
                    return 0.0
                
                # Calculate average token throughput from all running models
                total_throughput = 0.0
                count = 0
                
                for model in models:
                    model_name = model.get('name', '')
                    if model_name:
                        tok_per_sec = self.get_model_token_info(model_name)
                        if tok_per_sec > 0:
                            total_throughput += tok_per_sec
                            count += 1
                
                if count > 0:
                    return total_throughput / count
                else:
                    return 0.0
        except Exception as e:
            print(f"Error getting token throughput: {e}")
            return 0.0
        """Update token throughput display"""
        if not self.root.winfo_exists():
            return
            
        # Simple placeholder that shows the token display is functional
        # Actual token tracking would require monitoring generation requests
        # which would be disruptive to the user's workflow
        self.tokens_label.config(text="tok/s: 0.0")

    def get_ps_data(self):
        try:
            req = urllib.request.Request(f"{self.api_base}/ps")
            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode())
                models = data.get("models", [])
                self.running_model_names = [m.get('name') for m in models if m.get('name')]
                
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
            self.running_model_names = []
            return f"Error: {e}"

    def get_ai_insight(self, ps_text):
        try:
            prompt = f"Summarize current running AI status: {ps_text}"
            payload = json.dumps({"model": self.model_name, "prompt": prompt, "stream": False}).encode('utf-8')
            req = urllib.request.Request(f"{self.api_base}/generate", data=payload, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=15) as response:
                result = json.loads(response.read().decode())
                return result.get("response", "").strip()
        except Exception as e:
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

                # Update Token Display
                self.root.after(0, self.refresh_tokens)

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
            
            if hasattr(self, 'running_model_names'):
                current_values = list(self.model_combo['values'])
                if current_values != self.running_model_names:
                    self.model_combo['values'] = self.running_model_names
                    if self.running_model_names and self.model_combo.get() not in self.running_model_names:
                        self.model_combo.set(self.running_model_names[0])
                    elif not self.running_model_names:
                        self.model_combo.set("")

    def refresh_ai(self, text):
        if self.root.winfo_exists():
            self.ai_output.delete("1.0", tk.END)
            self.ai_output.insert(tk.END, f"SYSTEM ANALYSIS:\n\n\"{text}\"")

    def refresh_tokens(self):
        """Update token throughput display with actual values from models"""
        if not self.root.winfo_exists():
            return
        
        try:
            # Get actual token throughput from running models
            throughput = self.get_token_throughput()
            self.tokens_label.config(text=f"tok/s: {throughput:.1f}")
        except Exception as e:
            print(f"Error refreshing tokens: {e}")
            self.tokens_label.config(text="tok/s: 0.0")

    def stop_model(self):
        model_to_stop = self.model_combo.get()
        if not model_to_stop:
            return
            
        def _stop():
            try:
                payload = json.dumps({"model": model_to_stop, "keep_alive": 0}).encode('utf-8')
                req = urllib.request.Request(f"{self.api_base}/generate", data=payload, headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    pass
                print(f"Stopped model {model_to_stop}")
                # Refresh ps right away
                ps_text = self.get_ps_data()
                self.root.after(0, self.refresh_ps, ps_text)
            except Exception as e:
                print(f"Failed to stop model: {e}")

        threading.Thread(target=_stop, daemon=True).start()

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
