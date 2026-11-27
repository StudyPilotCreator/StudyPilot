# ClipPilot — YouTube-Link zu Shorts (Mac + iPhone)

## So funktioniert es

1. YouTube-Link einfügen.
2. Clip-Anzahl und Länge wählen.
3. Auf "Highlights erstellen" tippen.
4. Fertige 9:16-MP4-Clips mit Untertiteln ansehen oder speichern.

Du musst das Originalvideo **nicht selbst herunterladen oder hochladen**. ClipPilot ruft das Video über den Link automatisch ab. Für öffentlich erreichbare Videos ist kein YouTube Premium erforderlich. Während der Verarbeitung wird auf dem Mac eine temporäre Arbeitskopie angelegt und danach wieder gelöscht.

## Wichtige Einschränkung

Die Website-Oberfläche allein verarbeitet keine Videos. Die eigentliche Verarbeitung läuft lokal auf deinem Mac. Der Mac muss eingeschaltet sein und ClipPilot muss laufen. Es gibt derzeit **keinen kostenlosen, dauerhaft online verfügbaren Cloud-Server** für die Verarbeitung.

YouTube kann den Abruf bei privaten, geschützten, nur für Mitglieder verfügbaren oder alters-/regionsbeschränkten Videos verhindern. ClipPilot umgeht solche Schutzmaßnahmen nicht. Bitte verarbeite nur Videos, die du selbst erstellt hast oder für die du die nötigen Rechte und Erlaubnisse hast, und beachte die Regeln der Plattform.

## Installation auf dem Mac

Voraussetzung: macOS, Python 3 und Homebrew.

1. Lade das Repository von GitHub herunter oder klone es.
2. Öffne im Terminal den Ordner clipilot.
3. Installiere die Komponenten mit:
   bash Install_ClipPilot.command
4. Starte ClipPilot mit:
   bash Start_ClipPilot.command
5. Lass das Terminal geöffnet. Beim Start wird ein Verbindungstoken angezeigt.
6. Öffne auf deinem Mac http://127.0.0.1:8765.
7. Öffne "Einmalige Verbindung einrichten", füge das Token aus dem Terminal ein und speichere die Verbindung.
8. Danach genügt es, einen YouTube-Link einzufügen und "Highlights erstellen" anzuklicken.

Beim ersten Start kann Whisper sein Sprachmodell herunterladen. Das ist nicht der Download des YouTube-Videos durch dich, sondern die lokale Spracherkennungs-Komponente.

## Auf dem iPhone verwenden

1. Mac und iPhone müssen im selben WLAN sein.
2. Starte ClipPilot auf dem Mac und lass das Terminal offen.
3. Ermittle die lokale IP-Adresse deines Macs (WLAN-Einstellungen oder die Ausgabe im Start-Terminal).
4. Öffne auf dem iPhone in Safari http://MAC-IP:8765/mobile und ersetze MAC-IP durch die angezeigte IP-Adresse.
5. Trage das Token aus dem Mac-Terminal einmalig ein und speichere die Verbindung.
6. Danach kannst du auf dem iPhone nur noch den YouTube-Link eingeben.

Optional: Safari → Teilen → Zum Home-Bildschirm, um ClipPilot wie eine App zu öffnen.

## Verarbeitung und Qualität

- YouTube-Linkabruf über yt-dlp (kein manuelles Herunterladen durch dich).
- Transkription mit faster-whisper auf dem Mac.
- Automatische Highlight-Bewertung anhand von Sprachdichte, Reaktionen, Wendungen und Textsignalen.
- Export als 9:16-MP4 mit eingebrannten Untertiteln.
- Standardauswahl: 3 Clips mit je 45 Sekunden.

Die Highlight-Auswahl ist eine automatische Heuristik und versteht nicht jedes Video vollständig. Sie garantiert keine viralen Clips. Prüfe die Ergebnisse vor dem Veröffentlichen.

## Fehlerbehebung

- **Token falsch:** Token im Terminal erneut prüfen. In der Website lässt sich das gespeicherte Token löschen und neu eintragen.
- **Server nicht erreichbar:** Prüfen, ob das Start-Terminal noch läuft. Auf dem iPhone müssen beide Geräte im selben WLAN sein.
- **YouTube-Link fehlgeschlagen:** Prüfen, ob das Video öffentlich aufrufbar ist. ClipPilot unterstützt keine privaten oder zugangsbeschränkten Inhalte.
- **FFmpeg fehlt:** bash Install_ClipPilot.command erneut ausführen.
- **yt-dlp aktualisieren:** Im ClipPilot-Ordner den Befehl ./.venv/bin/pip install --upgrade yt-dlp ausführen und den Server danach neu starten.

## Sicherheit

Das Token nicht weitergeben. Es wird nur im lokalen Browser gespeichert, wenn du die Verbindung erfolgreich prüfst. Beim Löschen der gespeicherten Verbindung wird das Token aus diesem Browser entfernt. Beende den Server, wenn du ClipPilot nicht mehr brauchst.
