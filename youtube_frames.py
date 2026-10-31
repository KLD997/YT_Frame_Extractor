
#!/usr/bin/env python3
"""
YouTube Frame Extractor

Requirements:
    pip install -U yt-dlp
    FFmpeg and FFprobe installed and on PATH

Usage:
    python youtube_frames.py "YOUTUBE_URL"
    python youtube_frames.py "YOUTUBE_URL" -o frames
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yt_dlp


def check_dependencies():
    for executable in ("ffmpeg", "ffprobe"):
        if not shutil.which(executable):
            sys.exit(f"Error: {executable} not found in PATH.")


def download_video(url, directory):
    directory.mkdir(parents=True, exist_ok=True)

    options = {
        "format": "bestvideo*+bestaudio/best",
        "format_sort": [
            "res",
            "fps",
            "hdr",
            "vbr",
        ],
        "outtmpl": str(directory / "source.%(ext)s"),
        "merge_output_format": "mkv",
        "noplaylist": True,
        "overwrites": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([url])

    candidates = [
        p for p in directory.glob("source.*")
        if p.suffix.lower() in {
            ".mkv", ".mp4", ".webm", ".mov"
        }
    ]

    if not candidates:
        raise RuntimeError("Video download failed.")

    return max(candidates, key=lambda p: p.stat().st_mtime)


def get_video_info(video):
    command = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries",
        "stream=width,height,avg_frame_rate,nb_frames",
        "-of", "json",
        str(video),
    ]

    result = subprocess.run(
        command, capture_output=True,
        text=True, check=True
    )

    return json.loads(result.stdout)["streams"][0]


def extract_frames(video, output, bit_depth=8):
    output.mkdir(parents=True, exist_ok=True)

    pixel_format = (
        "rgb48be" if bit_depth == 16 else "rgb24"
    )

    command = [
        "ffmpeg",
        "-hide_banner",
        "-i", str(video),
        "-map", "0:v:0",
        "-fps_mode", "passthrough",
        "-pix_fmt", pixel_format,
        "-compression_level", "9",
        "-start_number", "1",
        str(output / "frame_%08d.png"),
    ]

    print("\nExtracting every frame...")
    subprocess.run(command, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "-o", "--output",
        default="youtube_extraction",
        help="Output directory"
    )
    parser.add_argument(
        "--bit-depth",
        type=int,
        choices=[8, 16],
        default=8,
        help="PNG channel bit depth (default: 8)"
    )
    parser.add_argument(
        "--keep-video",
        action="store_true",
        help="Keep downloaded source video"
    )

    args = parser.parse_args()
    check_dependencies()

    root = Path(args.output).resolve()
    frames = root / "frames"

    print("Downloading highest-quality video...")
    video = download_video(args.url, root)

    info = get_video_info(video)

    print("\nSource video:")
    print(f"Resolution: {info['width']}x{info['height']}")
    print(f"Frame rate: {info.get('avg_frame_rate')}")
    print(f"Reported frames: {info.get('nb_frames', 'N/A')}")

    extract_frames(video, frames, args.bit_depth)

    count = sum(1 for _ in frames.glob("frame_*.png"))
    print(f"\nSuccessfully extracted {count} frames.")
    print(f"Output: {frames}")

    if not args.keep_video:
        video.unlink()
        print("Downloaded video removed.")


if __name__ == "__main__":
    main()
