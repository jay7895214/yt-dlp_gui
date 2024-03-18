import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading

def download_video():
    url = url_entry.get("1.0", "end-1c")  # 獲取Text控件中的文字內容
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
        status_label.config(text="正在下載...")
        for line in iter(process.stdout.readline, ""):
            pass
        retcode = process.wait()
        if retcode:
            messagebox.showerror("錯誤", "下載時發生錯誤。請檢查URL和其他參數。")
        else:
            messagebox.showinfo("成功", "影片下載完成！")
    except subprocess.CalledProcessError:
        messagebox.showerror("錯誤", "下載時發生錯誤。請檢查URL和其他參數。")

    status_label.config(text="")

app = tk.Tk()
app.title("YouTube Downloader")

url_label = tk.Label(app, text="yt url:")
url_label.pack(pady=10)

url_entry = tk.Text(app, width=80, height=3, wrap=tk.WORD)  # 使用Text控件，設置 wrap 為 tk.WORD
url_entry.pack(pady=20)

section_label = tk.Label(app, text="section(*s-s):")
section_label.pack(pady=10)

section_entry = tk.Entry(app, width=40)
section_entry.pack(pady=10)
section_entry.bind('<Return>', lambda event=None: threading.Thread(target=download_video).start())

download_btn = tk.Button(app, text="下載影片", command=lambda: threading.Thread(target=download_video).start())
download_btn.pack(pady=20)

status_label = tk.Label(app, text="")
status_label.pack()

app.mainloop()
