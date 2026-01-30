# Time Tracker Companion - Chrome Extension

A Chrome extension for logging time entries to your Time Tracker server.

## Features

- Quick time logging popup
- Periodic reminder notifications
- Research group selection with default group support
- Editable start/end times
- Connection status monitoring
- Settings sync across Chrome instances

## Installation

### From Source (Developer Mode)

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `chrome_extension` folder
5. The extension icon should appear in your toolbar

### Usage

1. Click the extension icon to open the time logging popup
2. Enter your task description
3. Select a research group
4. Adjust start/end times if needed
5. Click Submit

### Settings

Click "Settings" in the popup or right-click the extension icon → Options:

- **Backend URL**: Your Flask server address (default: http://localhost:5001)
- **Reminder Interval**: How often to show notifications (15, 30, 45, or 60 minutes)
- **Enable Notifications**: Toggle reminder notifications
- **Default Research Group**: Pre-selected group when logging time

## Requirements

- The Flask Time Tracker server must be running
- For local use: `http://localhost:5001`
- For shared server: Update the Backend URL in settings

## Permissions

- `storage`: Save your settings
- `alarms`: Schedule reminder notifications
- `notifications`: Show reminder popups
- `host_permissions`: Connect to localhost/127.0.0.1
