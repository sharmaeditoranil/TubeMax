import os
import sys
import json
import time
import uuid
import re
import subprocess
import threading
import shutil
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Locate binaries (Brew defaults or PATH)
YT_DLP_BIN = "/opt/homebrew/bin/yt-dlp" if os.path.exists("/opt/homebrew/bin/yt-dlp") else "yt-dlp"
FFMPEG_BIN = "/opt/homebrew/bin/ffmpeg" if os.path.exists("/opt/homebrew/bin/ffmpeg") else "ffmpeg"

# Store active download tasks in memory
tasks_lock = threading.Lock()
tasks = {}

def format_duration(seconds):
    if not seconds:
        return "Unknown"
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def format_views(views):
    if not views:
        return "N/A"
    if views >= 1_000_000_000:
        return f"{views / 1_000_000_000:.1f}B"
    if views >= 1_000_000:
        return f"{views / 1_000_000:.1f}M"
    if views >= 1_000:
        return f"{views / 1_000:.1f}K"
    return f"{views:,}"

def format_bytes(size):
    if not size:
        return "N/A"
    power = 2**10
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB'}
    while size > power and n < 3:
        size /= power
        n += 1
    return f"{size:.1f} {power_labels[n]}"

COOKIES_FILE = BASE_DIR / "cookies.txt"

def ensure_cookies():
    """Sync cookies from YOUTUBE_COOKIES environment variable if provided."""
    env_cookies = os.environ.get("YOUTUBE_COOKIES", "").strip()
    if env_cookies:
        try:
            if not COOKIES_FILE.exists() or COOKIES_FILE.read_text(encoding="utf-8").strip() != env_cookies:
                COOKIES_FILE.write_text(env_cookies, encoding="utf-8")
                print("[TubeMax] Updated cookies.txt from YOUTUBE_COOKIES env var.")
        except Exception as e:
            print(f"[TubeMax] Failed writing cookies: {e}")

def get_yt_base_args():
    ensure_cookies()
    args = [
        "--no-check-certificates",
        "--socket-timeout", "30",
    ]
    if COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 0:
        args.extend(["--cookies", str(COOKIES_FILE)])
    return args

def sanitize_filename(name):
    # Keep alphanumeric, spaces, and common safe chars
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/info", methods=["POST"])
def get_info():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()

    if not url:
        return jsonify({"success": False, "error": "Kripya YouTube video link enter karein"}), 400

    base_args = get_yt_base_args()

    # Multi-strategy retry for anti-bot / datacenter protection
    strategies = [
        ["--extractor-args", "youtube:player_client=visionos"],       # 1. VisionOS (bypasses bot challenges & SABR issues)
        ["--extractor-args", "youtube:player_client=android_vr,tv"],  # 2. VR/TV fallback
        [],                                                           # 3. Standard Deno fallback
    ]

    env = os.environ.copy()
    env["PATH"] = f"/opt/homebrew/bin:/usr/local/bin:{env.get('PATH', '')}"

    last_error = ""
    info = None

    for extra_args in strategies:
        cmd = [
            YT_DLP_BIN,
            *base_args,
            *extra_args,
            "--dump-single-json",
            "--skip-download",
            "--no-playlist",
            "--ffmpeg-location", FFMPEG_BIN,
            url
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=35,
                env=env
            )

            if proc.returncode == 0:
                try:
                    info = json.loads(proc.stdout)
                    break
                except Exception:
                    pass
            else:
                last_error = proc.stderr.strip()
                # Fast exit for permanent errors
                if "Video unavailable" in last_error or "Private video" in last_error:
                    break
        except subprocess.TimeoutExpired:
            last_error = "YouTube server response timeout ho gaya (35s)."
            continue

    if not info:
        if "Video unavailable" in last_error:
            return jsonify({"success": False, "error": "Yeh video available nahi hai ya private hai."}), 400
        elif "Private video" in last_error:
            return jsonify({"success": False, "error": "Yeh video private hai."}), 400
        elif "Sign in" in last_error:
            return jsonify({"success": False, "error": "YouTube anti-bot verification trigger hua hai. Thodi der me retry karein."}), 400
        return jsonify({"success": False, "error": f"Video fetch nahi ho saka: {last_error[:200]}"}), 400

    try:
        formats = info.get("formats", [])
        heights = set(f.get("height") for f in formats if f.get("height"))

        # Build quality options
        qualities = []

        has_4k = any(h and h >= 2160 for h in heights)
        has_2k = any(h and h >= 1440 for h in heights)
        has_1080 = any(h and h >= 1080 for h in heights)

        # 4K Ultra HD (if video supports 4K)
        if has_4k:
            qualities.append({
                "id": "2160p",
                "label": "4K Ultra HD",
                "format_desc": "MP4 (3840x2160 + Studio Audio)",
                "badge": "🔥 4K ULTRA HD",
                "available": True,
                "type": "video",
                "is_4k": True
            })

        # 2K Quad HD (if video supports 2K)
        if has_2k:
            qualities.append({
                "id": "1440p",
                "label": "2K Quad HD",
                "format_desc": "MP4 (2560x1440 + Studio Audio)",
                "badge": "2K QHD",
                "available": True,
                "type": "video"
            })

        # 1080p Full HD
        qualities.append({
            "id": "1080p",
            "label": "1080p Full HD",
            "format_desc": "MP4 (Video 1080p + Audio merged)",
            "badge": "Recommended" if (has_1080 and not has_4k) else "Full HD",
            "available": True,
            "type": "video"
        })

        # 720p HD
        qualities.append({
            "id": "720p",
            "label": "720p HD",
            "format_desc": "MP4 (High Definition)",
            "badge": "Fast",
            "available": True,
            "type": "video"
        })

        # 480p SD
        qualities.append({
            "id": "480p",
            "label": "480p SD",
            "format_desc": "MP4 (Standard Definition)",
            "badge": "Data Saver",
            "available": True,
            "type": "video"
        })

        # Audio Only MP3
        qualities.append({
            "id": "mp3",
            "label": "MP3 Audio",
            "format_desc": "High Quality MP3 (320 kbps)",
            "badge": "Audio Only",
            "available": True,
            "type": "audio"
        })

        # Audio Only M4A
        qualities.append({
            "id": "m4a",
            "label": "M4A Audio",
            "format_desc": "Original Audio (AAC)",
            "badge": "Crystal Clear",
            "available": True,
            "type": "audio"
        })

        # Get best thumbnail
        thumb = info.get("thumbnail")
        thumbnails = info.get("thumbnails", [])
        if thumbnails:
            # pick highest resolution thumbnail
            best_thumb = max(thumbnails, key=lambda t: t.get("preference", 0) or t.get("width", 0) or 0)
            if best_thumb.get("url"):
                thumb = best_thumb.get("url")

        response_data = {
            "success": True,
            "id": info.get("id"),
            "title": info.get("title"),
            "channel": info.get("uploader") or info.get("channel"),
            "duration": format_duration(info.get("duration")),
            "duration_raw": info.get("duration", 0),
            "views": format_views(info.get("view_count")),
            "thumbnail": thumb,
            "webpage_url": info.get("webpage_url") or url,
            "qualities": qualities,
            "has_4k": has_4k
        }
        return jsonify(response_data)

    except Exception as e:
        return jsonify({"success": False, "error": f"Metadata parsing error: {str(e)}"}), 500


def run_download_worker(task_id, url, quality, title):
    with tasks_lock:
        task = tasks.get(task_id)
        if not task:
            return

    safe_title = sanitize_filename(title or "youtube_video")[:80]
    out_template = str(DOWNLOAD_DIR / f"{safe_title}_{task_id}.%(ext)s")

    env = os.environ.copy()
    env["PATH"] = f"/opt/homebrew/bin:/usr/local/bin:{env.get('PATH', '')}"

    base_args = get_yt_base_args()

    if quality == "mp3":
        format_args = ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
        expected_ext = "mp3"
    elif quality == "m4a":
        format_args = ["-x", "--audio-format", "m4a"]
        expected_ext = "m4a"
    elif quality in ("4k", "2160p"):
        format_args = ["-f", "bestvideo[height<=2160]+bestaudio/best[height<=2160]/best", "--merge-output-format", "mp4"]
        expected_ext = "mp4"
    elif quality in ("2k", "1440p"):
        format_args = ["-f", "bestvideo[height<=1440]+bestaudio/best[height<=1440]/best", "--merge-output-format", "mp4"]
        expected_ext = "mp4"
    elif quality == "1080p":
        format_args = ["-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best", "--merge-output-format", "mp4"]
        expected_ext = "mp4"
    elif quality == "720p":
        format_args = ["-f", "bestvideo[height<=720]+bestaudio/best[height<=720]/best", "--merge-output-format", "mp4"]
        expected_ext = "mp4"
    else:  # 480p or default
        format_args = ["-f", "bestvideo[height<=480]+bestaudio/best[height<=480]/best", "--merge-output-format", "mp4"]
        expected_ext = "mp4"

    cmd = [
        YT_DLP_BIN,
        *base_args,
        "--extractor-args", "youtube:player_client=visionos",
        *format_args,
        "--ffmpeg-location", FFMPEG_BIN,
        "-o", out_template,
        "--newline",
        "--progress-template", "%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s|%(progress.status)s",
        url
    ]

    try:
        with tasks_lock:
            task["status"] = "downloading"
            task["message"] = "Downloading streams from YouTube..."

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env
        )

        last_lines = []
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue

            last_lines.append(line)
            if len(last_lines) > 12:
                last_lines.pop(0)

            # Check if line matches our progress template: percent|speed|eta|status
            if "|" in line:
                parts = line.split("|")
                if len(parts) >= 4:
                    raw_pct = parts[0].replace("%", "").strip()
                    try:
                        pct_val = float(raw_pct)
                    except ValueError:
                        pct_val = task["percent"]

                    with tasks_lock:
                        task["percent"] = pct_val
                        task["speed"] = parts[1].strip() if parts[1].strip() != "NA" else task["speed"]
                        task["eta"] = parts[2].strip() if parts[2].strip() != "NA" else task["eta"]
                        if parts[3].strip() == "finished":
                            task["message"] = "Merging Video & Audio with FFmpeg..."
                        else:
                            task["message"] = f"Downloading... {task['percent']:.1f}%"
            elif "[Merger]" in line or "Merging" in line or "[ffmpeg]" in line:
                with tasks_lock:
                    task["message"] = "FFmpeg merging Full HD audio and video..."
                    task["percent"] = 99.0

        proc.wait()

        if proc.returncode == 0:
            # Locate downloaded file matching task_id
            matched_files = list(DOWNLOAD_DIR.glob(f"*{task_id}.*"))
            if matched_files:
                final_file = matched_files[0]
                with tasks_lock:
                    task["status"] = "completed"
                    task["percent"] = 100.0
                    task["message"] = "Download and merge completed successfully!"
                    task["filename"] = final_file.name
                    task["filesize"] = format_bytes(final_file.stat().st_size)
                    task["download_url"] = f"/api/file/{task_id}"
            else:
                with tasks_lock:
                    task["status"] = "error"
                    task["message"] = "Download ho gaya par output file nahi mili."
        else:
            err_line = next((l for l in reversed(last_lines) if "error" in l.lower()), "")
            if not err_line and last_lines:
                err_line = last_lines[-1]
            with tasks_lock:
                task["status"] = "error"
                task["message"] = f"Download fail ho gaya: {err_line[:140]}" if err_line else "Download fail ho gaya. YouTube anti-bot restriction."

    except Exception as e:
        with tasks_lock:
            task["status"] = "error"
            task["message"] = f"Error: {str(e)}"


@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    quality = data.get("quality") or "1080p"
    title = data.get("title") or "video"

    if not url:
        return jsonify({"success": False, "error": "URL missing"}), 400

    task_id = str(uuid.uuid4())[:8]

    task_obj = {
        "id": task_id,
        "url": url,
        "quality": quality,
        "title": title,
        "status": "starting",
        "percent": 0.0,
        "speed": "--",
        "eta": "--",
        "message": "Initializing high-speed download...",
        "filename": None,
        "filesize": None,
        "download_url": None,
        "created_at": time.time()
    }

    with tasks_lock:
        tasks[task_id] = task_obj

    # Start background thread
    t = threading.Thread(target=run_download_worker, args=(task_id, url, quality, title), daemon=True)
    t.start()

    return jsonify({"success": True, "task_id": task_id})


@app.route("/api/progress/<task_id>")
def get_progress(task_id):
    with tasks_lock:
        task = tasks.get(task_id)
        if not task:
            return jsonify({"success": False, "error": "Task not found"}), 404
        return jsonify({"success": True, "task": task})


@app.route("/api/file/<task_id>")
def serve_file(task_id):
    matched_files = list(DOWNLOAD_DIR.glob(f"*{task_id}.*"))
    if not matched_files:
        return "File not found", 404
    
    file_path = matched_files[0]
    # Clean display name by removing the _task_id suffix
    display_name = re.sub(f"_{task_id}\\.", ".", file_path.name)
    return send_file(file_path, as_attachment=True, download_name=display_name)


@app.route("/api/open-downloads", methods=["POST"])
def open_downloads_folder():
    try:
        subprocess.run(["open", str(DOWNLOAD_DIR)], check=True)
        return jsonify({"success": True, "message": "Folder opened in Finder"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/history", methods=["GET"])
def get_history():
    files_list = []
    for f in DOWNLOAD_DIR.iterdir():
        if f.is_file() and not f.name.startswith("."):
            stat = f.stat()
            # extract clean title
            clean_title = re.sub(r'_[a-f0-9]{8}\.', '.', f.name)
            files_list.append({
                "filename": f.name,
                "display_name": clean_title,
                "size": format_bytes(stat.st_size),
                "created_at": time.strftime("%d %b %Y, %I:%M %p", time.localtime(stat.st_mtime)),
                "mtime": stat.st_mtime,
                "ext": f.suffix.replace(".", "").upper()
            })
    # Sort latest first
    files_list.sort(key=lambda x: x["mtime"], reverse=True)
    return jsonify({"success": True, "files": files_list})


@app.route("/api/history/<filename>", methods=["DELETE"])
def delete_file(filename):
    file_path = DOWNLOAD_DIR / filename
    if file_path.exists() and file_path.is_file():
        file_path.unlink()
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "File not found"}), 404


@app.route("/api/history/download/<filename>", methods=["GET"])
def download_history_file(filename):
    file_path = DOWNLOAD_DIR / filename
    if file_path.exists() and file_path.is_file():
        clean_title = re.sub(r'_[a-f0-9]{8}\.', '.', f"{filename}")
        return send_file(file_path, as_attachment=True, download_name=clean_title)
    return "File not found", 404


@app.route("/robots.txt")
def robots_txt():
    content = """User-agent: *
Allow: /
Disallow: /api/
Sitemap: https://tubemax4k.com/sitemap.xml
"""
    return Response(content, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://tubemax4k.com/</loc>
    <lastmod>2026-10-11</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
"""
    return Response(content, mimetype="application/xml")


@app.route("/favicon.ico")
def favicon():
    svg_icon = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
        <rect width="32" height="32" rx="8" fill="#ff0033"/>
        <polygon points="12,9 23,16 12,23" fill="#ffffff"/>
    </svg>"""
@app.route("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": "TubeMax 4K Studio Backend",
        "has_cookies": COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 0,
        "deno": bool(shutil.which("deno")),
        "node": bool(shutil.which("node"))
    })

@app.route("/api/cookies", methods=["GET", "POST"])
def manage_cookies():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        cookie_text = data.get("cookies", "").strip()
        if not cookie_text:
            return jsonify({"success": False, "error": "Cookie text khali nahi ho sakta"}), 400
        try:
            COOKIES_FILE.write_text(cookie_text, encoding="utf-8")
            return jsonify({"success": True, "message": "Cookies successfully save ho gayi hain!"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    return jsonify({
        "has_cookies": COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 0,
        "cookie_file_size": COOKIES_FILE.stat().st_size if COOKIES_FILE.exists() else 0
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5005))
    print(f"🚀 YouTube Video Downloader running on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
