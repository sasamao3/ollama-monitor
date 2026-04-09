import tkinter as tk
from tkinter import ttk

class GreetingApp:
    """
    Tkinterアプリケーションをカプセル化し、ttkを使用した洗練されたスタイルを提供するクラス。
    """
    def __init__(self, master):
        """コンストラクタ：ウィンドウの初期化、タイトル設定、ウィジェットの作成を行う"""
        self.master = master
        master.title("おーっす！")

        # ttk.Labelを使用して、現代的なルック＆フィールを適用する
        self.label = ttk.Label(master, text="おーっす！", font=("Helvetica", 18))
        self.label.pack(padx=20, pady=20)

    def run(self):
        """アプリケーションのメインループを開始する"""
        self.master.mainloop()

if __name__ == "__main__":
    # ルートウィンドウのインスタンスを作成
    root = tk.Tk()
    # アプリケーションクラスのインスタンスを作成し、実行する
    app = GreetingApp(root)
    app.run()
