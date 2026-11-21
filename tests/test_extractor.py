"""Offline tests: no YouTube requests are made."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from youtube_transcript_api import RequestBlocked
from youtube_transcript_api._transcripts import FetchedTranscript, FetchedTranscriptSnippet
import youtube_transcript as app


class ExtractorTests(unittest.TestCase):
    def invoke(self, args):
        output = io.StringIO()
        with patch('sys.argv', ['youtube_transcript.py', *args]), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            result = app.main()
        return result, output.getvalue()

    def test_supported_links(self):
        for value in [
            'pVUgJt1sDmI',
            'https://www.youtube.com/watch?v=pVUgJt1sDmI&t=12',
            'https://youtu.be/pVUgJt1sDmI?si=abc',
            'youtube.com/shorts/pVUgJt1sDmI',
            'https://www.youtube.com/embed/pVUgJt1sDmI',
            'https://youtube.com/live/pVUgJt1sDmI',
        ]:
            with self.subTest(value=value):
                self.assertEqual(app.extract_video_id(value), 'pVUgJt1sDmI')

    def test_reject_untrusted_or_invalid_links(self):
        for value in ['https://youtube.com.evil.test/watch?v=pVUgJt1sDmI',
                      'https://example.com/watch?v=pVUgJt1sDmI',
                      'ftp://youtube.com/watch?v=pVUgJt1sDmI', 'short']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                app.extract_video_id(value)

    def test_bad_input_returns_two(self):
        code, output = self.invoke(['invalid'])
        self.assertEqual(code, 2)
        self.assertIn('Input error', output)

    def test_formats_and_no_overwrite(self):
        transcript = FetchedTranscript(
            snippets=[FetchedTranscriptSnippet(text='Hello world.', start=1.5, duration=2)],
            video_id='pVUgJt1sDmI', language='English', language_code='en',
            is_generated=False)
        with tempfile.TemporaryDirectory() as directory, \
                patch('youtube_transcript_api.YouTubeTranscriptApi') as api:
            api.return_value.list.return_value.find_transcript.return_value.fetch.return_value = transcript
            for fmt, expected in [('txt', 'Hello world.'), ('srt', '00:00:01,500'),
                                  ('json', '"start": 1.5')]:
                with self.subTest(fmt=fmt):
                    dest = Path(directory) / f'captions.{fmt}'
                    args = ['pVUgJt1sDmI', '--format', fmt, '-o', str(dest)]
                    code, output = self.invoke(args)
                    self.assertEqual(code, 0, output)
                    self.assertIn(expected, dest.read_text(encoding='utf-8'))
                    self.assertIn('Caption type: manual', output)
                    original = dest.read_bytes()
                    code, output = self.invoke(args)
                    self.assertEqual(code, 1)
                    self.assertIn('File already exists', output)
                    self.assertEqual(dest.read_bytes(), original)

    def test_blocked_request_returns_actionable_error(self):
        with patch('youtube_transcript_api.YouTubeTranscriptApi') as api:
            api.return_value.list.side_effect = RequestBlocked('pVUgJt1sDmI')
            code, output = self.invoke(['pVUgJt1sDmI'])
        self.assertEqual(code, 1)
        self.assertIn('YouTube blocked', output)

    def test_fallback_to_available_language(self):
        from youtube_transcript_api import NoTranscriptFound
        from unittest.mock import MagicMock
        transcript = FetchedTranscript(
            snippets=[FetchedTranscriptSnippet(text='Bonjour.', start=0, duration=1)],
            video_id='pVUgJt1sDmI', language='French', language_code='fr',
            is_generated=True)
        with tempfile.TemporaryDirectory() as directory, \
                patch('youtube_transcript_api.YouTubeTranscriptApi') as api:
            tracks = api.return_value.list.return_value
            tracks.find_transcript.side_effect = NoTranscriptFound('pVUgJt1sDmI', ['en'], [])
            track = MagicMock()
            track.fetch.return_value = transcript
            tracks.__iter__.return_value = iter([track])
            code, output = self.invoke(['pVUgJt1sDmI', '-o', str(Path(directory) / 'fr.txt')])
            self.assertEqual(code, 0, output)
            self.assertIn('French (fr)', output)
            self.assertIn('Caption type: automatic', output)


if __name__ == '__main__':
    unittest.main()
