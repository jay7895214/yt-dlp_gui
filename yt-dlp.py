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
import uuid
import time
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
    "max_concurrent": 2,
    "auto_retry_enable": False,
    "auto_retry_interval": 30,
    "auto_retry_max": 3,
}


class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Universal Downloader (YouTube/Podcast) v1.5.1")
        self.root.geometry("1150x850")
        self.root.minsize(950, 600)

        self.is_analyzing = False
        self.is_updating = False

        self.task_queue = []
        self.active_tasks = {}
        self.task_widgets = {}
        self.all_tasks = {}

        self.bin_folder = os.path.join(os.getcwd(), "bin")
        os.makedirs(self.bin_folder, exist_ok=True)

        self.config = self._load_config()

        self.setup_menu()
        self.setup_ui()
        self.refresh_versions()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _get_config_path(self):
        return os.path.join(os.getcwd(), CONFIG_FILE)

    def _load_config(self):
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
        try:
            self.config['max_concurrent'] = int(self.max_concurrent_var.get())
        except:
            self.config['max_concurrent'] = 2
            
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
            "max_concurrent": self.config['max_concurrent'],
            "auto_retry_enable": self.auto_retry_enable_var.get(),
            "auto_retry_interval": int(self.auto_retry_interval_entry.get()),
            "auto_retry_max": int(self.auto_retry_max_entry.get()),
        }
        try:
            with open(self._get_config_path(), 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _on_close(self):
        self._save_config()
        self.root.destroy()

    def setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="檢查並更新組件", command=self.start_update_tools)

    def setup_ui(self):
        cfg = self.config

        self.main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True)
        
        self.left_frame = tk.Frame(self.main_pane)
        self.right_frame = tk.Frame(self.main_pane)
        
        self.main_pane.add(self.left_frame, minsize=650, stretch="always")
        self.main_pane.add(self.right_frame, minsize=350, stretch="never")

        # ================= LEFT FRAME =================
        url_frame = tk.Frame(self.left_frame)
        url_frame.pack(pady=(10, 5), padx=10, fill=tk.X)

        tk.Label(url_frame, text="URL (影片/RSS/播放清單):", font=("Arial", 10)).pack(anchor="w")
        self.url_entry = tk.Text(url_frame, height=3, wrap=tk.WORD)
        self.url_entry.pack(fill=tk.X, pady=5)

        btn_frame = tk.Frame(self.left_frame)
        btn_frame.pack(pady=5, padx=10, fill=tk.X)

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

        tk.Label(btn_frame, text="最大同時下載數:", font=("Arial", 9)).pack(side=tk.LEFT, padx=(20, 5))
        self.max_concurrent_var = tk.StringVar(value=str(cfg.get("max_concurrent", 2)))
        cb = ttk.Combobox(btn_frame, textvariable=self.max_concurrent_var, values=[str(i) for i in range(1, 11)], width=3, state="readonly")
        cb.pack(side=tk.LEFT)
        cb.bind("<<ComboboxSelected>>", lambda e: self._check_queue())

        options_frame = tk.LabelFrame(self.left_frame, text="下載選項", padx=10, pady=5)
        options_frame.pack(pady=5, padx=10, fill=tk.X)

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

        retry_frame = tk.Frame(options_frame)
        retry_frame.pack(fill=tk.X, pady=3)
        self.auto_retry_enable_var = tk.BooleanVar(value=cfg.get("auto_retry_enable", False))
        tk.Checkbutton(retry_frame, text="自動重試 (403/網路錯誤)", variable=self.auto_retry_enable_var, command=self._toggle_retry_state).pack(side=tk.LEFT)
        tk.Label(retry_frame, text="間隔:").pack(side=tk.LEFT, padx=(10, 2))
        self.auto_retry_interval_entry = tk.Entry(retry_frame, width=4)
        self.auto_retry_interval_entry.pack(side=tk.LEFT)
        self.auto_retry_interval_entry.insert(0, str(cfg.get("auto_retry_interval", 30)))
        tk.Label(retry_frame, text="秒").pack(side=tk.LEFT, padx=(2, 5))
        tk.Label(retry_frame, text="最多:").pack(side=tk.LEFT, padx=(5, 2))
        self.auto_retry_max_entry = tk.Entry(retry_frame, width=3)
        self.auto_retry_max_entry.pack(side=tk.LEFT)
        self.auto_retry_max_entry.insert(0, str(cfg.get("auto_retry_max", 3)))
        tk.Label(retry_frame, text="次").pack(side=tk.LEFT, padx=(2, 0))

        path_frame = tk.Frame(options_frame)
        path_frame.pack(fill=tk.X, pady=3)
        tk.Label(path_frame, text="儲存位置:").pack(side=tk.LEFT)
        self.path_entry = tk.Entry(path_frame)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.path_entry.insert(0, cfg["save_path"])
        tk.Button(path_frame, text="瀏覽", command=self.browse_folder).pack(side=tk.LEFT)

        fmt_frame = tk.Frame(options_frame)
        fmt_frame.pack(fill=tk.X, pady=3)
        tk.Label(fmt_frame, text="影片格式:").pack(side=tk.LEFT)
        self.format_var = tk.StringVar(value=cfg["format"])
        for text, val in [("最佳畫質", "best"), ("1080p", "1080"), ("720p", "720"),
                          ("480p", "480"), ("僅音訊", "audio")]:
            tk.Radiobutton(fmt_frame, text=text, variable=self.format_var, value=val).pack(side=tk.LEFT, padx=4)

        container_frame = tk.Frame(options_frame)
        container_frame.pack(fill=tk.X, pady=3)
        tk.Label(container_frame, text="容器格式:").pack(side=tk.LEFT)
        self.container_var = tk.StringVar(value=cfg["container"])
        for text, val in [("自動 (最佳)", "auto"), ("MP4 偏好", "mp4"), ("WebM 偏好", "webm")]:
            tk.Radiobutton(container_frame, text=text, variable=self.container_var, value=val).pack(side=tk.LEFT, padx=4)

        sub_frame = tk.Frame(options_frame)
        sub_frame.pack(fill=tk.X, pady=3)
        self.write_subs_var = tk.BooleanVar(value=cfg["write_subs"])
        tk.Checkbutton(sub_frame, text="下載字幕", variable=self.write_subs_var).pack(side=tk.LEFT)
        self.auto_subs_var = tk.BooleanVar(value=cfg["auto_subs"])
        tk.Checkbutton(sub_frame, text="含自動產生字幕", variable=self.auto_subs_var).pack(side=tk.LEFT, padx=(10, 0))
        self.embed_subs_var = tk.BooleanVar(value=cfg["embed_subs"])
        tk.Checkbutton(sub_frame, text="嵌入字幕至影片", variable=self.embed_subs_var).pack(side=tk.LEFT, padx=(10, 0))

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

        self.log_text = scrolledtext.ScrolledText(self.left_frame, height=10, state='disabled')
        self.log_text.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        for color in ("red", "green", "blue", "orange", "purple", "black", "gray"):
            self.log_text.tag_configure(color, foreground=color)

        ver_frame = tk.Frame(self.left_frame)
        ver_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        self.ver_label = tk.Label(ver_frame, text="偵測版本中...", font=("Arial", 8), fg="gray")
        self.ver_label.pack(side=tk.RIGHT)

        # ================= RIGHT FRAME (Task Center) =================
        task_label = tk.Label(self.right_frame, text="📋 下載任務中心", font=("Arial", 11, "bold"), bg="#e0e0e0", pady=5)
        task_label.pack(fill=tk.X)

        global_ctrl_frame = tk.Frame(self.right_frame, bg="#e0e0e0")
        global_ctrl_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Button(global_ctrl_frame, text="🔄 全部重試", command=self.retry_all_tasks, font=("Arial", 9), padx=5).pack(side=tk.LEFT, padx=(10, 5))
        tk.Button(global_ctrl_frame, text="⏹ 全部停止", command=self.cancel_all_tasks, font=("Arial", 9), padx=5).pack(side=tk.LEFT, padx=5)

        self.task_canvas = tk.Canvas(self.right_frame)
        self.task_scrollbar = ttk.Scrollbar(self.right_frame, orient="vertical", command=self.task_canvas.yview)
        self.task_inner_frame = tk.Frame(self.task_canvas)

        self.task_inner_frame.bind(
            "<Configure>",
            lambda e: self.task_canvas.configure(scrollregion=self.task_canvas.bbox("all"))
        )

        self.task_window = self.task_canvas.create_window((0, 0), window=self.task_inner_frame, anchor="nw", width=330)
        self.task_canvas.configure(yscrollcommand=self.task_scrollbar.set)
        
        self.task_canvas.bind(
            "<Configure>",
            lambda e: self.task_canvas.itemconfig(self.task_window, width=e.width)
        )

        self.task_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.task_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._toggle_split_state()
        self._toggle_crop_state()
        self._toggle_retry_state()

    def log(self, msg, color="black"):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"{msg}\n", color)
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update_idletasks()

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

    def _toggle_retry_state(self):
        state = tk.NORMAL if self.auto_retry_enable_var.get() else tk.DISABLED
        self.auto_retry_interval_entry.config(state=state)
        self.auto_retry_max_entry.config(state=state)

    def browse_folder(self):
        d = filedialog.askdirectory()
        if d:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, d)

    def get_yt_dlp_cmd(self):
        bin_exe = os.path.join(self.bin_folder, "yt-dlp.exe")
        if os.path.exists(bin_exe):
            return bin_exe
        if os.path.exists("yt-dlp.exe"):
            return "yt-dlp.exe"
        return "yt-dlp"

    def check_tools_ready(self):
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
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return si

    def _get_subprocess_env(self):
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        return env

    def _build_format_arg(self):
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
        args = []
        need_write = self.write_subs_var.get()
        need_auto = self.auto_subs_var.get()
        need_embed = self.embed_subs_var.get()
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
        if not hasattr(self, 'crop_enable_var') or not self.crop_enable_var.get():
            return []
        start_time = self.crop_start_entry.get().strip()
        end_time = self.crop_end_entry.get().strip()
        s = start_time if start_time else "0"
        e = end_time if end_time else "inf"
        return ["--download-sections", f"*{s}-{e}", "--force-keyframes-at-cuts"]

    def _set_buttons_busy(self, busy=True):
        if busy:
            self.analyze_btn.config(state=tk.DISABLED)
            self.download_btn.config(state=tk.DISABLED)
        else:
            self.analyze_btn.config(state=tk.NORMAL)
            self.download_btn.config(state=tk.NORMAL)

    # ======================== 解析 ========================
    def start_analyze(self):
        if self.is_analyzing:
            return
        url = self.url_entry.get("1.0", tk.END).strip()
        if not url:
            return messagebox.showerror("錯誤", "請輸入 URL")

        exe = self.check_tools_ready()
        if not exe:
            return

        self.is_analyzing = True
        self._set_buttons_busy(True)
        threading.Thread(target=self.run_analyze, args=(exe, url), daemon=True).start()

    def run_analyze(self, exe, url):
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
                entries = data['entries']
                title = data.get('title', '未知列表')
                self.log(f"✓ 偵測到播放清單: {title}，共 {len(entries)} 個項目", "green")
                self.root.after(0, lambda: self._finish_analyze_playlist(title, entries, exe))
            else:
                self.log("✓ 偵測到單一影片，正在取得詳細資訊...", "green")
                self._run_detailed_analyze(exe, url)
        except Exception as e:
            self.log(f"解析失敗: {e}", "red")
            self.root.after(0, lambda: self._set_buttons_busy(False))
            self.is_analyzing = False

    def _finish_analyze_playlist(self, title, entries, exe):
        self._set_buttons_busy(False)
        self.is_analyzing = False
        self.show_playlist_window(title, entries, exe)

    def _run_detailed_analyze(self, exe, url):
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
            self.root.after(0, lambda: self._set_buttons_busy(False))
            self.is_analyzing = False

    def _finish_detailed_analyze(self, data, exe):
        self._set_buttons_busy(False)
        self.is_analyzing = False
        self.show_video_detail_window(data, exe)

    # ======================== 播放清單 ========================
    def show_playlist_window(self, title, entries, exe):
        top = tk.Toplevel(self.root)
        top.title(f"播放清單 - {title}")
        top.geometry("850x600")
        top.minsize(700, 400)

        ctrl_frame = tk.Frame(top, pady=10)
        ctrl_frame.pack(fill=tk.X, padx=10)
        tk.Label(ctrl_frame, text=f"共找到 {len(entries)} 個項目", font=("Arial", 10, "bold")).pack(side=tk.LEFT)

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

        items_map = {}
        for idx, entry in enumerate(entries, 1):
            date_str = entry.get('upload_date', '----')
            if len(date_str) == 8:
                date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
            dur = entry.get('duration')
            dur_str = str(datetime.timedelta(seconds=int(dur))) if dur else "--:--"
            item_id = tree.insert("", "end", values=(idx, date_str, entry.get('title', '未知'), dur_str))
            items_map[item_id] = entry

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
            selected_ids = tree.selection()
            if not selected_ids:
                return messagebox.showwarning("提示", "未選擇任何項目")
            if len(selected_ids) > 1:
                return messagebox.showwarning("提示", "詳細解析一次只能選擇一個影片\n請只選取一個項目")
            entry = items_map[selected_ids[0]]
            u = entry.get('url') or entry.get('webpage_url')
            if u:
                self.is_analyzing = True
                self._set_buttons_busy(True)
                threading.Thread(target=self._run_detailed_analyze, args=(exe, u), daemon=True).start()

        tk.Button(btn_frame, text="全選", command=select_all).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="全不選", command=select_none).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🔍 解析選取影片 (單個)", command=do_analyze_selected, bg="#2196F3", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="⬇️ 快速下載選取項目", command=do_quick_download, bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=5)

    # ======================== 影片詳情 ========================
    def show_video_detail_window(self, data, exe):
        top = tk.Toplevel(self.root)
        top.title(f"影片詳情 - {data.get('title', '未知')}")
        top.geometry("900x700")
        top.minsize(750, 500)

        info_frame = tk.LabelFrame(top, text="影片資訊", padx=10, pady=5)
        info_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        v_title = data.get('title', '未知')
        uploader = data.get('uploader', '未知')
        duration = data.get('duration')
        dur_str = str(datetime.timedelta(seconds=int(duration))) if duration else "--:--"
        upload_date = data.get('upload_date', '----')
        if len(upload_date) == 8:
            upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"

        tk.Label(info_frame, text=f"標題: {v_title}", font=("Arial", 11, "bold"), wraplength=850, anchor="w", justify="left").pack(anchor="w")
        tk.Label(info_frame, text=f"上傳者: {uploader}  |  時長: {dur_str}  |  日期: {upload_date}", font=("Arial", 9)).pack(anchor="w")

        notebook = ttk.Notebook(top)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        fmt_tab = tk.Frame(notebook)
        notebook.add(fmt_tab, text="📹 影片格式")
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
            item_id = fmt_tree.insert("", "end", values=(fid, ext, res, fps_str, vcodec, acodec, size_str, note))
            format_map[item_id] = f

        fmt_btn_frame = tk.Frame(fmt_tab, pady=5)
        fmt_btn_frame.pack(fill=tk.X, padx=5)

        def do_download_selected_format():
            selected = fmt_tree.selection()
            if not selected:
                return messagebox.showwarning("提示", "請先在上方選取一個影片格式")
            url = data.get('webpage_url') or data.get('original_url', '')
            if not url:
                return messagebox.showerror("錯誤", "找不到影片 URL")
            f = format_map[selected[0]]
            format_arg = f.get('format_id')
            if f.get('acodec') in ('none', None) and f.get('vcodec') not in ('none', None):
                format_arg = f"{format_arg}+bestaudio"
            top.destroy()
            self.add_task(url, v_title, format_id=format_arg, subtitle_args=[])

        tk.Button(fmt_btn_frame, text="⬇️ 下載選取格式", command=do_download_selected_format, bg="#FF9800", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

        sub_tab = tk.Frame(notebook)
        notebook.add(sub_tab, text="📝 字幕")
        sub_tree_frame = tk.Frame(sub_tab)
        sub_tree_frame.pack(fill=tk.BOTH, expand=True)
        sub_columns = ("type", "lang", "name", "formats")
        sub_tree = ttk.Treeview(sub_tree_frame, columns=sub_columns, show="headings", selectmode="extended")
        for col, heading, width in [("type", "類型", 120), ("lang", "語言代碼", 100), ("name", "語言名稱", 200), ("formats", "可用格式", 300)]:
            sub_tree.heading(col, text=heading)
            sub_tree.column(col, width=width)
        sub_tree.column("type", anchor="center")
        sub_tree.column("lang", anchor="center")
        sub_scroll = ttk.Scrollbar(sub_tree_frame, orient=tk.VERTICAL, command=sub_tree.yview)
        sub_tree.configure(yscroll=sub_scroll.set)
        sub_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sub_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        sub_items_map = {}
        subtitles = data.get('subtitles', {})
        for lang, subs in sorted(subtitles.items()):
            if not subs: continue
            name = subs[0].get('name', '') if subs else ''
            fmts = ', '.join(sorted(set(s.get('ext', '?') for s in subs)))
            iid = sub_tree.insert("", "end", values=("✋ 手動上傳", lang, name, fmts))
            sub_items_map[iid] = {"type": "manual", "lang": lang}

        auto_captions = data.get('automatic_captions', {})
        for lang, subs in sorted(auto_captions.items()):
            if not subs: continue
            name = subs[0].get('name', '') if subs else ''
            fmts = ', '.join(sorted(set(s.get('ext', '?') for s in subs)))
            iid = sub_tree.insert("", "end", values=("🤖 自動產生", lang, name, fmts))
            sub_items_map[iid] = {"type": "auto", "lang": lang}

        sub_btn_frame = tk.Frame(sub_tab, pady=5)
        sub_btn_frame.pack(fill=tk.X, padx=5)

        def do_download_selected_subs():
            selected = sub_tree.selection()
            if not selected:
                return messagebox.showwarning("提示", "請先在上方選取要下載的字幕")
            url = data.get('webpage_url') or data.get('original_url', '')
            if not url:
                return messagebox.showerror("錯誤", "找不到影片 URL")
            manual_langs, auto_langs = [], []
            for iid in selected:
                info = sub_items_map[iid]
                if info["type"] == "manual": manual_langs.append(info["lang"])
                else: auto_langs.append(info["lang"])
            sub_args = ["--skip-download"]
            if manual_langs: sub_args.append("--write-subs")
            if auto_langs: sub_args.append("--write-auto-subs")
            all_langs = list(dict.fromkeys(manual_langs + auto_langs))
            sub_args.extend(["--sub-langs", ",".join(all_langs)])
            sub_fmt = self.sub_format_var.get()
            if sub_fmt: sub_args.extend(["--convert-subs", sub_fmt])
            top.destroy()
            self.add_task(url, v_title, format_id=None, subtitle_args=sub_args)

        tk.Button(sub_btn_frame, text="📝 僅下載選取字幕", command=do_download_selected_subs, bg="#9C27B0", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

    # ======================== 任務與佇列管理 ========================
    def start_direct_download(self):
        url_text = self.url_entry.get("1.0", tk.END).strip()
        if not url_text:
            return messagebox.showerror("錯誤", "請輸入 URL")
        for line in url_text.split('\n'):
            line = line.strip()
            if line:
                self.add_task(line, line)

    def start_batch_download(self, targets):
        for title, url in targets:
            self.add_task(url, title)

    def add_task(self, url, title, format_id=None, subtitle_args=None):
        task_id = str(uuid.uuid4())
        task_info = {
            "id": task_id,
            "url": url,
            "title": title,
            "format_id": format_id,
            "subtitle_args": subtitle_args,
            "status": "等待中...",
            "process": None,
            "last_error": ""
        }
        self.all_tasks[task_id] = task_info
        self.task_queue.append(task_info)
        self.create_task_widget(task_info)
        self.log(f"已加入佇列: {title}")
        self._check_queue()

    def create_task_widget(self, task_info):
        frame = tk.Frame(self.task_inner_frame, bd=1, relief="solid", padx=5, pady=5, bg="#f9f9f9")
        frame.pack(fill=tk.X, pady=2, padx=2)

        display_title = task_info["title"][:45] + ("..." if len(task_info["title"]) > 45 else "")
        title_lbl = tk.Label(frame, text=display_title, font=("Arial", 9, "bold"), bg="#f9f9f9", anchor="w")
        title_lbl.pack(fill=tk.X)

        prog_var = tk.DoubleVar()
        prog_bar = ttk.Progressbar(frame, variable=prog_var, maximum=100)
        prog_bar.pack(fill=tk.X, pady=2)

        status_frame = tk.Frame(frame, bg="#f9f9f9")
        status_frame.pack(fill=tk.X)

        # Use grid layout to prevent buttons from being pushed off-screen
        status_frame.columnconfigure(0, weight=1)
        status_frame.columnconfigure(1, weight=0)
        status_frame.columnconfigure(2, weight=0)

        status_lbl = tk.Label(status_frame, text=task_info["status"], font=("Arial", 8), bg="#f9f9f9", fg="#555", anchor="w")
        status_lbl.grid(row=0, column=0, sticky="ew")

        retry_btn = tk.Button(status_frame, text="🔄", fg="blue", font=("Arial", 8), relief="flat", command=lambda: self.retry_task(task_info["id"]), state=tk.DISABLED)
        retry_btn.grid(row=0, column=1, padx=2)
        stop_btn = tk.Button(status_frame, text="⏹", fg="red", font=("Arial", 8), relief="flat", command=lambda: self.cancel_task(task_info["id"]))
        stop_btn.grid(row=0, column=2)

        self.task_widgets[task_info["id"]] = {
            "frame": frame,
            "title_lbl": title_lbl,
            "prog_var": prog_var,
            "prog_bar": prog_bar,
            "status_lbl": status_lbl,
            "stop_btn": stop_btn,
            "retry_btn": retry_btn
        }

    def update_task_ui(self, task_id, title=None, progress=None, status=None, indeterminate=None):
        if task_id not in self.task_widgets: return
        w = self.task_widgets[task_id]
        if title: w["title_lbl"].config(text=title[:45] + ("..." if len(title)>45 else ""))
        if progress is not None: w["prog_var"].set(progress)
        if status: w["status_lbl"].config(text=status[:60] + ("..." if len(status) > 60 else ""))
        if indeterminate is True:
            w["prog_bar"].config(mode="indeterminate")
            w["prog_bar"].start()
        elif indeterminate is False:
            w["prog_bar"].stop()
            w["prog_bar"].config(mode="determinate")

    def cancel_task(self, task_id):
        for i, t in enumerate(self.task_queue):
            if t["id"] == task_id:
                self.task_queue.pop(i)
                self.update_task_ui(task_id, status="已取消", progress=0)
                self.task_widgets[task_id]["stop_btn"].config(state=tk.DISABLED)
                self.task_widgets[task_id]["retry_btn"].config(state=tk.NORMAL)
                return
        if task_id in self.active_tasks:
            t = self.active_tasks[task_id]
            if t["process"]:
                try:
                    if sys.platform == 'win32':
                        subprocess.call(['taskkill', '/F', '/T', '/PID', str(t["process"].pid)], startupinfo=self._get_startupinfo())
                    else:
                        t["process"].terminate()
                except:
                    pass
            self.update_task_ui(task_id, status="正在停止...")
            self.task_widgets[task_id]["retry_btn"].config(state=tk.NORMAL)

    def retry_task(self, task_id):
        if task_id not in self.all_tasks: return
        task = self.all_tasks[task_id]
        if task["id"] in [t["id"] for t in self.task_queue] or task["id"] in self.active_tasks: return
        task["status"] = "等待中..."
        task["process"] = None
        task["last_error"] = ""
        self.task_queue.append(task)
        self.update_task_ui(task_id, status="等待中...", progress=0)
        self.task_widgets[task_id]["stop_btn"].config(state=tk.NORMAL)
        self.task_widgets[task_id]["retry_btn"].config(state=tk.DISABLED)
        self._check_queue()
        
    def retry_all_tasks(self):
        for task_id, w in self.task_widgets.items():
            if w["retry_btn"]["state"] == tk.NORMAL:
                self.retry_task(task_id)
                
    def cancel_all_tasks(self):
        for t in list(self.task_queue):
            self.cancel_task(t["id"])
        for task_id in list(self.active_tasks.keys()):
            self.cancel_task(task_id)

    def _check_queue(self):
        try:
            max_c = int(self.max_concurrent_var.get())
        except:
            max_c = 2

        while len(self.active_tasks) < max_c and self.task_queue:
            task = self.task_queue.pop(0)
            self.active_tasks[task["id"]] = task
            self.update_task_ui(task["id"], status="開始下載...")
            threading.Thread(target=self._run_task, args=(task,), daemon=True).start()

    def _run_task(self, task):
        exe = self.check_tools_ready()
        if not exe:
            self.root.after(0, lambda: self.update_task_ui(task["id"], status="錯誤：找不到核心套件"))
            self.active_tasks.pop(task["id"], None)
            return

        save_path = self.path_entry.get()
        cmd = [
            exe, "--ffmpeg-location", self.bin_folder, "--ignore-config", "--no-part", "--embed-metadata",
            "-P", save_path, "-o", "%(upload_date)s_%(title)s.%(ext)s",
            "--print", "after_move:filepath",
        ]

        is_sub_only = task.get("subtitle_args") and "--skip-download" in task["subtitle_args"]
        if task.get("format_id"): cmd.extend(["-f", task["format_id"]])
        elif not is_sub_only: cmd.extend(["-f", self._build_format_arg()])
        
        if task.get("subtitle_args") is not None: cmd.extend(task["subtitle_args"])
        else: cmd.extend(self._build_subtitle_args())
        
        if not is_sub_only: cmd.extend(self._build_section_args())
        
        cmd.append(task["url"])

        # Capture split options on the main thread context (they're already read here on the worker thread,
        # but we capture them as local vars to avoid further Tkinter access in process_split)
        split_enabled = self.split_enable_var.get() if not is_sub_only else False
        split_mode = self.split_mode_var.get()
        split_time_str = self.split_time_entry.get().strip()
        split_parts_str = self.split_parts_entry.get().strip()
        split_delete_original = self.split_delete_original_var.get()

        # Capture auto-retry options
        auto_retry_enabled = self.auto_retry_enable_var.get()
        try:
            auto_retry_interval = int(self.auto_retry_interval_entry.get())
        except:
            auto_retry_interval = 30
        try:
            auto_retry_max = int(self.auto_retry_max_entry.get())
        except:
            auto_retry_max = 3

        is_livestream = False
        final_filepath = None
        retry_count = 0

        while True:  # Auto-retry loop
            try:
                task["process"] = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding='utf-8', errors='replace',
                    startupinfo=self._get_startupinfo(),
                    env=self._get_subprocess_env()
                )

                last_lines = []
                printed_filepath = None  # Captured from --print after_move:filepath
                for line in task["process"].stdout:
                    line = line.strip()
                    if not line: continue
                    last_lines.append(line)
                    if len(last_lines) > 5: last_lines.pop(0)
                    
                    if line.startswith("[download] Destination: "):
                        final_filepath = line.replace("[download] Destination: ", "").strip()
                    elif line.startswith("[Merger] Merging formats into "):
                        final_filepath = line.replace("[Merger] Merging formats into ", "").strip().strip('"')
                    elif line.startswith("[VideoRemuxer] Remuxing video from "):
                        final_filepath = line.split(' to ')[-1].strip().strip('"')
                    elif line.startswith("[ExtractAudio] Destination: "):
                        final_filepath = line.replace("[ExtractAudio] Destination: ", "").strip()
                    elif line.startswith("[download] ") and "has already been downloaded" in line:
                        final_filepath = line.split("[download] ")[1].split(" has already")[0].strip()
                    # Capture --print after_move:filepath output (lines without [] prefix are print output)
                    elif not line.startswith("[") and not line.startswith("ERROR") and os.path.sep in line:
                        candidate = line.strip()
                        if os.path.splitext(candidate)[1]:  # Has file extension
                            printed_filepath = candidate

                    if "size=" in line and "time=" in line and "bitrate=" in line:
                        if not is_livestream:
                            is_livestream = True
                            self.root.after(0, lambda t=task["id"]: self.update_task_ui(t, indeterminate=True))
                        match = re.search(r'size=\s*(.*?)\s+time=(.*?)\s+bitrate=.*?speed=\s*(.*?)x', line)
                        if match:
                            size, time_str, speed = match.group(1).strip(), match.group(2).strip(), match.group(3).strip()
                            self.root.after(0, lambda t=task["id"], s=f"已下載 {size} | {speed}x | {time_str}": self.update_task_ui(t, status=s))
                    elif "[download]" in line and "at" in line and "%" not in line and "MiB" in line:
                        if not is_livestream:
                            is_livestream = True
                            self.root.after(0, lambda t=task["id"]: self.update_task_ui(t, indeterminate=True))
                        match = re.search(r'\[download\]\s+(.*?)\s+at\s+(.*?)\s+\((.*?)\)', line)
                        if match:
                            size, speed, time_str = match.group(1), match.group(2), match.group(3)
                            self.root.after(0, lambda t=task["id"], s=f"已下載 {size} | {speed} | {time_str}": self.update_task_ui(t, status=s))
                    elif "[download]" in line and "%" in line:
                        if is_livestream:
                            is_livestream = False
                            self.root.after(0, lambda t=task["id"]: self.update_task_ui(t, indeterminate=False))
                        match = re.search(r'(\d+\.?\d*)%', line)
                        if match:
                            pct = float(match.group(1))
                            self.root.after(0, lambda t=task["id"], p=pct: self.update_task_ui(t, progress=p, status=f"下載中: {p:.1f}%"))

                task["process"].wait()
                if is_livestream:
                    self.root.after(0, lambda t=task["id"]: self.update_task_ui(t, indeterminate=False))

                # Prefer --print filepath over parsed log lines
                if printed_filepath:
                    final_filepath = printed_filepath

                if task["process"].returncode == 0:
                    # If splitting is enabled, do it BEFORE reporting complete
                    if final_filepath and split_enabled:
                        self.root.after(0, lambda t=task["id"]: self.update_task_ui(t, progress=100, status="分割中..."))
                        self.log(f"開始分割影片: {os.path.basename(final_filepath)}")
                        self.process_split(task["id"], final_filepath, split_mode, split_time_str, split_parts_str, split_delete_original)
                    self.root.after(0, lambda t=task["id"]: self.update_task_ui(t, progress=100, status="完成"))
                    self.log(f"✓ 任務完成: {task['title']}", "green")
                    break  # Success — exit retry loop
                else:
                    err_msg = last_lines[-1] if last_lines else "失敗或已停止"
                    task["last_error"] = err_msg

                    # Check if we should auto-retry (403 / network errors)
                    is_retryable = auto_retry_enabled and retry_count < auto_retry_max and (
                        "403" in err_msg or "Forbidden" in err_msg or
                        "HTTP Error" in err_msg or "URLError" in err_msg or
                        "timed out" in err_msg.lower() or "connection" in err_msg.lower()
                    )

                    if is_retryable:
                        retry_count += 1
                        wait_sec = auto_retry_interval
                        self.log(f"任務失敗 ({task['title']}): {err_msg}，{wait_sec} 秒後自動重試 ({retry_count}/{auto_retry_max})...", "orange")
                        for remaining in range(wait_sec, 0, -1):
                            self.root.after(0, lambda t=task["id"], r=remaining, rc=retry_count, mx=auto_retry_max:
                                self.update_task_ui(t, status=f"重試 {rc}/{mx}，等待 {r} 秒..."))
                            time.sleep(1)
                            # Check if task was cancelled during wait
                            if task["id"] not in self.active_tasks:
                                break
                        if task["id"] not in self.active_tasks:
                            break  # Task was cancelled
                        self.root.after(0, lambda t=task["id"], rc=retry_count, mx=auto_retry_max:
                            self.update_task_ui(t, status=f"重試中 ({rc}/{mx})...", progress=0))
                        continue  # Retry the download
                    else:
                        self.root.after(0, lambda t=task["id"], msg=err_msg: self.update_task_ui(t, status=f"失敗: {msg}"))
                        self.log(f"任務失敗 ({task['title']}): {err_msg}", "red")
                        break  # No retry — exit loop

            except Exception as e:
                self.root.after(0, lambda t=task["id"], err=e: self.update_task_ui(t, status=f"錯誤: {err}"))
                self.log(f"任務錯誤 ({task['title']}): {e}", "red")
                break  # Exit retry loop on exception

        # Cleanup (runs after retry loop exits)
        self.root.after(0, lambda t=task["id"]: self.task_widgets[t]["stop_btn"].config(state=tk.DISABLED))
        self.root.after(0, lambda t=task["id"]: self.task_widgets[t]["retry_btn"].config(state=tk.NORMAL if task.get("last_error") else tk.DISABLED))
        task["process"] = None
        if task["id"] in self.active_tasks:
            self.active_tasks.pop(task["id"])
        self.root.after(0, self._check_queue)

    def process_split(self, task_id, filepath, mode, split_time_str, split_parts_str, delete_original):
        """Split a video file using FFmpeg. All parameters are passed in to avoid
        thread-unsafe Tkinter variable access."""
        # --- 穩健的檔案定位機制 ---
        # 步驟 1：等待檔案出現（最多等待 10 秒，每 0.5 秒檢查一次）
        if not os.path.exists(filepath):
            self.log(f"等待檔案寫入完成: {os.path.basename(filepath)}", "orange")
            for _ in range(20):  # 20 次 × 0.5 秒 = 最多 10 秒
                time.sleep(0.5)
                if os.path.exists(filepath):
                    break

        # 步驟 2：如果檔案仍然不存在，嘗試在同目錄下用檔名模糊搜尋
        if not os.path.exists(filepath):
            import glob
            directory = os.path.dirname(filepath)
            basename_no_ext = os.path.splitext(os.path.basename(filepath))[0]
            
            escaped_dir = glob.escape(directory)
            escaped_basename = glob.escape(basename_no_ext)
            search_pattern = os.path.join(escaped_dir, f"{escaped_basename}.*")
            
            # 搜尋同名但不同副檔名的檔案（排除已分割的 _partXXX 檔案）
            candidates = []
            for f in glob.glob(search_pattern):
                # 排除 _partXXX 結尾的檔案（那些是之前分割產生的）
                fname_no_ext = os.path.splitext(os.path.basename(f))[0]
                if re.search(r'_part\d+$', fname_no_ext):
                    continue
                candidates.append(f)
            
            if len(candidates) == 1:
                filepath = candidates[0]
                self.log(f"已找到替代檔案: {os.path.basename(filepath)}", "orange")
            elif len(candidates) > 1:
                # 多個候選：優先選擇影片檔案（按常見影片副檔名排序）
                video_exts = ['.mp4', '.mkv', '.webm', '.avi', '.mov', '.flv', '.m4a', '.opus', '.mp3']
                candidates.sort(key=lambda x: (
                    video_exts.index(os.path.splitext(x)[1].lower())
                    if os.path.splitext(x)[1].lower() in video_exts
                    else 999
                ))
                filepath = candidates[0]
                self.log(f"找到多個候選檔案，使用: {os.path.basename(filepath)}", "orange")
            else:
                self.log(f"分割失敗：找不到檔案 {filepath}", "red")
                return
        segment_time = 0
        total_duration = 0
        if mode == "time":
            try:
                parts = split_time_str.split(':')
                segment_time = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            except Exception as e:
                self.log(f"分割失敗：時間格式錯誤 '{split_time_str}'，請使用 HH:MM:SS 格式", "red")
                return
        elif mode == "parts":
            try:
                parts_count = int(split_parts_str)
                if parts_count <= 0:
                    self.log(f"分割失敗：分割數量必須大於 0", "red")
                    return
                fp_path = os.path.join(self.bin_folder, "ffprobe.exe")
                if not os.path.exists(fp_path): fp_path = "ffprobe"
                cmd = [fp_path, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filepath]
                proc = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
                total_duration = float(proc.stdout.strip())
                segment_time = int(total_duration / parts_count) + 1
                self.log(f"影片總長 {total_duration:.1f} 秒，分割為 {parts_count} 份（每份約 {segment_time} 秒）")
            except Exception as e:
                self.log(f"分割失敗：無法取得影片時長 ({e})", "red")
                return
        if segment_time <= 0:
            self.log(f"分割失敗：無效的分割時間 ({segment_time})", "red")
            return
        
        ff_path = os.path.join(self.bin_folder, "ffmpeg.exe")
        if not os.path.exists(ff_path): ff_path = "ffmpeg"
        base, ext = os.path.splitext(filepath)
        split_cmd = [
            ff_path, "-y", "-i", filepath,
            "-f", "segment", "-segment_time", str(segment_time),
            "-reset_timestamps", "1",
            "-c", "copy",
            f"{base}_part%03d{ext}"
        ]
        try:
            proc = subprocess.Popen(
                split_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', errors='replace',
                startupinfo=self._get_startupinfo()
            )

            # Read FFmpeg output line by line to avoid pipe deadlock and show progress
            if total_duration <= 0:
                # Try to get duration for progress calculation
                try:
                    fp_path2 = os.path.join(self.bin_folder, "ffprobe.exe")
                    if not os.path.exists(fp_path2): fp_path2 = "ffprobe"
                    dur_cmd = [fp_path2, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filepath]
                    dur_proc = subprocess.run(dur_cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
                    total_duration = float(dur_proc.stdout.strip())
                except:
                    total_duration = 0

            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                # Parse FFmpeg progress output (time= field)
                time_match = re.search(r'time=(\d+):(\d+):(\d+\.?\d*)', line)
                if time_match and total_duration > 0:
                    h, m, s = int(time_match.group(1)), int(time_match.group(2)), float(time_match.group(3))
                    current_time = h * 3600 + m * 60 + s
                    pct = min(99.0, (current_time / total_duration) * 100)
                    speed_match = re.search(r'speed=\s*(\S+)x', line)
                    speed_str = speed_match.group(1) if speed_match else "--"
                    self.root.after(0, lambda t=task_id, p=pct, sp=speed_str:
                        self.update_task_ui(t, progress=p, status=f"分割中: {p:.1f}% | {sp}x"))
                    self.log(f"  [FFmpeg 分割] {pct:.1f}% (speed: {speed_str}x)", "gray")
                elif "Opening" in line and "for writing" in line:
                    # FFmpeg logs each output segment file
                    seg_name = line.split("'")[1] if "'" in line else line
                    self.log(f"  [FFmpeg] 正在寫入: {os.path.basename(seg_name)}", "gray")

            proc.wait()

            if proc.returncode == 0:
                self.log(f"✓ 分割完成: {os.path.basename(filepath)}", "green")
                if delete_original:
                    try:
                        os.remove(filepath)
                        self.log(f"  已刪除原始檔案", "gray")
                    except Exception as e:
                        self.log(f"  無法刪除原始檔案: {e}", "orange")
            else:
                self.log(f"✗ 分割失敗 (FFmpeg 返回碼: {proc.returncode})", "red")
        except Exception as e:
            self.log(f"✗ 分割錯誤: {e}", "red")

    # ======================== 工具更新 ========================
    def start_update_tools(self):
        if self.is_updating: return messagebox.showwarning("忙碌中", "請等待更新結束")
        if messagebox.askyesno("更新", "確定要檢查並更新 yt-dlp 和 ffmpeg 嗎？"):
            self.is_updating = True
            threading.Thread(target=self.run_update, daemon=True).start()

    def run_update(self):
        try:
            self.log("=== 開始檢查更新 ===")
            yt_path = os.path.join(self.bin_folder, "yt-dlp.exe")
            if not os.path.exists(yt_path):
                self.log("下載 yt-dlp...")
                urllib.request.urlretrieve("https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe", yt_path)
            else:
                self.log("檢查 yt-dlp 更新...")
                subprocess.run([yt_path, "-U"], capture_output=True, text=True, creationflags=0x08000000)

            ff_path = os.path.join(self.bin_folder, "ffmpeg.exe")
            fp_path = os.path.join(self.bin_folder, "ffprobe.exe")
            if not os.path.exists(ff_path) or not os.path.exists(fp_path):
                self.log("下載 ffmpeg 和 ffprobe...")
                url = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
                with urllib.request.urlopen(url) as resp:
                    z = zipfile.ZipFile(BytesIO(resp.read()))
                    for n in z.namelist():
                        if n.endswith("bin/ffmpeg.exe"):
                            with z.open(n) as s, open(ff_path, "wb") as t: shutil.copyfileobj(s, t)
                        elif n.endswith("bin/ffprobe.exe"):
                            with z.open(n) as s, open(fp_path, "wb") as t: shutil.copyfileobj(s, t)
            self.log("=== 更新完成！ ===", "green")
            self.refresh_versions()
        finally:
            self.is_updating = False

    def refresh_versions(self):
        def _check():
            yt_ver = self._get_ver(os.path.join(self.bin_folder, "yt-dlp.exe"), "--version")
            ff_ver = self._get_ver(os.path.join(self.bin_folder, "ffmpeg.exe"), "-version")
            fp_ver = self._get_ver(os.path.join(self.bin_folder, "ffprobe.exe"), "-version")
            self.ver_label.config(text=f"yt-dlp: {yt_ver} | ffmpeg: {ff_ver} | ffprobe: {fp_ver}")
        threading.Thread(target=_check, daemon=True).start()

    def _get_ver(self, path, arg):
        if not os.path.exists(path): return "未安裝"
        try:
            r = subprocess.run([path, arg], capture_output=True, text=True, creationflags=0x08000000)
            line = r.stdout.split('\n')[0].strip()
            if "ffmpeg" in line.lower() or "ffprobe" in line.lower(): return line.split()[2]
            return line
        except: return "未知"


if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()
