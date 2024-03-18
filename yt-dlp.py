import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import threading

def update_progress(output):
    downloaded_size = 0
    total_size = 0

    for line in output.splitlines():
        if '[download]' in line:
            if 'of' in line:
                total_size_str = line.split('of')[-1].strip()
                total_size_str = total_size_str.split()[0].strip()
                # 檢查字串是否包含小數，如果是則轉換為浮點數
                if 'MiB' in total_size_str:
                    total_size = float(total_size_str.replace('MiB', ''))
            if 'ETA' not in line and 'MiB' in line:
                downloaded_size_str = line.split()[0].strip()
                # 檢查字串是否包含小數，如果是則轉換為浮點數
                if 'MiB' in downloaded_size_str:
                    downloaded_size = float(downloaded_size_str.replace('MiB', ''))

    downloaded_label.config(text=f"已下載: {downloaded_size} MiB")
    total_label.config(text=f"總大小: {total_size} MiB")

    if total_size > 0:
        progress = (downloaded_size / total_size) * 100
        progress_var.set(progress)


def download_video():
    url = url_entry.get()
    section = section_entry.get()

    if not url:
        messagebox.showerror("錯誤", "請輸入URL")
        return

    cmd = [
        "yt-dlp.exe", "--ignore-config",
        "--external-downloader", "aria2c",
        "--external-downloader-args", 'aria2c:"--conf-path=aria2_yt-dlp.conf"',
        "--youtube-skip-dash-manifest",
        "--embed-metadata", "--no-part",
        "--sub-lang", "zh-TW", "--write-sub", "--convert-subs", "srt",
        "-P", "D:/Download/yt-dlp"
    ]

    if section:
        cmd.extend([
            "-o", "%(uploader)s/%(playlist)s_%(upload_date)s_%(title)s_%(section_start)s-%(section_end)s.%(ext)s",
            "--download-sections", section
        ])
    else:
        cmd.extend(["-o", "%(uploader)s/%(playlist)s_%(upload_date)s_%(title)s.%(ext)s"])

    cmd.append(url)

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, text=True)
        # 顯示"正在下載"的訊息
        status_label.config(text="正在下載...")
        for line in iter(process.stdout.readline, ""):
            update_progress(line)
        retcode = process.wait()
        if retcode:
            messagebox.showerror("錯誤", "下載時發生錯誤。請檢查URL和其他參數。")
        else:
            messagebox.showinfo("成功", "影片下載完成！")
    except subprocess.CalledProcessError:
        messagebox.showerror("錯誤", "下載時發生錯誤。請檢查URL和其他參數。")

    progress_var.set(0.0)
    # 下載完成後將訊息重設為空
    status_label.config(text="")

def start_download():
    threading.Thread(target=download_video).start()

# 函數用於取消下載
def cancel_download():
    # 將目前的下載進程殺死
    for proc in subprocess.Popen.subprocesses:
        proc.kill()
    # 更新進度條為0
    progress_var.set(0.0)
    # 清空下載訊息
    status_label.config(text="")

app = tk.Tk()
app.title("YouTube Downloader")

url_label = tk.Label(app, text="yt url:")
url_label.pack(pady=10)

url_entry = tk.Entry(app, width=40)
url_entry.pack(pady=10)
url_entry.bind('<Return>', lambda event=None: start_download())

section_label = tk.Label(app, text="section(*s-s):")
section_label.pack(pady=10)

section_entry = tk.Entry(app, width=40)
section_entry.pack(pady=10)
section_entry.bind('<Return>', lambda event=None: start_download())

download_btn = tk.Button(app, text="下載影片", command=start_download)
download_btn.pack(pady=20)

downloaded_label = tk.Label(app, text="已下載: 0 MiB")
downloaded_label.pack()

total_label = tk.Label(app, text="總大小: 0 MiB")
total_label.pack()

progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(app, orient='horizontal', variable=progress_var, mode='determinate', maximum=100)
progress_bar.pack(pady=10, padx=10, fill=tk.X)

# 新增顯示下載狀態的標籤
status_label = tk.Label(app, text="")
status_label.pack()

# 新增取消按鈕
cancel_btn = tk.Button(app, text="取消下載", command=cancel_download)
cancel_btn.pack(pady=20)

app.mainloop()
