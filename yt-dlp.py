import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import subprocess
import threading
import os
import sys
import urllib.request
import zipfile
import shutil
from pathlib import Path
from io import BytesIO

class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader (含版本偵測)")
        self.root.geometry("700x700") # 稍微再加高以容納版本資訊
        
        self.is_downloading = False
        self.is_updating = False
        
        self.setup_menu()
        self.setup_ui()
        
        # 程式啟動時自動檢查版本
        self.refresh_versions()
        
    def setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="檢查並更新 yt-dlp 與 ffmpeg", command=self.start_update_tools)
        
    def setup_ui(self):
        # --- 主要輸入區 ---
        url_label = tk.Label(self.root, text="YouTube URL:", font=("Arial", 10))
        url_label.pack(pady=(10, 5))
        
        self.url_entry = tk.Text(self.root, width=80, height=3, wrap=tk.WORD)
        self.url_entry.pack(pady=5, padx=10)
        
        # --- Section 區段 ---
        section_frame = tk.Frame(self.root)
        section_frame.pack(pady=10)
        
        tk.Label(section_frame, text="下載區段 (選填):", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        
        tk.Label(section_frame, text="開始秒數:").pack(side=tk.LEFT, padx=(10, 5))
        self.start_sec_entry = tk.Entry(section_frame, width=10)
        self.start_sec_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Label(section_frame, text="結束秒數:").pack(side=tk.LEFT, padx=(10, 5))
        self.end_sec_entry = tk.Entry(section_frame, width=10)
        self.end_sec_entry.pack(side=tk.LEFT, padx=5)
        self.end_sec_entry.bind('<Return>', lambda e: self.start_download())
        
        # --- 路徑選擇 ---
        path_frame = tk.Frame(self.root)
        path_frame.pack(pady=10, padx=10, fill=tk.X)
        
        tk.Label(path_frame, text="下載路徑:", font=("Arial", 10)).pack(side=tk.LEFT)
        
        self.path_entry = tk.Entry(path_frame, width=50)
        self.path_entry.pack(side=tk.LEFT, padx=5)
        default_path = str(Path.home() / "Downloads" / "yt-dlp")
        self.path_entry.insert(0, default_path)
        
        tk.Button(path_frame, text="瀏覽", command=self.browse_folder).pack(side=tk.LEFT)
        
        # --- 下載按鈕 ---
        self.download_btn = tk.Button(
            self.root, 
            text="開始下載", 
            command=self.start_download,
            font=("Arial", 12),
            bg="#4CAF50",
            fg="white",
            padx=20,
            pady=5
        )
        self.download_btn.pack(pady=15)
        
        # --- 狀態顯示 ---
        self.status_label = tk.Label(self.root, text="就緒", font=("Arial", 10), fg="blue")
        self.status_label.pack(pady=5)
        
        # --- 日誌區 ---
        log_label = tk.Label(self.root, text="操作日誌:", font=("Arial", 10))
        log_label.pack(pady=(10, 5))
        
        self.log_text = scrolledtext.ScrolledText(self.root, width=80, height=12, wrap=tk.WORD)
        self.log_text.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

        # --- 版本資訊顯示區 (新增) ---
        info_frame = tk.LabelFrame(self.root, text="組件版本資訊", font=("Arial", 9), padx=10, pady=5)
        info_frame.pack(pady=10, padx=10, fill=tk.X, side=tk.BOTTOM)
        
        # 使用 Grid 來排版版本資訊
        tk.Label(info_frame, text="yt-dlp:", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky="e", padx=5)
        self.ver_ytdlp_label = tk.Label(info_frame, text="偵測中...", font=("Arial", 9), fg="#555")
        self.ver_ytdlp_label.grid(row=0, column=1, sticky="w")
        
        tk.Label(info_frame, text="FFmpeg:", font=("Arial", 9, "bold")).grid(row=0, column=2, sticky="e", padx=(20, 5))
        self.ver_ffmpeg_label = tk.Label(info_frame, text="偵測中...", font=("Arial", 9), fg="#555")
        self.ver_ffmpeg_label.grid(row=0, column=3, sticky="w")

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.path_entry.get())
        if folder:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, folder)
    
    def log_message(self, message, level="INFO"):
        self.log_text.insert(tk.END, f"[{level}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def update_status(self, text, color="blue"):
        self.status_label.config(text=text, fg=color)

    # ------------------ 版本檢查邏輯 (新增) ------------------
    def refresh_versions(self):
        """在背景執行版本檢查，以免卡住 UI"""
        threading.Thread(target=self._check_versions_thread, daemon=True).start()

    def _check_versions_thread(self):
        # 檢查 yt-dlp
        ytdlp_ver = self.get_cmd_version("yt-dlp.exe", "--version")
        # 檢查 ffmpeg
        ffmpeg_ver = self.get_cmd_version("ffmpeg.exe", "-version")
        
        # 更新 UI (需切回主線程，但 Tkinter 某些操作在 thread 中是安全的，文字更新通常沒問題)
        # 為了保險使用 root.after 委派
        self.root.after(0, lambda: self.update_version_labels(ytdlp_ver, ffmpeg_ver))

    def update_version_labels(self, ytdlp_ver, ffmpeg_ver):
        # 設定 yt-dlp 顏色
        if "未偵測到" in ytdlp_ver:
            self.ver_ytdlp_label.config(text=ytdlp_ver, fg="red")
        else:
            self.ver_ytdlp_label.config(text=ytdlp_ver, fg="green")
            
        # 設定 ffmpeg 顏色
        if "未偵測到" in ffmpeg_ver:
            self.ver_ffmpeg_label.config(text=ffmpeg_ver, fg="red")
        else:
            self.ver_ffmpeg_label.config(text=ffmpeg_ver, fg="green")

    def get_cmd_version(self, filename, flag):
        """執行命令並回傳第一行版本資訊"""
        if not os.path.exists(filename) and not self.check_command_on_path(filename.replace(".exe", "")):
            return "未偵測到 (請執行更新)"
        
        cmd_name = filename if os.path.exists(filename) else filename.replace(".exe", "")
        
        try:
            # 隱藏 console 視窗
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            result = subprocess.run(
                [cmd_name, flag], 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                errors='replace',
                startupinfo=startupinfo
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                lines = output.split('\n')
                if not lines: return "未知"
                
                first_line = lines[0].strip()
                
                # 特殊處理 ffmpeg 輸出: "ffmpeg version N-117865... Copyright..."
                if "ffmpeg" in first_line.lower():
                    parts = first_line.split()
                    if len(parts) >= 3:
                        return parts[2] # 通常版本號在第三個位置
                    return "已安裝 (版本未知)"
                
                # yt-dlp 通常直接回傳 "2024.11.04"
                return first_line
            return "執行錯誤"
        except Exception:
            return "錯誤"

    def check_command_on_path(self, cmd):
        try:
            subprocess.run([cmd, "--version"], capture_output=True, check=True)
            return True
        except:
            return False

    # ------------------ 更新功能區塊 ------------------
    def start_update_tools(self):
        if self.is_downloading or self.is_updating:
            messagebox.showwarning("警告", "目前有任務正在進行中")
            return
        
        if messagebox.askyesno("確認更新", "這將會檢查並更新 yt-dlp.exe 和 ffmpeg.exe。\n是否繼續？"):
            threading.Thread(target=self.run_update_process, daemon=True).start()

    def run_update_process(self):
        self.is_updating = True
        self.download_btn.config(state=tk.DISABLED)
        self.log_message("=== 開始檢查組件更新 ===", "UPDATE")
        
        try:
            self.update_ytdlp()
            self.update_ffmpeg()
            self.log_message("=== 組件檢查與更新完成 ===", "SUCCESS")
            messagebox.showinfo("完成", "組件更新檢查完成！")
            
            # 更新完成後，重新讀取版本號
            self.refresh_versions()
            
        except Exception as e:
            self.log_message(f"更新過程發生錯誤: {str(e)}", "ERROR")
            messagebox.showerror("更新失敗", str(e))
        finally:
            self.is_updating = False
            self.download_btn.config(state=tk.NORMAL)
            self.update_status("就緒", "blue")

    def update_ytdlp(self):
        exe_name = "yt-dlp.exe"
        if not os.path.exists(exe_name):
            self.log_message(f"找不到 {exe_name}，正在下載最新版...", "UPDATE")
            try:
                url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
                self.download_file(url, exe_name)
                self.log_message(f"{exe_name} 下載完成", "SUCCESS")
            except Exception as e:
                self.log_message(f"下載 yt-dlp 失敗: {e}", "ERROR")
        else:
            self.log_message(f"正在檢查 {exe_name} 更新...", "UPDATE")
            try:
                cmd = [exe_name, "-U"]
                # 隱藏視窗
                startupinfo = None
                if sys.platform == 'win32':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    encoding='utf-8', 
                    errors='replace',
                    startupinfo=startupinfo
                )
                
                if result.returncode == 0:
                    output = result.stdout.strip()
                    if "up-to-date" in output:
                        self.log_message("yt-dlp 已經是最新版本", "INFO")
                    else:
                        self.log_message(f"yt-dlp 更新結果: {output}", "SUCCESS")
                else:
                    self.log_message(f"yt-dlp 更新檢查失敗: {result.stderr}", "WARNING")
            except Exception as e:
                self.log_message(f"執行 yt-dlp 更新失敗: {e}", "ERROR")

    def update_ffmpeg(self):
        self.log_message("正在檢查 ffmpeg...", "UPDATE")
        ffmpeg_url = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        
        if os.path.exists("ffmpeg.exe"):
            self.log_message("ffmpeg.exe 已存在，跳過下載", "INFO")
            return

        self.log_message("正在下載 FFmpeg...", "UPDATE")
        self.update_status("正在下載 FFmpeg...", "orange")
        
        try:
            with urllib.request.urlopen(ffmpeg_url) as response:
                zip_data = response.read()
            
            self.log_message("FFmpeg 下載完成，解壓縮中...", "UPDATE")
            
            with zipfile.ZipFile(BytesIO(zip_data)) as zf:
                ffmpeg_src = None
                for name in zf.namelist():
                    if name.endswith("bin/ffmpeg.exe"):
                        ffmpeg_src = name
                        break
                
                if ffmpeg_src:
                    with zf.open(ffmpeg_src) as source, open("ffmpeg.exe", "wb") as target:
                        shutil.copyfileobj(source, target)
                    self.log_message("ffmpeg.exe 已安裝", "SUCCESS")
                else:
                    self.log_message("壓縮檔中找不到 ffmpeg.exe", "ERROR")
        except Exception as e:
            self.log_message(f"FFmpeg 安裝失敗: {e}", "ERROR")
            
    def download_file(self, url, filename):
        with urllib.request.urlopen(url) as response:
            with open(filename, 'wb') as f:
                shutil.copyfileobj(response, f)

    # ------------------ 下載功能區塊 ------------------
    def start_download(self):
        if self.is_downloading or self.is_updating:
            messagebox.showwarning("警告", "已有任務正在進行中")
            return
        threading.Thread(target=self.download_video, daemon=True).start()
    
    def download_video(self):
        self.is_downloading = True
        self.download_btn.config(state=tk.DISABLED, bg="#cccccc")
        
        url = self.url_entry.get("1.0", "end-1c").strip()
        start_sec = self.start_sec_entry.get().strip()
        end_sec = self.end_sec_entry.get().strip()
        download_path = self.path_entry.get().strip()
        
        if not url:
            messagebox.showerror("錯誤", "請輸入 YouTube URL")
            self.reset_download_state()
            return
        
        section = None
        if start_sec or end_sec:
            try:
                if start_sec and not start_sec.isdigit(): raise ValueError("開始秒數錯誤")
                if end_sec and not end_sec.isdigit(): raise ValueError("結束秒數錯誤")
                if start_sec and end_sec and int(start_sec) >= int(end_sec): raise ValueError("時間範圍錯誤")
                
                if start_sec and end_sec: section = f"*{start_sec}-{end_sec}"
                elif start_sec: section = f"*{start_sec}-inf"
                elif end_sec: section = f"*0-{end_sec}"
            except ValueError as e:
                messagebox.showerror("錯誤", str(e))
                self.reset_download_state()
                return
        
        try:
            Path(download_path).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("錯誤", f"路徑錯誤: {e}")
            self.reset_download_state()
            return
        
        exe_path = "yt-dlp.exe" if os.path.exists("yt-dlp.exe") else "yt-dlp"
        if not self.check_command_on_path(exe_path):
            if messagebox.askyesno("缺少組件", "找不到 yt-dlp，是否自動下載？"):
                self.update_ytdlp()
                self.refresh_versions() # 更新介面顯示
                if not os.path.exists("yt-dlp.exe"):
                    messagebox.showerror("錯誤", "下載失敗")
                    self.reset_download_state()
                    return
                exe_path = "yt-dlp.exe"
            else:
                self.reset_download_state()
                return
        
        cmd = [
            exe_path,
            "--ignore-config",
            "--external-downloader", "aria2c",
            "--external-downloader-args", 'aria2c:"--conf-path=aria2_yt-dlp.conf"',
            "--youtube-skip-dash-manifest",
            "--embed-metadata", "--no-part",
            "--sub-lang", "zh-TW", "--write-sub", "--convert-subs", "srt",
            "-P", download_path
        ]
        
        if section:
            cmd.extend([
                "-o", "%(uploader)s/%(playlist)s_%(upload_date)s_%(title)s_%(section_start)s-%(section_end)s.%(ext)s",
                "--download-sections", section,
                "--force-keyframes-at-cuts"
            ])
        else:
            cmd.extend(["-o", "%(uploader)s/%(playlist)s_%(upload_date)s_%(title)s.%(ext)s"])
        
        cmd.append(url)
        
        self.log_text.delete(1.0, tk.END)
        self.log_message(f"開始下載: {url}")
        self.update_status("正在下載...", "orange")
        
        try:
            system_encoding = sys.getdefaultencoding() if sys.platform != 'win32' else 'cp950'
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                text=True,
                encoding=system_encoding,
                errors='replace',
                startupinfo=startupinfo
            )
            
            for line in iter(process.stdout.readline, ""):
                if line:
                    self.log_message(line.rstrip())
            
            process.stdout.close()
            retcode = process.wait()
            
            if retcode == 0:
                self.log_message("下載完成！", "SUCCESS")
                self.update_status("下載完成", "green")
                messagebox.showinfo("成功", "影片下載完成！")
            else:
                self.log_message(f"下載失敗 (Code: {retcode})", "ERROR")
                self.update_status("下載失敗", "red")
                messagebox.showerror("錯誤", f"下載失敗，Code: {retcode}\n請檢查 ffmpeg 是否存在？")
                
        except Exception as e:
            error_msg = f"發生錯誤: {str(e)}"
            self.log_message(error_msg, "ERROR")
            self.update_status("錯誤", "red")
            messagebox.showerror("錯誤", error_msg)
        finally:
            self.reset_download_state()
    
    def reset_download_state(self):
        self.is_downloading = False
        self.download_btn.config(state=tk.NORMAL, bg="#4CAF50")
        if self.status_label.cget("text") == "正在下載...":
            self.update_status("就緒", "blue")

if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()