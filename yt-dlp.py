import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import threading
import re

def download_video():
    url = url_entry.get("1.0", "end-1c")  # 獲取Text控件中的文字內容
    section = section_entry.get()
    quality = quality_var.get()

    if not url:
        status_label.config(text="錯誤: 請輸入URL")
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

    if quality:
        cmd.extend(["-f", quality])

    if section:
        cmd.extend([
            "-o", "%(uploader)s/%(playlist)s_%(upload_date)s_%(title)s_%(section_start)s-%(section_end)s.%(ext)s",
            "--download-sections", section
        ])
    else:
        cmd.extend(["-o", "%(uploader)s/%(playlist)s_%(upload_date)s_%(title)s.%(ext)s"])

    cmd.append(url)

    log_file = open("download_log.txt", "w")

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, text=True)
        status_label.config(text="正在下載...")
        progress_bar['value'] = 0

        for line in iter(process.stdout.readline, ""):
            log_file.write(line)
            log_file.flush()
            print(line, end="")  # 將每行輸出打印到控制台
            if "Total file size" in line:
                total_size = float(re.search(r"([0-9.]+)", line).group(1))
            if "%" in line:
                match = re.search(r"([0-9.]+)%", line)
                if match:
                    percentage = float(match.group(1))
                    progress_bar['value'] = percentage
                    status_label.config(text=f"正在下載... {percentage:.2f}%")
        
        retcode = process.wait()
        if retcode:
            status_label.config(text="錯誤: 下載時發生錯誤。請檢查URL和其他參數。")
        else:
            status_label.config(text="成功: 影片下載完成！")
    except subprocess.CalledProcessError:
        status_label.config(text="錯誤: 下載時發生錯誤。請檢查URL和其他參數。")
    finally:
        log_file.close()

    progress_bar['value'] = 0

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

quality_label = tk.Label(app, text="影片畫質:")
quality_label.pack(pady=10)

quality_var = tk.StringVar()
quality_combobox = ttk.Combobox(app, textvariable=quality_var)
quality_combobox['values'] = ('best', 'worst', '144p', '240p', '360p', '480p', '720p', '1080p')
quality_combobox.current(0)  # 預設選擇 'best'
quality_combobox.pack(pady=10)

download_btn = tk.Button(app, text="下載影片", command=lambda: threading.Thread(target=download_video).start())
download_btn.pack(pady=20)

progress_bar = ttk.Progressbar(app, orient="horizontal", length=400, mode="determinate")
progress_bar.pack(pady=10)

status_label = tk.Label(app, text="")
status_label.pack()

app.mainloop()
