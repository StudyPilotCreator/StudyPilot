# StudyPilot — Dein Lerncoach

The original dark glassmorphism look is kept. The old calendar-first planner is replaced by a local learning workspace.

## Features
- First-run setup for school type, class grade, difficulty and subjects.
- Subject folders and saved study sets for tests, exams, presentations and regular learning.
- Upload photos, PDFs and TXT files or paste notes. Selectable PDF text is read with PDF.js; image and scanned-page OCR uses Tesseract.js.
- Files are processed in the browser. Original uploads are not sent to a StudyPilot server; recognised text and generated materials are saved on this device.
- Automatic topic summaries, flashcards and quiz questions generated with local text-processing rules.
- Topic quizzes and full-set quizzes.
- Flashcard review with per-card spaced-repetition scheduling.
- Saved learning sets, quiz results and JSON backup/restore.
- Installable PWA, no backend or AI API key required.

## Publish
GitHub Pages URL: https://studypilotcreator.github.io/StudyPilot/

## Limitations
This version does not call a large language model. Summary, flashcard and question generation uses local text rules, so important facts should be checked against class materials. OCR depends on image clarity. First-time PDF/photo processing downloads libraries from CDNs and requires an internet connection. Browser data stays on each device; there is no MacBook–iPhone sync.
