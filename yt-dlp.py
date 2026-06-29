import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import subprocess
import threading
import os
import sys
import urllib.request
import zipfile
import shutil
import json
import datetime
import re
from pathlib import Path
from io import BytesIO


CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "save_path": r"D:\Download\yt-dlp",
    "format": "best",
    "container": "auto",
    "write_subs": False,
    "auto_subs": False,
    "embed_subs": False,
    "sub_langs": "zh-TW,en",
    "sub_format": "srt",
    "split_enable": False,
    "split_mode": "time",
    "split_time": "00:30:00",
    "split_parts": "3",
    "split_delete_original": True,
    "crop_enable": False,
    "crop_start": "00:00:00",
    "crop_end": "00:00:60",
}


class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Universal Downloader (YouTube/Podcast) v1.3.0")
        self.root.geometry("780x850")
        self.root.minsize(700, 600)

        self.is_task_running = False  # 統稱任務狀態 (下載或更新或解析中)
        self.stop_flag = False       # 用於停止批次下載
        self.current_process = None  # 當前子程序 (用於停止按鈕)

        # 設定 bin 資料夾路徑
        self.bin_folder = os.path.join(os.getcwd(), "bin")
        os.makedirs(self.bin_folder, exist_ok=True)

        # 讀取設定檔
        self.config = self._load_config()

        self.setup_menu()
        self.setup_ui()
        self.refresh_versions()

        # 關閉視窗時自動保存設定
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ======================== 設定檔 ========================
    def _get_config_path(self):
        return os.path.join(os.getcwd(), CONFIG_FILE)

    def _load_config(self):
        """從 config.json 讀取設定，不存在則使用預設值"""
        path = self._get_config_path()
        config = DEFAULT_CONFIG.copy()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                config.update(saved)
            except Exception:
                pass
        return config

    def _save_config(self):
        """將目前 UI 設定值寫入 config.json"""
        config = {
            "save_path": self.path_entry.get(),
            "format": self.format_var.get(),
            "container": self.container_var.get(),
            "write_subs": self.write_subs_var.get(),
            "auto_subs": self.auto_subs_var.get(),
            "embed_subs": self.embed_subs_var.get(),
            "sub_langs": self.sub_lang_entry.get().strip(),
            "sub_format": self.sub_format_var.get(),
            "split_enable": self.split_enable_var.get(),
            "split_mode": self.split_mode_var.get(),
            "split_time": self.split_time_entry.get(),
            "split_parts": self.split_parts_entry.get(),
            "split_delete_original": self.split_delete_original_var.get(),
            "crop_enable": self.crop_enable_var.get(),
            "crop_start": self.crop_start_entry.get(),
            "crop_end": self.crop_end_entry.get(),
        }
        try:
            with open(self._get_config_path(), 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _on_close(self):
        """視窗關閉時自動保存設定"""
        self._save_config()
        self.root.destroy()

    # ======================== 選單 ========================
    def setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="檢查並更新組件", command=self.start_update_tools)

    # ======================== UI 佈局 ========================
    def setup_ui(self):
        cfg = self.config

        # --- URL 輸入區 ---
        url_frame = tk.Frame(self.root)
        url_frame.pack(pady=(10, 5), padx=10, fill=tk.X)

        tk.Label(url_frame, text="URL (影片/RSS/播放清單):", font=("Arial", 10)).pack(anchor="w")
        self.url_entry = tk.Text(url_frame, height=3, wrap=tk.WORD)
        self.url_entry.pack(fill=tk.X, pady=5)

        # --- 按鈕區 ---
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)

        self.analyze_btn = tk.Button(
            btn_frame, text="🔍 解析內容", command=self.start_analyze,
            bg="#2196F3", fg="white", font=("Arial", 10, "bold"), padx=10
        )
        self.analyze_btn.pack(side=tk.LEFT, padx=10)

        self.download_btn = tk.Button(
            btn_frame, text="⬇️ 直接下載", command=self.start_direct_download,
            bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), padx=10
        )
        self.download_btn.pack(side=tk.LEFT, padx=10)

        self.stop_btn = tk.Button(
            btn_frame, text="⏹ 停止", command=self.stop_task,
            bg="#f44336", fg="white", font=("Arial", 10, "bold"), padx=10,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=10)

        # --- 下載選項區 ---
        options_frame = tk.LabelFrame(self.root, text="下載選項", padx=10, pady=5)
        options_frame.pack(pady=5, padx=10, fill=tk.X)

        # 時間裁切
        time_frame = tk.Frame(options_frame)
        time_frame.pack(fill=tk.X, pady=3)
        
        self.crop_enable_var = tk.BooleanVar(value=cfg.get("crop_enable", False))
        tk.Checkbutton(time_frame, text="時間裁切", variable=self.crop_enable_var, command=self._toggle_crop_state).pack(side=tk.LEFT)
        
        self.crop_start_entry = tk.Entry(time_frame, width=10)
        self.crop_start_entry.pack(side=tk.LEFT, padx=5)
        self.crop_start_entry.insert(0, cfg.get("crop_start", "00:00:00"))
        
        tk.Label(time_frame, text="-").pack(side=tk.LEFT)
        
        self.crop_end_entry = tk.Entry(time_frame, width=10)
        self.crop_end_entry.pack(side=tk.LEFT, padx=5)
        self.crop_end_entry.insert(0, cfg.get("crop_end", "00:00:60"))

        # 影片分割
        split_frame = tk.Frame(options_frame)
        split_frame.pack(fill=tk.X, pady=3)
        self.split_enable_var = tk.BooleanVar(value=cfg.get("split_enable", False))
        tk.Checkbutton(split_frame, text="影片分割", variable=self.split_enable_var, command=self._toggle_split_state).pack(side=tk.LEFT)
        
        self.split_mode_var = tk.StringVar(value=cfg.get("split_mode", "time"))
        
        self.split_time_rb = tk.Radiobutton(split_frame, text="依時間", variable=self.split_mode_var, value="time")
        self.split_time_rb.pack(side=tk.LEFT, padx=(5, 0))
        self.split_time_entry = tk.Entry(split_frame, width=10)
        self.split_time_entry.pack(side=tk.LEFT, padx=2)
        self.split_time_entry.insert(0, cfg.get("split_time", "00:30:00"))
        
        self.split_parts_rb = tk.Radiobutton(split_frame, text="依數量", variable=self.split_mode_var, value="parts")
        self.split_parts_rb.pack(side=tk.LEFT, padx=(10, 0))
        self.split_parts_entry = tk.Entry(split_frame, width=5)
        self.split_parts_entry.pack(side=tk.LEFT, padx=2)
        self.split_parts_entry.insert(0, cfg.get("split_parts", "3"))
        tk.Label(split_frame, text="份").pack(side=tk.LEFT)
        
        self.split_delete_original_var = tk.BooleanVar(value=cfg.get("split_delete_original", True))
        self.split_delete_cb = tk.Checkbutton(split_frame, text="刪除原檔", variable=self.split_delete_original_var)
        self.split_delete_cb.pack(side=tk.LEFT, padx=(10, 0))

        # 儲存位置
        path_frame = tk.Frame(options_frame)
        path_frame.pack(fill=tk.X, pady=3)
        tk.Label(path_frame, text="儲存位置:").pack(side=tk.LEFT)
        self.path_entry = tk.Entry(path_frame)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.path_entry.insert(0, cfg["save_path"])
        tk.Button(path_frame, text="瀏覽", command=self.browse_folder).pack(side=tk.LEFT)

        # 影片格式選擇
        fmt_frame = tk.Frame(options_frame)
        fmt_frame.pack(fill=tk.X, pady=3)
        tk.Label(fmt_frame, text="影片格式:").pack(side=tk.LEFT)
        self.format_var = tk.StringVar(value=cfg["format"])
        for text, val in [("最佳畫質", "best"), ("1080p", "1080"), ("720p", "720"),
                          ("480p", "480"), ("僅音訊", "audio")]:
            tk.Radiobutton(fmt_frame, text=text, variable=self.format_var, value=val).pack(side=tk.LEFT, padx=4)

        # 容器格式偏好
        container_frame = tk.Frame(options_frame)
        container_frame.pack(fill=tk.X, pady=3)
        tk.Label(container_frame, text="容器格式:").pack(side=tk.LEFT)
        self.container_var = tk.StringVar(value=cfg["container"])
        for text, val in [("自動 (最佳)", "auto"), ("MP4 偏好", "mp4"), ("WebM 偏好", "webm")]:
            tk.Radiobutton(container_frame, text=text, variable=self.container_var, value=val).pack(side=tk.LEFT, padx=4)

        # 字幕選項
        sub_frame = tk.Frame(options_frame)
        sub_frame.pack(fill=tk.X, pady=3)

        self.write_subs_var = tk.BooleanVar(value=cfg["write_subs"])
        tk.Checkbutton(sub_frame, text="下載字幕", variable=self.write_subs_var).pack(side=tk.LEFT)

        self.auto_subs_var = tk.BooleanVar(value=cfg["auto_subs"])
        tk.Checkbutton(sub_frame, text="含自動產生字幕", variable=self.auto_subs_var).pack(side=tk.LEFT, padx=(10, 0))

        self.embed_subs_var = tk.BooleanVar(value=cfg["embed_subs"])
        tk.Checkbutton(sub_frame, text="嵌入字幕至影片", variable=self.embed_subs_var).pack(side=tk.LEFT, padx=(10, 0))

        # 字幕語言 & 格式
        sub_lang_frame = tk.Frame(options_frame)
        sub_lang_frame.pack(fill=tk.X, pady=3)
        tk.Label(sub_lang_frame, text="字幕語言:").pack(side=tk.LEFT)
        self.sub_lang_entry = tk.Entry(sub_lang_frame, width=20)
        self.sub_lang_entry.pack(side=tk.LEFT, padx=5)
        self.sub_lang_entry.insert(0, cfg["sub_langs"])
        tk.Label(sub_lang_frame, text="(逗號分隔, 如 zh-TW,en,ja)").pack(side=tk.LEFT, padx=5)

        tk.Label(sub_lang_frame, text="格式:").pack(side=tk.LEFT, padx=(15, 0))
        self.sub_format_var = tk.StringVar(value=cfg["sub_format"])
        ttk.Combobox(
            sub_lang_frame, textvariable=self.sub_format_var,
            values=["srt", "vtt", "ass"], width=5, state="readonly"
        ).pack(side=tk.LEFT, padx=5)

        # --- 進度條 ---
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(pady=(5, 0), padx=10, fill=tk.X)

        # --- 狀態列 ---
        self.status_label = tk.Label(self.root, text="就緒", fg="blue", font=("Arial", 10))
        self.status_label.pack(pady=3)

        # --- 日誌區 ---
        self.log_text = scrolledtext.ScrolledText(self.root, height=15, state='disabled')
        self.log_text.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        # 設定顏色標籤
        for color in ("red", "green", "blue", "orange", "purple", "black"):
            self.log_text.tag_configure(color, foreground=color)

        ver_frame = tk.Frame(self.root)
        ver_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        self.ver_label = tk.Label(ver_frame, text="偵測版本中...", font=("Arial", 8), fg="gray")
        self.ver_label.pack(side=tk.RIGHT)

        # 初始化分割與裁切選項狀態
        self._toggle_split_state()
        self._toggle_crop_state()

    # ======================== 工具方法 ========================
    def log(self, msg, color="black"):
        """寫入日誌 (支援顏色標籤)"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"{msg}\n", color)
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update_idletasks()

    def set_status(self, msg, color="blue"):
        self.status_label.config(text=msg, fg=color)

    def _toggle_crop_state(self):
        state = tk.NORMAL if self.crop_enable_var.get() else tk.DISABLED
        self.crop_start_entry.config(state=state)
        self.crop_end_entry.config(state=state)

    def _toggle_split_state(self):
        state = tk.NORMAL if self.split_enable_var.get() else tk.DISABLED
        self.split_time_rb.config(state=state)
        self.split_time_entry.config(state=state)
        self.split_parts_rb.config(state=state)
        self.split_parts_entry.config(state=state)
        self.split_delete_cb.config(state=state)

    def browse_folder(self):
        d = filedialog.askdirectory()
        if d:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, d)

    def get_yt_dlp_cmd(self):
        """取得 yt-dlp 執行檔路徑 (優先使用 bin 資料夾)"""
        bin_exe = os.path.join(self.bin_folder, "yt-dlp.exe")
        if os.path.exists(bin_exe):
            return bin_exe
        if os.path.exists("yt-dlp.exe"):
            return "yt-dlp.exe"
        return "yt-dlp"  # 嘗試系統路徑

    def check_tools_ready(self):
        """檢查工具是否就緒，若無則提示下載"""
        exe = self.get_yt_dlp_cmd()
        try:
            subprocess.run(
                [exe, "--version"], capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            return exe
        except FileNotFoundError:
            if messagebox.askyesno("缺少組件", "找不到 yt-dlp，是否立即下載？"):
                self.start_update_tools()
            return None

    def _get_startupinfo(self):
        """取得 Windows 隱藏視窗用的 STARTUPINFO"""
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return si

    def _get_subprocess_env(self):
        """取得強制 UTF-8 輸出的環境變數 (修正 yt-dlp 在 Windows 上的亂碼問題)"""
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        return env

    def _build_format_arg(self):
        """根據格式選擇與容器偏好建立 -f 參數"""
        fmt = self.format_var.get()
        container = self.container_var.get()

        if fmt == "audio":
            return "bestaudio/best"

        if fmt == "best":
            base = "bestvideo"
        else:
            base = f"bestvideo[height<={fmt}]"

        if container == "mp4":
            return f"{base}[ext=mp4]+bestaudio[ext=m4a]/{base}+bestaudio/best"
        elif container == "webm":
            return f"{base}[ext=webm]+bestaudio[ext=webm]/{base}+bestaudio/best"
        else:
            return f"{base}+bestaudio/best"

    def _build_subtitle_args(self):
        """建立字幕相關命令列參數 (主頁面設定)"""
        args = []
        need_write = self.write_subs_var.get()
        need_auto = self.auto_subs_var.get()
        need_embed = self.embed_subs_var.get()

        # 嵌入字幕需要先下載字幕
        if need_embed:
            need_write = True

        if need_write:
            args.append("--write-subs")
        if need_auto:
            args.append("--write-auto-subs")

        if need_write or need_auto:
            lang = self.sub_lang_entry.get().strip()
            if lang:
                args.extend(["--sub-langs", lang])
            else:
                args.extend(["--sub-langs", "all"])
            sub_fmt = self.sub_format_var.get()
            if sub_fmt:
                args.extend(["--convert-subs", sub_fmt])

        if need_embed:
            args.append("--embed-subs")

        return args

    def _build_section_args(self):
        """建立時間裁切參數"""
        if not hasattr(self, 'crop_enable_var') or not self.crop_enable_var.get():
            return []
            
        start_time = self.crop_start_entry.get().strip()
        end_time = self.crop_end_entry.get().strip()
        
        s = start_time if start_time else "0"
        e = end_time if end_time else "inf"
        return ["--download-sections", f"*{s}-{e}", "--force-keyframes-at-cuts"]

    def stop_task(self):
        """停止目前正在執行的任務"""
        self.stop_flag = True
        if self.current_process:
            try:
                self.log("⏹ 正在停止任務...", "red")
                if sys.platform == 'win32':
                    subprocess.call(
                        ['taskkill', '/F', '/T', '/PID', str(self.current_process.pid)],
                        startupinfo=self._get_startupinfo()
                    )
                else:
                    self.current_process.terminate()
            except Exception:
                pass

    def _set_buttons_busy(self, busy=True):
        """切換按鈕啟用/禁用狀態"""
        if busy:
            self.analyze_btn.config(state=tk.DISABLED)
            self.download_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
        else:
            self.analyze_btn.config(state=tk.NORMAL)
            self.download_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

    # ======================== 核心功能 1: 解析 ========================
    def start_analyze(self):
        if self.is_task_running:
            return
        url = self.url_entry.get("1.0", tk.END).strip()
        if not url:
            return messagebox.showerror("錯誤", "請輸入 URL")

        exe = self.check_tools_ready()
        if not exe:
            return

        self.is_task_running = True
        self.set_status("正在解析中...", "orange")
        self._set_buttons_busy(True)

        threading.Thread(target=self.run_analyze, args=(exe, url), daemon=True).start()

    def run_analyze(self, exe, url):
        """第一階段: 快速判斷是播放清單還是單一影片"""
        try:
            self.log(f"開始解析: {url}")

            cmd = [exe, "--dump-single-json", "--flat-playlist", "--ignore-errors", url]

            process = subprocess.run(
                cmd, capture_output=True, text=True,
                encoding='utf-8', errors='replace',
                startupinfo=self._get_startupinfo(),
                env=self._get_subprocess_env()
            )

            if process.returncode != 0:
                raise Exception(process.stderr)

            data = json.loads(process.stdout)

            if 'entries' in data and data.get('_type') in ('playlist', 'multi_video'):
                # 播放清單 → 顯示清單選擇視窗
                entries = data['entries']
                title = data.get('title', '未知列表')
                self.log(f"✓ 偵測到播放清單: {title}，共 {len(entries)} 個項目", "green")
                self.root.after(0, lambda: self._finish_analyze_playlist(title, entries, exe))
            else:
                # 單一影片 → 進入詳細解析
                self.log("✓ 偵測到單一影片，正在取得詳細資訊...", "green")
                self._run_detailed_analyze(exe, url)

        except Exception as e:
            self.log(f"解析失敗: {e}", "red")
            self.set_status("解析失敗", "red")
            self.root.after(0, lambda: self._set_buttons_busy(False))
            self.is_task_running = False

    def _finish_analyze_playlist(self, title, entries, exe):
        """在主執行緒中完成播放清單解析 (開啟選擇視窗)"""
        self._set_buttons_busy(False)
        self.is_task_running = False
        self.set_status("就緒")
        self.show_playlist_window(title, entries, exe)

    def _run_detailed_analyze(self, exe, url):
        """第二階段: 深入解析單一影片 (取得所有格式 + 字幕)"""
        try:
            cmd = [exe, "--dump-single-json", "--ignore-errors", url]

            process = subprocess.run(
                cmd, capture_output=True, text=True,
                encoding='utf-8', errors='replace',
                startupinfo=self._get_startupinfo(),
                env=self._get_subprocess_env()
            )

            if process.returncode != 0:
                raise Exception(process.stderr)

            data = json.loads(process.stdout)
            self.log(f"✓ 解析完成: {data.get('title', '未知')}", "green")
            self.root.after(0, lambda: self._finish_detailed_analyze(data, exe))

        except Exception as e:
            self.log(f"詳細解析失敗: {e}", "red")
            self.set_status("解析失敗", "red")
            self.root.after(0, lambda: self._set_buttons_busy(False))
            self.is_task_running = False

    def _finish_detailed_analyze(self, data, exe):
        """在主執行緒中完成詳細解析 (開啟詳情視窗)"""
        self._set_buttons_busy(False)
        self.is_task_running = False
        self.set_status("就緒")
        self.show_video_detail_window(data, exe)

    # ======================== 播放清單選擇視窗 ========================
    def show_playlist_window(self, title, entries, exe):
        top = tk.Toplevel(self.root)
        top.title(f"播放清單 - {title}")
        top.geometry("850x600")
        top.minsize(700, 400)

        # 頂部控制區
        ctrl_frame = tk.Frame(top, pady=10)
        ctrl_frame.pack(fill=tk.X, padx=10)
        tk.Label(ctrl_frame, text=f"共找到 {len(entries)} 個項目",
                 font=("Arial", 10, "bold")).pack(side=tk.LEFT)

        # Treeview 影片清單
        tree_frame = tk.Frame(top)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        columns = ("idx", "date", "title", "duration")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")

        tree.heading("idx", text="#")
        tree.heading("date", text="發布日期")
        tree.heading("title", text="標題")
        tree.heading("duration", text="時長")

        tree.column("idx", width=40, anchor="center")
        tree.column("date", width=100, anchor="center")
        tree.column("title", width=500)
        tree.column("duration", width=80, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 填入資料
        items_map = {}
        for idx, entry in enumerate(entries, 1):
            date_str = entry.get('upload_date', '----')
            if len(date_str) == 8:
                date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

            dur = entry.get('duration')
            dur_str = str(datetime.timedelta(seconds=int(dur))) if dur else "--:--"

            item_id = tree.insert("", "end",
                                  values=(idx, date_str, entry.get('title', '未知'), dur_str))
            items_map[item_id] = entry

        # 底部按鈕
        btn_frame = tk.Frame(top, pady=10)
        btn_frame.pack(fill=tk.X, padx=10)

        def select_all():
            for item in tree.get_children():
                tree.selection_add(item)

        def select_none():
            tree.selection_remove(tree.get_children())

        def get_selected_urls():
            selected_ids = tree.selection()
            if not selected_ids:
                messagebox.showwarning("提示", "未選擇任何項目")
                return None
            results = []
            for iid in selected_ids:
                entry = items_map[iid]
                u = entry.get('url') or entry.get('webpage_url')
                if u:
                    results.append((entry.get('title', '未知'), u))
            return results

        def do_quick_download():
            targets = get_selected_urls()
            if targets:
                top.destroy()
                self.start_batch_download(targets)

        def do_analyze_selected():
            """對選取的單一影片進行詳細解析"""
            selected_ids = tree.selection()
            if not selected_ids:
                return messagebox.showwarning("提示", "未選擇任何項目")
            if len(selected_ids) > 1:
                return messagebox.showwarning("提示", "詳細解析一次只能選擇一個影片\n請只選取一個項目")

            entry = items_map[selected_ids[0]]
            u = entry.get('url') or entry.get('webpage_url')
            if u:
                self.is_task_running = True
                self.set_status("正在詳細解析...", "orange")
                self._set_buttons_busy(True)
                threading.Thread(
                    target=self._run_detailed_analyze, args=(exe, u), daemon=True
                ).start()

        tk.Button(btn_frame, text="全選", command=select_all).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="全不選", command=select_none).pack(side=tk.LEFT, padx=5)
        tk.Button(
            btn_frame, text="🔍 解析選取影片 (單個)",
            command=do_analyze_selected,
            bg="#2196F3", fg="white", font=("Arial", 10, "bold")
        ).pack(side=tk.LEFT, padx=10)
        tk.Button(
            btn_frame, text="⬇️ 快速下載選取項目",
            command=do_quick_download,
            bg="#4CAF50", fg="white", font=("Arial", 10, "bold")
        ).pack(side=tk.RIGHT, padx=5)

    # ======================== 影片詳情視窗 ========================
    def show_video_detail_window(self, data, exe):
        top = tk.Toplevel(self.root)
        top.title(f"影片詳情 - {data.get('title', '未知')}")
        top.geometry("900x700")
        top.minsize(750, 500)

        # --- 影片基本資訊 ---
        info_frame = tk.LabelFrame(top, text="影片資訊", padx=10, pady=5)
        info_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        v_title = data.get('title', '未知')
        uploader = data.get('uploader', '未知')
        duration = data.get('duration')
        dur_str = str(datetime.timedelta(seconds=int(duration))) if duration else "--:--"
        upload_date = data.get('upload_date', '----')
        if len(upload_date) == 8:
            upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"

        tk.Label(info_frame, text=f"標題: {v_title}", font=("Arial", 11, "bold"),
                 wraplength=850, anchor="w", justify="left").pack(anchor="w")
        tk.Label(info_frame, text=f"上傳者: {uploader}  |  時長: {dur_str}  |  日期: {upload_date}",
                 font=("Arial", 9)).pack(anchor="w")

        # --- 分頁 (格式 / 字幕) ---
        notebook = ttk.Notebook(top)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # ===== 頁籤 1: 影片格式 =====
        fmt_tab = tk.Frame(notebook)
        notebook.add(fmt_tab, text="📹 影片格式")

        # 格式列表
        fmt_tree_frame = tk.Frame(fmt_tab)
        fmt_tree_frame.pack(fill=tk.BOTH, expand=True)

        fmt_columns = ("format_id", "ext", "resolution", "fps", "vcodec", "acodec", "size", "note")
        fmt_tree = ttk.Treeview(fmt_tree_frame, columns=fmt_columns, show="headings", selectmode="browse")

        for col, heading, width, anchor in [
            ("format_id", "ID", 60, "center"), ("ext", "格式", 50, "center"),
            ("resolution", "解析度", 100, "center"), ("fps", "FPS", 45, "center"),
            ("vcodec", "影像編碼", 100, "w"), ("acodec", "音訊編碼", 100, "w"),
            ("size", "檔案大小", 90, "e"), ("note", "備註", 200, "w"),
        ]:
            fmt_tree.heading(col, text=heading)
            fmt_tree.column(col, width=width, anchor=anchor)

        fmt_scroll = ttk.Scrollbar(fmt_tree_frame, orient=tk.VERTICAL, command=fmt_tree.yview)
        fmt_tree.configure(yscroll=fmt_scroll.set)
        fmt_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        fmt_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 填入格式資料
        format_map = {}
        for f in data.get('formats', []):
            fid = f.get('format_id', '?')
            ext = f.get('ext', '?')
            height = f.get('height')
            res = f"{f.get('width', '?')}x{height}" if height else "audio only"
            fps = f.get('fps')
            fps_str = str(int(fps)) if fps else ''
            vcodec = f.get('vcodec', 'none')
            vcodec = '--' if vcodec == 'none' else vcodec.split('.')[0]
            acodec = f.get('acodec', 'none')
            acodec = '--' if acodec == 'none' else acodec.split('.')[0]

            size = f.get('filesize') or f.get('filesize_approx')
            if size:
                if size > 1024 ** 3:
                    size_str = f"{size / 1024 ** 3:.1f} GB"
                elif size > 1024 ** 2:
                    size_str = f"{size / 1024 ** 2:.1f} MB"
                elif size > 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size} B"
            else:
                size_str = "未知"

            note = f.get('format_note', '') or ''

            item_id = fmt_tree.insert(
                "", "end",
                values=(fid, ext, res, fps_str, vcodec, acodec, size_str, note)
            )
            format_map[item_id] = f

        # 影片格式分頁內的下載按鈕
        fmt_btn_frame = tk.Frame(fmt_tab, pady=5)
        fmt_btn_frame.pack(fill=tk.X, padx=5)

        def do_download_selected_format():
            """僅下載選取的影片格式，不套用主頁面設定"""
            selected = fmt_tree.selection()
            if not selected:
                return messagebox.showwarning("提示", "請先在上方選取一個影片格式")

            url = data.get('webpage_url') or data.get('original_url', '')
            if not url:
                return messagebox.showerror("錯誤", "找不到影片 URL")

            f = format_map[selected[0]]
            format_arg = f.get('format_id')
            # 若是純影像串流，自動加上最佳音訊
            if f.get('acodec') in ('none', None) and f.get('vcodec') not in ('none', None):
                format_arg = f"{format_arg}+bestaudio"

            top.destroy()
            # subtitle_args=[] 表示不帶任何字幕參數
            self._download_single(exe, url, v_title, format_id=format_arg, subtitle_args=[])

        tk.Button(
            fmt_btn_frame, text="⬇️ 下載選取格式",
            command=do_download_selected_format,
            bg="#FF9800", fg="white", font=("Arial", 10, "bold")
        ).pack(side=tk.LEFT, padx=5)

        # ===== 頁籤 2: 字幕 =====
        sub_tab = tk.Frame(notebook)
        notebook.add(sub_tab, text="📝 字幕")

        # 字幕列表
        sub_tree_frame = tk.Frame(sub_tab)
        sub_tree_frame.pack(fill=tk.BOTH, expand=True)

        sub_columns = ("type", "lang", "name", "formats")
        sub_tree = ttk.Treeview(sub_tree_frame, columns=sub_columns, show="headings", selectmode="extended")

        for col, heading, width in [
            ("type", "類型", 120), ("lang", "語言代碼", 100),
            ("name", "語言名稱", 200), ("formats", "可用格式", 300),
        ]:
            sub_tree.heading(col, text=heading)
            sub_tree.column(col, width=width)
        sub_tree.column("type", anchor="center")
        sub_tree.column("lang", anchor="center")

        sub_scroll = ttk.Scrollbar(sub_tree_frame, orient=tk.VERTICAL, command=sub_tree.yview)
        sub_tree.configure(yscroll=sub_scroll.set)
        sub_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sub_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 儲存字幕 metadata 供下載使用
        sub_items_map = {}  # tree_item_id -> {"type": "manual"/"auto", "lang": "xx"}

        # 手動上傳的字幕
        subtitles = data.get('subtitles', {})
        for lang, subs in sorted(subtitles.items()):
            if not subs:
                continue
            name = subs[0].get('name', '') if subs else ''
            fmts = ', '.join(sorted(set(s.get('ext', '?') for s in subs)))
            iid = sub_tree.insert("", "end", values=("✋ 手動上傳", lang, name, fmts))
            sub_items_map[iid] = {"type": "manual", "lang": lang}

        # 自動產生的字幕
        auto_captions = data.get('automatic_captions', {})
        for lang, subs in sorted(auto_captions.items()):
            if not subs:
                continue
            name = subs[0].get('name', '') if subs else ''
            fmts = ', '.join(sorted(set(s.get('ext', '?') for s in subs)))
            iid = sub_tree.insert("", "end", values=("🤖 自動產生", lang, name, fmts))
            sub_items_map[iid] = {"type": "auto", "lang": lang}

        # 字幕分頁內的下載按鈕
        sub_btn_frame = tk.Frame(sub_tab, pady=5)
        sub_btn_frame.pack(fill=tk.X, padx=5)

        def do_download_selected_subs():
            """僅下載選取的字幕，不下載影片 (--skip-download)"""
            selected = sub_tree.selection()
            if not selected:
                return messagebox.showwarning("提示", "請先在上方選取要下載的字幕")

            url = data.get('webpage_url') or data.get('original_url', '')
            if not url:
                return messagebox.showerror("錯誤", "找不到影片 URL")

            # 收集選取的字幕資訊
            manual_langs = []
            auto_langs = []
            for iid in selected:
                info = sub_items_map[iid]
                if info["type"] == "manual":
                    manual_langs.append(info["lang"])
                else:
                    auto_langs.append(info["lang"])

            # 組裝字幕參數
            sub_args = ["--skip-download"]

            if manual_langs:
                sub_args.append("--write-subs")
            if auto_langs:
                sub_args.append("--write-auto-subs")

            # 合併語言清單 (去重但保持順序)
            all_langs = list(dict.fromkeys(manual_langs + auto_langs))
            sub_args.extend(["--sub-langs", ",".join(all_langs)])

            # 使用主頁面的字幕格式設定
            sub_fmt = self.sub_format_var.get()
            if sub_fmt:
                sub_args.extend(["--convert-subs", sub_fmt])

            top.destroy()
            self._download_single(exe, url, v_title, format_id=None, subtitle_args=sub_args)

        tk.Button(
            sub_btn_frame, text="📝 僅下載選取字幕",
            command=do_download_selected_subs,
            bg="#9C27B0", fg="white", font=("Arial", 10, "bold")
        ).pack(side=tk.LEFT, padx=5)

    # ======================== 核心功能 2: 下載 ========================
    def _download_single(self, exe, url, title, format_id=None, subtitle_args=None):
        """
        下載單一影片或字幕。
        format_id: 指定格式 (None = 使用主頁面設定)
        subtitle_args: 明確指定字幕參數 (None = 使用主頁面設定, [] = 不處理字幕)
        """
        self.is_task_running = True
        self.stop_flag = False
        self._set_buttons_busy(True)

        def _run():
            save_path = self.path_entry.get()

            cmd = [
                exe,
                "--ffmpeg-location", self.bin_folder,
                "--ignore-config",
                "--no-part",
                "--embed-metadata",
                "-P", save_path,
                "-o", "%(upload_date)s_%(title)s.%(ext)s",
            ]

            # 格式選擇
            is_sub_only = subtitle_args and "--skip-download" in subtitle_args
            if format_id:
                cmd.extend(["-f", format_id])
            elif not is_sub_only:
                cmd.extend(["-f", self._build_format_arg()])

            # 字幕參數
            if subtitle_args is not None:
                cmd.extend(subtitle_args)
            else:
                cmd.extend(self._build_subtitle_args())

            # 時間裁切 (僅下載字幕時不需要)
            if not is_sub_only:
                cmd.extend(self._build_section_args())

            cmd.append(url)

            self.log(f"開始下載: {title}")
            self.set_status(f"正在下載: {title[:40]}...", "orange")

            try:
                # 若為 Windows，移除 CREATE_NEW_PROCESS_GROUP 避免副作用，改用 taskkill
                self.current_process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding='utf-8', errors='replace',
                    startupinfo=self._get_startupinfo(),
                    env=self._get_subprocess_env()
                )
                
                is_livestream = False
                
                final_filepath = None
                for line in self.current_process.stdout:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # 擷取最終檔案路徑
                    if line.startswith("[download] Destination: "):
                        final_filepath = line.replace("[download] Destination: ", "").strip()
                    elif line.startswith("[Merger] Merging formats into "):
                        final_filepath = line.replace("[Merger] Merging formats into ", "").strip().strip('"')
                    elif line.startswith("[VideoRemuxer] Remuxing video from "):
                        final_filepath = line.split(' to ')[-1].strip().strip('"')
                    elif line.startswith("[download] ") and "has already been downloaded" in line:
                        final_filepath = line.split("[download] ")[1].split(" has already")[0].strip()

                    # 判斷 ffmpeg 直播日誌 (無百分比，有 frame, size, time)
                    # 例如: frame=  719 fps= 87 q=-1.0 size=    7168KiB time=00:00:12.00 bitrate=4891.0kbits/s speed=1.46x
                    if "size=" in line and "time=" in line and "bitrate=" in line:
                        if not is_livestream:
                            is_livestream = True
                            self.progress_bar.config(mode="indeterminate")
                            self.progress_bar.start()
                        
                        match = re.search(r'size=\s*(.*?)\s+time=(.*?)\s+bitrate=.*?speed=\s*(.*?)x', line)
                        if match:
                            size = match.group(1).strip()
                            time_str = match.group(2).strip()
                            speed = match.group(3).strip()
                            self.set_status(f"直播錄製中: 已下載 {size} | 速度: {speed}x | 時間: {time_str}", "orange")

                    # 原本的 yt-dlp 內部下載日誌
                    elif "[download]" in line and "at" in line and "%" not in line and "MiB" in line:
                        if not is_livestream:
                            is_livestream = True
                            self.progress_bar.config(mode="indeterminate")
                            self.progress_bar.start()
                        
                        match = re.search(r'\[download\]\s+(.*?)\s+at\s+(.*?)\s+\((.*?)\)', line)
                        if match:
                            size = match.group(1)
                            speed = match.group(2)
                            time_str = match.group(3)
                            self.set_status(f"直播錄製中: 已下載 {size} | 速度: {speed} | 時間: {time_str}", "orange")

                    elif "[download]" in line and "%" in line:
                        if is_livestream:
                            self.progress_bar.stop()
                            self.progress_bar.config(mode="determinate")
                            is_livestream = False
                            
                        match = re.search(r'(\d+\.?\d*)%', line)
                        if match:
                            pct = float(match.group(1))
                            self.progress_var.set(pct)
                            self.set_status(f"下載中: {pct:.1f}%", "orange")
                    else:
                        self.log(line)

                self.current_process.wait()
                if is_livestream:
                    self.progress_bar.stop()
                    self.progress_bar.config(mode="determinate")

                if self.current_process.returncode == 0 or self.stop_flag:
                    if self.stop_flag:
                        self.log(f"✓ 已手動停止，檔案已儲存", "green")
                    else:
                        self.log(f"✓ 下載完成: {title}", "green")
                    self.progress_var.set(100)
                    if final_filepath and self.split_enable_var.get() and not is_sub_only:
                        self.process_split(final_filepath)
                else:
                    self.log(f"✗ 下載失敗: {title}", "red")

            except Exception as e:
                self.log(f"執行錯誤: {e}", "red")
            finally:
                self.current_process = None
                self.is_task_running = False
                self.progress_var.set(0)
                self.root.after(0, lambda: self._set_buttons_busy(False))
                self.root.after(0, lambda: self.set_status("任務結束", "blue"))
                self.root.after(0, lambda: messagebox.showinfo("完成", f"下載任務已結束:\n{title}"))

        threading.Thread(target=_run, daemon=True).start()

    def start_batch_download(self, targets):
        """啟動批次下載，targets: list of (title, url)"""
        exe = self.check_tools_ready()
        if not exe:
            return

        self.is_task_running = True
        self.stop_flag = False
        self._set_buttons_busy(True)
        self.download_btn.config(text="下載中...")

        threading.Thread(target=self.run_batch_download, args=(exe, targets), daemon=True).start()

    def start_direct_download(self):
        """直接下載 (從 URL 輸入框)"""
        if self.is_task_running:
            return
        url = self.url_entry.get("1.0", tk.END).strip()
        if not url:
            return messagebox.showerror("錯誤", "請輸入 URL")
        self.start_batch_download([("直接下載任務", url)])

    def run_batch_download(self, exe, targets):
        total = len(targets)
        save_path = self.path_entry.get()

        self.log(f"=== 開始批次下載，共 {total} 個項目 ===", "blue")

        for i, (title, url) in enumerate(targets, 1):
            if self.stop_flag:
                self.log("⏹ 下載已手動停止", "red")
                break

            self.set_status(f"正在下載 ({i}/{total}): {title[:30]}...", "orange")
            self.log(f"[{i}/{total}] 處理中: {title}")

            cmd = [
                exe,
                "--ffmpeg-location", self.bin_folder,
                "--ignore-config",
                "--no-part",
                "--embed-metadata",
                "-f", self._build_format_arg(),
                "-P", save_path,
                "-o", "%(upload_date)s_%(title)s.%(ext)s",
                url
            ] + self._build_subtitle_args() + self._build_section_args()

            try:
                # 若為 Windows，移除 CREATE_NEW_PROCESS_GROUP
                self.current_process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding='utf-8', errors='replace',
                    startupinfo=self._get_startupinfo(),
                    env=self._get_subprocess_env()
                )

                is_livestream = False
                final_filepath = None
                for line in self.current_process.stdout:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # 擷取最終檔案路徑
                    if line.startswith("[download] Destination: "):
                        final_filepath = line.replace("[download] Destination: ", "").strip()
                    elif line.startswith("[Merger] Merging formats into "):
                        final_filepath = line.replace("[Merger] Merging formats into ", "").strip().strip('"')
                    elif line.startswith("[VideoRemuxer] Remuxing video from "):
                        final_filepath = line.split(' to ')[-1].strip().strip('"')
                    elif line.startswith("[download] ") and "has already been downloaded" in line:
                        final_filepath = line.split("[download] ")[1].split(" has already")[0].strip()

                    # 判斷 ffmpeg 直播日誌
                    if "size=" in line and "time=" in line and "bitrate=" in line:
                        if not is_livestream:
                            is_livestream = True
                            self.progress_bar.config(mode="indeterminate")
                            self.progress_bar.start()
                        
                        match = re.search(r'size=\s*(.*?)\s+time=(.*?)\s', line)
                        if match:
                            size = match.group(1).strip()
                            time_str = match.group(2).strip()
                            self.set_status(f"直播錄製中 ({i}/{total}): 已下載 {size} | 時間: {time_str}", "orange")

                    elif "[download]" in line and "at" in line and "%" not in line and "MiB" in line:
                        if not is_livestream:
                            is_livestream = True
                            self.progress_bar.config(mode="indeterminate")
                            self.progress_bar.start()
                        
                        match = re.search(r'\[download\]\s+(.*?)\s+at\s+(.*?)\s+\((.*?)\)', line)
                        if match:
                            size = match.group(1)
                            time_str = match.group(3)
                            self.set_status(f"直播錄製中 ({i}/{total}): 已下載 {size} | 時間: {time_str}", "orange")

                    elif "[download]" in line and "%" in line:
                        if is_livestream:
                            self.progress_bar.stop()
                            self.progress_bar.config(mode="determinate")
                            is_livestream = False
                            
                        match = re.search(r'(\d+\.?\d*)%', line)
                        if match:
                            pct = float(match.group(1))
                            overall = ((i - 1) + pct / 100) / total * 100
                            self.progress_var.set(overall)
                    else:
                        self.log(line)

                self.current_process.wait()
                if is_livestream:
                    self.progress_bar.stop()
                    self.progress_bar.config(mode="determinate")
                    
                if self.current_process.returncode == 0 or self.stop_flag:
                    self.log(f"✓ 完成: {title}", "green")
                    if final_filepath and self.split_enable_var.get():
                        self.process_split(final_filepath)
                else:
                    self.log(f"✗ 失敗: {title}", "red")

            except Exception as e:
                self.log(f"執行錯誤: {e}", "red")

        self.current_process = None
        self.is_task_running = False
        self.progress_var.set(0)
        self.root.after(0, lambda: self._set_buttons_busy(False))
        self.root.after(0, lambda: self.download_btn.config(text="⬇️ 直接下載"))
        self.root.after(0, lambda: self.set_status("任務結束", "blue"))
        self.root.after(0, lambda: messagebox.showinfo("完成", "所有排程任務已結束"))

    def process_split(self, filepath):
        """處理影片分割邏輯"""
        if not os.path.exists(filepath):
            self.log(f"無法進行分割: 找不到檔案 {filepath}", "red")
            return
            
        mode = self.split_mode_var.get()
        segment_time = 0
        
        if mode == "time":
            time_str = self.split_time_entry.get().strip()
            # parse hh:mm:ss
            try:
                parts = time_str.split(':')
                if len(parts) == 3:
                    segment_time = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                else:
                    raise ValueError("Invalid format")
            except:
                self.log(f"分割時間格式錯誤，請使用 hh:mm:ss", "red")
                return
        elif mode == "parts":
            parts_str = self.split_parts_entry.get().strip()
            try:
                parts_count = int(parts_str)
                if parts_count <= 1:
                    self.log(f"分割數量必須大於 1", "red")
                    return
                # 使用 ffprobe 取得影片時長
                fp_path = os.path.join(self.bin_folder, "ffprobe.exe")
                if not os.path.exists(fp_path):
                    fp_path = "ffprobe"
                
                cmd = [fp_path, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filepath]
                proc = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
                duration = float(proc.stdout.strip())
                segment_time = int(duration / parts_count) + 1
            except Exception as e:
                self.log(f"計算分割時間失敗: {e}", "red")
                return
                
        if segment_time <= 0:
            self.log(f"無效的分割時間", "red")
            return
            
        self.log(f"開始分割檔案... (每個片段約 {segment_time} 秒)")
        self.set_status("正在分割影片...", "orange")
        
        ff_path = os.path.join(self.bin_folder, "ffmpeg.exe")
        if not os.path.exists(ff_path):
            ff_path = "ffmpeg"
            
        # 建立輸出檔名
        base, ext = os.path.splitext(filepath)
        out_pattern = f"{base}_part%03d{ext}"
        
        split_cmd = [
            ff_path, "-y", "-i", filepath,
            "-f", "segment", "-segment_time", str(segment_time),
            "-c", "copy", out_pattern
        ]
        
        try:
            self.current_process = subprocess.Popen(
                split_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', errors='replace',
                startupinfo=self._get_startupinfo()
            )
            for line in self.current_process.stdout:
                pass # 消費 stdout 以免卡住
            self.current_process.wait()
            
            if self.current_process.returncode == 0:
                self.log(f"✓ 分割完成！", "green")
                if self.split_delete_original_var.get():
                    try:
                        os.remove(filepath)
                        self.log(f"已自動刪除原檔", "gray")
                    except Exception as e:
                        self.log(f"無法刪除原檔: {e}", "orange")
            else:
                self.log(f"✗ 分割失敗", "red")
        except Exception as e:
            self.log(f"執行分割錯誤: {e}", "red")
        finally:
            self.current_process = None

    # ======================== 工具更新 ========================
    def start_update_tools(self):
        if self.is_task_running:
            return messagebox.showwarning("忙碌中", "請等待目前任務結束")
        if messagebox.askyesno("更新", "確定要檢查並更新 yt-dlp 和 ffmpeg 嗎？"):
            self.is_task_running = True
            self.set_status("正在更新...", "purple")
            threading.Thread(target=self.run_update, daemon=True).start()

    def run_update(self):
        try:
            self.log("=== 開始檢查更新 ===")

            # 1. 更新 yt-dlp
            yt_path = os.path.join(self.bin_folder, "yt-dlp.exe")
            if not os.path.exists(yt_path):
                self.log("下載 yt-dlp...")
                urllib.request.urlretrieve(
                    "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe",
                    yt_path
                )
                self.log("  ✓ yt-dlp 下載完成", "green")
            else:
                self.log("檢查 yt-dlp 更新...")
                proc = subprocess.run(
                    [yt_path, "-U"],
                    capture_output=True, text=True,
                    encoding='utf-8', errors='replace',
                    creationflags=0x08000000
                )
                for line in (proc.stdout or '').strip().split('\n'):
                    if line.strip():
                        self.log(f"  {line.strip()}")
                if proc.stderr:
                    for line in proc.stderr.strip().split('\n'):
                        if line.strip():
                            self.log(f"  {line.strip()}", "orange")

            # 2. 更新 ffmpeg + ffprobe
            ff_path = os.path.join(self.bin_folder, "ffmpeg.exe")
            fp_path = os.path.join(self.bin_folder, "ffprobe.exe")

            need_ffmpeg = not os.path.exists(ff_path)
            need_ffprobe = not os.path.exists(fp_path)

            if need_ffmpeg or need_ffprobe:
                target_names = []
                if need_ffmpeg:
                    target_names.append("ffmpeg")
                if need_ffprobe:
                    target_names.append("ffprobe")
                self.log(f"下載 {', '.join(target_names)} (這可能需要一點時間)...")

                url = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
                with urllib.request.urlopen(url) as resp:
                    z = zipfile.ZipFile(BytesIO(resp.read()))
                    for n in z.namelist():
                        if need_ffmpeg and n.endswith("bin/ffmpeg.exe"):
                            with z.open(n) as s, open(ff_path, "wb") as t:
                                shutil.copyfileobj(s, t)
                            self.log("  ✓ ffmpeg.exe 已更新", "green")
                        elif need_ffprobe and n.endswith("bin/ffprobe.exe"):
                            with z.open(n) as s, open(fp_path, "wb") as t:
                                shutil.copyfileobj(s, t)
                            self.log("  ✓ ffprobe.exe 已更新", "green")
            else:
                self.log("ffmpeg 和 ffprobe 已存在，跳過下載")

            self.log("=== 更新完成！ ===", "green")
            self.refresh_versions()
        except Exception as e:
            self.log(f"更新失敗: {e}", "red")
        finally:
            self.is_task_running = False
            self.root.after(0, lambda: self.set_status("就緒"))

    def refresh_versions(self):
        def _check():
            yt_ver = self._get_ver(os.path.join(self.bin_folder, "yt-dlp.exe"), "--version")
            ff_ver = self._get_ver(os.path.join(self.bin_folder, "ffmpeg.exe"), "-version")
            fp_ver = self._get_ver(os.path.join(self.bin_folder, "ffprobe.exe"), "-version")
            self.ver_label.config(
                text=f"yt-dlp: {yt_ver} | ffmpeg: {ff_ver} | ffprobe: {fp_ver}"
            )

        threading.Thread(target=_check, daemon=True).start()

    def _get_ver(self, path, arg):
        if not os.path.exists(path):
            return "未安裝"
        try:
            r = subprocess.run(
                [path, arg], capture_output=True, text=True, creationflags=0x08000000
            )
            line = r.stdout.split('\n')[0].strip()
            if "ffmpeg" in line.lower() or "ffprobe" in line.lower():
                return line.split()[2]
            return line
        except Exception:
            return "未知"


if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()