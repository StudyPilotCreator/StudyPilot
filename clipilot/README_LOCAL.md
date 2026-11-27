# ClipPilot Local (Mac)

## Status / Grenzen
- Die Browser-Oberfläche wird über GitHub Pages geladen.
- Mac-Backend verarbeitet **lokal ausgewählte Videodateien**: Whisper-Transkript, grobe Highlight-Scoring, FFmpeg 9:16 MP4 mit Untertiteln.
- Es gibt **keinen automatischen Download/Extraktor für beliebige YouTube-/Twitch-URLs**. Plattformzugriff und Rechte sind nicht garantiert; verwende eigene Dateien oder Quellen, für die du Bearbeitungsrechte hast.
- iPhone-Sparmodus in der Browser-Oberfläche ist derzeit ein einfacher UI/Datei-Auswahl-Modus. Für Verarbeitung kann das iPhone im selben WLAN den Mac-Server mit Token nutzen. Unabhängige KI-Verarbeitung auf dem iPhone ist noch nicht implementiert.

## Mac-Installation
1. Repository auf dem Mac klonen oder den Ordner `clipilot` als Dateien lokal verfügbar machen.
2. Terminal im Ordner `clipilot` öffnen.
3. `bash Install_ClipPilot.command` ausführen (Homebrew/FFmpeg und Python-Pakete).
4. `bash Start_ClipPilot.command` ausführen und Terminal geöffnet lassen.
5. Browser öffnen: https://studypilotcreator.github.io/StudyPilot/clipilot/
6. Token, das im Terminal angezeigt wird, in das Token-Feld der Website eintragen.
7. Videodatei auswählen, Clipanzahl/Länge einstellen, Clips erstellen.

## iPhone im gleichen WLAN
1. Mac-Server starten.
2. Mac-IP im WLAN herausfinden (Systemeinstellungen > WLAN > Details > TCP/IP).
3. In ClipPilot iPhone-Modus IP und Port eintragen, z.B. `http://192.168.1.20:8765`, plus Token.
4. Datei auf dem iPhone auswählen. iPhone und Mac müssen im selben WLAN sein.
5. Achtung: iPhone-Safari kann bei großen Uploads/Verbindungen Limits haben.

## Sicherheit
Der Server bindet an alle lokalen Netzwerkinterfaces, um die Verbindung vom iPhone zu erlauben. Er ist mit Token geschützt. Teile den Token nicht; stoppe den Server, wenn du ihn nicht brauchst.
