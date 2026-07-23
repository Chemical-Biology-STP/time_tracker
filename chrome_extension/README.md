# Time Tracker - Chrome Extension

A fully standalone Chrome extension for tracking work time. Works entirely offline on a single device out of the box, with optional cross-device sync via Google sign-in and Firestore.

## Features

- ⏱️ Quick time logging popup
- 🔔 Periodic reminder notifications
- 📊 View entries and summary statistics
- 📥 Export to CSV for reporting
- 🔄 Optional cloud sync across devices (sign in with Google)
- 👥 Multiple research groups support

## Installation

1. Download or clone this repository
2. Open Chrome and go to `chrome://extensions/`
3. Enable "Developer mode" (toggle in top right)
4. Click "Load unpacked"
5. Select the `chrome_extension` folder
6. Pin the extension to your toolbar for easy access

The extension works fully offline on that one device at this point — no further setup needed.

## Cloud Sync (optional)

To sync your groups, projects, entries, and settings across multiple devices, see [`CLOUD_SYNC_SETUP.md`](./CLOUD_SYNC_SETUP.md). It walks through creating a free Firebase project and connecting it to the extension (about 10-15 minutes, one-time).

If you don't set this up, the extension still works normally — data just stays local to that device, the same way it worked in versions prior to 1.7.0.

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
