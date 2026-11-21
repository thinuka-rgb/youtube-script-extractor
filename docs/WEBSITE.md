# Website hosting

The frontend is published at **https://thinuka-rgb.github.io/youtube-script-extractor/** using GitHub Pages. It needs a separate Python backend. GitHub Pages only serves static HTML, CSS, and JavaScript ([GitHub documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)).

## Current setup

`web/config.js` starts with an empty API address. Until a working backend is connected, the website labels itself a preview and disables extraction. A deployment of the frontend alone is not a working online extractor.

## Deploy the Python server on Render

1. Create or sign in to a [Render account](https://dashboard.render.com/).
2. Open [Deploy from this repository](https://render.com/deploy?repo=https://github.com/thinuka-rgb/youtube-script-extractor).
3. Review the Blueprint. `render.yaml` selects **Free** compute and creates only a Python web service, with no database. Keep the free plan selected; check any account-level billing settings separately.
4. Connect this public repository if prompted and deploy it.
5. Open the returned `https://…onrender.com` address. The same website is served there, already connected to its own API.
6. **Test with a video that has available captions.** `/api/health` only checks that the server runs; it does not verify YouTube access. If YouTube blocks the server, this free-host arrangement is not ready for public extraction. Do not advertise it as working or add credentials/proxies to public source files.
7. Once extraction succeeds, set `window.EXTRACTOR_API = 'https://YOUR-SERVICE.onrender.com';` in `web/config.js`, commit, and push. The GitHub Pages workflow publishes that connection automatically. Confirm a successful extraction from the `github.io` URL too.

Render supports [FastAPI web services](https://render.com/docs/deploy-fastapi) and [free instances](https://render.com/docs/free). Free services sleep after inactivity and have usage limits. YouTube may block cloud IP addresses, as described by the [underlying library](https://github.com/jdepoix/youtube-transcript-api#working-around-ip-bans-requestblocked-or-ipblocked-exception). A free host is not a guarantee of reliable caption access.

## Local end-to-end run

From a Python virtual environment in the repository:

```sh
python -m pip install -r requirements-web.txt
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. The local web page connects to the same Python server. Leave `web/config.js` empty for this local setup.

## Server behavior

- `POST /api/transcript`: accepts `{"url": "YOUTUBE_LINK", "language": ""}`; returns text, SRT, JSON, language, and caption type. An empty language prefers English then falls back to an available track.
- `GET /api/health`: liveness response, not an extraction test.
- Only parsed YouTube video IDs reach the caption client. Arbitrary submitted URLs are not fetched.
- The app keeps at most 128 successful results in an in-memory cache, reusing them for up to ten minutes. Nothing is written to a transcript database or disk. Hosting providers may retain logs.
- Basic per-client limits allow six extraction requests per minute; four upstream operations may run concurrently. Limits and cache are per process, so the deployment uses one worker. These are hobby-service protections, not a distributed abuse-prevention system. Behind a proxy, configure trusted proxy handling for your host so client addresses are interpreted correctly; never trust arbitrary forwarded headers from the public internet.
- `ALLOWED_ORIGINS` is a comma-separated CORS allowlist. Default: `https://thinuka-rgb.github.io`. CORS controls browsers; it is not authentication.

## GitHub Pages

Enable **Settings → Pages → Source → GitHub Actions**. The `Publish website` workflow deploys only `web/`, keeping Python files outside the website artifact. No paid domain is needed. GitHub provides the `github.io` project URL ([GitHub documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)).
