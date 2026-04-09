import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from typing import Dict, Any

class SuspensionConfigApp:
    """
    バイクのサスペンション設定を管理するためのTkinter GUIアプリケーション。
    """
    CONFIG_FILE = "suspension_settings.json"

    def __init__(self, master):
        self.master = master
        master.title("Suspension Settings Manager")
        master.geometry("1000x700")

        # スタイルの設定
        style = ttk.Style()
        style.configure("Treeview.Heading", font=('Helvetica', 10, 'bold'))
        style.configure("TLabel", font=('Helvetica', 10))

        self.settings: Dict[str, Any] = self.load_data()
        self.current_item_id = None  # Treeviewで選択されている内部ID

        # メインコンテナ
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(pady=10, padx=10, expand=True, fill="both")

        # タブ1: 設定一覧
        self.list_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.list_frame, text="設定一覧 / View Settings")
        self._setup_list_view(self.list_frame)

        # タブ2: 設定入力/編集
        self.form_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.form_frame, text="設定入力・編集 / Edit Form")
        self._setup_form_view(self.form_frame)

        # 初期表示
        self.refresh_list()
        self.clear_form()

    def load_data(self) -> Dict[str, Any]:
        """JSONファイルから設定データを読み込む。"""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # リストで保存されていても辞書に変換して扱う
                    if isinstance(data, list):
                        return {f"ID_{i}": val for i, val in enumerate(data)}
                    return data
            except (json.JSONDecodeError, Exception):
                messagebox.showerror("Error", "データの読み込みに失敗しました。")
                return {}
        return {}

    def save_data(self):
        """データをJSONファイルに書き出す。"""
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Error", f"保存失敗: {e}")

    def _setup_list_view(self, frame):
        """一覧表示画面の構築。"""
        # Treeview
        columns = ("Model", "F_Pre", "F_Reb", "F_Com", "R_Pre", "R_RebHi", "R_RebLo", "R_ComHi", "R_ComLo")
        self.tree = ttk.Treeview(frame, columns=columns, show='headings')
        
        headers = {
            "Model": "モデル名", "F_Pre": "F Pre", "F_Reb": "F Reb", "F_Com": "F Com",
            "R_Pre": "R Pre", "R_RebHi": "R Reb Hi", "R_RebLo": "R Reb Lo",
            "R_ComHi": "R Com Hi", "R_ComLo": "R Com Lo"
        }
        for col, text in headers.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=80, anchor='center')
        self.tree.column("Model", width=150, anchor='w')

        self.tree.pack(padx=10, pady=10, fill="both", expand=True)

        # 操作ボタン
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="新規追加 (New)", command=self.prepare_new).pack(side=tk.LEFT, padx=5)
        self.edit_btn = ttk.Button(btn_frame, text="編集 (Edit)", command=self.load_selected_to_form)
        self.edit_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="削除 (Delete)", command=self.delete_setting).pack(side=tk.LEFT, padx=5)

    def _setup_form_view(self, frame):
        """入力フォームの構築。"""
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # モデル名
        model_frame = ttk.LabelFrame(scrollable_frame, text="バイク情報 / Bike Info", padding=10)
        model_frame.pack(padx=20, pady=10, fill="x")
        ttk.Label(model_frame, text="モデル名:").pack(side=tk.LEFT)
        self.model_entry = ttk.Entry(model_frame, width=40)
        self.model_entry.pack(side=tk.LEFT, padx=10)

        # フロント
        f_frame = ttk.LabelFrame(scrollable_frame, text="フロント / Front", padding=10)
        f_frame.pack(padx=20, pady=10, fill="x")
        
        self.f_vals = {}
        for i, label in enumerate(["Preload", "Rebound", "Compression"]):
            ttk.Label(f_frame, text=f"{label}:").grid(row=0, column=i*2, padx=5, pady=5)
            self.f_vals[label] = ttk.Entry(f_frame, width=10)
            self.f_vals[label].grid(row=0, column=i*2+1, padx=5, pady=5)

        # リア
        r_frame = ttk.LabelFrame(scrollable_frame, text="リア / Rear", padding=10)
        r_frame.pack(padx=20, pady=10, fill="x")
        
        ttk.Label(r_frame, text="Preload:").grid(row=0, column=0, padx=5, pady=5)
        self.r_pre = ttk.Entry(r_frame, width=10)
        self.r_pre.grid(row=0, column=1, padx=5, pady=5)

        self.r_reb = {}
        ttk.Label(r_frame, text="Rebound Hi:").grid(row=1, column=0, padx=5, pady=5)
        self.r_reb['Hi'] = ttk.Entry(r_frame, width=10)
        self.r_reb['Hi'].grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(r_frame, text="Rebound Lo:").grid(row=1, column=2, padx=5, pady=5)
        self.r_reb['Lo'] = ttk.Entry(r_frame, width=10)
        self.r_reb['Lo'].grid(row=1, column=3, padx=5, pady=5)

        self.r_com = {}
        ttk.Label(r_frame, text="Compression Hi:").grid(row=2, column=0, padx=5, pady=5)
        self.r_com['Hi'] = ttk.Entry(r_frame, width=10)
        self.r_com['Hi'].grid(row=2, column=1, padx=5, pady=5)
        ttk.Label(r_frame, text="Compression Lo:").grid(row=2, column=2, padx=5, pady=5)
        self.r_com['Lo'] = ttk.Entry(r_frame, width=10)
        self.r_com['Lo'].grid(row=2, column=3, padx=5, pady=5)

        # ボタン
        btn_f = ttk.Frame(scrollable_frame, padding=20)
        btn_f.pack(fill="x")
        ttk.Button(btn_f, text="保存 (Save)", command=self.save_current).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_f, text="クリア (Clear)", command=self.clear_form).pack(side=tk.LEFT, padx=10)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def refresh_list(self):
        """Treeviewの更新。"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        for iid, s in self.settings.items():
            self.tree.insert('', tk.END, iid=iid, values=(
                s['Model'], s['Front']['Preload'], s['Front']['Rebound'], s['Front']['Compression'],
                s['Rear']['Preload'], s['Rear']['Rebound']['Hi'], s['Rear']['Rebound']['Lo'],
                s['Rear']['Compression']['Hi'], s['Rear']['Compression']['Lo']
            ))

    def clear_form(self):
        """フォームのリセット。"""
        self.model_entry.delete(0, tk.END)
        for e in self.f_vals.values(): e.delete(0, tk.END)
        self.r_pre.delete(0, tk.END)
        for e in self.r_reb.values(): e.delete(0, tk.END)
        for e in self.r_com.values(): e.delete(0, tk.END)
        self.current_item_id = None

    def prepare_new(self):
        self.clear_form()
        self.notebook.select(self.form_frame)

    def load_selected_to_form(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "項目を選択してください。")
            return
        self.current_item_id = selected[0]
        data = self.settings[self.current_item_id]
        
        self.model_entry.insert(0, data['Model'])
        for k, v in data['Front'].items(): self.f_vals[k].insert(0, v)
        self.r_pre.insert(0, data['Rear']['Preload'])
        for k, v in data['Rear']['Rebound'].items(): self.r_reb[k].insert(0, v)
        for k, v in data['Rear']['Compression'].items(): self.r_com[k].insert(0, v)
        
        self.notebook.select(self.form_frame)

    def save_current(self):
        model = self.model_entry.get().strip()
        if not model:
            messagebox.showerror("Error", "モデル名は必須です。")
            return
        
        try:
            new_data = {
                'Model': model,
                'Front': {k: v.get() for k, v in self.f_vals.items()},
                'Rear': {
                    'Preload': self.r_pre.get(),
                    'Rebound': {k: v.get() for k, v in self.r_reb.items()},
                    'Compression': {k: v.get() for k, v in self.r_com.items()}
                }
            }
            
            if self.current_item_id:
                self.settings[self.current_item_id] = new_data
            else:
                new_id = f"ID_{int(max([k.split('_')[1] for k in self.settings.keys()] + [-1])) + 1}"
                self.settings[new_id] = new_data
            
            self.save_data()
            self.refresh_list()
            messagebox.showinfo("Success", "保存しました。")
            self.notebook.select(self.list_frame)
            self.clear_form()
        except Exception as e:
            messagebox.showerror("Error", f"保存失敗: {e}")

    def delete_setting(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "削除する項目を選択してください。")
            return
        if messagebox.askyesno("Confirm", "本当に削除しますか？"):
            del self.settings[selected[0]]
            self.save_data()
            self.refresh_list()

if __name__ == "__main__":
    root = tk.Tk()
    app = SuspensionConfigApp(root)
    root.mainloop()
