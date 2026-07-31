# Time Tracker - Chrome Extension

A fully standalone Chrome extension for tracking work time. No server or account required — everything runs locally in your browser.

## Features

- ⏱️ Quick time logging popup
- 🔔 Periodic reminder notifications
- 📊 View entries and summary statistics
- 📥 Export to CSV for reporting
- 🔁 Export/Import JSON to move data between devices
- 👥 Multiple research groups support

## Installation

1. Download or clone this repository
2. Open Chrome and go to `chrome://extensions/`
3. Enable "Developer mode" (toggle in top right)
4. Click "Load unpacked"
5. Select the `chrome_extension` folder
6. Pin the extension to your toolbar for easy access

The extension works fully offline on that one device at this point — no further setup needed.

## Moving data between devices

Use **Export JSON** and **Import JSON** in the Settings page:

1. On the device with your data, open Settings and click **Export JSON**
2. Copy that file to the other device
3. Open Settings there and click **Import JSON**

Importing merges by item — nothing is deleted, and if the same item exists on both devices the more recently edited version is kept. That makes it safe to import the same file twice, or to import in both directions. Settings (reminder interval, hourly rate, working days) are only imported if you tick the checkbox.

## Cloud Sync (advanced, optional, off by default)

There's also an optional automatic sync through Firebase Firestore. It's **disabled and hidden** unless configured, because it requires creating your own Firebase project and OAuth client — see [`CLOUD_SYNC_SETUP.md`](./CLOUD_SYNC_SETUP.md) if you want it.

Be aware that this setup has to be repeated by everyone who installs the extension from source, which is why Export/Import above is the recommended approach for most people.

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
