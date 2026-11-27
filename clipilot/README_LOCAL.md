# ClipPilot Local (Mac + Browser + iPhone)

## What is working in this version
- GitHub Pages browser UI with Mac Pro and iPhone Spar modes.
- Mac local API: processes **video files selected by the user**, locally.
- Whisper (faster-whisper) transcription, basic transcript-based highlight scoring, FFmpeg vertical MP4 export with SRT captions.
- Token-protected API. The server prints a token on startup.
- iPhone PWA shell can be added to the Home Screen; it can connect to the Mac server while both devices are on the same Wi-Fi.
- The PWA shell is cached for basic offline opening, but processing requires the local server.

## Important limitations
- Link processing is experimental: the Mac uses yt-dlp to retrieve supported public video links. This is not guaranteed for every YouTube/Twitch URL, protected content, live streams, age/region restrictions, or platform changes. Use only content you have permission to process and comply with platform rules.
- Mac is the full local processing mode.
- iPhone standalone AI processing is **not yet implemented**. Mobile can choose a file and submit it to the Mac server over local Wi-Fi; when away from the Mac it is currently just a lightweight UI/file selection, not clip generation.
- Highlight ranking is heuristic (transcript words, speech density, punctuation); it is not a guaranteed viral predictor.
- First run downloads Whisper model weights. There are no paid API calls.

## Mac setup (one time)
1. Open Terminal.
2. Clone the repo: `git clone https://github.com/StudyPilotCreator/StudyPilot.git`
3. Enter project: `cd StudyPilot/clipilot`
4. Install: `bash Install_ClipPilot.command` (Homebrew + FFmpeg + Python dependencies; install can take a while).
5. Start local backend: `bash Start_ClipPilot.command` and keep Terminal running.
6. Open the web UI: https://studypilotcreator.github.io/StudyPilot/clipilot/
7. Copy the token printed in Terminal into the **Lokaler Server-Token** field.
8. Select a video file and choose number/duration. Click **Lokale Clips erstellen**.
9. The output MP4s are stored under `~/.clippilot/clips/` and linked in the page.

## iPhone setup
1. Open the dedicated mobile page in Safari: https://studypilotcreator.github.io/StudyPilot/clipilot/mobile.html
2. For the Mac-powered processing flow, open the same page while the Mac server is running, then enter the Mac's LAN URL and token.
3. If the GitHub Pages URL is not published/accessible, open the page from the repository after Pages deployment is enabled.

## iPhone + Mac link-processing steps
1. Open the web UI in Safari: https://studypilotcreator.github.io/StudyPilot/clipilot/
2. Safari Share button > **Add to Home Screen**.
3. To process on Mac over Wi-Fi, start the Mac backend and use the iPhone mode.
4. Find the Mac's private Wi-Fi IP (Mac System Settings > Wi-Fi > Details > TCP/IP), then enter e.g. `http://192.168.1.20:8765` plus the token.
5. Choose the video in iPhone Files/Photos picker and submit. Both devices must be on same Wi-Fi; keep Mac awake.
6. If away from Mac, mobile processing is not currently available; this is planned as a separate on-device light engine.

## Safety
Local server binds to LAN for optional iPhone connection and uses a token. Don't share the token. Stop the server when not needed.
