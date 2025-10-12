import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import subprocess
import threading
import os
from pathlib import Path

class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")
        self.root.geometry("700x600")
        
        self.is_downloading = False
        self.setup_ui()
        
    def setup_ui(self):
        # URL 輸入區域
        url_label = tk.Label(self.root, text="YouTube URL:", font=("Arial", 10))
        url_label.pack(pady=(10, 5))
        
        self.url_entry = tk.Text(self.root, width=80, height=3, wrap=tk.WORD)
        self.url_entry.pack(pady=5, padx=10)
        
        # Section 輸入區域
        section_label = tk.Label(self.root, text="下載區段 (選填，格式: *開始秒數-結束秒數):", font=("Arial", 10))
        section_label.pack(pady=(10, 5))
        
        self.section_entry = tk.Entry(self.root, width=40)
        self.section_entry.pack(pady=5)
        self.section_entry.bind('<Return>', lambda e: self.start_download())
        
        # 下載路徑選擇
        path_frame = tk.Frame(self.root)
        path_frame.pack(pady=10, padx=10, fill=tk.X)
        
        tk.Label(path_frame, text="下載路徑:", font=("Arial", 10)).pack(side=tk.LEFT)
        
        self.path_entry = tk.Entry(path_frame, width=50)
        self.path_entry.pack(side=tk.LEFT, padx=5)
        self.path_entry.insert(0, "D:/Download/yt-dlp")
        
        tk.Button(path_frame, text="瀏覽", command=self.browse_folder).pack(side=tk.LEFT)
        
        # 下載按鈕
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
        
        # 狀態標籤
        self.status_label = tk.Label(self.root, text="就緒", font=("Arial", 10), fg="blue")
        self.status_label.pack(pady=5)
        
        # 輸出日誌區域
        log_label = tk.Label(self.root, text="下載日誌:", font=("Arial", 10))
        log_label.pack(pady=(10, 5))
        
        self.log_text = scrolledtext.ScrolledText(self.root, width=80, height=15, wrap=tk.WORD)
        self.log_text.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        
    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.path_entry.get())
        if folder:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, folder)
    
    def log_message(self, message, level="INFO"):
        colors = {"INFO": "black", "ERROR": "red", "SUCCESS": "green", "WARNING": "orange"}
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def update_status(self, text, color="blue"):
        self.status_label.config(text=text, fg=color)
    
    def start_download(self):
        if self.is_downloading:
            messagebox.showwarning("警告", "已有下載任務正在進行中")
            return
        
        threading.Thread(target=self.download_video, daemon=True).start()
    
    def download_video(self):
        self.is_downloading = True
        self.download_btn.config(state=tk.DISABLED, bg="#cccccc")
        
        url = self.url_entry.get("1.0", "end-1c").strip()
        section = self.section_entry.get().strip()
        download_path = self.path_entry.get().strip()
        
        # 驗證輸入
        if not url:
            messagebox.showerror("錯誤", "請輸入 YouTube URL")
            self.reset_download_state()
            return
        
        # 確保下載路徑存在
        try:
            Path(download_path).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("錯誤", f"無法創建下載路徑: {e}")
            self.reset_download_state()
            return
        
        # 檢查 yt-dlp 是否存在
        if not os.path.exists("yt-dlp.exe") and not self.check_command("yt-dlp"):
            messagebox.showerror("錯誤", "找不到 yt-dlp.exe，請確保它在程式目錄中或已安裝在系統中")
            self.reset_download_state()
            return
        
        # 構建命令
        cmd = [
            "yt-dlp.exe" if os.path.exists("yt-dlp.exe") else "yt-dlp",
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
                "--download-sections", section
            ])
        else:
            cmd.extend(["-o", "%(uploader)s/%(playlist)s_%(upload_date)s_%(title)s.%(ext)s"])
        
        cmd.append(url)
        
        self.log_text.delete(1.0, tk.END)
        self.log_message(f"開始下載: {url}")
        self.update_status("正在下載...", "orange")
        
        try:
            # 在 Windows 上使用系統預設編碼，通常是 CP950 或 Big5
            import sys
            system_encoding = sys.getdefaultencoding() if sys.platform != 'win32' else 'cp950'
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                text=True,
                encoding=system_encoding,
                errors='replace'
            )
            
            # 即時顯示輸出
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
                self.log_message(f"下載失敗，返回碼: {retcode}", "ERROR")
                self.update_status("下載失敗", "red")
                messagebox.showerror("錯誤", f"下載失敗，請檢查 URL 和參數\n返回碼: {retcode}")
                
        except FileNotFoundError:
            error_msg = "找不到 yt-dlp 或 aria2c，請確保已正確安裝"
            self.log_message(error_msg, "ERROR")
            self.update_status("錯誤", "red")
            messagebox.showerror("錯誤", error_msg)
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
    
    def check_command(self, cmd):
        """檢查命令是否存在於系統中"""
        try:
            subprocess.run([cmd, "--version"], capture_output=True, check=True)
            return True
        except:
            return False

if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()