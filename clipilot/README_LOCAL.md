# ClipPilot (Mac + iPhone)

## Mobile page
Dedicated iPhone UI: https://studypilotcreator.github.io/StudyPilot/clipilot/mobile.html

The mobile page is designed for iPhone: paste a supported YouTube/Twitch URL, choose clip count and duration, connect to the ClipPilot server, and receive links to the MP4 clips. It validates the server connection and shows clear errors/results.

**Important:** GitHub Pages only hosts the static website. It cannot run yt-dlp, Whisper, or FFmpeg. The current mobile page still needs the ClipPilot processing server (currently the Mac local server). If the Mac/server is offline, clip generation is unavailable. A free always-online cloud processor has not been deployed.

## Current local processing features
- yt-dlp link retrieval for supported public links (experimental and may fail with platform changes, age/region checks, protected or live content).
- faster-whisper speech transcription.
- Heuristic highlight ranking using speech coverage/density, transcript cue phrases, punctuation, word count, and lexical variety.
- Non-overlapping candidate selection with extra separation.
- Vertical 9:16 MP4 output and burned-in captions.
- Token-protected local API.

Highlight ranking is automated and heuristic; it cannot promise viral results or reliably understand all context. Use only videos you have permission to process and comply with the source platform's rules.

## Mac setup
1. Clone the repository: `git clone https://github.com/StudyPilotCreator/StudyPilot.git`
2. Enter the folder: `cd StudyPilot/clipilot`
3. Install: `bash Install_ClipPilot.command`
4. Start: `bash Start_ClipPilot.command` and keep it running.
5. The terminal prints the ClipPilot access token. Keep it private.
6. Open the mobile page in Safari, enter the Mac's local address (for example `http://192.168.1.20:8765`) and token. Both devices must be on the same Wi-Fi.
7. Paste a supported video link, choose clip count/duration, and tap **Highlights erstellen**.

## iPhone PWA
Open the page in Safari and use Share > Add to Home Screen. For processing, keep the Mac/server online and reachable; the standalone static page cannot process video on its own.

## Security
The local API uses a token. Don't share it. Stop the local server when you finish.