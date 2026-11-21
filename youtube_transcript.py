"""Retrieve available YouTube captions from a video or Shorts link.

Install: python -m pip install -r requirements.txt
Standalone install: python -m pip install "youtube-transcript-api>=1.2.0,<2.0.0"
Run:     python youtube_transcript.py
Docs:    https://github.com/jdepoix/youtube-transcript-api
"""

import argparse
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, urlparse


def extract_video_id(value):
    """Accept watch, Shorts, share, embed, and live URLs or a video ID."""
    value = value.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return value
    if "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Use an http or https YouTube link.")
    host = (parsed.hostname or "").lower()
    parts = parsed.path.strip("/").split("/")
    video_id = ""
    if host in {"youtu.be", "www.youtu.be"}:
        video_id = parts[0]
    elif host in {
        "youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com",
        "youtube-nocookie.com", "www.youtube-nocookie.com",
    }:
        if parsed.path.rstrip("/") == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        elif len(parts) == 2 and parts[0] in {"shorts", "embed", "live"}:
            video_id = parts[1]
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("Paste a valid YouTube video/Shorts link or 11-character video ID.")
    return video_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?", help="YouTube video or Shorts link")
    parser.add_argument("--languages", nargs="+", metavar="CODE",
                        help="Preferred caption languages, e.g. --languages en si")
    parser.add_argument("--format", choices=("txt", "srt", "json"), default="txt")
    parser.add_argument("-o", "--output", type=Path, help="Output file path")
    args = parser.parse_args()

    try:
        value = args.url or input("Paste a YouTube video or Shorts link: ")
        video_id = extract_video_id(value)
    except (ValueError, EOFError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2

    try:
        from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound
        from youtube_transcript_api import (
            TranscriptsDisabled, VideoUnavailable, RequestBlocked,
            CouldNotRetrieveTranscript,
        )
        from youtube_transcript_api.formatters import (
            TextFormatter, SRTFormatter, JSONFormatter,
        )
        from requests.exceptions import RequestException
    except ImportError:
        print('Install the dependency: python -m pip install "youtube-transcript-api>=1.2.0,<2.0.0"',
              file=sys.stderr)
        return 1

    try:
        available = YouTubeTranscriptApi().list(video_id)
        if args.languages:
            selected = available.find_transcript(args.languages)
        else:
            # Prefer English; otherwise use the first available caption track.
            try:
                selected = available.find_transcript(["en"])
            except NoTranscriptFound:
                selected = next(iter(available), None)
                if selected is None:
                    print("No caption tracks are available for this video.", file=sys.stderr)
                    return 1
        transcript = selected.fetch()
        if not len(transcript):
            print("YouTube returned an empty transcript.", file=sys.stderr)
            return 1
    except NoTranscriptFound:
        print("No transcript matches the requested languages. Try without --languages.",
              file=sys.stderr)
        return 1
    except TranscriptsDisabled:
        print("Captions are disabled or unavailable for this video.", file=sys.stderr)
        return 1
    except VideoUnavailable:
        print("The video is unavailable. It may be private, removed, or restricted.",
              file=sys.stderr)
        return 1
    except RequestBlocked:
        print("YouTube blocked this request/IP. Try again later or on another network.",
              file=sys.stderr)
        return 1
    except (CouldNotRetrieveTranscript, RequestException) as exc:
        print(f"Could not retrieve captions ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 1

    formatters = {"txt": TextFormatter, "srt": SRTFormatter, "json": JSONFormatter}
    content = formatters[args.format]().format_transcript(transcript)
    destination = args.output or (
        Path(__file__).resolve().parent / "transcripts" / f"{video_id}.{args.format}"
    )
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Avoid silently overwriting an existing transcript.
        with destination.open("x", encoding="utf-8") as output:
            output.write(content + "\n")
    except FileExistsError:
        print(f"File already exists: {destination}. Choose another path with -o.",
              file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Could not save the transcript: {exc}", file=sys.stderr)
        return 1

    print(f"Language: {transcript.language} ({transcript.language_code})")
    print(f"Caption type: {'automatic' if transcript.is_generated else 'manual'}")
    try:
        print(content)
    except UnicodeEncodeError:
        print("Transcript saved; this terminal cannot display all its characters.")
    print(f"\nSaved to: {destination.resolve()}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        sys.exit(130)
