import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import threading

# 函數用於更新進度條的進度值
def update_progress(output):
    for line in output.splitlines():
        if '[download]' in line:
            # 從輸出中提取百分比並更新進度變數
            percentage = line.split('%')[0].rsplit(' ', 1)[-1]
            try:
                progress_var.set(float(percentage))
            except ValueError:
                pass

# 函數用於開始下載影片
def download_video():
    # 從使用者輸入獲取影片URL和選定的片段
    url = url_entry.get()
    section = section_entry.get()

    # 檢查是否輸入了URL
    if not url:
        messagebox.showerror("錯誤", "請輸入URL")
        return

    # 設置 yt-dlp 命令行參數
    cmd = [
        "yt-dlp.exe", "--ignore-config",
        "--external-downloader", "aria2c",
        "--external-downloader-args", 'aria2c:"--conf-path=aria2_yt-dlp.conf"',
        "--youtube-skip-dash-manifest",
        "--embed-metadata", "--no-part",
        "--sub-lang", "zh-TW", "--write-sub", "--convert-subs", "srt",
        "-P", "D:/Download/yt-dlp"
    ]

    # 如果指定了片段，則設置相關參數
    if section:
        cmd.extend([
            "-o", "%(uploader)s/%(playlist)s_%(upload_date)s_%(title)s_%(section_start)s-%(section_end)s.%(ext)s",
            "--download-sections", section
        ])
    else:
        cmd.extend(["-o", "%(uploader)s/%(playlist)s_%(upload_date)s_%(title)s.%(ext)s"])

    # 將URL添加到命令中
    cmd.append(url)

    try:
        # 執行 yt-dlp 命令並捕獲輸出
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, text=True)
        # 逐行處理輸出，並更新進度條
        for line in iter(process.stdout.readline, ""):
            update_progress(line)
        # 等待命令執行完畢，並獲取返回碼
        retcode = process.wait()
        # 根據返回碼顯示相應訊息
        if retcode:
            messagebox.showerror("錯誤", "下載時發生錯誤。請檢查URL和其他參數。")
        else:
            messagebox.showinfo("成功", "影片下載完成！")
    except subprocess.CalledProcessError:
        messagebox.showerror("錯誤", "下載時發生錯誤。請檢查URL和其他參數。")

    # 下載完成後，將進度重設為0
    progress_var.set(0.0)

# 函數用於在新線程中啟動下載影片
def start_download():
    threading.Thread(target=download_video).start()

# 創建應用程式主窗口
app = tk.Tk()
app.title("YouTube Downloader")

# 創建影片URL輸入框及其標籤
url_label = tk.Label(app, text="yt url:")
url_label.pack(pady=10)
url_entry = tk.Entry(app, width=40)
url_entry.pack(pady=10)
url_entry.bind('<Return>', lambda event=None: start_download())

# 創建片段輸入框及其標籤
section_label = tk.Label(app, text="section(*s-s):")
section_label.pack(pady=10)
section_entry = tk.Entry(app, width=40)
section_entry.pack(pady=10)
section_entry.bind('<Return>', lambda event=None: start_download())

# 創建下載按鈕
download_btn = tk.Button(app, text="下載影片", command=start_download)
download_btn.pack(pady=20)

# 創建進度條
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(app, orient='horizontal', variable=progress_var, mode='determinate', maximum=100)
progress_bar.pack(pady=10, padx=10, fill=tk.X)

# 啟動應用程式主迴圈
app.mainloop()
