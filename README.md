# 🎬 TubeMax 4K Studio (4K Ultra HD, 1080p & MP3 Downloader)

A modern, high-speed, local web application designed to download YouTube videos in **4K Ultra HD (2160p)**, **2K (1440p)**, **Full HD (1080p)**, and extract **High-Quality Audio (MP3 320 kbps)** with crystal-clear audio and video streams merged seamlessly using **FFmpeg** and **yt-dlp**.

---

## ✨ Features
- **🔥 True 4K Ultra HD (2160p) & 2K QHD (1440p)**: Download native 4K and 2K resolution videos with full dynamic range and studio audio.
- **True 1080p Full HD Muxing**: Automatically downloads high-bitrate video and audio streams and merges them into a single `.mp4` file using FFmpeg without quality loss.
- **Pure Audio Extraction**: Convert videos or songs into 320 kbps high-bitrate MP3 or original AAC (M4A).
- **Fast Local Web App**: Clean, dark glassmorphic UI with responsive controls, thumbnail previews, and metadata extraction.
- **Real-Time Progress & Speed**: Live download percentage, transfer speed (MB/s), and ETA counters.
- **Mac Finder Integration**: 1-click button to open your downloaded files directly in macOS Finder (`downloads/` directory).
- **Download History**: View, save, and manage past downloads with file size and timestamp.

---

## 🚀 How to Run

### Option 1: Terminal Command
```bash
cd "/Users/anilsharma/Documents/Anil Sharma Final Website Meterial/Youtube Video Downloader"
./run.sh
```
Or with Python:
```bash
./venv/bin/python3 app.py
```

### Option 2: Open in your Browser
Jab server running ho, apne browser me open karein:
👉 **[http://127.0.0.1:5005](http://127.0.0.1:5005)**

---

## 🛠 Tech Stack
- **Backend**: Python Flask, `yt-dlp` (Homebrew build with Deno JS challenge engine), `FFmpeg` 9.x
- **Frontend**: Vanilla HTML5, Modern CSS (Glassmorphism, Dark Obsidian theme), Vanilla JavaScript
- **Muxing**: High-speed multi-threaded audio & video stream merging via FFmpeg
