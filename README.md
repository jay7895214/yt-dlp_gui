[繁體中文](README_zh-TW.md) | [English](README.md)

# yt-dlp_gui v1.2.0

A universal downloader GUI for YouTube and Podcasts, built with Python and Tkinter.
It acts as a wrapper around `yt-dlp` and `ffmpeg`.

## Features
- Batch download support
- Playlist and single video analysis
- Selection of video formats, resolutions, and container preferences (MP4/WebM)
- Subtitle downloading (manual and auto-generated) with language and format options
- Standalone subtitle downloading without video
- Embedding subtitles and metadata
- Built-in updater for `yt-dlp`, `ffmpeg`, and `ffprobe`
- Progress bar, detailed logging, and UI configuration auto-saving

## Requirements
- Python 3.x
- `yt-dlp`, `ffmpeg`, `ffprobe` (can be downloaded via the tool's update feature)

## Usage
Run the script:
```bash
python yt-dlp.py
```

## Download Behaviors Explained

The GUI offers different download buttons depending on the context. Here is how they behave regarding video format and subtitle settings:

| Scenario | Button Location | Video Behavior | Subtitle Behavior |
|----------|-----------------|----------------|-------------------|
| **Direct Download** | Main Window (`⬇️ 直接下載`) | Uses Main Window format & container settings | Uses Main Window subtitle settings |
| **Quick Download** | Playlist Window (`⬇️ 快速下載選取項目`) | Uses Main Window format & container settings | Uses Main Window subtitle settings |
| **Download Selected Format** | Video Details Window ➔ Video Format Tab | Downloads **only** the selected format. Overrides Main Window. | **Ignored**. No subtitles are downloaded. |
| **Download Selected Subs Only** | Video Details Window ➔ Subtitle Tab | **Skipped** (`--skip-download`). No video is downloaded. | Downloads **only** the selected subtitle(s) using Main Window's subtitle format setting. |