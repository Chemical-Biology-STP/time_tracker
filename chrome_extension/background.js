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
  const data = await chrome.storage.sync.get([
    'notificationsEnabled',
    'workingDays', 
    'workStartTime',
    'workEndTime'
  ]);
  
  // Apply defaults for missing values
  const notificationsEnabled = data.notificationsEnabled !== false; // default true
  const workingDays = Array.isArray(data.workingDays) && data.workingDays.length > 0 
    ? data.workingDays 
    : [1, 2, 3, 4, 5]; // Mon-Fri default
  const workStartTime = data.workStartTime || '09:00';
  const workEndTime = data.workEndTime || '17:00';
  
  console.log('Reminder check:', { notificationsEnabled, workingDays, workStartTime, workEndTime });
  
  if (!notificationsEnabled) {
    console.log('Notifications disabled, skipping');
    return;
  }
  
  // Check if today is a working day
  const now = new Date();
  const currentDay = now.getDay(); // 0=Sun, 1=Mon, etc.
  
  console.log('Current day:', currentDay, 'Working days:', workingDays);
  
  if (!workingDays.includes(currentDay)) {
    console.log('Not a working day, skipping notification');
    return;
  }
  
  // Check if within working hours
  const currentTime = now.getHours() * 60 + now.getMinutes();
  const [startH, startM] = workStartTime.split(':').map(Number);
  const [endH, endM] = workEndTime.split(':').map(Number);
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

// Listen for settings changes to update alarm
chrome.storage.onChanged.addListener((changes, namespace) => {
  if (namespace === 'sync' && changes.promptIntervalMinutes) {
    initializeAlarm();
  }
});
