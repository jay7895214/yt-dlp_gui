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