import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import threading

def update_progress(output):
    for line in output.splitlines():
        if '[download]' in line:
            percentage = line.split('%')[0].rsplit(' ', 1)[-1]
            try:
                progress_var.set(float(percentage))
            except ValueError:
                pass

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

def start_download():
    threading.Thread(target=download_video).start()

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

progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(app, orient='horizontal', variable=progress_var, mode='determinate', maximum=100)
progress_bar.pack(pady=10, padx=10, fill=tk.X)

app.mainloop()
