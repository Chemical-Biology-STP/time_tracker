// Background service worker for Time Tracker

// Initialize alarm on install
chrome.runtime.onInstalled.addListener(async () => {
  console.log('Time Tracker installed');
  await initializeAlarm();
});

// Initialize alarm on startup
chrome.runtime.onStartup.addListener(async () => {
  await initializeAlarm();
});

// Handle alarm
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'timeTrackerReminder') {
    showReminder();
  }
});

// Handle notification click - open popup
chrome.notifications.onClicked.addListener((notificationId) => {
  if (notificationId === 'timeTrackerReminder') {
    chrome.action.openPopup();
  }
});

async function initializeAlarm() {
  const data = await chrome.storage.sync.get({ promptIntervalMinutes: 30 });
  
  // Clear existing alarm
  await chrome.alarms.clear('timeTrackerReminder');
  
  // Create new alarm
  chrome.alarms.create('timeTrackerReminder', {
    delayInMinutes: data.promptIntervalMinutes,
    periodInMinutes: data.promptIntervalMinutes
  });
  
  console.log(`Reminder alarm set for every ${data.promptIntervalMinutes} minutes`);
}

async function showReminder() {
  const data = await chrome.storage.sync.get({ notificationsEnabled: true });
  
  if (!data.notificationsEnabled) {
    return;
  }
  
  chrome.notifications.create('timeTrackerReminder', {
    type: 'basic',
    iconUrl: 'icons/icon128.png',
    title: 'Time Tracker',
    message: 'Time to log what you\'ve been working on!',
    priority: 2,
    requireInteraction: true
  });
}

// Listen for settings changes to update alarm
chrome.storage.onChanged.addListener((changes, namespace) => {
  if (namespace === 'sync' && changes.promptIntervalMinutes) {
    initializeAlarm();
  }
});
