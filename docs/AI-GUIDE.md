# Your link → your transcript → your AI

[← Back to the README](../README.md)

You can give an AI assistant the extractor and ask it to run it. The assistant must be able to execute Python, install the dependency, and make requests to YouTube. If any of these are unavailable, run the tool on your computer and upload the resulting transcript instead.

## Route A · Attach the script

1. Download `youtube_transcript.py` from the [latest release](https://github.com/thinuka-rgb/youtube-script-extractor/releases/latest).
2. Start a chat with an assistant that supports file attachments.
3. Attach that `.py` file and paste the prompt below, replacing the link.
4. Download the returned `.txt`. Check the assistant's report for the selected caption language and type.

### Copy this prompt

```text
Please use the attached Python script to get the available YouTube caption
transcript for: [PASTE YOUTUBE LINK]

Read the script before running it. Install its dependency into an appropriate
Python environment:
python -m pip install "youtube-transcript-api>=1.2.0,<2.0.0"

Then run:
python youtube_transcript.py "[PASTE YOUTUBE LINK]" -o "transcript.txt"

Return the saved file as a download. Tell me which language was retrieved
and whether the caption track is manual or automatic. Preserve the caption
wording. Do not fill gaps from memory or generate a replacement script.

If you lack execution, internet access, or caption access, report that
limitation honestly and give me the command to run locally. If the output
file already exists, choose a new filename rather than deleting it.
```

Attaching only the script is enough to provide the code. It does not bundle Python or the dependency, and does not guarantee the AI can execute it. The dependency and relevant limits are described in the [README](../README.md).

## Route B · Run locally, then upload the text

1. Download and extract the [repository ZIP](https://github.com/thinuka-rgb/youtube-script-extractor/archive/refs/heads/main.zip).
2. Run `run.bat` on Windows, or `sh run.sh` on macOS/Linux, with Python installed.
3. Paste the YouTube link when prompted.
4. Attach the saved file from `transcripts/` to your assistant.

This route lets your computer make the caption request when an assistant cannot. YouTube can still reject requests on a local connection.

### Ask for a readable version

```text
Format the attached caption transcript into readable paragraphs.
Preserve its wording and order. Do not add facts or silently fix phrases.
Flag unclear text separately. Keep a copy of the original transcript.
```

### Ask for a summary

```text
Summarize the attached transcript. Base the summary only on the file.
Separate what the speaker says from your interpretation, and quote short
supporting excerpts where useful. Flag claims that need external verification.
```

For timestamps, ask the assistant to run with `--format srt -o transcript.srt` and use that file. TXT output contains caption text without timing information.

## What to expect

- A caption transcript, not the creator's original script or code shown on screen.
- The chosen track's language. Use `--languages en` to require English; otherwise the tool may fall back to another available language.
- Original caption wording, including possible errors. Automatic captions are not a verified transcription.
- A clear failure when captions cannot be retrieved, rather than an invented transcript.

For the underlying service behavior and request blocking, see the [upstream documentation](https://github.com/jdepoix/youtube-transcript-api#readme).
