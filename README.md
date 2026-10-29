# StudyPilot

Your personal planner for school, activities, and everyday life.

## Features
- First-run setup with separate start and end times for each school day.
- Recurring weekly activities such as sports, music lessons, and clubs.
- Date-specific tasks with duration and priority.
- Automatic daily task suggestions around fixed school and activity times.
- Breaks between task blocks, plus warnings for overlapping fixed appointments.
- Monthly calendar, weekly routines, and one-off events.
- Local browser storage; no account, remote database, or AI API required.
- JSON backup export and confirmed backup import.
- Installable web-app structure and offline support; the service worker checks online for newer app versions.
- Dedicated 180×180 PNG home-screen icon for iPhone.

## Publish with GitHub Pages
GitHub Pages publishes the main branch from the repository root.
Expected URL: https://studypilotcreator.github.io/StudyPilot/

Open this HTTPS URL in Safari on your iPhone and choose Share → Add to Home Screen.

## Data and privacy
The app stores the schedule, routines, tasks, and events in local browser storage on each device. There is no cross-device synchronization and no remote database. The repository itself is public, so never commit personal schedule data to it; enter personal details only inside the app.

## Planning notes
The automatic planner is a suggestion, not a calendar write operation. It leaves fixed appointments untouched. The current version schedules whole tasks within a free slot and does not split a task across multiple slots.