import tkinter as tk
from tkinter import scrolledtext
import urllib.request
import json
import threading
import time
import sys
import os
import traceback
from datetime import datetime

# --- STABLE LOGGING TO /tmp/ ---
# /tmp/ is always writable on macOS even inside a restricted terminal/sandbox
class Logger:
    def __init__(self, filename="ollama_monitor_log.txt"):
        self.terminal = sys.stdout
        self.log_path = os.path.join("/tmp", filename)
        try:
            self.log = open(self.log_path, "a", encoding="utf-8")
            self.log.write(f"\n--- App Started: {datetime.now()} ---\n")
            # Always print to terminal too
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
        self.root.title("Ollama Monitor (Stable)")
        self.root.geometry("900x650")
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
            # Explicitly force update to ensure painter works
            self.root.update_idletasks()
            self.root.update()
        except Exception as e:
            print(f"UI Error: {e}")
            traceback.print_exc()

    def create_widgets(self):
        # Header using standard tk.Frame (no ttk)
        header_frame = tk.Frame(self.root, bg="#121212")
        header_frame.pack(fill="x", padx=30, pady=(30, 10))
        
        self.title_label = tk.Label(header_frame, text="OLLAMA MONITOR", 
                                    fg="#BB86FC", bg="#121212", font=("Helvetica", 18, "bold"))
        self.title_label.pack(side="left")
        
        self.time_label = tk.Label(header_frame, text="Initializing...", 
                                   fg="#888888", bg="#121212", font=("Helvetica", 10))
        self.time_label.pack(side="right", pady=10)

        # Main Container
        main_container = tk.Frame(self.root, bg="#121212")
        main_container.pack(fill="both", expand=True, padx=30, pady=10)

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
        
        tk.Label(right_panel, text="GEMMA 4 INSIGHTS", fg="#03DAC6", bg="#121212", 
                 font=("Helvetica", 12, "bold")).pack(anchor="w", pady=(0, 10))
        
        self.ai_output = scrolledtext.ScrolledText(
            right_panel, bg="#1A1A1A", fg="#BB86FC", insertbackground="white",
            font=("Helvetica", 12, "italic"), borderwidth=0, highlightthickness=1, highlightbackground="#333333", wrap="word"
        )
        self.ai_output.pack(fill="both", expand=True)
        self.ai_output.insert("1.0", "Waiting for AI analysis...")

        self.status_bar = tk.Label(self.root, text="System: Ready", 
                                   fg="#888888", bg="#121212", font=("Helvetica", 10))
        self.status_bar.pack(side="bottom", fill="x", padx=30, pady=20)

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
            prompt = f"Summarize status: {ps_text}"
            payload = json.dumps({"model": self.model_name, "prompt": prompt, "stream": False}).encode('utf-8')
            req = urllib.request.Request(f"{self.api_base}/generate", data=payload, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=15) as response:
                result = json.loads(response.read().decode())
                return result.get("response", "").strip()
        except:
            return "Ollama offline."

    def update_loop(self):
        while self.running:
            try:
                if not self.root.winfo_exists(): break
                now = datetime.now().strftime("%H:%M:%S")
                self.root.after(0, lambda t=now: self.time_label.config(text=f"Last Sync: {t}"))

                ps_text = self.get_ps_data()
                self.root.after(0, self.refresh_ps, ps_text)

                current_time = time.time() * 1000
                if current_time - self.last_ai_time > self.ai_interval:
                    insight = self.get_ai_insight(ps_text)
                    self.root.after(0, self.refresh_ai, insight)
                    self.last_ai_time = current_time

                time.sleep(self.update_interval / 1000)
            except Exception as e:
                print(f"Loop error: {e}")
                time.sleep(2)

    def refresh_ps(self, text):
        if self.root.winfo_exists():
            self.ps_output.delete("1.0", tk.END)
            self.ps_output.insert(tk.END, text)

    def refresh_ai(self, text):
        if self.root.winfo_exists():
            self.ai_output.delete("1.0", tk.END)
            self.ai_output.insert(tk.END, f"SYSTEM ANALYSIS:\n\n\"{text}\"")

if __name__ == "__main__":
    root = tk.Tk()
    app = OllamaMonitorApp(root)
    
    def on_closing():
        app.running = False
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    update_thread = threading.Thread(target=app.update_loop, daemon=True)
    update_thread.start()
    
    root.mainloop()
