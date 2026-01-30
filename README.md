# Time Tracker

A time tracking application for logging work hours with periodic reminders.

## Options

### Chrome Extension (Recommended for Windows/Linux)

A standalone Chrome extension that works on any OS. No server required - data syncs automatically across devices via your Google account.

**Installation:**
1. Download `TimeTrackerExtension.zip` from [Releases](https://github.com/Chemical-Biology-STP/time_tracker/releases)
2. Unzip the file
3. Open Chrome → `chrome://extensions/`
4. Enable **Developer mode** (top right toggle)
5. Click **Load unpacked** and select the `chrome_extension` folder
6. Pin the extension to your toolbar

**Features:**
- Quick time logging popup
- Periodic reminder notifications
- Filter entries by group, year, and month
- Export to CSV with totals
- Data syncs across all Chrome browsers

### macOS Companion App

A native macOS menu bar app with bundled Flask server.

**Installation:**
1. Download `TimeTrackerCompanion.dmg` from [Releases](https://github.com/Chemical-Biology-STP/time_tracker/releases)
2. Open the DMG and drag to Applications
3. If you see "app is damaged" error, run:
   ```bash
   xattr -cr /Applications/TimeTrackerCompanion.app
   ```
4. Launch from Applications

**Features:**
- Menu bar icon with quick access
- Bundled Flask server (auto-starts)
- Web interface at http://localhost:5001
- Periodic reminder prompts

## Development

### Prerequisites

- [Pixi](https://pixi.sh) package manager

### Setup

```bash
pixi install
```

### Run Flask Server

```bash
pixi run run
```

Server runs at http://localhost:5001

### Run Tests

```bash
pixi run pytest
```

### Build macOS App

```bash
./build_release.sh
```

Output: `dist/TimeTrackerCompanion.dmg`

## License

See [LICENSE](LICENSE) file.

## Author

Created by **Yew Mun** from the Chemical Biology STP.

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-yellow?style=flat&logo=buy-me-a-coffee)](https://buymeacoffee.com/yewmun)
