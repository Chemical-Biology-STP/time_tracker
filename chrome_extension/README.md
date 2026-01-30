# Time Tracker - Chrome Extension

A fully standalone Chrome extension for tracking work time. No server required - data syncs automatically across devices via your Google account.

## Features

- ⏱️ Quick time logging popup
- 🔔 Periodic reminder notifications
- 📊 View entries and summary statistics
- 📥 Export to CSV for reporting
- 🔄 Auto-sync across all your Chrome browsers
- 👥 Multiple research groups support

## Installation

1. Download or clone this repository
2. Open Chrome and go to `chrome://extensions/`
3. Enable "Developer mode" (toggle in top right)
4. Click "Load unpacked"
5. Select the `chrome_extension` folder
6. Pin the extension to your toolbar for easy access

## Usage

### Logging Time
1. Click the extension icon
2. Enter what you've been working on
3. Select a research group
4. Adjust start/end times if needed
5. Click Submit

### Viewing Entries
- Click the "Entries" tab to see your logged time
- Filter by research group
- Export to CSV for spreadsheet analysis

### Settings
- Click ⚙️ Settings or right-click extension → Options
- Set reminder interval (15, 30, 45, or 60 minutes)
- Enable/disable notifications
- Manage research groups
- Set default group

## Data Storage

Your data is stored in Chrome's sync storage:
- Automatically syncs across all Chrome browsers where you're signed in
- No server or account setup required
- Data persists even if you reinstall the extension
- Export to JSON for backup

## Permissions

- `storage`: Save your time entries and settings
- `alarms`: Schedule reminder notifications  
- `notifications`: Show reminder popups

No network permissions needed - everything stays local to Chrome!
