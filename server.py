"""Caption API and optional same-origin website. No transcripts are stored on disk."""
from collections import OrderedDict, deque
import os
from pathlib import Path
from threading import BoundedSemaphore, Lock
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from requests import Session
from requests.exceptions import RequestException
from youtube_transcript_api import (
    YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled,
    VideoUnavailable, RequestBlocked, CouldNotRetrieveTranscript,
)
from youtube_transcript_api.formatters import TextFormatter, SRTFormatter, JSONFormatter
from youtube_transcript import extract_video_id

app = FastAPI(title='YouTube Script Extractor', docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv('ALLOWED_ORIGINS', 'https://thinuka-rgb.github.io').split(','),
    allow_methods=['POST', 'GET'], allow_headers=['Content-Type'],
)
slots = BoundedSemaphore(4)
lock = Lock()
cache = OrderedDict()
visitors = OrderedDict()


class CaptionRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    language: str = Field(default='', max_length=20, pattern=r'^[A-Za-z0-9-]*$')


class TimeoutSession(Session):
    def request(self, *args, **kwargs):
        kwargs.setdefault('timeout', (5, 20))
        return super().request(*args, **kwargs)


def retrieve(video_id, language):
    with TimeoutSession() as session:
        tracks = YouTubeTranscriptApi(http_client=session).list(video_id)
        if language:
            selected = tracks.find_transcript([language])
        else:
            try:
                selected = tracks.find_transcript(['en'])
            except NoTranscriptFound:
                selected = next(iter(tracks), None)
                if selected is None:
                    raise HTTPException(404, 'No caption tracks are available for this video.')
        transcript = selected.fetch()
    if not len(transcript):
        raise HTTPException(404, 'YouTube returned an empty caption track.')
    return {
        'video_id': video_id, 'language': transcript.language,
        'language_code': transcript.language_code, 'is_generated': transcript.is_generated,
        'text': TextFormatter().format_transcript(transcript),
        'srt': SRTFormatter().format_transcript(transcript),
        'json': JSONFormatter().format_transcript(transcript),
    }


@app.get('/api/health')
def health():
    # Liveness only; this does not assert that YouTube allows this host.
    return {'status': 'ok'}


@app.post('/api/transcript')
def captions(body: CaptionRequest, request: Request):
    try:
        video_id = extract_video_id(body.url)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    now = time.monotonic()
    ip = request.client.host if request.client else 'unknown'
    key = (video_id, body.language)
    with lock:
        history = visitors.setdefault(ip, deque())
        while history and history[0] < now - 60:
            history.popleft()
        if len(history) >= 6:
            raise HTTPException(429, 'Too many requests. Wait a minute and try again.')
        history.append(now)
        visitors.move_to_end(ip)
        while len(visitors) > 4096:
            visitors.popitem(last=False)
        entry = cache.get(key)
        if entry and now - entry[0] < 600:
            return entry[1]
    if not slots.acquire(blocking=False):
        raise HTTPException(503, 'The extractor is busy. Please try again shortly.')
    try:
        result = retrieve(video_id, body.language)
    except NoTranscriptFound as exc:
        raise HTTPException(404, 'That caption language is unavailable. Try Auto language.') from exc
    except TranscriptsDisabled as exc:
        raise HTTPException(404, 'Captions are disabled or unavailable for this video.') from exc
    except VideoUnavailable as exc:
        raise HTTPException(404, 'This video is unavailable or restricted.') from exc
    except RequestBlocked as exc:
        raise HTTPException(503, 'YouTube blocked this server. Try the downloadable Python tool on your own computer.') from exc
    except (CouldNotRetrieveTranscript, RequestException) as exc:
        raise HTTPException(502, 'Could not retrieve captions from YouTube. Try again later or use the local Python tool.') from exc
    finally:
        slots.release()
    with lock:
        cache[key] = (time.monotonic(), result)
        cache.move_to_end(key)
        while len(cache) > 128:
            cache.popitem(last=False)
    return result


app.mount('/', StaticFiles(directory=Path(__file__).parent / 'web', html=True), name='web')
