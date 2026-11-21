"""API contract, origin restrictions, and failure tests; no external requests."""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from youtube_transcript_api import RequestBlocked
import server


class ServerTests(unittest.TestCase):
    def setUp(self):
        server.cache.clear()
        server.visitors.clear()
        self.client = TestClient(server.app)

    def test_health_and_site(self):
        self.assertEqual(self.client.get('/api/health').json(), {'status': 'ok'})
        self.assertIn('Keep the words.', self.client.get('/').text)

    def test_rejects_arbitrary_url_without_upstream_call(self):
        with patch('server.retrieve') as retrieve:
            response = self.client.post('/api/transcript', json={'url': 'https://example.com'})
        self.assertEqual(response.status_code, 400)
        retrieve.assert_not_called()

    def test_result_and_cache(self):
        fixture = {'video_id': 'pVUgJt1sDmI', 'text': '<script>caption</script>',
                   'srt': 'captions', 'json': '[]', 'language': 'English',
                   'language_code': 'en', 'is_generated': False}
        with patch('server.retrieve', return_value=fixture) as retrieve:
            response = self.client.post('/api/transcript', json={'url': 'https://youtu.be/pVUgJt1sDmI'})
            again = self.client.post('/api/transcript', json={'url': 'pVUgJt1sDmI'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), fixture)
        self.assertEqual(again.json(), fixture)
        retrieve.assert_called_once_with('pVUgJt1sDmI', '')

    def test_blocked_host_is_reported_honestly(self):
        with patch('server.retrieve', side_effect=RequestBlocked('pVUgJt1sDmI')):
            response = self.client.post('/api/transcript', json={'url': 'pVUgJt1sDmI'})
        self.assertEqual(response.status_code, 503)
        self.assertIn('YouTube blocked', response.json()['detail'])

    def test_rate_limit(self):
        with patch('server.retrieve', return_value={'text': 'test'}):
            for _ in range(6):
                self.assertEqual(self.client.post('/api/transcript', json={'url': 'pVUgJt1sDmI'}).status_code, 200)
            self.assertEqual(self.client.post('/api/transcript', json={'url': 'pVUgJt1sDmI'}).status_code, 429)

    def test_cors_origin_allowlist(self):
        for origin, allowed in [('https://thinuka-rgb.github.io', True), ('https://example.com', False)]:
            with self.subTest(origin=origin):
                response = self.client.options('/api/transcript', headers={
                    'Origin': origin, 'Access-Control-Request-Method': 'POST',
                    'Access-Control-Request-Headers': 'Content-Type'})
                self.assertEqual(response.status_code, 200 if allowed else 400)

    def test_invalid_body(self):
        response = self.client.post('/api/transcript', json={'url': 'x' * 2049})
        self.assertEqual(response.status_code, 422)


if __name__ == '__main__':
    unittest.main()
