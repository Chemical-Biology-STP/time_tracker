# Time Tracker Companion - Windows/Cross-Platform Edition

A system tray application for logging time entries to the Flask backend.

## Features

- System tray icon with quick access menu
- Periodic prompts to log time (configurable interval)
- Research group selection with default group support
- Editable start/end times
- Settings persistence
- Connection status monitoring

## Running from Source

1. Install dependencies:
   ```bash
   pixi install
   ```

2. Start the Flask server (in another terminal):
   ```bash
   pixi run run
   ```

3. Run the companion app:
   ```bash
   pixi run run-companion
   ```

## Building Executable

To build a standalone executable:

```bash
pixi run build-companion
```

The executable will be created in `dist/TimeTrackerCompanion.exe` (Windows) or `dist/TimeTrackerCompanion` (macOS/Linux).

## Usage

1. The app runs in the system tray
2. Double-click the tray icon to log time
3. Right-click for menu options:
   - Log Time... - Open the time logging dialog
   - Open Web Interface - Open the Flask web UI in browser
   - Settings... - Configure the app
   - Quit - Exit the application

## Settings

Settings are stored in `~/.timetrackercompanion/settings.json`:

- Backend URL (default: http://localhost:5001)
- Prompt interval (15, 30, 45, or 60 minutes)
- Default research group
- Launch at login (Windows only)
