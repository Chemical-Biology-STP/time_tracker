// Background service worker for Time Tracker

// Service workers can't use <script> tags, so the shared modules are loaded
// here with importScripts(). Order matters only in that each file expects
// the ones before it to already be on `self` (FirestoreClient uses
// FirebaseConfig, SyncEngine uses CloudAuth + FirestoreClient + the
// chrome.storage.local shape that Storage defines, etc).
importScripts(
  'firebase-config.js',
  'cloud-auth.js',
  'firestore-client.js',
  'storage.js',
  'sync-engine.js'
);

const CLOUD_SYNC_ALARM = 'timeTrackerCloudSync';
const CLOUD_SYNC_PERIOD_MINUTES = 5;

// Initialize alarms on install
chrome.runtime.onInstalled.addListener(async () => {
  console.log('Time Tracker installed');
  await initializeReminderAlarm();
  await initializeCloudSyncAlarm();
});

// Initialize alarms on startup
chrome.runtime.onStartup.addListener(async () => {
  await initializeReminderAlarm();
  await initializeCloudSyncAlarm();
});

// Handle alarms
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'timeTrackerReminder') {
    showReminder();
  } else if (alarm.name === CLOUD_SYNC_ALARM) {
    SyncEngine.syncNow().catch(err => console.warn('Cloud sync failed:', err));
  }
});

// Handle notification click - open popup or create new window
chrome.notifications.onClicked.addListener(async (notificationId) => {
  if (notificationId === 'timeTrackerReminder') {
    try {
      // Try to open popup (requires active browser window)
      await chrome.action.openPopup();
    } catch (e) {
      // No active window - create one and open the popup page
      chrome.windows.create({
        url: 'popup.html',
        type: 'popup',
        width: 400,
        height: 500,
        focused: true
      });
    }
  }
});

async function initializeReminderAlarm() {
  const settings = await Storage.getSettings();

  // Clear existing alarm
  await chrome.alarms.clear('timeTrackerReminder');

  // Create new alarm
  chrome.alarms.create('timeTrackerReminder', {
    delayInMinutes: settings.promptIntervalMinutes,
    periodInMinutes: settings.promptIntervalMinutes
  });

  console.log(`Reminder alarm set for every ${settings.promptIntervalMinutes} minutes`);
}

async function initializeCloudSyncAlarm() {
  chrome.alarms.create(CLOUD_SYNC_ALARM, {
    delayInMinutes: 1,
    periodInMinutes: CLOUD_SYNC_PERIOD_MINUTES
  });

  // Also try an immediate sync (no-op if the user isn't signed in yet).
  SyncEngine.syncNow().catch(err => console.warn('Initial cloud sync failed:', err));
}

async function showReminder() {
  const settings = await Storage.getSettings();

  console.log('Reminder check:', settings);

  if (!settings.notificationsEnabled) {
    console.log('Notifications disabled, skipping');
    return;
  }

  // Check if today is a working day
  const now = new Date();
  const currentDay = now.getDay(); // 0=Sun, 1=Mon, etc.

  console.log('Current day:', currentDay, 'Working days:', settings.workingDays);

  if (!settings.workingDays.includes(currentDay)) {
    console.log('Not a working day, skipping notification');
    return;
  }

  // Check if within working hours
  const currentTime = now.getHours() * 60 + now.getMinutes();
  const [startH, startM] = settings.workStartTime.split(':').map(Number);
  const [endH, endM] = settings.workEndTime.split(':').map(Number);
  const startMinutes = startH * 60 + startM;
  const endMinutes = endH * 60 + endM;

  console.log('Current time (mins):', currentTime, 'Working hours:', startMinutes, '-', endMinutes);

  if (currentTime < startMinutes || currentTime >= endMinutes) {
    console.log('Outside working hours, skipping notification');
    return;
  }

  console.log('Showing notification');
  chrome.notifications.create('timeTrackerReminder', {
    type: 'basic',
    iconUrl: 'icons/icon128.png',
    title: 'Time Tracker',
    message: 'Time to log what you\'ve been working on!',
    priority: 2,
    requireInteraction: true
  });
}

// Listen for settings changes to update the reminder alarm
chrome.storage.onChanged.addListener((changes, namespace) => {
  if (namespace === 'local' && changes.settings) {
    const oldInterval = changes.settings.oldValue && changes.settings.oldValue.promptIntervalMinutes;
    const newInterval = changes.settings.newValue && changes.settings.newValue.promptIntervalMinutes;
    if (newInterval && newInterval !== oldInterval) {
      initializeReminderAlarm();
    }
  }
});
