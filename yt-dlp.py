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
from pathlib import Path
from io import BytesIO

class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Universal Downloader (YouTube/Podcast)")
        self.root.geometry("750x750")
        
        self.is_task_running = False # 統稱任務狀態 (下載或更新或解析中)
        self.stop_flag = False       # 用於停止批次下載
        
        # 設定 bin 資料夾路徑
        self.bin_folder = os.path.join(os.getcwd(), "bin")
        if not os.path.exists(self.bin_folder):
            os.makedirs(self.bin_folder)
            
        self.setup_menu()
        self.setup_ui()
        self.refresh_versions()
        
    def setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="檢查並更新組件", command=self.start_update_tools)
        
    def setup_ui(self):
        # URL 區塊
        url_frame = tk.Frame(self.root)
        url_frame.pack(pady=(10, 5), padx=10, fill=tk.X)
        
        tk.Label(url_frame, text="URL (影片/RSS/播放清單):", font=("Arial", 10)).pack(anchor="w")
        self.url_entry = tk.Text(url_frame, height=3, wrap=tk.WORD)
        self.url_entry.pack(fill=tk.X, pady=5)
        
        # 按鈕區塊 (分析 vs 直接下載)
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)
        
        self.analyze_btn = tk.Button(btn_frame, text="🔍 解析列表/Podcast", command=self.start_analyze, bg="#2196F3", fg="white", font=("Arial", 10, "bold"), padx=10)
        self.analyze_btn.pack(side=tk.LEFT, padx=10)
        
        self.download_btn = tk.Button(btn_frame, text="⬇️ 直接下載", command=self.start_direct_download, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), padx=10)
        self.download_btn.pack(side=tk.LEFT, padx=10)

        # 下載參數區
        options_frame = tk.LabelFrame(self.root, text="下載選項", padx=10, pady=5)
        options_frame.pack(pady=10, padx=10, fill=tk.X)
        
        # 時間區段
        time_frame = tk.Frame(options_frame)
        time_frame.pack(fill=tk.X, pady=5)
        tk.Label(time_frame, text="時間裁切 (秒):").pack(side=tk.LEFT)
        self.start_sec_entry = tk.Entry(time_frame, width=8)
        self.start_sec_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(time_frame, text="-").pack(side=tk.LEFT)
        self.end_sec_entry = tk.Entry(time_frame, width=8)
        self.end_sec_entry.pack(side=tk.LEFT, padx=5)
        
        # 路徑選擇
        path_frame = tk.Frame(options_frame)
        path_frame.pack(fill=tk.X, pady=5)
        tk.Label(path_frame, text="儲存位置:").pack(side=tk.LEFT)
        self.path_entry = tk.Entry(path_frame)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.path_entry.insert(0, str(Path.home() / "Downloads" / "Podcast_DL"))
        tk.Button(path_frame, text="瀏覽", command=self.browse_folder).pack(side=tk.LEFT)

        # 狀態與日誌
        self.status_label = tk.Label(self.root, text="就緒", fg="blue", font=("Arial", 10))
        self.status_label.pack(pady=5)
        
        self.log_text = scrolledtext.ScrolledText(self.root, height=15, state='disabled')
        self.log_text.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        
        # 版本資訊
        ver_frame = tk.Frame(self.root)
        ver_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        self.ver_label = tk.Label(ver_frame, text="偵測版本中...", font=("Arial", 8), fg="gray")
        self.ver_label.pack(side=tk.RIGHT)

    def log(self, msg, color="black"):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"{msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update_idletasks()

    def set_status(self, msg, color="blue"):
        self.status_label.config(text=msg, fg=color)

    def browse_folder(self):
        d = filedialog.askdirectory()
        if d:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, d)

    def get_yt_dlp_cmd(self):
        """取得 yt-dlp 執行檔路徑 (優先使用 bin 資料夾)"""
        bin_exe = os.path.join(self.bin_folder, "yt-dlp.exe")
        if os.path.exists(bin_exe): return bin_exe
        if os.path.exists("yt-dlp.exe"): return "yt-dlp.exe"
        return "yt-dlp" # 嘗試系統路徑

    def check_tools_ready(self):
        """檢查工具是否就緒，若無則提示下載"""
        exe = self.get_yt_dlp_cmd()
        # 簡單檢查
        try:
            subprocess.run([exe, "--version"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
            return exe
        except FileNotFoundError:
            if messagebox.askyesno("缺少組件", "找不到 yt-dlp，是否立即下載？"):
                self.start_update_tools()
            return None

    # ================= 核心功能 1: 解析列表 (Podcast/Playlist) =================
    def start_analyze(self):
        if self.is_task_running: return
        url = self.url_entry.get("1.0", tk.END).strip()
        if not url: return messagebox.showerror("錯誤", "請輸入 URL")
        
        exe = self.check_tools_ready()
        if not exe: return

        self.is_task_running = True
        self.set_status("正在解析 RSS/播放清單...", "orange")
        self.analyze_btn.config(state=tk.DISABLED)
        self.download_btn.config(state=tk.DISABLED)
        
        threading.Thread(target=self.run_analyze, args=(exe, url), daemon=True).start()

    def run_analyze(self, exe, url):
        try:
            self.log(f"開始解析: {url}")
            # 使用 --dump-single-json --flat-playlist 快速抓取列表而不下載
            cmd = [
                exe, 
                "--dump-single-json", 
                "--flat-playlist", 
                "--ignore-errors",
                url
            ]
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            process = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', startupinfo=startupinfo)
            
            if process.returncode != 0:
                raise Exception(process.stderr)

            data = json.loads(process.stdout)
            
            # 判斷是否為列表
            entries = []
            if 'entries' in data:
                entries = data['entries']
                title = data.get('title', '未知列表')
            else:
                # 可能是單一影片
                entries = [data]
                title = data.get('title', '單一影片')

            # 轉回主執行緒顯示選擇視窗
            self.root.after(0, lambda: self.show_selection_window(title, entries))

        except Exception as e:
            self.log(f"解析失敗: {e}", "red")
            self.set_status("解析失敗", "red")
        finally:
            self.is_task_running = False
            self.analyze_btn.config(state=tk.NORMAL)
            self.download_btn.config(state=tk.NORMAL)
            if self.status_label.cget("text") == "正在解析 RSS/播放清單...":
                 self.set_status("就緒", "blue")

    def show_selection_window(self, title, entries):
        top = tk.Toplevel(self.root)
        top.title(f"選擇下載內容 - {title}")
        top.geometry("800x600")
        
        # 頂部控制區
        ctrl_frame = tk.Frame(top, pady=10)
        ctrl_frame.pack(fill=tk.X, padx=10)
        
        tk.Label(ctrl_frame, text=f"共找到 {len(entries)} 個項目").pack(side=tk.LEFT)
        
        # Treeview 列表
        columns = ("chk", "date", "title", "duration")
        tree = ttk.Treeview(top, columns=columns, show="headings", selectmode="extended")
        
        tree.heading("chk", text="序號")
        tree.heading("date", text="發布日期")
        tree.heading("title", text="標題")
        tree.heading("duration", text="時長")
        
        tree.column("chk", width=50, anchor="center")
        tree.column("date", width=100, anchor="center")
        tree.column("title", width=500)
        tree.column("duration", width=80, anchor="center")
        
        scrollbar = ttk.Scrollbar(top, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 填充資料
        items_map = {} # 用來對應 tree item id 到真實資料
        for idx, entry in enumerate(entries, 1):
            # 處理日期
            date_str = entry.get('upload_date', '----')
            if len(date_str) == 8:
                date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
            
            # 處理時長
            dur = entry.get('duration')
            dur_str = str(datetime.timedelta(seconds=int(dur))) if dur else "--:--"
            
            item_id = tree.insert("", "end", values=(idx, date_str, entry.get('title'), dur_str))
            items_map[item_id] = entry

        # 底部按鈕
        btn_frame = tk.Frame(top, pady=10)
        btn_frame.pack(fill=tk.X)

        def select_all():
            for item in tree.get_children(): tree.selection_add(item)
            
        def select_none():
            tree.selection_remove(tree.get_children())
            
        def do_download():
            selected_ids = tree.selection()
            if not selected_ids:
                return messagebox.showwarning("提示", "未選擇任何項目")
            
            # 收集要下載的 URL
            target_urls = []
            for iid in selected_ids:
                entry = items_map[iid]
                # 優先使用 url (原始檔案位址) 若無則用 webpage_url
                u = entry.get('url') or entry.get('webpage_url')
                if u: target_urls.append((entry.get('title'), u))
            
            top.destroy()
            self.start_batch_download(target_urls)

        tk.Button(btn_frame, text="全選", command=select_all).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="全不選", command=select_none).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="下載選取項目", bg="#4CAF50", fg="white", command=do_download, font=("Arial", 11, "bold")).pack(side=tk.RIGHT, padx=10)

    # ================= 核心功能 2: 批次下載 =================
    def start_batch_download(self, targets):
        """targets: list of (title, url)"""
        exe = self.check_tools_ready()
        if not exe: return
        
        self.is_task_running = True
        self.stop_flag = False
        self.download_btn.config(state=tk.DISABLED, text="下載中...")
        self.analyze_btn.config(state=tk.DISABLED)
        
        threading.Thread(target=self.run_batch_download, args=(exe, targets), daemon=True).start()
        
    def start_direct_download(self):
        """舊有的直接下載功能 (單一連結)"""
        if self.is_task_running: return
        url = self.url_entry.get("1.0", tk.END).strip()
        if not url: return
        self.start_batch_download([("直接下載任務", url)])

    def run_batch_download(self, exe, targets):
        total = len(targets)
        save_path = self.path_entry.get()
        start_sec = self.start_sec_entry.get().strip()
        end_sec = self.end_sec_entry.get().strip()
        
        # 處理 section 字串
        section_cmd = []
        if start_sec or end_sec:
            try:
                s = start_sec if start_sec else "0"
                e = end_sec if end_sec else "inf"
                section_cmd = ["--download-sections", f"*{s}-{e}", "--force-keyframes-at-cuts"]
            except: pass

        self.log(f"=== 開始批次下載，共 {total} 個項目 ===", "blue")
        
        for i, (title, url) in enumerate(targets, 1):
            if self.stop_flag: 
                self.log("下載已手動停止", "red")
                break
                
            self.set_status(f"正在下載 ({i}/{total}): {title[:30]}...", "orange")
            self.log(f"[{i}/{total}] 處理中: {title}")
            
            cmd = [
                exe,
                "--ffmpeg-location", self.bin_folder, # 指定 ffmpeg 位置
                "--ignore-config",
                "--no-part",
                "-P", save_path,
                "-o", "%(upload_date)s_%(title)s.%(ext)s", # 檔名格式
                url
            ] + section_cmd
            
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                      text=True, encoding='utf-8', errors='replace', startupinfo=startupinfo)
                
                for line in proc.stdout:
                    if "[download]" in line and "%" in line:
                        # 簡化進度條顯示，避免 log 刷太快
                        pass 
                    elif "ERROR" in line:
                        self.log(line.strip(), "red")
                
                proc.wait()
                if proc.returncode == 0:
                    self.log(f"✓ 完成: {title}", "green")
                else:
                    self.log(f"✗ 失敗: {title}", "red")
                    
            except Exception as e:
                self.log(f"執行錯誤: {e}", "red")

        self.is_task_running = False
        self.set_status("任務結束", "blue")
        self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL, text="直接下載"))
        self.root.after(0, lambda: self.analyze_btn.config(state=tk.NORMAL))
        messagebox.showinfo("完成", "所有排程任務已結束")

    # ================= 工具與更新 (整合 v3 功能) =================
    def start_update_tools(self):
        if self.is_task_running: return messagebox.showwarning("忙碌中", "請等待目前任務結束")
        if messagebox.askyesno("更新", "確定要檢查並更新 yt-dlp 和 ffmpeg 嗎？"):
            self.is_task_running = True
            self.set_status("正在更新...", "purple")
            threading.Thread(target=self.run_update, daemon=True).start()

    def run_update(self):
        try:
            self.log("=== 開始檢查更新 ===")
            
            # 1. Update yt-dlp
            yt_path = os.path.join(self.bin_folder, "yt-dlp.exe")
            if not os.path.exists(yt_path):
                self.log("下載 yt-dlp...")
                urllib.request.urlretrieve("https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe", yt_path)
            else:
                self.log("檢查 yt-dlp 更新...")
                subprocess.run([yt_path, "-U"], creationflags=0x08000000) # CREATE_NO_WINDOW
            
            # 2. Update ffmpeg
            ff_path = os.path.join(self.bin_folder, "ffmpeg.exe")
            if not os.path.exists(ff_path):
                self.log("下載 ffmpeg (這可能需要一點時間)...")
                url = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
                with urllib.request.urlopen(url) as resp:
                    z = zipfile.ZipFile(BytesIO(resp.read()))
                    for n in z.namelist():
                        if n.endswith("bin/ffmpeg.exe"):
                            with z.open(n) as s, open(ff_path, "wb") as t:
                                shutil.copyfileobj(s, t)
                            break
            
            self.log("更新完成！", "green")
            self.refresh_versions()
        except Exception as e:
            self.log(f"更新失敗: {e}", "red")
        finally:
            self.is_task_running = False
            self.set_status("就緒")

    def refresh_versions(self):
        def _check():
            yt_ver = self._get_ver(os.path.join(self.bin_folder, "yt-dlp.exe"), "--version")
            ff_ver = self._get_ver(os.path.join(self.bin_folder, "ffmpeg.exe"), "-version")
            self.ver_label.config(text=f"yt-dlp: {yt_ver} | ffmpeg: {ff_ver}")
            
        threading.Thread(target=_check, daemon=True).start()

    def _get_ver(self, path, arg):
        if not os.path.exists(path): return "未安裝"
        try:
            r = subprocess.run([path, arg], capture_output=True, text=True, creationflags=0x08000000)
            line = r.stdout.split('\n')[0].strip()
            if "ffmpeg" in line.lower(): return line.split()[2] # version info
            return line
        except: return "未知"

if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()